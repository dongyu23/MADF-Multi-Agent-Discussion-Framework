"""Third-judge scoring (cross-vendor: DeepSeek via getoken relay), v2.

Lessons from v1: the relay rate-limits hard under concurrency (429/503).
v2 is strictly sequential with patient backoff, and NEVER writes a
judgment unless every dimension produced a parseable score — failed
dimensions are retried, and a discussion is skipped (not defaulted) if
it still fails, so no garbage enters the dataset.

Covers all experimental discussions (p1-/p2-/p3- prefixes).
"""

import json
import time
import urllib.request
from pathlib import Path

from judge import (SCORING_DIMENSIONS, JUDGE_PROMPTS, build_discussion_text,
                   parse_judge_response)

RAW = Path(__file__).parent / "results" / "raw"
GETOKEN_BASE = "https://api.getoken.tech/v1"
GETOKEN_KEY = "sk-getoken-96f0c9d4d5f4bb578abdf5a015682461"
THIRD_JUDGE = "deepseek-v4.1-flash"  # different vendor from StepFun
MAX_ROUNDS = 6  # full passes over the todo list before giving up


def chat(messages: list[dict], temperature: float = 0.1,
         max_tokens: int = 4000, timeout: int = 120) -> str:
    body = json.dumps({"model": THIRD_JUDGE, "messages": messages,
                       "temperature": temperature,
                       "max_tokens": max_tokens}).encode()
    req = urllib.request.Request(
        f"{GETOKEN_BASE}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {GETOKEN_KEY}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    msg = data["choices"][0].get("message", {})
    return (msg.get("content") or "").strip() or \
        (msg.get("reasoning_content") or "").strip()


def judge_one_dimension(prompt: str):
    """One dimension with retries; returns (score, reasoning) or None."""
    for attempt in range(4):
        try:
            raw = chat([{"role": "user", "content": prompt}])
            score, reasoning, _, _ = parse_judge_response(raw)
            return score, reasoning
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


def judge_discussion(disc_id: str, messages: list):
    transcript, counts, max_gap = build_discussion_text(messages)
    scores, reasonings = {}, {}
    for dim in SCORING_DIMENSIONS:
        prompt = JUDGE_PROMPTS[dim].replace("{discussion}", transcript)
        out = judge_one_dimension(prompt)
        if out is None:
            return None  # do not write partial/garbage judgments
        scores[dim], reasonings[dim] = out
    overall = sum(scores[d] * 0.2 for d in SCORING_DIMENSIONS)
    return {"judge_model": THIRD_JUDGE, "scores": scores,
            "reasonings": reasonings, "overall": overall,
            "turn_counts": counts, "max_gap": max_gap, "disc_id": disc_id}


def main():
    for round_no in range(1, MAX_ROUNDS + 1):
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
        print(f"round {round_no}: {len(todo)} discussions to judge", flush=True)
        if not todo:
            print("THIRD JUDGE DONE", flush=True)
            return
        for d in todo:
            j = judge_discussion(d["job"]["id"], d["messages"])
            if j is None:
                print(f"  SKIP {d['job']['id']} (relay failing)", flush=True)
                continue
            with open(RAW / "judgments.jsonl", "a") as f:
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
            print(f"  OK {d['job']['id']}: overall={j['overall']:.2f}",
                  flush=True)
            time.sleep(2)
    print("THIRD JUDGE: gave up after max rounds", flush=True)


if __name__ == "__main__":
    main()
