"""LLM 交互模块，封装大语言模型的调用、重试和消息发送。"""

from typing import Any

from app.config.setting import ApiType
from app.core.llm.types import StandardResponse
from app.core.llm.providers.base import BaseProvider
from app.core.llm.providers.openai_chat import OpenAIChatProvider
from app.core.llm.providers.openai_responses import OpenAIResponsesProvider
from app.core.llm.providers.anthropic import AnthropicProvider
from app.utils.log_util import logger


class LLMConfigError(RuntimeError):
    """LLM 配置缺失时抛出。"""


class LLM:
    """大语言模型封装类，提供对话调用、重试和工具调用验证功能。"""

    def __init__(
        self,
        api_type: ApiType | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        task_id: str = "",
        max_tokens: int | None = None,
    ):
        self.api_type = api_type
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.chat_count = 0
        self.max_tokens = max_tokens
        self.task_id = task_id
        self.provider = self._create_provider(api_type)

    def _create_provider(self, api_type: ApiType | None) -> BaseProvider:
        """根据 api_type 创建对应的 Provider。"""
        match api_type:
            case ApiType.OPENAI_RESPONSES:
                return OpenAIResponsesProvider()
            case ApiType.ANTHROPIC:
                return AnthropicProvider()
            case _:
                return OpenAIChatProvider()

    def _validate_config(self, agent_name: str) -> None:
        """验证 LLM 配置是否完整。"""
        if not self.model or not str(self.model).strip():
            raise LLMConfigError(f"{agent_name} 未配置模型 ID，请设置对应的 *_MODEL")
        if not self.api_key or not str(self.api_key).strip():
            raise LLMConfigError(f"{agent_name} 未配置 API Key，请设置对应的 *_API_KEY")

    async def chat(
        self,
        history: list | None = None,
        tools: list | None = None,
        tool_choice: str | None = None,
        max_retries: int | None = None,
        retry_delay: float = 1.0,
        top_p: float | None = None,
        agent_name: str = "SystemAgent",
        sub_title: str | None = None,
    ) -> StandardResponse:
        """调用 LLM 进行对话。

        Args:
            history: 对话历史。
            tools: 可用工具列表。
            tool_choice: 工具选择策略。
            max_retries: 最大重试次数。
            retry_delay: 重试延迟（秒）。
            top_p: 采样参数。
            agent_name: Agent 名称。
            sub_title: 子任务标题。

        Returns:
            标准化响应对象。
        """
        self._validate_config(agent_name)

        messages = history or []
        attempt = 0
        max_attempts = max_retries or 3

        while attempt < max_attempts:
            try:
                response = await self.provider.call(
                    messages=messages,
                    model=self.model,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    tools=tools,
                    tool_choice=tool_choice,
                    max_tokens=self.max_tokens,
                    top_p=top_p,
                )
                self.chat_count += 1
                logger.info(
                    f"{agent_name} API 调用成功: content={response.content!r}, "
                    f"tool_calls={len(response.tool_calls)}"
                )
                return response

            except Exception as e:
                attempt += 1
                logger.warning(
                    f"{agent_name} API 调用失败 (尝试 {attempt}/{max_attempts}): {e}"
                )
                if attempt >= max_attempts:
                    raise
                import asyncio
                await asyncio.sleep(retry_delay * attempt)

        raise RuntimeError(f"{agent_name} API 调用重试次数耗尽")


async def simple_chat(model: LLM, history: list) -> str:
    """执行一次简单的对话，返回响应文本。

    Args:
        model: LLM 实例。
        history: 对话历史。

    Returns:
        模型响应文本。
    """
    response = await model.chat(history=history)
    return response.content or ""
