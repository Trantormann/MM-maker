"""建模任务路由模块，提供任务创建、API 验证和配置管理等接口。"""

import asyncio
import os
from typing import Dict, Tuple

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.config.setting import settings
from app.core.workflow import MathModelWorkFlow
from app.schemas.enums import CompTemplate, FormatOutPut
from app.schemas.request import HILDecisionRequest, Problem
from app.schemas.response import SystemMessage
from app.services.redis_manager import redis_manager
from app.utils.common_utils import create_task_id, create_work_dir, get_current_files, md_2_docx
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


@router.post("/save-api-config")
async def save_api_config(request: SaveApiConfigRequest):
    """保存验证成功的 API 配置到 settings。"""
    try:
        if request.coordinator:
            settings.COORDINATOR_API_KEY = request.coordinator.get("apiKey", "")
            settings.COORDINATOR_MODEL = request.coordinator.get("modelId", "")
            settings.COORDINATOR_BASE_URL = request.coordinator.get("baseUrl", "")
            if api_type := request.coordinator.get("apiType"):
                settings.COORDINATOR_API_TYPE = api_type
            if cw := request.coordinator.get("contextWindow"):
                settings.COORDINATOR_CONTEXT_WINDOW = int(cw)

        if request.modeler:
            settings.MODELER_API_KEY = request.modeler.get("apiKey", "")
            settings.MODELER_MODEL = request.modeler.get("modelId", "")
            settings.MODELER_BASE_URL = request.modeler.get("baseUrl", "")
            if api_type := request.modeler.get("apiType"):
                settings.MODELER_API_TYPE = api_type
            if cw := request.modeler.get("contextWindow"):
                settings.MODELER_CONTEXT_WINDOW = int(cw)

        if request.coder:
            settings.CODER_API_KEY = request.coder.get("apiKey", "")
            settings.CODER_MODEL = request.coder.get("modelId", "")
            settings.CODER_BASE_URL = request.coder.get("baseUrl", "")
            if api_type := request.coder.get("apiType"):
                settings.CODER_API_TYPE = api_type
            if cw := request.coder.get("contextWindow"):
                settings.CODER_CONTEXT_WINDOW = int(cw)

        if request.writer:
            settings.WRITER_API_KEY = request.writer.get("apiKey", "")
            settings.WRITER_MODEL = request.writer.get("modelId", "")
            settings.WRITER_BASE_URL = request.writer.get("baseUrl", "")
            if api_type := request.writer.get("apiType"):
                settings.WRITER_API_TYPE = api_type
            if cw := request.writer.get("contextWindow"):
                settings.WRITER_CONTEXT_WINDOW = int(cw)

        if request.reviewer:
            settings.REVIEWER_API_KEY = request.reviewer.get("apiKey", "")
            settings.REVIEWER_MODEL = request.reviewer.get("modelId", "")
            settings.REVIEWER_BASE_URL = request.reviewer.get("baseUrl", "")
            if api_type := request.reviewer.get("apiType"):
                settings.REVIEWER_API_TYPE = api_type
            if cw := request.reviewer.get("contextWindow"):
                settings.REVIEWER_CONTEXT_WINDOW = int(cw)

        if request.openalex_email:
            settings.OPENALEX_EMAIL = request.openalex_email

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

    # 创建工作流实例
    workflow = MathModelWorkFlow()
    cancel_event = asyncio.Event()
    workflow.cancel_event = cancel_event

    # 在后台执行任务
    task = asyncio.create_task(workflow.execute(problem))
    _active_tasks[task_id] = (task, cancel_event, workflow)

    logger.info(f"任务 {task_id} 已启动，工作目录: {work_dir}")

    return {
        "task_id": task_id,
        "work_dir": work_dir,
        "message": "任务已启动",
    }


@router.post("/modeling/{task_id}/cancel")
async def cancel_modeling(task_id: str):
    """取消建模任务。"""
    if task_id not in _active_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task, cancel_event, _ = _active_tasks[task_id]
    cancel_event.set()
    task.cancel()

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
