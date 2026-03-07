import json
from utils import get_chat_completion, parse_json_from_response
from app.agent.memory import PrivateMemory

class BaseAgent:
    def __init__(self, name, system_prompt):
        self.name = name
        self.system_prompt = system_prompt


class ModeratorAgent(BaseAgent):
    def __init__(self, theme, name="主持人", system_prompt=None):
        self.theme = theme
        default_prompt = "你是一场圆桌论坛的专业主持人。你的职责是引导话题、总结发言、并控制流程。"
        super().__init__(name, system_prompt or default_prompt)

    def opening(self, guests):
        guest_intros = "\n".join([f"- {g['name']} ({g['title']}): {g['stance']}" for g in guests])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        嘉宾名单：
        {guest_intros}

        请做开场发言：
        1. 欢迎大家。
        2. 简要介绍主题背景。
        3. 介绍在场嘉宾。
        4. 宣布圆桌论坛正式开始。

        **重要要求**：
        - 请直接输出发言内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式，就像你在现场说话一样。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

    def periodic_summary(self, messages):
        """
        Summarize the recent messages (window).
        """
        msgs_text = "\n".join([f"{m['speaker']}: {m['content']}" for m in messages])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        以下是刚才几位嘉宾的发言：
        {msgs_text}

        请对以上内容进行简要总结，保留每位发言者的核心观点（精髓）。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

    def closing(self, summary_history):
        """
        Final summary and closing.
        """
        history_text = "\n".join([f"阶段总结: {s}" for s in summary_history])
        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        论坛时间已到。以下是本次论坛的各个阶段总结：
        {history_text}

        请对整场论坛进行最终总结，且必须严格包含以下四个部分：
        1. **议题脉络**：梳理讨论的发展过程。
        2. **共识**：大家达成一致的观点。
        3. **分歧**：大家争论不休的观点。
        4. **未解决问题**：留待未来探讨的问题。

        最后宣布论坛结束。

        **重要要求**：
        - 请直接输出总结内容，不要包含任何前缀（如“主持人 20:15:20”）。
        - 不要使用脚本格式。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

