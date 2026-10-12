"""Third-judge scoring v3 — third judge is step-3.5-flash (StepFun API,
a third distinct model alongside step-5-preview and step-3.7-flash).

Notes:
- step-3.5-flash is a reasoning model: needs max_tokens=4000 or its
  chain-of-thought consumes the budget and no JSON is emitted (same
  silent-degradation mode documented in the paper).
- Only writes a judgment when all five dimensions parse; failures are
  retried, never defaulted.

Appends to results/raw/judgments.jsonl in the standard format.
"""

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from judge import (SCORING_DIMENSIONS, JUDGE_PROMPTS, build_discussion_text,
                   parse_judge_response)

RAW = Path(__file__).parent / "results" / "raw"
API_BASE = "https://api.stepfun.com/step_plan/v1"
API_KEY = "3rWPBEwXKxBngh3SqwSiMF9JtjE4bqP3ReJC403OTlQBkk6anGMav9yBT5Aholj1e"
THIRD_JUDGE = "step-3.5-flash"


def chat(prompt: str, temperature: float = 0.1,
         max_tokens: int = 4000, timeout: int = 180) -> str:
    body = json.dumps({"model": THIRD_JUDGE,
                       "messages": [{"role": "user", "content": prompt}],
                       "temperature": temperature,
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {API_KEY}",
                 "Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            msg = data["choices"][0].get("message", {})
            return (msg.get("content") or "").strip() or \
                (msg.get("reasoning_content") or "").strip()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    return ""


def judge_one(disc_id: str, messages: list):
    transcript, counts, max_gap = build_discussion_text(messages)
    scores, reasonings = {}, {}
    for dim in SCORING_DIMENSIONS:
        prompt = JUDGE_PROMPTS[dim].replace("{discussion}", transcript)
        for attempt in range(3):
            try:
                raw = chat(prompt)
                score, reasoning, _, _ = parse_judge_response(raw)
                scores[dim], reasonings[dim] = score, reasoning
                break
            except Exception:
                if attempt == 2:
                    return None
                time.sleep(3 * (attempt + 1))
    overall = sum(scores[d] * 0.2 for d in SCORING_DIMENSIONS)
    return {"judge_model": THIRD_JUDGE, "scores": scores,
            "reasonings": reasonings, "overall": overall,
            "turn_counts": counts, "max_gap": max_gap, "disc_id": disc_id}


def main():
    discs = [json.loads(l) for l in
             (RAW / "discussions.jsonl").read_text().splitlines()]
    judged = set()
    for line in (RAW / "judgments.jsonl").read_text().splitlines():
        try:
            j = json.loads(line)
            if j["judge_model"] == THIRD_JUDGE:
                judged.add(j["disc_id"])
        except Exception:
            pass
    todo = [d for d in discs
            if d["job"]["id"].startswith(("p1-", "p2-", "p3-"))
            and d["job"]["id"] not in judged]
    print(f"third-judge ({THIRD_JUDGE}) jobs: {len(todo)}", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for j in pool.map(lambda d: judge_one(d["job"]["id"], d["messages"]), todo):
            if j is None:
                print(f"  FAILED (skipped, will retry on next run)", flush=True)
                continue
            with open(RAW / "judgments.jsonl", "a") as f:
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
            print(f"  OK {j['disc_id']}: overall={j['overall']:.2f}", flush=True)
            results.append(j)
    print(f"DONE: {len(results)} new judgments", flush=True)


if __name__ == "__main__":
    main()
