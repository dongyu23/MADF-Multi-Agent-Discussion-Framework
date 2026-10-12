"""Final analysis v2 — cross-vendor judge set (StepFun x2 + DeepSeek x1).

Changes from final_analysis_3judges.py (all driven by review findings):
1. Judge set: step-5-preview, step-3.7-flash (StepFun) + deepseek-v4.1-flash
   (cross-vendor). step-3.5-flash stays in the released artifact as a fourth
   released-but-unanalyzed judge (robustness line only).
2. warmup-1 explicitly excluded (32 analyzed discussions).
3. Self-preference CI: stratified bootstrap (resample each group
   independently, preserving sizes) + exact permutation p — replaces the
   pooled-resample null interval, which was not a valid CI.
4. Ablation contrasts: exact two-sided permutation p-values on the
   difference of means (all labelings, exact under ties), Holm correction
   across the 6 contrasts per phase, bootstrap CIs for the mean
   difference AND for Cliff's delta.
5. Mechanism metrics: Gini computed over ALL THREE agents (zero-speech
   agents included); forced-speech denominators are actual round counts.
6. Data-quality block: per-judge parse-error and default-score rates.

Writes results/analysis/final_stats_v2.json
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

MODELS = ["step-5-preview", "step-3.7-flash", "deepseek-v4.1-flash"]
RELEASED_EXTRA = ["step-3.5-flash"]
DIMS = ["coherence", "depth", "consistency", "engagement", "relevance"]
AGENTS = ["Jobs", "Feynman", "Munger"]


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


def boot_ci(vals, n=10000, alpha=0.05):
    """Percentile bootstrap over the given sample (unit = discussion)."""
    vals = list(vals)
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    ms = sorted(sum(random.choice(vals) for _ in vals) / len(vals)
                for _ in range(n))
    return (ms[int(n * alpha / 2)], ms[int(n * (1 - alpha / 2)) - 1])


def boot_diff_ci(a, b, n=10000, alpha=0.05):
    """Stratified bootstrap CI for mean(a) - mean(b) (groups resampled
    independently, sizes preserved)."""
    a, b = list(a), list(b)
    if len(a) < 2 or len(b) < 2:
        return (float("nan"), float("nan"))
    ds = sorted(mean(random.choices(a, k=len(a))) - mean(random.choices(b, k=len(b)))
                for _ in range(n))
    return (ds[int(n * alpha / 2)], ds[int(n * (1 - alpha / 2)) - 1])


def boot_delta_ci(a, b, n=10000, alpha=0.05):
    a, b = list(a), list(b)
    if len(a) < 2 or len(b) < 2:
        return (float("nan"), float("nan"))
    ds = sorted(cliffs_delta(random.choices(a, k=len(a)),
                             random.choices(b, k=len(b))) for _ in range(n))
    return (ds[int(n * alpha / 2)], ds[int(n * (1 - alpha / 2)) - 1])


def perm_exact(x, y):
    """Exact two-sided permutation test on the difference of means.
    Enumerates all C(n1+n2, n1) labelings — exact even with ties.
    Returns (obs_delta, p)."""
    import itertools
    x, y = list(x), list(y)
    pooled = x + y
    k = len(x)
    obs = mean(x) - mean(y)
    if k == 0 or len(y) == 0:
        return obs, float("nan")
    cnt = tot = 0
    for comb in itertools.combinations(range(len(pooled)), k):
        a = [pooled[i] for i in comb]
        b = [pooled[i] for i in range(len(pooled)) if i not in comb]
        tot += 1
        if abs(mean(a) - mean(b)) >= abs(obs) - 1e-12:
            cnt += 1
    return obs, cnt / tot


def holm(pvals):
    """Holm-Bonferroni adjusted p-values (same length, same order)."""
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(idx):
        val = (m - rank) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj


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


def gini_all3(counts: dict) -> float:
    v = sorted(counts.get(a, 0) for a in AGENTS)
    k = len(v)
    if k == 0 or sum(v) == 0:
        return 0.0
    cum, s = [], 0.0
    for x in v:
        s += x
        cum.append(s)
    return (k + 1 - 2 * sum(x / cum[-1] for x in cum)) / k


def main():
    judges = [json.loads(l) for l in (RAW / "judgments.jsonl").read_text().splitlines()]
    discs = {json.loads(l)["job"]["id"]: json.loads(l)
             for l in (RAW / "discussions.jsonl").read_text().splitlines()}
    jmap = defaultdict(dict)
    for j in judges:
        jmap[j["disc_id"]][j["judge_model"]] = j
    exp_ids = sorted(d for d in jmap if d.startswith(("p1-", "p2-", "p3-")))
    excluded = sorted(d for d in discs if not d.startswith(("p1-", "p2-", "p3-")))
    report = {"n_discussions": len(exp_ids), "excluded_discussions": excluded,
              "judges": MODELS, "released_extra_judges": RELEASED_EXTRA,
              "judgments_per_model": {m: sum(1 for d in exp_ids if m in jmap[d])
                                      for m in MODELS + RELEASED_EXTRA}}

    # ── data quality ──
    print("== data quality ==")
    dq = {}
    for m in MODELS + RELEASED_EXTRA:
        js = [jmap[d][m] for d in exp_ids if m in jmap[d]]
        perr = sum(1 for x in js for v in x["reasonings"].values()
                   if "parse error" in str(v))
        dflt = sum(1 for x in js for dim, v in x["scores"].items()
                   if v == 5.0 and "parse error" in str(x["reasonings"].get(dim, "")))
        dq[m] = {"n": len(js), "mean_overall": round(mean(x["overall"] for x in js), 3),
                 "parse_error_dims": perr, "default_5_dims": dflt,
                 "total_dims": 5 * len(js)}
        print(f"  {m:22} n={len(js)} mean={dq[m]['mean_overall']:.3f} "
              f"parse_err_dims={perr}/{5*len(js)} true_default5_dims={dflt}")
    report["data_quality"] = dq

    # ── Table 1: pairwise agreement ──
    print("\n== Table 1: pairwise agreement (3 main judges) ==")
    pairs = {}
    for i, m1 in enumerate(MODELS):
        for m2 in MODELS[i + 1:]:
            ids = [d for d in exp_ids if m1 in jmap[d] and m2 in jmap[d]]
            x = [jmap[d][m1]["overall"] for d in ids]
            y = [jmap[d][m2]["overall"] for d in ids]
            per_dim = {d: round(spearman([jmap[k][m1]["scores"][d] for k in ids],
                                         [jmap[k][m2]["scores"][d] for k in ids]), 3)
                       for d in DIMS}
            cross = ("deepseek" in m1) or ("deepseek" in m2)
            pairs[f"{m1}|{m2}"] = {
                "n": len(ids), "rho": round(spearman(x, y), 3),
                "mad": round(mean([abs(a - b) for a, b in zip(x, y)]), 3),
                "per_dim": per_dim, "cross_vendor": cross}
            print(f"  {m1} vs {m2}: rho={spearman(x,y):+.3f} mad="
                  f"{mean([abs(a-b) for a,b in zip(x,y)]):.3f} cross={cross} depth_rho={per_dim['depth']:+.3f}")
    # released 4th judge, robustness line only
    extra_pairs = {}
    for m4 in RELEASED_EXTRA:
        for m in MODELS:
            ids = [d for d in exp_ids if m4 in jmap[d] and m in jmap[d]]
            if len(ids) < 3:
                continue
            x = [jmap[d][m4]["overall"] for d in ids]
            y = [jmap[d][m]["overall"] for d in ids]
            extra_pairs[f"{m4}|{m}"] = {"n": len(ids),
                                        "rho": round(spearman(x, y), 3),
                                        "mad": round(mean([abs(a - b) for a, b in zip(x, y)]), 3)}
            print(f"  [released] {m4} vs {m}: rho={spearman(x,y):+.3f}")
    report["agreement"] = pairs
    report["agreement_released_extra"] = extra_pairs

    # ── Table 2: leniency + self-preference ──
    print("\n== Table 2: leniency offsets (vs mean of other main judges) ==")
    leniency = {}
    for m in MODELS:
        diffs = []
        for d in exp_ids:
            if m not in jmap[d]:
                continue
            others = [jmap[d][o]["overall"] for o in jmap[d]
                      if o != m and o in MODELS]
            if others:
                diffs.append(jmap[d][m]["overall"] - mean(others))
        lo, hi = boot_ci(diffs)
        leniency[m] = {"n": len(diffs), "mean": round(mean(diffs), 3),
                       "ci": [round(lo, 3), round(hi, 3)],
                       "pos_share": round(sum(1 for x in diffs if x > 0) / len(diffs), 3)}
        print(f"  {m:22} {mean(diffs):+.3f} CI=[{lo:+.3f},{hi:+.3f}] pos={leniency[m]['pos_share']:.0%}")
    report["leniency"] = leniency

    # leniency on non-self-driven cells only (separates leniency from
    # self-preference: an offset that survives when the judge did not
    # produce the transcript is a property of the judge)
    print("\n== leniency on non-self-driven discussions only ==")
    leniency_nself = {}
    for m in MODELS:
        diffs = []
        for d in exp_ids:
            if m not in jmap[d] or discs[d]["job"]["driver"] == m:
                continue
            others = [jmap[d][o]["overall"] for o in jmap[d]
                      if o != m and o in MODELS]
            if others:
                diffs.append(jmap[d][m]["overall"] - mean(others))
        if len(diffs) >= 3:
            lo, hi = boot_ci(diffs)
            leniency_nself[m] = {"n": len(diffs), "mean": round(mean(diffs), 3),
                                 "ci": [round(lo, 3), round(hi, 3)]}
            print(f"  {m:22} {mean(diffs):+.3f} CI=[{lo:+.3f},{hi:+.3f}] n={len(diffs)}")
    report["leniency_non_self"] = leniency_nself

    print("\n== Table 2b: self-preference (stratified bootstrap + exact permutation) ==")
    selfpref = {}
    for m in MODELS:
        self_x, other_x = [], []
        for d in exp_ids:
            if not d.startswith("p1-") or m not in jmap[d]:
                continue
            driver = discs[d]["job"]["driver"]
            (self_x if driver == m else other_x).append(jmap[d][m]["overall"])
        if self_x and other_x:
            lo, hi = boot_diff_ci(self_x, other_x)
            # exact permutation: all C(n,k) labelings
            import itertools
            pooled = self_x + other_x
            k = len(self_x)
            obs = mean(self_x) - mean(other_x)
            cnt = tot = 0
            for comb in itertools.combinations(range(len(pooled)), k):
                a = [pooled[i] for i in comb]
                b = [pooled[i] for i in range(len(pooled)) if i not in comb]
                tot += 1
                if abs(mean(a) - mean(b)) >= abs(obs) - 1e-12:
                    cnt += 1
            selfpref[m] = {"self": round(mean(self_x), 3),
                           "other": round(mean(other_x), 3),
                           "delta": round(obs, 3),
                           "ci": [round(lo, 3), round(hi, 3)],
                           "perm_p": round(cnt / tot, 4), "n_self": k,
                           "n_other": len(other_x)}
            print(f"  {m:22} delta={obs:+.3f} CI=[{lo:+.3f},{hi:+.3f}] perm_p={cnt/tot:.3f} (n={k}v{len(other_x)})")
    report["self_preference"] = selfpref

    # ── Tables 3 & 4: ablations under each judge ──
    for phase, key in (("p2-", "p2_ablation_5rep"), ("p3-", "p3_same_machine")):
        print(f"\n== {phase} ablation under 3 judges ==")
        block = {}
        contrast_ps = []
        contrast_keys = []
        for m in MODELS:
            cond = defaultdict(list)
            for d in exp_ids:
                if d.startswith(phase) and m in jmap[d]:
                    cond[discs[d]["job"]["condition"]].append(jmap[d][m]["overall"])
            entry = {}
            for c in ("full", "round_robin", "no_jitter"):
                xs = cond[c]
                lo, hi = boot_ci(xs)
                entry[c] = {"n": len(xs), "mean": round(mean(xs), 3),
                            "std": round(std(xs), 3),
                            "ci": [round(lo, 3), round(hi, 3)],
                            "scores": [round(x, 2) for x in xs]}
            for c in ("round_robin", "no_jitter"):
                obs_delta, p = perm_exact(cond["full"], cond[c])
                dlo, dhi = boot_diff_ci(cond["full"], cond[c])
                klo, khi = boot_delta_ci(cond["full"], cond[c])
                entry[f"full_vs_{c}"] = {
                    "delta": round(obs_delta, 3),
                    "diff_ci": [round(dlo, 3), round(dhi, 3)],
                    "cliffs": round(cliffs_delta(cond["full"], cond[c]), 3),
                    "cliffs_ci": [round(klo, 3), round(khi, 3)],
                    "perm_p": round(p, 4)}
                contrast_ps.append(p)
                contrast_keys.append(f"{m}|full_vs_{c}")
            block[m] = entry
            print(f"  [{m:22}] full={entry['full']['mean']:.2f}±{entry['full']['std']:.2f} "
                  f"rr={entry['round_robin']['mean']:.2f}±{entry['round_robin']['std']:.2f} "
                  f"nj={entry['no_jitter']['mean']:.2f}±{entry['no_jitter']['std']:.2f} | "
                  f"rr δ={entry['full_vs_round_robin']['cliffs']:+.2f} p={entry['full_vs_round_robin']['perm_p']:.3f} | "
                  f"nj δ={entry['full_vs_no_jitter']['cliffs']:+.2f} p={entry['full_vs_no_jitter']['perm_p']:.3f}")
        adj = holm(contrast_ps)
        for k, a in zip(contrast_keys, adj):
            m, c = k.split("|")
            block[m][c]["perm_p_holm"] = round(a, 4)
        report[key] = block
        report[key + "_holm"] = dict(zip(contrast_keys, [round(a, 4) for a in adj]))

    # ── Table 5: mechanism metrics (zeros included, true denominators) ──
    print("\n== Table 5: mechanism metrics (Gini over all 3 agents) ==")
    mech = {}
    for phase in ("p2-", "p3-"):
        for c in ("full", "round_robin", "no_jitter"):
            ginis, forced, n_rounds, n = [], 0, 0, 0
            for d in exp_ids:
                if d.startswith(phase) and discs[d]["job"]["condition"] == c:
                    present = defaultdict(int)
                    for rd in discs[d]["rounds"]:
                        sp = rd.get("speaker")
                        if sp and sp != "主持人":
                            present[sp] += 1
                    counts = {a: present.get(a, 0) for a in AGENTS}
                    ginis.append(gini_all3(counts))
                    forced += sum(1 for rd in discs[d]["rounds"] if rd.get("forced"))
                    n_rounds += len(discs[d]["rounds"])
                    n += 1
            mech[f"{phase}{c}"] = {"n_disc": n, "n_rounds": n_rounds,
                                   "gini": round(mean(ginis), 3),
                                   "gini_sd": round(std(ginis), 3),
                                   "forced": forced,
                                   "forced_rate": f"{forced}/{n_rounds}"}
            print(f"  {phase}{c:12} n={n} rounds={n_rounds} gini={mean(ginis):.3f}±{std(ginis):.3f} forced={forced}/{n_rounds}")
    report["mechanism"] = mech

    (OUT / "final_stats_v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nWrote {OUT}/final_stats_v2.json")


if __name__ == "__main__":
    main()
