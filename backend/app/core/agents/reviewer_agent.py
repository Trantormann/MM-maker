"""评审手 Agent 模块，负责对建模结果和论文进行质量评审。"""

import asyncio
import json

from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import REVIEWER_PROMPT
from app.schemas.A2A import ReviewResult
from app.schemas.response import ReviewerMessage, SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.log_util import logger

MAX_JSON_RETRIES = 3


class ReviewerAgent(Agent):
    """评审手 Agent，对建模方案、代码结果和论文质量进行评审，提供反馈和改进建议。"""

    def __init__(
        self,
        task_id: str,
        model: LLM,
        context_window: int = 128000,
        cancel_event: asyncio.Event | None = None,
    ) -> None:
        super().__init__(task_id, model, context_window, cancel_event=cancel_event)
        self.system_prompt = REVIEWER_PROMPT
        self.is_first_run = True

    async def review_modeling(
        self,
        questions: dict,
        solutions: dict[str, str],
    ) -> ReviewResult:
        """评审建模方案。

        Args:
            questions: 拆解后的问题。
            solutions: 建模方案。

        Returns:
            ReviewResult 评审结果。
        """
        prompt = f"""
请评审以下建模方案：

## 问题
{json.dumps(questions, ensure_ascii=False, indent=2)}

## 建模方案
{json.dumps(solutions, ensure_ascii=False, indent=2)}

请从以下维度评分（0-10）并给出反馈：
1. 模型选择合理性
2. 方案完整性
3. 创新性
4. 可行性
5. 可视化方案质量
"""
        return await self._do_review(prompt, "modeling")

    async def review_code_result(
        self,
        subtask: str,
        code_response: str,
        created_images: list[str],
    ) -> ReviewResult:
        """评审代码执行结果。

        Args:
            subtask: 子任务名称。
            code_response: 代码执行结果。
            created_images: 生成的图片列表。

        Returns:
            ReviewResult 评审结果。
        """
        prompt = f"""
请评审以下代码执行结果：

## 子任务
{subtask}

## 执行结果
{code_response}

## 生成的图片
{json.dumps(created_images, ensure_ascii=False)}

请从以下维度评分（0-10）并给出反馈：
1. 结果正确性
2. 结果完整性
3. 可视化质量
4. 数据特征描述充分性
"""
        return await self._do_review(prompt, "code_result")

    async def review_paper(
        self,
        section: str,
        content: str,
        available_images: list[str],
    ) -> ReviewResult:
        """评审论文章节。

        Args:
            section: 章节名称。
            content: 论文内容。
            available_images: 可用图片列表。

        Returns:
            ReviewResult 评审结果。
        """
        prompt = f"""
请评审以下论文章节：

## 章节
{section}

## 内容
{content}

## 可用图片
{json.dumps(available_images, ensure_ascii=False)}

请从以下维度评分（0-10）并给出反馈：
1. 内容完整性
2. 逻辑清晰性
3. 学术规范性
4. 图表引用正确性
5. 语言表达质量
"""
        return await self._do_review(prompt, "paper")

    async def review_full_paper(self, full_paper: str) -> ReviewResult:
        """评审完整论文。

        Args:
            full_paper: 完整论文内容。

        Returns:
            ReviewResult 评审结果。
        """
        prompt = f"""
请评审以下完整论文：

{full_paper}

请从以下维度评分（0-10）并给出反馈：
1. 摘要质量（是否完整概述问题、方法、结果、结论）
2. 结构完整性（各章节是否齐全）
3. 模型合理性（假设有依据、参数有来源）
4. 结果可信度（误差分析、交叉验证）
5. 写作规范性（段落式写作、图表分析充分）
6. 创新性（模型适配性、方法创新）
7. 整体印象（是否达到国奖水平）
"""
        return await self._do_review(prompt, "full_paper")

    async def _do_review(self, prompt: str, review_type: str) -> ReviewResult:
        """执行评审并解析结果。

        Args:
            prompt: 评审提示。
            review_type: 评审类型。

        Returns:
            ReviewResult 评审结果。
        """
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content=f"评审手开始评审: {review_type}"),
        )

        # system 提示只写入一次，避免重复评审时堆积
        if self.is_first_run:
            self.is_first_run = False
            await self.append_chat_history(
                {"role": "system", "content": self.system_prompt}
            )
        await self.append_chat_history({"role": "user", "content": prompt})

        attempt = 0
        while attempt < MAX_JSON_RETRIES:
            try:
                response = await self._chat(
                    history=self.chat_history,
                    agent_name=self.__class__.__name__,
                )

                json_str = response.content or ""
                json_str = json_str.replace("```json", "").replace("```", "").strip()

                result_data = json.loads(json_str)

                result = ReviewResult(
                    score=result_data.get("score", 5.0),
                    dimension_scores=result_data.get("dimension_scores", {}),
                    feedback=result_data.get("feedback", ""),
                    suggestions=result_data.get("suggestions", []),
                    needs_revision=result_data.get("needs_revision", True),
                    revision_areas=result_data.get("revision_areas", []),
                )

                await redis_manager.publish_message(
                    self.task_id,
                    ReviewerMessage(
                        content=f"评审完成: {review_type}, 得分: {result.score}",
                        score=result.score,
                    ),
                )

                return result

            except (json.JSONDecodeError, KeyError) as e:
                attempt += 1
                logger.warning(
                    f"ReviewerAgent JSON 解析失败 (尝试 {attempt}/{MAX_JSON_RETRIES}): {e}"
                )
                # 将错误的输出作为 assistant 消息追加，保证对话上下文连贯
                await self.append_chat_history(
                    {"role": "assistant", "content": json_str}
                )
                await self.append_chat_history(
                    {
                        "role": "user",
                        "content": "请严格按照JSON格式输出评审结果，包含 score, dimension_scores, feedback, suggestions, needs_revision, revision_areas 字段。",
                    }
                )

        # 解析失败，返回默认结果
        logger.error("ReviewerAgent JSON 解析重试次数耗尽，返回默认评审结果")
        return ReviewResult(
            score=5.0,
            dimension_scores={},
            feedback="评审结果解析失败，请人工检查",
            suggestions=["请人工评审"],
            needs_revision=True,
            revision_areas=["全部"],
        )
