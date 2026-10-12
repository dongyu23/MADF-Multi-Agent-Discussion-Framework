"""Generate the paper's four figures as SVG from final_stats.json + raw data."""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "results" / "analysis"
FIG = ROOT.parent / "paper" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

stats = json.loads((OUT / "final_stats.json").read_text())
judges = [json.loads(l) for l in (ROOT / "results/raw/judgments.jsonl").read_text().splitlines()]
discs = {json.loads(l)["job"]["id"]: json.loads(l)
         for l in (ROOT / "results/raw/discussions.jsonl").read_text().splitlines()}
jmap = defaultdict(dict)
for j in judges:
    jmap[j["disc_id"]][j["judge_model"]] = j


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def bar_chart(path, groups, series, title, ylabel, ymin=0, ymax=10):
    """series: [(name, values, errs, color)]"""
    W, H = 640, 400
    ml, mr, mt, mb = 70, 20, 50, 70
    pw, ph = W - ml - mr, H - mt - mb
    n_g, n_s = len(groups), len(series)
    gw = pw / n_g
    bw = gw / (n_s + 0.6)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{W/2}" y="26" text-anchor="middle" font-size="15" font-weight="bold">{esc(title)}</text>']
    for i in range(6):
        v = ymin + (ymax - ymin) * i / 5
        y = mt + ph - ph * i / 5
        p.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W-mr}" y2="{y:.1f}" stroke="#ddd"/>')
        p.append(f'<text x="{ml-8}" y="{y+4:.1f}" text-anchor="end" font-size="11">{v:.1f}</text>')
    for gi, g in enumerate(groups):
        for si, (name, vals, errs, color) in enumerate(series):
            v = vals[gi]
            x = ml + gi * gw + (si + 0.3) * bw
            h = ph * (v - ymin) / (ymax - ymin)
            p.append(f'<rect x="{x:.1f}" y="{mt+ph-h:.1f}" width="{bw*0.9:.1f}" height="{h:.1f}" fill="{color}" opacity="0.85"/>')
            p.append(f'<text x="{x+bw*0.45:.1f}" y="{mt+ph-h-5:.1f}" text-anchor="middle" font-size="10">{v:.2f}</text>')
            if errs and errs[gi]:
                e = ph * errs[gi] / (ymax - ymin)
                p.append(f'<line x1="{x+bw*0.45:.1f}" y1="{mt+ph-h:.1f}" x2="{x+bw*0.45:.1f}" y2="{mt+ph-h-e:.1f}" stroke="#333" stroke-width="1.5"/>')
                p.append(f'<line x1="{x+bw*0.45-4:.1f}" y1="{mt+ph-h-e:.1f}" x2="{x+bw*0.45+4:.1f}" y2="{mt+ph-h-e:.1f}" stroke="#333" stroke-width="1.5"/>')
        p.append(f'<text x="{ml+gi*gw+gw/2:.1f}" y="{H-mb+20}" text-anchor="middle" font-size="11">{esc(g)}</text>')
    lx = ml
    for name, _, _, color in series:
        p.append(f'<rect x="{lx}" y="{H-30}" width="10" height="10" fill="{color}"/>')
        p.append(f'<text x="{lx+14}" y="{H-21}" font-size="11">{esc(name)}</text>')
        lx += 14 + 7 * len(name) + 30
    p.append(f'<text x="20" y="{mt+ph/2}" transform="rotate(-90 20 {mt+ph/2})" text-anchor="middle" font-size="11">{esc(ylabel)}</text>')
    p.append("</svg>")
    path.write_text("\n".join(p))


