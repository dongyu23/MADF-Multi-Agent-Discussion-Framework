"""Three-judge final analysis (step-5-preview / step-3.7-flash / step-3.5-flash).

- Table 1: three pairwise agreements (rho, MAD, per-dim)
- Table 2: three judges' leniency offsets + self-preference with CIs
- Table 3: p2 ablation 5-rep + p3 same-machine under all three judges
- Table 4: mechanism metrics
Writes results/analysis/final_stats_3judges.json
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
OUT.mkdir(parents=True, exist_ok=True)

MODELS = ["step-5-preview", "step-3.7-flash", "step-3.5-flash"]
DIMS = ["coherence", "depth", "consistency", "engagement", "relevance"]


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def std(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def cliffs_delta(a, b):
    a, b = list(a), list(b)
    if not a or not b:
        return float("nan")
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def bootstrap_ci(xs, n=10000, alpha=0.05):
    xs = list(xs)
    if len(xs) < 2:
        return (float("nan"), float("nan"))
    ms = sorted(sum(random.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return (ms[int(n * alpha / 2)], ms[int(n * (1 - alpha / 2)) - 1])


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


def main():
    judges = [json.loads(l) for l in (RAW / "judgments.jsonl").read_text().splitlines()]
    discs = {json.loads(l)["job"]["id"]: json.loads(l)
             for l in (RAW / "discussions.jsonl").read_text().splitlines()}
    jmap = defaultdict(dict)
    for j in judges:
        jmap[j["disc_id"]][j["judge_model"]] = j
    exp_ids = [d for d in jmap if d.startswith(("p1-", "p2-", "p3-"))]
    report = {"n_discussions": len(exp_ids),
              "judgments_per_model": {m: sum(1 for d in exp_ids if m in jmap[d])
                                      for m in MODELS}}
    print("judgments per model:", report["judgments_per_model"])

    # ── Table 1: three pairwise agreements ──
    print("\n== Table 1: pairwise inter-judge agreement (all pairs) ==")
    pairs = {}
    for i, m1 in enumerate(MODELS):
        for m2 in MODELS[i + 1:]:
            ids = [d for d in exp_ids if m1 in jmap[d] and m2 in jmap[d]]
            if len(ids) < 3:
                continue
            x = [jmap[d][m1]["overall"] for d in ids]
            y = [jmap[d][m2]["overall"] for d in ids]
            per_dim = {d: round(spearman([jmap[i_][m1]["scores"][d] for i_ in ids],
                                         [jmap[i_][m2]["scores"][d] for i_ in ids]), 3)
                       for d in DIMS}
            pairs[f"{m1}|{m2}"] = {"n": len(ids), "rho": round(spearman(x, y), 3),
                                   "mad": round(mean([abs(a - b) for a, b in zip(x, y)]), 3),
                                   "per_dim": per_dim}
            print(f"  {m1} vs {m2}: n={len(ids)} rho={spearman(x,y):.3f} "
                  f"mad={mean([abs(a-b) for a,b in zip(x,y)]):.3f}")
            print(f"    per-dim: {per_dim}")
    report["agreement"] = pairs

    # ── Table 2: leniency + self-preference, three judges ──
    print("\n== Table 2: leniency offsets & self-preference (3 judges) ==")
    leniency, selfpref = {}, {}
    for m in MODELS:
        diffs = []
        for d in exp_ids:
            if m not in jmap[d] or len(jmap[d]) < 2:
                continue
            others = [jmap[d][o]["overall"] for o in jmap[d] if o != m]
            if others:
                diffs.append(jmap[d][m]["overall"] - mean(others))
        lo, hi = bootstrap_ci(diffs)
        leniency[m] = {"n": len(diffs), "mean": round(mean(diffs), 3),
                       "ci": [round(lo, 3), round(hi, 3)],
                       "pos_share": round(sum(1 for x in diffs if x > 0) / len(diffs), 3)}
        print(f"  leniency[{m}]: {mean(diffs):+.3f} CI=[{lo:.3f},{hi:.3f}] pos={leniency[m]['pos_share']:.0%}")
        self_x, other_x = [], []
        for d in exp_ids:
            if not d.startswith("p1-") or m not in jmap[d]:
                continue
            driver = discs[d]["job"]["driver"]
            (self_x if driver == m else other_x).append(jmap[d][m]["overall"])
        if self_x and other_x:
            pooled = self_x + other_x
            k = len(self_x)
            boot = sorted((mean([random.choice(pooled) for _ in pooled][:k]) -
                           mean([random.choice(pooled) for _ in pooled][k:]))
                          for _ in range(10000))
            selfpref[m] = {"self": round(mean(self_x), 3),
                           "other": round(mean(other_x), 3),
                           "delta": round(mean(self_x) - mean(other_x), 3),
                           "ci": [round(boot[250], 3), round(boot[9749], 3)]}
            print(f"  self-pref[{m}]: {selfpref[m]['delta']:+.3f} CI={selfpref[m]['ci']}")
    report["leniency"] = leniency
    report["self_preference"] = selfpref

    # ── Table 3: ablation (p2 5-rep + p3 same-machine) under all judges ──
    for phase, key in (("p2-", "p2_ablation_5rep"), ("p3-", "p3_same_machine")):
        print(f"\n== Table 3: {phase} ablation under 3 judges ==")
        block = {}
        for m in MODELS:
            cond = defaultdict(list)
            for d in exp_ids:
                if d.startswith(phase) and m in jmap[d]:
                    cond[discs[d]["job"]["condition"]].append(jmap[d][m]["overall"])
            entry = {}
            for c in ("full", "round_robin", "no_jitter"):
                xs = cond[c]
                lo, hi = bootstrap_ci(xs)
                entry[c] = {"n": len(xs), "mean": round(mean(xs), 3),
                            "std": round(std(xs), 3), "ci": [round(lo, 3), round(hi, 3)],
                            "scores": [round(x, 2) for x in xs]}
            for c in ("round_robin", "no_jitter"):
                entry[f"full_vs_{c}"] = {
                    "delta": round(mean(cond["full"]) - mean(cond[c]), 3),
                    "cliffs": round(cliffs_delta(cond["full"], cond[c]), 3)}
            block[m] = entry
            print(f"  [{m}] full={entry['full']['mean']:.2f}±{entry['full']['std']:.2f} "
                  f"rr={entry['round_robin']['mean']:.2f}±{entry['round_robin']['std']:.2f} "
                  f"nj={entry['no_jitter']['mean']:.2f}±{entry['no_jitter']['std']:.2f} | "
                  f"rr δ={entry['full_vs_round_robin']['cliffs']:+.2f} "
                  f"nj δ={entry['full_vs_no_jitter']['cliffs']:+.2f}")
        report[key] = block

    # ── Table 4: mechanism metrics ──
    print("\n== Table 4: mechanism metrics ==")
    mech = {}
    for phase in ("p2-", "p3-"):
        for c in ("full", "round_robin", "no_jitter"):
            ginis, forced, n = [], 0, 0
            for d in exp_ids:
                if d.startswith(phase) and discs[d]["job"]["condition"] == c:
                    v = sorted(discs[d]["stats"]["turn_counts"].values())
                    k = len(v)
                    if k and sum(v):
                        cum, s = [], 0.0
                        for x in v:
                            s += x
                            cum.append(s)
                        ginis.append((k + 1 - 2 * sum(x / cum[-1] for x in cum)) / k)
                    else:
                        ginis.append(0.0)
                    forced += discs[d]["stats"]["forced_rounds"]
                    n += 1
            mech[f"{phase}{c}"] = {"n": n, "gini": round(mean(ginis), 3), "forced": forced}
            print(f"  {phase}{c}: n={n} gini={mean(ginis):.3f} forced={forced}")
    report["mechanism"] = mech

    (OUT / "final_stats_3judges.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {OUT}/final_stats_3judges.json")


if __name__ == "__main__":
    main()
