# 狼人杀游戏完整开发Prompt

## 项目背景

你是一个全栈AI开发助手，需要基于现有的《Beast Carnival》项目，完善并实现一个完整的12人标准版狼人杀游戏。项目使用FastAPI后端、Vue3前端、WebSocket实时通信、Redis数据存储，AI服务使用通义千问API。

## 现有代码结构

### 后端结构
- `backend/main.py` - FastAPI主应用，包含WebSocket路由
- `backend/services/werewolf_service.py` - 狼人杀游戏逻辑服务
- `backend/models/game.py` - 游戏数据模型（GameRoom, Player, GamePhase, PlayerRole）
- `backend/services/ai_service.py` - AI服务，调用通义千问API
- `backend/services/redis_service.py` - Redis数据存储服务

### 前端结构
- `frontend/src/views/Werewolf.vue` - 狼人杀游戏界面
- 包含房间创建/加入、玩家列表、消息区域、私有消息显示

### 现有功能
- ✅ 房间创建和加入
- ✅ 身份分配（部分角色：狼人、平民、预言家、女巫、猎人）
- ✅ 基础的夜晚/白天/投票阶段
- ✅ WebSocket实时通信
- ✅ 公共消息和私有消息分离
- ❌ **缺少守卫角色**
- ❌ **缺少完整的夜晚行动流程**
- ❌ **缺少AI主持人智能引导**
- ❌ **缺少女巫技能完整实现（解药/毒药）**
- ❌ **缺少守卫技能实现**
- ❌ **缺少猎人技能实现（开枪）**
- ❌ **缺少完整的游戏阶段控制**

## 必须实现的游戏规则

### 一、角色配置（12人标准局）

#### 🐺 狼人阵营（4人）
- **狼人 × 4**
  - 每晚共同决定杀死一名玩家
  - 白天伪装成好人，混淆视听、带节奏

#### 👥 好人阵营（8人）

##### 🌟 神职角色（4人）

1. **预言家 × 1**
   - 每晚可查验一名玩家身份（得知是"好人"还是"狼人"）
   - 是好人阵营的核心信息源

2. **女巫 × 1**
   - 拥有解药（可救被刀玩家）和毒药（可毒杀任意玩家）
   - 每瓶只能用一次，每晚只能使用一瓶
   - **首夜不能自救**（重要规则）

3. **猎人 × 1**
   - 被投票出局或被狼刀（且未被毒）时，可开枪带走一名玩家
   - 若被女巫毒死，则无法开枪

4. **守卫 × 1**
   - 每晚可守护一人（包括自己），防止其被刀
   - **不能连续两晚守同一人**
   - 若守的人被女巫救，可能出现"同守同救"导致死亡

##### 👨‍🌾 平民（4人）
- 无任何技能，全程"闭眼"
- 依靠白天发言、逻辑推理和信任神职来找出狼人

### 二、游戏流程

#### 阶段顺序
1. **准备阶段（WAITING）** - 玩家加入房间，等待开始
2. **身份分配（IDENTITY_ASSIGN）** - 系统分配身份，发送私有消息
3. **夜晚阶段（NIGHT）** - 各角色依次行动
4. **白天阶段（DAY）** - 玩家发言讨论
5. **投票阶段（VOTING）** - 投票出局
6. **淘汰阶段（ELIMINATION）** - 处理被淘汰玩家（如猎人开枪）
7. **游戏结束（GAME_OVER）** - 判断胜负

#### 夜晚行动顺序（重要！）
1. **守卫行动** - 选择守护目标
2. **狼人行动** - 共同决定击杀目标
3. **预言家行动** - 选择查验目标
4. **女巫行动** - 选择是否使用解药/毒药

#### 白天流程
1. AI主持人宣布夜晚结果（谁被刀、是否被救、是否有人死亡）
2. 玩家依次发言（或自由发言）
3. 进入投票阶段
4. 宣布投票结果
5. 处理被投票出局玩家的技能（如猎人开枪）

### 三、胜利条件

- **好人胜**：所有狼人被投出或击杀
- **狼人胜**：狼人数量 ≥ 好人数量

