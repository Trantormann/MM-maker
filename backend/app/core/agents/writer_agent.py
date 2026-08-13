"""写作手 Agent 模块，负责基于建模结果撰写学术论文。"""

import asyncio
import json

from app.config.setting import ApiType
from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import get_writer_prompt
from app.core.functions import writer_tools, writer_tools_anthropic
from app.schemas.A2A import WriterResponse
from app.schemas.enums import CompTemplate, FormatOutPut
from app.schemas.response import SystemMessage, WriterMessage
from app.services.redis_manager import redis_manager
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.log_util import logger


class WriterAgent(Agent):
    """写作手 Agent，基于建模和代码执行结果撰写竞赛论文。"""

    def __init__(
        self,
        task_id: str,
        model: LLM,
        comp_template: CompTemplate = CompTemplate.CHINA,
        format_output: FormatOutPut = FormatOutPut.Markdown,
        scholar: OpenAlexScholar | None = None,
        context_window: int = 128000,
        cancel_event: asyncio.Event | None = None,
    ) -> None:
        super().__init__(task_id, model, context_window, cancel_event=cancel_event)
        self.format_out_put = format_output
        self.comp_template = comp_template
        self.scholar = scholar
        self.is_first_run = True
        self.system_prompt = get_writer_prompt(format_output)
        self.available_images: list[str] = []

    async def run(
        self,
        prompt: str,
        available_images: list[str] | None = None,
        sub_title: str | None = None,
    ) -> WriterResponse:
        """执行写作任务。

        Args:
            prompt: 写作提示。
            available_images: 可用的图片相对路径列表。
            sub_title: 子任务标题。

        Returns:
            WriterResponse 对象，包含论文内容和脚注。
        """
        logger.info(f"WriterAgent 开始写作: {sub_title}")

        api_type = self.model.api_type
        tools = writer_tools_anthropic if api_type == ApiType.ANTHROPIC else writer_tools

        if self.is_first_run:
            self.is_first_run = False
            await self.append_chat_history(
                {"role": "system", "content": self.system_prompt}
            )

        if available_images:
            self.available_images = available_images
            image_lines = "\n".join(
                [f"- ![{img}]({img})" for img in available_images]
            )
            image_prompt = (
                f"\n\n【必须插入的图片列表】\n"
                f"以下图片是代码手生成的，你必须在论文相关段落后用 Markdown 格式逐一插入：\n"
                f"{image_lines}\n"
                f"插入格式为独占一行的 ![描述](文件名)，每张图片后需配3行以上的分析解读。\n"
            )
            prompt = prompt + image_prompt

        await self.append_chat_history({"role": "user", "content": prompt})

        response = await self._chat(
            history=self.chat_history,
            tools=tools,
            tool_choice="auto",
            agent_name=self.__class__.__name__,
            sub_title=sub_title,
        )

        footnotes = []
        response_content: str = ""

        if response.tool_calls:
            # 只处理 search_papers 工具调用
            tool_calls = [tc for tc in response.tool_calls if tc.name == "search_papers"]

            if tool_calls:
                tool_call = tool_calls[0]
                tool_id = tool_call.id

                # 先写 assistant 消息（含 tool_calls），保证配对完整
                assistant_msg: dict = {"role": "assistant", "content": response.content}
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

                logger.info("调用工具: search_papers")
                await redis_manager.publish_message(
                    self.task_id,
                    SystemMessage(content="写作手调用search_papers工具"),
                )

                try:
                    query = json.loads(tool_call.arguments)["query"]
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.error(f"工具调用参数解析失败: {e}")
                    await self.append_chat_history(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": "search_papers",
                            "content": f"工具参数解析失败: {e}",
                        }
                    )
                    return WriterResponse(
                        response_content=f"文献检索失败: {e}", footnotes=footnotes
                    )

                await redis_manager.publish_message(
                    self.task_id,
                    WriterMessage(content=query),
                )

                try:
                    assert self.scholar is not None, "scholar 未初始化"
                    papers = await self.scholar.search_papers(query)
                except Exception as e:
                    error_msg = f"搜索文献失败: {str(e)}"
                    logger.error(error_msg)
                    # 无论成败都追加 tool 响应，保证配对完整
                    await self.append_chat_history(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": "search_papers",
                            "content": error_msg,
                        }
                    )
                    return WriterResponse(
                        response_content=error_msg, footnotes=footnotes
                    )

                papers_str = self.scholar.papers_to_str(papers)
                await self.append_chat_history(
                    {
                        "role": "tool",
                        "content": papers_str,
                        "tool_call_id": tool_id,
                        "name": "search_papers",
                    }
                )
                next_response = await self._chat(
                    history=self.chat_history,
                    tools=tools,
                    tool_choice="auto",
                    agent_name=self.__class__.__name__,
                    sub_title=sub_title,
                )
                response_content = next_response.content or ""
            else:
                # 模型返回了未知工具调用，直接使用响应文本
                response_content = response.content or ""
        else:
            response_content = response.content or ""

        self.chat_history.append(
            {"role": "assistant", "content": response_content}
        )
        logger.info(f"WriterAgent 完成写作: {sub_title}")
        return WriterResponse(response_content=response_content, footnotes=footnotes)

    async def summarize(self) -> str:
        """总结对话内容，生成任务执行摘要。"""
        try:
            await self.append_chat_history(
                {"role": "user", "content": "请简单总结以上完成什么任务取得什么结果:"}
            )
            response = await self._chat(
                history=self.chat_history, agent_name=self.__class__.__name__
            )
            response_content = response.content or ""
            summary_msg: dict = {"role": "assistant", "content": response_content}
            if response.reasoning_content:
                summary_msg["reasoning_content"] = response.reasoning_content
            await self.append_chat_history(summary_msg)
            return response_content
        except Exception as e:
            logger.error(f"总结生成失败: {str(e)}")
            return "由于网络原因无法生成详细总结，但已完成主要任务处理。"
