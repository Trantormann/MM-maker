"""建模任务路由模块，提供任务创建、API 验证和配置管理等接口。"""

import asyncio
import os
from typing import Dict, Tuple

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.config.setting import ApiType, settings
from app.core.workflow import MathModelWorkFlow
from app.schemas.enums import CompTemplate, FormatOutPut
from app.schemas.request import HILDecisionRequest, Problem
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.common_utils import create_task_id, create_work_dir, find_work_dir, get_current_files, md_2_docx
from app.utils.log_util import logger

router = APIRouter()

# 任务注册表: task_id -> (asyncio.Task, asyncio.Event, MathModelWorkFlow)
_active_tasks: Dict[str, Tuple[asyncio.Task, asyncio.Event, MathModelWorkFlow]] = {}


class ValidateApiKeyRequest(BaseModel):
    """API Key 验证请求。"""

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_id: str
    api_type: str = "openai-chat"


class ValidateApiKeyResponse(BaseModel):
    """API Key 验证响应。"""

    valid: bool
    message: str


class SaveApiConfigRequest(BaseModel):
    """保存 API 配置请求。"""

    coordinator: dict
    modeler: dict
    coder: dict
    writer: dict
    reviewer: dict
    openalex_email: str


def _parse_api_type(value) -> ApiType | None:
    """将前端传入的字符串安全转换为 ApiType 枚举。"""
    if not value:
        return None
    if isinstance(value, ApiType):
        return value
    try:
        return ApiType(str(value))
    except ValueError:
        return None


def _persist_env_updates(updates: dict[str, str]) -> None:
    """将配置写回 .env.dev 文件，保留原有注释和未涉及的键。

    已存在的键原地更新，不存在的键追加到文件末尾。
    使用 UTF-8（无 BOM）写入，与 pydantic-settings 的读取编码一致。
    """
    env_path = "backend/.env.dev"
    if not os.path.exists(env_path):
        env_path = ".env.dev"
    if not os.path.exists(env_path):
        logger.warning("未找到 .env.dev，跳过配置持久化")
        return

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    seen: set[str] = set()
    updated_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            updated_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            updated_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            updated_lines.append(line)

    # 追加未出现在文件中的键
    for key, value in updates.items():
        if key not in seen:
            updated_lines.append(f"{key}={value}")

    with open(env_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(updated_lines) + "\n")
    logger.info(f"配置已持久化到 {env_path}")


@router.post("/save-api-config")
async def save_api_config(request: SaveApiConfigRequest):
    """保存验证成功的 API 配置到 settings，并持久化到 .env.dev。"""
    try:
        updates: dict[str, str] = {}

        def _apply(prefix: str, config: dict) -> None:
            """将单个 Agent 的配置写入 settings 并收集持久化项。"""
            if not config:
                return
            key_map = {
                "apiKey": f"{prefix}_API_KEY",
                "modelId": f"{prefix}_MODEL",
                "baseUrl": f"{prefix}_BASE_URL",
                "apiType": f"{prefix}_API_TYPE",
                "contextWindow": f"{prefix}_CONTEXT_WINDOW",
            }
            for field, env_key in key_map.items():
                value = config.get(field)
                if value in (None, ""):
                    continue
                if field == "apiType":
                    parsed = _parse_api_type(value)
                    if parsed is not None:
                        setattr(settings, env_key, parsed)
                        updates[env_key] = parsed.value
                elif field == "contextWindow":
                    int_val = int(value)
                    setattr(settings, env_key, int_val)
                    updates[env_key] = str(int_val)
                else:
                    setattr(settings, env_key, value)
                    updates[env_key] = value

        _apply("COORDINATOR", request.coordinator)
        _apply("MODELER", request.modeler)
        _apply("CODER", request.coder)
        _apply("WRITER", request.writer)
        _apply("REVIEWER", request.reviewer)

        if request.openalex_email:
            settings.OPENALEX_EMAIL = request.openalex_email
            updates["OPENALEX_EMAIL"] = request.openalex_email

        # 持久化到 .env.dev（失败不阻塞保存流程）
        try:
            _persist_env_updates(updates)
        except Exception as e:
            logger.error(f"配置持久化失败: {e}")

        return {"status": "success", "message": "配置保存成功"}
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-api-key", response_model=ValidateApiKeyResponse)
async def validate_api_key(request: ValidateApiKeyRequest):
    """验证 API Key 是否有效。"""
    try:
        import openai

        client = openai.OpenAI(
            api_key=request.api_key,
            base_url=request.base_url,
        )
        # 尝试列出模型来验证 API Key
        models = client.models.list()
        return ValidateApiKeyResponse(valid=True, message="API Key 验证成功")
    except Exception as e:
        return ValidateApiKeyResponse(valid=False, message=f"验证失败: {str(e)}")


