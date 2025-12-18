import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加 backend 目录到 Python 路径，以便正确导入模块
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.character import Character, CharacterMemory
from services.redis_service import redis_service

class CharacterService:
    """角色服务"""
    
    def __init__(self):
        self.characters_file = os.path.join(os.path.dirname(__file__), "..", "data", "characters.json")
        self._load_characters()
    
    def _load_characters(self):
        """加载角色数据"""
        with open(self.characters_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.characters = {char["id"]: char for char in data["characters"]}
    
    def get_all_characters(self) -> List[Dict]:
        """获取所有角色"""
        return list(self.characters.values())
    
    def get_character(self, character_id: str) -> Optional[Dict]:
        """获取单个角色"""
        return self.characters.get(character_id)
    
    async def get_user_characters(self, user_id: str) -> Dict[str, List[Dict]]:
        """获取用户的角色列表（已解锁/未解锁）"""
        user_data = await redis_service.get_user_data(user_id)
        unlocked_ids = user_data.get("unlocked_characters", ["cat"]) if user_data else ["cat"]
        
        unlocked = [char for char_id, char in self.characters.items() if char_id in unlocked_ids]
        locked = [char for char_id, char in self.characters.items() if char_id not in unlocked_ids]
        
        return {
            "unlocked": unlocked,
            "locked": locked
        }
    
    async def unlock_character(self, user_id: str, character_id: str) -> bool:
        """解锁角色"""
        user_data = await redis_service.get_user_data(user_id) or {}
        unlocked = user_data.get("unlocked_characters", ["cat"])
        
        if character_id not in unlocked:
            unlocked.append(character_id)
            user_data["unlocked_characters"] = unlocked
            await redis_service.set_user_data(user_id, user_data)
            return True
        return False
    
    async def check_unlock_condition(self, user_id: str, character_id: str) -> bool:
        """检查角色解锁条件"""
        character = self.get_character(character_id)
        if not character:
            return False
        
        user_data = await redis_service.get_user_data(user_id) or {}
        condition = character.get("unlock_condition", "")
        
        # 根据条件判断
        if "新手引导" in condition:
            return True  # 默认解锁
        elif "赢得3场狼人杀" in condition:
            wins = user_data.get("werewolf_wins", 0)
            return wins >= 3
        elif "完成第一个大事件" in condition:
            completed_events = user_data.get("completed_events", [])
            return len(completed_events) > 0
        elif "作为平民获胜" in condition:
            villager_wins = user_data.get("villager_wins", 0)
            return villager_wins > 0
        elif "作为狼人获胜" in condition:
            wolf_wins = user_data.get("wolf_wins", 0)
            return wolf_wins > 0
        
        return False
    
    async def get_character_memory(self, user_id: str, character_id: str) -> CharacterMemory:
        """获取角色对话记忆"""
        key = f"character_memory:{user_id}:{character_id}"
        data = await redis_service.get(key)
        
        if data:
            return CharacterMemory(**data)
        else:
            return CharacterMemory(
                character_id=character_id,
                user_id=user_id,
                conversation_history=[],
                personality_traits={}
            )
    
    async def save_character_memory(self, memory: CharacterMemory):
        """保存角色对话记忆"""
        key = f"character_memory:{memory.user_id}:{memory.character_id}"
        await redis_service.set(key, memory.model_dump(), ex=86400 * 7)  # 7天过期

character_service = CharacterService()

