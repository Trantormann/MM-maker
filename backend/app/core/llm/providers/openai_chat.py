"""OpenAI Chat Completions Provider。"""

import openai

from app.core.llm.providers.base import BaseProvider
from app.core.llm.types import StandardResponse, ToolCall, Usage


def _prune_unanswered_tool_calls(messages: list, unanswered_ids: set) -> None:
    """从消息列表末尾的 assistant 消息中移除未被回应的 tool_calls。"""
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            remaining = [
                tc for tc in msg["tool_calls"] if tc.get("id") not in unanswered_ids
            ]
            if remaining:
                msg["tool_calls"] = remaining
            else:
                msg.pop("tool_calls", None)
            return


def _sanitize_messages(messages: list) -> list:
    """修复消息列表中的工具调用配对，避免 OpenAI 400 错误。

    确保每条含 tool_calls 的 assistant 消息后都紧跟对应的 tool 消息回应，
    移除孤立的 tool 消息和未被回应的 tool_calls。
    """
    result: list = []
    pending_ids: set = set()

    for msg in messages:
        role = msg.get("role")

        if role == "tool":
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id and tool_call_id in pending_ids:
                result.append(msg)
                pending_ids.discard(tool_call_id)
            # 孤立的 tool 消息（无对应 assistant tool_calls），直接丢弃
            continue

        # 遇到新的非 tool 消息时，清理上一个 assistant 中未被回应的 tool_calls
        if pending_ids:
            _prune_unanswered_tool_calls(result, pending_ids)
            pending_ids = set()

        result.append(msg)

        if role == "assistant" and msg.get("tool_calls"):
            pending_ids = {
                tc.get("id") for tc in msg["tool_calls"] if tc.get("id")
            }

    # 收尾：清理末尾仍未被回应的 tool_calls
    if pending_ids:
        _prune_unanswered_tool_calls(result, pending_ids)

    return result


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

        messages = _sanitize_messages(messages)

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
