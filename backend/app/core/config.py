"""
核心配置模块 - 加载环境变量和配置文件
"""
from typing import List, Optional
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ==================== 应用配置 ====================
    app_name: str = Field(default="ExamGenerator")
    app_version: str = Field(default="1.0.0")
    env: str = Field(default="development")
    debug: bool = Field(default=True)
    secret_key: str = Field(default="change-me-in-production")

    # ==================== 数据库配置 ====================
    # MySQL
    mysql_host: str = Field(default="localhost")
    mysql_port: int = Field(default=3306)
    mysql_user: str = Field(default="exam_user")
    mysql_password: str = Field(default="exam_password_change_me")
    mysql_database: str = Field(default="exam_generator")

    @property
    def database_url(self) -> str:
        """MySQL连接URL"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"

    @property
    def async_database_url(self) -> str:
        """MySQL异步连接URL"""
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)

    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Qdrant
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_api_key: Optional[str] = Field(default=None)

    @field_validator("qdrant_api_key", mode="before")
    @classmethod
    def _empty_api_key_to_none(cls, v):
        """空字符串归一化为None，避免Qdrant客户端误用HTTPS"""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    # ==================== LLM配置 ====================
    # API Keys
    deepseek_api_key: Optional[str] = Field(default=None)
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1")

    zhipu_api_key: Optional[str] = Field(default=None)
    zhipu_base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4")

    kimi_api_key: Optional[str] = Field(default=None)
    kimi_base_url: str = Field(default="https://api.moonshot.cn/v1")

    qwen_api_key: Optional[str] = Field(default=None)
    qwen_base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1")

    # 模型选择
    llm_provider: str = Field(default="deepseek")
    llm_high_quality_model: str = Field(default="deepseek-chat")
    llm_cost_efficient_model: str = Field(default="deepseek-chat")

    embedding_provider: str = Field(default="zhipu")
    embedding_model: str = Field(default="embedding-3")
    embedding_dimension: int = Field(default=2048)

    # ==================== LangSmith配置 ====================
    langchain_tracing_v2: bool = Field(default=False)
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com")
    langchain_api_key: Optional[str] = Field(default=None)
    langchain_project: str = Field(default="exam-generator-mvp")

    # ==================== 监控配置 ====================
    # Prometheus
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=9090)

    # ==================== 文件存储配置 ====================
    upload_dir: str = Field(default="./data/uploads")
    max_upload_size: int = Field(default=50)  # MB

    # 配图存储路径（支持相对路径和绝对路径）
    figure_dir: str = Field(default="./static/figures")  # 图片保存目录
    figure_url_prefix: str = Field(default="/static/figures")  # 访问URL前缀

    # OSS配置
    oss_provider: str = Field(default="local")  # aliyun/qiniu/local
    oss_access_key: Optional[str] = Field(default=None)
    oss_secret_key: Optional[str] = Field(default=None)
    oss_bucket: Optional[str] = Field(default=None)
    oss_endpoint: Optional[str] = Field(default=None)

    # ==================== 安全配置 ====================
    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=1440)

    # 内容安全
    content_safety_provider: str = Field(default="none")  # baidu/aliyun/none
    content_safety_api_key: Optional[str] = Field(default=None)
    content_safety_secret_key: Optional[str] = Field(default=None)

    # ==================== 服务配置 ====================
    # API
    api_v1_prefix: str = Field(default="/api/v1")
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000")

    @property
    def cors_origins_list(self) -> List[str]:
        """CORS允许的源列表"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # WebSocket
    ws_heartbeat_interval: int = Field(default=30)

    # 并发控制
    max_concurrent_llm_calls: int = Field(default=3)
    max_concurrent_generation_sessions: int = Field(default=5)

    # 超时配置
    llm_timeout: int = Field(default=300)  # 通义千问等国产API响应慢，文档解析需要5分钟
    tool_timeout: int = Field(default=30)
    workflow_timeout: int = Field(default=300)

    # 重试配置
    max_retries: int = Field(default=3)
    retry_backoff_factor: int = Field(default=2)

    # ==================== 监控配置 ====================
    prometheus_port: int = Field(default=9090)
    metrics_enabled: bool = Field(default=True)

    # Sentry
    sentry_dsn: Optional[str] = Field(default=None)
    sentry_environment: str = Field(default="development")

    # ==================== 其他配置 ====================
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # json/text
    timezone: str = Field(default="Asia/Shanghai")


class ModelConfig:
    """模型配置加载器"""

    def __init__(self, config_path: str = "config/models.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载YAML配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def get_llm_config(self, provider: Optional[str] = None) -> dict:
        """获取LLM配置"""
        if provider is None:
            provider = self.config["llm"]["provider"]

        return self.config["llm"].get(provider, {})

    def get_embedding_config(self, provider: Optional[str] = None) -> dict:
        """获取Embedding配置"""
        if provider is None:
            provider = self.config["embedding"]["provider"]

        return self.config["embedding"].get(provider, {})

    def get_agent_config(self, agent_name: str) -> dict:
        """获取Agent配置"""
        return self.config["agents"].get(agent_name, {})

    def get_workflow_config(self) -> dict:
        """获取Workflow配置"""
        return self.config.get("workflow", {})

    def get_vector_db_config(self, collection_name: str) -> dict:
        """获取向量数据库配置"""
        collections = self.config.get("vector_db", {}).get("collections", {})
        return collections.get(collection_name, {})

    def get_rag_config(self) -> dict:
        """获取RAG配置"""
        return self.config.get("rag", {})

    def get_question_generation_config(self) -> dict:
        """获取题目生成配置"""
        return self.config.get("question_generation", {})

    def get_figure_generation_config(self) -> dict:
        """获取配图生成配置"""
        return self.config.get("figure_generation", {})


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例）"""
    return Settings()


@lru_cache()
def get_model_config() -> ModelConfig:
    """获取模型配置实例（单例）"""
    return ModelConfig()


# 导出配置实例
settings = get_settings()
model_config = get_model_config()
