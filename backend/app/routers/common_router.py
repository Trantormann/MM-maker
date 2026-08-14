"""通用路由模块，提供健康检查等基础接口。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "healthy", "service": "MMmaker"}
