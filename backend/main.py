from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import json
import uuid

from config import config
from services.character_service import character_service
from services.event_service import event_service
from services.werewolf_service import werewolf_service
from services.ai_service import AIService
from services.redis_service import redis_service

app = FastAPI(title="Beast Carnival API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, room_id: str):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str, room_id: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(message)

manager = ConnectionManager()

# ==================== 基础API ====================

@app.get("/")
async def root():
    return {"message": "Beast Carnival API", "version": "1.0.0"}

@app.get("/api/worldview")
async def get_worldview():
    """获取世界观"""
    return {
        "title": "猛兽派对",
        "description": "欢迎来到猛兽派对——一切混乱、惊喜与爆笑的开端。",
        "host_ai": "森罗",
        "intro": "你将从解锁第一个角色——丧彪（猫）开始，逐步揭开这个世界的秘密。"
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
            
            # 检查是否完成
            if len(progress["found_clues"]) >= len(event["clues"]) and not progress["completed"]:
                await event_service.complete_event(user_id, event_id)
                ai_response += "\n\n🎉 恭喜！你解开了谜题！"
            
            # 发送回复
            await websocket.send_text(json.dumps({
                "type": "message",
                "content": ai_response
            }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"event_{user_id}_{event_id}")

# ==================== 狼人杀游戏 ====================

@app.post("/api/werewolf/room")
async def create_werewolf_room():
    """创建狼人杀房间"""
    room_id = await werewolf_service.create_room()
    return {"room_id": room_id}

@app.post("/api/werewolf/room/{room_id}/join")
async def join_werewolf_room(room_id: str, user_id: str, username: str):
    """加入狼人杀房间"""
    success = await werewolf_service.join_room(room_id, user_id, username)
    if success:
        return {"success": True, "room_id": room_id}
    raise HTTPException(status_code=400, detail="加入房间失败")

@app.post("/api/werewolf/room/{room_id}/start")
async def start_werewolf_game(room_id: str):
    """开始狼人杀游戏"""
    success = await werewolf_service.start_game(room_id)
    if success:
        return {"success": True}
    raise HTTPException(status_code=400, detail="开始游戏失败")

@app.get("/api/werewolf/room/{room_id}")
async def get_werewolf_room(room_id: str):
    """获取房间信息"""
    room = await werewolf_service.get_room(room_id)
    if room:
        return room.dict()
    raise HTTPException(status_code=404, detail="房间不存在")

@app.websocket("/ws/werewolf/{room_id}/{user_id}")
async def werewolf_game(websocket: WebSocket, room_id: str, user_id: str):
    """狼人杀游戏WebSocket"""
    await manager.connect(websocket, f"werewolf_{room_id}")
    
    try:
        room = await werewolf_service.get_room(room_id)
        if not room:
            await websocket.send_text(json.dumps({"error": "房间不存在"}))
            return
        
        # 发送房间状态
        await websocket.send_text(json.dumps({
            "type": "room_state",
            "room": room.dict()
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
                result = await werewolf_service.player_action(room_id, user_id, action, target)
                await websocket.send_text(json.dumps(result))
            
            elif action_type == "message":
                # 玩家发言
                content = message_data.get("content", "")
                await werewolf_service.player_action(room_id, user_id, content)
            
            # 广播更新
            room = await werewolf_service.get_room(room_id)
            if room:
                await manager.broadcast(json.dumps({
                    "type": "room_update",
                    "room": room.dict()
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

