import redis
import json
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# 添加 backend 目录到 Python 路径，以便正确导入模块
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import config

# 检查 asyncio.to_thread 是否可用（Python 3.9+）
HAS_TO_THREAD = hasattr(asyncio, 'to_thread')
# 统一创建线程池，用于回退方案
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="redis")

class RedisService:
    """Redis服务，用于房间同步和状态管理 - 简化版本，避免Windows兼容性问题"""
    
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
    
    def _set_sync(self, key: str, value: str, ex: Optional[int] = None):
        """同步设置键值 - 内部方法"""
        try:
            if ex is not None and ex > 0:
                result = self.redis_client.set(key, value, ex=ex)
                return result
            else:
                result = self.redis_client.set(key, value)
                return result
        except Exception as e:
            # 如果带 ex 参数失败，尝试不带参数
            if ex is not None:
                try:
                    result = self.redis_client.set(key, value)
                    return result
                except Exception as retry_e:
                    raise retry_e
            raise e
    
    def _get_sync(self, key: str) -> Optional[str]:
        """同步获取值 - 内部方法"""
        return self.redis_client.get(key)
    
    def _delete_sync(self, key: str):
        """同步删除键 - 内部方法"""
        return self.redis_client.delete(key)
    
    def _exists_sync(self, key: str) -> bool:
        """同步检查键是否存在 - 内部方法"""
        return bool(self.redis_client.exists(key))
    
    async def set(self, key: str, value: Any, ex: Optional[int] = None):
        """设置键值 - 使用线程池执行同步操作"""
        try:
            # 先序列化数据
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, default=str)
            
            # 使用线程池执行同步操作，避免阻塞事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            
            # 统一使用 run_in_executor，避免 asyncio.to_thread 在 Windows 上的兼容性问题
            if ex is not None and ex > 0:
                set_func = partial(self._set_sync, key, value, ex)
            else:
                set_func = partial(self._set_sync, key, value)
            
            # 直接使用 run_in_executor，在所有平台上都稳定
            try:
                # 添加超时保护，避免无限等待
                result = await asyncio.wait_for(
                    loop.run_in_executor(_executor, set_func),
                    timeout=5.0  # 5秒超时
                )
            except asyncio.TimeoutError:
                raise Exception("Redis操作超时") from None
            except Exception as executor_error:
                import traceback
                error_trace = traceback.format_exc()
                print(f"[Redis错误] 执行失败 (key={key}): {type(executor_error).__name__}: {executor_error}", flush=True)
                raise
            
        except redis.RedisError as e:
            error_msg = f"Redis连接错误 (key={key}): {e}"
            print(f"[Redis错误] {error_msg}", flush=True)
            raise Exception(error_msg) from e
        except json.JSONEncodeError as e:
            error_msg = f"JSON序列化错误 (key={key}): {e}"
            print(f"[Redis错误] {error_msg}", flush=True)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Redis set操作失败 (key={key}): {e}"
            print(f"[Redis错误] {error_msg}", flush=True)
            raise Exception(error_msg) from e
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            value = await loop.run_in_executor(_executor, self._get_sync, key)
            
            if value:
                try:
                    return json.loads(value)
                except:
                    return value
            return None
        except Exception as e:
            print(f"[Redis错误] get操作失败 (key={key}): {e}", flush=True)
            return None
    
    async def delete(self, key: str):
        """删除键"""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            await loop.run_in_executor(_executor, self._delete_sync, key)
        except Exception as e:
            print(f"[Redis错误] delete操作失败 (key={key}): {e}", flush=True)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(_executor, self._exists_sync, key)
            return result
        except Exception as e:
            print(f"[Redis错误] exists操作失败 (key={key}): {e}", flush=True)
            return False
    
    async def set_user_data(self, user_id: str, data: Dict):
        """设置用户数据"""
        await self.set(f"user:{user_id}", data)
    
    async def get_user_data(self, user_id: str) -> Optional[Dict]:
        """获取用户数据"""
        return await self.get(f"user:{user_id}")
    
    async def set_room_data(self, room_id: str, data: Dict):
        """设置房间数据"""
        # 暂时不使用过期时间，避免 Windows 上的参数问题
        # await self.set(f"room:{room_id}", data, ex=3600)  # 1小时过期
        await self.set(f"room:{room_id}", data)  # 暂时不使用过期时间
    
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
