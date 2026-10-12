"""Generate TikZ figures (figures_all.tex) from final_stats_v2.json.

Four figures, all values read from the analysis JSON + raw judgments:
  fig:flip         p2 ablation bars per judge, bootstrap 95% CI error bars
  fig:trajectories per-discussion pairwise scatter, 32 points per pair
  fig:samemachine  p3 same-machine bars per judge, SD error bars
  fig:mechanism    speaking-count Gini per condition, both drivers

Writes paper/figures_all.tex (the source tree the paper compiles from).
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
STATS = json.loads((ROOT / "results" / "analysis" / "final_stats_v2.json").read_text())
OUT = ROOT.parent / "paper" / "figures_all.tex"

MODELS = STATS["judges"]
SHORT = {"step-5-preview": "step-5-preview", "step-3.7-flash": "step-3.7-flash",
         "deepseek-v4.1-flash": "deepseek-v4.1-flash"}
VENDOR = {"step-5-preview": "StepFun", "step-3.7-flash": "StepFun",
          "deepseek-v4.1-flash": "DeepSeek"}
COLORS = {"step-5-preview": "blue!70", "step-3.7-flash": "red!70",
          "deepseek-v4.1-flash": "green!50!black!70"}
CONDS = [("full", "full"), ("round_robin", "rr"), ("no_jitter", "nj")]
XTICKLABELS = "Full system, No arb.\\\\ (round-robin), No jitter"

# ── fig 1: p2 ablation bars, bootstrap CI ──
p2 = STATS["p2_ablation_5rep"]
plots = []
for m in MODELS:
    coords = " ".join(
        f"({lbl}, {p2[m][c]['mean']:.3f}) +- (0, "
        f"{(p2[m][c]['ci'][1] - p2[m][c]['ci'][0]) / 2:.3f})" for c, lbl in CONDS)
    plots.append((m, coords))

fig1 = f"""\\begin{{figure}}[t]
\\centering
\\caption{{Ablation under three judges (primary driver, five repetitions; error bars: bootstrap 95\\% CI). Condition ordering varies across judges: the same-model judge ranks the full system below both ablations, the cross-vendor judge above both.}}
\\label{{fig:flip}}
\\begin{{tikzpicture}}[scale=0.50, transform shape]
\\begin{{axis}}[
    ybar, bar width=14pt, ymin=4, ymax=8,
    ylabel={{mean overall score (1--10)}},
    symbolic x coords={{full, rr, nj}},
    xticklabels={{Full system, No arb.\\\\ (round-robin), No jitter}},
    xtick=data, x tick label style={{align=center, font=\\small}}, ybar=2pt,
    enlarge x limits=0.25,
    legend style={{at={{(0.5,-0.28)}}, anchor=north, legend columns=3, font=\\small, draw=none}},
    error bars/y dir=both, error bars/error bar style={{thick}},
    nodes near coords, every node near coord/.append style={{font=\\tiny, /pgf/number format/fixed, /pgf/number format/precision=2}},
]
"""
for m, coords in plots:
    fig1 += (f"\\addplot+[fill={COLORS[m]}, draw={COLORS[m].split('!')[0]}, "
             f"error bars/.cd, y explicit] coordinates {{{coords}}};\n"
             f"\\addlegendentry{{{SHORT[m]} ({VENDOR[m]})}}\n")
fig1 += "\\end{axis}\n\\end{tikzpicture}\n\\end{figure}\n"

# ── fig 2: pairwise trajectories, 32 points each ──
jmap = defaultdict(dict)
for line in (ROOT / "results" / "raw" / "judgments.jsonl").read_text().splitlines():
    j = json.loads(line)
    if j["judge_model"] in MODELS and j["disc_id"].startswith(("p1-", "p2-", "p3-")):
        jmap[j["disc_id"]][j["judge_model"]] = j["overall"]
ids = sorted(d for d in jmap if len(jmap[d]) == len(MODELS))

fig2 = """\\begin{figure}[t]
\\centering
\\caption{Per-discussion overall scores for all three judge pairs (32 discussions). Dashed line: perfect agreement. No pair shows tight agreement.}
\\label{fig:trajectories}
\\begin{tikzpicture}
\\begin{groupplot}[group style={group size=3 by 1, horizontal sep=0.7cm},
    width=0.3\\textwidth, height=0.24\\textwidth,
    xmin=4, xmax=8, ymin=4, ymax=8,
    xtick={5,6,7,8}, ytick={5,6,7,8},
    grid=both, grid style={gray!20},
]
"""
for i, m1 in enumerate(MODELS):
    for m2 in MODELS[i + 1:]:
        pts = " ".join(f"({jmap[d][m1]:.2f}, {jmap[d][m2]:.2f})" for d in ids)
        fig2 += f"""\\nextgroupplot[xlabel={{{SHORT[m1]}}}, ylabel={{{SHORT[m2]}}}]
