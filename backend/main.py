from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from typing import List, Dict
import json
import uuid
import os
import sys
import logging
import time
import traceback

from config import config
from services.character_service import character_service
from services.event_service import event_service
from services.werewolf_service import werewolf_service
from services.ai_service import AIService
from services.redis_service import redis_service

# 配置日志 - 确保所有模块的日志都能输出
# 先清除所有现有的处理器，避免重复
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# 配置基础日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True,  # 强制重新配置，避免被其他配置覆盖
    handlers=[
        logging.StreamHandler(sys.stdout)  # 明确输出到stdout
    ]
)

# 确保根 logger 配置正确
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 确保 uvicorn 相关 logger 也能输出
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.INFO)
uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_error_logger.setLevel(logging.INFO)
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.INFO)

# 确保所有服务模块的日志都能输出
# 允许 propagate=True，确保日志能输出
for module_name in ['services.werewolf_service', 'services.ai_service', 'services.redis_service', 
                    'services.character_service', 'services.event_service', 'services', 'main']:
    module_logger = logging.getLogger(module_name)
    module_logger.setLevel(logging.INFO)
    module_logger.propagate = True  # 允许向上传播，确保日志能输出

logger = logging.getLogger(__name__)

app = FastAPI(title="Beast Carnival API")

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器，确保所有异常都被记录"""
    error_type = type(exc).__name__
    error_msg = str(exc)
    error_trace = traceback.format_exc()
    
    logger.error(f"【全局异常】{request.method} {request.url.path} - {error_type}: {error_msg}", exc_info=True)
    
    # 如果是 HTTPException，直接抛出
    if isinstance(exc, HTTPException):
        raise exc
    
    # 其他异常返回 500
    return JSONResponse(
        status_code=500,
        content={"detail": f"内部服务器错误: {error_msg}"}
    )

# CORS配置 - 必须先添加，因为中间件执行顺序是后进先出
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件 - 只记录错误，不记录正常请求
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """只记录HTTP请求错误，不记录正常请求"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        error_msg = f"【请求异常】{request.method} {request.url.path} - 错误: {str(e)}"
        error_trace = traceback.format_exc()
        
        # 只记录错误信息
        logger.error(error_msg, exc_info=True)
        
        # 返回500错误响应
        return JSONResponse(
            status_code=500,
            content={"detail": f"内部服务器错误: {str(e)}"}
        )

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        # 存储格式: {room_id: [(websocket, user_id), ...]}
        self.active_connections: Dict[str, List[tuple]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str = None):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append((websocket, user_id))
    
    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id] = [
                (ws, uid) for ws, uid in self.active_connections[room_id] if ws != websocket
            ]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def send_personal_message_to_user(self, room_id: str, user_id: str, message: str):
        """向特定用户发送个人消息"""
        room_key = f"werewolf_{room_id}"
        if room_key in self.active_connections:
            for websocket, ws_user_id in self.active_connections[room_key]:
                if ws_user_id == user_id:
                    try:
                        await websocket.send_text(message)
                    except Exception as e:
                        logger.error(f"发送私有消息失败 (房间 {room_id}, 用户 {user_id}): {e}")
    
    async def broadcast(self, message: str, room_id: str):
        if room_id in self.active_connections:
            for websocket, _ in self.active_connections[room_id]:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.error(f"广播消息失败 (房间 {room_id}): {e}")

manager = ConnectionManager()

async def get_room_data_with_extras(room_id: str):
    """获取房间数据，包含额外字段（如unlocked_characters）"""
    room = await werewolf_service.get_room(room_id)
    if room:
        room_data = room.model_dump()
        # 从Redis获取完整的房间数据，包含额外字段
        full_room_data = await redis_service.get_room_data(room_id)
        if full_room_data and "unlocked_characters" in full_room_data:
            room_data["unlocked_characters"] = full_room_data["unlocked_characters"]
        return room_data
    return None

