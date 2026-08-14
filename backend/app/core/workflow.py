"""工作流模块，编排多 Agent 协作完成数学建模任务。"""

import asyncio
import json
import os

from app.config.setting import settings
from app.core.agents import (
    CoderAgent,
    CoordinatorAgent,
    ModelerAgent,
    ReviewerAgent,
    WriterAgent,
)
from app.core.flows import Flows
from app.core.llm.llm_factory import LLMFactory
from app.models.user_output import UserOutput
from app.schemas.A2A import HILCheckpoint, ModelerToCoder
from app.schemas.enums import HILAction
from app.schemas.request import Problem
from app.schemas.response import SystemMessage, TaskStatusMessage, HILCheckpointMessage
from app.services.redis_manager import redis_manager
from app.tools.interpreter_factory import create_interpreter
from app.tools.notebook_serializer import NotebookSerializer
from app.tools.openalex_scholar import OpenAlexScholar
from app.utils.common_utils import create_work_dir, find_work_dir, get_config_template
from app.utils.log_util import logger


class WorkFlow:
    """工作流基类。"""

    def __init__(self):
        pass

    def execute(self) -> None:
        """执行工作流。"""
        pass


class MathModelWorkFlow(WorkFlow):
    """数学建模工作流，协调协调者、建模手、代码手、写作手和评审手完成完整建模任务。"""

    task_id: str
    work_dir: str
    ques_count: int = 0
    questions: dict[str, str | int] = {}
    cancel_event: asyncio.Event | None = None
    code_interpreter = None

    # HIL 相关
    hil_enabled: bool = True
    hil_checkpoints: dict = {}
    pending_checkpoint: HILCheckpoint | None = None
    checkpoint_event: asyncio.Event | None = None

    # 反馈循环
    feedback_enabled: bool = True
    feedback_iteration: int = 0
    max_feedback_iterations: int = 3

    def _checkpoint_path(self) -> str:
        """获取 checkpoint 文件路径。"""
        return os.path.join(self.work_dir, "checkpoint.json")

    def _save_checkpoint(self, data: dict) -> None:
        """保存断点续传 checkpoint。"""
        try:
            with open(self._checkpoint_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 checkpoint 失败: {e}")

    def _load_checkpoint(self) -> dict | None:
        """读取断点续传 checkpoint，不存在或损坏时返回 None。"""
        path = self._checkpoint_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取 checkpoint 失败: {e}")
            return None

    async def _check_cancelled(self) -> None:
        """检查是否收到取消信号，若已取消则发布通知并抛出 CancelledError。"""
        if self.cancel_event and self.cancel_event.is_set():
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="任务已停止", type="warning"),
            )
            raise asyncio.CancelledError("任务被用户停止")

    async def _publish_status(self, status: str, progress: float, stage: str, message: str):
        """发布任务状态，并持久化到 Redis 供查询。"""
        status_msg = TaskStatusMessage(
            task_id=self.task_id,
            status=status,
            progress=progress,
            current_stage=stage,
            message=message,
        )
        await redis_manager.publish_message(self.task_id, status_msg)
        try:
            await redis_manager.set_task_status(
                self.task_id,
                {
                    "task_id": self.task_id,
                    "status": status,
                    "progress": progress,
                    "current_stage": stage,
                    "message": message,
                },
            )
        except Exception as e:
            logger.warning(f"任务状态持久化失败: {e}")

    async def _wait_hil_decision(self, checkpoint: HILCheckpoint) -> HILCheckpoint:
        """等待 HIL 用户决策。

        Args:
            checkpoint: 检查点数据。

        Returns:
            用户决策后的检查点数据。
        """
        if not self.hil_enabled:
            checkpoint.action = HILAction.CONFIRM
            return checkpoint

        self.pending_checkpoint = checkpoint
        self.checkpoint_event = asyncio.Event()

        # 发布检查点消息（携带 checkpoint_id 和 stage，供前端弹出决策 UI）
        await redis_manager.publish_message(
            self.task_id,
            HILCheckpointMessage(
                checkpoint_id=checkpoint.checkpoint_id,
                stage=checkpoint.stage,
                content=checkpoint.content,
                timeout=settings.HIL_TIMEOUT,
            ),
        )
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(
                content=f"HIL 检查点: {checkpoint.stage}，等待用户决策...",
                type="info",
            ),
        )

        # 等待用户决策（带超时）
        try:
            await asyncio.wait_for(
                self.checkpoint_event.wait(),
                timeout=settings.HIL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(f"HIL 检查点 {checkpoint.checkpoint_id} 超时，自动确认")
            checkpoint.action = HILAction.CONFIRM

        self.pending_checkpoint = None
        return checkpoint

    async def submit_hil_decision(
        self, checkpoint_id: str, action: str, feedback: str | None = None, edited_content: dict | None = None
    ) -> None:
        """提交 HIL 用户决策。

        Args:
            checkpoint_id: 检查点 ID。
            action: 用户决策动作。
            feedback: 用户反馈。
            edited_content: 编辑后的内容。
        """
        if self.pending_checkpoint and self.pending_checkpoint.checkpoint_id == checkpoint_id:
            self.pending_checkpoint.action = action
            self.pending_checkpoint.feedback = feedback
            if edited_content:
                self.pending_checkpoint.content = edited_content
            if self.checkpoint_event:
                self.checkpoint_event.set()

    async def execute(self, problem: Problem):
        """执行数学建模工作流。

        Args:
            problem: 包含题目信息、模板配置等的 Problem 对象。
        """
        self.task_id = problem.task_id
        # 优先复用已有工作目录（断点续传场景），否则创建新目录
        existing_dir = find_work_dir(self.task_id)
        if existing_dir is not None:
            self.work_dir = existing_dir
            logger.info(f"复用已有工作目录: {self.work_dir}")
        else:
            self.work_dir = create_work_dir(self.task_id)
        self.ques_all = problem.ques_all
        self.hil_enabled = settings.HIL_ENABLED
        self.hil_checkpoints = settings.HIL_CHECKPOINTS
        self.feedback_enabled = settings.FEEDBACK_ENABLED
        self.max_feedback_iterations = settings.FEEDBACK_MAX_ITERATIONS

        # 预校验配置
        missing = []
        for name, model_val, key_val in [
            ("Coordinator", settings.COORDINATOR_MODEL, settings.COORDINATOR_API_KEY),
            ("Modeler", settings.MODELER_MODEL, settings.MODELER_API_KEY),
            ("Coder", settings.CODER_MODEL, settings.CODER_API_KEY),
            ("Writer", settings.WRITER_MODEL, settings.WRITER_API_KEY),
            ("Reviewer", settings.REVIEWER_MODEL, settings.REVIEWER_API_KEY),
        ]:
            if not model_val or not str(model_val).strip():
                missing.append(f"{name} 模型 ID")
            if not key_val or not str(key_val).strip():
                missing.append(f"{name} API Key")
        if missing:
            raise ValueError(f"以下配置缺失，请先在设置中填写并保存：{', '.join(missing)}")

        llm_factory = LLMFactory(self.task_id)
        coordinator_llm, modeler_llm, coder_llm, writer_llm, reviewer_llm = llm_factory.get_all_llms()

        # 初始化 Agent
        coordinator_agent = CoordinatorAgent(
            self.task_id, coordinator_llm,
            context_window=settings.COORDINATOR_CONTEXT_WINDOW,
            cancel_event=self.cancel_event,
        )

        modeler_agent = ModelerAgent(
            self.task_id, modeler_llm,
            context_window=settings.MODELER_CONTEXT_WINDOW,
            cancel_event=self.cancel_event,
        )

        reviewer_agent = ReviewerAgent(
            self.task_id, reviewer_llm,
            context_window=settings.REVIEWER_CONTEXT_WINDOW,
            cancel_event=self.cancel_event,
        )

        await self._publish_status("running", 5, "init", "初始化完成")

        # ========== 断点续传：尝试加载 checkpoint ==========
        checkpoint = self._load_checkpoint()
        restored = False
        if checkpoint and checkpoint.get("questions") and checkpoint.get("modeler_solution"):
            logger.info(f"检测到 checkpoint，从断点恢复任务 {self.task_id}")
            restored = True
            self.questions = checkpoint["questions"]
            self.ques_count = checkpoint.get("ques_count", 0)
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(
                    content=f"检测到未完成任务，从断点恢复（已完成 {len(checkpoint.get('completed_flows', []))} 个子问题）...",
                    type="warning",
                ),
            )
            await self._publish_status("running", 20, "modeler", "从断点恢复建模方案")

        # ========== 阶段 1: 问题拆解 ==========
        if not restored:
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="阶段 1/6：协调者正在分析题目、拆解子问题..."),
            )
            await self._check_cancelled()

            try:
                coordinator_response = await coordinator_agent.run(problem.ques_all)
                self.questions = coordinator_response.questions
                self.ques_count = coordinator_response.ques_count
            except Exception as e:
                logger.error(f"CoordinatorAgent 执行失败: {e}")
                raise

            await self._publish_status("running", 10, "coordinator", f"问题拆解完成，共 {self.ques_count} 个子问题")

            # HIL 检查点：问题拆解确认
            if self.hil_checkpoints.get("problem_split", False):
                checkpoint = HILCheckpoint(
                    checkpoint_id=f"{self.task_id}_problem_split",
                    stage="problem_split",
                    content={"questions": self.questions, "ques_count": self.ques_count},
                )
                checkpoint = await self._wait_hil_decision(checkpoint)
                if checkpoint.action == HILAction.ABORT:
                    raise asyncio.CancelledError("用户中止任务")
                if checkpoint.action == HILAction.EDIT and checkpoint.content:
                    self.questions = checkpoint.content.get("questions", self.questions)
                    self.ques_count = checkpoint.content.get("ques_count", self.ques_count)

        # ========== 阶段 2: 建模设计 ==========
        if not restored:
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="阶段 2/6：建模手正在设计建模方案..."),
            )
            await self._check_cancelled()

            modeler_response = await modeler_agent.run(coordinator_response)

            await self._publish_status("running", 20, "modeler", "建模方案设计完成")

            # HIL 检查点：模型选择确认
            if self.hil_checkpoints.get("model_selection", False):
                checkpoint = HILCheckpoint(
                    checkpoint_id=f"{self.task_id}_model_selection",
                    stage="model_selection",
                    content={"solutions": modeler_response.questions_solution},
                )
                checkpoint = await self._wait_hil_decision(checkpoint)
                if checkpoint.action == HILAction.ABORT:
                    raise asyncio.CancelledError("用户中止任务")
                if checkpoint.action == HILAction.REGENERATE:
                    # 重新生成建模方案
                    modeler_response = await modeler_agent.run(coordinator_response)

            # 评审建模方案
            if self.feedback_enabled:
                review_result = await reviewer_agent.review_modeling(
                    self.questions, modeler_response.questions_solution
                )
                if review_result.needs_revision and self.feedback_iteration < self.max_feedback_iterations:
                    self.feedback_iteration += 1
                    logger.info(f"建模方案需要修改 (第{self.feedback_iteration}次反馈): {review_result.feedback}")
                    await redis_manager.publish_message(
                        self.task_id,
                        SystemMessage(
                            content=f"建模方案评审得分 {review_result.score}/10，正在根据反馈重新生成...",
                            type="warning",
                        ),
                    )
                    feedback_prompt = (
                        f"评审得分：{review_result.score}/10\n"
                        f"反馈：{review_result.feedback}\n"
                        f"改进建议：{'；'.join(review_result.suggestions)}"
                    )
                    modeler_response = await modeler_agent.run(
                        coordinator_response, feedback=feedback_prompt
                    )
        else:
            # 从 checkpoint 恢复建模方案
            modeler_response = ModelerToCoder(
                questions_solution=checkpoint["modeler_solution"]
            )

        # ========== 阶段 3: 初始化环境 ==========
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="阶段 3/6：正在创建代码沙盒环境..."),
        )

        if restored:
            user_output = UserOutput.from_dict(
                self.work_dir, checkpoint.get("user_output", {})
            )
        else:
            user_output = UserOutput(work_dir=self.work_dir, ques_count=self.ques_count)

        notebook_serializer = NotebookSerializer(work_dir=self.work_dir)
        self.code_interpreter = await create_interpreter(
            kind=settings.CODE_INTERPRETER_KIND,
            task_id=self.task_id,
            work_dir=self.work_dir,
            notebook_serializer=notebook_serializer,
            timeout=3000,
        )
        code_interpreter = self.code_interpreter

        # 断点恢复时，将已存在的图片设为基线，避免重复引用
        if restored:
            image_exts = (".png", ".jpg", ".jpeg", ".svg")
            existing_images: set[str] = set()
            for root, _, filenames in os.walk(self.work_dir):
                for f in filenames:
                    if f.lower().endswith(image_exts):
                        rel = os.path.relpath(os.path.join(root, f), self.work_dir).replace(os.sep, "/")
                        existing_images.add(rel)
            code_interpreter.set_image_baseline(existing_images)

        scholar = None
        if settings.OPENALEX_EMAIL:
            scholar = OpenAlexScholar(
                task_id=self.task_id,
                email=settings.OPENALEX_EMAIL,
                api_key=settings.OPENALEX_API_KEY,
            )

        coder_agent = CoderAgent(
            task_id=problem.task_id,
            model=coder_llm,
            work_dir=self.work_dir,
            max_chat_turns=settings.MAX_CHAT_TURNS,
            max_retries=settings.MAX_RETRIES,
            code_interpreter=code_interpreter,
            context_window=settings.CODER_CONTEXT_WINDOW,
            cancel_event=self.cancel_event,
        )

        writer_agent = WriterAgent(
            task_id=problem.task_id,
            model=writer_llm,
            comp_template=problem.comp_template,
            format_output=problem.format_output,
            scholar=scholar,
            context_window=settings.WRITER_CONTEXT_WINDOW,
            cancel_event=self.cancel_event,
        )

        flows = Flows(self.questions)
        config_template = get_config_template(problem.comp_template)

        await self._publish_status("running", 30, "solve", "环境初始化完成，开始求解")

        # ========== 阶段 4: 求解阶段 ==========
        solution_flows = flows.get_solution_flows(self.questions, modeler_response)
        total_steps = len(solution_flows)
        completed_flows: list[str] = checkpoint.get("completed_flows", []) if restored else []
        current_step = 0

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content=f"阶段 4/6：开始求解，共 {total_steps} 个子问题"),
        )

        for key, value in solution_flows.items():
            await self._check_cancelled()
            current_step += 1
            progress = 30 + (current_step / total_steps) * 40  # 30-70%

            # 断点恢复：跳过已完成的子问题
            if restored and key in completed_flows:
                await self._publish_status("running", progress, "solve", f"跳过已完成: {key}")
                continue

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"[{current_step}/{total_steps}] 代码手正在求解: {key}"),
            )

            coder_response = await coder_agent.run(
                prompt=value["coder_prompt"], subtask_title=key
            )

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"[{current_step}/{total_steps}] 代码求解成功: {key}", type="success"),
            )

            # 评审代码结果
            if self.feedback_enabled:
                code_review = await reviewer_agent.review_code_result(
                    key, coder_response.code_response or "", coder_response.created_images or []
                )
                if code_review.needs_revision:
                    logger.info(f"代码结果需要改进: {code_review.feedback}")

            # 写作手撰写对应章节
            writer_prompt = flows.get_writer_prompt(
                key,
                coder_response.code_response or "",
                coder_response.created_images or [],
                code_interpreter,
                config_template,
            )

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"[{current_step}/{total_steps}] 写作手正在撰写: {key}"),
            )

            writer_response = await writer_agent.run(
                writer_prompt,
                available_images=coder_response.created_images,
                sub_title=key,
            )

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"[{current_step}/{total_steps}] 章节完成: {key}", type="success"),
            )

            # 评审论文章节
            if self.feedback_enabled:
                paper_review = await reviewer_agent.review_paper(
                    key, writer_response.response_content, coder_response.created_images or []
                )
                if paper_review.needs_revision:
                    logger.info(f"论文章节需要改进: {paper_review.feedback}")

            user_output.set_res(key, writer_response)
            completed_flows.append(key)

            # 保存断点 checkpoint（每个子问题完成后）
            self._save_checkpoint({
                "questions": self.questions,
                "ques_count": self.ques_count,
                "ques_all": self.ques_all,
                "modeler_solution": modeler_response.questions_solution,
                "completed_flows": completed_flows,
                "user_output": user_output.to_dict(),
            })

            await self._publish_status("running", progress, "solve", f"完成: {key}")

        # 关闭沙盒
        await self.cleanup()
        logger.info(user_output.get_res())

        # ========== 阶段 5: 写作阶段 ==========
        # 断点恢复时优先使用 checkpoint 中保存的原始题目
        bg_ques_all = self.ques_all or problem.ques_all
        if restored and checkpoint.get("ques_all"):
            bg_ques_all = checkpoint["ques_all"]
        write_flows = flows.get_write_flows(
            user_output, config_template, bg_ques_all
        )
        total_write = len(write_flows)
        current_write = 0

        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content=f"阶段 5/6：开始整理论文，共 {total_write} 个章节"),
        )

        for key, value in write_flows.items():
            await self._check_cancelled()
            current_write += 1
            progress = 70 + (current_write / total_write) * 20  # 70-90%

            # 断点恢复：跳过已完成的章节
            if restored and key in user_output.res:
                await self._publish_status("running", progress, "write", f"跳过已完成: {key}")
                continue

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"[{current_write}/{total_write}] 写作手正在撰写: {key}"),
            )

            writer_response = await writer_agent.run(prompt=value, sub_title=key)
            user_output.set_res(key, writer_response)

            # 写作阶段也保存 checkpoint（幂等，覆盖写入）
            self._save_checkpoint({
                "questions": self.questions,
                "ques_count": self.ques_count,
                "ques_all": self.ques_all or problem.ques_all,
                "modeler_solution": modeler_response.questions_solution,
                "completed_flows": completed_flows,
                "user_output": user_output.to_dict(),
            })

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content=f"[{current_write}/{total_write}] 章节完成: {key}", type="success"),
            )
            await self._publish_status("running", progress, "write", f"完成: {key}")

        # ========== 阶段 6: 最终评审 ==========
        full_paper = user_output.get_result_to_save()

        if self.feedback_enabled:
            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(content="阶段 6/6：评审手正在进行最终评审..."),
            )

            final_review = await reviewer_agent.review_full_paper(full_paper)

            await redis_manager.publish_message(
                self.task_id,
                SystemMessage(
                    content=f"最终评审得分: {final_review.score}/10",
                    type="success" if final_review.score >= 7 else "warning",
                ),
            )

            # 如果评分不达标且还有迭代次数，可以触发重跑
            if (final_review.score < settings.FEEDBACK_SCORE_THRESHOLD
                    and self.feedback_iteration < self.max_feedback_iterations):
                logger.info(f"论文评分 {final_review.score} 低于阈值，建议重跑")

        # HIL 检查点：最终确认
        if self.hil_checkpoints.get("final_review", False):
            checkpoint = HILCheckpoint(
                checkpoint_id=f"{self.task_id}_final_review",
                stage="final_review",
                content={"paper_preview": full_paper[:2000], "score": final_review.score if self.feedback_enabled else None},
            )
            checkpoint = await self._wait_hil_decision(checkpoint)
            if checkpoint.action == HILAction.ABORT:
                raise asyncio.CancelledError("用户中止任务")

        # ========== 保存结果 ==========
        user_output.save_result()

        # 任务正常完成，清理 checkpoint，避免下次误恢复
        try:
            if os.path.exists(self._checkpoint_path()):
                os.remove(self._checkpoint_path())
        except Exception as e:
            logger.warning(f"清理 checkpoint 失败: {e}")

        await self._publish_status("completed", 100, "done", "任务完成")
        await redis_manager.publish_message(
            self.task_id,
            SystemMessage(content="数学建模任务全部完成！论文已生成。", type="success"),
        )

        logger.info(f"任务 {self.task_id} 完成，结果保存在 {self.work_dir}")

    async def cleanup(self) -> None:
        """清理工作流资源（代码解释器等），异常/取消时也会调用。"""
        if self.code_interpreter is not None:
            try:
                await self.code_interpreter.cleanup()
            except Exception as e:
                logger.warning(f"代码解释器清理失败: {e}")
            finally:
                self.code_interpreter = None
