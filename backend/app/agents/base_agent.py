"""
Agent基类 - 封装LLM调用、重试和JSON解析
"""
import json
import re
from typing import Any, Dict, List, Optional

from app.core.config import model_config, settings
from app.core.llm_client import get_llm_client
from app.core.logging import logger


class BaseAgent:
    """所有Agent的基类"""

    # 子类应覆盖此名称，用于从config/models.yaml读取agent配置
    agent_name: str = "base"

    def __init__(self, provider: Optional[str] = None):
        self.llm = get_llm_client(provider)
        self.config = model_config.get_agent_config(self.agent_name)

    def _resolve_model(self) -> str:
        """根据agent配置的llm_type选择模型"""
        llm_type = self.config.get("llm_type", "high_quality")
        if llm_type == "cost_efficient":
            return self.llm.get_cost_efficient_model()
        return self.llm.get_high_quality_model()

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        model: Optional[str] = None,
    ) -> str:
        """
        调用LLM并返回文本内容

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            model: 模型名称，默认按agent配置选择
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await self.llm.async_chat_completion(
            messages=messages,
            model=model or self._resolve_model(),
            temperature=temperature,
        )
        return response.choices[0].message.content

    @staticmethod
    def extract_json(text: str) -> Any:
        """
        从LLM输出中提取JSON

        支持：纯JSON、```json代码块、混杂文本中的JSON对象/数组

        注意：使用 strict=False 来保留 LaTeX 中的反斜杠（如 \frac）
        """
        if text is None:
            raise ValueError("LLM返回内容为空")

        # 1. 优先提取```json代码块
        fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        candidate = fence_match.group(1).strip() if fence_match else text.strip()

        # 2. 直接尝试解析（strict=False 保留 LaTeX 反斜杠）
        try:
            return json.loads(candidate, strict=False)
        except json.JSONDecodeError:
            pass

        # 3. 提取第一个JSON数组或对象
        for pattern in (r"\[.*\]", r"\{.*\}"):
            match = re.search(pattern, candidate, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0), strict=False)
                except json.JSONDecodeError:
                    continue

        logger.bind(agent=True).error(f"无法从LLM输出解析JSON: {text[:500]}")
        raise ValueError("无法从LLM输出解析JSON")

    async def call_llm_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_retries: Optional[int] = None,
    ) -> Any:
        """
        调用LLM并解析为JSON，失败时重试

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数
            max_retries: 最大重试次数，默认按agent配置
        """
        retries = max_retries if max_retries is not None else self.config.get(
            "max_retries", settings.max_retries
        )
        last_error: Optional[Exception] = None

        for attempt in range(1, retries + 1):
            try:
                content = await self.call_llm(
                    system_prompt, user_prompt, temperature=temperature
                )
                return self.extract_json(content)
            except Exception as e:  # noqa: BLE001 - 重试所有可恢复错误
                last_error = e
                logger.bind(agent=True).warning(
                    f"[{self.agent_name}] LLM调用/解析失败 (第{attempt}/{retries}次): {e}"
                )

        raise RuntimeError(
            f"[{self.agent_name}] LLM调用在{retries}次重试后仍失败: {last_error}"
        )
