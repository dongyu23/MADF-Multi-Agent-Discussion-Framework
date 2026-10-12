"""Robustness re-judge for the 7 discussions where an agent never spoke.

The audited judge's turn-count statistic counts only agents that appear in
the transcript, so an agent with zero speeches is omitted and max_gap is
underestimated (e.g. counts 2,1,0 reported as gap 1 instead of 2; counts
2,2,0 reported as gap 0 — "mechanical rotation" — instead of 2).

Main analysis keeps the audited (as-released) prompts for fidelity. This
script re-judges ONLY the affected discussions with corrected statistics
(all three agents, zero counts included, true max_gap), so the paper can
report whether any conclusion depends on the miscomputed cap.

Writes results/raw/judgments_robustness.jsonl (never overwrites).
"""

import json
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from judge import SCORING_DIMENSIONS, JUDGE_PROMPTS, parse_judge_response

ROOT = Path(__file__).parent
RAW = ROOT / "results" / "raw"
OUT = RAW / "judgments_robustness.jsonl"

STEPFUN_BASE = "https://api.stepfun.com/step_plan/v1"
STEPFUN_KEY = "3rWPBEwXKxBngh3SqwSiMF9JtjE4bqP3ReJC403OTlQBkk6anGMav9yBT5Aholj1e"
GETOKEN_BASE = "https://api.getoken.tech/v1"
GETOKEN_KEY = "sk-getoken-96f0c9d4d5f4bb578abdf5a015682461"

AGENTS = ["Jobs", "Feynman", "Munger"]
JUDGES = ["step-5-preview", "step-3.7-flash", "deepseek-v4.1-flash"]

AFFECTED = {
    "p1-step-5-preview-t2-r1", "p2-full-r1", "p2-full-r2", "p2-full-r3",
    "p2-no_jitter-r3", "p3-no_jitter-r1", "p3-no_jitter-r3",
}


def chat(model: str, prompt: str, temperature: float = 0.1,
         max_tokens: int = 4000, timeout: int = 180) -> str:
    if model.startswith("deepseek"):
        base, key = GETOKEN_BASE, GETOKEN_KEY
        body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature, "max_tokens": max_tokens}
    else:
        base, key = STEPFUN_BASE, STEPFUN_KEY
        body = {"model": model, "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature, "max_tokens": max_tokens,
                "reasoning_effort": "low"}
    req = urllib.request.Request(
        f"{base}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            msg = data["choices"][0].get("message", {})
            out = (msg.get("content") or "").strip()
            if not out:
                out = (msg.get("reasoning_content") or "").strip()
            if out:
                return out
            last = "empty response"
        except Exception as exc:
            last = repr(exc)
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"chat failed for {model}: {last}")


def build_corrected_text(messages: list[dict]):
    """Same as judge.build_discussion_text but counts ALL agents (zeros)."""
    lines = [f"[{m.get('speaker', 'Unknown')}]: {m.get('content', '')}\n"
             for m in messages]
    agent_msgs = [m for m in messages if m.get("speaker", "") != "主持人"]
    present = Counter(m["speaker"] for m in agent_msgs)
    counts = {a: present.get(a, 0) for a in AGENTS}
    vals = list(counts.values())
    max_gap = max(vals) - min(vals)
    header = "【发言次数统计（预计算，直接使用）】\n"
    for name, cnt in sorted(counts.items(), key=lambda kv: -kv[1]):
        header += f"  {name}: {cnt}次\n"
    header += f"  最大差距 = {max_gap}（{max_gap}≤1→机械调度，{max_gap}≥3→自然讨论）\n\n"
    return header + "\n".join(lines), counts, max_gap


def judge_one(disc_id: str, messages: list, judge_model: str) -> dict:
    transcript, counts, max_gap = build_corrected_text(messages)
    scores, reasonings = {}, {}
    for dim in SCORING_DIMENSIONS:
        prompt = JUDGE_PROMPTS[dim].replace("{discussion}", transcript)
        ok = False
        for attempt in range(4):
            try:
                raw = chat(judge_model, prompt)
                score, reasoning, _, _ = parse_judge_response(raw)
                if reasoning == "parse error" and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                scores[dim], reasonings[dim] = score, reasoning
                ok = True
                break
            except Exception:
                time.sleep(3 * (attempt + 1))
        if not ok:
            raise RuntimeError(f"{disc_id}/{judge_model}/{dim} failed")
    overall = sum(scores[d] * 0.2 for d in SCORING_DIMENSIONS)
    return {"judge_model": judge_model, "scores": scores,
            "reasonings": reasonings, "overall": overall,
            "turn_counts": counts, "max_gap": max_gap,
            "disc_id": disc_id, "corrected_stats": True}


def main():
    discs = {json.loads(l)["job"]["id"]: json.loads(l)
             for l in (RAW / "discussions.jsonl").read_text().splitlines()}
    done = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                r = json.loads(line)
                done.add((r["disc_id"], r["judge_model"]))
            except Exception:
                pass
    jobs = [(d, m) for d in sorted(AFFECTED) for m in JUDGES
            if (d, m) not in done]
    print(f"robustness jobs: {len(jobs)}", flush=True)

    def run(job):
        d, m = job
        try:
            r = judge_one(d, discs[d]["messages"], m)
            with open(OUT, "a") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            return f"OK {d}/{m}: overall={r['overall']:.2f} gap={r['max_gap']}"
        except Exception as exc:
            return f"FAIL {d}/{m}: {exc}"

    with ThreadPoolExecutor(max_workers=6) as pool:
        for line in pool.map(run, jobs):
            print(line, flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
