"""代码手 Agent 模块，负责生成和执行 Python 代码完成建模任务。"""

import asyncio
import json

from app.config.setting import ApiType, settings
from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import CODER_PROMPT, get_reflection_prompt
from app.core.functions import coder_tools, coder_tools_anthropic
from app.schemas.A2A import CoderToWriter
from app.schemas.response import InterpreterMessage, SystemMessage
from app.services.redis_manager import redis_manager
from app.tools.base_interpreter import BaseCodeInterpreter
from app.utils.common_utils import get_current_files
from app.utils.log_util import logger


class CoderAgent(Agent):
    """代码手 Agent，通过 LLM 生成代码并在解释器中执行，支持错误反思和重试。"""

    def __init__(
        self,
        task_id: str,
        model: LLM,
        work_dir: str,
        max_chat_turns: int | None = settings.MAX_CHAT_TURNS,
        max_retries: int | None = settings.MAX_RETRIES,
        code_interpreter: BaseCodeInterpreter | None = None,
        context_window: int = 128000,
        cancel_event: asyncio.Event | None = None,
    ) -> None:
        super().__init__(task_id, model, context_window, cancel_event=cancel_event)
        self.work_dir = work_dir
        self.max_chat_turns = max_chat_turns
        self.current_chat_turns = 0
        self.max_retries = max_retries
        self.is_first_run = True
        self.system_prompt = CODER_PROMPT
        self.code_interpreter = code_interpreter

    async def run(self, prompt: str, subtask_title: str) -> CoderToWriter:
        """执行代码手子任务，生成并运行代码。

        Args:
            prompt: 子任务描述。
            subtask_title: 子任务标题，用于分段输出。

        Returns:
            CoderToWriter 对象，包含代码执行结果和生成的图片列表。
        """
        logger.info(f"{self.__class__.__name__}:开始:执行子任务: {subtask_title}")
        assert self.code_interpreter is not None, "code_interpreter 未初始化"
        self.code_interpreter.add_section(subtask_title)

        # 每个子任务独立计算对话轮次，避免前序子任务耗尽全局轮次预算
        self.current_chat_turns = 0

        # 根据 api_type 选择 tools 格式
        api_type = self.model.api_type
        tools = coder_tools_anthropic if api_type == ApiType.ANTHROPIC else coder_tools

        # 首次运行初始化
        if self.is_first_run:
            logger.info("首次运行，添加系统提示和数据集文件信息")
            self.is_first_run = False
            await self.append_chat_history(
                {"role": "system", "content": self.system_prompt}
            )
            await self.append_chat_history(
                {
                    "role": "user",
                    "content": f"当前文件夹下的数据集文件:\n{get_current_files(self.work_dir, 'data')}",
                }
            )

        await self.append_chat_history({"role": "user", "content": prompt})

        retry_count = 0
        last_error_message = ""

        while True:
            # 检查重试次数
            if self.max_retries is not None and retry_count >= self.max_retries:
                logger.error(f"超过最大尝试次数: {self.max_retries}")
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content="超过最大尝试次数", type="error"),
                )
                return CoderToWriter(
                    code_response=f"任务失败，超过最大尝试次数{self.max_retries}, 最后错误信息: {last_error_message}",
                    created_images=[],
                )

            # 检查对话轮次
            if self.max_chat_turns is not None and self.current_chat_turns >= self.max_chat_turns:
                logger.error(f"超过最大聊天次数: {self.max_chat_turns}")
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content="超过最大聊天次数", type="error"),
                )
                raise Exception(
                    f"Reached maximum number of chat turns ({self.max_chat_turns}). Task incomplete."
                )

            self.current_chat_turns += 1
            logger.info(f"当前对话轮次: {self.current_chat_turns}")

            try:
                response = await self._chat(
                    history=self.chat_history,
                    tools=tools,
                    tool_choice="auto",
                    agent_name=self.__class__.__name__,
                )

                # 处理工具调用
                if response.tool_calls:
                    # 只处理 execute_code 工具
                    tool_calls = [tc for tc in response.tool_calls if tc.name == "execute_code"]

                    # 更新对话历史：先写 assistant 消息（含 tool_calls）
                    assistant_msg: dict = {"role": "assistant", "content": response.content or ""}
                    if response.reasoning_content:
                        assistant_msg["reasoning_content"] = response.reasoning_content
                    if tool_calls:
                        assistant_msg["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {"name": tc.name, "arguments": tc.arguments},
                            }
                            for tc in tool_calls
                        ]
                    await self.append_chat_history(assistant_msg)

                    if not tool_calls:
                        # 模型返回了无法识别的工具调用，视为完成
                        logger.warning("响应包含未知工具调用，视为任务完成")
                        return CoderToWriter(
                            code_response=response.content,
                            created_images=await self.code_interpreter.get_created_images(
                                subtask_title
                            ),
                        )

                    # 依次执行每个工具调用，并为每个调用追加 tool 响应
                    error_occurred = False
                    for tool_call in tool_calls:
                        tool_id = tool_call.id
                        logger.info(f"调用工具: {tool_call.name}")

                        await redis_manager.publish_message(
                            self.task_id,
                            SystemMessage(content=f"代码手调用{tool_call.name}工具"),
                        )

                        try:
                            code = json.loads(tool_call.arguments)["code"]
                        except (json.JSONDecodeError, KeyError, TypeError) as e:
                            logger.warning(f"工具调用参数解析失败: {e}")
                            error_occurred = True
                            await self.append_chat_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_id,
                                    "name": "execute_code",
                                    "content": f"工具参数解析失败: {e}",
                                }
                            )
                            continue

                        await redis_manager.publish_message(
                            self.task_id,
                            InterpreterMessage(input={"code": code}),
                        )

                        # 执行代码
                        try:
                            (
                                text_to_gpt,
                                exec_error,
                                error_message,
                            ) = await self.code_interpreter.execute_code(code)
                        except Exception as e:
                            logger.error(f"代码解释器执行异常: {e}")
                            exec_error = True
                            text_to_gpt = ""
                            error_message = f"代码解释器执行异常: {e}"

                        # 无论成败都要追加 tool 响应，保证 tool_calls 配对完整
                        await self.append_chat_history(
                            {
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": "execute_code",
                                "content": error_message if exec_error else text_to_gpt,
                            }
                        )

                        if exec_error:
                            error_occurred = True
                            logger.warning(f"代码执行错误: {error_message}")
                            retry_count += 1
                            last_error_message = error_message
                            reflection_prompt = get_reflection_prompt(error_message, code)
                            await redis_manager.publish_message(
                                self.task_id,
                                SystemMessage(content="代码手反思纠正错误", type="error"),
                            )
                            await self.append_chat_history(
                                {"role": "user", "content": reflection_prompt}
                            )

                    continue
                else:
                    # 没有工具调用，任务完成
                    logger.info("没有工具调用，任务完成")
                    return CoderToWriter(
                        code_response=response.content,
                        created_images=await self.code_interpreter.get_created_images(
                            subtask_title
                        ),
                    )

            except Exception as e:
                logger.error(f"执行过程中发生异常: {str(e)}")
                retry_count += 1
                last_error_message = str(e)
                continue
