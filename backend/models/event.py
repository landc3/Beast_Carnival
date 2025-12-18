from pydantic import BaseModel
from typing import List, Optional, Dict

class EventClue(BaseModel):
    id: str
    content: str
    found: bool = False

class MysteryEvent(BaseModel):
    id: str
    character_id: str
    title: str
    background: str
    clues: List[EventClue]
    solution: str
    unlocked: bool = False
    completed: bool = False
    player_clues: List[str] = []  # 玩家已找到的线索
    conversation_history: List[Dict[str, str]] = []


















