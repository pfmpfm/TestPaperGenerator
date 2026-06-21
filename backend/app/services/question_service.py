"""
题目服务
"""
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.database import Question as DBQuestion
from app.schemas.schemas import Question, QuestionCreate


class QuestionService:
    """题目服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_questions(
        self,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Question], int]:
        """
        查询题目列表

        Returns:
            (题目列表, 总数)
        """
        # 构建查询
        query = select(DBQuestion)

        # 添加过滤条件
        if grade:
            query = query.where(DBQuestion.grade == grade)
        if subject:
            query = query.where(DBQuestion.subject == subject)
        if difficulty:
            query = query.where(DBQuestion.difficulty == difficulty)
        if question_type:
            query = query.where(DBQuestion.question_type == question_type)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页查询
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        questions = result.scalars().all()

        return [Question.model_validate(q) for q in questions], total

    async def get_question(self, question_id: str) -> Optional[Question]:
        """获取单个题目"""
        result = await self.db.execute(
            select(DBQuestion).where(DBQuestion.id == question_id)
        )
        question = result.scalar_one_or_none()

        if question:
            return Question.model_validate(question)
        return None

    async def create_question(self, question: QuestionCreate) -> Question:
        """创建题目"""
        db_question = DBQuestion(**question.model_dump())
        self.db.add(db_question)
        await self.db.commit()
        await self.db.refresh(db_question)

        logger.info(f"创建题目 | ID: {db_question.id}")
        return Question.model_validate(db_question)

    async def delete_question(self, question_id: str) -> bool:
        """删除题目"""
        result = await self.db.execute(
            select(DBQuestion).where(DBQuestion.id == question_id)
        )
        question = result.scalar_one_or_none()

        if not question:
            return False

        await self.db.delete(question)
        await self.db.commit()

        logger.info(f"删除题目 | ID: {question_id}")
        return True