class ParticipantAgent(BaseAgent):
    def __init__(self, name, persona, n_participants, theme, ablation_flags=None):
        system_prompt = persona.get('system_prompt', "你是一个参与圆桌讨论的嘉宾。")
        super().__init__(name, system_prompt)
        self.title = persona.get('title', "专家")
        self.bio = persona.get('bio', "无")
        self.theories = persona.get('theories', [])
        self.stance = persona.get('stance', "中立")
        self.priority = 100
        self.private_memory = PrivateMemory(n_participants)
        self.has_spoken = False
        self.theme = theme
        self.ablation_flags = ablation_flags or {}

    def think(self, context):
        """
        Fast Thinking: Analyze context using Bio and Theories.
        """
        my_memory = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
        
        prompt = f"""
        无需提及但要记住主题：
        {self.theme}
        【当前环境】
        {context}
        """
        
        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
        【你的私有记忆】
        {my_memory}
        """

        prompt += f"""
        【你的生平与理论】
        生平: {self.bio}
        理论武库: {', '.join(self.theories)}

        请进行“快思考”，你的任务是通过主观思考判断自己是否需要申请讲话。
        **不要使用通用的官方的逻辑（如利弊分析），不要和稀泥，不要攻击他人。**
        **请从你的理论武库中挑选1-2个理论作为切入点。**

        请进行一段自由的内心独白（Inner Monologue），表达你对当前讨论的真实看法、情感反应以及是否想要发言的冲动。
        你可以带有个人情绪，可以偏激，可以热情，切忌机械化。

        最后，请明确给出你的决策：是申请发言（APPLY_SPEAK）还是继续倾听（LISTEN）。

        请严格按照以下格式输出：
        DECISION: [APPLY_SPEAK | LISTEN]
        INNER_MONOLOGUE: [你的内心独白内容]
        THEORY_USED: [引用的理论，如果没有则填无]
        PREVIOUS_VIEW: [对前一个发言者的简要看法]
        BENEFIT: [如果发言，你的发言能带来什么新视角]
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = get_chat_completion(messages) # No json_mode=True, use text parsing
        if response:
            content = response.choices[0].message.content
            return self._parse_think_response(content)
        return None

    def _parse_think_response(self, content):
        result = {
            "action": "listen",
            "mind": "",
            "theory_used": "",
            "previous": "",
            "benefit": ""
        }
        try:
            normalized = content.replace("：", ":")
            lines = normalized.strip().split('\n')
            current_key = None
            
            for line in lines:
                line = line.strip()
                if not line: continue

                upper_line = line.upper()
                if upper_line.startswith("DECISION:") or upper_line.startswith("行动:") or upper_line.startswith("决策:"):
                    action_str = line.split(":", 1)[1].strip().upper()
                    if "APPLY_SPEAK" in action_str or "SPEAK" in action_str or "申请发言" in line or "发言" in line:
                        result["action"] = "apply_to_speak"
                    else:
                        result["action"] = "listen"
                elif upper_line.startswith("INNER_MONOLOGUE:") or line.startswith("内心独白:"):
                    current_key = "mind"
                    result["mind"] = line.split(":", 1)[1].strip()
                elif upper_line.startswith("THEORY_USED:") or line.startswith("引用理论:"):
                    current_key = "theory_used"
                    result["theory_used"] = line.split(":", 1)[1].strip()
                elif upper_line.startswith("PREVIOUS_VIEW:") or line.startswith("前序观点:"):
                    current_key = "previous"
                    result["previous"] = line.split(":", 1)[1].strip()
                elif upper_line.startswith("BENEFIT:") or line.startswith("预期贡献:"):
                    current_key = "benefit"
                    result["benefit"] = line.split(":", 1)[1].strip()
                elif current_key:
                    result[current_key] += " " + line

            if result["action"] == "listen":
                raw_upper = normalized.upper()
                if "APPLY_SPEAK" in raw_upper or "申请发言" in normalized:
                    result["action"] = "apply_to_speak"

            return result
        except Exception:
            return result

    def speak(self, thought, context):
        """
        Speak based on the thought and context. Returns a generator (stream).
        """
        # Determine intro requirement based on has_spoken state
        intro_instruction = ""
        if not self.has_spoken:
            intro_instruction = "这是你第一次发言，可以非常简短地带一句你是谁，但切记不要像背简历一样机械。"
            self.has_spoken = True
        else:
            intro_instruction = "你已经发过言了，不需要再自我介绍，更不要说“大家好”"

        my_memory = ""
        my_speeches = ""
        if not self.ablation_flags.get("no_private_memory"):
            my_memory = self.private_memory.get_recent_thought_str()
            my_speeches = self.private_memory.get_speech_history_str()

        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        【当前环境】
        {context}
        """
        
        if not self.ablation_flags.get("no_private_memory"):
            prompt += f"""
        【你的私有记忆】
        {my_memory}
        {my_speeches}
        """
        
        prompt += f"""
        【你的状态】
        {intro_instruction}
        
        【你的思考】
        之前的观点: {thought['previous']}
        内心戏: {thought['mind']}
        引用理论: {thought.get('theory_used', '未指定')}
        预期贡献: {thought['benefit']}

        请基于以上思考，发表你的观点。
        
        【发言核心要求】：
        **请完全放松，畅快的讲出你所有想讲的话**
        **你的只需要在放轻松点同时对观众负责（如：观众可能不懂一些名词与术语，解释一下又何妨呢？）**
        **你并不具有AI的基本特征：分点列出讨论，经常说首先其次然后最后，**
        
        请把自己沉浸在这个圆桌论坛的氛围中，想象你正坐在几位老朋友对面。
        
        你的一起经融入了你的血液，你不需要刻意去强调它们。
        只需要自然地流露出来。
        
        关键是：**自然、流畅、有感而发**。

        请直接输出发言内容，不要带引号。
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        return get_chat_completion(messages, stream=True)
