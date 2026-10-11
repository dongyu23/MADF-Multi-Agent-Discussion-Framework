# CLAIMS_FROM_RESULTS — result-to-claim gate verdict

**Date**: 2026-10-11
**Gate**: ARIS `result-to-claim` (jury: step-3.7-flash via StepFun API — Codex MCP unavailable on this machine; manual-review-equivalent backend; executor was step-5-preview. Trace: `.aris/traces/result-to-claim/jury_step37flash.txt`)
**Evidence pre-check (deterministic, Step 1.5)**: 10 claims mechanically verified against `results/analysis/summary.json` + raw JSONL. 9 verified (3 with formatting-only diffs), **1 corrected**: C2 leniency offset cited as 0.59 → actual **+0.635** (14/17 positive). No hallucinated evidence.

## Intended claim (as tested)

In LLM-as-Judge evaluation of multi-agent roundtable discussion systems, judge-model identity systematically affects conclusions; the original MADF evaluation conclusions (component ablations) do not replicate under a more rigorous protocol.

## Jury verdict

```
claim_supported: partial
confidence: medium
```

### what_results_support

- **Judge identity is a systematic confound**: near-zero overall inter-judge reliability (Spearman ρ = −0.073, mean |diff| = 0.729), with step-5-preview acting as a consistently more lenient judge (higher scores in 14/17 discussions, mean offset **+0.635**).
- **The leniency offset is NOT self-preference**: self-preference deltas are small (step-5-preview: +0.05; step-3.7-flash: −0.10), and the leniency effect is present even when driver ≠ judge — it is a general judge-specific scoring behavior difference.
- **Ablation conclusions are judge-dependent**: under step-3.7-flash judge, point estimates align with the original paper's direction but are non-significant (p = 0.600, p = 1.000); under step-5-preview judge, the direction is fully reversed (ablations score higher than full system; p = 0.400, p = 0.100) — directly contradicting the original conclusions.
- **Original full-system score (6.20) replicates only under the step-3.7-flash judge**; step-5-preview judge gives 6.60 for the same system.

### what_results_dont_support

- That the original ablation conclusions *fully* fail to replicate: under the step-3.7-flash judge, point estimates are in the original's direction — the data show non-detection (small n), not absence.
- That the replication failure is *solely* due to protocol rigor: driver capability is confounded with judge identity in the 2×2 factorial.
- Generalizability: ablation used 1 topic, 3 of 5 original conditions; factorial cells have n = 4.

### missing_evidence

1. Ablation for the two omitted conditions (summary removal, rules removal).
2. Ablation on the second topic.
3. Fixed-driver factorial to disentangle judge identity from driver capability.
4. ≥5 reps per condition for adequate power.
5. Per-discussion inter-judge reliability (not just pooled).
6. Human annotation calibration to validate either judge's absolute scale.

### suggested_claim_revision (jury-endorsed, adopted in REPORT §6)

> In LLM-as-Judge evaluation of multi-agent roundtable discussion systems, judge-model identity is a major uncontrolled confound that systematically alters evaluation conclusions; original MADF component-ablation conclusions (which used a single judge matched to the system driver) are not robust to independent re-evaluation with a different judge model, with effect directions reversing depending on the judge used.

### next_experiments_needed (recorded for future work)

Full 5-condition × 2-topic × ≥5-rep × 2-judge ablation; fixed-driver factorial; third non-reasoning judge; human calibration subset; in-house replication of the original single-judge protocol to separate implementation differences from protocol effects.