### 四、安全信息隔离原则
    
- 夜晚行动时，主持人只向对应角色玩家显示其操作选项
- 其他玩家不应看到私密信息
- 在WebSocket中通过私有消息通道发送身份和行动信息
- 公共消息只显示游戏阶段和公开信息

### 五、输出要求

- 使用清晰的中文提示（如"【夜晚】狼人们，请共同决定要击杀的玩家"）
- 每轮开始/结束打印当前存活玩家列表
- AI主持人用分段格式提示：
  ```
  【阶段提示】
  【系统信息】
  【玩家行动建议】
  【剧情推进】
  【可选指令列表】
  ```

## 开发任务清单

### 任务1：完善数据模型

**文件：`backend/models/game.py`**

需要添加/修改：

1. **PlayerRole枚举** - 添加 `GUARD = "guard"`（守卫）
2. **Player模型** - 添加以下字段：
   - `guarded: bool = False` - 是否被守卫守护
   - `checked_by_seer: bool = False` - 是否被预言家查验过
   - `saved_by_witch: bool = False` - 是否被女巫救过
   - `poisoned_by_witch: bool = False` - 是否被女巫毒过
   - `guard_target: Optional[str] = None` - 守卫守护的目标（用于检查连续守护）
   - `last_guard_target: Optional[str] = None` - 上一晚守卫的目标
   - `witch_antidote_used: bool = False` - 女巫解药是否已使用
   - `witch_poison_used: bool = False` - 女巫毒药是否已使用
   - `hunter_shot_used: bool = False` - 猎人是否已开枪

3. **GameRoom模型** - 添加以下字段：
   - `night_actions: Dict[str, Dict]` - 记录夜晚行动 {role: {action_type: target}}
   - `current_night_phase: Optional[str]` - 当前夜晚子阶段（guard/wolf/seer/witch）
   - `eliminated_tonight: Optional[str]` - 今晚被击杀的玩家
   - `saved_tonight: Optional[str]` - 今晚被救的玩家

### 任务2：完善角色配置

**文件：`backend/services/werewolf_service.py`**

修改 `ROLES` 列表为12人标准配置：
```python
ROLES = [
    PlayerRole.WOLF, PlayerRole.WOLF, PlayerRole.WOLF, PlayerRole.WOLF,  # 4狼人
    PlayerRole.SEER,  # 1预言家
    PlayerRole.WITCH,  # 1女巫
    PlayerRole.HUNTER,  # 1猎人
    PlayerRole.GUARD,  # 1守卫
    PlayerRole.VILLAGER, PlayerRole.VILLAGER, PlayerRole.VILLAGER, PlayerRole.VILLAGER  # 4平民
]
```

### 任务3：实现完整的夜晚行动流程

**文件：`backend/services/werewolf_service.py`**

需要实现以下方法：

1. **`async def _start_night_phase(room: GameRoom)`**
   - 进入夜晚阶段
   - 重置夜晚行动记录
   - 按顺序引导各角色行动

2. **`async def _handle_guard_action(room: GameRoom, player: Player, target: str)`**
   - 守卫选择守护目标
   - 检查不能连续两晚守同一人
   - 记录守护目标

3. **`async def _handle_wolf_action(room: GameRoom, wolves: List[Player], target: str)`**
   - 狼人共同决定击杀目标
   - 需要所有狼人都投票才能确定
   - 记录击杀目标

4. **`async def _handle_seer_action(room: GameRoom, player: Player, target: str)`**
   - 预言家查验目标
   - 返回"好人"或"狼人"（不显示具体身份）

5. **`async def _handle_witch_action(room: GameRoom, player: Player, action: str, target: Optional[str])`**
   - 女巫使用解药（救被刀玩家）
   - 女巫使用毒药（毒杀任意玩家）
   - 检查解药/毒药是否已使用
   - 检查首夜不能自救

6. **`async def _process_night_results(room: GameRoom)`**
   - 处理夜晚行动结果
   - 判断谁被击杀、谁被救、谁死亡
   - 处理"同守同救"情况（守卫守护+女巫救=死亡）
   - 更新玩家状态
   - 进入白天阶段

