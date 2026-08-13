"""WebSocket 管理模块。"""

import json

from fastapi import WebSocket

from app.utils.log_util import logger


class WebSocketManager:
    """WebSocket 连接管理器。"""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        """建立 WebSocket 连接。"""
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        logger.info(f"WebSocket connected for task {task_id}")

    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开 WebSocket 连接。"""
        if task_id in self.active_connections:
            self.active_connections[task_id] = [
                ws for ws in self.active_connections[task_id] if ws != websocket
            ]
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        logger.info(f"WebSocket disconnected for task {task_id}")

    async def send_message(self, task_id: str, message: dict):
        """向指定任务的所有连接发送消息。"""
        if task_id not in self.active_connections:
            return
        disconnected = []
        for ws in self.active_connections[task_id]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws, task_id)

    async def broadcast(self, message: dict):
        """广播消息到所有连接。"""
        for task_id in list(self.active_connections.keys()):
            await self.send_message(task_id, message)


ws_manager = WebSocketManager()
