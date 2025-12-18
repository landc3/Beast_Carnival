import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加 backend 目录到 Python 路径，以便正确导入模块
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.event import MysteryEvent, EventClue
from services.redis_service import redis_service

class EventService:
    """大事件服务"""
    
    def __init__(self):
        self.events_file = os.path.join(os.path.dirname(__file__), "..", "data", "events.json")
        self._load_events()
    
    def _load_events(self):
        """加载事件数据"""
        with open(self.events_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.events = {event["id"]: event for event in data["events"]}
    
    def get_event(self, event_id: str) -> Optional[Dict]:
        """获取事件"""
        return self.events.get(event_id)
    
    def get_character_event(self, character_id: str) -> Optional[Dict]:
        """根据角色ID获取事件"""
        for event in self.events.values():
            if event.get("character_id") == character_id:
                return event
        return None
    
    async def get_user_events(self, user_id: str) -> List[Dict]:
        """获取用户的事件列表"""
        user_data = await redis_service.get_user_data(user_id) or {}
        unlocked_characters = user_data.get("unlocked_characters", ["cat"])
        
        events = []
        for char_id in unlocked_characters:
            event = self.get_character_event(char_id)
            if event:
                event_data = await self.get_user_event_progress(user_id, event["id"])
                event.update(event_data)
                events.append(event)
        
        return events
    
    async def get_user_event_progress(self, user_id: str, event_id: str) -> Dict:
        """获取用户的事件进度"""
        key = f"event_progress:{user_id}:{event_id}"
        progress = await redis_service.get(key)
        
        if progress:
            return progress
        else:
            return {
                "unlocked": True,
                "completed": False,
                "found_clues": [],
                "conversation_history": []
            }
    
    async def save_event_progress(self, user_id: str, event_id: str, progress: Dict):
        """保存事件进度"""
        key = f"event_progress:{user_id}:{event_id}"
        await redis_service.set(key, progress, ex=86400 * 30)  # 30天过期
    
    async def add_clue(self, user_id: str, event_id: str, clue_id: str):
        """添加找到的线索"""
        progress = await self.get_user_event_progress(user_id, event_id)
        if clue_id not in progress["found_clues"]:
            progress["found_clues"].append(clue_id)
            await self.save_event_progress(user_id, event_id, progress)
    
    async def complete_event(self, user_id: str, event_id: str):
        """完成事件"""
        progress = await self.get_user_event_progress(user_id, event_id)
        progress["completed"] = True
        await self.save_event_progress(user_id, event_id, progress)
        
        # 更新用户数据
        user_data = await redis_service.get_user_data(user_id) or {}
        completed_events = user_data.get("completed_events", [])
        if event_id not in completed_events:
            completed_events.append(event_id)
            user_data["completed_events"] = completed_events
            await redis_service.set_user_data(user_id, user_data)

event_service = EventService()

