"""
试卷生成API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.schemas.schemas import (
    ExamRequirement,
    GenerationSession,
    ResponseBase,
    SessionStatus,
)
from app.services.generation_service import GenerationService

router = APIRouter()


@router.post("/start", response_model=ResponseBase)
async def start_generation(
    requirement: ExamRequirement,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    开始生成试卷

    Args:
        requirement: 试卷需求
        background_tasks: 后台任务
        db: 数据库会话

    Returns:
        包含session_id的响应
    """
    try:
        logger.info(f"收到试卷生成请求 | 年级: {requirement.grade} | 科目: {requirement.subject}")

        # 创建生成服务
        service = GenerationService(db)

        # 创建会话
        session = await service.create_session(requirement)

        # 在后台启动生成任务
        background_tasks.add_task(service.run_generation, session.session_id)

        logger.info(f"生成任务已启动 | Session ID: {session.session_id}")

        return ResponseBase(
            success=True,
            message="试卷生成任务已启动",
            data={
                "session_id": session.session_id,
                "status": session.status,
            }
        )

    except Exception as e:
        logger.exception(f"启动生成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{session_id}", response_model=ResponseBase)
async def get_generation_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    查询生成状态

    Args:
        session_id: 会话ID
        db: 数据库会话

    Returns:
        生成状态信息
    """
    try:
        service = GenerationService(db)
        session = await service.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        return ResponseBase(
            success=True,
            message="查询成功",
            data={
                "session_id": session.session_id,
                "status": session.status,
                "workflow_state": session.workflow_state,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"查询生成状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result/{session_id}", response_model=ResponseBase)
async def get_generation_result(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取生成结果

    Args:
        session_id: 会话ID
        db: 数据库会话

    Returns:
        生成的试卷信息
    """
    try:
        service = GenerationService(db)
        session = await service.get_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        if session.status != SessionStatus.COMPLETED:
            return ResponseBase(
                success=False,
                message=f"试卷尚未生成完成，当前状态: {session.status}",
                data={"status": session.status}
            )

        # 获取生成的试卷
        paper = await service.get_paper_by_session(session_id)

        if not paper:
            raise HTTPException(status_code=404, detail="未找到生成的试卷")

        return ResponseBase(
            success=True,
            message="获取成功",
            data={
                "paper_id": paper.id,
                "title": paper.title,
                "metadata": paper.paper_metadata,
                "question_ids": paper.question_ids,
                "quality_score": float(paper.quality_score) if paper.quality_score else None,
                "created_at": paper.created_at.isoformat(),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取生成结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cancel/{session_id}", response_model=ResponseBase)
async def cancel_generation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    取消生成任务

    Args:
        session_id: 会话ID
        db: 数据库会话

    Returns:
        取消结果
    """
    try:
        service = GenerationService(db)
        success = await service.cancel_session(session_id)

        if not success:
            raise HTTPException(status_code=404, detail="会话不存在或已完成")

        return ResponseBase(
            success=True,
            message="生成任务已取消",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"取消生成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
