# Novelty Dossier — MADF Judge-Audit Paper (post-review revision)

Date: 2026-10-12. Executor: ZCode (StepFun step-5-preview). Reviewer: codex MCP (gpt-6-sol, xhigh).
Note: this supersedes NOVELTY_DOSSIER_initial.md (the pre-experiment version); the study is now complete with 32 discussions, three judges from two vendors, and three rounds of adversarial review already passed (score 4 → 6 → 7).

## The work under review

**Title**: "Judge Identity as a Confounding Factor: An Audit of LLM-as-Judge Evaluation for a Multi-Agent Discussion System"

**What it is**: An audit/case-study paper. Object of study: the evaluation protocol by which multi-agent *discussion* systems (several role-conditioned LLM agents deliberating on an open question) establish component-importance claims — a single LLM judge reads discussion transcripts and scores quality dimensions; differences between system variants are read as properties of the system.

**What was done**:
1. The audited system (MADF, commit 2f1baa; its own published evaluation is "Who Speaks Next?", arXiv 2412.04937, Frontiers in AI 2025, which used GPT-4 as a single judge, 1–5 scores, 50 conversations/condition) was re-implemented as a headless protocol-faithful testbed.
2. 32 discussions across conditions (2 drivers × 2 topics × 2 reps factorial; ablation full/round-robin/no-jitter × 5 reps under primary driver; same 3 conditions × 3 reps under secondary driver).
3. Every transcript scored by THREE judges from TWO vendors: step-5-preview + step-3.7-flash (StepFun) + deepseek-v4.1-flash (DeepSeek), using the audited system's own judge prompts verbatim (5 dimensions, 1–10, anchored rubrics, pre-computed turn-count statistics). A fourth judge (step-3.5-flash) is released but not analyzed.
4. Statistics: pairwise Spearman/MAD; leniency offsets (vs mean of other judges) with discussion-level bootstrap CIs; self-preference (same-driver vs other-driver under a fixed judge) with stratified bootstrap + exact permutation p; ablation contrasts with Cliff's δ, exact permutation p (all labelings), Holm correction, bootstrap CIs for differences and δ; judge-free mechanism metrics (Gini over all agents, forced-speech rates).
5. Robustness: 7 discussions affected by a defect found in the audited judge prompt (turn-count statistic omits zero-speech agents) were re-judged with corrected statistics; directions preserved. Parser-fallback sensitivity analysis (parse-failure dimensions treated as missing) — leniency ladder preserved.

