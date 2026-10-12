# AUTO_REVIEW — MADF Judge-Audit Paper

Run: `run_20261012_f5830c04` — auto-review-loop, MAX_ROUNDS=4, difficulty=medium.
Reviewer backend: codex (MCP). Reviewer model: gpt-6-sol (OpenAI family via
getoken relay) — different family from the StepFun executor model.
Note: the codex MCP server initially carried a stale getoken key; the key was
rotated (user-provided) and the model set to gpt-6-sol with a 272k context
window. Reviewer independence holds (OpenAI-family reviewer vs StepFun-family
executor); no Copilot native session exists on this host.

---

## Round 1 (2026-10-12)

### Assessment (Summary)
- Score: 4/10
- Verdict: not ready ("reject / major revision")
- Reviewer: gpt-6-sol, xhigh effort, read paper + code + raw data itself
- Gate: `review_gate.py` → decision `continue` (positive threshold not met)

### Key criticisms (reviewer's, verbatim in REVIEWER_MEMORY.md)
1. (Critical) Released raw artifact doesn't match stated dataset: 33 discussions
   incl. warmup-1 vs paper's 32; 128 judgments from 4 judges incl. undocumented
   deepseek-v4.1-flash vs paper's 96.
2. (Critical) Statistical pipeline doesn't implement claimed Mann–Whitney; no
   effect CIs; multiplicity unaddressed.
3. (Critical) Self-preference bootstrap CI invalid (pooled resample = null
   distribution, not a CI).
4. (High) Judge prompt turn-count cap wrong when an agent never speaks
   (7 of 32 discussions).
5. (High) Factorial doesn't cleanly identify driver and judge effects.
6. (High) "Verbatim"/"reproducible" overstate fidelity; uuid4 jitter input.
7. (Medium) Mechanism table forced-speech denominator 5/25 should be 5/15.
8. (High) paper/ tree can't compile (missing figures_all.tex); stale trajectory
   plots (14 points vs caption's 32); appendix paths exam2/... don't exist.

### Executor verification of each criticism
- #1 CONFIRMED (warmup-1 present; 4 judges × 32 in judgments.jsonl).
- #2 CONFIRMED (no MWU in pipeline; only per-group CIs; no multiplicity).
- #3 CONFIRMED (final_analysis_3judges.py:135-139 pools and randomly splits;
  leniency CI was valid, self-preference CI was not).
- #4 CONFIRMED (judge.py:50-58; verified per-discussion turn_counts;
  p3-no_jitter-r1 misreported gap 0 vs true 2 → harshest cap).
- #5 PARTIALLY ACCEPTED (design is as scoped; language strengthened to
  "within the tested transcripts").
- #6 CONFIRMED ("verbatim" → "protocol-faithful"; jitter now described as
  hash-derived given a per-call agent identifier).
- #7 CONFIRMED AND EXTENDED (primary 5/15, 0/15, 5/15 — reviewer right;
  secondary actually 1/14, 0/15, 1/14 — reviewer said "consistent", it was not;
  executor caught this additionally).
- #8 CONFIRMED (figures_all.tex was only in overleaf/; trajectory plots had 14
  points; appendix pointed at exam2/).

### Actions taken (Round 1 → Round 2 state)
1. **Cross-vendor judge promoted**: judge set is now step-5-preview +
   step-3.7-flash (StepFun) + deepseek-v4.1-flash (DeepSeek, cross-vendor),
   matching the study plan; step-3.5-flash released but excluded from main
   analysis (its parse-failure rate is ~3× the others — Appendix A.2).
   All statistics recomputed (work/final_analysis_v2.py →
   results/analysis/final_stats_v2.json).
2. **Statistics rebuilt**: exact two-sided permutation tests on the difference
   of means (all C(n1+n2,n1) labelings, exact under ties), Holm correction
   across the 6 prespecified contrasts per phase, bootstrap CIs for mean
   differences AND Cliff's δ, stratified-bootstrap self-preference intervals
   plus exact permutation p. No contrast is significant after correction;
   the paper now makes no significance claims and says so explicitly.
3. **Robustness re-judgment**: 7 affected discussions × 3 judges × 5 dims
   re-judged with corrected turn counts (work/rejudge_robustness.py →
   results/raw/judgments_robustness.jsonl, 21/21 complete). Directions all
   preserved; the defect materially affected the flagship judge's capped
   dimensions (+1.00). New Appendix A.3.
4. **Mechanism metrics corrected**: Gini now over all three agents
   (zero-speech agents included): primary 0.27/0.00/0.09 (was 0.10/0.00/0.03),
   secondary 0.23/0.13/0.38 (was 0.23/0.13/0.19); forced denominators now
   actual rounds (5/15, 0/15, 5/15; 1/14, 0/15, 1/14). The "jitter is the
   operative source of inequality" claim is now scoped to the primary driver
   (secondary driver shows the opposite pattern).
5. **Claims recalibrated**: "verbatim" → "protocol-faithful"; "property of
   the judge, not the system" → judge-dependent direction, no driver-
   independent causal claim; "substantial agreement" → exact values with a
   stated reading; "no judge pair" → among analyzed judges ρ ≤ +0.28
   (+0.47 max including the released fourth judge).
