from pydantic import BaseModel
from typing import List, Optional, Dict

class Character(BaseModel):
    id: str
    name: str
    animal: str  # 猫、狗、鸭子、鳄鱼、狼
    personality: str  # 毒舌、傲娇、治愈、冷静、反社交
    background: str
    skills: List[str]
    unlock_condition: str
    unlocked: bool = False
    event_id: Optional[str] = None  # 对应的大事件ID

class CharacterMemory(BaseModel):
    character_id: str
    user_id: str
    conversation_history: List[Dict[str, str]]  # [{"role": "user/assistant", "content": "..."}]
    personality_traits: Dict[str, str]  # 自定义性格特征





