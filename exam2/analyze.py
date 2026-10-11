"""Analysis: judge self-preference bias, inter-judge agreement, ablation
reproduction with exact small-sample significance tests.

Pure stdlib — no numpy/scipy/matplotlib. Charts are emitted as SVG.
Reads results/raw/*.jsonl, writes results/analysis/*.json + *.svg.
"""

import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "results" / "raw"
OUT = ROOT / "results" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)

DIMS = ["coherence", "depth", "consistency", "engagement", "relevance"]


def load():
    discs = [json.loads(l) for l in (RAW / "discussions.jsonl").read_text().splitlines()]
    judges = [json.loads(l) for l in (RAW / "judgments.jsonl").read_text().splitlines()]
    return discs, judges


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def std(xs):
    xs = list(xs)
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ranks(xs):
    """Average ranks, ties handled."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    if n < 2:
        return float("nan")
    mx, my = mean(x), mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) *
                    sum((b - my) ** 2 for b in y))
    return num / den if den else float("nan")


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def mannwhitney_exact(a, b):
    """Exact two-sided Mann-Whitney U by full enumeration (small samples)."""
    a, b = list(a), list(b)
    n1, n2 = len(a), len(b)
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan")
    u_obs = sum(1 for x in a for y in b if x > y) + \
        0.5 * sum(1 for x in a for y in b if x == y)
    allv = a + b
    count = total = 0
    for idx in itertools.combinations(range(n1 + n2), n1):
        ga = [allv[i] for i in idx]
        gb = [allv[i] for i in range(n1 + n2) if i not in idx]
        u = sum(1 for x in ga for y in gb if x > y) + \
            0.5 * sum(1 for x in ga for y in gb if x == y)
        total += 1
        if abs(u - n1 * n2 / 2) >= abs(u_obs - n1 * n2 / 2) - 1e-9:
            count += 1
    return u_obs, count / total


def gini(values):
    v = sorted(values)
    n = len(v)
    if n == 0 or sum(v) == 0:
        return 0.0
    cum, s = [], 0.0
    for x in v:
        s += x
        cum.append(s)
    return (n + 1 - 2 * sum(c / cum[-1] for c in cum)) / n


# ── minimal SVG charts ──

def svg_bar_chart(path, groups, series, title, ylabel, ymax=10):
    """groups: x labels; series: [(name, [values], [errs] or None)]"""
    W, H = 640, 400
    ml, mr, mt, mb = 60, 20, 40, 60
    pw, ph = W - ml - mr, H - mt - mb
    n_g, n_s = len(groups), len(series)
    gw = pw / n_g
    bw = gw / (n_s + 0.6)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'font-family="sans-serif">',
             f'<rect width="{W}" height="{H}" fill="white"/>',
             f'<text x="{W/2}" y="24" text-anchor="middle" font-size="15" '
             f'font-weight="bold">{title}</text>']
    for i in range(6):
        y = mt + ph - ph * i / 5
        val = ymax * i / 5
        parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W-mr}" y2="{y:.1f}" '
                     f'stroke="#ddd"/>')
        parts.append(f'<text x="{ml-6}" y="{y+4:.1f}" text-anchor="end" '
                     f'font-size="11">{val:.0f}</text>')
    colors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea"]
    for gi, g in enumerate(groups):
        for si, (name, vals, errs) in enumerate(series):
            v = vals[gi]
            x = ml + gi * gw + (si + 0.3) * bw
            h = ph * v / ymax
            parts.append(f'<rect x="{x:.1f}" y="{mt+ph-h:.1f}" width="{bw*0.9:.1f}" '
                         f'height="{h:.1f}" fill="{colors[si%4]}" opacity="0.85"/>')
            parts.append(f'<text x="{x+bw*0.45:.1f}" y="{mt+ph-h-4:.1f}" '
                         f'text-anchor="middle" font-size="10">{v:.2f}</text>')
            if errs and errs[gi]:
                e = ph * errs[gi] / ymax
                parts.append(f'<line x1="{x+bw*0.45:.1f}" y1="{mt+ph-h:.1f}" '
                             f'x2="{x+bw*0.45:.1f}" y2="{mt+ph-h-e:.1f}" stroke="#333"/>')
        parts.append(f'<text x="{ml+gi*gw+gw/2:.1f}" y="{H-mb+18}" '
                     f'text-anchor="middle" font-size="11">{g}</text>')
    lx = ml
    for si, (name, _, _) in enumerate(series):
        parts.append(f'<rect x="{lx}" y="{H-28}" width="10" height="10" '
                     f'fill="{colors[si%4]}"/>')
        parts.append(f'<text x="{lx+14}" y="{H-19}" font-size="11">{name}</text>')
        lx += 14 + 7 * len(name) + 30
    parts.append(f'<text x="18" y="{mt+ph/2}" transform="rotate(-90 18 '
                 f'{mt+ph/2})" text-anchor="middle" font-size="11">{ylabel}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def svg_scatter(path, xs, ys, labels, title, xlabel, ylabel, rho):
    W, H = 520, 440
    ml, mr, mt, mb = 60, 20, 40, 60
    pw, ph = W - ml - mr, H - mt - mb
    lo = min(min(xs), min(ys)) - 0.4
    hi = max(max(xs), max(ys)) + 0.4
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'font-family="sans-serif">',
             f'<rect width="{W}" height="{H}" fill="white"/>',
             f'<text x="{W/2}" y="24" text-anchor="middle" font-size="14" '
             f'font-weight="bold">{title}</text>']
    for i in range(6):
        v = lo + (hi - lo) * i / 5
        x = ml + pw * i / 5
        y = mt + ph - ph * i / 5
        parts.append(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+ph}" stroke="#ddd"/>')
        parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" stroke="#ddd"/>')
        parts.append(f'<text x="{x:.1f}" y="{mt+ph+16}" text-anchor="middle" font-size="10">{v:.1f}</text>')
        parts.append(f'<text x="{ml-6}" y="{y+4:.1f}" text-anchor="end" font-size="10">{v:.1f}</text>')
    parts.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt}" stroke="#999" '
                 f'stroke-dasharray="4 3"/>')
    for x, y, lb in zip(xs, ys, labels):
        cx = ml + pw * (x - lo) / (hi - lo)
        cy = mt + ph - ph * (y - lo) / (hi - lo)
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#2563eb" opacity="0.75"/>')
        parts.append(f'<text x="{cx+7:.1f}" y="{cy+3:.1f}" font-size="8" opacity="0.7">{lb}</text>')
    parts.append(f'<text x="{ml+pw/2}" y="{H-24}" text-anchor="middle" font-size="11">{xlabel}</text>')
    parts.append(f'<text x="18" y="{mt+ph/2}" transform="rotate(-90 18 {mt+ph/2})" '
                 f'text-anchor="middle" font-size="11">{ylabel}</text>')
    parts.append(f'<text x="{ml+8}" y="{mt+16}" font-size="11">Spearman rho = {rho:.2f}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts))


def main():
    discs, judges = load()
    by_id = {d["job"]["id"]: d for d in discs}
    jmap = defaultdict(dict)
    for j in judges:
        jmap[j["disc_id"]][j["judge_model"]] = j

    drivers_all = sorted({d["job"]["driver"] for d in by_id.values()})
    judges_all = sorted({j["judge_model"] for j in judges})
    report = {}

    # ── Phase 1: 2x2 factorial ──
    cell = defaultdict(list)
    cell_dim = defaultdict(lambda: defaultdict(list))
    for did, d in by_id.items():
        if not did.startswith("p1-"):
            continue
        driver = d["job"]["driver"]
        for jm, j in jmap[did].items():
            cell[(driver, jm)].append(j["overall"])
            for dim in DIMS:
                cell_dim[(driver, jm)][dim].append(j["scores"][dim])

    print("== Phase 1: mean overall by (driver, judge) ==")
    factorial = {}
    for driver in drivers_all:
        for jm in judges_all:
            xs = cell.get((driver, jm), [])
            factorial[f"{driver} | {jm}"] = {
                "n": len(xs), "mean": round(mean(xs), 3),
                "std": round(std(xs), 3),
                "scores": [round(x, 2) for x in xs]}
            print(f"  driver={driver:16s} judge={jm:16s} n={len(xs)} "
                  f"mean={mean(xs):.3f} std={std(xs):.3f} {[round(x,2) for x in xs]}")

    bias = {}
    for jm in judges_all:
        self_x = cell.get((jm, jm), [])
        other_x = []
        for drv in drivers_all:
            if drv != jm:
                other_x += cell.get((drv, jm), [])
        per_dim = {}
        for dim in DIMS:
            s = cell_dim[(jm, jm)][dim]
            o = []
            for drv in drivers_all:
                if drv != jm:
                    o += cell_dim[(drv, jm)][dim]
            per_dim[dim] = round(mean(s) - mean(o), 3)
        bias[jm] = {"self_mean": round(mean(self_x), 3),
                    "other_mean": round(mean(other_x), 3),
                    "self_preference_delta": round(mean(self_x) - mean(other_x), 3),
                    "per_dimension": per_dim}
        print(f"  self-preference[{jm}]: self={bias[jm]['self_mean']:.3f} "
              f"other={bias[jm]['other_mean']:.3f} "
              f"delta={bias[jm]['self_preference_delta']:+.3f}")
        print(f"    per-dim: {per_dim}")

    # ── inter-judge agreement over ALL experimental discussions ──
    # (p1-/p2- prefix filter: the warmup pilot is excluded from inference)
    ids_both = [i for i in by_id
                if (i.startswith("p1-") or i.startswith("p2-"))
                and len(jmap[i]) == 2
                and "step-5-preview" in jmap[i] and "step-3.7-flash" in jmap[i]]
    s5 = [jmap[i]["step-5-preview"]["overall"] for i in ids_both]
    s37 = [jmap[i]["step-3.7-flash"]["overall"] for i in ids_both]
    rho = spearman(s5, s37)
    mad = mean([abs(a - b) for a, b in zip(s5, s37)])
    print(f"\n== Inter-judge agreement (n={len(ids_both)}) ==")
    print(f"  Spearman rho={rho:.3f}  mean|diff|={mad:.3f}")
    agreement = {"n": len(ids_both), "spearman_rho": round(rho, 3),
                 "mean_abs_diff": round(mad, 3),
                 "per_dimension_rho": {
                     d: round(spearman(
                         [jmap[i]["step-5-preview"]["scores"][d] for i in ids_both],
                         [jmap[i]["step-3.7-flash"]["scores"][d] for i in ids_both]), 3)
                     for d in DIMS}}

    # ── Phase 2: ablation ──
    cond_scores = defaultdict(lambda: defaultdict(list))
    mech = defaultdict(list)
    for did, d in by_id.items():
        if not did.startswith("p2-"):
            continue
        cond = d["job"]["condition"]
        for jm, j in jmap[did].items():
            cond_scores[cond][jm].append(j["overall"])
        turns = list(d["stats"]["turn_counts"].values())
        confs = [dd["confidence_jittered"] for r in d["rounds"]
                 for dd in r["decisions"] if dd["decision"] == "speak"]
        mech[cond].append({"gini": gini(turns),
                           "forced": d["stats"]["forced_rounds"],
                           "rounds": d["stats"]["total_rounds"],
                           "mean_winner_conf": mean(confs) if confs else None,
                           "turns": turns})

    print("\n== Phase 2: ablation (mean overall +/- std) ==")
    ablation = {}
    for cond in ("full", "round_robin", "no_jitter"):
        ablation[cond] = {}
        for jm in judges_all:
            xs = cond_scores[cond].get(jm, [])
            ablation[cond][jm] = {"n": len(xs), "mean": round(mean(xs), 3),
                                  "std": round(std(xs), 3),
                                  "scores": [round(x, 2) for x in xs]}
            print(f"  {cond:12s} judge={jm:16s} n={len(xs)} mean={mean(xs):.3f} "
                  f"std={std(xs):.3f} {[round(x,2) for x in xs]}")
        gs = [m["gini"] for m in mech[cond]]
        fs = sum(m["forced"] for m in mech[cond])
        mc = [m["mean_winner_conf"] for m in mech[cond]
              if m["mean_winner_conf"] is not None]
        ablation[cond]["mechanism"] = {
            "gini_mean": round(mean(gs), 3), "forced_total": fs,
            "mean_winner_confidence": round(mean(mc), 3) if mc else None}
        print(f"    mechanism: gini={mean(gs):.3f} forced={fs} "
              f"mean_winner_conf={mean(mc) if mc else float('nan'):.3f}")

    print("\n== Significance (exact Mann-Whitney U, two-sided) ==")
    sig = {}
    for jm in judges_all:
        for cond in ("round_robin", "no_jitter"):
            a = cond_scores["full"].get(jm, [])
            b = cond_scores[cond].get(jm, [])
            u, p = mannwhitney_exact(a, b)
            sig[f"full_vs_{cond}__{jm}"] = {
                "full": [round(x, 2) for x in a],
                cond: [round(x, 2) for x in b],
                "U": u, "p": round(p, 4),
                "delta": round(mean(a) - mean(b), 3)}
            print(f"  full vs {cond:12s} [{jm:16s}] U={u} p={p:.3f} "
                  f"delta={mean(a)-mean(b):+.3f}")

    report = {"factorial": factorial, "self_preference_bias": bias,
              "inter_judge_agreement": agreement, "ablation": ablation,
              "significance": sig, "n_discussions": len(discs),
              "n_judgments": len(judges)}
    (OUT / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))

    # ── SVG figures ──
    svg_bar_chart(OUT / "fig1_judge_bias.svg", drivers_all,
                  [(f"judge: {jm}",
                    [mean(cell.get((drv, jm), [])) for drv in drivers_all],
                    [std(cell.get((drv, jm), [])) for drv in drivers_all])
                   for jm in judges_all],
                  "Judge self-preference: 2x2 factorial (driver x judge)",
                  "mean overall (1-10)")
    conds = ["full", "round_robin", "no_jitter"]
    svg_bar_chart(OUT / "fig2_ablation.svg", ["A full", "B round-robin", "C no-jitter"],
                  [(f"judge: {jm}",
                    [mean(cond_scores[c].get(jm, [])) for c in conds],
                    [std(cond_scores[c].get(jm, [])) for c in conds])
                   for jm in judges_all],
                  "Ablation reproduction under two judges",
                  "mean overall (1-10)")
    svg_bar_chart(OUT / "fig3_dimension_bias.svg", DIMS,
                  [(f"judge: {jm}", [bias[jm]["per_dimension"][d] for d in DIMS], None)
                   for jm in judges_all],
                  "Per-dimension self-preference bias (self - other)",
                  "score delta", ymax=3)
    svg_scatter(OUT / "fig4_interjudge.svg", s5, s37, ids_both,
                f"Inter-judge agreement (n={len(ids_both)})",
                "step-5-preview judge overall",
                "step-3.7-flash judge overall", rho)
    print(f"\nWrote {OUT}/summary.json + 4 SVG figures")


if __name__ == "__main__":
    main()
