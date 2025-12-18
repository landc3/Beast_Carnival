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
    
    def check_solution_match(self, event_id: str, user_message: str) -> bool:
        """检查玩家的回答是否匹配固定答案"""
        event = self.get_event(event_id)
        if not event or not event.get("solution"):
            return False
        
        solution = event["solution"].lower()
        user_message_lower = user_message.lower()
        
        # 提取答案中的关键要素（根据事件类型不同，提取不同的关键词）
        # 对于"消失的鱼干"事件，关键要素包括：狐狸、偷走、暗恋/吸引注意、约会
        if event_id == "event_cat_mystery":
            # 关键要素：狐狸、偷/偷走、暗恋/吸引、约会
            key_terms = [
                ["狐狸", "小狐狸", "狐"],
                ["偷", "偷走", "拿走", "带走", "盗"],
                ["暗恋", "喜欢", "吸引", "注意", "爱慕"],
                ["约会", "邀请", "纸条", "见面"]
            ]
            # 至少需要匹配4个关键要素组中的2个，且必须包含"狐狸"或"偷"相关（核心要素）
            matched_groups = sum(1 for group in key_terms if any(term in user_message_lower for term in group))
            has_core_terms = any(term in user_message_lower for group in [key_terms[0], key_terms[1]] for term in group)
            return matched_groups >= 2 and has_core_terms
        elif event_id == "event_dog_mystery":
            # "失踪的小主人"事件
            key_terms = [
                ["离家出走", "出走", "离开"],
                ["被欺负", "欺负", "霸凌"],
                ["森林", "秘密基地"],
                ["勇气", "证明"]
            ]
            matched_groups = sum(1 for group in key_terms if any(term in user_message_lower for term in group))
            return matched_groups >= 2
        elif event_id == "event_duck_mystery":
            # "池塘的秘密"事件
            key_terms = [
                ["工厂", "污染", "污水"],
                ["排放", "偷偷"],
                ["证据", "收集"]
            ]
            matched_groups = sum(1 for group in key_terms if any(term in user_message_lower for term in group))
            return matched_groups >= 2
        else:
            # 对于其他事件，使用更通用的匹配逻辑
            import re
            # 提取答案中的关键词（去除常见词和标点）
            common_words = {"的", "了", "是", "在", "有", "和", "与", "或", "但", "因为", "所以", "需要", "可能", "应该"}
            solution_words = set([word for word in re.findall(r'\w+', solution) 
                                 if len(word) > 1 and word not in common_words])
            user_words = set([word for word in re.findall(r'\w+', user_message_lower) 
                            if len(word) > 1 and word not in common_words])
            # 计算重叠度
            if len(solution_words) == 0:
                return False
            overlap_ratio = len(solution_words & user_words) / len(solution_words)
            # 如果重叠度超过30%，或者包含答案的前半部分关键短语
            return overlap_ratio >= 0.3 or any(key_phrase in user_message_lower 
                                              for key_phrase in solution.split("，")[:2] if len(key_phrase) > 5)
    
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

