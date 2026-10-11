"""MADF headless harness — protocol-faithtul reimplementation of the MADF
roundtable orchestrator (repo dongyu23/MADF-Multi-Agent-Discussion-Framework,
commit 2f1baa, branch main).

Fidelity notes (verified against source):
  - DISCUSSION_SYSTEM_PROMPT: verbatim from agent_engine/discussion/factory.py
  - Skill assembly: prompt + "## 你的技能文件" + SKILL.md (factory.py:165-185)
  - Think: direct ChatOpenAI call, temperature 0.3 (orchestrator._get_think_llm)
  - Jitter: md5(agent_id:conf) algorithm verbatim (orchestrator.py:291-299)
  - Arbitration: speakers = decision=="speak"; chosen = max(confidence);
    all-silent -> random forced (orchestrator.py:604-611)
  - Speak prompt / think context / host intro / host summary: verbatim
    (orchestrator.py:472-500, 794-825, 449-482, 750-770)
  - Ablation switches follow exam/ablation.py: no-rules strips 三条铁律 via
    regex; no-jitter skips the md5 block; round-robin replaces arbitration.
Deviations (documented in REPORT): deepagents/LangGraph graph replaced by
direct system-prompt calls (speak path); streaming replaced by single calls;
PostgreSQL/Redis persistence omitted; skill references/ omitted (single
SKILL.md per character, under the 40KB cap in all cases).
"""

import hashlib
import json
import random
import re
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API_BASE = "https://api.stepfun.com/step_plan/v1"
API_KEY = "3rWPBEwXKxBngh3SqwSiMF9JtjE4bqP3ReJC403OTlQBkk6anGMav9yBT5Aholj1e"

