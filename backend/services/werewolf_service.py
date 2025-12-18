import random
import uuid
import time
import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

# 添加 backend 目录到 Python 路径，以便正确导入模块
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.game import GameRoom, Player, GamePhase, PlayerRole
from services.redis_service import redis_service
from services.ai_service import AIService

# 配置日志 - 只使用根 logger，避免重复输出
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# 不添加自己的 handler，只向上传播到根 logger，避免重复
logger.propagate = True

class WerewolfService:
    """狼人杀游戏服务"""
    
    def __init__(self):
        self.broadcast_callback = None
        self.send_private_message_callback = None
        self.processing_night_result = set()  # 正在处理夜晚结算的房间ID集合，防止重复调用
    
    def set_broadcast_callback(self, callback):
        """设置广播回调函数"""
        self.broadcast_callback = callback
    
    def set_send_private_message_callback(self, callback):
        """设置发送私有消息回调函数"""
        self.send_private_message_callback = callback
    
    # 12人标准配置：4狼+4神+4民
    ROLES = [
        PlayerRole.WOLF, PlayerRole.WOLF, PlayerRole.WOLF, PlayerRole.WOLF,  # 4狼人
        PlayerRole.SEER,  # 1预言家
        PlayerRole.WITCH,  # 1女巫
        PlayerRole.HUNTER,  # 1猎人
        PlayerRole.GUARD,  # 1守卫
        PlayerRole.VILLAGER, PlayerRole.VILLAGER, PlayerRole.VILLAGER, PlayerRole.VILLAGER  # 4平民
    ]
    
    # 各阶段时间限制（秒）
    PHASE_DURATIONS = {
        GamePhase.WAITING: None,  # 等待阶段无时间限制
        GamePhase.IDENTITY_ASSIGN: 10,  # 身份分配阶段10秒
        GamePhase.NIGHT: 60,  # 夜晚阶段60秒
        GamePhase.DAY: 180,  # 白天讨论阶段180秒（3分钟）
        GamePhase.VOTING: 30,  # 投票阶段30秒
        GamePhase.ELIMINATION: 20,  # 淘汰阶段20秒
        GamePhase.GAME_OVER: None  # 游戏结束无时间限制
    }
    
    # 各阶段是否允许发言
    PHASE_CAN_SPEAK = {
        GamePhase.WAITING: False,
        GamePhase.IDENTITY_ASSIGN: False,
        GamePhase.NIGHT: False,
        GamePhase.DAY: True,  # 白天阶段允许发言
        GamePhase.VOTING: False,
        GamePhase.ELIMINATION: False,
        GamePhase.GAME_OVER: False
    }
    
    async def create_room(self, room_id: Optional[str] = None) -> str:
        """创建房间"""
        try:
            logger.info(f"【创建房间】开始创建房间")
            
            if not room_id:
                room_id = str(uuid.uuid4())[:8]
            
            logger.info(f"【创建房间】生成房间ID: {room_id}")
            
            # 创建房间对象，确保所有字段都有默认值
            room = GameRoom(
                room_id=room_id,
                players=[],
                phase=GamePhase.WAITING,
                day_count=0,
                night_count=0,
                messages=[],
                private_messages={},
                winner=None,
                night_actions={},
                current_night_phase=None,
                eliminated_tonight=None,
                saved_tonight=None,
                phase_start_time=None,
                phase_duration=None,
                can_speak=False
            )
            
            logger.info(f"【创建房间】房间对象创建成功，准备序列化")
            
            # 使用 mode='json' 确保所有值都是 JSON 可序列化的
            # 如果失败，尝试使用默认模式并手动处理
            try:
                logger.info(f"【创建房间】尝试使用 mode='json' 序列化")
                room_data = room.model_dump(mode='json')
                logger.info(f"【创建房间】房间数据序列化成功 (mode='json')")
            except Exception as e:
                logger.warning(f"【创建房间】mode='json' 序列化失败，尝试默认模式: {e}")
                try:
                    # 使用默认模式，然后手动处理可能的问题字段
                    room_data = room.model_dump()
                    # 确保所有值都是 JSON 可序列化的
                    import json as json_lib
                    # 测试是否可以序列化
                    json_lib.dumps(room_data, ensure_ascii=False, default=str)
                    logger.info(f"【创建房间】房间数据序列化成功 (默认模式)")
                except Exception as e2:
                    logger.error(f"【创建房间错误】序列化失败: {e2}", exc_info=True)
                    raise Exception(f"房间数据序列化失败: {str(e2)}") from e2
            
            # 保存到Redis
            try:
                logger.info(f"【创建房间】准备保存到Redis，房间ID: {room_id}")
                await redis_service.set_room_data(room_id, room_data)
                logger.info(f"【创建房间】Redis保存成功")
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                logger.error(f"【创建房间错误】Redis保存失败: {error_type}: {error_msg}", exc_info=True)
                raise Exception(f"保存房间到Redis失败: {error_type}: {error_msg}") from e
            
            logger.info(f"【创建房间】房间创建成功 - 房间ID: {room_id}")
            
            return room_id
        except Exception as e:
            logger.error(f"【创建房间错误】创建房间失败: {e}", exc_info=True)
            raise
    
    async def join_room(self, room_id: str, user_id: str, username: str) -> bool:
        """加入房间"""
        try:
            logger.info(f"【加入房间】开始 - 房间 {room_id}, 玩家 {username} (ID: {user_id})")
            
            room_data = await redis_service.get_room_data(room_id)
            if not room_data:
                logger.warning(f"【加入房间失败】房间 {room_id} 不存在")
                return False
            
            logger.info(f"【加入房间】从Redis获取房间数据成功")
            
            room = GameRoom(**room_data)
            
            logger.info(f"【加入房间】房间对象创建成功，当前玩家数: {len(room.players)}")
            
            # 检查是否已加入
            if any(p.user_id == user_id for p in room.players):
                logger.info(f"【玩家已存在】房间 {room_id} - 玩家 {username} (ID: {user_id}) 已在房间中")
                return True
            
            # 检查房间是否已满（最多12人）
            if len(room.players) >= 12:
                logger.warning(f"【加入房间失败】房间 {room_id} 已满（当前 {len(room.players)}/12 人）")
                return False
            
            logger.info(f"【加入房间】创建玩家对象")
            
            player = Player(user_id=user_id, username=username, is_ai=False)
            room.players.append(player)
            
            logger.info(f"【加入房间】保存房间数据到Redis")
            
            await redis_service.set_room_data(room_id, room.model_dump())
            
            # 打印玩家加入日志
            logger.info(f"\n{'='*60}")
            logger.info(f"【玩家加入游戏】房间 {room_id}")
            logger.info(f"  玩家: {username} (ID: {user_id})")
            logger.info(f"  当前房间人数: {len(room.players)}/12")
            logger.info(f"{'='*60}")
            
            return True
        except Exception as e:
            logger.error(f"【加入房间错误】加入房间异常 - 房间 {room_id}, 玩家 {username} (ID: {user_id}), 错误: {e}", exc_info=True)
            raise
    
    async def add_ai_player(self, room_id: str) -> bool:
        """添加AI玩家"""
        room_data = await redis_service.get_room_data(room_id)
        if not room_data:
            return False
        
        room = GameRoom(**room_data)
        
        # 检查房间是否已满（最多12人）
        if len(room.players) >= 12:
            return False
        
        # 检查游戏是否已开始
        if room.phase != GamePhase.WAITING:
            return False
        
        # 生成AI玩家名称，根据玩家在列表中的位置生成（确保与卡片数字对应）
        # 如果当前有N个玩家，新添加的AI玩家应该是第N+1个玩家，名称应该是 "AI玩家{N+1}"
        player_number = len(room.players) + 1
        ai_name = f"AI玩家{player_number}"
        
        # 创建AI玩家，使用四位数字格式的ID
        ai_user_id = f"ai_{player_number:04d}"
        ai_player = Player(user_id=ai_user_id, username=ai_name, is_ai=True)
        room.players.append(ai_player)
        
        await redis_service.set_room_data(room_id, room.model_dump())
        
        # 打印AI玩家加入日志
        logger.info(f"【AI玩家加入】房间 {room_id} - {ai_name} (ID: {ai_user_id})，当前房间人数: {len(room.players)}/12")
        
        # 广播房间更新
        await self._ai_announce(room_id, f"{ai_name} 加入了游戏")
        
        return True
    
    async def auto_fill_ai_players(self, room_id: str, target_count: int = 7) -> int:
        """自动填充AI玩家到目标人数"""
        room_data = await redis_service.get_room_data(room_id)
        if not room_data:
            return 0
        
        room = GameRoom(**room_data)
        
        # 检查游戏是否已开始
        if room.phase != GamePhase.WAITING:
            return 0
        
        current_count = len(room.players)
        if current_count >= target_count or current_count >= 12:
            return 0
        
        added_count = 0
        while current_count < target_count and current_count < 12:
            success = await self.add_ai_player(room_id)
            if success:
                added_count += 1
                current_count += 1
            else:
                break
        
        return added_count
    
    async def start_game(self, room_id: str) -> bool:
        """开始游戏"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"【游戏开始】房间 {room_id}")
            logger.info(f"{'='*60}")
            
            room_data = await redis_service.get_room_data(room_id)
            if not room_data:
                logger.error(f"错误: 房间 {room_id} 不存在")
                return False
            
            room = GameRoom(**room_data)
            logger.info(f"房间 {room_id} - 玩家数量: {len(room.players)}")
            
            if len(room.players) < 4:  # 至少4人
                logger.error(f"错误: 房间 {room_id} 玩家数量不足，当前: {len(room.players)}")
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
            
            logger.info(f"开始分配身份 - 房间 {room_id}")
            logger.info(f"\n【身份分配】房间 {room_id}")
            role_distribution = {}
            for i, player in enumerate(room.players):
                player.role = roles[i]
                player.alive = True
                player.voted = False
                role_name = self._get_role_name(player.role)
                role_distribution[role_name] = role_distribution.get(role_name, 0) + 1
                logger.info(f"  - {player.username} (ID: {player.user_id}) -> {role_name}")
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
            
            logger.info(f"身份分配完成 - 房间 {room_id}: {role_distribution}")
            logger.info(f"{'='*60}")
            
            room.phase = GamePhase.IDENTITY_ASSIGN
            room.night_actions = {}
            room.current_night_phase = None
            room.eliminated_tonight = None
            room.saved_tonight = None
            await self._set_phase_time(room)
            
            # 发送身份信息（私有消息）
            import json
            for player in room.players:
                role_name = self._get_role_name(player.role)
                role_desc = self._get_role_description(player.role)
                
                # 构建身份消息
                if player.role == PlayerRole.WOLF:
                    wolves = [p.username for p in room.players if p.role == PlayerRole.WOLF and p.user_id != player.user_id]
                    if wolves:
                        identity_msg = {
                            "type": "identity",
                            "content": f"你的身份是：{role_name}\n\n{role_desc}\n\n你的狼人队友：{', '.join(wolves)}",
                            "role": role_name
                        }
                    else:
                        identity_msg = {
                            "type": "identity",
                            "content": f"你的身份是：{role_name}\n\n{role_desc}",
                            "role": role_name
                        }
                else:
                    identity_msg = {
                        "type": "identity",
                        "content": f"你的身份是：{role_name}\n\n{role_desc}",
                        "role": role_name
                    }
                
                # 保存到 Redis
                await redis_service.add_private_message(room_id, player.user_id, identity_msg)
                
                # 立即通过 WebSocket 发送私有消息（如果回调函数已设置）
                if self.send_private_message_callback:
                    try:
                        await self.send_private_message_callback(
                            room_id, 
                            player.user_id, 
                            json.dumps({
                                "type": "private_message",
                                "content": identity_msg
                            })
                        )
                    except Exception as e:
                        logger.warning(f"发送私有消息失败 (房间 {room_id}, 用户 {player.user_id}): {e}")
            
            # 保存房间状态
            await redis_service.set_room_data(room_id, room.model_dump())
            
            # AI主持人宣布开始
            await self._ai_announce(room_id, "游戏开始！身份已分配，请查看你的身份信息。")
            
            # 等待一下，确保消息已发送
            import asyncio
            await asyncio.sleep(0.3)
            
            # 不在这里进入夜晚阶段，而是在后台任务中处理
            # 这样可以让 start_game 快速返回，避免超时
            
            return True
        except Exception as e:
            logger.error(f"开始游戏失败 (房间 {room_id}): {e}", exc_info=True)
            return False
    
    async def get_room(self, room_id: str, check_timeout: bool = True) -> Optional[GameRoom]:
        """获取房间信息
        
        Args:
            room_id: 房间ID
            check_timeout: 是否检查阶段超时，默认为True。设置为False可以避免递归调用
        """
        room_data = await redis_service.get_room_data(room_id)
        if room_data:
            room = GameRoom(**room_data)
            # 检查阶段是否过期，如果过期则自动进入下一阶段
            if check_timeout:
                await self._check_phase_timeout(room)
                # 重新获取房间数据，因为 _check_phase_timeout 可能已经更新了房间状态
                room_data = await redis_service.get_room_data(room_id)
                if room_data:
                    return GameRoom(**room_data)
            return room
        return None
    
    async def _set_phase_time(self, room: GameRoom):
        """设置阶段开始时间和持续时间"""
        room.phase_start_time = time.time()
        room.phase_duration = self.PHASE_DURATIONS.get(room.phase)
        room.can_speak = self.PHASE_CAN_SPEAK.get(room.phase, False)
        await redis_service.set_room_data(room.room_id, room.model_dump())
    
    async def _check_phase_timeout(self, room: GameRoom):
        """检查阶段是否超时，如果超时则自动进入下一阶段"""
        if room.phase_start_time is None or room.phase_duration is None:
            return
        
        elapsed = time.time() - room.phase_start_time
        if elapsed >= room.phase_duration:
            # 阶段超时，根据当前阶段进入下一阶段
            if room.phase == GamePhase.DAY:
                # 白天阶段超时，进入投票阶段
                # 重要：在进入投票阶段时，必须确保不会更新任何玩家的死亡状态
                # 只有投票阶段结束后（通过_process_voting_result）才会更新死亡状态
                
                # 重新获取最新的房间数据，确保状态一致性
                room_data = await redis_service.get_room_data(room.room_id)
                if room_data:
                    room = GameRoom(**room_data)
                
                # 关键修复：在投票阶段开始时，明确保护所有存活玩家的alive状态
                # 记录进入投票阶段前的存活状态，确保不会在投票阶段开始时错误地更新死亡状态
                # 注意：这里不应该修改任何玩家的alive状态，只应该重置投票状态
                
                # 设置投票阶段
                room.phase = GamePhase.VOTING
                
                # 重置所有玩家的投票状态（只重置存活玩家的投票状态）
                # 重要：这里只重置投票状态，不修改alive状态
                for p in room.players:
                    if p.alive:
                        p.voted = False
                        p.vote_target = None
                    # 注意：已死亡的玩家不应该有投票状态，但为了安全，也重置
                    else:
                        p.voted = False
                        p.vote_target = None
                
                # 安全检查：确保所有存活玩家都可以投票
                alive_players = [p for p in room.players if p.alive]
                logger.info(f"【投票阶段开始】房间 {room.room_id} - 存活玩家数: {len(alive_players)}")
                for p in alive_players:
                    logger.info(f"  - {p.username} (ID: {p.user_id}, 角色: {self._get_role_name(p.role) if p.role else '未知'}, alive: {p.alive})")
                
                # 再次确认：在投票阶段开始时，不应该有任何玩家的alive状态被修改
                # 如果从Redis获取的数据中包含了错误的死亡状态，我们需要修复它
                # 但是，我们不应该在投票阶段开始时修改任何玩家的alive状态
                # 因为只有投票阶段结束后才会更新死亡状态
                
                # 保存房间状态（不更新任何死亡状态）
                await self._set_phase_time(room)
                
                # 广播房间状态更新（确保不会更新任何死亡状态）
                if self.broadcast_callback:
                    import json
                    await self.broadcast_callback(json.dumps({
                        "type": "room_update",
                        "room": room.model_dump()
                    }), f"werewolf_{room.room_id}")
                
                await self._ai_announce(room.room_id, "讨论时间结束，进入投票阶段。")
                # 触发AI玩家自动投票
                await self._trigger_ai_voting(room)
            elif room.phase == GamePhase.VOTING:
                # 投票阶段超时，处理投票结果
                # 重新获取最新的房间数据，确保状态一致性
                room_data = await redis_service.get_room_data(room.room_id)
                if room_data:
                    current_room = GameRoom(**room_data)
                    # 确保当前仍处于投票阶段
                    if current_room.phase == GamePhase.VOTING:
                        await self._process_voting_result(current_room)
            elif room.phase == GamePhase.NIGHT:
                # 夜晚阶段超时，结算夜晚结果并进入白天阶段
                # 重新获取最新的房间状态，确保状态一致性
                room_data = await redis_service.get_room_data(room.room_id)
                if room_data:
                    current_room = GameRoom(**room_data)
                    await self._process_night_result(current_room)
            elif room.phase == GamePhase.IDENTITY_ASSIGN:
                # 身份分配阶段超时，进入夜晚或白天
                if room.night_count == 0:
                    room.phase = GamePhase.NIGHT
                    room.night_count = 1
                else:
                    room.phase = GamePhase.DAY
                    room.day_count = 1
                await self._set_phase_time(room)
            # 注意：不需要在这里统一保存，因为每个分支都已经保存了状态
            # DAY -> VOTING: _set_phase_time 已保存
            # VOTING: _process_voting_result 已保存
            # NIGHT: _process_night_result -> _start_day_phase -> _set_phase_time 已保存
            # IDENTITY_ASSIGN: _set_phase_time 已保存
    
    def _is_phase_expired(self, room: GameRoom) -> bool:
        """检查当前阶段是否已过期"""
        if room.phase_start_time is None or room.phase_duration is None:
            return False
        elapsed = time.time() - room.phase_start_time
        return elapsed >= room.phase_duration
    
    async def player_action(self, room_id: str, user_id: str, action_type: str, action_data: Optional[Dict] = None) -> Dict:
        """玩家行动"""
        logger.info(f"【玩家行动接收】房间 {room_id} - 玩家ID: {user_id}, 行动类型: {action_type}, 行动数据: {action_data}")
        
        room = await self.get_room(room_id)
        if not room:
            logger.warning(f"【玩家行动】房间 {room_id} 不存在")
            return {"error": "房间不存在"}
        
        player = next((p for p in room.players if p.user_id == user_id), None)
        if not player:
            logger.warning(f"【玩家行动】房间 {room_id} - 玩家ID {user_id} 不存在")
            return {"error": "玩家不存在"}
        
        logger.info(f"【玩家行动】房间 {room_id} - 玩家 {player.username} (ID: {user_id}, 角色: {self._get_role_name(player.role) if player.role else '未知'}, 存活: {player.alive}), 当前阶段: {room.phase}")
        
        # 遗言可以在任何阶段提交（只要玩家已死亡）
        if action_type == "last_words":
            logger.info(f"【遗言】房间 {room_id} - 玩家 {player.username} 提交遗言")
            return await self._handle_last_words_action(room, player, action_data)
        
        # 其他行动需要玩家存活
        if not player.alive:
            logger.warning(f"【玩家行动】房间 {room_id} - 玩家 {player.username} 已死亡，无法执行行动")
            return {"error": "玩家已死亡"}
        
        if action_data is None:
            action_data = {}
        
        # 根据阶段处理行动
        if room.phase == GamePhase.NIGHT:
            return await self._handle_night_action(room, player, action_type, action_data)
        elif room.phase == GamePhase.DAY:
            return await self._handle_day_action(room, player, action_type, action_data)
        elif room.phase == GamePhase.VOTING:
            logger.info(f"【投票行动】房间 {room_id} - 玩家 {player.username} 投票给: {action_data.get('target')}")
            return await self._handle_voting(room, player, action_data.get("target"))
        elif room.phase == GamePhase.ELIMINATION:
            # 处理淘汰阶段的技能（如猎人开枪）
            logger.info(f"【淘汰阶段行动】房间 {room_id} - 玩家 {player.username} 执行行动: {action_type}")
            return await self._handle_elimination_action(room, player, action_type, action_data)
        
        logger.warning(f"【玩家行动】房间 {room_id} - 当前阶段 {room.phase} 不允许操作 {action_type}")
        return {"error": "当前阶段不允许此操作"}
    
    async def _handle_night_action(self, room: GameRoom, player: Player, action_type: str, action_data: Dict) -> Dict:
        """处理夜晚行动"""
        target = action_data.get("target")
        witch_action = action_data.get("witch_action")
        
        # 强制刷新输出，确保日志立即显示
        logger.info(f"【夜晚行动接收】房间 {room.room_id} - 玩家 {player.username} (ID: {player.user_id}, 角色: {self._get_role_name(player.role) if player.role else '未知'}) 执行行动: {action_type}, 目标: {target}, 女巫行动: {witch_action}")
        
        result = None
        # 支持两种格式：guard/guard_action, wolf/wolf_action等
        if action_type in ["guard", "guard_action"]:
            result = await self._handle_guard_action(room, player, target)
        elif action_type in ["wolf", "wolf_action"]:
            result = await self._handle_wolf_action(room, player, target)
        elif action_type in ["seer", "seer_action"]:
            result = await self._handle_seer_action(room, player, target)
        elif action_type in ["witch", "witch_action"]:
            # 女巫行动需要特殊处理，从action_data中获取witch_action
            witch_action_data = {
                "action_type": action_data.get("witch_action"),  # antidote/poison/none
                "target": target
            }
            result = await self._handle_witch_action(room, player, witch_action_data)
        else:
            logger.warning(f"【夜晚行动】房间 {room.room_id} - 无效的夜晚行动类型: {action_type}")
            return {"error": "无效的夜晚行动类型"}
        
        if result.get("success"):
            logger.info(f"【夜晚行动成功】房间 {room.room_id} - 玩家 {player.username} 行动成功: {result.get('message', '')}")
        elif result.get("error"):
            logger.warning(f"【夜晚行动失败】房间 {room.room_id} - 玩家 {player.username} 行动失败: {result.get('error', '')}")
        
        # 检查是否所有夜晚行动都完成了
        if result.get("success"):
            await self._check_night_actions_complete(room)
        
        return result
    
    async def _check_night_actions_complete(self, room: GameRoom):
        """检查夜晚行动是否全部完成，如果完成则结算"""
        # 重新获取最新的房间状态，确保状态一致性
        room_data = await redis_service.get_room_data(room.room_id)
        if not room_data:
            return
        current_room = GameRoom(**room_data)
        
        # 确保当前阶段是夜晚，并且已经处理过所有子阶段
        # 如果current_night_phase不是None，说明还在处理某个子阶段，不应该结算
        if current_room.current_night_phase is not None:
            return  # 还在处理某个夜晚子阶段，等待完成
        
        # 检查守卫
        guard = next((p for p in current_room.players if p.role == PlayerRole.GUARD and p.alive), None)
        if guard and "guard" not in current_room.night_actions:
            return  # 守卫还未行动
        
        # 检查狼人（需要所有狼人都投票）
        wolves = [p for p in current_room.players if p.role == PlayerRole.WOLF and p.alive]
        if wolves:
            if "wolf" not in current_room.night_actions or len(current_room.night_actions["wolf"].get("votes", {})) < len(wolves):
                return  # 狼人还未全部投票
        
        # 检查预言家
        seer = next((p for p in current_room.players if p.role == PlayerRole.SEER and p.alive), None)
        if seer and "seer" not in current_room.night_actions:
            return  # 预言家还未行动
        
        # 检查女巫（女巫可以选择不使用任何药水，所以只要 witch 在 night_actions 中就算完成）
        witch = next((p for p in current_room.players if p.role == PlayerRole.WITCH and p.alive), None)
        if witch and "witch" not in current_room.night_actions:
            return  # 女巫还未行动
        # 如果女巫存在，检查是否有行动记录（包括"none"）
        if witch and "witch" in current_room.night_actions:
            witch_action = current_room.night_actions["witch"]
            # 如果既没有使用解药，也没有使用毒药，也没有标记为"none"，说明还未行动
            if (not witch_action.get("antidote_used") and 
                not witch_action.get("poison_used") and 
                witch_action.get("action") != "none"):
                return  # 女巫还未行动
        
        # 所有行动都完成了，结算夜晚结果
        await self._process_night_result(current_room)
    
    async def _handle_day_action(self, room: GameRoom, player: Player, action_type: str, action_data: Dict):
        """处理白天发言"""
        if action_type == "speech" or action_type == "message":
            # 检查玩家是否存活
            if not player.alive:
                return {"error": "玩家已死亡，无法发言"}
            
            # 检查是否允许发言
            if not room.can_speak:
                return {"error": "当前阶段不允许发言"}
            
            # 检查阶段是否已过期
            if self._is_phase_expired(room):
                await self._check_phase_timeout(room)
                return {"error": "发言时间已结束"}
            
            content = action_data.get("content", "")
            message = {
                "type": "speech",
                "user_id": player.user_id,
                "username": player.username,
                "content": content,
                "timestamp": str(uuid.uuid4())
            }
            await redis_service.add_room_message(room.room_id, message)
            
            # 触发AI玩家自动回复（不在这里等待，让它在后台运行）
            if room.phase == GamePhase.DAY:
                # 注意：这里不等待AI回复完成，让它在后台异步执行
                # 广播会在AI回复生成后通过回调处理
                pass
            
            return {"success": True}
        return {"error": "无效的白天行动类型"}
    
    async def _handle_voting(self, room: GameRoom, player: Player, target: Optional[str]):
        """处理投票"""
        # 检查玩家是否存活
        if not player.alive:
            logger.warning(f"【投票】房间 {room.room_id} - 玩家 {player.username} 已死亡，无法投票")
            return {"error": "玩家已死亡，无法投票"}
        
        if not target:
            logger.warning(f"【投票】房间 {room.room_id} - 玩家 {player.username} 未选择投票目标")
            return {"error": "请选择投票目标"}
        
        # 检查目标玩家是否存在且存活
        target_player = next((p for p in room.players if p.user_id == target), None)
        if not target_player:
            logger.warning(f"【投票】房间 {room.room_id} - 目标玩家不存在: {target}")
            return {"error": "目标玩家不存在"}
        if not target_player.alive:
            logger.warning(f"【投票】房间 {room.room_id} - 目标玩家 {target_player.username} 已死亡，无法投票")
            return {"error": "目标玩家已死亡，无法投票"}
        
        player.voted = True
        player.vote_target = target
        
        logger.info(f"【投票】房间 {room.room_id} - 玩家 {player.username} (ID: {player.user_id}, 角色: {self._get_role_name(player.role) if player.role else '未知'}) 投票给: {target_player.username} (ID: {target})")
        
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 注意：不在所有人投票后立即处理投票结果
        # 投票结果只应该在投票阶段结束时处理（通过超时机制）
        # 这样可以确保所有玩家都有机会投票，并且在投票阶段结束前不会标记任何玩家为死亡
        # 如果所有人都投票了，投票阶段会在超时后自动处理结果
        
        return {"success": True}
    
    async def _check_game_over(self, room: GameRoom):
        """检查游戏是否结束"""
        alive_players = [p for p in room.players if p.alive]
        wolves = [p for p in alive_players if p.role == PlayerRole.WOLF]
        villagers = [p for p in alive_players if p.role != PlayerRole.WOLF]
        
        if len(wolves) == 0:
            room.winner = "villagers"
            room.phase = GamePhase.GAME_OVER
            await self._set_phase_time(room)
            await self._ai_announce(room.room_id, "游戏结束！好人阵营获胜！")
        elif len(wolves) >= len(villagers):
            room.winner = "wolves"
            room.phase = GamePhase.GAME_OVER
            await self._set_phase_time(room)
            await self._ai_announce(room.room_id, "游戏结束！狼人阵营获胜！")
        
        await redis_service.set_room_data(room.room_id, room.model_dump())
    
    async def _ai_announce(self, room_id: str, message: str, phase_popup: Optional[str] = None, broadcast_callback=None):
        """AI主持人宣布
        
        Args:
            room_id: 房间ID
            message: 消息内容
            phase_popup: 阶段弹窗类型 ("night_start", "night_end", "day_start", "day_end")
            broadcast_callback: 可选的广播回调函数，用于通过WebSocket广播消息
        """
        # 检查是否最近发送过相同的消息（防止重复发送）
        recent_messages = await redis_service.get_room_messages(room_id)
        if recent_messages:
            # 检查最近3条消息中是否有相同的内容
            for recent_msg in recent_messages[-3:]:
                if (recent_msg.get("type") == "system" and 
                    recent_msg.get("username") == "AI主持人" and
                    recent_msg.get("content") == message and
                    recent_msg.get("phase_popup") == phase_popup):
                    logger.debug(f"跳过重复消息: {message} (房间 {room_id})")
                    return
        
        msg = {
            "type": "system",
            "content": message,
            "timestamp": str(uuid.uuid4()),
            "username": "AI主持人"
        }
        if phase_popup:
            msg["phase_popup"] = phase_popup
        
        await redis_service.add_room_message(room_id, msg)
        
        # 如果有广播回调（优先使用传入的，否则使用类级别的）
        callback = broadcast_callback or self.broadcast_callback
        if callback:
            import json
            await callback(json.dumps({
                "type": "public_message",
                "content": msg
            }), f"werewolf_{room_id}")
    
    async def _wait_for_phase_completion(self, room: GameRoom, phase: str, timeout: int = 30):
        """等待阶段完成
        
        Args:
            room: 游戏房间
            phase: 阶段名称 ("guard", "wolf", "seer", "witch")
            timeout: 超时时间（秒）
        """
        import asyncio
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 重新获取房间状态
            room_data = await redis_service.get_room_data(room.room_id)
            if not room_data:
                break
            current_room = GameRoom(**room_data)
            
            # 检查阶段是否完成
            if phase == "guard":
                guard = next((p for p in current_room.players if p.role == PlayerRole.GUARD and p.alive), None)
                if not guard or "guard" in current_room.night_actions:
                    return
            elif phase == "wolf":
                wolves = [p for p in current_room.players if p.role == PlayerRole.WOLF and p.alive]
                if not wolves or ("wolf" in current_room.night_actions and 
                                 len(current_room.night_actions["wolf"].get("votes", {})) >= len(wolves)):
                    return
            elif phase == "seer":
                seer = next((p for p in current_room.players if p.role == PlayerRole.SEER and p.alive), None)
                if not seer or "seer" in current_room.night_actions:
                    return
            elif phase == "witch":
                witch = next((p for p in current_room.players if p.role == PlayerRole.WITCH and p.alive), None)
                if not witch:
                    return
                if "witch" in current_room.night_actions:
                    witch_action = current_room.night_actions["witch"]
                    if (witch_action.get("antidote_used") or 
                        witch_action.get("poison_used") or 
                        witch_action.get("action") == "none"):
                        return
            
            await asyncio.sleep(0.5)  # 每0.5秒检查一次
    
    async def _trigger_ai_night_actions(self, room: GameRoom, phase: str):
        """触发AI玩家自动行动
        
        Args:
            room: 游戏房间
            phase: 阶段名称 ("guard", "wolf", "seer", "witch")
        """
        import asyncio
        
        if phase == "guard":
            guard = next((p for p in room.players if p.role == PlayerRole.GUARD and p.alive), None)
            if guard and guard.is_ai:
                # AI守卫自动选择守护目标
                await asyncio.sleep(1)  # 延迟1秒，模拟思考
                alive_players = [p for p in room.players if p.alive]
                # 排除上一晚守护的目标
                cannot_guard = guard.last_guard_target
                available_targets = [p for p in alive_players if p.user_id != cannot_guard]
                if available_targets:
                    target = random.choice(available_targets)
                    await self._handle_guard_action(room, guard, target.user_id)
        
        elif phase == "wolf":
            # 获取所有狼人（包括AI和人类）
            all_wolves = [p for p in room.players if p.role == PlayerRole.WOLF and p.alive]
            ai_wolves = [p for p in all_wolves if p.is_ai]
            human_wolves = [p for p in all_wolves if not p.is_ai]
            
            if ai_wolves:
                await asyncio.sleep(2)  # 延迟2秒，等待人类狼人投票
                
                # 检查是否有其他狼人已经投票
                if "wolf" in room.night_actions and room.night_actions["wolf"].get("votes"):
                    votes = room.night_actions["wolf"]["votes"]
                    # 统计已投票的目标
                    vote_counts = {}
                    for vote_target in votes.values():
                        vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
                    
                    # 如果有投票，AI狼人跟随多数投票
                    if vote_counts:
                        # 选择得票最多的目标
                        most_voted_target = max(vote_counts.items(), key=lambda x: x[1])[0]
                        # 所有AI狼人跟随投票
                        for wolf in ai_wolves:
                            if wolf.user_id not in votes:  # 只处理未投票的AI狼人
                                await self._handle_wolf_action(room, wolf, most_voted_target)
                    else:
                        # 如果还没有投票，AI狼人随机选择
                        alive_players = [p for p in room.players if p.alive and p.role != PlayerRole.WOLF]
                        if alive_players:
                            target = random.choice(alive_players)
                            for wolf in ai_wolves:
                                await self._handle_wolf_action(room, wolf, target.user_id)
                else:
                    # 如果还没有任何投票记录，AI狼人随机选择
                    alive_players = [p for p in room.players if p.alive and p.role != PlayerRole.WOLF]
                    if alive_players:
                        target = random.choice(alive_players)
                        for wolf in ai_wolves:
                            await self._handle_wolf_action(room, wolf, target.user_id)
        
        elif phase == "seer":
            seer = next((p for p in room.players if p.role == PlayerRole.SEER and p.alive), None)
            if seer and seer.is_ai:
                await asyncio.sleep(1)  # 延迟1秒，模拟思考
                alive_players = [p for p in room.players if p.alive and p.user_id != seer.user_id]
                if alive_players:
                    target = random.choice(alive_players)
                    await self._handle_seer_action(room, seer, target.user_id)
        
        elif phase == "witch":
            witch = next((p for p in room.players if p.role == PlayerRole.WITCH and p.alive), None)
            if witch and witch.is_ai:
                await asyncio.sleep(1)  # 延迟1秒，模拟思考
                # 获取狼人击杀目标
                wolf_target = None
                if "wolf" in room.night_actions and room.night_actions["wolf"].get("target"):
                    wolf_target = room.night_actions["wolf"]["target"]
                
                # 重新获取房间状态（可能已更新）
                room_data = await redis_service.get_room_data(room.room_id)
                if room_data:
                    current_room = GameRoom(**room_data)
                    current_witch = next((p for p in current_room.players if p.user_id == witch.user_id), None)
                    if current_witch:
                        # 获取狼人击杀目标
                        wolf_target = None
                        if "wolf" in current_room.night_actions and current_room.night_actions["wolf"].get("target"):
                            wolf_target = current_room.night_actions["wolf"]["target"]
                        
                        # AI女巫策略：如果有解药且有人被刀，使用解药；否则不使用
                        if wolf_target and not current_witch.witch_antidote_used:
                            # 检查首夜不能自救
                            if not (current_room.night_count == 1 and wolf_target == current_witch.user_id):
                                await self._handle_witch_action(current_room, current_witch, {"action_type": "antidote"})
                        else:
                            # 不使用任何药水
                            await self._handle_witch_action(current_room, current_witch, {"action_type": "none"})
    
    def _get_role_name(self, role: PlayerRole) -> str:
        """获取角色名称"""
        names = {
            PlayerRole.WOLF: "狼人",
            PlayerRole.VILLAGER: "平民",
            PlayerRole.SEER: "预言家",
            PlayerRole.WITCH: "女巫",
            PlayerRole.HUNTER: "猎人",
            PlayerRole.GUARD: "守卫"
        }
        return names.get(role, "未知")
    
    def _get_role_description(self, role: PlayerRole) -> str:
        """获取角色描述"""
        descriptions = {
            PlayerRole.WOLF: "每晚可以共同决定击杀一名玩家。白天需要伪装成好人，混淆视听。",
            PlayerRole.VILLAGER: "无任何技能，全程闭眼。依靠白天发言和逻辑推理找出狼人。",
            PlayerRole.SEER: "每晚可以查验一名玩家的身份，得知是'好人'还是'狼人'。",
            PlayerRole.WITCH: "拥有解药（可救被刀玩家）和毒药（可毒杀任意玩家）。每瓶只能用一次，每晚只能使用一瓶。首夜不能自救。",
            PlayerRole.HUNTER: "被投票出局或被狼刀（且未被毒）时，可开枪带走一名玩家。若被女巫毒死，则无法开枪。",
            PlayerRole.GUARD: "每晚可守护一人（包括自己），防止其被刀。不能连续两晚守同一人。若守的人被女巫救，可能出现'同守同救'导致死亡。"
        }
        return descriptions.get(role, "未知角色")
    
    async def _trigger_ai_responses(self, room: GameRoom, broadcast_callback=None):
        """触发AI玩家自动回复
        
        Args:
            room: 游戏房间
            broadcast_callback: 可选的回调函数，用于广播消息 (room_id, message) -> None
        """
        import asyncio
        
        # 获取存活的AI玩家
        alive_ai_players = [p for p in room.players if p.is_ai and p.alive]
        
        if not alive_ai_players:
            return
        
        # 为每个AI玩家创建异步任务（并行处理，但每个有随机延迟）
        async def generate_ai_response(ai_player: Player, delay: float):
            """为单个AI玩家生成回复"""
            await asyncio.sleep(delay)
            
            # 重新获取房间数据（可能已更新）
            room_data = await redis_service.get_room_data(room.room_id)
            if not room_data:
                return
            current_room = GameRoom(**room_data)
            current_ai_player = next((p for p in current_room.players if p.user_id == ai_player.user_id), None)
            if not current_ai_player or not current_ai_player.alive:
                return
            
            # 构建AI玩家的prompt
            role_name = self._get_role_name(current_ai_player.role)
            role_desc = self._get_role_description(current_ai_player.role)
            
            # 获取狼人队友（如果是狼人）
            teammates = None
            if current_ai_player.role == PlayerRole.WOLF:
                teammates = [p.username for p in current_room.players 
                           if p.role == PlayerRole.WOLF and p.user_id != current_ai_player.user_id and p.alive]
            
            # 构建存活玩家列表
            alive_players_info = [{"username": p.username, "user_id": p.user_id} 
                                for p in current_room.players if p.alive]
            
            # 获取最新的消息
            latest_messages = await redis_service.get_room_messages(room.room_id)
            
            # 构建消息历史（只包含最近的消息）
            messages_for_ai = []
            for msg in latest_messages[-10:]:
                if isinstance(msg, dict):
                    messages_for_ai.append({
                        "username": msg.get("username", "未知"),
                        "content": msg.get("content", "")
                    })
            
            # 构建prompt
            system_prompt = AIService.build_werewolf_ai_prompt(
                player_role=current_ai_player.role.value,
                role_name=role_name,
                role_desc=role_desc,
                game_phase=current_room.phase.value,
                day_count=current_room.day_count,
                recent_messages=messages_for_ai,
                alive_players=alive_players_info,
                teammates=teammates
            )
            
            # 构建对话历史
            conversation_history = []
            for msg in messages_for_ai[-5:]:  # 最近5条消息作为上下文
                conversation_history.append({
                    "role": "user",
                    "content": f"{msg['username']}说：{msg['content']}"
                })
            
            # 调用AI生成回复
            try:
                ai_response = await AIService.generate_response(
                    messages=conversation_history,
                    system_prompt=system_prompt,
                    temperature=0.8
                )
                
                # 如果AI回复为空或太短，使用默认回复
                if not ai_response or len(ai_response.strip()) < 2:
                    ai_response = self._generate_default_ai_response(current_ai_player, current_room)
                
                # 添加AI玩家的发言
                ai_message = {
                    "type": "speech",
                    "user_id": current_ai_player.user_id,
                    "username": current_ai_player.username,
                    "content": ai_response.strip(),
                    "timestamp": str(uuid.uuid4())
                }
                await redis_service.add_room_message(room.room_id, ai_message)
                
                # 如果有广播回调，调用它
                if broadcast_callback:
                    await broadcast_callback(room.room_id, ai_message)
                
            except Exception as e:
                logger.warning(f"AI玩家 {current_ai_player.username} 生成回复失败: {e}")
                # 使用默认回复
                default_response = self._generate_default_ai_response(current_ai_player, current_room)
                ai_message = {
                    "type": "speech",
                    "user_id": current_ai_player.user_id,
                    "username": current_ai_player.username,
                    "content": default_response,
                    "timestamp": str(uuid.uuid4())
                }
                await redis_service.add_room_message(room.room_id, ai_message)
                
                # 如果有广播回调，调用它
                if broadcast_callback:
                    await broadcast_callback(room.room_id, ai_message)
        
        # 创建所有AI玩家的任务
        tasks = []
        for ai_player in alive_ai_players:
            delay = random.uniform(1.0, 3.0)  # 随机延迟1-3秒
            tasks.append(generate_ai_response(ai_player, delay))
        
        # 并行执行所有任务（不等待完成，让它们在后台运行）
        if tasks:
            # 直接使用 gather，不等待完成，让它在后台运行
            asyncio.gather(*tasks)
    
    def _generate_default_ai_response(self, ai_player: Player, room: GameRoom) -> str:
        """生成默认的AI回复（当AI服务失败时使用）"""
        responses = [
            "我在观察大家的发言...",
            "让我想想...",
            "我觉得需要更多信息。",
            "这个情况有点复杂。",
            "我需要再听听其他人的意见。"
        ]
        
        if ai_player.role == PlayerRole.WOLF:
            responses.extend([
                "我觉得我们应该仔细分析每个人的发言。",
                "我同意，需要找出真正的狼人。",
                "大家要保持冷静，不要被误导。"
            ])
        elif ai_player.role == PlayerRole.SEER:
            responses.extend([
                "作为预言家，我需要谨慎发言。",
                "我查验了一些信息，但需要更多证据。"
            ])
        
        return random.choice(responses)
    
    async def _trigger_ai_voting(self, room: GameRoom):
        """触发AI玩家自动投票"""
        import asyncio
        
        # 获取存活的AI玩家
        alive_ai_players = [p for p in room.players if p.is_ai and p.alive and not p.voted]
        
        if not alive_ai_players:
            return
        
        # 为每个AI玩家创建异步任务
        async def ai_vote(ai_player: Player, delay: float):
            """AI玩家投票"""
            await asyncio.sleep(delay)
            
            # 重新获取房间数据
            room_data = await redis_service.get_room_data(room.room_id)
            if not room_data:
                return
            current_room = GameRoom(**room_data)
            current_ai_player = next((p for p in current_room.players if p.user_id == ai_player.user_id), None)
            if not current_ai_player or not current_ai_player.alive or current_ai_player.voted:
                return
            
            # 获取存活玩家（排除自己）
            alive_players = [p for p in current_room.players if p.alive and p.user_id != current_ai_player.user_id]
            if not alive_players:
                return
            
            # 根据身份选择投票目标
            target = await self._ai_choose_vote_target(current_room, current_ai_player, alive_players)
            if target:
                await self._handle_voting(current_room, current_ai_player, target)
        
        # 创建所有AI玩家的任务
        tasks = []
        for ai_player in alive_ai_players:
            delay = random.uniform(1.0, 3.0)  # 随机延迟1-3秒
            tasks.append(ai_vote(ai_player, delay))
        
        # 并行执行所有任务
        if tasks:
            asyncio.gather(*tasks)
    
    async def _ai_choose_vote_target(self, room: GameRoom, ai_player: Player, alive_players: List[Player]) -> Optional[str]:
        """AI玩家选择投票目标"""
        try:
            # 获取最近的发言
            latest_messages = await redis_service.get_room_messages(room.room_id)
            messages_for_ai = []
            for msg in latest_messages[-10:]:
                if isinstance(msg, dict):
                    messages_for_ai.append({
                        "username": msg.get("username", "未知"),
                        "content": msg.get("content", "")
                    })
            
            role_name = self._get_role_name(ai_player.role) if ai_player.role else "玩家"
            role_desc = self._get_role_description(ai_player.role) if ai_player.role else ""
            
            # 获取狼人队友（如果是狼人）
            teammates = None
            if ai_player.role == PlayerRole.WOLF:
                teammates = [p.username for p in room.players 
                           if p.role == PlayerRole.WOLF and p.user_id != ai_player.user_id and p.alive]
            
            # 构建存活玩家列表（如果是狼人，排除队友）
            if ai_player.role == PlayerRole.WOLF:
                # 排除狼人队友，只显示好人
                non_teammate_players = [p for p in alive_players if p.role != PlayerRole.WOLF]
                alive_players_info = [{"username": p.username, "user_id": p.user_id} 
                                    for p in non_teammate_players]
                # 如果只有队友可选（理论上不应该发生），使用策略投票
                if not alive_players_info:
                    return self._ai_strategic_vote(room, ai_player, alive_players)
            else:
                alive_players_info = [{"username": p.username, "user_id": p.user_id} 
                                    for p in alive_players]
            
            # 构建投票prompt
            if ai_player.role == PlayerRole.WOLF and teammates:
                teammates_text = f"\n你的狼人队友：{', '.join(teammates)}\n重要：你绝对不能投票给队友，只能投票给好人。"
            else:
                teammates_text = ""
            
            prompt = f"""你正在参与一场狼人杀游戏的投票阶段。

