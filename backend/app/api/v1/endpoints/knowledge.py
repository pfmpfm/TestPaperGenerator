"""
知识点管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.schemas import ResponseBase

router = APIRouter()


@router.get("/", response_model=ResponseBase)
async def list_knowledge_points(
    db: AsyncSession = Depends(get_db),
):
    """
    查询知识点列表
    """
    # TODO: 实现知识点列表查询
    return ResponseBase(
        success=True,
        message="查询成功",
        data={"knowledge_points": []}
    )