\\addplot[only marks, mark=*, mark size=1.2pt, blue!70] coordinates {{{pts}}};
\\addplot[dashed, gray, domain=4:8] {{x}};
"""
fig2 += "\\end{groupplot}\n\\end{tikzpicture}\n\\end{figure}\n"

# ── fig 3: p3 same-machine bars, SD ──
p3 = STATS["p3_same_machine"]
fig3 = """\\begin{figure}[t]
\\centering
\\caption{Same-machine replication (secondary driver, three repetitions; error bars: SD). Identical transcripts; only the judge differs. The driver's own model, a same-vendor sibling, and a cross-vendor judge produce three different condition orderings.}
\\label{fig:samemachine}
\\begin{tikzpicture}[scale=0.50, transform shape]
\\begin{axis}[
    ybar, bar width=14pt, ymin=4, ymax=8,
    ylabel={mean overall score (1--10)},
    symbolic x coords={full, rr, nj},
    xticklabels={Full system, No arb.\\\\ (round-robin), No jitter},
    xtick=data, x tick label style={align=center, font=\\small}, ybar=2pt,
    enlarge x limits=0.25,
    legend style={at={(0.5,-0.28)}, anchor=north, legend columns=3, font=\\small, draw=none},
    error bars/y dir=both, error bars/error bar style={thick},
    nodes near coords, every node near coord/.append style={font=\\tiny, /pgf/number format/fixed, /pgf/number format/precision=2},
]
"""
for m in MODELS:
    coords = " ".join(
        f"({lbl}, {p3[m][c]['mean']:.3f}) +- (0, {p3[m][c]['std']:.3f})"
        for c, lbl in CONDS)
    fig3 += (f"\\addplot+[fill={COLORS[m]}, draw={COLORS[m].split('!')[0]}, "
             f"error bars/.cd, y explicit] coordinates {{{coords}}};\n"
             f"\\addlegendentry{{{SHORT[m]} ({VENDOR[m]})}}\n")
fig3 += "\\end{axis}\n\\end{tikzpicture}\n\\end{figure}\n"

# ── fig 4: mechanism Gini, both drivers ──
mech = STATS["mechanism"]
g = {ph: [mech[f"{ph}{c}"]["gini"] for c, _ in CONDS] for ph in ("p2-", "p3-")}
fig4 = f"""\\begin{{figure}}[t]
\\centering
\\caption{{Speaking-count inequality (Gini over all three agents, zero-speech agents included) per ablation condition, both drivers.}}
\\label{{fig:mechanism}}
\\begin{{tikzpicture}}[scale=0.50, transform shape]
\\begin{{axis}}[
    ybar, bar width=14pt, ymin=0, ymax=0.45,
    ylabel={{Gini coefficient}},
    symbolic x coords={{full, rr, nj}},
    xticklabels={{Full system, No arb.\\\\ (round-robin), No jitter}},
    xtick=data, x tick label style={{align=center, font=\\small}}, ybar=2pt,
    enlarge x limits=0.25,
    legend style={{at={{(0.5,-0.28)}}, anchor=north, legend columns=2, font=\\small, draw=none}},
    nodes near coords, every node near coord/.append style={{font=\\tiny, /pgf/number format/fixed, /pgf/number format/precision=3}},
]
\\addplot+[fill=blue!70, draw=blue] coordinates {{(full, {g['p2-'][0]:.3f}) (rr, {g['p2-'][1]:.3f}) (nj, {g['p2-'][2]:.3f})}};
\\addlegendentry{{Primary driver}}
\\addplot+[fill=red!70, draw=red] coordinates {{(full, {g['p3-'][0]:.3f}) (rr, {g['p3-'][1]:.3f}) (nj, {g['p3-'][2]:.3f})}};
\\addlegendentry{{Secondary driver}}
\\end{{axis}}
\\end{{tikzpicture}}
\\end{{figure}}
"""

OUT.write_text(fig1 + "\n" + fig2 + "\n" + fig3 + "\n" + fig4)
npts = len(ids)
print(f"wrote {OUT} ({npts} points per trajectory pair)")
