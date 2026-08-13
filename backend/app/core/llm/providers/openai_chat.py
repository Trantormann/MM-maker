"""OpenAI Chat Completions Provider。"""

import openai

from app.core.llm.providers.base import BaseProvider
from app.core.llm.types import StandardResponse, ToolCall, Usage


class OpenAIChatProvider(BaseProvider):
    """OpenAI Chat Completions API Provider。"""

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
        """调用 OpenAI Chat Completions API。"""
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        kwargs = {
            "model": model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if top_p is not None:
            kwargs["top_p"] = top_p

        response = await client.chat.completions.create(**kwargs)

        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        usage = Usage()
        if response.usage:
            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        return StandardResponse(
            content=message.content,
            tool_calls=tool_calls,
            usage=usage,
            raw=response,
        )
