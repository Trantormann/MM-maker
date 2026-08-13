"""LLM 类型定义模块。"""

from typing import Any

from pydantic import BaseModel


class ToolCall(BaseModel):
    """工具调用。"""

    id: str
    name: str
    arguments: str


class Usage(BaseModel):
    """Token 使用量。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class StandardResponse(BaseModel):
    """标准化 LLM 响应。"""

    content: str | None = None
    reasoning_content: str | None = None
    tool_calls: list[ToolCall] = []
    usage: Usage = Usage()
    raw: Any = None
