"""Final analysis with complete data:
- p2 ablation at 5 reps (driver step-5-preview) under both judges
- p3 same-machine replication (driver step-3.7-flash, 3 reps):
  same-model judge (original-protocol analog) vs cross-model judge
- pairwise agreement / leniency / self-preference across all p1-p3
Outputs results/analysis/final_stats.json
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
    means = sorted(sum(random.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return (means[int(n * alpha / 2)], means[int(n * (1 - alpha / 2)) - 1])


def ranks(v):
    order = sorted(range(len(v)), key=lambda k: v[k])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
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
    report = {}

    exp_ids = [d for d in jmap if d.startswith(("p1-", "p2-", "p3-"))]
    print(f"experimental discussions: {len(exp_ids)}")

    # ── Table 1: pairwise agreement (all pairs, all experimental discs) ──
    models = ["step-5-preview", "step-3.7-flash"]
    print("\n== Table 1: pairwise inter-judge agreement ==")
    pairs = {}
    for i, m1 in enumerate(models):
        for m2 in models[i + 1:]:
            ids = [d for d in exp_ids if m1 in jmap[d] and m2 in jmap[d]]
            x = [jmap[d][m1]["overall"] for d in ids]
            y = [jmap[d][m2]["overall"] for d in ids]
            rho = spearman(x, y)
            mad = mean([abs(a - b) for a, b in zip(x, y)])
            per_dim = {}
            for dim in ["coherence", "depth", "consistency", "engagement", "relevance"]:
                dx = [jmap[d][m1]["scores"][dim] for d in ids]
                dy = [jmap[d][m2]["scores"][dim] for d in ids]
                per_dim[dim] = round(spearman(dx, dy), 3)
            pairs[f"{m1}|{m2}"] = {"n": len(ids), "rho": round(rho, 3),
                                   "mad": round(mad, 3), "per_dim": per_dim}
            print(f"  {m1} vs {m2}: n={len(ids)} rho={rho:.3f} mad={mad:.3f}")
            print(f"    per-dim: {per_dim}")
    report["agreement"] = pairs

    # ── Table 2: leniency + self-preference with CIs ──
    print("\n== Table 2: leniency offset & self-preference ==")
    leniency, selfpref = {}, {}
    for m in models:
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
            boot = sorted(mean(random.choice(pooled) for _ in pooled) - mean(random.choice(pooled) for _ in pooled) for _ in range(1))  # placeholder
            # proper paired-ish bootstrap on the difference of means
            k = len(self_x)
            boot = []
            for _ in range(10000):
                s = [random.choice(pooled) for _ in pooled]
                boot.append(mean(s[:k]) - mean(s[k:]))
            boot.sort()
            selfpref[m] = {"self": round(mean(self_x), 3), "other": round(mean(other_x), 3),
                           "delta": round(mean(self_x) - mean(other_x), 3),
                           "ci": [round(boot[250], 3), round(boot[9749], 3)]}
            print(f"  self-pref[{m}]: {selfpref[m]['delta']:+.3f} CI={selfpref[m]['ci']} "
                  f"(self={mean(self_x):.2f} other={mean(other_x):.2f})")
    report["leniency"] = leniency
    report["self_preference"] = selfpref

    # ── Table 3a: p2 ablation at 5 reps (driver step-5-preview) ──
    print("\n== Table 3a: p2 ablation (5 reps, driver step-5-preview) ==")
    p2 = {}
    for m in models:
        cond = defaultdict(list)
        for d in exp_ids:
            if d.startswith("p2-") and m in jmap[d]:
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
        p2[m] = entry
        print(f"  [{m}] full={entry['full']['mean']:.2f}±{entry['full']['std']:.2f} "
              f"rr={entry['round_robin']['mean']:.2f}±{entry['round_robin']['std']:.2f} "
              f"nj={entry['no_jitter']['mean']:.2f}±{entry['no_jitter']['std']:.2f} | "
              f"rr_delta={entry['full_vs_round_robin']['delta']:+.2f}(δ={entry['full_vs_round_robin']['cliffs']:+.2f}) "
              f"nj_delta={entry['full_vs_no_jitter']['delta']:+.2f}(δ={entry['full_vs_no_jitter']['cliffs']:+.2f})")
    report["p2_ablation_5rep"] = p2

    # ── Table 3b: p3 same-machine replication (driver step-3.7-flash) ──
    print("\n== Table 3b: p3 same-machine replication (driver step-3.7-flash) ==")
    p3 = {}
    for m in models:
        cond = defaultdict(list)
        for d in exp_ids:
            if d.startswith("p3-") and m in jmap[d]:
                cond[discs[d]["job"]["condition"]].append(jmap[d][m]["overall"])
        entry = {}
        for c in ("full", "round_robin", "no_jitter"):
            xs = cond[c]
            entry[c] = {"n": len(xs), "mean": round(mean(xs), 3),
                        "std": round(std(xs), 3), "scores": [round(x, 2) for x in xs]}
        for c in ("round_robin", "no_jitter"):
            entry[f"full_vs_{c}"] = {
                "delta": round(mean(cond["full"]) - mean(cond[c]), 3),
                "cliffs": round(cliffs_delta(cond["full"], cond[c]), 3)}
        p3[m] = entry
        tag = "SAME-MODEL (original protocol analog)" if m == "step-3.7-flash" else "CROSS-MODEL"
        print(f"  [{m} — {tag}] full={entry['full']['mean']:.2f}±{entry['full']['std']:.2f} "
              f"rr={entry['round_robin']['mean']:.2f}±{entry['round_robin']['std']:.2f} "
              f"nj={entry['no_jitter']['mean']:.2f}±{entry['no_jitter']['std']:.2f} | "
              f"rr_delta={entry['full_vs_round_robin']['delta']:+.2f}(δ={entry['full_vs_round_robin']['cliffs']:+.2f}) "
              f"nj_delta={entry['full_vs_no_jitter']['delta']:+.2f}(δ={entry['full_vs_no_jitter']['cliffs']:+.2f})")
    report["p3_same_machine"] = p3

    # ── Table 4: mechanism metrics ──
    print("\n== Table 4: mechanism metrics ==")
    mech = {}
    for phase, label in (("p2-", "p2 (driver step-5-preview)"), ("p3-", "p3 (driver step-3.7-flash)")):
        for c in ("full", "round_robin", "no_jitter"):
            turns_list, forced, n = [], 0, 0
            for d in exp_ids:
                if d.startswith(phase) and discs[d]["job"]["condition"] == c:
                    turns = list(discs[d]["stats"]["turn_counts"].values())
                    v = sorted(turns)
                    k = len(v)
                    if k and sum(v):
                        cum, s = [], 0.0
                        for x in v:
                            s += x
                            cum.append(s)
                        gini = (k + 1 - 2 * sum(x / cum[-1] for x in cum)) / k
                    else:
                        gini = 0.0
                    turns_list.append(gini)
                    forced += discs[d]["stats"]["forced_rounds"]
                    n += 1
            mech[f"{phase}{c}"] = {"n": n, "gini": round(mean(turns_list), 3),
                                   "forced": forced}
            print(f"  {label} {c}: n={n} gini={mean(turns_list):.3f} forced={forced}")
    report["mechanism"] = mech

    (OUT / "final_stats.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {OUT}/final_stats.json")


if __name__ == "__main__":
    main()