def scatter(path, xs, ys, labels, title, xlabel, ylabel):
    W, H = 560, 460
    ml, mr, mt, mb = 70, 20, 50, 70
    pw, ph = W - ml - mr, H - mt - mb
    lo, hi = 4.5, 8.5
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<text x="{W/2}" y="26" text-anchor="middle" font-size="15" font-weight="bold">{esc(title)}</text>']
    for i in range(5):
        v = lo + (hi - lo) * i / 4
        x = ml + pw * i / 4
        y = mt + ph - ph * i / 4
        p.append(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+ph}" stroke="#ddd"/>')
        p.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" stroke="#ddd"/>')
        p.append(f'<text x="{x:.1f}" y="{mt+ph+16}" text-anchor="middle" font-size="10">{v:.1f}</text>')
        p.append(f'<text x="{ml-8}" y="{y+4:.1f}" text-anchor="end" font-size="10">{v:.1f}</text>')
    p.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt}" stroke="#999" stroke-dasharray="5 4"/>')
    p.append(f'<text x="{ml+pw-90}" y="{mt+18}" font-size="10" fill="#666">agreement line</text>')
    for x, y, lb in zip(xs, ys, labels):
        cx = ml + pw * (x - lo) / (hi - lo)
        cy = mt + ph - ph * (y - lo) / (hi - lo)
        p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#2563eb" opacity="0.7"/>')
    p.append(f'<text x="{ml+pw/2}" y="{H-26}" text-anchor="middle" font-size="11">{esc(xlabel)}</text>')
    p.append(f'<text x="22" y="{mt+ph/2}" transform="rotate(-90 22 {mt+ph/2})" text-anchor="middle" font-size="11">{esc(ylabel)}</text>')
    p.append("</svg>")
    path.write_text("\n".join(p))


BLUE, RED = "#2563eb", "#dc2626"

# ── fig1: p2 ablation, 5 reps, both judges ──
p2 = stats["p2_ablation_5rep"]
groups = ["Full system", "No arbitration\n(round-robin)", "No jitter"]
cond_keys = ["full", "round_robin", "no_jitter"]
bar_chart(FIG / "fig1_condition_scores.svg", groups,
          [("Judge A (step-5-preview)",
            [p2["step-5-preview"][c]["mean"] for c in cond_keys],
            [(p2["step-5-preview"][c]["ci"][1] - p2["step-5-preview"][c]["ci"][0]) / 2 for c in cond_keys], BLUE),
           ("Judge B (step-3.7-flash)",
            [p2["step-3.7-flash"][c]["mean"] for c in cond_keys],
            [(p2["step-3.7-flash"][c]["ci"][1] - p2["step-3.7-flash"][c]["ci"][0]) / 2 for c in cond_keys], RED)],
          "Ablation under two judges (primary driver, 5 reps)",
          "mean overall score (1-10)")

# ── fig2: per-discussion scatter ──
ids = sorted(d for d in jmap if d.startswith(("p1-", "p2-", "p3-"))
             and len(jmap[d]) == 2)
xs = [jmap[d]["step-5-preview"]["overall"] for d in ids]
ys = [jmap[d]["step-3.7-flash"]["overall"] for d in ids]
scatter(FIG / "fig2_trajectories.svg", xs, ys, ids,
        f"Per-discussion scores, both judges (n={len(ids)})",
        "Judge A (step-5-preview) overall", "Judge B (step-3.7-flash) overall")

# ── fig3: same-machine replication ──
p3 = stats["p3_same_machine"]
bar_chart(FIG / "fig3_same_machine.svg", groups,
          [("Same-model judge",
            [p3["step-3.7-flash"][c]["mean"] for c in cond_keys],
            [p3["step-3.7-flash"][c]["std"] for c in cond_keys], BLUE),
           ("Cross-model judge",
            [p3["step-5-preview"][c]["mean"] for c in cond_keys],
            [p3["step-5-preview"][c]["std"] for c in cond_keys], RED)],
          "Same-machine replication (secondary driver, 3 reps)",
          "mean overall score (1-10)")

# ── fig4: mechanism metrics ──
mech = stats["mechanism"]
bar_chart(FIG / "fig4_mechanism.svg", groups,
          [("Primary driver Gini",
            [mech[f"p2-{c}"]["gini"] for c in cond_keys], None, BLUE),
           ("Secondary driver Gini",
            [mech[f"p3-{c}"]["gini"] for c in cond_keys], None, RED)],
          "Speaking-count inequality (Gini) per condition",
          "Gini coefficient", ymin=0, ymax=0.5)

print("figures written:", sorted(p.name for p in FIG.glob("*.svg")))