# 启动事件处理器
@app.on_event("startup")
async def startup_event():
    """服务器启动时的初始化"""
    try:
        logger.info(f"后端服务已启动，监听地址: http://{config.HOST}:{config.PORT}")
        logger.info(f"API文档: http://{config.HOST}:{config.PORT}/docs")
        # 测试Redis连接
        try:
            redis_service.redis_client.ping()
            logger.info("✓ Redis连接正常")
        except Exception as e:
            logger.warning(f"⚠ Redis连接测试失败: {e}")
    except Exception as e:
        logger.error(f"启动事件处理失败: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    """服务器关闭时的清理"""
    logger.info("后端服务正在关闭...")

# ==================== 基础API ====================

@app.get("/")
async def root():
    return {"message": "Beast Carnival API", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查Redis连接
        redis_ok = False
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            await loop.run_in_executor(redis_service.executor, redis_service.redis_client.ping)
            redis_ok = True
        except:
            pass
        
        return {
            "status": "healthy",
            "redis": "connected" if redis_ok else "disconnected",
            "port": config.PORT,
            "host": config.HOST
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}

@app.get("/api/worldview")
async def get_worldview():
    """获取世界观"""
    try:
        worldview_file = os.path.join(os.path.dirname(__file__), "data", "worldview.json")
        with open(worldview_file, "r", encoding="utf-8") as f:
            worldview_data = json.load(f)
        
        worldview = worldview_data.get("worldview", {})
        
        # 计算实际项数
        item_count = 0
        item_count += len(worldview.get("settings", []))
        item_count += len(worldview.get("characters_overview", []))
        item_count += len(worldview.get("gameplay_features", []))
        item_count += len(worldview.get("gameplay_rules", []))
        # 加上基础信息项（title, subtitle, host_ai, introduction, contact）
        item_count += 5
        
        return {
            **worldview,
            "item_count": item_count
        }
    except FileNotFoundError:
        # 如果文件不存在，返回默认数据
        return {
            "title": "猛兽派对",
            "description": "欢迎来到猛兽派对——一切混乱、惊喜与爆笑的开端。",
            "host_ai": "森罗",
            "intro": "你将从解锁第一个角色——丧彪（猫）开始，逐步揭开这个世界的秘密。",
            "item_count": 0
        }

# ==================== 角色系统 ====================

@app.get("/api/characters")
async def get_characters():
    """获取所有角色"""
    return {"characters": character_service.get_all_characters()}

@app.get("/api/user/{user_id}/characters")
async def get_user_characters(user_id: str):
    """获取用户的角色列表"""
    characters = await character_service.get_user_characters(user_id)
    return characters

@app.post("/api/user/{user_id}/characters/{character_id}/unlock")
async def unlock_character(user_id: str, character_id: str):
    """解锁角色"""
    # 检查解锁条件
    can_unlock = await character_service.check_unlock_condition(user_id, character_id)
    if not can_unlock:
        raise HTTPException(status_code=400, detail="未满足解锁条件")
    
    success = await character_service.unlock_character(user_id, character_id)
    if success:
        return {"success": True, "message": f"🎉 新成员加入！你解锁了：{character_service.get_character(character_id)['name']}。"}
    return {"success": False, "message": "角色已解锁"}

# ==================== AI角色对话 ====================

@app.websocket("/ws/character/{user_id}/{character_id}")
async def character_chat(websocket: WebSocket, user_id: str, character_id: str):
    """角色对话WebSocket"""
    await manager.connect(websocket, f"character_{user_id}_{character_id}")
    
    try:
        character = character_service.get_character(character_id)
        if not character:
            await websocket.send_text(json.dumps({"error": "角色不存在"}))
            return
        
        # 获取对话记忆
        memory = await character_service.get_character_memory(user_id, character_id)
        
        # 构建system prompt
        system_prompt = AIService.build_character_prompt(character)
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            # 添加到对话历史
            memory.conversation_history.append({"role": "user", "content": user_message})
            
            # 调用AI
            ai_response = await AIService.generate_response(
                messages=memory.conversation_history,
                system_prompt=system_prompt
            )
            
            # 保存AI回复
            memory.conversation_history.append({"role": "assistant", "content": ai_response})
            await character_service.save_character_memory(memory)
            
            # 发送回复
            await websocket.send_text(json.dumps({
                "type": "message",
                "content": ai_response,
                "character": character["name"]
            }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"character_{user_id}_{character_id}")

# ==================== 大事件解谜 ====================

@app.get("/api/user/{user_id}/events")
async def get_user_events(user_id: str):
    """获取用户的事件列表"""
    events = await event_service.get_user_events(user_id)
    return {"events": events}

@app.websocket("/ws/event/{user_id}/{event_id}")
async def event_chat(websocket: WebSocket, user_id: str, event_id: str):
    """大事件解谜WebSocket"""
    await manager.connect(websocket, f"event_{user_id}_{event_id}")
    
    try:
        event = event_service.get_event(event_id)
        if not event:
            await websocket.send_text(json.dumps({"error": "事件不存在"}))
            return
        
        # 获取事件进度
        progress = await event_service.get_user_event_progress(user_id, event_id)
        
        # 发送背景
        await websocket.send_text(json.dumps({
            "type": "background",
            "content": event["background"]
        }))
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            # 构建prompt
            found_clues = [event["clues"][i]["content"] for i, clue in enumerate(event["clues"]) 
                          if clue["id"] in progress["found_clues"]]
            prompt = AIService.build_mystery_prompt(event, found_clues)
            
            # 构建对话历史
            messages = progress.get("conversation_history", [])
            messages.append({"role": "user", "content": user_message})
            
            # 调用AI
            ai_response = await AIService.generate_response(
                messages=messages,
                system_prompt=prompt
            )
            
            messages.append({"role": "assistant", "content": ai_response})
            progress["conversation_history"] = messages
            
            # 检查是否找到新线索（简单逻辑，实际应该更智能）
            for clue in event["clues"]:
                if clue["id"] not in progress["found_clues"]:
                    if any(keyword in user_message.lower() for keyword in clue["content"].lower().split()[:3]):
                        await event_service.add_clue(user_id, event_id, clue["id"])
                        progress["found_clues"].append(clue["id"])
                        ai_response += f"\n\n🔍 你发现了新线索：{clue['content']}"
            
            # 保存进度
            await event_service.save_event_progress(user_id, event_id, progress)
            
            # 检查是否完成：需要找到所有线索 AND 玩家说出正确答案
            event_completed = False
            unlocked_characters = []
            
            if not progress["completed"]:
                has_all_clues = len(progress["found_clues"]) >= len(event["clues"])
                solution_matched = event_service.check_solution_match(event_id, user_message)
                
                if has_all_clues and solution_matched:
                    await event_service.complete_event(user_id, event_id)
                    event_completed = True
                    ai_response += "\n\n🎉 恭喜！你解开了谜题！真相是：" + event.get("solution", "")
                    
                    # 检查并解锁符合条件的角色
                    unlocked_characters = await character_service.check_and_unlock_characters(user_id)
                elif solution_matched and not has_all_clues:
                    # 玩家说出了答案但还没找到所有线索，给予提示
                    ai_response += "\n\n💡 你的推理方向很接近了！但还需要更多线索来确认。继续调查吧！"
            
            # 发送回复
            response_data = {
                "type": "message",
                "content": ai_response
            }
            
            # 如果事件完成，添加完成标记
            if event_completed:
                response_data["event_completed"] = True
            
            # 如果有解锁的角色，添加解锁信息
            if unlocked_characters:
                response_data["unlocked_characters"] = unlocked_characters
            
            await websocket.send_text(json.dumps(response_data))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"event_{user_id}_{event_id}")

# ==================== 健康检查和测试路由 ====================

@app.get("/")
async def root():
    """根路径，用于健康检查"""
    return {"status": "ok", "message": "Beast Carnival API is running"}

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "Beast Carnival API"}

@app.get("/api/test")
async def test_endpoint():
    """测试端点，验证请求是否能到达后端"""
    return {"status": "ok", "message": "后端正常工作"}

@app.post("/api/test")
async def test_post_endpoint():
    """测试 POST 端点"""
    return {"status": "ok", "message": "POST 请求正常工作"}

# ==================== 狼人杀游戏 ====================

@app.post("/api/werewolf/room")
async def create_werewolf_room():
    """创建狼人杀房间"""
    try:
        room_id = await werewolf_service.create_room()
        logger.info(f"创建房间成功 - 房间ID: {room_id}")
        return {"room_id": room_id}
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"创建房间失败: {str(e)}"
        logger.error(f"创建房间失败: {error_detail}", exc_info=True)
        raise HTTPException(status_code=500, detail=error_detail)

@app.post("/api/werewolf/room/{room_id}/join")
async def join_werewolf_room(room_id: str, user_id: str, username: str):
    """加入狼人杀房间"""
    try:
        logger.info(f"【API调用】加入房间 - 房间ID: {room_id}, 用户ID: {user_id}, 用户名: {username}")
        success = await werewolf_service.join_room(room_id, user_id, username)
        if success:
            logger.info(f"【API调用】加入房间成功 - 房间ID: {room_id}, 用户ID: {user_id}")
            return {"success": True, "room_id": room_id}
        else:
            logger.warning(f"【API调用】加入房间失败 - 房间ID: {room_id}, 用户ID: {user_id}")
            raise HTTPException(status_code=400, detail="加入房间失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"【API错误】加入房间异常 - 房间ID: {room_id}, 用户ID: {user_id}, 错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"加入房间失败: {str(e)}")

@app.post("/api/werewolf/room/{room_id}/start")
async def start_werewolf_game(room_id: str, background_tasks: BackgroundTasks):
    """开始狼人杀游戏"""
    try:
        # 定义广播回调函数
        async def broadcast_message(message: str, room_key: str):
            await manager.broadcast(message, room_key)
        
        # 定义发送私有消息回调函数
        async def send_private_message(room_id: str, user_id: str, message: str):
            await manager.send_personal_message_to_user(room_id, user_id, message)
        
        # 设置广播回调，让werewolf_service能够广播消息
        werewolf_service.set_broadcast_callback(broadcast_message)
        # 设置发送私有消息回调
        werewolf_service.set_send_private_message_callback(send_private_message)
        
        success = await werewolf_service.start_game(room_id)
        if success:
            # 广播房间更新和消息
            room = await werewolf_service.get_room(room_id)
            if room:
                # 广播房间状态更新（包含unlocked_characters字段）
                room_data = await get_room_data_with_extras(room_id)
                if room_data:
                    await manager.broadcast(json.dumps({
                        "type": "room_update",
                        "room": room_data
                    }), f"werewolf_{room_id}")
                
                # 确保所有已连接的玩家都能收到私有消息
                # 从 Redis 获取所有私有消息并发送给对应的玩家
                for player in room.players:
                    private_messages = await redis_service.get_private_messages(room_id, player.user_id)
                    for msg in private_messages:
                        # 只发送身份消息（type为identity的消息）
                        if msg.get("type") == "identity":
                            await manager.send_personal_message_to_user(
                                room_id,  # send_personal_message_to_user 内部会自动添加 werewolf_ 前缀
                                player.user_id,
                                json.dumps({
                                    "type": "private_message",
                                    "content": msg
                                })
                            )
                
                # 广播所有公共消息（包括阶段弹窗消息）
                public_messages = await redis_service.get_room_messages(room_id)
                for msg in public_messages:
                    await manager.broadcast(json.dumps({
                        "type": "public_message",
                        "content": msg
                    }), f"werewolf_{room_id}")
            
            # 在后台任务中启动夜晚阶段，避免阻塞API响应
            async def start_night_phase_background():
                """后台任务：启动夜晚阶段"""
                try:
                    import asyncio
                    # 等待一下，确保身份分配消息已发送
                    await asyncio.sleep(0.5)
                    # 启动夜晚阶段（这会花费较长时间）
                    await werewolf_service._start_night_phase(room_id)
                except Exception as e:
                    logger.error(f"后台启动夜晚阶段失败 (房间 {room_id}): {e}", exc_info=True)
            
            # 添加后台任务
            background_tasks.add_task(start_night_phase_background)
            
            return {"success": True}
        else:
            raise HTTPException(status_code=400, detail="开始游戏失败：请检查房间状态和玩家数量")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开始游戏异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"开始游戏失败：{str(e)}")

@app.get("/api/werewolf/room/{room_id}")
async def get_werewolf_room(room_id: str):
    """获取房间信息"""
    room_data = await get_room_data_with_extras(room_id)
    if room_data:
        return room_data
    raise HTTPException(status_code=404, detail="房间不存在")

@app.post("/api/werewolf/room/{room_id}/add-ai")
async def add_ai_player(room_id: str):
    """添加AI玩家"""
    success = await werewolf_service.add_ai_player(room_id)
    if success:
        return {"success": True}
    raise HTTPException(status_code=400, detail="添加AI玩家失败")

@app.post("/api/werewolf/room/{room_id}/auto-fill-ai")
async def auto_fill_ai_players(room_id: str, target_count: int = 7):
    """自动填充AI玩家到目标人数"""
    added_count = await werewolf_service.auto_fill_ai_players(room_id, target_count)
    return {"success": True, "added_count": added_count}

@app.websocket("/ws/werewolf/{room_id}/{user_id}")
async def werewolf_game(websocket: WebSocket, room_id: str, user_id: str):
    """狼人杀游戏WebSocket"""
    await manager.connect(websocket, f"werewolf_{room_id}", user_id)
    
    try:
        room = await werewolf_service.get_room(room_id)
        if not room:
            await websocket.send_text(json.dumps({"error": "房间不存在"}))
            return
        
        # 发送房间状态（包含额外字段）
        room_data = await get_room_data_with_extras(room_id)
        if room_data:
            await websocket.send_text(json.dumps({
                "type": "room_state",
                "room": room_data
            }))
        
        # 发送私有消息
        private_messages = await redis_service.get_private_messages(room_id, user_id)
        for msg in private_messages:
            await websocket.send_text(json.dumps({
                "type": "private_message",
                "content": msg
            }))
        
        # 发送公共消息
        public_messages = await redis_service.get_room_messages(room_id)
        for msg in public_messages[-10:]:  # 最近10条
            await websocket.send_text(json.dumps({
                "type": "public_message",
                "content": msg
            }))
        
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            action_type = message_data.get("type")
            
            if action_type == "action":
                # 玩家行动
                action = message_data.get("action", "")
                target = message_data.get("target")
                action_data = {"target": target} if target is not None else {}
                result = await werewolf_service.player_action(room_id, user_id, action, action_data)
                await websocket.send_text(json.dumps(result))
            
            elif action_type == "wolf_chat":
                # 狼人私聊消息
                content = message_data.get("content", "")
                result = await werewolf_service.handle_wolf_chat(room_id, user_id, content)
                # 如果成功，广播给所有狼人
                if result.get("success"):
                    room = await werewolf_service.get_room(room_id)
                    if room:
                        # 获取所有狼人玩家
                        wolves = [p for p in room.players if p.role.value == "wolf" and p.alive]
                        for wolf in wolves:
                            await manager.send_personal_message_to_user(
                                f"werewolf_{room_id}",
                                wolf.user_id,
                                json.dumps({
                                    "type": "wolf_chat",
                                    "content": {
                                        "content": content,
                                        "username": result.get("username", "未知"),
                                        "timestamp": result.get("timestamp")
                                    }
                                })
                            )
            
            elif action_type == "message":
                # 玩家发言
                content = message_data.get("content", "")
                result = await werewolf_service.player_action(room_id, user_id, "message", {"content": content})
                
                # 广播玩家消息
                room = await werewolf_service.get_room(room_id)
                if room:
                    # 获取最新的消息并广播
                    public_messages = await redis_service.get_room_messages(room_id)
                    if public_messages:
                        latest_message = public_messages[-1]
                        await manager.broadcast(json.dumps({
                            "type": "public_message",
                            "content": latest_message
                        }), f"werewolf_{room_id}")
                    
                    # 广播房间更新（包含额外字段）
                    room_data = await get_room_data_with_extras(room_id)
                    if room_data:
                        await manager.broadcast(json.dumps({
                            "type": "room_update",
                            "room": room_data
                        }), f"werewolf_{room_id}")
                    
                    # 触发AI玩家自动回复
                    if room.phase == "day":
                        async def broadcast_ai_message(room_id: str, message: Dict):
                            """广播AI玩家的消息"""
                            await manager.broadcast(json.dumps({
                                "type": "public_message",
                                "content": message
                            }), f"werewolf_{room_id}")
                        
                        # 异步触发AI回复（不等待完成）
                        import asyncio
                        asyncio.create_task(werewolf_service._trigger_ai_responses(room, broadcast_ai_message))
            
            elif action_type == "last_words":
                # 玩家提交遗言
                content = message_data.get("content", "")
                result = await werewolf_service.player_action(room_id, user_id, "last_words", {"content": content})
                await websocket.send_text(json.dumps(result))
                
                # 广播房间更新和遗言消息
                room = await werewolf_service.get_room(room_id)
                if room:
                    # 获取最新的消息并广播
                    public_messages = await redis_service.get_room_messages(room_id)
                    if public_messages:
                        latest_message = public_messages[-1]
                        await manager.broadcast(json.dumps({
                            "type": "public_message",
                            "content": latest_message
                        }), f"werewolf_{room_id}")
                    
                    room_data = await get_room_data_with_extras(room_id)
                    if room_data:
                        await manager.broadcast(json.dumps({
                            "type": "room_update",
                            "room": room_data
                        }), f"werewolf_{room_id}")
            
            elif action_type == "hunter_shot":
                # 猎人开枪
                target = message_data.get("target")
                result = await werewolf_service.player_action(room_id, user_id, "hunter_shot", {"target": target})
                await websocket.send_text(json.dumps(result))
                
                # 广播房间更新
                room = await werewolf_service.get_room(room_id)
                if room:
                    # 获取最新的消息并广播
                    public_messages = await redis_service.get_room_messages(room_id)
                    if public_messages:
                        latest_message = public_messages[-1]
                        await manager.broadcast(json.dumps({
                            "type": "public_message",
                            "content": latest_message
                        }), f"werewolf_{room_id}")
                    
                    room_data = await get_room_data_with_extras(room_id)
                    if room_data:
                        await manager.broadcast(json.dumps({
                            "type": "room_update",
                            "room": room_data
                        }), f"werewolf_{room_id}")
            
            # 广播更新（用于其他类型的action）
            if action_type not in ["message", "last_words", "hunter_shot"]:
                room_data = await get_room_data_with_extras(room_id)
                if room_data:
                    await manager.broadcast(json.dumps({
                        "type": "room_update",
                        "room": room_data
                    }), f"werewolf_{room_id}")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"werewolf_{room_id}")

# ==================== 真心话大冒险 ====================

@app.post("/api/truth-or-dare/generate")
async def generate_truth_or_dare(game_result: str, player_count: int = 2):
    """生成真心话/大冒险问题"""
    prompt = f"""生成一个{'真心话' if game_result == 'wolves_win' else '大冒险'}问题。

游戏结果：{'狼人胜利' if game_result == 'wolves_win' else '好人胜利'}
玩家数量：{player_count}

请生成一个有趣的问题，类型可以是：趣味、情感、社死、哲学、行为挑战中的一种。
只返回问题内容，不要其他说明。"""
    
    response = await AIService.generate_response(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9
    )
    
    return {"question": response, "type": "truth_or_dare"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)