### 任务4：实现白天发言和投票

**文件：`backend/services/werewolf_service.py`**

1. **`async def _start_day_phase(room: GameRoom)`**
   - 进入白天阶段
   - AI主持人宣布夜晚结果
   - 显示当前存活玩家列表

2. **`async def _handle_day_speech(room: GameRoom, player: Player, content: str)`**
   - 处理玩家白天发言
   - 添加到公共消息

3. **`async def _start_voting_phase(room: GameRoom)`**
   - 进入投票阶段
   - 引导玩家投票

4. **`async def _process_voting_result(room: GameRoom)`**
   - 统计投票结果
   - 处理平票情况（可能需要重新投票或无人出局）
   - 宣布被投票出局的玩家
   - 触发被投票玩家的技能（如猎人开枪）

### 任务5：实现角色技能

**文件：`backend/services/werewolf_service.py`**

1. **猎人技能**
   - `async def _handle_hunter_shot(room: GameRoom, hunter: Player, target: str)`
   - 被投票出局或被狼刀时触发
   - 检查是否被毒（被毒不能开枪）
   - 选择开枪目标并执行

2. **守卫技能**
   - 已在夜晚行动中实现

3. **女巫技能**
   - 已在夜晚行动中实现

4. **预言家技能**
   - 已在夜晚行动中实现

### 任务6：实现AI主持人智能引导

**文件：`backend/services/werewolf_service.py`**

创建方法：
```python
async def _ai_guide_phase(room: GameRoom, phase: str, context: Dict = None)
```

使用 `AIService.generate_response()` 调用AI，传入：
- 当前游戏状态
- 当前阶段
- 需要引导的内容

AI主持人应该：
- 清晰宣布当前阶段
- 提示当前可执行的操作
- 引导玩家进行下一步行动
- 用分段格式输出

### 任务7：完善WebSocket消息处理

**文件：`backend/main.py`**

在 `werewolf_game` WebSocket处理函数中：

1. 解析玩家行动类型：
   - `night_action` - 夜晚行动（包含role和target）
   - `day_speech` - 白天发言
   - `vote` - 投票
   - `skill_use` - 使用技能（如猎人开枪）

2. 根据游戏阶段和玩家身份，调用对应的处理方法

3. 实时广播游戏状态更新

### 任务8：完善前端UI

**文件：`frontend/src/views/Werewolf.vue`**

需要添加/改进：

1. **夜晚行动界面**
   - 根据玩家身份显示对应的行动选项
   - 守卫：选择守护目标（显示不能连续守护的提示）
   - 狼人：显示其他狼人，共同选择击杀目标
   - 预言家：选择查验目标
   - 女巫：显示解药/毒药状态，选择使用（显示被刀玩家）

2. **白天发言界面**
   - 显示当前发言顺序
   - 发言倒计时（可选）

3. **投票界面**
   - 显示所有存活玩家
   - 单选投票
   - 显示投票进度

4. **游戏状态显示**
   - 当前阶段（夜晚/白天/投票）
   - 当前存活玩家列表
   - 游戏天数

5. **私有消息区域**
   - 更明显的显示
   - 区分不同类型的私有消息（身份、查验结果、行动确认等）

### 任务9：添加游戏阶段自动推进

**文件：`backend/services/werewolf_service.py`**

实现阶段自动推进逻辑：

1. 夜晚阶段：所有角色行动完成后，自动进入白天
2. 白天阶段：发言时间结束或所有玩家发言后，自动进入投票
3. 投票阶段：所有玩家投票后，自动处理结果并进入下一轮

### 任务10：完善游戏结束判断

**文件：`backend/services/werewolf_service.py`**

在 `_check_game_over` 方法中：

1. 每轮结束后检查胜负条件
2. 统计存活狼人和好人数量
3. 判断是否满足胜利条件
4. 宣布游戏结果

## 代码实现要求

### 1. 错误处理
- 所有方法都要有异常处理
- 返回清晰的错误信息
- 防止非法操作（如已死亡玩家行动、非当前阶段行动等）

### 2. 数据一致性
- 使用Redis事务或锁保证数据一致性
- 确保所有玩家看到的状态一致

