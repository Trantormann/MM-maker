"""MMmaker 后端应用入口。"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import modeling_router, ws_router, common_router, files_router
from app.utils.log_util import logger

# 确保工作目录存在（StaticFiles 挂载时要求目录已存在，需在 import 阶段创建）
os.makedirs("project/work_dir", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    logger.info("Starting MMmaker Backend")
    os.makedirs("project/work_dir", exist_ok=True)
    yield
    logger.info("Stopping MMmaker Backend")


app = FastAPI(
    title="MMmaker",
    description="国奖级数学建模竞赛自动化系统",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册路由
app.include_router(modeling_router.router)
app.include_router(ws_router.router)
app.include_router(common_router.router)
app.include_router(files_router.router)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 静态文件服务（生成的论文、图片等）
app.mount(
    "/static",
    StaticFiles(directory="project/work_dir"),
    name="static",
)
