"""文件管理路由模块。"""

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/files/{task_id}/list")
async def list_files(task_id: str):
    """列出任务工作目录下的所有文件。"""
    base_dir = "project/work_dir"
    work_dirs = []
    if os.path.exists(base_dir):
        for d in os.listdir(base_dir):
            if task_id[:8] in d:
                work_dirs.append(os.path.join(base_dir, d))

    if not work_dirs:
        raise HTTPException(status_code=404, detail="任务不存在")

    work_dir = work_dirs[0]
    files = []
    for root, _, filenames in os.walk(work_dir):
        for f in filenames:
            rel_path = os.path.relpath(os.path.join(root, f), work_dir)
            size = os.path.getsize(os.path.join(root, f))
            files.append({"path": rel_path, "size": size})

    return {"task_id": task_id, "work_dir": work_dir, "files": files}


@router.get("/files/{task_id}/download/{file_path:path}")
async def download_file(task_id: str, file_path: str):
    """下载任务工作目录下的文件。"""
    base_dir = "project/work_dir"
    work_dirs = []
    if os.path.exists(base_dir):
        for d in os.listdir(base_dir):
            if task_id[:8] in d:
                work_dirs.append(os.path.join(base_dir, d))

    if not work_dirs:
        raise HTTPException(status_code=404, detail="任务不存在")

    full_path = os.path.join(work_dirs[0], file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(full_path, filename=os.path.basename(file_path))
