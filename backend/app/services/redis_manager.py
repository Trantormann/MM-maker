"""Redis 管理模块，负责任务队列和消息发布。"""

import json

import redis.asyncio as redis

from app.config.setting import settings
from app.utils.log_util import logger


class RedisManager:
    """Redis 连接管理器。"""

    def __init__(self):
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None

    async def get_client(self) -> redis.Redis:
        """获取 Redis 客户端连接。"""
        if self._client is None:
            self._pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._pool)
        return self._client

    async def publish_message(self, task_id: str, message) -> None:
        """发布消息到指定任务的频道。"""
        try:
            client = await self.get_client()
            channel = f"task:{task_id}"
            if hasattr(message, "model_dump_json"):
                data = message.model_dump_json()
            elif isinstance(message, dict):
                data = json.dumps(message, ensure_ascii=False)
            else:
                data = str(message)
            await client.publish(channel, data)
            logger.debug(f"Published to {channel}: {data[:100]}...")
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")

    async def subscribe(self, task_id: str):
        """订阅任务频道。"""
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"task:{task_id}")
        return pubsub

    async def set_task_status(self, task_id: str, status: dict) -> None:
        """设置任务状态。"""
        client = await self.get_client()
        await client.set(f"task_status:{task_id}", json.dumps(status, ensure_ascii=False))

    async def get_task_status(self, task_id: str) -> dict | None:
        """获取任务状态。"""
        client = await self.get_client()
        data = await client.get(f"task_status:{task_id}")
        return json.loads(data) if data else None

    async def close(self):
        """关闭连接。"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()


redis_manager = RedisManager()