### 3. 代码规范
- 使用类型提示
- 添加必要的注释
- 遵循PEP 8代码风格

### 4. 测试要点
- 测试12人满员游戏
- 测试所有角色技能
- 测试各种边界情况（平票、同守同救等）

## 关键实现细节

### 夜晚行动顺序处理
```python
async def _process_night_actions(room: GameRoom):
    # 1. 守卫行动
    guard = next((p for p in room.players if p.role == PlayerRole.GUARD and p.alive), None)
    if guard and room.night_actions.get("guard"):
        target = room.night_actions["guard"]["target"]
        # 检查不能连续守护
        if target != guard.last_guard_target:
            guard.guard_target = target
            # 发送确认消息
    
    # 2. 狼人行动
    wolves = [p for p in room.players if p.role == PlayerRole.WOLF and p.alive]
    if room.night_actions.get("wolf"):
        # 需要所有狼人都投票
        wolf_votes = room.night_actions["wolf"]["votes"]
        if len(wolf_votes) == len(wolves):
            target = max(set(wolf_votes), key=wolf_votes.count)  # 多数决定
            room.eliminated_tonight = target
    
    # 3. 预言家行动
    seer = next((p for p in room.players if p.role == PlayerRole.SEER and p.alive), None)
    if seer and room.night_actions.get("seer"):
        target = room.night_actions["seer"]["target"]
        target_player = next((p for p in room.players if p.user_id == target), None)
        if target_player:
            result = "狼人" if target_player.role == PlayerRole.WOLF else "好人"
            # 发送私有消息给预言家
    
    # 4. 女巫行动
    witch = next((p for p in room.players if p.role == PlayerRole.WITCH and p.alive), None)
    if witch and room.night_actions.get("witch"):
        action = room.night_actions["witch"]
        if action.get("use_antidote") and not witch.witch_antidote_used:
            saved = action.get("antidote_target")
            room.saved_tonight = saved
            witch.witch_antidote_used = True
        if action.get("use_poison") and not witch.witch_poison_used:
            poisoned = action.get("poison_target")
            # 标记被毒玩家
```

### 同守同救处理
```python
# 在 _process_night_results 中
if room.eliminated_tonight:
    eliminated_player = next((p for p in room.players if p.user_id == room.eliminated_tonight), None)
    if eliminated_player:
        # 检查是否被守卫守护
        guard = next((p for p in room.players if p.role == PlayerRole.GUARD and p.alive), None)
        guarded = guard and guard.guard_target == room.eliminated_tonight
        
        # 检查是否被女巫救
        saved = room.saved_tonight == room.eliminated_tonight
        
        # 同守同救 = 死亡
        if guarded and saved:
            eliminated_player.alive = False
            await self._ai_announce(room.room_id, f"{eliminated_player.username}因同守同救死亡！")
        elif guarded or saved:
            # 被救或守护，不死
            pass
        else:
            # 正常死亡
            eliminated_player.alive = False
```

## 交付检查清单

完成开发后，确保以下功能都正常工作：

- [ ] 12人标准配置（4狼+4神+4民）正确分配
- [ ] 守卫技能：每晚守护一人，不能连续守护同一人
- [ ] 狼人技能：每晚共同击杀一人
- [ ] 预言家技能：每晚查验一人身份
- [ ] 女巫技能：解药救被刀玩家，毒药毒杀玩家，首夜不能自救
- [ ] 猎人技能：被投票/被刀时可开枪，被毒不能开枪
- [ ] 夜晚行动按正确顺序进行
- [ ] 同守同救规则正确处理
- [ ] 白天发言和投票流程完整
- [ ] 游戏胜负判断正确
- [ ] 私有消息正确发送给对应玩家
- [ ] AI主持人引导清晰
- [ ] 前端UI显示所有必要信息
- [ ] WebSocket实时同步正常

## 开始开发

请按照以上要求，逐步实现所有功能。遇到不明确的地方，请根据标准狼人杀规则做出合理假设。优先实现核心游戏逻辑，再完善UI和AI引导。

 帮我写出分段的prompt提示词，不需要一次性回答全部