"""
LLM客户端管理 - 支持多种国产大模型
"""
import os
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI, AsyncOpenAI

from app.core.config import settings, model_config
from app.core.logging import logger


class LLMClient:
    """LLM客户端封装"""

    def __init__(self, provider: Optional[str] = None):
        """
        初始化LLM客户端

        Args:
            provider: 提供商名称 (deepseek/zhipu/kimi/qwen)，默认使用配置文件中的设置
        """
        self.provider = provider or settings.llm_provider
        self.config = model_config.get_llm_config(self.provider)

        # 获取API配置
        self.base_url = self._get_base_url()
        self.api_key = self._get_api_key()

        # 初始化OpenAI客户端
        self.sync_client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=settings.llm_timeout,
        )

        self.async_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=settings.llm_timeout,
        )

        logger.bind(llm=True).info(
            f"LLM客户端初始化成功 | 提供商: {self.provider} | Base URL: {self.base_url}"
        )

    def _get_base_url(self) -> str:
        """获取Base URL"""
        base_url = self.config.get("base_url")
        if not base_url:
            raise ValueError(f"未配置 {self.provider} 的 base_url")
        return base_url

    def _get_api_key(self) -> str:
        """获取API Key

        优先从环境变量读取，回退到settings(已加载.env文件)。
        """
        api_key_env = f"{self.provider.upper()}_API_KEY"
        api_key = os.getenv(api_key_env) or getattr(
            settings, f"{self.provider.lower()}_api_key", None
        )

        if not api_key:
            raise ValueError(f"未配置API密钥: {api_key_env} (检查环境变量或.env文件)")

        return api_key

    def get_high_quality_model(self) -> str:
        """获取高质量模型名称"""
        return self.config.get("models", {}).get("high_quality", "")

    def get_cost_efficient_model(self) -> str:
        """获取成本优化模型名称"""
        return self.config.get("models", {}).get("cost_efficient", "")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """
        同步聊天补全

        Args:
            messages: 消息列表
            model: 模型名称，默认使用高质量模型
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出
            **kwargs: 其他参数
        """
        if model is None:
            model = self.get_high_quality_model()

        if max_tokens is None:
            max_tokens = self.config.get("max_tokens", 4096)

        logger.bind(llm=True).debug(
            f"调用LLM | 模型: {model} | 消息数: {len(messages)} | Temperature: {temperature}"
        )

        try:
            response = self.sync_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )

            if not stream:
                logger.bind(llm=True).debug(
                    f"LLM响应 | Token使用: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}"
                )

            return response

        except Exception as e:
            logger.bind(llm=True).error(f"LLM调用失败: {str(e)}")
            raise

    async def async_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """
        异步聊天补全

        Args:
            messages: 消息列表
            model: 模型名称，默认使用高质量模型
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出
            **kwargs: 其他参数
        """
        if model is None:
            model = self.get_high_quality_model()

        if max_tokens is None:
            max_tokens = self.config.get("max_tokens", 4096)

        logger.bind(llm=True).debug(
            f"异步调用LLM | 模型: {model} | 消息数: {len(messages)} | Temperature: {temperature}"
        )

        # Metrics: 记录开始时间
        start_time = time.time()
        status = "success"

        try:
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )

            if not stream:
                # Metrics: 记录token使用
                if hasattr(response, 'usage') and response.usage:
                    if settings.enable_metrics:
                        from app.core.metrics import llm_tokens_used
                        llm_tokens_used.labels(
                            provider=self.provider,
                            model=model,
                            type='prompt'
                        ).inc(response.usage.prompt_tokens)
                        llm_tokens_used.labels(
                            provider=self.provider,
                            model=model,
                            type='completion'
                        ).inc(response.usage.completion_tokens)

                    logger.bind(llm=True).debug(
                        f"LLM响应 | Token使用: {response.usage.total_tokens}"
                    )

            return response

        except Exception as e:
            status = "error"
            logger.bind(llm=True).error(f"LLM调用失败: {str(e)}")
            raise
        finally:
            # Metrics: 记录请求
            if settings.enable_metrics:
                from app.core.metrics import llm_requests_total, llm_request_duration_seconds
                duration = time.time() - start_time
                llm_requests_total.labels(
                    provider=self.provider,
                    model=model,
                    status=status
                ).inc()
                llm_request_duration_seconds.labels(
                    provider=self.provider,
                    model=model
                ).observe(duration)


