# Reviewer Memory

## Round 1 — Score: 4/10

Reviewer backend: codex (MCP transport broken by stale env key after key rotation; call executed via mcp__codex__codex once env was refreshed). Reviewer model: gpt-6-sol (OpenAI family, via getoken relay) — different family from the StepFun executor. Effort: xhigh. Verdict: not ready.

### Raw Reviewer Response (verbatim)

**Verdict**

- **Score: 4/10** for a top NeurIPS/ICML-style venue.
- **Ready for submission: No.**
- The central observation is plausible and potentially publishable as a careful audit, but the current artifact, statistical reporting, and reproducibility package are not reliable enough.

**What Checks Out**

- The selected experimental subset is **32 discussions**: 8 factorial + 15 primary-driver ablations + 9 secondary-driver replications.
- The reported three-judge agreement values match `work/results/analysis/final_stats_3judges.json`: Spearman values `-0.049/0.207/0.472`, MAD values `0.719/0.900/0.544`, and the reported per-dimension depth correlations.
- The three-judge leniency means and the primary-driver ablation means/SDs/Cliff's deltas match the selected raw records.
- The "self-preference is not detected" wording is better calibrated than claiming self-preference is absent.
- The `3 × 3` minimum two-sided Mann–Whitney resolution of `p = 0.1` is correct in the no-tie extreme case.

**Critical Weaknesses**

1. **The released raw artifact does not match the paper's stated dataset. Severity: Critical**
   - `work/results/raw/discussions.jsonl` contains **33 records**, including `warmup-1`; the paper says 32 without clearly identifying the exclusion.
   - `work/results/raw/judgments.jsonl` contains **128 judgments**, not 96: 32 each from four models, including undocumented `deepseek-v4.1-flash`.
   - The paper's derived analyses silently exclude the fourth judge. Including it changes the picture: for example, its agreement with `step-3.7-flash` is approximately `rho=-0.10`, and its leniency offset is different from the reported three-judge ladder.
   - **Minimum fix:** release a clean, explicitly labeled analysis dataset; state that warmup is excluded; either analyze the fourth judge or remove it from the released "raw" artifact and document the exclusion.

2. **The statistical pipeline does not implement what the paper claims. Severity: Critical**
   - `paper/sections/3_method.tex:89-97` says exact two-sided Mann–Whitney tests are reported alongside effect sizes and intervals, but neither `final_stats_3judges.json` nor the paper reports those p-values.
   - The final analysis code contains no Mann–Whitney implementation (`work/final_analysis_3judges.py:148-174`).
   - The ablation CIs are CIs for each group mean separately, not CIs for the ablation effect. "Disjoint group CIs" is not a substitute for an effect CI.
   - Multiple comparisons are not addressed: 3 judges × 2 ablation contrasts, plus agreement dimensions, self-preference, and multiple exploratory claims.
   - **Minimum fix:** add exact permutation/Mann–Whitney results for every prespecified contrast, report CIs for mean differences or Cliff's delta directly, and label the family of tests as exploratory or apply an appropriate correction.

3. **The self-preference bootstrap CI is not a valid bootstrap CI. Severity: Critical**
   - `work/final_analysis_3judges.py:135-143` and `work/stats_addendum.py:139-146` pool self and other observations, resample the pool, then randomly split it into groups.
   - That destroys the observed group labels and estimates a random-label/null distribution rather than resampling the self and other groups while preserving their sample sizes.
   - The point estimates `+0.05` and `-0.10` are correct, but the reported CIs are not justified by the stated bootstrap procedure.
   - **Minimum fix:** bootstrap self-group observations and other-group observations independently, or use an exact/randomization test and call the interval a randomization interval rather than a bootstrap CI.

4. **The judge prompt's turn-count cap is wrong whenever an agent never speaks. Severity: High**
   - `work/judge.py:50-58` computes counts only for agents appearing in the transcript. It omits zero-count agents.
   - This occurs in **7 of the 32 experimental discussions**. For example, `p2-full-r1` has counts `Jobs=2, Munger=1`, with Feynman absent; the code reports `max_gap=1`, although the full three-agent count vector is `2,1,0`, whose gap is `2`.
   - Therefore the hard caps "maximum difference ≤1" and "≥3" are applied to miscomputed statistics.
   - **Minimum fix:** include all three known agents with zero counts, regenerate the affected judge prompts and judgments, and rerun the downstream analysis.

5. **The factorial design does not cleanly identify driver and judge effects. Severity: High**
   - The nominal `2×2` factorial exists only for the 8 full-system discussions in Phase 1.
   - The ablation experiments use `step-5-preview` as driver, while the same-machine replication uses `step-3.7-flash`; they use different seeds, repetitions, and effectively different transcript samples.
   - The same-machine comparison is valid as a within-transcript judge comparison, but it cannot establish a general driver-independent causal effect.
   - **Minimum fix:** either run a balanced driver × judge design for each ablation condition, or weaken the language to "within this fixed-transcript replication, judge identity changes rankings."

