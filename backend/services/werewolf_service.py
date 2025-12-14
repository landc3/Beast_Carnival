import random
import uuid
from typing import List, Dict, Optional
from models.game import GameRoom, Player, GamePhase, PlayerRole
from services.redis_service import redis_service
from services.ai_service import AIService

class WerewolfService:
    """狼人杀游戏服务"""
    
    # 12人标准配置：4狼+4神+4民
    ROLES = [
        PlayerRole.WOLF, PlayerRole.WOLF, PlayerRole.WOLF, PlayerRole.WOLF,  # 4狼人
        PlayerRole.SEER,  # 1预言家
        PlayerRole.WITCH,  # 1女巫
        PlayerRole.HUNTER,  # 1猎人
        PlayerRole.GUARD,  # 1守卫
        PlayerRole.VILLAGER, PlayerRole.VILLAGER, PlayerRole.VILLAGER, PlayerRole.VILLAGER  # 4平民
    ]
    
    async def create_room(self, room_id: Optional[str] = None) -> str:
        """创建房间"""
        if not room_id:
            room_id = str(uuid.uuid4())[:8]
        
        room = GameRoom(
            room_id=room_id,
            players=[],
            phase=GamePhase.WAITING,
            day_count=0,
            night_count=0,
            messages=[],
            private_messages={},
            winner=None
        )
        
        await redis_service.set_room_data(room_id, room.dict())
        return room_id
    
    async def join_room(self, room_id: str, user_id: str, username: str) -> bool:
        """加入房间"""
        room_data = await redis_service.get_room_data(room_id)
        if not room_data:
            return False
        
        room = GameRoom(**room_data)
        
        # 检查是否已加入
        if any(p.user_id == user_id for p in room.players):
            return True
        
        # 检查房间是否已满（最多12人）
        if len(room.players) >= 12:
            return False
        
        player = Player(user_id=user_id, username=username)
        room.players.append(player)
        
        await redis_service.set_room_data(room_id, room.dict())
        return True
    
    async def start_game(self, room_id: str) -> bool:
        """开始游戏"""
        room_data = await redis_service.get_room_data(room_id)
        if not room_data:
            return False
        
        room = GameRoom(**room_data)
        
        if len(room.players) < 4:  # 至少4人
            return False
        
        # 分配身份（使用12人标准配置，如果人数不足则按比例分配）
        if len(room.players) == 12:
            roles = self.ROLES.copy()
        else:
            # 按比例分配角色
            roles = []
            num_wolves = max(1, len(room.players) // 3)
            num_gods = max(1, len(room.players) // 3)
            num_villagers = len(room.players) - num_wolves - num_gods
            
            roles.extend([PlayerRole.WOLF] * num_wolves)
            roles.extend([PlayerRole.SEER, PlayerRole.WITCH, PlayerRole.HUNTER, PlayerRole.GUARD][:num_gods])
            roles.extend([PlayerRole.VILLAGER] * num_villagers)
            roles = roles[:len(room.players)]
        
        random.shuffle(roles)
        
        for i, player in enumerate(room.players):
            player.role = roles[i]
            player.alive = True
            player.voted = False
            # 初始化所有字段
            player.guarded = False
            player.guard_target = None
            player.last_guard_target = None
            player.checked_by_seer = False
            player.saved_by_witch = False
            player.poisoned_by_witch = False
            player.witch_antidote_used = False
            player.witch_poison_used = False
            player.hunter_shot_used = False
        
        room.phase = GamePhase.IDENTITY_ASSIGN
        room.night_actions = {}
        room.current_night_phase = None
        room.eliminated_tonight = None
        room.saved_tonight = None
        await redis_service.set_room_data(room_id, room.dict())
        
        # 发送身份信息（私有消息）
        for player in room.players:
            role_name = self._get_role_name(player.role)
            role_desc = self._get_role_description(player.role)
            
            # 如果是狼人，告知其他狼人
            if player.role == PlayerRole.WOLF:
                wolves = [p.username for p in room.players if p.role == PlayerRole.WOLF and p.user_id != player.user_id]
                if wolves:
                    await redis_service.add_private_message(
                        room_id, player.user_id,
                        {
                            "type": "identity",
                            "content": f"你的身份是：{role_name}\n\n{role_desc}\n\n你的狼人队友：{', '.join(wolves)}",
                            "role": role_name
                        }
                    )
                else:
                    await redis_service.add_private_message(
                        room_id, player.user_id,
                        {
                            "type": "identity",
                            "content": f"你的身份是：{role_name}\n\n{role_desc}",
                            "role": role_name
                        }
                    )
            else:
                await redis_service.add_private_message(
                    room_id, player.user_id,
                    {
                        "type": "identity",
                        "content": f"你的身份是：{role_name}\n\n{role_desc}",
                        "role": role_name
                    }
                )
        
        # AI主持人宣布开始
        await self._ai_announce(room_id, "游戏开始！身份已分配，请查看你的身份信息。")
        
        # 自动进入第一夜
        await self._start_night_phase(room_id)
        
        return True
    
    async def get_room(self, room_id: str) -> Optional[GameRoom]:
        """获取房间信息"""
        room_data = await redis_service.get_room_data(room_id)
        if room_data:
            return GameRoom(**room_data)
        return None
    
    async def player_action(self, room_id: str, user_id: str, action_type: str, action_data: Optional[Dict] = None) -> Dict:
        """玩家行动"""
        room = await self.get_room(room_id)
        if not room:
            return {"error": "房间不存在"}
        
        player = next((p for p in room.players if p.user_id == user_id), None)
        if not player or not player.alive:
            return {"error": "玩家不存在或已死亡"}
        
        if action_data is None:
            action_data = {}
        
        # 根据阶段处理行动
        if room.phase == GamePhase.NIGHT:
            return await self._handle_night_action(room, player, action_type, action_data)
        elif room.phase == GamePhase.DAY:
            return await self._handle_day_action(room, player, action_type, action_data)
        elif room.phase == GamePhase.VOTING:
            return await self._handle_voting(room, player, action_data.get("target"))
        elif room.phase == GamePhase.ELIMINATION:
            # 处理淘汰阶段的技能（如猎人开枪）
            return await self._handle_elimination_action(room, player, action_type, action_data)
        
        return {"error": "当前阶段不允许此操作"}
    
    async def _handle_night_action(self, room: GameRoom, player: Player, action_type: str, action_data: Dict) -> Dict:
        """处理夜晚行动"""
        target = action_data.get("target")
        
        if action_type == "guard_action":
            return await self._handle_guard_action(room, player, target)
        elif action_type == "wolf_action":
            return await self._handle_wolf_action(room, player, target)
        elif action_type == "seer_action":
            return await self._handle_seer_action(room, player, target)
        elif action_type == "witch_action":
            return await self._handle_witch_action(room, player, action_data)
        else:
            return {"error": "无效的夜晚行动类型"}
    
    async def _handle_day_action(self, room: GameRoom, player: Player, action_type: str, action_data: Dict):
        """处理白天发言"""
        if action_type == "speech":
            content = action_data.get("content", "")
            message = {
                "type": "speech",
                "user_id": player.user_id,
                "username": player.username,
                "content": content,
                "timestamp": str(uuid.uuid4())
            }
            await redis_service.add_room_message(room.room_id, message)
            return {"success": True}
        return {"error": "无效的白天行动类型"}
    
    async def _handle_voting(self, room: GameRoom, player: Player, target: Optional[str]):
        """处理投票"""
        if not target:
            return {"error": "请选择投票目标"}
        
        player.voted = True
        player.vote_target = target
        
        await redis_service.set_room_data(room.room_id, room.dict())
        
        # 检查是否所有人都投票了
        alive_players = [p for p in room.players if p.alive]
        if all(p.voted for p in alive_players):
            await self._process_voting_result(room)
        
        return {"success": True}
    
    async def _process_voting_result(self, room: GameRoom):
        """处理投票结果"""
        votes = {}
        for player in room.players:
            if player.alive and player.vote_target:
                votes[player.vote_target] = votes.get(player.vote_target, 0) + 1
        
        if votes:
            eliminated = max(votes.items(), key=lambda x: x[1])[0]
            eliminated_player = next((p for p in room.players if p.user_id == eliminated), None)
            if eliminated_player:
                eliminated_player.alive = False
                await self._ai_announce(room.room_id, f"{eliminated_player.username}被投票出局！")
        
        # 检查游戏是否结束
        await self._check_game_over(room)
    
    async def _check_game_over(self, room: GameRoom):
        """检查游戏是否结束"""
        alive_players = [p for p in room.players if p.alive]
        wolves = [p for p in alive_players if p.role == PlayerRole.WOLF]
        villagers = [p for p in alive_players if p.role != PlayerRole.WOLF]
        
        if len(wolves) == 0:
            room.winner = "villagers"
            room.phase = GamePhase.GAME_OVER
            await self._ai_announce(room.room_id, "游戏结束！好人阵营获胜！")
        elif len(wolves) >= len(villagers):
            room.winner = "wolves"
            room.phase = GamePhase.GAME_OVER
            await self._ai_announce(room.room_id, "游戏结束！狼人阵营获胜！")
        
        await redis_service.set_room_data(room.room_id, room.dict())
    
    async def _ai_announce(self, room_id: str, message: str):
        """AI主持人宣布"""
        msg = {
            "type": "system",
            "content": message,
            "timestamp": str(uuid.uuid4())
        }
        await redis_service.add_room_message(room_id, msg)
    
    def _get_role_name(self, role: PlayerRole) -> str:
        """获取角色名称"""
        names = {
            PlayerRole.WOLF: "狼人",
            PlayerRole.VILLAGER: "平民",
            PlayerRole.SEER: "预言家",
            PlayerRole.WITCH: "女巫",
            PlayerRole.HUNTER: "猎人"
        }
        return names.get(role, "未知")

werewolf_service = WerewolfService()

