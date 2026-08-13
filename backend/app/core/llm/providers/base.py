"""LLM Provider 基类模块。"""

from abc import ABC, abstractmethod

from app.core.llm.types import StandardResponse


class BaseProvider(ABC):
    """LLM Provider 抽象基类。"""

    @abstractmethod
    async def call(
        self,
        messages: list,
        model: str,
        api_key: str,
        base_url: str | None = None,
        tools: list | None = None,
        tool_choice: str | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ) -> StandardResponse:
        """调用 LLM API。

        Args:
            messages: 消息列表。
            model: 模型 ID。
            api_key: API 密钥。
            base_url: 自定义 API 地址。
            tools: 工具列表。
            tool_choice: 工具选择策略。
            max_tokens: 最大 token 数。
            top_p: 采样参数。

        Returns:
            标准化响应对象。
        """
        ...
