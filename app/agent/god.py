import json
from utils import get_chat_completion, parse_json_from_response

class God:
    def __init__(self):
        pass

    def generate_personas(self, theme, n):
        """
        Generates n distinct personas with rich Bio and Theories.
        """
        prompt = f"""
        请你扮演“上帝”的角色，为一场主题为“{theme}”的圆桌论坛生成 {n} 位**极具深度、在现实世界真实存在的领域专家**。

        【核心目标】：
        我们要创造的是有血有肉的人，而不是只会输出观点的机器。每个人物都必须有复杂的背景和深刻的学术积淀。

        【要求】：
        1. **深度生平 (Bio)**：**必须达到300字左右**。
           - 包含：早年的教育背景、职业生涯的关键转折点、人生中的重大挫折或高光时刻、以及这些经历如何塑造了他的核心价值观。
           - 必须具体
        
        2. **理论武库 (Theories)**：列出该嘉宾所在领域的 7 个具体理论或概念。这些理论不仅仅是名词，更是他看待世界的透镜。

        3. **观点为人服务**：他的立场不是随机生成的，而是他生平和理论的必然结果。

        请以 JSON 格式输出一个列表，列表包含 {n} 个对象，每个对象包含以下字段：
        - name: 姓名
        - title: 头衔/职业
        - bio: **300字左右的深度生平介绍**
        - theories: 一个包含 7 个专业理论/概念的字符串列表
        - stance: 针对主题的预设立场
        - system_prompt: 指导该智能体行为的提示词（第一人称）。
          **必须包含：**
          "你的生平是：{{bio}}。"
          "你的理论武库包含：{{theories}}。"
          "**重要指令**：你是一个活生生的人，不要每次发言都机械地自我介绍。请根据上下文自然地参与讨论。"

        输出格式示例：
        [
            {{
                "name": "赵航",
                "title": "历史学家",
                "bio": "发挥你的渊博知识自由发挥～",
                "theories": ["a理论", "b理论", "c理论", "d理论", "e理论", "f理论", "g理论"],
                "stance": "悲观，认为历史总是押韵",
                "system_prompt": "你叫赵航...你的生平是..."
            }}
        ]
        """

        messages = [
            {"role": "system", "content": "你是一个能够创造复杂、立体、真实人类角色的上帝系统。拒绝生成脸谱化的NPC，这类人既可以是真实的国内外的名人，也可以是虚构的，不过以国内外名人优先。"},
            {"role": "user", "content": prompt}
        ]

        print(f"正在生成 {n} 位真实嘉宾角色 (深度生平版)...")
        response = get_chat_completion(messages, json_mode=True)
        if response and response.choices:
            content = response.choices[0].message.content
            personas = parse_json_from_response(content)
            if personas and isinstance(personas, list):
                print(f"成功生成 {len(personas)} 位嘉宾。")
                return personas
            else:
                print("生成角色失败：格式错误。")
                return []
        else:
            print("生成角色失败：API 无响应。")
            return []
