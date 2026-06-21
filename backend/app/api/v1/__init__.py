"""
API v1 路由配置
"""
from fastapi import APIRouter

from app.api.v1.endpoints import generation, questions, papers, knowledge, textbook

api_router = APIRouter()

# 注册子路由
api_router.include_router(
    generation.router,
    prefix="/generation",
    tags=["试卷生成"]
)

api_router.include_router(
    questions.router,
    prefix="/questions",
    tags=["题目管理"]
)

api_router.include_router(
    papers.router,
    prefix="/papers",
    tags=["试卷管理"]
)

api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["知识点管理"]
)

api_router.include_router(
    textbook.router,
    prefix="/textbook",
    tags=["教材知识库"]
)