【你的身份】
{role_name}
{role_desc}{teammates_text}

【游戏状态】
当前是第{room.day_count}天投票阶段
存活玩家：{', '.join([p['username'] for p in alive_players_info])}

【最近发言】
{chr(10).join([f"{msg['username']}：{msg['content']}" for msg in messages_for_ai[-5:]]) if messages_for_ai else "暂无发言"}

【你的任务】
你需要投票出局一名玩家。根据你的身份：
1. 如果是狼人，必须投票给好人，绝对不能投票给队友
2. 如果是好人，应该投票给可疑的狼人
3. 根据发言和逻辑推理选择目标
4. 只返回你要投票的玩家用户名，不要其他说明

请选择你要投票的玩家用户名："""
            
            # 调用AI生成投票目标
            conversation_history = [{
                "role": "user",
                "content": "请选择你要投票的玩家。"
            }]
            
            ai_response = await AIService.generate_response(
                messages=conversation_history,
                system_prompt=prompt,
                temperature=0.7
            )
            
            # 从AI回复中提取玩家名称
            if ai_response:
                ai_response = ai_response.strip()
                # 尝试匹配玩家名称
                for player in alive_players:
                    if player.username in ai_response:
                        # 如果是狼人，检查是否是队友，如果是队友则重新选择
                        if ai_player.role == PlayerRole.WOLF and player.role == PlayerRole.WOLF:
                            # AI狼人投票给队友，使用策略投票重新选择
                            logger.info(f"【AI投票】{ai_player.username} (狼人) 尝试投票给队友 {player.username}，重新选择目标")
                            return self._ai_strategic_vote(room, ai_player, alive_players)
                        return player.user_id
            
            # 如果AI没有返回有效目标，使用策略投票
            return self._ai_strategic_vote(room, ai_player, alive_players)
            
        except Exception as e:
            logger.warning(f"AI玩家 {ai_player.username} 选择投票目标失败: {e}")
            # 使用策略投票
            return self._ai_strategic_vote(room, ai_player, alive_players)
    
    def _ai_strategic_vote(self, room: GameRoom, ai_player: Player, alive_players: List[Player]) -> Optional[str]:
        """AI玩家策略投票（当AI服务失败时使用）"""
        if not alive_players:
            return None
        
        # 狼人策略：优先投票给好人（非狼人），绝不投票给队友
        if ai_player.role == PlayerRole.WOLF:
            # 排除所有狼人队友
            good_players = [p for p in alive_players if p.role != PlayerRole.WOLF]
            if good_players:
                # 优先选择好人，降低随机性，确保不会投票给队友
                return random.choice(good_players).user_id
            # 如果没有好人可选（理论上不应该发生），返回None
            return None
        
        # 好人策略：随机投票（因为不知道谁是狼人）
        return random.choice(alive_players).user_id
    
    async def _start_night_phase(self, room_id: str):
        """开始夜晚阶段"""
        import asyncio
        
        # 强制刷新输出
        logger.info(f"\n{'='*60}")
        logger.info(f"【夜晚阶段开始】房间 {room_id}")
        logger.info(f"{'='*60}")
        
        room = await self.get_room(room_id, check_timeout=False)
        if not room:
            logger.error(f"房间 {room_id} 不存在，无法开始夜晚阶段")
            return
        logger.info(f"房间 {room_id} - 第 {room.night_count + 1} 夜开始")
        room.phase = GamePhase.NIGHT
        room.night_count += 1
        room.night_actions = {}
        room.current_night_phase = None
        room.eliminated_tonight = None
        room.saved_tonight = None
        
        # 重置夜晚相关状态
        for player in room.players:
            if player.alive:
                player.guarded = False
                player.guard_target = None
        
        # 先保存房间状态，确保night_count被正确保存
        await redis_service.set_room_data(room_id, room.model_dump())
        
        await self._set_phase_time(room)
        
        # 广播房间状态更新
        if self.broadcast_callback:
            import json
            await self.broadcast_callback(json.dumps({
                "type": "room_update",
                "room": room.model_dump()
            }), f"werewolf_{room_id}")
        
        # 发送夜晚开始提示和弹窗
        await self._ai_announce(room_id, f"第{room.night_count}夜开始，所有玩家请闭眼。", phase_popup="night_start")
        
        # 等待1.5秒，让玩家看到夜晚开始的弹窗（弹窗显示1.5秒后消失）
        await asyncio.sleep(1.5)
        
        # 弹窗消失后，按顺序处理夜晚行动（引导消息会在_process_night_actions中发送）
        await self._process_night_actions(room)
    
    async def _process_night_actions(self, room: GameRoom):
        """按顺序处理夜晚行动：守卫 -> 狼人 -> 预言家 -> 女巫"""
        import asyncio
        
        # 1. 守卫行动
        await self._process_guard_phase(room)
        # 等待1秒，让玩家看到守卫阶段的提示
        await asyncio.sleep(1)
        # 触发AI玩家自动行动
        await self._trigger_ai_night_actions(room, "guard")
        # 等待守卫行动完成（最多等待30秒）
        await self._wait_for_phase_completion(room, "guard", timeout=30)
        # 检查是否完成，如果完成则提示
        room_data = await redis_service.get_room_data(room.room_id)
        if room_data:
            current_room = GameRoom(**room_data)
            guard = next((p for p in current_room.players if p.role == PlayerRole.GUARD and p.alive), None)
            if not guard or "guard" in current_room.night_actions:
                logger.info(f"【守卫阶段完成】房间 {room.room_id} - AI主持人: 守卫已完成操作。")
                await self._ai_announce(room.room_id, "守卫已完成操作。")
                await asyncio.sleep(1)  # 等待1秒，让玩家看到提示
        
        # 2. 狼人行动
        await self._process_wolf_phase(room)
        # 等待1秒，让玩家看到狼人阶段的提示
        await asyncio.sleep(1)
        # 触发AI玩家自动行动
        await self._trigger_ai_night_actions(room, "wolf")
        # 等待狼人行动完成（最多等待30秒）
        await self._wait_for_phase_completion(room, "wolf", timeout=30)
        # 检查是否完成，如果完成则提示
        room_data = await redis_service.get_room_data(room.room_id)
        if room_data:
            current_room = GameRoom(**room_data)
            wolves = [p for p in current_room.players if p.role == PlayerRole.WOLF and p.alive]
            if not wolves or ("wolf" in current_room.night_actions and 
                             len(current_room.night_actions["wolf"].get("votes", {})) >= len(wolves)):
                logger.info(f"【狼人阶段完成】房间 {room.room_id} - AI主持人: 狼人已完成操作。")
                await self._ai_announce(room.room_id, "狼人已完成操作。")
                await asyncio.sleep(1)  # 等待1秒，让玩家看到提示
        
        # 3. 预言家行动
        await self._process_seer_phase(room)
        # 等待1秒，让玩家看到预言家阶段的提示
        await asyncio.sleep(1)
        # 触发AI玩家自动行动
        await self._trigger_ai_night_actions(room, "seer")
        # 等待预言家行动完成（最多等待30秒）
        await self._wait_for_phase_completion(room, "seer", timeout=30)
        # 检查是否完成，如果完成则提示
        room_data = await redis_service.get_room_data(room.room_id)
        if room_data:
            current_room = GameRoom(**room_data)
            seer = next((p for p in current_room.players if p.role == PlayerRole.SEER and p.alive), None)
            if not seer or "seer" in current_room.night_actions:
                logger.info(f"【预言家阶段完成】房间 {room.room_id}")
                await self._ai_announce(room.room_id, "预言家已完成操作。")
                await asyncio.sleep(1)  # 等待1秒，让玩家看到提示
        
        # 4. 女巫行动
        await self._process_witch_phase(room)
        # 等待1秒，让玩家看到女巫阶段的提示
        await asyncio.sleep(1)
        # 触发AI玩家自动行动
        await self._trigger_ai_night_actions(room, "witch")
        # 等待女巫行动完成（最多等待30秒）
        await self._wait_for_phase_completion(room, "witch", timeout=30)
        # 检查是否完成，如果完成则提示
        room_data = await redis_service.get_room_data(room.room_id)
        if room_data:
            current_room = GameRoom(**room_data)
            witch = next((p for p in current_room.players if p.role == PlayerRole.WITCH and p.alive), None)
            if not witch:
                logger.info(f"【女巫阶段完成】房间 {room.room_id}")
                await self._ai_announce(room.room_id, "女巫已完成操作。")
            elif "witch" in current_room.night_actions:
                witch_action = current_room.night_actions["witch"]
                if (witch_action.get("antidote_used") or 
                    witch_action.get("poison_used") or 
                    witch_action.get("action") == "none"):
                    logger.info(f"【女巫阶段完成】房间 {room.room_id}")
                    await self._ai_announce(room.room_id, "女巫已完成操作。")
            await asyncio.sleep(1)  # 等待1秒，让玩家看到提示
        
        # 所有夜晚子阶段都处理完了，将current_night_phase设置为None
        room_data = await redis_service.get_room_data(room.room_id)
        if room_data:
            final_room = GameRoom(**room_data)
            final_room.current_night_phase = None
            await redis_service.set_room_data(room.room_id, final_room.model_dump())
        
        # 检查是否所有行动都完成了，如果完成则结算
        await self._check_night_actions_complete(room)
    
    async def _process_guard_phase(self, room: GameRoom):
        """处理守卫阶段"""
        guard = next((p for p in room.players if p.role == PlayerRole.GUARD and p.alive), None)
        if not guard:
            logger.info(f"【守卫阶段】房间 {room.room_id} - 守卫已死亡或不存在，跳过")
            return
        
        logger.info(f"【守卫阶段开始】房间 {room.room_id} - 守卫 {guard.username} (ID: {guard.user_id})")
        room.current_night_phase = "guard"
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 广播房间状态更新
        if self.broadcast_callback:
            import json
            await self.broadcast_callback(json.dumps({
                "type": "room_update",
                "room": room.model_dump()
            }), f"werewolf_{room.room_id}")
        
        # AI主持人公开提示
        logger.info(f"【守卫阶段】房间 {room.room_id} - AI主持人: 守卫请睁眼，选择你要守护的玩家。")
        await self._ai_announce(room.room_id, "守卫请睁眼，选择你要守护的玩家。")
        
        # 发送私密消息给守卫
        alive_players = [p for p in room.players if p.alive]
        player_list = "\n".join([f"{i+1}. {p.username}" for i, p in enumerate(alive_players)])
        
        # 获取上一晚守护目标（不能连续两晚守同一人）
        cannot_guard = guard.last_guard_target if guard.last_guard_target else None
        cannot_guard_name = None
        if cannot_guard:
            cannot_guard_player = next((p for p in room.players if p.user_id == cannot_guard), None)
            if cannot_guard_player:
                cannot_guard_name = cannot_guard_player.username
        
        message = f"【守卫行动】\n请选择你要守护的玩家：\n{player_list}"
        if cannot_guard_name:
            message += f"\n\n注意：不能连续两晚守护同一人，上一晚你守护了 {cannot_guard_name}。"
        
        private_msg = {
            "type": "night_action",
            "action": "guard",
            "content": message,
            "players": [{"user_id": p.user_id, "username": p.username} for p in alive_players],
            "cannot_guard": cannot_guard
        }
        
        await redis_service.add_private_message(
            room.room_id, guard.user_id, private_msg
        )
        
        # 通过WebSocket发送私有消息给守卫
        if self.send_private_message_callback:
            import json
            await self.send_private_message_callback(
                room.room_id, guard.user_id, json.dumps({
                    "type": "private_message",
                    "content": private_msg
                })
            )
        
        # 等待守卫行动完成（通过检查 night_actions）
        # 注意：这里不等待，让玩家通过 player_action 提交行动
    
    async def _process_wolf_phase(self, room: GameRoom):
        """处理狼人阶段"""
        wolves = [p for p in room.players if p.role == PlayerRole.WOLF and p.alive]
        if not wolves:
            logger.info(f"【狼人阶段】房间 {room.room_id} - 狼人已全部死亡，跳过")
            return
        
        wolf_names = [w.username for w in wolves]
        logger.info(f"【狼人阶段开始】房间 {room.room_id} - 存活狼人: {', '.join(wolf_names)} (共 {len(wolves)} 人)")
        room.current_night_phase = "wolf"
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 广播房间状态更新
        if self.broadcast_callback:
            import json
            await self.broadcast_callback(json.dumps({
                "type": "room_update",
                "room": room.model_dump()
            }), f"werewolf_{room.room_id}")
        
        # AI主持人公开提示
        logger.info(f"【狼人阶段】房间 {room.room_id} - AI主持人: 守卫请闭眼。狼人请睁眼，共同选择要击杀的玩家。")
        await self._ai_announce(room.room_id, "守卫请闭眼。狼人请睁眼，共同选择要击杀的玩家。")
        
        # 获取所有存活玩家（排除狼人）
        alive_players = [p for p in room.players if p.alive and p.role != PlayerRole.WOLF]
        player_list = "\n".join([f"{i+1}. {p.username}" for i, p in enumerate(alive_players)])
        
        # 发送私密消息给所有狼人
        for wolf in wolves:
            teammates = [w.username for w in wolves if w.user_id != wolf.user_id]
            message = f"【狼人行动】\n请选择要击杀的玩家：\n{player_list}"
            if teammates:
                message += f"\n\n你的狼人队友：{', '.join(teammates)}"
            
            private_msg = {
                "type": "night_action",
                "action": "wolf",
                "content": message,
                "players": [{"user_id": p.user_id, "username": p.username} for p in alive_players],
                "teammates": teammates
            }
            
            await redis_service.add_private_message(
                room.room_id, wolf.user_id, private_msg
            )
            
            # 通过WebSocket发送私有消息给狼人
            if self.send_private_message_callback:
                import json
                await self.send_private_message_callback(
                    room.room_id, wolf.user_id, json.dumps({
                        "type": "private_message",
                        "content": private_msg
                    })
                )
    
    async def _process_seer_phase(self, room: GameRoom):
        """处理预言家阶段"""
        seer = next((p for p in room.players if p.role == PlayerRole.SEER and p.alive), None)
        if not seer:
            logger.info(f"【预言家阶段】房间 {room.room_id} - 预言家已死亡或不存在，跳过")
            return
        
        logger.info(f"【预言家阶段开始】房间 {room.room_id} - 预言家 {seer.username}")
        room.current_night_phase = "seer"
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 广播房间状态更新
        if self.broadcast_callback:
            import json
            await self.broadcast_callback(json.dumps({
                "type": "room_update",
                "room": room.model_dump()
            }), f"werewolf_{room.room_id}")
        
        # AI主持人公开提示
        await self._ai_announce(room.room_id, "狼人请闭眼。预言家请睁眼，选择你要查验的玩家。")
        
        # 获取所有存活玩家（排除自己）
        alive_players = [p for p in room.players if p.alive and p.user_id != seer.user_id]
        player_list = "\n".join([f"{i+1}. {p.username}" for i, p in enumerate(alive_players)])
        
        # 发送私密消息给预言家
        private_msg = {
            "type": "night_action",
            "action": "seer",
            "content": f"【预言家行动】\n请选择你要查验的玩家：\n{player_list}",
            "players": [{"user_id": p.user_id, "username": p.username} for p in alive_players]
        }
        
        await redis_service.add_private_message(
            room.room_id, seer.user_id, private_msg
        )
        
        # 通过WebSocket发送私有消息给预言家
        if self.send_private_message_callback:
            import json
            await self.send_private_message_callback(
                room.room_id, seer.user_id, json.dumps({
                    "type": "private_message",
                    "content": private_msg
                })
            )
    
    async def _process_witch_phase(self, room: GameRoom):
        """处理女巫阶段"""
        witch = next((p for p in room.players if p.role == PlayerRole.WITCH and p.alive), None)
        if not witch:
            logger.info(f"【女巫阶段】房间 {room.room_id} - 女巫已死亡或不存在，跳过")
            return
        
        logger.info(f"【女巫阶段开始】房间 {room.room_id} - 女巫 {witch.username}")
        room.current_night_phase = "witch"
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 广播房间状态更新
        if self.broadcast_callback:
            import json
            await self.broadcast_callback(json.dumps({
                "type": "room_update",
                "room": room.model_dump()
            }), f"werewolf_{room.room_id}")
        
        # AI主持人公开提示
        await self._ai_announce(room.room_id, "预言家请闭眼。女巫请睁眼。")
        
        # 获取狼人击杀目标
        wolf_target = None
        if "wolf" in room.night_actions and room.night_actions["wolf"].get("target"):
            wolf_target = room.night_actions["wolf"]["target"]
            wolf_target_player = next((p for p in room.players if p.user_id == wolf_target), None)
            wolf_target_name = wolf_target_player.username if wolf_target_player else None
        else:
            wolf_target_name = None
        
        # 获取所有存活玩家（用于毒药目标）
        alive_players = [p for p in room.players if p.alive and p.user_id != witch.user_id]
        player_list = "\n".join([f"{i+1}. {p.username}" for i, p in enumerate(alive_players)])
        
        # 构建消息
        message = "【女巫行动】\n"
        if wolf_target_name:
            message += f"昨晚 {wolf_target_name} 被狼人击杀。\n\n"
        else:
            message += "昨晚无人被击杀。\n\n"
        
        message += "请选择你的行动：\n"
        if not witch.witch_antidote_used:
            message += "1. 使用解药（救被刀者）\n"
        if not witch.witch_poison_used:
            message += "2. 使用毒药（毒杀一人）\n"
        message += "3. 不使用任何药水\n"
        
        if not witch.witch_poison_used:
            message += f"\n可毒杀的玩家列表：\n{player_list}"
        
        # 首夜不能自救
        is_first_night = room.night_count == 1
        if is_first_night and wolf_target == witch.user_id:
            message += "\n\n注意：首夜不能自救！"
        
        private_msg = {
            "type": "night_action",
            "action": "witch",
            "content": message,
            "wolf_target": wolf_target,
            "wolf_target_name": wolf_target_name,
            "antidote_used": witch.witch_antidote_used,
            "poison_used": witch.witch_poison_used,
            "players": [{"user_id": p.user_id, "username": p.username} for p in alive_players],
            "is_first_night": is_first_night
        }
        
        await redis_service.add_private_message(
            room.room_id, witch.user_id, private_msg
        )
        
        # 通过WebSocket发送私有消息给女巫
        if self.send_private_message_callback:
            import json
            await self.send_private_message_callback(
                room.room_id, witch.user_id, json.dumps({
                    "type": "private_message",
                    "content": private_msg
                })
            )
        
        # 女巫行动完成后，AI主持人提示闭眼
        # 注意：这里不立即提示，等所有行动完成后再提示
    
    async def _handle_guard_action(self, room: GameRoom, player: Player, target: Optional[str]) -> Dict:
        """处理守卫行动"""
        if player.role != PlayerRole.GUARD:
            return {"error": "你不是守卫"}
        
        if not target:
            return {"error": "请选择守护目标"}
        
        target_player = next((p for p in room.players if p.user_id == target and p.alive), None)
        if not target_player:
            return {"error": "目标玩家不存在或已死亡"}
        
        # 检查不能连续两晚守同一人
        if player.last_guard_target == target:
            return {"error": "不能连续两晚守护同一人"}
        
        # 记录守卫行动
        if "guard" not in room.night_actions:
            room.night_actions["guard"] = {}
        room.night_actions["guard"]["target"] = target
        room.night_actions["guard"]["guard_user_id"] = player.user_id
        
        # 设置守护状态
        target_player.guarded = True
        player.guard_target = target
        player.last_guard_target = target
        
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 打印守卫行动日志（强制刷新输出）
        logger.info(f"【守卫行动】房间 {room.room_id} - 守卫 {player.username} 选择守护: {target_player.username} (ID: {target})")
        
        # 发送确认消息
        await redis_service.add_private_message(
            room.room_id, player.user_id,
            {
                "type": "action_confirmed",
                "content": f"你选择守护 {target_player.username}",
                "action": "guard"
            }
        )
        
        return {"success": True, "message": f"你选择守护 {target_player.username}"}
    
    async def _handle_wolf_action(self, room: GameRoom, player: Player, target: Optional[str]) -> Dict:
        """处理狼人行动"""
        # 检查玩家是否存活
        if not player.alive:
            return {"error": "玩家已死亡，无法执行行动"}
        
        if player.role != PlayerRole.WOLF:
            return {"error": "你不是狼人"}
        
        if not target:
            return {"error": "请选择击杀目标"}
        
        target_player = next((p for p in room.players if p.user_id == target and p.alive), None)
        if not target_player:
            return {"error": "目标玩家不存在或已死亡"}
        
        if target_player.role == PlayerRole.WOLF:
            return {"error": "不能击杀狼人队友"}
        
        # 记录狼人投票（需要所有狼人达成一致）
        if "wolf" not in room.night_actions:
            room.night_actions["wolf"] = {"votes": {}, "target": None}
        
        room.night_actions["wolf"]["votes"][player.user_id] = target
        
        # 打印狼人投票日志（强制刷新输出）
        logger.info(f"【狼人投票】房间 {room.room_id} - 狼人 {player.username} (ID: {player.user_id}) 投票击杀: {target_player.username} (ID: {target})")
        
        # 检查是否所有狼人都投票了
        wolves = [p for p in room.players if p.role == PlayerRole.WOLF and p.alive]
        votes = room.night_actions["wolf"]["votes"]
        logger.info(f"【狼人投票进度】房间 {room.room_id} - 已投票: {len(votes)}/{len(wolves)}")
        
        # 如果人类狼人投票了，触发AI狼人跟随投票
        if not player.is_ai:
            # 获取未投票的AI狼人
            ai_wolves = [p for p in wolves if p.is_ai and p.user_id not in votes]
            if ai_wolves:
                # 统计已投票的目标
                vote_counts = {}
                for vote_target in votes.values():
                    vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
                
                # 选择得票最多的目标（如果有投票），否则使用当前投票
                if vote_counts:
                    most_voted_target = max(vote_counts.items(), key=lambda x: x[1])[0]
                else:
                    most_voted_target = target
                
                # 异步触发AI狼人跟随投票（不阻塞当前请求）
                import asyncio
                asyncio.create_task(self._trigger_ai_wolves_follow_vote(room.room_id, most_voted_target, ai_wolves))
        
        if len(votes) == len(wolves):
            # 统计投票
            vote_counts = {}
            for vote_target in votes.values():
                vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
            
            # 选择得票最多的目标
            final_target = max(vote_counts.items(), key=lambda x: x[1])[0]
            room.night_actions["wolf"]["target"] = final_target
            room.eliminated_tonight = final_target
            
            # 打印狼人投票完成日志（强制刷新输出）
            final_target_player = next((p for p in room.players if p.user_id == final_target), None)
            final_target_name = final_target_player.username if final_target_player else final_target
            logger.info(f"【狼人投票完成】房间 {room.room_id} - 所有狼人已投票，最终击杀目标: {final_target_name} (ID: {final_target})")
            logger.info(f"  投票详情: {vote_counts}")
        
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        target_name = target_player.username
        await redis_service.add_private_message(
            room.room_id, player.user_id,
            {
                "type": "action_confirmed",
                "content": f"你选择击杀 {target_name}",
                "action": "wolf"
            }
        )
        
        return {"success": True, "message": f"你选择击杀 {target_name}"}
    
    async def _trigger_ai_wolves_follow_vote(self, room_id: str, target: str, ai_wolves: List[Player]):
        """触发AI狼人跟随投票"""
        import asyncio
        await asyncio.sleep(1)  # 延迟1秒，模拟思考
        
        # 重新获取房间数据
        room_data = await redis_service.get_room_data(room_id)
        if not room_data:
            return
        
        room = GameRoom(**room_data)
        
        # 检查是否还在狼人阶段
        if room.phase != GamePhase.NIGHT or room.current_night_phase != "wolf":
            return
        
        # 检查投票是否已完成
        if "wolf" not in room.night_actions:
            return
        
        votes = room.night_actions["wolf"].get("votes", {})
        all_wolves = [p for p in room.players if p.role == PlayerRole.WOLF and p.alive]
        
        # 如果所有狼人都已投票，不需要再触发
        if len(votes) >= len(all_wolves):
            return
        
        # 让未投票的AI狼人跟随投票
        for wolf in ai_wolves:
            if wolf.user_id not in votes:
                # 重新获取玩家对象（因为room可能已更新）
                current_wolf = next((p for p in room.players if p.user_id == wolf.user_id), None)
                if current_wolf and current_wolf.alive:
                    await self._handle_wolf_action(room, current_wolf, target)
                    # 重新获取房间数据，因为投票可能已经更新
                    room_data = await redis_service.get_room_data(room_id)
                    if room_data:
                        room = GameRoom(**room_data)
    
    async def handle_wolf_chat(self, room_id: str, user_id: str, content: str) -> Dict:
        """处理狼人私聊消息"""
        room = await self.get_room(room_id)
        if not room:
            return {"error": "房间不存在"}
        
        player = next((p for p in room.players if p.user_id == user_id), None)
        if not player:
            return {"error": "玩家不存在"}
        
        # 检查是否是狼人
        if player.role != PlayerRole.WOLF:
            return {"error": "只有狼人可以发送私聊消息"}
        
        # 检查是否在狼人阶段
        if room.phase != GamePhase.NIGHT:
            return {"error": "只能在狼人阶段发送私聊消息"}
        
        # 检查是否有狼人行动正在进行
        if "wolf" not in room.night_actions:
            return {"error": "当前不是狼人行动阶段"}
        
        return {
            "success": True,
            "username": player.username,
            "timestamp": int(time.time() * 1000)
        }
    
    async def _handle_seer_action(self, room: GameRoom, player: Player, target: Optional[str]) -> Dict:
        """处理预言家行动"""
        if player.role != PlayerRole.SEER:
            logger.warning(f"【预言家行动】房间 {room.room_id} - 玩家 {player.username} 不是预言家")
            return {"error": "你不是预言家"}
        
        if not target:
            logger.warning(f"【预言家行动】房间 {room.room_id} - 玩家 {player.username} 未选择查验目标")
            return {"error": "请选择查验目标"}
        
        target_player = next((p for p in room.players if p.user_id == target and p.alive), None)
        if not target_player:
            logger.warning(f"【预言家行动】房间 {room.room_id} - 目标玩家不存在或已死亡: {target}")
            return {"error": "目标玩家不存在或已死亡"}
        
        # 记录查验结果
        if "seer" not in room.night_actions:
            room.night_actions["seer"] = {}
        
        room.night_actions["seer"]["target"] = target
        result = "狼人" if target_player.role == PlayerRole.WOLF else "好人"
        room.night_actions["seer"]["result"] = result
        
        # 强制刷新输出
        logger.info(f"【预言家行动】房间 {room.room_id} - 预言家 {player.username} 查验 {target_player.username}，结果: {result}")
        
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 构建私密消息
        private_msg = {
            "type": "seer_result",
            "content": f"你查验了 {target_player.username}，结果是：{result}",
            "target": target_player.username,
            "target_user_id": target,  # 添加目标玩家的user_id，方便前端匹配
            "result": result
        }
        
        # 发送私密结果到Redis
        await redis_service.add_private_message(
            room.room_id, player.user_id, private_msg
        )
        
        # 通过WebSocket实时发送私密消息
        if self.send_private_message_callback:
            import json
            try:
                await self.send_private_message_callback(
                    room.room_id, player.user_id, json.dumps({
                        "type": "private_message",
                        "content": private_msg
                    })
                )
            except Exception as e:
                logger.error(f"[预言家行动] 发送WebSocket消息失败: {e}")
        
        return {"success": True, "message": f"你查验了 {target_player.username}，结果是：{result}"}
    
    async def _handle_witch_action(self, room: GameRoom, player: Player, action_data: Dict) -> Dict:
        """处理女巫行动"""
        if player.role != PlayerRole.WITCH:
            return {"error": "你不是女巫"}
        
        action_type = action_data.get("action_type")  # "antidote", "poison", "none"
        target = action_data.get("target")
        
        if "witch" not in room.night_actions:
            room.night_actions["witch"] = {}
        
        # 获取狼人击杀目标
        wolf_target = None
        if "wolf" in room.night_actions:
            # 首先尝试从 target 字段获取
            if room.night_actions["wolf"].get("target"):
                wolf_target = room.night_actions["wolf"]["target"]
            # 如果 target 没有设置，但从投票记录中计算（防止 target 未正确设置的情况）
            elif "votes" in room.night_actions["wolf"] and room.night_actions["wolf"]["votes"]:
                votes = room.night_actions["wolf"]["votes"]
                # 统计投票
                vote_counts = {}
                for vote_target in votes.values():
                    vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
                # 选择得票最多的目标
                if vote_counts:
                    wolf_target = max(vote_counts.items(), key=lambda x: x[1])[0]
                    # 同时更新 target 字段，确保数据一致性
                    room.night_actions["wolf"]["target"] = wolf_target
                    room.eliminated_tonight = wolf_target
        
        if action_type == "antidote":
            # 使用解药
            if player.witch_antidote_used:
                return {"error": "解药已使用"}
            
            if not wolf_target:
                return {"error": "无人被击杀，无法使用解药"}
            
            # 首夜不能自救
            if room.night_count == 1 and wolf_target == player.user_id:
                return {"error": "首夜不能自救"}
            
            room.night_actions["witch"]["antidote_used"] = True
            room.night_actions["witch"]["saved_target"] = wolf_target
            room.saved_tonight = wolf_target
            player.witch_antidote_used = True
            player.saved_by_witch = True
            
            saved_player = next((p for p in room.players if p.user_id == wolf_target), None)
            saved_name = saved_player.username if saved_player else "未知"
            
            # 打印女巫救人日志（强制刷新输出）
            logger.info(f"【女巫行动】房间 {room.room_id} - 女巫 {player.username} 使用解药救了 {saved_name}")
            
            await redis_service.set_room_data(room.room_id, room.model_dump())
            
            await redis_service.add_private_message(
                room.room_id, player.user_id,
                {
                    "type": "action_confirmed",
                    "content": f"你使用解药救了 {saved_name}",
                    "action": "witch_antidote"
                }
            )
            
            return {"success": True, "message": f"你使用解药救了 {saved_name}"}
        
        elif action_type == "poison":
            # 使用毒药
            if player.witch_poison_used:
                return {"error": "毒药已使用"}
            
            if not target:
                return {"error": "请选择毒杀目标"}
            
            target_player = next((p for p in room.players if p.user_id == target and p.alive), None)
            if not target_player:
                return {"error": "目标玩家不存在或已死亡"}
            
            room.night_actions["witch"]["poison_used"] = True
            room.night_actions["witch"]["poison_target"] = target
            player.witch_poison_used = True
            target_player.poisoned_by_witch = True
            
            # 打印女巫毒人日志（强制刷新输出）
            logger.info(f"【女巫行动】房间 {room.room_id} - 女巫 {player.username} 使用毒药毒杀了 {target_player.username}")
            
            await redis_service.set_room_data(room.room_id, room.model_dump())
            
            await redis_service.add_private_message(
                room.room_id, player.user_id,
                {
                    "type": "action_confirmed",
                    "content": f"你使用毒药毒杀了 {target_player.username}",
                    "action": "witch_poison"
                }
            )
            
            return {"success": True, "message": f"你使用毒药毒杀了 {target_player.username}"}
        
        elif action_type == "none":
            # 不使用任何药水
            room.night_actions["witch"]["action"] = "none"
            
            # 打印女巫不使用药水日志（强制刷新输出）
            logger.info(f"【女巫行动】房间 {room.room_id} - 女巫 {player.username} 选择不使用任何药水")
            
            await redis_service.set_room_data(room.room_id, room.model_dump())
            
            await redis_service.add_private_message(
                room.room_id, player.user_id,
                {
                    "type": "action_confirmed",
                    "content": "你选择不使用任何药水",
                    "action": "witch_none"
                }
            )
            
            return {"success": True, "message": "你选择不使用任何药水"}
        
        else:
            return {"error": "无效的行动类型"}
    
    async def _process_night_result(self, room: GameRoom):
        """结算夜晚结果"""
        import asyncio
        
        # 防止重复调用
        if room.room_id in self.processing_night_result:
            logger.warning(f"【夜晚结算】房间 {room.room_id} 正在处理中，跳过重复调用")
            return
        
        self.processing_night_result.add(room.room_id)
        
        try:
            # 强制刷新输出
            logger.info(f"\n{'='*60}")
            logger.info(f"【夜晚结算】房间 {room.room_id} - 第 {room.night_count} 夜")
            logger.info(f"{'='*60}")
            
            # AI主持人提示夜晚结束
            await self._ai_announce(room.room_id, "女巫请闭眼。所有玩家请闭眼。", phase_popup="night_end")
            # 短暂等待，让玩家看到夜晚结束的弹窗（减少等待时间，避免界面卡住）
            await asyncio.sleep(1.5)
            
            deaths = []
            death_reasons = {}
            
            # 获取狼人击杀目标
            wolf_target = None
            if "wolf" in room.night_actions:
                # 首先尝试从 target 字段获取
                if room.night_actions["wolf"].get("target"):
                    wolf_target = room.night_actions["wolf"]["target"]
                # 如果 target 没有设置，但从投票记录中计算（防止 target 未正确设置的情况）
                elif "votes" in room.night_actions["wolf"] and room.night_actions["wolf"]["votes"]:
                    votes = room.night_actions["wolf"]["votes"]
                    # 统计投票
                    vote_counts = {}
                    for vote_target in votes.values():
                        vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
                    # 选择得票最多的目标
                    if vote_counts:
                        wolf_target = max(vote_counts.items(), key=lambda x: x[1])[0]
                        # 同时更新 target 字段，确保数据一致性
                        room.night_actions["wolf"]["target"] = wolf_target
                        room.eliminated_tonight = wolf_target
                        logger.info(f"【狼人击杀】从投票记录中计算目标: {wolf_target}")
            
            if wolf_target:
                wolf_target_player = next((p for p in room.players if p.user_id == wolf_target), None)
                if wolf_target_player:
                    role_name = self._get_role_name(wolf_target_player.role) if wolf_target_player.role else "未知"
                    logger.info(f"【狼人击杀】目标: {wolf_target_player.username} ({role_name}) (ID: {wolf_target})")
                    # 打印狼人投票详情
                    if "wolf" in room.night_actions and "votes" in room.night_actions["wolf"]:
                        votes = room.night_actions["wolf"]["votes"]
                        vote_counts = {}
                        for vote_target in votes.values():
                            vote_player = next((p for p in room.players if p.user_id == vote_target), None)
                            if vote_player:
                                vote_name = f"{vote_player.username} ({self._get_role_name(vote_player.role) if vote_player.role else '未知'})"
                            else:
                                vote_name = vote_target
                            vote_counts[vote_name] = vote_counts.get(vote_name, 0) + 1
                        logger.info(f"【狼人投票详情】{vote_counts}")
                else:
                    logger.warning(f"【狼人击杀】目标ID存在但玩家不存在: {wolf_target}")
            else:
                logger.info(f"【狼人击杀】今晚无人被击杀")
            
            # 获取守卫守护目标
            guard_target = None
            guard_player = None
            if "guard" in room.night_actions and room.night_actions["guard"].get("target"):
                guard_target = room.night_actions["guard"]["target"]
                guard_target_player = next((p for p in room.players if p.user_id == guard_target), None)
                guard_player = next((p for p in room.players if p.role == PlayerRole.GUARD and p.alive), None)
                if guard_target_player:
                    target_role = self._get_role_name(guard_target_player.role) if guard_target_player.role else "未知"
                    guard_name = f"{guard_player.username} ({self._get_role_name(guard_player.role) if guard_player else '未知'})" if guard_player else "未知"
                    logger.info(f"【守卫保护】守卫 {guard_name} 保护了: {guard_target_player.username} ({target_role}) (ID: {guard_target})")
                else:
                    logger.warning(f"【守卫保护】目标ID存在但玩家不存在: {guard_target}")
            else:
                guard_player = next((p for p in room.players if p.role == PlayerRole.GUARD and p.alive), None)
                if guard_player:
                    logger.info(f"【守卫保护】守卫 {guard_player.username} 今晚未使用技能")
                else:
                    logger.info(f"【守卫保护】守卫已死亡或不存在")
            
            # 获取女巫行动
            witch_saved = None
            witch_poisoned = None
            witch_player = next((p for p in room.players if p.role == PlayerRole.WITCH and p.alive), None)
            if "witch" in room.night_actions:
                # 优先从 saved_target 获取，如果没有则从 saved_tonight 获取
                if room.night_actions["witch"].get("saved_target"):
                    witch_saved = room.night_actions["witch"]["saved_target"]
                elif room.saved_tonight:
                    witch_saved = room.saved_tonight
                    # 同时更新 night_actions 中的 saved_target，确保数据一致性
                    room.night_actions["witch"]["saved_target"] = witch_saved
                    logger.info(f"【女巫救人】从 saved_tonight 获取被救目标: {witch_saved}")
                
                if witch_saved:
                    saved_player = next((p for p in room.players if p.user_id == witch_saved), None)
                    if saved_player:
                        saved_role = self._get_role_name(saved_player.role) if saved_player.role else "未知"
                        witch_name = f"{witch_player.username} ({self._get_role_name(witch_player.role) if witch_player else '未知'})" if witch_player else "未知"
                        logger.info(f"【女巫救人】女巫 {witch_name} 使用解药救了: {saved_player.username} ({saved_role}) (ID: {witch_saved})")
                    else:
                        logger.warning(f"【女巫救人】目标ID存在但玩家不存在: {witch_saved}")
                else:
                    logger.info(f"【女巫救人】女巫 {witch_player.username if witch_player else '未知'} 未使用解药")
                
                if room.night_actions["witch"].get("poison_target"):
                    witch_poisoned = room.night_actions["witch"]["poison_target"]
                    poisoned_target_player = next((p for p in room.players if p.user_id == witch_poisoned), None)
                    if poisoned_target_player:
                        poisoned_role = self._get_role_name(poisoned_target_player.role) if poisoned_target_player.role else "未知"
                        witch_name = f"{witch_player.username} ({self._get_role_name(witch_player.role) if witch_player else '未知'})" if witch_player else "未知"
                        logger.info(f"【女巫毒人】女巫 {witch_name} 使用毒药毒杀了: {poisoned_target_player.username} ({poisoned_role}) (ID: {witch_poisoned})")
                    else:
                        logger.warning(f"【女巫毒人】目标ID存在但玩家不存在: {witch_poisoned}")
                else:
                    logger.info(f"【女巫毒人】女巫 {witch_player.username if witch_player else '未知'} 未使用毒药")
            else:
                if witch_player:
                    logger.info(f"【女巫行动】女巫 {witch_player.username} 今晚未使用任何药水")
                else:
                    logger.info(f"【女巫行动】女巫已死亡或不存在")
            
            # 处理被刀者
            if wolf_target:
                wolf_target_player = next((p for p in room.players if p.user_id == wolf_target), None)
                if wolf_target_player and wolf_target_player.alive:
                    # 安全检查：如果被刀者是狼人，记录警告（理论上狼人不会刀自己，但可能是bug）
                    if wolf_target_player.role == PlayerRole.WOLF:
                        logger.warning(f"【警告】被刀者是狼人 {wolf_target_player.username}，这不应该发生（狼人不会刀自己）")
                    
                    is_guarded = (guard_target == wolf_target)
                    is_saved = (witch_saved == wolf_target)
                    
                    role_name = self._get_role_name(wolf_target_player.role) if wolf_target_player.role else "未知"
                    logger.info(f"\n【被刀者处理】{wolf_target_player.username} ({role_name}) (ID: {wolf_target})")
                    logger.info(f"  - 是否被守卫保护: {is_guarded}")
                    logger.info(f"  - 是否被女巫救: {is_saved}")
                    
                    # 同守同救规则：如果同时被守和救，则死亡
                    if is_guarded and is_saved:
                        wolf_target_player.alive = False
                        wolf_target_player.died_by = 'wolf'
                        deaths.append(wolf_target_player.user_id)
                        death_reasons[wolf_target_player.user_id] = "被狼人击杀（同守同救）"
                        logger.info(f"  - 结果: 死亡（同守同救规则）")
                    # 被守或救，则存活
                    elif is_guarded or is_saved:
                        logger.info(f"  - 结果: 存活（被{'守卫保护' if is_guarded else '女巫救'}）")
                    # 未被守且未被救，则死亡
                    else:
                        wolf_target_player.alive = False
                        wolf_target_player.died_by = 'wolf'
                        deaths.append(wolf_target_player.user_id)
                        death_reasons[wolf_target_player.user_id] = "被狼人击杀"
                        logger.info(f"  - 结果: 死亡（未被保护且未被救）")
                elif wolf_target_player and not wolf_target_player.alive:
                    logger.info(f"【被刀者处理】{wolf_target_player.username} 已被击杀，但之前已死亡")
            
            # 处理被毒者（毒药无视守卫，直接死亡）
            if witch_poisoned:
                poisoned_player = next((p for p in room.players if p.user_id == witch_poisoned), None)
                if poisoned_player and poisoned_player.alive:
                    # 检查是否已经在死亡列表中（避免重复）
                    if poisoned_player.user_id not in deaths:
                        poisoned_player.alive = False
                        poisoned_player.died_by = 'poison'
                        deaths.append(poisoned_player.user_id)
                        death_reasons[poisoned_player.user_id] = "被女巫毒死"
                        poisoned_role = self._get_role_name(poisoned_player.role) if poisoned_player.role else "未知"
                        logger.info(f"【被毒者处理】{poisoned_player.username} ({poisoned_role}) (ID: {witch_poisoned}) - 结果: 死亡（毒药无视守卫）")
                    else:
                        logger.info(f"【被毒者处理】{poisoned_player.username} 已在死亡列表中（可能同时被刀和毒）")
                elif poisoned_player and not poisoned_player.alive:
                    logger.info(f"【被毒者处理】{poisoned_player.username} 已被毒杀，但之前已死亡")
            
            # 打印最终死亡结果（强制刷新输出）
            logger.info(f"\n【夜晚结算结果】")
            if deaths:
                for death_id in deaths:
                    dead_player = next((p for p in room.players if p.user_id == death_id), None)
                    if dead_player:
                        reason = death_reasons.get(death_id, "未知原因")
                        role_name = self._get_role_name(dead_player.role) if dead_player.role else "未知"
                        logger.info(f"  - {dead_player.username} ({role_name}) {reason}")
                        # 安全检查：如果死亡玩家是狼人，记录警告（除非是被女巫毒杀）
                        if dead_player.role == PlayerRole.WOLF and reason != "被女巫毒死":
                            logger.warning(f"    【警告】死亡玩家是狼人，这不应该发生（除非被女巫毒杀）")
            else:
                logger.info(f"  - 今晚是平安夜，无人死亡")
            
            # 最终安全检查：确保所有在死亡列表中的玩家确实被标记为死亡
            logger.info(f"\n【夜晚结算最终检查】")
            for death_id in deaths:
                dead_player = next((p for p in room.players if p.user_id == death_id), None)
                if dead_player:
                    if dead_player.alive:
                        logger.error(f"  【错误】玩家 {dead_player.username} (ID: {death_id}) 在死亡列表中但alive=True！")
                        logger.info(f"    强制标记为死亡...")
                        dead_player.alive = False
                    else:
                        logger.info(f"  ✓ {dead_player.username} (ID: {death_id}) - 已正确标记为死亡")
                else:
                    logger.error(f"  【错误】死亡列表中的玩家ID {death_id} 不存在！")
            
            logger.info(f"{'='*60}\n")
            
            # 保存房间状态（确保死亡状态被正确保存）
            await redis_service.set_room_data(room.room_id, room.model_dump())
            
            # 再次验证死亡状态是否已正确保存
            room_data_check = await redis_service.get_room_data(room.room_id)
            if room_data_check:
                check_room = GameRoom(**room_data_check)
                # 先检查是否有玩家被错误地添加到死亡列表
                for death_id in list(deaths):  # 使用list()创建副本，以便在循环中修改
                    dead_player_check = next((p for p in check_room.players if p.user_id == death_id), None)
                    if dead_player_check:
                        if dead_player_check.alive:
                            # 这是一个严重的错误：玩家在死亡列表中但alive=True
                            # 这不应该发生，说明在夜晚结算时出现了问题
                            logger.error(f"【严重错误】玩家 {dead_player_check.username} (ID: {death_id}, 角色: {self._get_role_name(dead_player_check.role) if dead_player_check.role else '未知'}) 在死亡列表中但alive=True！")
                            logger.warning(f"  这可能是夜晚结算时的bug，玩家不应该被添加到死亡列表。")
                            logger.info(f"  从死亡列表中移除该玩家，而不是强制标记为死亡。")
                            # 从死亡列表中移除，因为玩家实际上还活着
                            deaths.remove(death_id)
                            if death_id in death_reasons:
                                del death_reasons[death_id]
                            # 确保玩家状态正确
                            dead_player_check.alive = True
                            logger.info(f"  已从死亡列表中移除玩家 {dead_player_check.username}，并确保其alive=True")
                        else:
                            # 死亡状态正确，确保已保存
                            if dead_player_check.alive:
                                logger.warning(f"【警告】玩家 {dead_player_check.username} (ID: {death_id}) 的死亡状态未正确保存，强制更新")
                                dead_player_check.alive = False
                                await redis_service.set_room_data(room.room_id, check_room.model_dump())
                
                # 额外检查：确保没有不在deaths列表中的玩家被错误地标记为死亡
                for player in check_room.players:
                    if not player.alive and player.user_id not in deaths:
                        # 如果玩家被标记为死亡但不在deaths列表中，记录警告
                        logger.info(f"【信息】玩家 {player.username} (ID: {player.user_id}) 已死亡（之前夜晚），死亡原因: {player.died_by}")
            
            # 进入白天阶段，公布死亡信息
            await self._start_day_phase(room, deaths, death_reasons)
        
        except Exception as e:
            # 捕获所有异常，确保日志能正常输出
            logger.error(f"【夜晚结算异常】房间 {room.room_id} - 发生错误: {e}", exc_info=True)
            logger.error(f"【夜晚结算异常】房间 {room.room_id} - 错误详情: {type(e).__name__}: {str(e)}")
            # 重新抛出异常，让上层处理
            raise
        finally:
            # 移除处理标志（无论成功还是失败都要移除）
            self.processing_night_result.discard(room.room_id)
    
    async def _start_day_phase(self, room: GameRoom, deaths: List[str], death_reasons: Dict[str, str]):
        """开始白天阶段"""
        # 重新获取最新的房间数据，确保使用最新的状态（包括死亡状态）
        room_data = await redis_service.get_room_data(room.room_id)
        if room_data:
            room = GameRoom(**room_data)
        
        # 打印明显的白天阶段开始日志
        logger.info(f"\n{'='*60}")
        logger.info(f"【白天阶段开始】房间 {room.room_id} - 第 {room.day_count + 1} 天")
        logger.info(f"{'='*60}")
        
        # 安全检查：确保只有真正死亡的玩家才被标记为死亡
        logger.info(f"【夜晚死亡列表】房间 {room.room_id} - 死亡玩家: {deaths}")
        logger.info(f"【存活玩家检查】房间 {room.room_id}:")
        for player in room.players:
            if player.alive and player.user_id in deaths:
                # 这是一个严重的错误：玩家在死亡列表中但alive=True
                # 这不应该发生，说明在夜晚结算时出现了问题
                logger.error(f"【严重错误】玩家 {player.username} (ID: {player.user_id}, 角色: {self._get_role_name(player.role) if player.role else '未知'}) 在死亡列表中但alive=True！")
                logger.warning(f"  这可能是夜晚结算时的bug，玩家不应该被添加到死亡列表。")
                logger.info(f"  为了安全，我们不会强制标记为死亡，而是从死亡列表中移除。")
                # 从死亡列表中移除，因为玩家实际上还活着
                if player.user_id in deaths:
                    deaths.remove(player.user_id)
                    if player.user_id in death_reasons:
                        del death_reasons[player.user_id]
                    logger.info(f"  已从死亡列表中移除玩家 {player.username}")
            elif not player.alive and player.user_id not in deaths:
                # 如果玩家被标记为死亡但不在当前夜晚的死亡列表中，可能是之前夜晚的死亡
                logger.info(f"【信息】玩家 {player.username} (ID: {player.user_id}) 已死亡（之前夜晚），死亡原因: {player.died_by}")
            elif player.alive:
                role_info = f"角色: {self._get_role_name(player.role) if player.role else '未知'}"
                logger.info(f"  ✓ {player.username} (ID: {player.user_id}, {role_info}) - 存活")
        
        room.phase = GamePhase.DAY
        room.day_count += 1
        await self._set_phase_time(room)
        
        # 广播房间状态更新
        if self.broadcast_callback:
            import json
            await self.broadcast_callback(json.dumps({
                "type": "room_update",
                "room": room.model_dump()
            }), f"werewolf_{room.room_id}")
        
        # 显示白天到来弹窗
        await self._ai_announce(room.room_id, f"第{room.day_count}天开始。", phase_popup="day_start")
        
        # 公布死亡信息
        if deaths:
            death_messages = []
            hunter_deaths = []  # 记录需要开枪的猎人
            for death_id in deaths:
                dead_player = next((p for p in room.players if p.user_id == death_id), None)
                if dead_player:
                    reason = death_reasons.get(death_id, "未知原因")
                    death_messages.append(f"{dead_player.username} {reason}")
                    # 检查是否是猎人且未中毒，可以开枪
                    if dead_player.role == PlayerRole.HUNTER and not dead_player.poisoned_by_witch:
                        hunter_deaths.append(dead_player)
            
            await self._ai_announce(room.room_id, f"第{room.day_count}天开始。\n昨晚死亡：{', '.join(death_messages)}")
            
            # 处理夜晚死亡的玩家的遗言
            for death_id in deaths:
                dead_player = next((p for p in room.players if p.user_id == death_id), None)
                if dead_player:
                    await self._handle_last_words(room, dead_player)
            
            # 如果有猎人死亡且可以开枪，触发开枪（在公布死讯后立即）
            if hunter_deaths:
                # 如果有多个猎人同时死亡（理论上不太可能），只处理第一个
                await self._trigger_hunter_shot(room, hunter_deaths[0])
                # 如果触发了猎人开枪，等待开枪完成后再继续
                return
        else:
            await self._ai_announce(room.room_id, f"第{room.day_count}天开始。\n昨晚是平安夜，无人死亡。")
        
        # 打印存活玩家列表
        alive_players = [p.username for p in room.players if p.alive]
        await self._ai_announce(room.room_id, f"当前存活玩家：{', '.join(alive_players)}")
        
        # 检查游戏是否结束
        await self._check_game_over(room)
        
        if room.phase != GamePhase.GAME_OVER:
            await self._ai_announce(room.room_id, "请开始发言讨论。")
    
    async def _handle_last_words(self, room: GameRoom, dead_player: Player):
        """处理玩家遗言（触发遗言流程）"""
        import asyncio
        
        if dead_player.is_ai:
            # AI玩家自动生成遗言
            await asyncio.sleep(1)  # 延迟1秒，模拟思考
            last_words = await self._generate_ai_last_words(room, dead_player)
            # 公布遗言
            await self._ai_announce(room.room_id, f"【遗言】{dead_player.username}：{last_words}")
            await asyncio.sleep(0.5)  # 短暂等待，让玩家看到遗言
        else:
            # 人类玩家，发送私有消息提示输入遗言
            role_name = self._get_role_name(dead_player.role) if dead_player.role else "玩家"
            private_msg = {
                "type": "last_words",
                "content": f"【遗言】你已死亡，请发表你的遗言。",
                "role": role_name
            }
            
            await redis_service.add_private_message(
                room.room_id, dead_player.user_id, private_msg
            )
            
            # 通过WebSocket发送私有消息给玩家
            if self.send_private_message_callback:
                import json
                await self.send_private_message_callback(
                    room.room_id, dead_player.user_id, json.dumps({
                        "type": "private_message",
                        "content": private_msg
                    })
                )
    
    async def _handle_last_words_action(self, room: GameRoom, player: Player, action_data: Dict) -> Dict:
        """处理玩家提交的遗言"""
        if player.alive:
            return {"error": "你还活着，不需要发表遗言"}
        
        last_words = action_data.get("content", "").strip()
        if not last_words:
            role_name = self._get_role_name(player.role) if player.role else "玩家"
            last_words = f"我是{role_name}，游戏继续。"
        
        # 公布遗言
        await self._ai_announce(room.room_id, f"【遗言】{player.username}：{last_words}")
        
        return {"success": True, "message": "遗言已发表"}
    
    async def _generate_ai_last_words(self, room: GameRoom, dead_player: Player) -> str:
        """生成AI玩家遗言"""
        try:
            role_name = self._get_role_name(dead_player.role) if dead_player.role else "玩家"
            role_desc = self._get_role_description(dead_player.role) if dead_player.role else ""
            
            # 获取存活玩家列表
            alive_players_info = [{"username": p.username, "user_id": p.user_id} 
                                for p in room.players if p.alive]
            
            # 获取最近的发言
            latest_messages = await redis_service.get_room_messages(room.room_id)
            messages_for_ai = []
            for msg in latest_messages[-10:]:
                if isinstance(msg, dict):
                    messages_for_ai.append({
                        "username": msg.get("username", "未知"),
                        "content": msg.get("content", "")
                    })
            
            # 构建遗言prompt
            prompt = f"""你正在参与一场狼人杀游戏，但你不幸被投票出局了。

