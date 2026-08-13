"""WebSocket 路由模块，提供实时消息推送。"""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.redis_manager import redis_manager
from app.services.ws_manager import ws_manager
from app.utils.log_util import logger

router = APIRouter()


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket 连接端点，订阅指定任务的消息。"""
    await ws_manager.connect(websocket, task_id)
    forward_task = None

    try:
        # 同时订阅 Redis 消息并转发到 WebSocket
        pubsub = await redis_manager.subscribe(task_id)

        async def forward_redis_messages():
            """将 Redis 消息转发到 WebSocket。"""
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            await ws_manager.send_message(task_id, data)
                        except json.JSONDecodeError:
                            await ws_manager.send_message(
                                task_id, {"content": message["data"], "type": "info"}
                            )
            except Exception as e:
                logger.error(f"Redis 消息转发失败: {e}")

        import asyncio
        forward_task = asyncio.create_task(forward_redis_messages())

        # 接收客户端消息
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WebSocket 收到消息: {data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: {task_id}")
    finally:
        if forward_task:
            forward_task.cancel()
        ws_manager.disconnect(websocket, task_id)
