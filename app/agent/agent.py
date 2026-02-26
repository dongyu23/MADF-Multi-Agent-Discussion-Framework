import json
from utils import get_chat_completion, parse_json_from_response
from app.agent.memory import PrivateMemory

class BaseAgent:
    def __init__(self, name, system_prompt):
        self.name = name
        self.system_prompt = system_prompt


class ModeratorAgent(BaseAgent):
    def __init__(self, theme):
        self.theme = theme
        super().__init__("主持人", "你是一场圆桌论坛的专业主持人。你的职责是引导话题、总结发言、并控制流程。")

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

        请对整场论坛进行最终总结，梳理主要冲突点和共识，并宣布论坛结束。
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        return get_chat_completion(messages, stream=True)

class ParticipantAgent(BaseAgent):
    def __init__(self, name, persona, n_participants, theme):
        super().__init__(name, persona['system_prompt'])
        self.title = persona['title']
        self.bio = persona['bio']
        self.theories = persona['theories']
        self.priority = 100
        self.private_memory = PrivateMemory(n_participants)
        self.has_spoken = False
        self.theme = theme

    def think(self, context):
        """
        Fast Thinking: Analyze context using Bio and Theories.
        """
        my_memory = self.private_memory.get_recent_thought_str()
        
        prompt = f"""
        无需提及但要记住主题：
        {self.theme}
        【当前环境】
        {context}

        【你的私有记忆】
        {my_memory}

        【你的生平与理论】
        生平: {self.bio}
        理论武库: {', '.join(self.theories)}

        请进行“快思考”，你的任务是通过主观思考判断自己是否需要申请讲话。
        **不要使用通用的官方的逻辑（如利弊分析），不要和稀泥，不要攻击他人。**
        **请从你的理论武库中挑选1-2个理论作为切入点。**

        要求输出 JSON 格式，包含：
        - "previous": "你之前的人是什么观点？20字左右"
        - "mind": "你的内心戏是什么？结合你的生平和理论，以“我”为主语，50字左右"
        - "theory_used": "你打算引用的理论"
        - "benefit": "你的发言能给听众带来什么收获？10字左右"
        - "action": 若你想发言，填 "apply_to_speak"；否则填 "listen"。

        注意：你不是在表达观点，你是在**成为一个真实的有血有肉的自己**。
        """
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = get_chat_completion(messages, json_mode=True)
        if response:
            return parse_json_from_response(response.choices[0].message.content)
        return None

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

        my_memory = self.private_memory.get_recent_thought_str()
        my_speeches = self.private_memory.get_speech_history_str()

        prompt = f"""
        无需专门提及但要记住主题：
        {self.theme}
        【当前环境】
        {context}
        【你的私有记忆】
        {my_memory}
        {my_speeches}
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
