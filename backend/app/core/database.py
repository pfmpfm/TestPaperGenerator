"""
数据库连接模块
"""
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from redis import asyncio as aioredis
from qdrant_client import QdrantClient
from qdrant_client.async_qdrant_client import AsyncQdrantClient

from app.core.config import settings

# ==================== MySQL ====================
# 同步引擎 (用于Alembic迁移)
sync_engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.debug,
)

# 异步引擎 (用于FastAPI)
async_engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.debug,
)

# Session工厂
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Base类
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ==================== Redis ====================
class RedisClient:
    """Redis客户端"""

    def __init__(self):
        self.client: aioredis.Redis | None = None

    async def connect(self):
        """连接Redis"""
        self.client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10,
        )

    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.close()

    async def get(self, key: str):
        """获取值"""
        if not self.client:
            await self.connect()
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        """设置值"""
        if not self.client:
            await self.connect()
        return await self.client.set(key, value, ex=ex)

    async def delete(self, key: str):
        """删除键"""
        if not self.client:
            await self.connect()
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.client:
            await self.connect()
        return bool(await self.client.exists(key))

    async def expire(self, key: str, seconds: int):
        """设置过期时间"""
        if not self.client:
            await self.connect()
        return await self.client.expire(key, seconds)

    async def hset(self, name: str, key: str, value: str):
        """Hash set"""
        if not self.client:
            await self.connect()
        return await self.client.hset(name, key, value)

    async def hget(self, name: str, key: str):
        """Hash get"""
        if not self.client:
            await self.connect()
        return await self.client.hget(name, key)

    async def hgetall(self, name: str):
        """Hash get all"""
        if not self.client:
            await self.connect()
        return await self.client.hgetall(name)


# Redis客户端实例
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """获取Redis客户端"""
    if not redis_client.client:
        await redis_client.connect()
    return redis_client


# ==================== Qdrant ====================
class QdrantManager:
    """Qdrant向量数据库管理器"""

    def __init__(self):
        self.sync_client: QdrantClient | None = None
        self.async_client: AsyncQdrantClient | None = None

    def get_sync_client(self) -> QdrantClient:
        """获取同步客户端"""
        if not self.sync_client:
            self.sync_client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                timeout=30,
            )
        return self.sync_client

    def get_async_client(self) -> AsyncQdrantClient:
        """获取异步客户端"""
        if not self.async_client:
            self.async_client = AsyncQdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                timeout=30,
            )
        return self.async_client

    async def close(self):
        """关闭连接"""
        if self.async_client:
            await self.async_client.close()


# Qdrant管理器实例
qdrant_manager = QdrantManager()


def get_qdrant_client() -> QdrantClient:
    """获取Qdrant同步客户端"""
    return qdrant_manager.get_sync_client()


def get_qdrant_async_client() -> AsyncQdrantClient:
    """获取Qdrant异步客户端"""
    return qdrant_manager.get_async_client()


# ==================== 数据库初始化 ====================
async def init_db():
    """初始化数据库"""
    # 创建所有表 (仅用于开发，生产环境使用Alembic)
    if settings.debug:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    await async_engine.dispose()
    await redis_client.disconnect()
    await qdrant_manager.close()
