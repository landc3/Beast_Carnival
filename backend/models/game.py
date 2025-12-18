from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class GamePhase(str, Enum):
    WAITING = "waiting"  # 等待玩家
    IDENTITY_ASSIGN = "identity_assign"  # 分配身份
    NIGHT = "night"  # 夜晚
    DAY = "day"  # 白天
    VOTING = "voting"  # 投票
    ELIMINATION = "elimination"  # 淘汰
    GAME_OVER = "game_over"  # 游戏结束

class PlayerRole(str, Enum):
    WOLF = "wolf"  # 狼人
    VILLAGER = "villager"  # 平民
    SEER = "seer"  # 预言家
    WITCH = "witch"  # 女巫
    HUNTER = "hunter"  # 猎人
    GUARD = "guard"  # 守卫

class Player(BaseModel):
    user_id: str
    username: str
    role: Optional[PlayerRole] = None
    alive: bool = True
    voted: bool = False
    vote_target: Optional[str] = None
    is_ai: bool = False  # 是否为AI玩家
    # 守卫相关
    guarded: bool = False  # 是否被守卫守护
    guard_target: Optional[str] = None  # 守卫守护的目标（用于检查连续守护）
    last_guard_target: Optional[str] = None  # 上一晚守卫的目标
    # 预言家相关
    checked_by_seer: bool = False  # 是否被预言家查验过
    # 女巫相关
    saved_by_witch: bool = False  # 是否被女巫救过
    poisoned_by_witch: bool = False  # 是否被女巫毒过
    witch_antidote_used: bool = False  # 女巫解药是否已使用
    witch_poison_used: bool = False  # 女巫毒药是否已使用
    # 猎人相关
    hunter_shot_used: bool = False  # 猎人是否已开枪
    # 死亡相关
    died_by: Optional[str] = None  # 死亡原因：'wolf', 'vote', 'poison', 'hunter'等

class GameRoom(BaseModel):
    room_id: str
    players: List[Player]
    phase: GamePhase = GamePhase.WAITING
    day_count: int = 0
    night_count: int = 0
    messages: List[Dict[str, str]]  # 公共消息
    private_messages: Dict[str, List[Dict[str, str]]]  # 私有消息 {user_id: [messages]}
    winner: Optional[str] = None  # "wolves" or "villagers"
    # 夜晚行动记录
    night_actions: Dict[str, Dict] = {}  # 记录夜晚行动 {role: {action_type: target}}
    current_night_phase: Optional[str] = None  # 当前夜晚子阶段（guard/wolf/seer/witch）
    eliminated_tonight: Optional[str] = None  # 今晚被击杀的玩家
    saved_tonight: Optional[str] = None  # 今晚被救的玩家
    # 时间限制相关
    phase_start_time: Optional[float] = None  # 阶段开始时间（Unix时间戳）
    phase_duration: Optional[int] = None  # 阶段持续时间（秒）
    can_speak: bool = False  # 是否允许发言



