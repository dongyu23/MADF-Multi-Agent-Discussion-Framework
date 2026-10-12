"""Parser-robustness sensitivity analysis.

The judge pipeline falls back to regex extraction when the model's output
is not parseable JSON, and to a 5.0 default when no score is recoverable
(work/judge.py). The main analysis keeps every dimension call. This
script re-computes the headline results on a parser-clean subset:
dimension calls whose reasoning is not a parse error are treated as
observed, parse-fallback calls as missing, and a discussion-judge cell
is kept only if at least three of five dimensions are observed.

Writes results/analysis/parser_sensitivity.json
"""

import json
import math
import random
from collections import defaultdict
from pathlib import Path

random.seed(42)
ROOT = Path(__file__).parent
RAW = ROOT / "results" / "raw"
OUT = ROOT / "results" / "analysis"

MODELS = ["step-5-preview", "step-3.7-flash", "deepseek-v4.1-flash"]
DIMS = ["coherence", "depth", "consistency", "engagement", "relevance"]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def ranks(v):
    order = sorted(range(len(v)), key=lambda k: v[k])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = mean(rx), mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def cliffs_delta(a, b):
    a, b = list(a), list(b)
    if not a or not b:
        return float("nan")
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def boot_ci(vals, n=10000, alpha=0.05):
    vals = list(vals)
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    ms = sorted(sum(random.choice(vals) for _ in vals) / len(vals) for _ in range(n))
    return (ms[int(n * alpha / 2)], ms[int(n * (1 - alpha / 2)) - 1])


def main():
    judges = [json.loads(l) for l in (RAW / "judgments.jsonl").read_text().splitlines()]
    discs = {json.loads(l)["job"]["id"]: json.loads(l)
             for l in (RAW / "discussions.jsonl").read_text().splitlines()}
    # clean overall per (disc, judge)
    clean = {}
    kept_cells = defaultdict(int)
    for x in judges:
        if x["judge_model"] not in MODELS:
            continue
        d = x["disc_id"]
        if not d.startswith(("p1-", "p2-", "p3-")):
            continue
        obs = [x["scores"][dim] for dim in DIMS
               if "parse error" not in str(x["reasonings"].get(dim, ""))]
        kept_cells[x["judge_model"]] += 1 if len(obs) >= 3 else 0
        if len(obs) >= 3:
            clean[(d, x["judge_model"])] = mean(obs)
    report = {"kept_cells_per_judge": dict(kept_cells)}

    print("kept cells:", dict(kept_cells))

    # agreement on clean overalls
    print("\n== agreement (parser-clean) ==")
    pairs = {}
    for i, m1 in enumerate(MODELS):
        for m2 in MODELS[i + 1:]:
            ids = [d for d in discs
                   if d.startswith(("p1-", "p2-", "p3-"))
                   and (d, m1) in clean and (d, m2) in clean]
            x = [clean[(d, m1)] for d in ids]
            y = [clean[(d, m2)] for d in ids]
            pairs[f"{m1}|{m2}"] = {"n": len(ids),
                                   "rho": round(spearman(x, y), 3),
                                   "mad": round(mean([abs(a - b) for a, b in zip(x, y)]), 3)}
            print(f"  {m1} vs {m2}: n={len(ids)} rho={spearman(x,y):+.3f} mad={mean([abs(a-b) for a,b in zip(x,y)]):.3f}")
    report["agreement_clean"] = pairs

    # leniency on clean overalls
    print("\n== leniency (parser-clean) ==")
    leniency = {}
    for m in MODELS:
        diffs = []
        for d in discs:
            if not d.startswith(("p1-", "p2-", "p3-")) or (d, m) not in clean:
                continue
            others = [clean[(d, o)] for o in MODELS if o != m and (d, o) in clean]
            if others:
                diffs.append(clean[(d, m)] - mean(others))
        if len(diffs) >= 3:
            lo, hi = boot_ci(diffs)
            leniency[m] = {"n": len(diffs), "mean": round(mean(diffs), 3),
                           "ci": [round(lo, 3), round(hi, 3)]}
            print(f"  {m:22} {mean(diffs):+.3f} CI=[{lo:+.3f},{hi:+.3f}] n={len(diffs)}")
    report["leniency_clean"] = leniency

    # ablation directions on clean overalls
    print("\n== p2 ablation directions (parser-clean) ==")
    block = {}
    for m in MODELS:
        cond = defaultdict(list)
        for d in discs:
            if d.startswith("p2-") and (d, m) in clean:
                cond[discs[d]["job"]["condition"]].append(clean[(d, m)])
        entry = {}
        for c in ("full", "round_robin", "no_jitter"):
            entry[c] = {"n": len(cond[c]), "mean": round(mean(cond[c]), 3)}
        for c in ("round_robin", "no_jitter"):
            entry[f"full_vs_{c}"] = {
                "delta": round(mean(cond["full"]) - mean(cond[c]), 3),
                "cliffs": round(cliffs_delta(cond["full"], cond[c]), 3),
                "direction": "full_below" if mean(cond["full"]) < mean(cond[c]) else "full_above"}
        block[m] = entry
        print(f"  {m:22} full={entry['full']['mean']:.2f}(n={entry['full']['n']}) "
              f"rr={entry['round_robin']['mean']:.2f}(n={entry['round_robin']['n']}) "
              f"nj={entry['no_jitter']['mean']:.2f}(n={entry['no_jitter']['n']}) | "
              f"rr:{entry['full_vs_round_robin']['direction']} nj:{entry['full_vs_no_jitter']['direction']}")
    report["p2_clean"] = block

    # p3 directions
    print("\n== p3 same-machine directions (parser-clean) ==")
    block3 = {}
    for m in MODELS:
        cond = defaultdict(list)
        for d in discs:
            if d.startswith("p3-") and (d, m) in clean:
                cond[discs[d]["job"]["condition"]].append(clean[(d, m)])
        entry = {}
        for c in ("full", "round_robin", "no_jitter"):
            entry[c] = {"n": len(cond[c]), "mean": round(mean(cond[c]), 3)}
        for c in ("round_robin", "no_jitter"):
            entry[f"full_vs_{c}"] = {
                "cliffs": round(cliffs_delta(cond["full"], cond[c]), 3),
                "direction": "full_below" if mean(cond["full"]) < mean(cond[c]) else "full_above"}
        block3[m] = entry
        print(f"  {m:22} full={entry['full']['mean']:.2f} rr={entry['round_robin']['mean']:.2f} "
              f"nj={entry['no_jitter']['mean']:.2f} | rr:{entry['full_vs_round_robin']['direction']} "
              f"nj:{entry['full_vs_no_jitter']['direction']}")
    report["p3_clean"] = block3

    (OUT / "parser_sensitivity.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {OUT}/parser_sensitivity.json")


if __name__ == "__main__":
    main()
