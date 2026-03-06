import json
import re
import requests
from typing import List, Dict, Any, Generator
from utils import get_chat_completion, parse_json_from_response
from config import SERPAPI_API_KEY

REACT_PROMPT_TEMPLATE = """
你是一个拥有互联网搜索能力的上帝智能体。你的任务是根据用户的描述，生成**一位**极具深度、有血有肉的真实（或基于真实背景的）智能体角色。

【用户描述】：
{question}

【核心目标】：
我们要创造的是真实的人，或者基于真实历史/现实人物背景的角色。每个人物都必须有复杂的背景和深刻的学术积淀。

【可用工具】：
- Search: 一个网页搜索引擎。当你需要查找真实人物、历史事实、时事或专业知识时，必须使用此工具。

【流程】：
1. 分析用户描述，确定需要搜索的关键信息（如特定人物生平、特定领域的专家、历史背景等）。
2. 使用 Search 工具获取信息。**务必针对该角色的生平细节、核心观点、性格特征进行深入搜索**。
3. 根据搜索结果，构思角色详情。
4. 最终生成角色（JSON格式）。

【回复格式要求】：
请严格按照以下格式进行回应（包括思维过程和行动）：

Thought: 你的思考过程，分析当前需要做什么。
Action: Search[搜索关键词]  <-- 如果需要搜索
Observation: [工具返回的结果] <-- 这部分由系统填写
... (重复思考和行动直到收集足够信息) ...
Thought: 我已经收集了足够的信息，现在开始生成角色。
Action: Finish[JSON数据]

【JSON格式特别说明】：
1. JSON字符串值内部如果包含引号，请务必使用单引号（'）代替双引号（"），或者使用转义（\"）。
   - 错误示例：{{"bio": "他被称为"现代物理学之父"..."}}
   - 正确示例：{{"bio": "他被称为'现代物理学之父'..."}}
2. 确保 JSON 格式合法，不要有多余的逗号。

【最终 JSON 数据要求】：
必须是一个列表，仅包含 **1位** 角色。
每个对象包含：
- name: 姓名
- title: 头衔/职业
- bio: **400字以上的深度生平**，基于搜索到的真实背景，包含教育经历、职业转折、重大成就及个人挫折。
- theories: 7个具体理论/概念。
- stance: **400字以上的深度性格与立场描述**，详细阐述其世界观、价值观及对待争议话题的态度。
- system_prompt: 第一人称的指导提示词。

示例 JSON:
[
    {{
        "name": "埃隆·马斯克",
        "title": "科技企业家",
        "bio": "（400字以上）...",
        "theories": ["第一性原理", "火星殖民", ...],
        "stance": "（400字以上）...",
        "system_prompt": "..."
    }}
]

开始！
"""

