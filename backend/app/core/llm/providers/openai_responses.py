"""OpenAI Responses API Provider。"""

import openai

from app.core.llm.providers.base import BaseProvider
from app.core.llm.types import StandardResponse, ToolCall, Usage


class OpenAIResponsesProvider(BaseProvider):
    """OpenAI Responses API Provider（支持 o1/o3 等推理模型）。"""

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
        """调用 OpenAI Responses API。"""
        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

        # 转换消息格式为 Responses API 格式
        input_messages = []
        for msg in messages:
            input_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        kwargs = {
            "model": model,
            "input": input_messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice
        if max_tokens:
            kwargs["max_output_tokens"] = max_tokens

        response = await client.responses.create(**kwargs)

        # 解析响应
        content = ""
        reasoning_content = ""
        tool_calls = []

        for output_item in response.output:
            if output_item.type == "message":
                for content_item in output_item.content:
                    if content_item.type == "output_text":
                        content += content_item.text
            elif output_item.type == "reasoning":
                for summary in output_item.summary:
                    reasoning_content += summary.text
            elif output_item.type == "function_call":
                tool_calls.append(
                    ToolCall(
                        id=output_item.call_id,
                        name=output_item.name,
                        arguments=output_item.arguments,
                    )
                )

        usage = Usage()
        if response.usage:
            usage = Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

        return StandardResponse(
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=tool_calls,
            usage=usage,
            raw=response,
        )
