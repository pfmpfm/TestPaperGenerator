"""
核心配置模块测试
"""
import pytest
from app.core.config import settings, model_config


class TestSettings:
    """配置测试"""

    def test_app_config(self):
        """测试应用配置"""
        assert settings.app_name == "ExamGenerator"
        assert settings.app_version == "1.0.0"
        assert settings.env in ["development", "testing", "production"]

    def test_database_url(self):
        """测试数据库URL生成"""
        assert "mysql" in settings.database_url
        assert settings.mysql_database in settings.database_url

    def test_async_database_url(self):
        """测试异步数据库URL"""
        assert "aiomysql" in settings.async_database_url

    def test_cors_origins_list(self):
        """测试CORS来源列表"""
        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert len(origins) > 0

    def test_monitoring_config(self):
        """测试监控配置"""
        assert isinstance(settings.enable_metrics, bool)
        assert isinstance(settings.metrics_port, int)


class TestModelConfig:
    """模型配置测试"""

    def test_load_config(self):
        """测试配置加载"""
        assert model_config.config is not None
        assert "llm" in model_config.config

    def test_get_llm_config(self):
        """测试获取LLM配置"""
        config = model_config.get_llm_config("deepseek")
        assert config is not None
        assert "base_url" in config

    def test_get_embedding_config(self):
        """测试获取Embedding配置"""
        config = model_config.get_embedding_config("zhipu")
        assert config is not None
        assert "model" in config

    def test_invalid_provider(self):
        """测试无效提供商"""
        config = model_config.get_llm_config("invalid_provider")
        assert config == {}