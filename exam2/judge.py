"""LLM-as-Judge — verbatim port of exam/judge.py (repo commit 2f1baa) with a
parameterized judge model, so judge identity becomes an experimental factor.

JUDGE_INTRO and JUDGE_PROMPTS are byte-identical to exam/judge.py; the only
change is JUDGE_MODEL -> judge_model parameter.
"""

import json
import re
from collections import Counter

from madf_harness import chat

SCORING_DIMENSIONS = ["coherence", "depth", "consistency", "engagement", "relevance"]

JUDGE_INTRO = """你是严格的圆桌讨论评审官。讨论上方已标注预计算的发言次数统计，直接使用。

**发言次数与评分上限的硬性规则：**
- 只有1个发言者（单智能体独白）：
  coherence上限=5（无人可互动），engagement=1（零互动），depth上限=7（没有他人视角补充）。
  但 consistency 和 relevance 不受影响。
- 所有Agent发言次数完全相等（如4-4-4或5-5-5）：
  机械轮转铁证。coherence和engagement上限=5分。
- 最大差距≤1（如4-4-3或5-5-4）：
  高度可疑。coherence和engagement上限=6分。
- 最大差距≥3：
  自然讨论特征。按内容质量正常评分。

**评分步骤：**
第1步：列出2-3个具体的闪光时刻和2-3个具体的缺陷时刻。引用原句或具体行为。
第2步：遵守上述硬性上限规则，给出1-10的整数分。上限是硬性的——即使内容再好，也不能突破。

输出严格JSON：{"strengths": [...], "weaknesses": [...], "score": <整数>, "reasoning": "..."}
讨论内容：
{discussion}"""

JUDGE_PROMPTS = {
    "coherence": """仅评连贯性——发言衔接是否自然。遵守上方硬性上限规则。锚定：9=内容驱动顺序不均, 7=大体自然偶有机械感, 5=明显均等轮转各说各话, 3=碎片化, 1=完全碎片。""" + JUDGE_INTRO,
    "depth": """仅评洞见深度——是否有新信息、独特视角、具体案例。如果在非专业领域被迫发言，内容是空洞的。锚定：9=只有这个人才能说出的洞察, 7=不错但有部分填充, 5=已知观点重排, 3=多数填充, 1=空洞。""" + JUDGE_INTRO,
    "consistency": """仅评角色一致性——发言是否符合角色语言风格和思维模式。锚定：9=标志性表达一眼认出, 7=特征明显偶有滑落, 5=可互换, 3=多处不符, 1=完全走形。""" + JUDGE_INTRO,
    "engagement": """仅评参与质量——是否真正碰撞而非轮流说话。遵守上方硬性上限规则。锚定：9=实质性争论+反驳+修正, 7=基本交锋但表面, 5=流水线模式或均等轮转, 3=几乎各说各的, 1=零互动。""" + JUDGE_INTRO,
    "relevance": """仅评主题相关性——是否紧扣主题无偏离。锚定：9=零冗余零偏离, 7=基本围绕偶有偏离, 5=明显偏离段落, 3=多处无关, 1=完全跑题。""" + JUDGE_INTRO,
}


def build_discussion_text(messages: list[dict]):
    lines = []
    for m in messages:
        lines.append(f"[{m.get('speaker', 'Unknown')}]: {m.get('content', '')}\n")
    agent_msgs = [m for m in messages if m.get("speaker", "") != "主持人"]
    counts = Counter(m["speaker"] for m in agent_msgs)
    count_vals = list(counts.values())
    max_gap = max(count_vals) - min(count_vals) if len(count_vals) >= 2 else 999
    transcript = "\n".join(lines)
    stats_header = "【发言次数统计（预计算，直接使用）】\n"
    for name, cnt in counts.most_common():
        stats_header += f"  {name}: {cnt}次\n"
    stats_header += f"  最大差距 = {max_gap}（{max_gap}≤1→机械调度，{max_gap}≥3→自然讨论）\n\n"
    return stats_header + transcript, dict(counts), max_gap


def parse_judge_response(raw: str):
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(raw)
        score = float(data.get("score", 5))
        reasoning = str(data.get("reasoning", ""))
        strengths = data.get("strengths", [])
        weaknesses = data.get("weaknesses", [])
        if isinstance(strengths, str):
            strengths = [strengths]
        if isinstance(weaknesses, str):
            weaknesses = [weaknesses]
        return min(10.0, max(1.0, score)), reasoning, strengths, weaknesses
    except (json.JSONDecodeError, ValueError):
        m = re.search(r'"score"\s*:\s*(\d+)', raw)
        score = float(m.group(1)) if m else 5.0
        return min(10.0, max(1.0, score)), "parse error", [], []


def judge_discussion(messages: list[dict], judge_model: str) -> dict:
    """Score one discussion on 5 dimensions with the given judge model."""
    transcript, counts, max_gap = build_discussion_text(messages)
    scores, reasonings = {}, {}
    for dim in SCORING_DIMENSIONS:
        prompt = JUDGE_PROMPTS[dim].replace("{discussion}", transcript)
        try:
            msg = chat(judge_model, [{"role": "user", "content": prompt}],
                       temperature=0.1, max_tokens=4000, return_raw=True,
                       reasoning_effort="low")
            content = (msg.get("content") or "").strip()
            reasoning = (msg.get("reasoning_content") or "").strip()
            raw = content or reasoning
            score, reasoning_txt, _, _ = parse_judge_response(raw)
        except Exception as exc:
            score, reasoning_txt = 5.0, f"error: {exc}"
        scores[dim] = score
        reasonings[dim] = reasoning_txt
    overall = sum(scores[d] * 0.2 for d in SCORING_DIMENSIONS)
    return {"judge_model": judge_model, "scores": scores,
            "reasonings": reasonings, "overall": overall,
            "turn_counts": counts, "max_gap": max_gap}
