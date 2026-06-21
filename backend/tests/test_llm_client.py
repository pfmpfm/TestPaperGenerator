"""
LLM客户端测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.llm_client import LLMClient, get_llm_client


class TestLLMClient:
    """LLM客户端测试"""

    def test_init_client(self):
        """测试客户端初始化"""
        client = LLMClient(provider="deepseek")
        assert client.provider == "deepseek"
        assert client.base_url is not None
        assert client.api_key is not None

    def test_get_models(self):
        """测试获取模型名称"""
        client = LLMClient(provider="deepseek")
        high_quality = client.get_high_quality_model()
        cost_efficient = client.get_cost_efficient_model()
        assert high_quality
        assert cost_efficient

    @pytest.mark.asyncio
    @patch('app.core.llm_client.AsyncOpenAI')
    async def test_async_chat_completion(self, mock_openai):
        """测试异步聊天补全"""
        # Mock响应
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="测试响应"))
        ]
        mock_response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        client = LLMClient(provider="deepseek")
        client.async_client = mock_client

        messages = [{"role": "user", "content": "你好"}]
        response = await client.async_chat_completion(messages)

        assert response is not None
        assert hasattr(response, 'choices')

    def test_get_singleton(self):
        """测试单例获取"""
        client1 = get_llm_client()
        client2 = get_llm_client()
        assert client1 is client2


class TestLLMClientError:
    """LLM客户端错误处理测试"""

    def test_invalid_provider(self):
        """测试无效提供商"""
        with pytest.raises(ValueError):
            LLMClient(provider="invalid_provider")

    @patch.dict('os.environ', {}, clear=True)
    @patch('app.core.config.settings')
    def test_missing_api_key(self, mock_settings):
        """测试缺失API密钥"""
        mock_settings.llm_provider = "deepseek"
        mock_settings.deepseek_api_key = None

        with pytest.raises(ValueError, match="未配置API密钥"):
            LLMClient(provider="deepseek")