6. **The paper overstates protocol fidelity and reproducibility. Severity: High**
   - `paper/sections/3_method.tex:24-39` acknowledges that persona skills were authored by the authors, duration/minimum-round behavior was changed, and the reference graph/persistence stack was replaced.
   - Yet the abstract and introduction call the result "verbatim" and "reproducible."
   - `apply_jitter` is described as deterministic (`work/madf_harness.py:174-182`), but the input ID is generated with `uuid.uuid4()` at `work/madf_harness.py:341`, so the jitter is not reproducible from the stated experiment seed.
   - **Minimum fix:** replace "verbatim" with "orchestration-faithful reimplementation," explicitly scope conclusions to the authored skills, and use stable logged agent IDs if reproducibility is claimed.

7. **There is a concrete denominator error in the mechanism table. Severity: Medium**
   - `paper/sections/4_results.tex:172-174` reports primary-driver forced speech as `5/25`, `0/25`, and `5/25`.
   - The primary ablation has five discussions × three rounds = **15 rounds per condition**, and the raw data give 5, 0, and 5 forced rounds. The denominator should be `15`, not `25`.
   - The secondary-driver denominators `1/9` and `0/9` are consistent.
   - **Minimum fix:** correct the table to `5/15`, `0/15`, and `5/15`, then regenerate the figure/table from one script.

8. **The paper cannot be compiled from the supplied `paper/` tree. Severity: High**
   - `paper/sections/4_results.tex:5` contains `\input{figures_all}`, but `paper/figures_all.tex` and `paper/figures/figures_all.tex` do not exist.
   - A separate `overleaf/figures_all.tex` exists, but it is not in the paper source tree and appears stale: its pairwise trajectory plots contain only 14 points per pair despite captions claiming 32 discussions.
   - The appendix points to nonexistent `exam2/...` paths rather than the actual `work/...` paths (`paper/sections/A_appendix.tex:37-49`).
   - **Minimum fix:** create one clean source tree that compiles, move or regenerate `figures_all.tex`, regenerate plots from raw data, and correct every appendix path.

**Claim Calibration**

- "Judge identity affects conclusions" is supported in this case study.
- "Leniency offsets are present" is supported for the selected three-model subset, but not as a vendor-general result.
- "Self-preference is not detected" is acceptable only after fixing the CI procedure and emphasizing low power.
- "No judge pair reaches substantial agreement" is too categorical without defining "substantial"; `rho=0.472` is not near zero in an absolute sense. Use exact values and say agreement is heterogeneous/modest rather than uniformly near-zero.
- "The ranking is a property of the judge, not the system" is too strong. The data show ranking instability under the tested judges and transcripts; they do not identify the true system ranking.
- The proposed reporting norm is reasonable as a recommendation, but the experiment does not establish it as a validated standard.

**Minimum Submission-Saving Package**

1. Clean and reconcile the raw artifact: 32 analyzed discussions, explicit warmup exclusion, explicit treatment of DeepSeek.
2. Fix zero-speaker turn counts and rerun affected judgments.
3. Replace the invalid self-preference bootstrap and add direct effect CIs.
4. Report exact tests and multiplicity handling, or remove inferential language and present the work as descriptive.
5. Correct `5/25` to `5/15`.
6. Repair the source tree and regenerate all figures from raw JSONL.
7. Reframe "verbatim," "reproducible," "near zero," and "property of the judge" claims.

With those fixes, this could become a credible scoped audit or workshop/Findings paper. In its current form, I would recommend **reject / major revision**, not submission.

---

## Round 1 — Executor Verification Notes (appended by executor after independent fact-check)

These are the executor's own verification results, kept separate from the reviewer's words above.

- **Confirmed as stated**: warmup-1 in 33 records; 128 judgments with 4 judges incl. deepseek-v4.1-flash (32 each); turn-count bug in judge.py (7 discussions with an absent agent; p3-no_jitter-r1 misreported gap 0 vs true 2 → harshest cap applied); forced-speech denominators wrong (primary 5/15, 0/15, 5/15 — reviewer right; secondary actually 1/14, 0/15, 1/14 — reviewer said "consistent", it is not; executor caught this additionally).
- **Rejected as overreach**: none of the numeric mismatches were fabricated; however the reviewer's framing of the DeepSeek judge as an artifact-hygiene problem understates the opportunity — the executor's study plan requires a cross-vendor judge, and the DeepSeek judgments are complete (32/32) and quality-comparable (mean 5.906 vs step-3.5-flash 5.925). Decision: promote deepseek-v4.1-flash to the analyzed cross-vendor judge (two StepFun + one DeepSeek), keep step-3.5-flash in the released artifact as a fourth released-but-not-analyzed judge.
- **To verify still**: bootstrap pooling claim in final_analysis_3judges.py:135-143; uuid4 jitter input at madf_harness.py:341; figure trajectory point counts.
