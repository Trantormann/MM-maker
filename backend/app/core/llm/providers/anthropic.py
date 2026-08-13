"""Anthropic Provider。"""

import anthropic

from app.core.llm.providers.base import BaseProvider
from app.core.llm.types import StandardResponse, ToolCall, Usage


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API Provider。"""

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
        """调用 Anthropic Messages API。"""
        client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )

        # 分离 system 消息
        system_msg = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens or 4096,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = {"type": tool_choice}
        if top_p is not None:
            kwargs["top_p"] = top_p

        response = await client.messages.create(**kwargs)

        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=str(block.input),
                    )
                )

        usage = Usage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
        )

        return StandardResponse(
            content=content,
            tool_calls=tool_calls,
            usage=usage,
            raw=response,
        )
