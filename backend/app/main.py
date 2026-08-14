"""MMmaker 后端应用入口。"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import modeling_router, ws_router, common_router, files_router
from app.utils.log_util import logger

# 确保工作目录存在（StaticFiles 挂载时要求目录已存在，需在 import 阶段创建）
os.makedirs("project/work_dir", exist_ok=True)

# 前端构建产物目录（相对 backend 目录）；存在则单进程托管前端
FRONTEND_DIST = Path("frontend_dist")


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


# ---- 前端静态托管（单进程部署） ----
# 若存在前端构建产物，则挂载其静态资源，并将根路径与未匹配的路径回退到 index.html。
# 这样生产环境只需启动后端一个进程，浏览器访问 http://localhost:8000 即可。
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="frontend-assets",
        )

    async def _serve_index():
        """返回前端入口 HTML。"""
        return FileResponse(str(FRONTEND_DIST / "index.html"))

    @app.get("/", include_in_schema=False)
    async def spa_root():
        """根路径：单进程部署时返回前端页面。"""
        return await _serve_index()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """SPA 回退：非 API 路径统一返回 index.html。"""
        # 已注册的 API 路由优先匹配，不会走到这里；
        # 走到这里的都是未知路径，尝试返回前端入口。
        index_path = FRONTEND_DIST / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"detail": "Not Found"}
else:
    logger.info("未检测到 frontend_dist，跳过前端静态托管（开发模式请运行前端 dev server）")
