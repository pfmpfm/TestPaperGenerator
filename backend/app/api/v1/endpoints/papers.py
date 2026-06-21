"""
试卷管理API
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.schemas.schemas import ResponseBase

router = APIRouter()


@router.get("/", response_model=ResponseBase)
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    查询试卷列表
    """
    # TODO: 实现试卷列表查询
    return ResponseBase(
        success=True,
        message="查询成功",
        data={"papers": [], "total": 0}
    )


@router.get("/{paper_id}", response_model=ResponseBase)
async def get_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取试卷详情
    """
    # TODO: 实现试卷详情查询
    return ResponseBase(
        success=True,
        message="查询成功",
        data=None
    )
