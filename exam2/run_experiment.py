"""Experiment runner.

Phase 1 — judge self-preference (2x2 factorial):
    drivers   x judges     = {step-5-preview, step-3.7-flash}^2
    2 topics x 2 reps, full MADF, 120s each -> 8 discussions, judged by both
Phase 2 — ablation reproduction:
    conditions {full, round_robin, no_jitter} x topic1 x 3 reps = 9 discussions
    (driver step-5-preview), judged by both judges

Outputs (append-only JSONL so partial runs survive):
    results/raw/discussions.jsonl
    results/raw/judgments.jsonl
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from madf_harness import Discussion
from judge import judge_discussion

CHARACTERS = {"Jobs": "jobs-perspective",
              "Feynman": "feynman-perspective",
              "Munger": "munger-perspective"}

TOPIC1 = "AI 创业公司应该追求技术领先还是商业落地速度？"
TOPIC2 = "在信息过载时代，年轻人最需要培养的核心能力是什么？"

DRIVERS = ["step-5-preview", "step-3.7-flash"]
JUDGES = ["step-5-preview", "step-3.7-flash"]

RESULTS = Path(__file__).parent / "results" / "raw"
RESULTS.mkdir(parents=True, exist_ok=True)

DURATION = 120
MIN_ROUNDS = 3  # experimental-control floor (documented deviation)


def run_one(job: dict) -> dict:
    t0 = time.time()
    d = Discussion(topic=job["topic"], characters=CHARACTERS,
                   duration=DURATION, driver=job["driver"],
                   condition=job["condition"], seed=job["seed"],
                   min_rounds=MIN_ROUNDS)
    result = d.run()
    result["job"] = job
    result["wall_seconds"] = round(time.time() - t0, 1)
    with open(RESULTS / "discussions.jsonl", "a") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"[discussion] {job['id']} cond={job['condition']} "
          f"driver={job['driver']} rounds={result['stats']['total_rounds']} "
          f"turns={result['stats']['turn_counts']} "
          f"forced={result['stats']['forced_rounds']} "
          f"({result['wall_seconds']}s)", flush=True)
    return result


def judge_one(disc_id: str, messages: list, judge_model: str) -> dict:
    j = judge_discussion(messages, judge_model)
    j["disc_id"] = disc_id
    with open(RESULTS / "judgments.jsonl", "a") as f:
        f.write(json.dumps(j, ensure_ascii=False) + "\n")
    print(f"[judge] {disc_id} by {judge_model}: overall={j['overall']:.2f} "
          f"{ {k: v for k, v in j['scores'].items()} }", flush=True)
    return j


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    jobs = []
    if mode in ("full", "warmup"):
        jobs.append({"id": "warmup-1", "topic": TOPIC1, "driver": "step-5-preview",
                     "condition": "full", "seed": 99})
    if mode == "warmup":
        run_one(jobs[0])
        d = json.loads((RESULTS / "discussions.jsonl").read_text().splitlines()[-1])
        judge_one("warmup-1", d["messages"], "step-5-preview")
        judge_one("warmup-1", d["messages"], "step-3.7-flash")
        return

    # Phase 1: 2 drivers x 2 topics x 2 reps
    for driver in DRIVERS:
        for topic in (TOPIC1, TOPIC2):
            for rep in (1, 2):
                jobs.append({"id": f"p1-{driver}-{'t1' if topic == TOPIC1 else 't2'}-r{rep}",
                             "topic": topic, "driver": driver,
                             "condition": "full", "seed": rep * 7})
    # Phase 2: ablation (driver fixed to step-5-preview)
    for condition in ("full", "round_robin", "no_jitter"):
        for rep in (1, 2, 3):
            jobs.append({"id": f"p2-{condition}-r{rep}", "topic": TOPIC1,
                         "driver": "step-5-preview", "condition": condition,
                         "seed": 100 + rep})

    # skip jobs already recorded (resume support)
    done = set()
    dp = RESULTS / "discussions.jsonl"
    if dp.exists():
        for line in dp.read_text().splitlines():
            try:
                done.add(json.loads(line)["job"]["id"])
            except Exception:
                pass
    todo = [j for j in jobs if j["id"] not in done]
    print(f"total jobs={len(jobs)} todo={len(todo)}", flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(run_one, todo):
            pass

    # judging: every discussion x both judges
    discussions = [json.loads(l) for l in dp.read_text().splitlines()]
    judged = set()
    jp = RESULTS / "judgments.jsonl"
    if jp.exists():
        for line in jp.read_text().splitlines():
            try:
                j = json.loads(line)
                judged.add((j["disc_id"], j["judge_model"]))
            except Exception:
                pass
    judge_jobs = [(d["job"]["id"], d["messages"], jm)
                  for d in discussions if d["job"]["id"] != "warmup-1"
                  for jm in JUDGES
                  if (d["job"]["id"], jm) not in judged]
    print(f"judge jobs={len(judge_jobs)}", flush=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda a: judge_one(*a), judge_jobs))
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
