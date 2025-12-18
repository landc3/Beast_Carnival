import redis
import json
import asyncio
from typing import Optional, Dict, Any, List
from config import config

class RedisService:
    """Redis服务，用于房间同步和状态管理"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        # 测试连接
        try:
            self.redis_client.ping()
        except redis.ConnectionError as e:
            print(f"警告: Redis连接失败: {e}")
            print("请确保Redis服务正在运行")
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        """设置键值"""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        # 使用 asyncio.to_thread 将同步操作转换为异步
        await asyncio.to_thread(self.redis_client.set, key, value, ex=ex)
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        value = await asyncio.to_thread(self.redis_client.get, key)
        if value:
            try:
                return json.loads(value)
            except:
                return value
        return None
    
    async def delete(self, key: str):
        """删除键"""
        await asyncio.to_thread(self.redis_client.delete, key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        result = await asyncio.to_thread(self.redis_client.exists, key)
        return bool(result)
    
    async def set_user_data(self, user_id: str, data: Dict):
        """设置用户数据"""
        await self.set(f"user:{user_id}", data)
    
    async def get_user_data(self, user_id: str) -> Optional[Dict]:
        """获取用户数据"""
        return await self.get(f"user:{user_id}")
    
    async def set_room_data(self, room_id: str, data: Dict):
        """设置房间数据"""
        await self.set(f"room:{room_id}", data, ex=3600)  # 1小时过期
    
    async def get_room_data(self, room_id: str) -> Optional[Dict]:
        """获取房间数据"""
        return await self.get(f"room:{room_id}")
    
    async def add_room_message(self, room_id: str, message: Dict):
        """添加房间消息"""
        key = f"room:{room_id}:messages"
        messages = await self.get(key) or []
        messages.append(message)
        await self.set(key, messages, ex=3600)
    
    async def get_room_messages(self, room_id: str) -> List[Dict]:
        """获取房间消息"""
        return await self.get(f"room:{room_id}:messages") or []
    
    async def add_private_message(self, room_id: str, user_id: str, message: Dict):
        """添加私有消息"""
        key = f"room:{room_id}:private:{user_id}"
        messages = await self.get(key) or []
        messages.append(message)
        await self.set(key, messages, ex=3600)
    
    async def get_private_messages(self, room_id: str, user_id: str) -> List[Dict]:
        """获取私有消息"""
        return await self.get(f"room:{room_id}:private:{user_id}") or []

# 全局Redis服务实例
redis_service = RedisService()

