"""通用路由模块，提供健康检查等基础接口。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "healthy", "service": "MMmaker"}


@router.get("/")
async def root():
    """根路径。"""
    return {
        "name": "MMmaker",
        "version": "0.1.0",
        "description": "国奖级数学建模竞赛自动化系统",
    }
