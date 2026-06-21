"""
AutoGen模型客户端适配器

将项目的LLM配置(国产模型/OpenAI兼容接口)桥接到AutoGen的模型客户端。
"""
from typing import Optional

from autogen_core.models import ModelFamily, ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient

from app.core.config import settings
from app.core.llm_client import LLMClient


def build_autogen_model_client(
    provider: Optional[str] = None,
    llm_type: str = "high_quality",
) -> OpenAIChatCompletionClient:
    """
    构建AutoGen的OpenAI兼容模型客户端

    国产模型(DeepSeek/智谱等)对AutoGen是未知模型，必须显式提供model_info，
    否则AutoGen会因无法识别模型能力而报错。

    Args:
        provider: 提供商，默认使用settings.llm_provider
        llm_type: high_quality 或 cost_efficient

    Returns:
        配置好的AutoGen模型客户端
    """
    llm = LLMClient(provider)
    model = (
        llm.get_high_quality_model()
        if llm_type == "high_quality"
        else llm.get_cost_efficient_model()
    )

    model_info = ModelInfo(
        vision=False,
        function_calling=False,
        json_output=True,
        family=ModelFamily.UNKNOWN,
        structured_output=False,
    )

    return OpenAIChatCompletionClient(
        model=model,
        base_url=llm.base_url,
        api_key=llm.api_key,
        timeout=settings.llm_timeout,
        model_info=model_info,
    )