class RealGodAgent:
    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps
        self.history = []

    def search(self, query: str) -> str:
        """Executes a Google search using SerpAPI."""
        try:
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": SERPAPI_API_KEY,
                "engine": "google",
                "hl": "zh-cn",
                "gl": "cn"
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                results = response.json()
                # Extract organic results
                snippets = []
                if "organic_results" in results:
                    for item in results["organic_results"][:3]: # Top 3 results
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        snippets.append(f"Title: {title}\nSnippet: {snippet}")
                elif "knowledge_graph" in results:
                     k = results["knowledge_graph"]
                     snippets.append(f"Knowledge: {k.get('description', '')}")
                
                return "\n---\n".join(snippets) if snippets else "未找到相关结果。"
            else:
                return f"搜索失败: HTTP {response.status_code}"
        except Exception as e:
            return f"搜索出错: {str(e)}"

    def run(self, prompt: str, n: int = 1, generated_names: List[str] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Runs the ReAct loop and yields events.
        """
        self.history = []
        current_step = 0
        search_count = 0  # Track search calls
        
        # Modified prompt to include context of already generated personas
        context_instruction = ""
        # Fix unhashable type: 'slice' error by ensuring generated_names is a list
        if generated_names is None:
            generated_names = []
            
        if generated_names:
            context_instruction = f"\n【已生成角色（请勿重复）】：{', '.join(generated_names)}"
            
        # Add instruction to explicitly state who to generate next
        # IMPORTANT: Force LLM to plan for only ONE persona, even if n > 1 in theory (we handle loop externally)
        full_prompt = REACT_PROMPT_TEMPLATE.format(question=prompt + context_instruction, n=n)
        
        full_prompt += """

**重要指令 (CRITICAL)**：
1. 本次任务**只生成 1 位**角色。即使你在思考中提到了多个人物，也请一次只处理一个。
2. 在开始搜索或生成之前，请先在 Thought 中明确指出：“本次我计划生成的人物是：[姓名]”。
3. **严禁**在单次任务中搜索多个人物。严禁在搜索完第一个人物后继续搜索第二个人物。
4. 每个角色的搜索次数严格限制为 **最多2次**。
5. 一旦完成当前角色的信息收集，请立即使用 Finish[JSON数据] 结束。
6. 你的 Finish 动作中，JSON 列表只包含 **1个** 对象。
7. 如果搜索结果已经足够生成角色，**禁止**继续搜索，必须立即执行 Finish。
8. 只要你生成了一个人物的JSON数据，就立即结束任务！
"""
        
        messages = [{"role": "user", "content": full_prompt}]

        while current_step < self.max_steps:
            current_step += 1
            
            # Call LLM
            response = get_chat_completion(messages)
            if not response or not response.choices:
                yield {"type": "error", "content": "LLM未响应"}
                return

            response_text = response.choices[0].message.content
            
            # Parse Thought and Action
            thought, action = self._parse_output(response_text)
            
            if thought:
                yield {"type": "thought", "content": thought}
                # Add to history context for next turn
                # Note: We don't append full prompt again, just the conversation flow
                # Actually, for ZhipuAI/OpenAI, we should append the assistant message
                messages.append({"role": "assistant", "content": response_text})
            
            if not action:
                # If no action found but has thought, maybe it's just thinking. 
                # But strict format requires Action. 
                # If it outputted just thought, we might need to prompt it to continue?
                # For now, let's assume it follows format or we break.
                # However, sometimes LLM outputs "Thought: ... \nAction: ..." in one go.
                pass

            if action:
                if action.startswith("Finish"):
                    # Extract content inside Finish[...]
                    # Use a more robust regex that handles multiline content inside brackets
                    # and potential trailing text
                    match = re.search(r"Finish\[(.*)\]", action, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                    else:
                        # Fallback: maybe the whole action content is the JSON
                        json_str = action.replace("Finish", "").strip()
                    
                    # Clean up common LLM artifacts like "JSON数据]" prefix
                    json_str = json_str.replace("JSON数据]", "").strip()
                    if json_str.startswith("[") and json_str.endswith("]"):
                         pass # Looks like valid JSON array
                    
                    # Parse JSON
                    personas = parse_json_from_response(json_str)
                    if personas:
                         # Ensure we only return 1 persona as requested
                         if isinstance(personas, list) and len(personas) > 1:
                             personas = personas[:1]
                         elif isinstance(personas, dict): # Handle case where LLM returns single object instead of list
                             personas = [personas]
                             
                         yield {"type": "result", "content": personas}
                    else:
                         # Try to find JSON array in the thought/action text if parsing failed
                         # Look for the LAST JSON array-like structure
                         # Use finditer to avoid greedy matching issues
                         json_candidates = list(re.finditer(r"\[\s*\{.*?\}\s*\]", response_text, re.DOTALL))
                         
                         if json_candidates:
                             for match in reversed(json_candidates):
                                 candidate = match.group(0)
                                 personas = parse_json_from_response(candidate)
                                 if personas:
                                     # Ensure we only return 1 persona as requested
                                     if isinstance(personas, list) and len(personas) > 1:
                                         personas = personas[:1]
                                     elif isinstance(personas, dict):
                                         personas = [personas]
                                         
                                     yield {"type": "result", "content": personas}
                                     return
                         
                         yield {"type": "error", "content": "生成的JSON格式无效"}
                    return

                # Parse Tool
                tool_name, tool_input = self._parse_action(action)
                if tool_name == "Search":
                    if search_count >= 2:
                        # Skip execution, force LLM to proceed
                        observation = "搜索次数已达上限（2次）。你已拥有足够信息，请立即使用 Finish[JSON数据] 生成角色。不要再进行任何搜索！"
                        yield {"type": "error", "content": "搜索限制触发：强制停止搜索，请立即生成结果"}
                        messages.append({"role": "user", "content": f"Observation: {observation}"})
                    else:
                        search_count += 1
                        yield {"type": "action", "content": f"正在搜索: {tool_input}"}
                        observation = self.search(tool_input)
                        yield {"type": "observation", "content": observation}
                        # Append observation to history
                        messages.append({"role": "user", "content": f"Observation: {observation}"})
                else:
                    yield {"type": "error", "content": f"未知工具: {tool_name}"}
                    return
            else:
                 # No action found, maybe finished or error?
                 if "JSON" in response_text or "[" in response_text:
                     # Try to parse JSON directly if it forgot "Finish"
                     personas = parse_json_from_response(response_text)
                     if personas and isinstance(personas, list):
                         yield {"type": "result", "content": personas}
                         return
                 
                 yield {"type": "error", "content": "LLM未返回有效指令"}
                 return

    def _parse_output(self, text: str):
        # Flexible parsing
        thought = None
        action = None
        
        # 1. 优先尝试标准的 Thought: ... Action: ... 结构
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        if thought_match:
            thought = thought_match.group(1).strip()
            
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        if action_match:
            action = action_match.group(1).strip()
            # Clean up action (remove trailing text if any)
            # Finish[...] can be multiline, so be careful not to split it
            if "Finish" not in action:
                action = action.split("\n")[0]
        
        # 2. 如果没有 Action，尝试从文本末尾找 Finish
        if not action:
            if "Finish[" in text:
                 match = re.search(r"(Finish\[.*?\])", text, re.DOTALL)
                 if match:
                     action = match.group(1)
            elif "Finish" in text: # Sometimes LLM forgets brackets or format
                 # Try to find JSON block near Finish
                 match = re.search(r"Finish.*?(\[.*\])", text, re.DOTALL)
                 if match:
                     action = f"Finish[{match.group(1)}]"
        
        return thought, action

    def _parse_action(self, action_text: str):
        # Match Tool[Input]
        # Allow multiline input for Search sometimes? No, search is usually one line.
        # But allow loose matching
        match = re.search(r"(\w+)\[(.*?)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

    def _parse_action_input(self, action_text: str):
        # Match Finish[Input]
        # Use DOTALL to capture newlines in JSON
        match = re.search(r"Finish\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1)
        return ""
