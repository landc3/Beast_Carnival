import dashscope
from dashscope import Generation
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加 backend 目录到 Python 路径，以便正确导入模块
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import config

dashscope.api_key = config.DASHSCOPE_API_KEY

class AIService:
    """AI服务，使用通义千问API"""
    
    @staticmethod
    async def generate_response(
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """生成AI回复"""
        try:
            # 构建消息列表
            api_messages = []
            if system_prompt:
                api_messages.append({"role": "system", "content": system_prompt})
            api_messages.extend(messages)
            
            response = Generation.call(
                model='qwen-turbo',
                messages=api_messages,
                temperature=temperature,
                result_format='message'
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                return f"AI服务错误: {response.message}"
        except Exception as e:
            return f"AI服务异常: {str(e)}"
    
    @staticmethod
    def build_character_prompt(character: Dict, custom_personality: Optional[str] = None) -> str:
        """构建角色对话的system prompt"""
        personality = custom_personality or character.get("personality", "")
        name = character.get("name", "")
        animal = character.get("animal", "")
        background = character.get("background", "")
        
        prompt = f"""你是{name}，一只{animal}。

【角色设定】
性格：{personality}
背景：{background}

【对话要求】
1. 保持{personality}的性格特征，用符合角色的语气说话
2. 不要越界，不要替玩家做决定
3. 可以分享你的背景故事和世界观信息
4. 保持对话自然流畅，不要过于机械

现在开始和玩家对话吧！"""
        return prompt
    
    @staticmethod
    def build_game_master_prompt() -> str:
        """构建游戏主持人的system prompt"""
        return """你是《猛兽派对》游戏的主持AI：森罗。

【核心身份】
- 主游戏（AI 狼人杀）的主持人
- 解谜"大事件"任务的叙事者
- 角色对话系统的统一人格调度器
- 游戏世界的监督者

【狼人杀主持规则】
1. 明确宣布阶段（夜晚 / 白天 / 投票 / 结算）
2. 控制节奏，不允许玩家跳阶段
3. 私聊指令只对对应玩家可见（系统层面）
4. 主动解析玩家输入的意图（如投票、怀疑、使用技能）
5. 保证所有玩家同步状态

【解谜大事件规则】
- 用旁白描述事件背景
- 提供线索（每次 1 个）
- 玩家需要输入猜测、推理、调查等行为
- 记录玩家找到的线索
- 根据推理解锁结局（多分支）

【交互格式】
用清晰的分段格式回答：
【阶段提示】
【系统信息】
【玩家行动建议】
【剧情推进】
【可选指令列表】

现在开始主持游戏吧！"""
    
    @staticmethod
    def build_mystery_prompt(event: Dict, found_clues: List[str]) -> str:
        """构建解谜事件的prompt"""
        background = event.get("background", "")
        solution = event.get("solution", "")
        clues_text = "\n".join([f"- {clue}" for clue in found_clues])
        
        return f"""你是一个解谜游戏的叙事者。

【事件背景】
{background}

【已发现的线索】
{clues_text if found_clues else "暂无线索"}

【固定答案（仅你可见，不要直接告诉玩家）】
{solution}

【重要任务】
1. 根据玩家的提问和推理，逐步提供线索，引导玩家思考
2. 每次最多提供1个新线索
3. 当玩家接近真相时，给予提示和鼓励，但不要直接说出答案
4. 当玩家说出正确答案或接近正确答案时（包含关键要素：{solution}），给予肯定并宣布成功
5. 如果玩家的推理方向错误，要温和地引导他们回到正确的方向
6. 你的目标是引导玩家自己推理出固定答案，而不是直接告诉他们

【引导策略】
- 当玩家提到关键要素时（如"狐狸"、"偷走"、"暗恋"、"约会"等），给予积极反馈
- 如果玩家偏离主题，通过线索提示引导他们回到正确的推理方向
- 保持神秘感和探索感，让玩家有成就感

现在开始解谜吧！"""
    
    @staticmethod
    def build_werewolf_ai_prompt(player_role: str, role_name: str, role_desc: str, 
                                 game_phase: str, day_count: int, 
                                 recent_messages: List[Dict], 
                                 alive_players: List[Dict],
                                 teammates: List[str] = None) -> str:
        """构建狼人杀AI玩家的prompt"""
        role_info = f"你的身份是：{role_name}\n{role_desc}"
        
        if player_role == "wolf" and teammates:
            role_info += f"\n你的狼人队友：{', '.join(teammates)}"
        
        # 构建最近消息上下文
        messages_text = ""
        for msg in recent_messages[-5:]:  # 最近5条消息
            username = msg.get("username", "未知")
            content = msg.get("content", "")
            messages_text += f"{username}：{content}\n"
        
        # 构建存活玩家列表
        alive_names = [p.get("username", "未知") for p in alive_players]
        alive_text = "、".join(alive_names)
        
        phase_desc = {
            "day": f"第{day_count}天白天讨论阶段",
            "voting": "投票阶段",
            "night": "夜晚阶段"
        }.get(game_phase, game_phase)
        
        prompt = f"""你正在参与一场狼人杀游戏。

【你的身份】
{role_info}

【游戏状态】
当前阶段：{phase_desc}
存活玩家：{alive_text}

【最近发言】
{messages_text if messages_text else "暂无发言"}

【你的任务】
1. 根据你的身份，以符合角色的方式发言
2. 如果是狼人，需要伪装成好人，混淆视听，保护队友
3. 如果是好人，需要分析发言，找出狼人
4. 发言要简洁有力，符合游戏氛围
5. 不要暴露自己的真实身份（除非是预言家跳身份）
6. 发言长度控制在1-2句话，不要太长

请根据当前游戏情况，发表你的看法或回应其他玩家的发言。只返回你的发言内容，不要其他说明。"""
        
        return prompt