**Findings**:
- F1: Inter-judge rank agreement is low and heterogeneous (ρ from −0.10 to +0.28 among the three analyzed judges; +0.47 max including the released fourth; MAD up to 0.87 on a 10-point scale). Depth-dimension agreement near zero or negative for pairs involving the flagship judge.
- F2: Judges form a leniency ladder (+0.61 / +0.02 / −0.62; extremes' CIs exclude zero; offsets persist on transcripts the judge did not produce); self-preference NOT detected (+0.05 / −0.10; permutation p ≥ 0.83, 4v4). Decomposes two mechanisms the standard "use a different family" mitigation conflates.
- F3: Single-judge component-importance conclusions vary with the judge (Cliff's δ from −1.00 to +0.78 across judges and drivers); the same-model judge reverses the audited ordering; no judge reproduces the audited magnitudes; in the same-machine replication (identical transcripts, only the judge varies) no judge reproduces the audited ordering on both contrasts; no contrast survives Holm correction.

**Proposal**: a case-study-derived multi-judge reporting heuristic (≥2 judges from different families/vendors; report agreement and per-judge offsets; downgrade conclusions when judges disagree).

## Core claims that carry the delta

1. **Judge identity is an unexamined confound for multi-agent discussion component-importance conclusions specifically** — prior work audits judge reliability in general (biases, human alignment) but does not measure what judge identity does to a system's published component ranking.
2. **Same-machine replication on multi-agent discussion transcripts** (identical transcripts, only judge varies) as the identification strategy for judge-driven conclusion flips.
3. **Leniency-offset vs self-preference decomposition on a real multi-agent system's own prompts**, with offsets shown to persist on non-self-driven transcripts.
4. **First quantification of cross-judge agreement for the multi-party discussion-transcript artifact** (as opposed to chat preference, QA, code, safety, translation).
5. Two engineering findings as byproducts: reasoning-model silent degradation of a non-reasoning-era protocol; a concrete defect in the audited judge's prompt (zero-speech agents omitted from turn-count statistics).

## Candidate prior work (all arXiv IDs verified via arXiv API 2026-10-12; verdict PASS, hallucination rate 0)

| # | Paper | arXiv | What it does | Overlap with this work |
|---|-------|-------|--------------|------------------------|
| 1 | All Verdicts are Not Equal: Rethinking LLM Judge Reliability | 2610.12083 | Pressure-tests judges: temperature-0 instability, position-order flips, item-specific (not model-level) reliability; proposes trustworthy verdict rate | Judge-instrument reliability audit; does not touch multi-agent system conclusions |
| 2 | Reliability without Validity (Norman et al.) | 2606.19544 | Judge rankings shift across benchmarks; reliability ≠ validity | Judge meta-evaluation at benchmark level |
| 3 | MAWILE: Multi-Axis Workbench for Inspecting LLM Evaluators | 2609.22599 | Workbench that audits a configured judge's sensitivity across prompt/rubric/input/output surfaces via controlled perturbations | Judge-instrument auditing tooling; no system-level component claims |
| 4 | Bias in the Loop: Auditing LLM-as-a-Judge for Software Engineering | 2604.16790 | Quantifies judge sensitivity and inter-judge agreement for SE tasks; prompt biases as confounders | Same audit genre, different artifact (code tasks) |
| 5 | Beyond Consensus: Downward Bias and Role Asymmetry in Multi-Agent LLM Judges | 2608.30373 | Single judge vs consensus-MAD protocols vs human alignment on subjective scoring; single judge wins | Multi-agent JUDGE panels vs humans; not multi-agent SYSTEM evaluation |
| 6 | When KV Cache Reuse Fails in Multi-Agent Systems | 2601.08343 | Judge decisions not invariant under KV-cache reuse; order perturbation amplifies inconsistency | Another confound of judge decisions (infrastructure-level); not system conclusions |
| 7 | Learning an Efficient Multi-Turn Dialogue Evaluator from Multiple LLM Judges | 2508.00454 | Distills 5 LLM judges into one evaluator; varies judge composition | Judge composition effects on a learned evaluator; not audit of a system's claims |
| 8 | Agent-as-a-Judge (ICML 2025) | 2410.10934 | Agentic evaluation of agentic systems; DevAI benchmark with 365 human hierarchical annotations | Uses judges for agent systems WITH human grounding; not a judge-identity audit |
| 9 | ChatEval | 2308.07201 | Multi-agent debate as evaluator; better human alignment than single agent | Judge-panel construction; alignment with humans |
| 10 | Who Speaks Next? (Nonomura & Mori) — THE AUDITED SYSTEM | 2412.04937 | Multi-party discussion with turn-taking mechanics; GPT-4 single judge, 1–5 scores, 50 convs/condition, plus human eval | The object under audit; its evaluation never varied judge identity |
| 11 | Judge's Verdict (Han et al.) | 2510.09738 | Catalogues 50+ models' agreement with human annotators | Human-agreement catalogue |

Also seen but NOT verified (no arXiv ID captured): "JuStRank: benchmarking LLM judges for system ranking" (ACL 2025, cited inside 2601.08343) — [UNVERIFIED]; and MAJ-EVAL / Multi-Agent-as-Judge (NeurIPS 2025 workshop poster, Chen et al.) — workshop poster, human-alignment framing.

## Questions for the reviewer

1. Is there any PUBLISHED paper that already contains this result — specifically: judge identity varied as an experimental factor to test whether a multi-agent discussion system's component-importance conclusions replicate, with a same-transcript (same-machine) design? Name it.
2. Given the candidate list, what is the closest prior work and what is the verifiable delta?
3. Is the genre (judge-reliability audits, 2026) crowded enough that this delta is thin? What would make it carry?
4. Does JuStRank (ACL 2025, benchmarking LLM judges for system ranking) or any unverified item above occupy the delta? What should be checked before submission?
5. Positioning: the paper proposes a reporting norm and audits one system (the first author's own framework). Is that a defensible contribution shape for a scoped audit venue, or is it two weak papers (narrow case study + unvalidated norm)?

=== NOVELTY VERDICT LIMITS (these bound how you judge, never how widely you search) ===
Search exhaustively; judge calibrated. Two failures waste months equally:
passing an idea a published paper already contains, and killing a viable idea
because the territory has neighbors.
1. Proximity is information, not a verdict. Someone working nearby goes in the
report; it is not by itself a reason to reject.
2. ABANDON has exactly one qualification: a specific published paper already
contains this result — name that paper. No named paper, no ABANDON.
3. Crowded-but-deltaed is PROCEED: state the delta in one sentence a reviewer
could verify. Thin or contested delta is PROCEED WITH CAUTION — say what
would make it carry, not why it should die. CAUTION is not a safe middle:
if you cannot name the specific thing that makes the delta thin, the
verdict is PROCEED.
4. Concurrent or competing work is not a veto. That is a race — report it and
let the user decide whether to run it.
5. A direct attack on a central problem is legitimate novelty when nobody has
executed it well. "This area is hot" does not mean "this area is taken."
6. This check is an early gate, never the last one — more triage, pilots, or
external review still stand between any idea and a paper, whatever order
this run uses. A wrongly passed idea dies cheaply at one of them; a wrongly
killed idea is never seen again. When torn between two verdicts, choose the
more permissive one.
Say plainly when an idea clears the check. Do not manufacture overlap.

Output format: verdict (PROCEED / PROCEED WITH CAUTION / ABANDON), novelty score 1–10 (5 = clear neighbors, defensible delta worth a pilot), closest prior work + delta in one verifiable sentence, what a reviewer would cite as prior work, and the single biggest risk to the delta.