class EmbeddingClient:
    """Embedding客户端封装"""

    def __init__(self, provider: Optional[str] = None):
        """
        初始化Embedding客户端

        Args:
            provider: 提供商名称，默认使用配置文件中的设置
        """
        self.provider = provider or settings.embedding_provider
        self.config = model_config.get_embedding_config(self.provider)

        # 获取API配置
        self.base_url = self.config.get("base_url")
        self.api_key = self._get_api_key()
        self.model = self.config.get("model", "")
        self.dimension = self.config.get("dimension", 1024)

        # 初始化OpenAI客户端（兼容接口）
        self.sync_client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=settings.llm_timeout,
        )

        self.async_client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=settings.llm_timeout,
        )

        logger.bind(llm=True).info(
            f"Embedding客户端初始化成功 | 提供商: {self.provider} | 维度: {self.dimension}"
        )

    def _get_api_key(self) -> str:
        """获取API Key

        优先从环境变量读取，回退到settings(已加载.env文件)。
        """
        api_key_env = f"{self.provider.upper()}_API_KEY"
        api_key = os.getenv(api_key_env) or getattr(
            settings, f"{self.provider.lower()}_api_key", None
        )

        if not api_key:
            raise ValueError(f"未配置API密钥: {api_key_env} (检查环境变量或.env文件)")

        return api_key

    def create_embedding(self, text: str) -> List[float]:
        """
        同步创建embedding

        Args:
            text: 文本内容

        Returns:
            embedding向量
        """
        logger.bind(llm=True).debug(f"创建Embedding | 文本长度: {len(text)}")

        try:
            response = self.sync_client.embeddings.create(
                model=self.model,
                input=text,
            )

            embedding = response.data[0].embedding
            logger.bind(llm=True).debug(f"Embedding创建成功 | 维度: {len(embedding)}")

            return embedding

        except Exception as e:
            logger.bind(llm=True).error(f"Embedding创建失败: {str(e)}")
            raise

    async def async_create_embedding(self, text: str) -> List[float]:
        """
        异步创建embedding

        Args:
            text: 文本内容

        Returns:
            embedding向量
        """
        logger.bind(llm=True).debug(f"异步创建Embedding | 文本长度: {len(text)}")

        try:
            response = await self.async_client.embeddings.create(
                model=self.model,
                input=text,
            )

            embedding = response.data[0].embedding
            logger.bind(llm=True).debug(f"Embedding创建成功 | 维度: {len(embedding)}")

            return embedding

        except Exception as e:
            logger.bind(llm=True).error(f"异步Embedding创建失败: {str(e)}")
            raise

    def create_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量创建embeddings

        Args:
            texts: 文本列表

        Returns:
            embedding向量列表
        """
        logger.bind(llm=True).debug(f"批量创建Embeddings | 数量: {len(texts)}")

        try:
            response = self.sync_client.embeddings.create(
                model=self.model,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]
            logger.bind(llm=True).debug(f"批量Embeddings创建成功 | 数量: {len(embeddings)}")

            return embeddings

        except Exception as e:
            logger.bind(llm=True).error(f"批量Embedding创建失败: {str(e)}")
            raise


# 全局客户端实例
_llm_client: Optional[LLMClient] = None
_embedding_client: Optional[EmbeddingClient] = None


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """获取LLM客户端实例（单例）"""
    global _llm_client
    if _llm_client is None or (provider and provider != _llm_client.provider):
        _llm_client = LLMClient(provider)
    return _llm_client


def get_embedding_client(provider: Optional[str] = None) -> EmbeddingClient:
    """获取Embedding客户端实例（单例）"""
    global _embedding_client
    if _embedding_client is None or (provider and provider != _embedding_client.provider):
        _embedding_client = EmbeddingClient(provider)
    return _embedding_client