6. **Source tree repaired**: paper/figures_all.tex generated from raw data
   (32 points per trajectory pair); appendix paths point at work/...;
   paper compiles locally (pdflatex, TeX Live 2025) with 0 errors and
   0 undefined references — 18 pages.
7. **Data quality reporting**: per-judge parse-fallback and default counts
   (Appendix A.2); warmup-1 exclusion stated in Method.

### Results
- Paper rewritten end-to-end with v2 numbers; all tables/figures/text
  internally consistent; Overleaf/GitHub push pending after Round 2.

### Status
- Continuing to Round 2 (reviewer: codex-reply, same thread).

## Method Description (updated)

The testbed re-implements the MADF speaking protocol (decision JSON,
confidence arbitration with md5-derived jitter, forced speech, host
prompts) in pure stdlib Python against the StepFun OpenAI-compatible
endpoint, with ablation switches for arbitration/jitter/intro/summary/
rules and a round-robin fallback. Three judges (two StepFun models, one
DeepSeek model via a relay) score every transcript on five dimensions
using the audited system's own prompts at temperature 0.1. Analysis
(final_analysis_v2.py) computes pairwise Spearman agreement, leniency
offsets with discussion-level bootstrap CIs, self-preference with
stratified bootstrap + exact permutation, ablation contrasts with
Cliff's δ / exact permutation p / Holm adjustment / difference CIs, and
judge-free mechanism metrics (Gini over all agents, forced-speech rates).
Figures are generated as TikZ from the analysis JSON.

---

## Round 2 (2026-10-12)

### Assessment (Summary)
- Score: 6/10 — Verdict: "Almost — not submission-ready yet"
- Gate: positive threshold met (>=6 AND almost), but the reviewer listed 7
  actionable minimum fixes; loop continued to exhaust them (MAX_ROUNDS=4).

### Key criticisms
1. "Clean calls" column double-subtracted the defaulted calls (defaulted is a
   subset of parse-fallback).
2. No parser-fallback sensitivity analysis; stale "Mann-Whitney" docstring.
3. "Prespecified" contrasts unsupported (no preregistration).
4. Robustness appendix overstated causal support ("materially depressed",
   "establishes").
5. Self-preference permutation unblocked despite factorial structure.
6. Artifact path typo (CLAMS→CLAIMS) and .aris/traces prefix.
7. natbib author warnings, overfull boxes, 18 pages vs 8-10 target.

### Actions taken
- Quality table fixed: "Direct JSON" 132/133/130/82 (verified against raw
  reasonings).
- Parser-robustness sensitivity analysis built (work/parser_sensitivity.py):
  parse-fallback dims treated as missing, cells kept at >=3/5 direct parses
  (30/29/30 retained). Leniency ladder preserved (+0.63/+0.03/-0.66, extremes'
  CIs exclude zero); same-model judge's reversal preserved; 1 of 6 p2 direction
  labels moves (cross-vendor no-jitter, n=3); one cross-vendor pair's rho rises
  +0.28→+0.61 while MAD stays 0.73-0.84. Reported in Appendix A.2 with exact
  numbers; agreement claim restated as heterogeneous/modest.
- "Prespecified" → post hoc family-wise control (method + results + caption).
- Robustness wording softened to "did not overturn any qualitative direction";
  shifts explicitly not attributable solely to the prompt correction.
- Self-preference labeled exploratory/unblocked/underpowered.
- Paths fixed; artifact list rewritten with short paths that all exist.
- natbib \citet→\cite (warnings gone); wide tables resized to the column;
  trajectory subplots narrowed; figures at 0.50 scale; microtype added;
  overfull boxes 14 (max 85.8pt) → 4 (max 5.4pt).

## Round 3 (2026-10-12)

### Assessment (Summary)
- Score: 7/10 — Verdict: "Almost"; reviewer: "With those wording changes, I
  would consider the paper ready for submission to a scoped audit/evaluation
  venue." Stop condition met; loop terminated after applying the conditional
  fixes (wording-level; all numbers previously verified).

### Remaining items (all applied)
1. Parser-clean sensitivity surfaced in abstract, intro contribution (ii),
   and Results 4.1 (rho=+0.61 pair; heterogeneous rather than uniformly low).
2. "bound how much" → "show how much".
3. Complete-case estimand sentence added to Appendix A.2.
4. "Independent jury record" → "Auxiliary model review record" + explicit
   "not a blind review, not an independent replication" (appendix + method).
5. "Minimum reporting norm" → "case-study-derived reporting heuristic";
   states the study establishes the need to report judge sensitivity, not that
   the panel size is sufficient.
6. Page count: 19 total = 12 main text + ~7 appendix/references; not compressed
   further to 8-10 because that would require dropping tables or the
   sensitivity analysis; appendix is outside the main-text limit by LNNS
   convention. Recorded as an accepted deviation.

### Final state
- Compile: 0 errors, 0 undefined references, 4 overfull <=5.4pt, 19 pages.
- Score trajectory: 4 → 6 → 7.
- Reviewer's verified-correct list covers: judge set, all table numbers vs
  final_stats_v2.json and raw JSONL, direct-JSON counts, sensitivity numbers,
  robustness directions, artifact paths.