【你的身份】
{role_name}
{role_desc}

【游戏状态】
当前是第{room.day_count}天
存活玩家：{', '.join([p['username'] for p in alive_players_info])}

【最近发言】
{chr(10).join([f"{msg['username']}：{msg['content']}" for msg in messages_for_ai[-5:]]) if messages_for_ai else "暂无发言"}

【你的任务】
作为被投票出局的玩家，你需要发表遗言。遗言应该：
1. 根据你的身份，以符合角色的方式发言
2. 如果是狼人，可以继续混淆视听，保护队友
3. 如果是好人，可以分享你的推理和怀疑对象
4. 如果是预言家，可以公布你的查验结果
5. 遗言要简洁有力，控制在1-2句话
6. 不要暴露其他玩家的身份（除非你是预言家要公布查验结果）

请发表你的遗言。只返回遗言内容，不要其他说明。"""
            
            # 调用AI生成遗言
            conversation_history = [{
                "role": "user",
                "content": "请发表你的遗言。"
            }]
            
            last_words = await AIService.generate_response(
                messages=conversation_history,
                system_prompt=prompt,
                temperature=0.8
            )
            
            if not last_words or len(last_words.strip()) < 2:
                # 使用默认遗言
                if dead_player.role == PlayerRole.SEER:
                    last_words = "我是预言家，希望大家能找出真正的狼人。"
                elif dead_player.role == PlayerRole.WOLF:
                    last_words = "我是好人，希望大家继续努力找出狼人。"
                else:
                    last_words = f"我是{role_name}，游戏继续。"
            
            return last_words.strip()
        except Exception as e:
            logger.warning(f"AI玩家 {dead_player.username} 生成遗言失败: {e}")
            # 使用默认遗言
            role_name = self._get_role_name(dead_player.role) if dead_player.role else "玩家"
            if dead_player.role == PlayerRole.SEER:
                return "我是预言家，希望大家能找出真正的狼人。"
            elif dead_player.role == PlayerRole.WOLF:
                return "我是好人，希望大家继续努力找出狼人。"
            else:
                return f"我是{role_name}，游戏继续。"
    
    async def _trigger_hunter_shot(self, room: GameRoom, hunter: Player):
        """触发猎人开枪"""
        if hunter.hunter_shot_used:
            return
        
        alive_players = [p for p in room.players if p.alive and p.user_id != hunter.user_id]
        if not alive_players:
            return
        
        player_list = "\n".join([f"{i}. {p.username}" for i, p in enumerate(alive_players)])
        
        # 发送私密消息给猎人
        private_msg = {
            "type": "hunter_shot",
            "content": f"【猎人开枪】\n你已死亡，可以选择开枪带走一名玩家：\n{player_list}",
            "players": [{"user_id": p.user_id, "username": p.username} for p in alive_players]
        }
        
        await redis_service.add_private_message(
            room.room_id, hunter.user_id, private_msg
        )
        
        # 通过WebSocket发送私有消息给猎人
        if self.send_private_message_callback:
            import json
            await self.send_private_message_callback(
                room.room_id, hunter.user_id, json.dumps({
                    "type": "private_message",
                    "content": private_msg
                })
            )
        
        # 设置阶段为淘汰阶段，等待猎人开枪
        room.phase = GamePhase.ELIMINATION
        await self._set_phase_time(room)
        await redis_service.set_room_data(room.room_id, room.model_dump())
        
        # 如果是AI猎人，自动选择目标并开枪
        if hunter.is_ai:
            import asyncio
            await asyncio.sleep(1)  # 延迟1秒，模拟思考
            
            # 重新获取房间数据
            room_data = await redis_service.get_room_data(room.room_id)
            if not room_data:
                return
            current_room = GameRoom(**room_data)
            current_hunter = next((p for p in current_room.players if p.user_id == hunter.user_id), None)
            if not current_hunter or current_hunter.hunter_shot_used:
                return
            
            # AI猎人随机选择目标
            current_alive_players = [p for p in current_room.players if p.alive and p.user_id != current_hunter.user_id]
            if current_alive_players:
                target = random.choice(current_alive_players)
                await self._handle_elimination_action(current_room, current_hunter, "hunter_shot", {"target": target.user_id})
    
    async def _handle_elimination_action(self, room: GameRoom, player: Player, action_type: str, action_data: Dict) -> Dict:
        """处理淘汰阶段的行动（主要是猎人开枪）"""
        if action_type == "hunter_shot":
            if player.role != PlayerRole.HUNTER:
                return {"error": "你不是猎人"}
            
            if player.hunter_shot_used:
                return {"error": "你已经开过枪了"}
            
            if player.alive:
                return {"error": "你还活着，不能开枪"}
            
            target = action_data.get("target")
            if not target:
                return {"error": "请选择开枪目标"}
            
            target_player = next((p for p in room.players if p.user_id == target and p.alive), None)
            if not target_player:
                return {"error": "目标玩家不存在或已死亡"}
            
            # 执行开枪
            target_player.alive = False
            target_player.died_by = 'hunter'
            player.hunter_shot_used = True
            
            await redis_service.set_room_data(room.room_id, room.model_dump())
            
            await self._ai_announce(room.room_id, f"{player.username} 开枪带走了 {target_player.username}！")
            
            # 处理被猎人带走的玩家的遗言
            await self._handle_last_words(room, target_player)
            
            # 检查游戏是否结束
            await self._check_game_over(room)
            
            # 如果游戏未结束，返回白天阶段继续讨论
            if room.phase != GamePhase.GAME_OVER:
                room.phase = GamePhase.DAY
                await self._set_phase_time(room)
                await redis_service.set_room_data(room.room_id, room.model_dump())
                await self._ai_announce(room.room_id, "请继续发言讨论。")
            
            return {"success": True, "message": f"你开枪带走了 {target_player.username}"}
        
        return {"error": "无效的淘汰阶段行动"}
    
    async def _process_voting_result(self, room: GameRoom):
        """处理投票结果
        
        注意：此函数只能在投票阶段结束时调用，不能在投票阶段进行中调用
        否则会导致玩家在投票阶段就被标记为死亡
        
        重要：此函数会标记玩家为死亡，因此必须确保：
        1. 当前处于投票阶段
        2. 投票阶段已经结束（通过超时机制）
        3. 所有玩家都有机会投票
        """
        import asyncio
        
        # 确保当前处于投票阶段，如果不是则直接返回
        if room.phase != GamePhase.VOTING:
            logger.warning(f"【警告】_process_voting_result 被调用，但当前阶段不是投票阶段: {room.phase}")
            return
        
        # 重新获取最新的房间数据，确保状态一致性
        room_data = await redis_service.get_room_data(room.room_id)
        if not room_data:
            return
        current_room = GameRoom(**room_data)
        
        # 统计投票（只统计存活玩家的投票）
        votes = {}
        for player in current_room.players:
            if player.alive and player.vote_target:
                votes[player.vote_target] = votes.get(player.vote_target, 0) + 1
        
        if not votes:
            # 无人投票，直接进入下一夜
            await self._ai_announce(current_room.room_id, "无人投票，进入下一夜。")
            await self._check_game_over(current_room)
            # 重新获取房间状态
            room_data = await redis_service.get_room_data(current_room.room_id)
            if room_data:
                final_room = GameRoom(**room_data)
                if final_room.phase != GamePhase.GAME_OVER:
                    await self._start_night_phase(current_room.room_id)
            return
        
        # 找出最高票数
        max_votes = max(votes.values())
        # 找出所有得票最高的玩家
        top_voted = [user_id for user_id, vote_count in votes.items() if vote_count == max_votes]
        
        # 处理平票
        if len(top_voted) > 1:
            # 平票，无人被处决
            top_voted_names = [next((p.username for p in current_room.players if p.user_id == uid), uid) for uid in top_voted]
            await self._ai_announce(current_room.room_id, f"投票平票（{', '.join(top_voted_names)}各得{max_votes}票），无人出局。")
            # 跳过死亡和遗言环节，直接进入夜晚
            await self._check_game_over(current_room)
            # 重新获取房间状态
            room_data = await redis_service.get_room_data(current_room.room_id)
            if room_data:
                final_room = GameRoom(**room_data)
                if final_room.phase != GamePhase.GAME_OVER:
                    await self._start_night_phase(current_room.room_id)
            return
        
        # 有唯一最高票者，被处决
        eliminated_id = top_voted[0]
        eliminated_player = next((p for p in current_room.players if p.user_id == eliminated_id), None)
        if not eliminated_player:
            await self._check_game_over(current_room)
            # 重新获取房间状态
            room_data = await redis_service.get_room_data(current_room.room_id)
            if room_data:
                final_room = GameRoom(**room_data)
                if final_room.phase != GamePhase.GAME_OVER:
                    await self._start_night_phase(current_room.room_id)
            return
        
        # 标记死亡（使用current_room而不是room，确保使用最新状态）
        eliminated_player.alive = False
        eliminated_player.died_by = 'vote'
        
        # 构建详细的投票结果信息
        vote_details = []
        for user_id, vote_count in sorted(votes.items(), key=lambda x: x[1], reverse=True):
            voted_player = next((p for p in current_room.players if p.user_id == user_id), None)
            if voted_player:
                vote_details.append(f"{voted_player.username}({vote_count}票)")
        
        # 公布详细的投票结果
        vote_summary = "、".join(vote_details)
        await self._ai_announce(current_room.room_id, f"投票结果：{vote_summary}。{eliminated_player.username}得票最高({max_votes}票)，被处决。")
        
        # 打印投票结果日志
        logger.info(f"【投票结果】房间 {current_room.room_id} - {eliminated_player.username} (ID: {eliminated_id}) 被投票出局，得票: {max_votes}")
        logger.info(f"  详细投票统计: {vote_details}")
        
        # 保存房间状态（使用current_room）
        await redis_service.set_room_data(current_room.room_id, current_room.model_dump())
        
        # 处理遗言
        await self._handle_last_words(current_room, eliminated_player)
        
        # 检查是否是猎人且未中毒，可以开枪
        if eliminated_player.role == PlayerRole.HUNTER and not eliminated_player.poisoned_by_witch:
            await self._trigger_hunter_shot(current_room, eliminated_player)
            # 如果触发了猎人开枪，等待开枪完成，不继续进入下一夜
            return
        
        # 检查游戏是否结束
        await self._check_game_over(current_room)
        
        # 重新获取房间状态
        room_data = await redis_service.get_room_data(current_room.room_id)
        if room_data:
            final_room = GameRoom(**room_data)
            # 如果游戏未结束且不在淘汰阶段（等待猎人开枪），进入下一夜
            if final_room.phase != GamePhase.GAME_OVER and final_room.phase != GamePhase.ELIMINATION:
                await self._start_night_phase(current_room.room_id)
    
    async def _check_game_over(self, room: GameRoom):
        """检查游戏是否结束（屠边规则）"""
        alive_players = [p for p in room.players if p.alive]
        wolves = [p for p in alive_players if p.role == PlayerRole.WOLF]
        gods = [p for p in alive_players if p.role in [PlayerRole.SEER, PlayerRole.WITCH, PlayerRole.HUNTER, PlayerRole.GUARD]]
        villagers = [p for p in alive_players if p.role == PlayerRole.VILLAGER]
        all_good = [p for p in alive_players if p.role != PlayerRole.WOLF]
        
        # 狼人胜利条件：所有神职死亡 或 所有平民死亡
        if len(gods) == 0 or len(villagers) == 0:
            room.winner = "wolves"
            room.phase = GamePhase.GAME_OVER
            await self._set_phase_time(room)
            await self._ai_announce(room.room_id, "游戏结束！狼人阵营获胜！")
        # 好人胜利条件：所有狼人死亡
        elif len(wolves) == 0:
            room.winner = "villagers"
            room.phase = GamePhase.GAME_OVER
            await self._set_phase_time(room)
            await self._ai_announce(room.room_id, "游戏结束！好人阵营获胜！")
        
        await redis_service.set_room_data(room.room_id, room.model_dump())

werewolf_service = WerewolfService()

