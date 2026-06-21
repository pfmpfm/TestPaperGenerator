"""
试卷生成服务
"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.database import (
    GenerationSession as DBSession,
    ExamPaper,
    Question as DBQuestion,
)
from app.schemas.schemas import (
    ExamRequirement,
    GenerationSession,
    SessionStatus,
)
from app.workflows.generation_workflow import GenerationWorkflow


class GenerationService:
    """试卷生成服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, requirement: ExamRequirement) -> GenerationSession:
        """
        创建生成会话

        Args:
            requirement: 试卷需求

        Returns:
            生成会话
        """
        # 创建会话记录
        session = DBSession(
            status=SessionStatus.IN_PROGRESS,
            requirement=requirement.model_dump(),
            workflow_state={"current_step": "init"},
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(f"创建生成会话 | Session ID: {session.session_id}")

        return GenerationSession.model_validate(session)

    async def get_session(self, session_id: str) -> Optional[GenerationSession]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息
        """
        result = await self.db.execute(
            select(DBSession).where(DBSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            return GenerationSession.model_validate(session)
        return None

    async def update_session_status(
        self,
        session_id: str,
        status: SessionStatus,
        workflow_state: Optional[dict] = None,
    ):
        """
        更新会话状态

        Args:
            session_id: 会话ID
            status: 新状态
            workflow_state: Workflow状态
        """
        result = await self.db.execute(
            select(DBSession).where(DBSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if session:
            session.status = status
            if workflow_state:
                session.workflow_state = workflow_state
            session.updated_at = datetime.utcnow()

            await self.db.commit()
            logger.info(f"更新会话状态 | Session ID: {session_id} | Status: {status}")

    async def get_paper_by_session(self, session_id: str) -> Optional[ExamPaper]:
        """
        根据会话ID获取试卷

        Args:
            session_id: 会话ID

        Returns:
            试卷
        """
        result = await self.db.execute(
            select(ExamPaper).where(ExamPaper.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def cancel_session(self, session_id: str) -> bool:
        """
        取消生成任务

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        result = await self.db.execute(
            select(DBSession).where(DBSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session or session.status != SessionStatus.IN_PROGRESS:
            return False

        session.status = SessionStatus.FAILED
        session.updated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"取消生成任务 | Session ID: {session_id}")
        return True

    async def run_generation(self, session_id: str):
        """
        执行生成任务（后台任务入口）

        后台任务在请求结束后运行，原请求的db session已关闭，
        因此这里创建独立的数据库会话。

        Args:
            session_id: 会话ID
        """
        async with AsyncSessionLocal() as db:
            service = GenerationService(db)
            await service._execute_generation(session_id)

    async def _execute_generation(self, session_id: str):
        """执行生成的实际逻辑（使用本服务持有的db会话）"""
        try:
            logger.info(f"开始执行生成任务 | Session ID: {session_id}")

            session = await self.get_session(session_id)
            if not session:
                logger.error(f"会话不存在 | Session ID: {session_id}")
                return

            requirement = session.requirement

            # 进度回调：每完成一个节点更新会话的workflow_state
            async def on_progress(step: str, state: dict):
                await self.update_session_status(
                    session_id,
                    SessionStatus.IN_PROGRESS,
                    {
                        "current_step": step,
                        "question_count": len(state.get("questions", [])),
                    },
                )

            # 1. 执行LangGraph workflow生成题目和试卷
            workflow = GenerationWorkflow()
            result = await workflow.run(requirement, progress_callback=on_progress)

            questions = result.get("questions", [])
            paper_data = result.get("paper", {})

            if not paper_data or not questions:
                raise RuntimeError("Workflow未能生成完整试卷，请检查workflow日志")

            # 2. 持久化题目
            question_ids = await self._save_questions(questions)

            # 3. 持久化试卷
            await self._save_paper(session_id, paper_data, question_ids)

            # 4. 更新会话状态
            await self.update_session_status(
                session_id,
                SessionStatus.COMPLETED,
                {
                    "current_step": "completed",
                    "question_count": len(question_ids),
                    "errors": result.get("errors", []),
                },
            )

            logger.info(
                f"生成任务完成 | Session ID: {session_id} | 题目数: {len(question_ids)}"
            )

        except Exception as e:
            logger.exception(f"生成任务失败 | Session ID: {session_id} | Error: {str(e)}")
            await self.update_session_status(
                session_id,
                SessionStatus.FAILED,
                {"current_step": "failed", "error": str(e)},
            )

    async def _save_questions(self, questions: list) -> list:
        """保存生成的题目，返回题目ID列表"""
        question_ids = []
        for q in questions:
            db_question = DBQuestion(
                content=q["content"],
                answer=q.get("answer", ""),
                explanation=q.get("explanation"),
                question_type=q.get("question_type"),
                difficulty=q.get("difficulty"),
                grade=q.get("grade"),
                subject=q.get("subject"),
                knowledge_points=q.get("knowledge_points", []),
                figure_url=q.get("figure_url"),
                figure_spec=q.get("figure_spec"),
                quality_score=q.get("quality_score"),
                is_approved=bool(q.get("is_approved", True)),
            )
            self.db.add(db_question)
            await self.db.flush()  # 获取生成的id
            question_ids.append(db_question.id)

        await self.db.commit()
        logger.info(f"保存题目完成 | 数量: {len(question_ids)}")
        return question_ids

    async def _save_paper(self, session_id: str, paper_data: dict, question_ids: list):
        """保存试卷记录"""
        paper = ExamPaper(
            title=paper_data.get("title", "未命名试卷"),
            paper_metadata=paper_data.get("metadata", {}),
            question_ids=question_ids,
            session_id=session_id,
            status="draft",
        )
        self.db.add(paper)
        await self.db.commit()
        logger.info(f"保存试卷完成 | Session ID: {session_id} | 试卷标题: {paper.title}")