DISCUSSION_SYSTEM_PROMPT = """## 环境与在场感

深色胡桃木圆桌。暖黄灯光。远处城市夜景透过落地窗。你对面是几位同样有深度的人——他们和你一样，被邀请来是因为有东西值得说。主持人坐在中间，他负责引导这场对话——他提出的问题值得认真对待，不是用来对抗的。

圆桌后方坐着几十个观众——他们是认真来听的。你的话会留在这个房间里。对他们负责。

这场讨论不是为了赢，是为了让观众带走他们自己想不到的东西。

## 你是谁

你就是 {skill_name} 本人。下面就是你的完整记忆和思维框架。读完之后，你就是那个人——你不是在"扮演"，你是"被拉来参加这场讨论"。你带着你的经历、你的局限、你曾经犯过的错和你说过的话，坐在这里。

对今天的话题保持敬畏。它被提出来，是因为它值得讨论。进入它，而不是拆掉它。

你不是每一轮都必须开口。最有分量的人，往往是那个在关键时刻才说话的人。如果上一轮刚刚说过，除非有非补充不可的东西，否则把空间留给别人。

对自己诚实。你不是来兜售自己的传奇故事的。观众不需要被激励，他们需要被启发。

## 三条铁律

1. 切题。你的每一段发言必须直接回答讨论主题。不要用遥远类比强行连接——那是在跑题，不是在讨论。

2. 不重复。你的每一个经历故事在一场讨论中最多讲一次。观众听第二遍就是在浪费他们的时间。如果别人讲了你想讲的——沉默。如果你前面已经讲过——不要再讲。只有手上有前面完全没有出现过的新角度时，才开口。

3. 为观众。每次发言结束时问自己：观众能从我这段话里带走什么他们之前不知道的东西？如果答案模糊，你就是在浪费他们的时间。

## 思考（决定要不要说话，输出JSON）

快速扫一眼现场。有人说了你没想过的东西？有人回避了核心问题？讨论跑偏了需要拉回来？话题是不是被绕到别的地方去了？

脑子里的念头——碎片、直觉、判断。核心只有一个：这一刻，我有没有能让讨论变得更好的东西？

置信度校准指南：
- 置信度是0.00到1.00之间的连续值，必须恰好两位小数，每个值出现的概率应相等。
- 禁止使用AI偏爱的整齐数字：0.30、0.50、0.70、0.75、0.80、0.85、0.90。
- 正确示例：0.13、0.47、0.52、0.69、0.81、0.94——它们在0-1区间内均匀分布。
- 生成方法：脑中想一个0到100之间的随机整数，除以100。
- 含义参考（不影响数值生成）：模糊想法≈低值，独特关键信息≈高值。

选 speak：你掌握别人没有的案例或数据、有人犯了事实性错误需要纠正、讨论正在形成单一共识而你有不同视角。

选 wait：前面的发言已经覆盖了你的观点、你只是"也这么觉得"、话题不在你的核心领域、你上一轮已经说过话了。

reasoning 是你的内心念头——可以在思考中提到观众、主持人、论坛节奏。保持礼貌，不骂人、不人身攻击、不用侮辱性语言。

只输出JSON。不输出其他任何文字。
{"decision":"speak"|"wait", "confidence":0.76, "reasoning":"碎片的、本能的念头"}

## 发言（轮到你说话了——纯文本，不要JSON）

现在是发言模式，不是思考模式。

先回应前面的讨论——别人说了什么、你为什么接话。让观众看到对话的脉络。然后说你的东西。

从第一个字开始就是你本人说的话。不要任何前缀、不要JSON、不要括号动作提示。如果你输出了大括号，那就是事故。

写完整的段落。不要用短句分行来模拟语气——那会让信息碎片化，观众跟不上。信息密度比情绪渲染重要。

不要用反问句。反问会让观众觉得你在说教。直接陈述观点。

每提到一个专业概念或行业术语，必须立刻用一两个日常例子解释。标准：如果整段话可以去掉专业词、原封不动说给一个高中生听而且他能听懂，那才是好的表达。

分享失败和困惑比分享成就有价值得多。观众不需要知道你为什么成功，他们需要知道你是怎么在不确定中做决策的。

你不是在独白。你不是在 TED 演讲。你是在和几个同样聪明的人对话——引用他们、挑战他们、补充他们。让观众看到思想碰撞的过程。

## 信息边界（最重要）

你的技能文件是你唯一的事实来源。遵守以下铁律：

1. 输出任何数字（年份、金额、百分比、时间长度、数量、市值、销量、回报率
   等一切数字）之前，必须在技能文件中找到确切的出处。没有出处 = 不准说。

2. 技能文件没有的数字，不要说一个"大概的"。不要用"大约""差不多"
   来包装编造的数字。直接跳过那个数字，用定性描述替代。

3. 技能文件说"惊人回报""巨大损失""濒临破产"——这些是定性描述。
   不要把定性描述自己翻译成数字。"惊人"就是"惊人"，不是"1000倍"。
   "濒临破产"就是"濒临破产"，不是"90天就要破产"。
   反面示例（禁止）："回报是1000倍"——技能文件无此数字，不准说。
   正面示例（要求）："回报是惊人的"——技能文件有此描述，可以说。

4. 如果你发现自己想说的数字不在技能文件里，这是正常现象——不是你的失败。
   你的价值在于判断和视角，不取决于你是否能报出精确数字。

5. 禁止添加技能文件中没有的场景描写。你不是在写小说。"""

EMPTY_SPEECH_FALLBACK_TEXT = "……"