def _launch_task(task_id: str, problem: Problem) -> dict:
    """在后台启动工作流任务，并注册到 _active_tasks。

    Args:
        task_id: 任务 ID。
        problem: Problem 对象。

    Returns:
        启动信息字典。
    """
    workflow = MathModelWorkFlow()
    cancel_event = asyncio.Event()
    workflow.cancel_event = cancel_event

    async def _run_and_finalize():
        """执行工作流并在结束后统一清理：记录状态、回收资源、移除注册表。"""
        try:
            await workflow.execute(problem)
        except asyncio.CancelledError:
            logger.info(f"任务 {task_id} 被取消")
            try:
                await redis_manager.set_task_status(
                    task_id,
                    {"task_id": task_id, "status": "cancelled", "progress": 0,
                     "current_stage": "cancelled", "message": "任务已取消"},
                )
            except Exception as e:
                logger.warning(f"取消状态持久化失败: {e}")
            raise
        except Exception as e:
            logger.error(f"任务 {task_id} 执行失败: {e}")
            try:
                await redis_manager.set_task_status(
                    task_id,
                    {"task_id": task_id, "status": "error", "progress": 0,
                     "current_stage": "error", "message": str(e)},
                )
                await redis_manager.publish_message(
                    task_id,
                    SystemMessage(content=f"任务执行失败: {e}", type="error"),
                )
            except Exception as pub_err:
                logger.warning(f"错误状态发布失败: {pub_err}")
        finally:
            try:
                await workflow.cleanup()
            finally:
                _active_tasks.pop(task_id, None)

    # 在后台执行任务
    task = asyncio.create_task(_run_and_finalize())
    _active_tasks[task_id] = (task, cancel_event, workflow)
    logger.info(f"任务 {task_id} 已启动")

    return {"task_id": task_id, "work_dir": workflow.work_dir, "message": "任务已启动"}


