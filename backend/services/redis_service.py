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
            print(f"[Redis同步] 执行 set: key={key}, value_len={len(value) if value else 0}, ex={ex}", flush=True)
            if ex is not None and ex > 0:
                result = self.redis_client.set(key, value, ex=ex)
                print(f"[Redis同步] set 成功 (带过期时间): {result}", flush=True)
                return result
            else:
                result = self.redis_client.set(key, value)
                print(f"[Redis同步] set 成功 (无过期时间): {result}", flush=True)
                return result
        except Exception as e:
            print(f"[Redis同步错误] set 失败: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # 如果带 ex 参数失败，尝试不带参数
            if ex is not None:
                try:
                    print(f"[Redis同步] 尝试不带过期时间重试", flush=True)
                    result = self.redis_client.set(key, value)
                    print(f"[Redis同步] 重试成功: {result}", flush=True)
                    return result
                except Exception as retry_e:
                    print(f"[Redis同步错误] 重试也失败: {type(retry_e).__name__}: {retry_e}", flush=True)
                    traceback.print_exc()
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
            print(f"[Redis] 开始设置键: {key}, ex={ex}", flush=True)
            sys.stdout.write(f"[Redis] 开始设置键: {key}, ex={ex}\n")
            sys.stdout.flush()
            
            # 先序列化数据
            if isinstance(value, (dict, list)):
                print(f"[Redis] 序列化数据，类型: {type(value)}", flush=True)
                sys.stdout.write(f"[Redis] 序列化数据，类型: {type(value)}\n")
                sys.stdout.flush()
                value = json.dumps(value, ensure_ascii=False, default=str)
                print(f"[Redis] 序列化完成，长度: {len(value)}", flush=True)
                sys.stdout.write(f"[Redis] 序列化完成，长度: {len(value)}\n")
                sys.stdout.flush()
            
            # 使用线程池执行同步操作，避免阻塞事件循环
            # 在 Windows 上，直接使用 run_in_executor 更稳定
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            
            print(f"[Redis] 准备执行 set 操作", flush=True)
            sys.stdout.write(f"[Redis] 准备执行 set 操作\n")
            sys.stdout.flush()
            
            # 统一使用 run_in_executor，避免 asyncio.to_thread 在 Windows 上的兼容性问题
            if ex is not None and ex > 0:
                print(f"[Redis] 使用过期时间: {ex}秒", flush=True)
                sys.stdout.write(f"[Redis] 使用过期时间: {ex}秒\n")
                sys.stdout.flush()
                set_func = partial(self._set_sync, key, value, ex)
            else:
                print(f"[Redis] 不使用过期时间", flush=True)
                sys.stdout.write(f"[Redis] 不使用过期时间\n")
                sys.stdout.flush()
                set_func = partial(self._set_sync, key, value)
            
            # 直接使用 run_in_executor，在所有平台上都稳定
            print(f"[Redis] 调用 run_in_executor 执行 set 操作", flush=True)
            sys.stdout.write(f"[Redis] 调用 run_in_executor 执行 set 操作\n")
            sys.stdout.flush()
            try:
                # 添加超时保护，避免无限等待
                result = await asyncio.wait_for(
                    loop.run_in_executor(_executor, set_func),
                    timeout=5.0  # 5秒超时
                )
                print(f"[Redis] run_in_executor 执行完成，结果: {result}", flush=True)
                sys.stdout.write(f"[Redis] run_in_executor 执行完成，结果: {result}\n")
                sys.stdout.flush()
            except asyncio.TimeoutError:
                error_msg = "[Redis错误] run_in_executor 执行超时（超过5秒）"
                print(error_msg, flush=True)
                sys.stdout.write(error_msg + "\n")
                sys.stdout.flush()
                raise Exception("Redis操作超时") from None
            except Exception as executor_error:
                print(f"[Redis错误] run_in_executor 执行失败: {type(executor_error).__name__}: {executor_error}", flush=True)
                sys.stdout.write(f"[Redis错误] run_in_executor 执行失败: {type(executor_error).__name__}: {executor_error}\n")
                sys.stdout.flush()
                import traceback
                error_trace = traceback.format_exc()
                print(f"[Redis错误] 执行器错误堆栈:\n{error_trace}", flush=True)
                sys.stdout.write(f"[Redis错误] 执行器错误堆栈:\n{error_trace}\n")
                sys.stdout.flush()
                raise
            
            print(f"[Redis] set 操作完成: {key}", flush=True)
            
        except redis.RedisError as e:
            error_msg = f"Redis连接错误 (key={key}): {e}"
            print(f"[Redis错误] {error_msg}", flush=True)
            import traceback
            traceback.print_exc()
            raise Exception(error_msg) from e
        except json.JSONEncodeError as e:
            error_msg = f"JSON序列化错误 (key={key}): {e}"
            print(f"[Redis错误] {error_msg}", flush=True)
            import traceback
            traceback.print_exc()
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Redis set操作失败 (key={key}): {e}"
            print(f"[Redis错误] {error_msg}", flush=True)
            import traceback
            traceback.print_exc()
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