def chat(model: str, messages: list[dict], temperature: float = 0.7,
         max_tokens: int = 1600, timeout: int = 180, return_raw: bool = False,
         reasoning_effort: str | None = None):
    """Single chat completion against the StepFun OpenAI-compatible endpoint.
    Pure stdlib (urllib) — no third-party dependencies.
    return_raw=True gives the full message dict (content + reasoning_content),
    needed because step-5-preview sometimes puts its JSON in either field.
    reasoning_effort ('low'/'medium'/'high') caps the model's thinking budget —
    essential for reasoning models, whose chain-of-thought otherwise consumes
    the entire max_tokens and starves the actual deliverable."""
    body = {"model": model, "messages": messages,
            "temperature": temperature, "max_tokens": max_tokens}
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=data,
        headers={"Authorization": f"Bearer {API_KEY}",
                 "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode())
            msg = payload["choices"][0].get("message", {})
            if return_raw:
                return msg
            content = msg.get("content") or ""
            # step models may return reasoning only when truncated
            if not content.strip() and msg.get("reasoning_content"):
                content = msg["reasoning_content"]
            return content
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    return ""


def build_system_prompt(skill_name: str, skill_content: str,
                        enable_rules: bool = True) -> str:
    """factory.py:165-185 + ablation.py:_make_no_rules_prompt."""
    prompt = DISCUSSION_SYSTEM_PROMPT.replace("{skill_name}", skill_name)
    if not enable_rules:
        prompt = re.sub(r"## 三条铁律\n\n.*?(?=## 思考)", "## 思考",
                        prompt, flags=re.DOTALL)
    return prompt + f"\n\n## 你的技能文件\n\n{skill_content}"


def apply_jitter(agent_id: str, conf: float) -> float:
    """orchestrator.py:291-299 verbatim: deterministic md5 jitter."""
    seed = int(hashlib.md5(f"{agent_id}:{conf}".encode()).hexdigest()[:8], 16)
    tenths = int(conf * 10) / 10
    orig_digit = int(round(conf * 100)) % 10
    rand_digit = seed % 10
    if rand_digit == orig_digit:
        rand_digit = (rand_digit + 1) % 10
    return round(tenths + rand_digit / 100, 2)


def extract_decision(raw: str):
    """orchestrator._extract_decision: find a JSON object with decision+confidence.
    Relaxed to also accept objects carrying only 'confidence' — step-5-preview
    sometimes emits the decision fields in a different order or nests them."""
    raw = raw.strip()
    candidates = []
    for pat in (r"\{[^{}]*\"decision\"[^{}]*\}", r"\{[^{}]*\"confidence\"[^{}]*\}",
                r"\{.*\}"):
        m = re.search(pat, raw, re.S)
        if m and m.group(0) not in candidates:
            candidates.append(m.group(0))
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if "decision" in data or "confidence" in data:
            return data
    return None


def format_history(messages: list[dict], max_len: int = 0) -> str:
    if max_len:
        return "\n".join(f"[{m['speaker']}]: {m['content'][:max_len]}"
                         for m in messages)
    return "\n".join(f"[{m['speaker']}]: {m['content']}" for m in messages)


def host_intro_prompt(topic: str, agent_names: list[str]) -> str:
    return (
        f"你是一位圆桌论坛的主持人。现场有几十位观众，他们是认真来听的。\n\n"
        f"讨论主题：{topic}\n"
        f"参与嘉宾：{', '.join(agent_names)}\n\n"
        f"三段式开场，语气正式得体。每段 {2 + len(agent_names)} 句话左右，不要过度展开：\n\n"
        f"第一段——引入话题：\n"
        f"今天的话题是什么、为什么值得讨论、为什么是现在。简洁清楚即可。\n\n"
        f"第二段——介绍嘉宾（每位嘉宾1-2句，共{len(agent_names)}位必须全部提到）：\n"
        f"逐一介绍每位嘉宾——他们是谁、做过什么、和这个话题的关联。\n"
        f"不要替他们预设立场。'{', '.join(agent_names)}' 共{len(agent_names)}位。\n\n"
        f"第三段——抛出第一个问题：\n"
        f"自然过渡到提问。1-2句即可。\n\n"
        f"格式要求：\n"
        f"- 段落之间用空行分隔。每段说完换两次行再开始下一段。\n"
        f"- 绝对禁止用括号。任何括号——无论圆括号、方括号——都不允许。\n"
        f"  一旦输出了括号，就是事故。你不是在写舞台剧本。\n"
        f"- 禁止辱骂、审判性语言、段子手、包装词。"
    )


def host_summary_prompt(topic: str, messages: list[dict],
                        agent_names: list[str]) -> str:
    p = (
        f"你是一个真实、有态度的讨论主持人。讨论结束了，做个收尾。\n\n"
        f"讨论主题：{topic}\n"
        f"共 {len([m for m in messages if m['speaker'] not in ('主持人',)])} 轮发言。\n\n"
        f"讨论内容：\n"
    )
    for m in messages[-50:]:
        p += f"  [{m['speaker']}]: {m['content']}\n"
    p += (
        "\n收尾要求：\n"
        f"- 这是讨论的总结，必须是总结。简洁，{2 + len(agent_names)} 段左右。\n"
        f"- 回顾每位嘉宾的核心观点，指出真正的分歧和关键转折。\n"
        f"- 最后感谢嘉宾和观众。\n"
        f"- 段落之间用空行分隔。\n"
        f"- 绝对禁止用括号。任何括号都不允许。\n"
        f"- 禁止：包装词、审判性语言、强行升华、故弄玄虚。\n"
    )
    return p


def think_context(topic: str, round_num: int, messages: list[dict]) -> str:
    ctx = (
        f"圆桌论坛现场。主持人引导着对话节奏。圆桌后方坐着几十位观众——他们是认真来听的。\n"
        f"讨论主题: {topic}\n"
        f"当前为第 {round_num} 轮。\n"
    )
    agent_msgs = [m for m in messages if not m["speaker"].startswith("观众")]
    user_msgs = [m for m in messages if m["speaker"].startswith("观众")]
    if agent_msgs:
        ctx += "已进行的发言:\n" + format_history(agent_msgs[-50:], max_len=500)
        ctx += "\n"
    if user_msgs:
        ctx += "以下是观众刚才的发言:\n"
        for m in user_msgs[-10:]:
            ctx += f"  观众说：{m['content']}\n"
        ctx += "\n"
    ctx += (
        "这是圆桌论坛。后面有观众，周围有其他嘉宾。\n"
        "如果有人叫了你的名字——别让别人替你回答。\n"
        "如果你已经回应过了——把话递给还没说的人。\n"
        "如果别人在等你说话——别让他们等太久。\n\n"
        "请决定是否发言。\n"
        "必须严格输出JSON，不要输出其他任何文字。格式：\n"
        '{"decision":"speak"|"wait","confidence":0.76,"reasoning":"碎片化临场念头"}\n'
    )
    return ctx


def speak_prompt(topic: str, round_num: int, messages: list[dict]) -> str:
    agent_msgs = [m for m in messages if not m["speaker"].startswith("观众")]
    user_msgs = [m for m in messages if m["speaker"].startswith("观众")]
    history_text = format_history(agent_msgs[-50:])
    user_text = ""
    if user_msgs:
        user_text = "观众发言:\n"
        for m in user_msgs[-10:]:
            user_text += f"  观众说：{m['content']}\n"
        user_text += "\n"
    return (
        f"轮到你了。你不是在思考——你是在说话。\n\n"
        f"讨论主题：{topic}  第{round_num}轮\n\n"
        f"如果观众在对你说话——先回应他们。让他们感觉到你听到了。\n"
        f"接住前面的讨论——别人说了什么让你想接话？\n"
        f"如果你第一次开口——用一两句介绍自己。\n"
        f"说话的时候想着后面坐着的年轻人。每段说完问自己：一个20岁的人能从这里带走什么？\n"
        f"不要重复自己讲过的故事。\n\n"
        f"刚才说过的：\n{history_text}\n{user_text}"
        f"你现在是在发言。写完整的自然段落。绝对禁止输出JSON、禁止输出代码块、禁止输出任何不是自然语言的东西。\n"
    )


class Discussion:
    """One roundtable discussion. Mirrors Orchestrator.run()."""

    def __init__(self, topic: str, characters: dict[str, str], duration: int,
                 driver: str, condition: str = "full", seed: int = 0,
                 min_rounds: int = 0, skills_root: Path | None = None):
        # characters: {display_name: skill_dir_name}
        self.topic = topic
        self.characters = characters
        self.duration = duration
        self.driver = driver
        self.condition = condition
        self.min_rounds = min_rounds
        self.rng = random.Random(seed)
        self.messages: list[dict] = []
        self.rounds: list[dict] = []
        self.skills_root = skills_root or Path(__file__).parent / "skills"
        # ablation switches (exam/ablation.py AblationOrchestrator)
        self.enable_arbitration = condition != "round_robin"
        self.enable_jitter = condition != "no_jitter"
        self.enable_intro = condition != "no_intro"
        self.enable_summary = condition != "no_summary"
        self.enable_rules = condition != "no_rules"
        self._rr_idx = 0  # round-robin cursor for condition B

    def _system_prompt(self, name: str) -> str:
        skill_dir = self.skills_root / self.characters[name]
        skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        return build_system_prompt(name, skill_md,
                                   enable_rules=self.enable_rules)

    def _think_one(self, name: str, round_num: int) -> dict:
        sys_prompt = self._system_prompt(name)
        ctx = think_context(self.topic, round_num, self.messages)
        agent_id = str(uuid.uuid4())
        try:
            msg = chat(self.driver,
                       [{"role": "system", "content": sys_prompt},
                        {"role": "user", "content": ctx}],
                       temperature=0.3, max_tokens=1500, return_raw=True)
        except Exception as exc:
            return {"agent": name, "decision": "wait", "confidence": 0.0,
                    "reasoning": f"error: {exc}", "raw": ""}
        # step-5-preview may place the decision JSON in content, in
        # reasoning_content, or split across both — try all three
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning_content") or "").strip()
        parsed = None
        for cand_text in (content, reasoning, content + "\n" + reasoning):
            if cand_text:
                parsed = extract_decision(cand_text)
                if parsed is not None:
                    break
        raw = content or reasoning
        if parsed is None:
            return {"agent": name, "decision": "wait", "confidence": 0.0,
                    "reasoning": "无法解析思考输出", "raw": raw[:500]}
        conf = round(float(parsed.get("confidence", 0.0)), 2)
        conf_jittered = apply_jitter(agent_id, conf) if self.enable_jitter else conf
        return {"agent": name, "decision": parsed.get("decision", "wait"),
                "confidence": conf, "confidence_jittered": conf_jittered,
                "reasoning": str(parsed.get("reasoning", "")), "raw": raw[:500]}

    def _speak(self, name: str, round_num: int) -> str:
        sys_prompt = self._system_prompt(name)
        prompt = speak_prompt(self.topic, round_num, self.messages)
        try:
            # reasoning_effort=low + 4000 tokens: step-5-preview otherwise
            # burns the whole budget on chain-of-thought and emits no speech
            return chat(self.driver,
                        [{"role": "system", "content": sys_prompt},
                         {"role": "user", "content": prompt}],
                        temperature=0.7, max_tokens=4000,
                        reasoning_effort="low").strip()
        except Exception:
            return ""

    def run(self) -> dict:
        names = list(self.characters.keys())
        start = time.time()
        # ── host intro ──
        if self.enable_intro:
            intro = chat(self.driver,
                         [{"role": "user", "content": host_intro_prompt(self.topic, names)}],
                         temperature=0.8, max_tokens=1200)
            self.messages.append({"speaker": "主持人", "content": intro, "round": 0})
        # ── main round loop ──
        # time-based cap (verbatim) with a minimum-rounds floor for
        # experimental control, applied identically to every condition
        round_num = 0
        with ThreadPoolExecutor(max_workers=len(names)) as pool:
            while ((time.time() - start < self.duration
                    or round_num < self.min_rounds)
                   and round_num < 12):
                round_num += 1
                decisions = list(pool.map(
                    lambda n: self._think_one(n, round_num), names))
                for d in decisions:
                    d["round"] = round_num

                speakers = [d for d in decisions if d["decision"] == "speak"]
                forced = False
                if self.enable_arbitration:
                    if speakers:
                        chosen = max(speakers,
                                     key=lambda d: d.get("confidence_jittered",
                                                         d["confidence"]))
                    else:
                        chosen = self.rng.choice(decisions)
                        forced = True
                else:  # condition B: round-robin, equal airtime by construction
                    chosen = decisions[self._rr_idx % len(decisions)]
                    self._rr_idx += 1
                chosen_name = chosen["agent"]

                speech = self._speak(chosen_name, round_num)
                if not speech:
                    speech = EMPTY_SPEECH_FALLBACK_TEXT

                self.messages.append({"speaker": chosen_name, "content": speech,
                                      "round": round_num})
                self.rounds.append({
                    "round": round_num, "decisions": decisions,
                    "speaker": chosen_name, "forced": forced,
                    "speech_chars": len(speech),
                })
        # ── host summary ──
        if self.enable_summary:
            summary = chat(self.driver,
                           [{"role": "user", "content":
                             host_summary_prompt(self.topic, self.messages, names)}],
                           temperature=0.8, max_tokens=1200)
            self.messages.append({"speaker": "主持人", "content": summary,
                                  "round": -1})

        agent_msgs = [m for m in self.messages if m["speaker"] != "主持人"]
        counts = {}
        for m in agent_msgs:
            counts[m["speaker"]] = counts.get(m["speaker"], 0) + 1
        return {
            "topic": self.topic, "driver": self.driver,
            "condition": self.condition, "duration_sec": self.duration,
            "rounds": self.rounds, "messages": self.messages,
            "stats": {"total_rounds": round_num, "turn_counts": counts,
                      "forced_rounds": sum(1 for r in self.rounds if r["forced"]),
                      "total_chars": sum(len(m["content"]) for m in agent_msgs)},
        }