@router.post("/modeling")
async def start_modeling(
    background_tasks: BackgroundTasks,
    ques_all: str = Form(...),
    comp_template: str = Form("CHINA"),
    format_output: str = Form("Markdown"),
    files: list[UploadFile] = File(default=[]),
):
    """启动数学建模任务。

    Args:
        ques_all: 完整题目信息。
        comp_template: 竞赛模板。
        format_output: 输出格式。
        files: 上传的数据文件。

    Returns:
        任务 ID 和工作目录。
    """
    task_id = create_task_id()
    work_dir = create_work_dir(task_id)

    # 保存上传的文件
    data_dir = os.path.join(work_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    for file in files:
        if file.filename:
            file_path = os.path.join(data_dir, file.filename)
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

    # 创建 Problem 对象
    problem = Problem(
        task_id=task_id,
        ques_all=ques_all,
        comp_template=CompTemplate(comp_template),
        format_output=FormatOutPut(format_output),
    )

    return _launch_task(task_id, problem)


@router.post("/modeling/{task_id}/resume")
async def resume_modeling(task_id: str):
    """从中断点恢复未完成的任务。

    通过工作目录下的 checkpoint.json 恢复问题拆解、建模方案与
    已完成子问题的论文章节，跳过已完成部分继续执行。
    """
    if task_id in _active_tasks:
        raise HTTPException(status_code=409, detail="任务正在运行中")

    work_dir = find_work_dir(task_id)
    if work_dir is None:
        raise HTTPException(status_code=404, detail="任务工作目录不存在")

    checkpoint_path = os.path.join(work_dir, "checkpoint.json")
    if not os.path.exists(checkpoint_path):
        raise HTTPException(status_code=409, detail="任务无断点信息（可能已完成或未开始求解）")

    # 恢复时需从工作目录重建 Problem 上下文
    # 题目原文与模板信息无法从 checkpoint 完全还原，这里使用占位恢复，
    # 工作流会优先读取 checkpoint 中的 questions 和 modeler_solution。
    problem = Problem(
        task_id=task_id,
        ques_all="",
        comp_template=CompTemplate.CHINA,
        format_output=FormatOutPut.Markdown,
    )

    return _launch_task(task_id, problem)


@router.post("/modeling/{task_id}/cancel")
async def cancel_modeling(task_id: str):
    """取消建模任务。"""
    if task_id not in _active_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task, cancel_event, workflow = _active_tasks[task_id]
    cancel_event.set()
    task.cancel()

    # 立即释放代码解释器资源（内核/沙盒）
    try:
        await workflow.cleanup()
    except Exception as e:
        logger.warning(f"取消时清理资源失败: {e}")

    await redis_manager.publish_message(
        task_id,
        SystemMessage(content="任务已取消", type="warning"),
    )

    return {"status": "success", "message": "任务已取消"}


@router.post("/modeling/{task_id}/hil-decision")
async def submit_hil_decision(task_id: str, request: HILDecisionRequest):
    """提交 HIL 用户决策。"""
    if task_id not in _active_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    _, _, workflow = _active_tasks[task_id]
    await workflow.submit_hil_decision(
        checkpoint_id=request.checkpoint_id,
        action=request.action,
        feedback=request.feedback,
        edited_content=request.edited_content,
    )

    return {"status": "success", "message": "决策已提交"}


@router.get("/modeling/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态。"""
    status = await redis_manager.get_task_status(task_id)
    if status is None:
        if task_id in _active_tasks:
            task, _, _ = _active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "running" if not task.done() else "completed",
                "done": task.done(),
            }
        raise HTTPException(status_code=404, detail="任务不存在")
    return status


@router.get("/modeling/{task_id}/result")
async def get_task_result(task_id: str):
    """获取任务结果。"""
    # 查找工作目录
    work_dirs = []
    base_dir = "project/work_dir"
    if os.path.exists(base_dir):
        for d in os.listdir(base_dir):
            if task_id[:8] in d:
                work_dirs.append(os.path.join(base_dir, d))

    if not work_dirs:
        raise HTTPException(status_code=404, detail="结果不存在")

    work_dir = work_dirs[0]
    res_path = os.path.join(work_dir, "res.md")

    if not os.path.exists(res_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    with open(res_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {
        "task_id": task_id,
        "work_dir": work_dir,
        "content": content,
    }


@router.get("/modeling/{task_id}/download-docx")
async def download_docx(task_id: str):
    """下载 DOCX 格式的论文。"""
    work_dirs = []
    base_dir = "project/work_dir"
    if os.path.exists(base_dir):
        for d in os.listdir(base_dir):
            if task_id[:8] in d:
                work_dirs.append(os.path.join(base_dir, d))

    if not work_dirs:
        raise HTTPException(status_code=404, detail="结果不存在")

    work_dir = work_dirs[0]
    md_path = os.path.join(work_dir, "res.md")
    docx_path = os.path.join(work_dir, "res.docx")

    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="结果文件不存在")

    if not os.path.exists(docx_path):
        success = md_2_docx(md_path, docx_path)
        if not success:
            raise HTTPException(status_code=500, detail="DOCX 转换失败")

    from fastapi.responses import FileResponse
    return FileResponse(docx_path, filename=f"paper_{task_id[:8]}.docx")
