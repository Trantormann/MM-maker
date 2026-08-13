"""Agent 基类模块，提供对话管理和记忆压缩功能。"""

import asyncio
from typing import Any

from app.core.llm.llm import LLM, simple_chat
from app.utils.log_util import logger

# 每个字符估算的 token 数（中英混合文本的保守估计）
_CHARS_PER_TOKEN = 3
# 触发压缩的 token 占比阈值（相对 context_window）
_DEFAULT_TOKEN_THRESHOLD_RATIO = 0.75


class Agent:
    """Agent 基类，管理对话历史、轮次控制和记忆压缩。"""

    def __init__(
        self,
        task_id: str,
        model: LLM,
        context_window: int = 128000,
        token_threshold_ratio: float = _DEFAULT_TOKEN_THRESHOLD_RATIO,
        cancel_event: asyncio.Event | None = None,
    ) -> None:
        self.task_id = task_id
        self.model = model
        self.chat_history: list[dict] = []
        self.context_window = context_window
        self.token_threshold_ratio = token_threshold_ratio
        self.current_token_count = 0
        self.cancel_event = cancel_event

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量。"""
        return max(1, len(text) // _CHARS_PER_TOKEN)

    def _estimate_message_tokens(self, msg: dict) -> int:
        """估算单条消息的 token 数（含结构开销）。"""
        content = msg.get("content") or ""
        return self._estimate_tokens(content) + 4

    async def _chat(self, **kwargs) -> Any:
        """调用 LLM 模型，支持取消中断。"""
        if not self.cancel_event:
            return await self.model.chat(**kwargs)

        chat_task = asyncio.create_task(self.model.chat(**kwargs))
        cancel_wait_task = asyncio.create_task(self.cancel_event.wait())
        done, pending = await asyncio.wait(
            {chat_task, cancel_wait_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if cancel_wait_task in done:
            chat_task.cancel()
            for p in pending:
                p.cancel()
            raise asyncio.CancelledError("任务被用户停止")
        return await chat_task

    async def run(self, prompt: str, system_prompt: str, sub_title: str) -> Any:
        """执行 Agent 对话并返回模型响应。

        Args:
            prompt: 用户输入的提示。
            system_prompt: 系统提示词。
            sub_title: 子任务标题。

        Returns:
            模型的响应文本。
        """
        try:
            logger.info(f"{self.__class__.__name__}:开始:执行对话")

            await self.append_chat_history({"role": "system", "content": system_prompt})
            await self.append_chat_history({"role": "user", "content": prompt})

            response = await self._chat(
                history=self.chat_history,
                agent_name=self.__class__.__name__,
                sub_title=sub_title,
            )

            response_content = response.content
            assistant_msg: dict = {"role": "assistant", "content": response_content}
            if response.reasoning_content:
                assistant_msg["reasoning_content"] = response.reasoning_content
            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": tc.arguments},
                    }
                    for tc in response.tool_calls
                ]
            self.chat_history.append(assistant_msg)

            if response.usage.prompt_tokens > 0:
                self.current_token_count = response.usage.prompt_tokens
            else:
                self.current_token_count += self._estimate_message_tokens(
                    {"content": response_content}
                )

            logger.info(f"{self.__class__.__name__}:完成:执行对话")
            return response_content
        except asyncio.CancelledError:
            logger.info(f"{self.__class__.__name__}:任务被用户停止")
            raise
        except Exception as e:
            error_msg = f"执行过程中遇到错误: {str(e)}"
            logger.error(f"Agent执行失败: {str(e)}")
            return error_msg

    async def append_chat_history(self, msg: dict) -> None:
        """向对话历史追加消息，并在必要时触发记忆压缩。"""
        self.chat_history.append(msg)
        self.current_token_count += self._estimate_message_tokens(msg)

        if msg.get("role") != "tool":
            await self.compress_if_needed()

    async def compress_if_needed(self) -> None:
        """当 token 数超过上下文窗口阈值时，使用 LLM 总结压缩历史。"""
        threshold = int(self.context_window * self.token_threshold_ratio)
        if self.current_token_count <= threshold:
            return

        logger.info(
            f"{self.__class__.__name__}:触发记忆压缩，"
            f"当前 token ~{self.current_token_count}，阈值 {threshold}"
        )

        try:
            system_msg = (
                self.chat_history[0]
                if self.chat_history and self.chat_history[0]["role"] == "system"
                else None
            )

            preserve_start_idx = self._find_safe_preserve_point()
            start_idx = 1 if system_msg else 0
            end_idx = preserve_start_idx

            if end_idx > start_idx:
                summarize_history = []
                if system_msg:
                    summarize_history.append(system_msg)

                summarize_history.append(
                    {
                        "role": "user",
                        "content": f"请简洁总结以下对话的关键内容和重要结论，保留重要的上下文信息：\n\n{self._format_history_for_summary(self.chat_history[start_idx:end_idx])}",
                    }
                )

                summary = await simple_chat(self.model, summarize_history)

                new_history = []
                if system_msg:
                    new_history.append(system_msg)

                new_history.append(
                    {"role": "assistant", "content": f"[历史对话总结] {summary}"}
                )
                new_history.extend(self.chat_history[preserve_start_idx:])

                self.chat_history = new_history
                self.current_token_count = sum(
                    self._estimate_message_tokens(m) for m in self.chat_history
                )

                logger.info(
                    f"{self.__class__.__name__}:记忆压缩完成，"
                    f"压缩后 token ~{self.current_token_count}"
                )
        except Exception as e:
            logger.error(f"记忆压缩失败: {e}")

    def _find_safe_preserve_point(self) -> int:
        """找到安全的保留起始点，确保不截断工具调用对。"""
        # 保留最后 6 条消息，确保上下文完整
        preserve_count = min(6, len(self.chat_history))
        idx = len(self.chat_history) - preserve_count

        # 确保不截断 tool 调用对
        while idx > 0 and self.chat_history[idx].get("role") == "tool":
            idx -= 1

        return max(1, idx)

    def _format_history_for_summary(self, messages: list[dict]) -> str:
        """格式化历史消息用于总结。"""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                lines.append(f"[{role}]: {content[:500]}")
        return "\n".join(lines)
