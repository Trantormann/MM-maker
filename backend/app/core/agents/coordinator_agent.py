"""协调者 Agent 模块，负责识别用户意图并拆解数学建模问题。"""

import asyncio
import json
import re

from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import COORDINATOR_PROMPT
from app.schemas.A2A import CoordinatorToModeler
from app.utils.log_util import logger

MAX_JSON_RETRIES = 3


class CoordinatorAgent(Agent):
    """协调者 Agent，判断用户输入是否为数学建模问题并拆解为结构化问题列表。"""

    def __init__(
        self,
        task_id: str,
        model: LLM,
        context_window: int = 128000,
        cancel_event: asyncio.Event | None = None,
    ) -> None:
        super().__init__(task_id, model, context_window, cancel_event=cancel_event)
        self.system_prompt = COORDINATOR_PROMPT

    async def run(self, ques_all: str) -> CoordinatorToModeler:
        """解析用户输入的问题并格式化为结构化 JSON。

        Args:
            ques_all: 用户输入的完整题目信息。

        Returns:
            CoordinatorToModeler 对象，包含结构化问题和问题数量。

        Raises:
            ValueError: 非数学建模问题或 JSON 解析失败。
        """
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )
        await self.append_chat_history({"role": "user", "content": ques_all})

        attempt = 0
        last_error: Exception | None = None

        while attempt < MAX_JSON_RETRIES:
            try:
                response = await self._chat(
                    history=self.chat_history,
                    agent_name=self.__class__.__name__,
                )
                json_str = response.content or ""

                # 清理 JSON 字符串
                json_str = json_str.replace("```json", "").replace("```", "").strip()
                json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_str)

                if not json_str:
                    raise ValueError("返回的 JSON 字符串为空")

                # 检查是否为拒绝响应
                if "拒绝" in json_str or "不是数学建模" in json_str:
                    raise ValueError(f"非数学建模问题: {json_str[:200]}")

                questions = json.loads(json_str)
                ques_count = questions.get("ques_count", 0)

                if ques_count <= 0:
                    raise ValueError("未能识别出有效的问题数量")

                logger.info(f"CoordinatorAgent 拆解完成: {ques_count} 个问题")
                return CoordinatorToModeler(questions=questions, ques_count=ques_count)

            except (json.JSONDecodeError, ValueError, KeyError) as e:
                attempt += 1
                last_error = e
                logger.warning(
                    f"CoordinatorAgent 解析失败 (尝试 {attempt}/{MAX_JSON_RETRIES}): {e}"
                )

                error_prompt = f"⚠️ 上次响应格式错误: {str(e)}。请严格输出JSON格式"
                await self.append_chat_history({
                    "role": "system",
                    "content": self.system_prompt + "\n" + error_prompt,
                })

        raise last_error or ValueError("CoordinatorAgent JSON 解析重试次数耗尽")
