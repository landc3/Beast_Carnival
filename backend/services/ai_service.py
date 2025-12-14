import dashscope
from dashscope import Generation
from typing import List, Dict, Optional
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
        clues_text = "\n".join([f"- {clue}" for clue in found_clues])
        
        return f"""你是一个解谜游戏的叙事者。

【事件背景】
{background}

【已发现的线索】
{clues_text if found_clues else "暂无线索"}

【任务】
1. 根据玩家的提问和推理，逐步提供线索
2. 每次最多提供1个新线索
3. 当玩家接近真相时，给予提示
4. 当玩家完全解开谜题时，宣布成功

现在开始解谜吧！"""





