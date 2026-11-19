# Reviewer Control Plane — GLM-5.2 Reviewer Capability Gates (H6, slim)

> **Fold destination** (BRF-T7-F15, BRF-T7-1, route 1b, 2026-11-03): renamed from `glm52-reviewer-capability-gates.md`; every former handoff of this plan target is a `## Track:` with its own gate marker: `glm52-reviewer-capability-gates`, `reviewer-escalation-and-human-gate-policy`, `reviewer-latency-and-sampling-budget`, `reviewer-model-ablations` (rows REV-05, REV-06, REV-07 retired into REV-02). The former `glm52-reviewer-capability-gates.md` body is `## Track: glm52-reviewer-capability-gates`; tracks those handoffs already had are lifted verbatim after their owner.

> **RETARGETED 2026-09-22 to DeepSeek-V4.1-Flash, by operator decision.** GLM-5.3-Flash (the
> 2026-09-01 subject) was DELETED from disk on 2026-09-22, operator-confirmed — the UD-Q4_K_XL
> model, its DFlash2 drafters and the three `llama.cpp-experimental-glm53-*` worktrees (the
> branches remain pushed). No GLM-5.3 reviewer gate had been run, so nothing measured is lost.
> Operator instruction: "translate the GLM-5.3-Flash handoffs to target DeepSeek-V4.1 instead
> (assuming they are applicable)". The new subject is `deepseek-ai/DeepSeek-V4.1-Flash`, arch
> **`deepseek41`** (763B MoE, 384 experts, 40 layers, 3 MTP layers, Engram n-gram tables,
> hyper-connections, sparse attention). The artifact is `antirez/deepseek-v4.1-flash-gguf` Q4,
> ~483 GiB: Q4_K routed experts; Q8 attention, shared experts and output; native FP8 Engram
> tables ~189 GiB. It has been downloading since 2026-09-22. Filename is still retained for
> link stability.
>
> **Applicability.** The same split as the 2026-09-01 retarget applies. The three capability
> questions (GC-1/2/3), the corpus and harness assets, the representation guards and the rule
> against rerunning unchanged slices all carry over unchanged. They are model-agnostic.
> Nothing from GLM-5.3-Flash is carried forward: its `glm5next` arch, its `indexer.kpool` field,
> its UD-Q4_K_XL quant profile and its footprint are all VOID for this subject. The GLM-5.2
> `indexer_top_k` schedule is still historical only. DeepSeek-V4.1's sparse-attention selection
> cap must be derived from scratch on the ported tree, by the same method (a prompt-band sweep
> with an exact-output check). An under-sized cap corrupts output before it degrades quality.
>
> **BLOCKED until [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md) clears its
> port, load/coherence and sparse-attention-disposition gates (the equivalents of INF-69 T0-T2).**
> Production v9 knows only `deepseek4`, not `deepseek41`, so no tree on this host can serve the
> model yet. An experimental port is required first.
>
> ---
>
> *Superseded banner, retained as history:*
>
> **RETARGETED 2026-09-01 to GLM-5.3-Flash, by operator ruling.** The original subject, GLM-5.2
> UD-IQ2_M, was ruled KILL (OP-8) and its 223 GB artifact deleted, so every gate below was
> unrunnable as written. Filename retained for cross-reference stability (~19 inbound links), as
> the GLM-5.2 evaluation handoff did before it.
>
> **What transfers** (model-agnostic, and the genuinely valuable half): the three capability
> questions — GC-1 strict-IF / typed emission, GC-2 rubric authoring, GC-3 why-diagnosis — and the
> whole corpus/harness asset built to ask them honestly: the representation-mixing bug fix (the
> runner refuses `substring`/`exact_match` answer-fragment rows and records mixed source-suite /
> scoring representations), the C-CRAB accept-control relabel that produced a decision-grade
> hard-accept pool, and the standing rule against rerunning unchanged slices. None of that depended
> on which model was behind the endpoint.
>
> **What does NOT transfer** — treat as historical evidence about a deleted model, never as
> carry-forward state: every GLM-5.2 *measurement* (`FA 41.7%` / `FR 25.0%` on matched C-CRAB,
> JudgeBench-GPT `22/24`, SWE-bench-Verified `22/24`), and every GLM-5.2 *serving* constant — the
> next-power-of-two `indexer_top_k` schedule (`2048`/`4096`/`16384`), the DSA-DENSE-MASK
> disposition, and the protocol/channel matrix's prompt bands. GLM-5.3-Flash is arch **`glm5next`**
> (288x10B), not `glm-dsa`, and it carries a NEW `indexer.kpool` field: those constants must be
> re-derived, not inherited. Assuming them is the fastest way to get a wrong quality verdict.
>
> **BLOCKED until [`glm53-flash-evaluation.md`](../completed/glm53-flash-evaluation.md) (INF-69) clears T0-T2**:
> no tree on this host is yet known to load `glm5next`, and the `indexer_top_k`/`kpool` semantics
> gate output correctness before they gate quality — an under-sized cap corrupted GLM-5.2's exact
> output above its prompt band, and a quality run under a wrong cap measures the cap, not the model.

**Status**: active — **re-blocked 2026-09-22 on the DeepSeek-V4.1-Flash port** (see banner). The rest of this line is the GLM-5.2 status, kept as history: GC-0d reviewer-serving chat protocol/schema gate closed; GC-1/2/3 smoke probes and repair smokes now executed under the next-power-of-two GLM top-k schedule (`2048` through ~2.05K, `4096` through ~3.05K, `16384` at ~12.05K). Natural-prompt repair smokes pass the small synthetic checks. The initial real near-miss slices were quality-blocked, then diagnosed as representation-mixed: the binary-schema n=24 selected exact-answer controls, substring/code-prefix controls, Python patch diffs, and C-CRAB patch reviews in one "balanced" slice. The runner now records/refuses mixed source-suite/scoring representations and refuses `substring`/`exact_match` answer-fragment rows by default. Homogeneous `cruxeval/exact_match` n=24 improved to `FA 0.0%`, `FR 16.7%` only when scoped as exact-answer review; matched C-CRAB patch-diff n=24 failed by over-approval (`FA 91.7%`, `FR 16.7%`). Curated oracle-note repair now rejects all six old false-accepted C-CRAB hard negatives in a targeted n=12 screen (`FA 0.0%`). The mechanical c-CRAB accept-control relabel/rebuild now yields a decision-grade hard-accept pool (`n=24`), and the matched C-CRAB P-REV-1 confirmation completed but failed admission (`FA 41.7%`, `FR 25.0%`, parse `0.0%`). External evidence is mixed: JudgeBench-GPT exact choice is positive (`22/24`, `91.7%`) and SWE-bench-Verified accept controls are positive (`22/24`, `FR 8.3%`, parse `0/24`), but neither clears C-CRAB hard-negative patch-review risk. GLM remains research-only; patch-review role admission is not cleared. Raw `/completion` and `/v1/completions` remain unvalidated and are not the default reviewer-serving channel.
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, quantization, local_inference
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related / ownership boundary**: **infra tasks (download/sha256/load-smoke/CPU-bench/expert-routing-skew profile) live in [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md)** (parallel-session-owned) — this handoff holds ONLY the reviewer-specific capability gates and must not duplicate that work. Kernel-side blockers live in [`gemma-challenge-kernel-techniques-v7.md`](rocm-kernel-authoring.md#track-gemma-challenge-kernel-techniques-v7); GLM cache/runtime reconciliation is closed by K23 / experimental-v7 `3dee86a5a`, sparse final-attention remains kernel work, and current-source 32K needle/coherence currently fails with malformed `peg-native` output.
**Repo**: `epyc-orchestrator` + `epyc-inference-research`

**Priority**: LOW — T7 (rank 163): 12 of 25 open items blocked; reviewer gates wait on the DeepSeek-V4.1-Flash retarget and approved claims.

## Track: glm52-reviewer-capability-gates
<!-- gate: INF-77 -->

> Folded from the body of `handoffs/active/glm52-reviewer-capability-gates.md` (row REV-02), from its first `##` section on, @ `28b488861d1f` on 2026-11-03 (BRF-T7-F15, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.

#### Objective

Take GLM-5.2 UD-IQ2_M (754B glm_moe_dsa, ~239GB, downloaded, true >64K stale-binary DSA-engagement smoke-passed, and current-source DSA-wired) from "loads" to "validated typed-decision reviewer candidate" — the reviewer-specific capability layer only. Current reviewer admission is now blocked by failed claim-grade quality, not by first smoke execution or accept-control labeling: inference-research commit `a6651ed` plus the follow-up sweep show `glm-dsa.attention.indexer.top_k` is the final-attention KV selection cap, `3072` fails at 2.1K/3K, `8192`/`12288` fail at 12K, next power-of-two caps are the observed safe path (`2048`, `4096`, `16384` for the tested prompt bands), and the 2026-07-18 chat protocol/schema matrix passed exact free-text and JSON-schema outputs at actual ~2.9K/~12.0K prompt bands. The initial direct reviewer-capability smokes exposed repairable prompt/scorer issues and the repaired synthetic smokes pass. The first near-miss corpus slices exposed a runner/corpus-contract bug: unfiltered "balanced" samples mixed incompatible candidate representations, including 100-character code-prefix accept controls. The targeted C-CRAB oracle-note n=12 confirmation fixed the old false-accept half (`6/6` rejects correct), the mechanical c-CRAB accept relabel made the accept side decision-grade, and the matched P-REV-1 run then failed admission (`FA 41.7%`, `FR 25.0%`). External JudgeBench-GPT then passed pairwise exact choice (`22/24`) and SWE-bench-Verified accept controls passed `22/24` (`FR 8.3%`), but neither provides the missing hard-negative patch-review clearance. Do not rerun unchanged `multi_oracle`, unchanged binary-schema, answer-fragment slices, the same C-CRAB P-REV-1 policy, or the same SWE accept-only slice; next progress requires a new reviewer repair hypothesis, scoped-use decision, or alternate reviewer routing.

**2026-07-18 acceleration-gating note (v7 lever audit).** GLM-5.2 **acceleration** EV is
*contingent on this quality gate*, not standalone. The two real GLM kernel levers — the
native-GLM-MTP forward-graph port ([tree-draft-forward-port-plan.md](../completed/tree-draft-forward-port-plan.md),
+34–89% decode) and the real sparse final-attention path ([llama-cpp-dsa-contribution.md](rocm-kernel-authoring.md#track-llama-cpp-dsa-contribution)
D2, currently DSA-DENSE-MASK) — are explicitly **sequenced AFTER GC-shadow-repair4b → P-REV-1**.
Rationale: the flagship GLM role is cross-family patch reviewer, and patch-review still
over-approves (FA up to 91.7%); ~1–3 weeks of kernel work on a model that cannot yet do its
job has near-zero EV. GC-shadow-repair4b has now executed and failed admission, so further
kernel acceleration remains downstream of an external ground-truth verdict or a new reviewer
repair hypothesis.
Operator exception recorded the same day: bounded source prep for native GLM-MTP is allowed
while quality work continues. The `glm-dsa` experimental-v7 scaffold now builds, survives
bounded same-model `draft-mtp` smokes, and has a matched long-output acceleration pass after
the 2026-07-19 DeepSeek32/GLM-DSA NEXTN repair. This is an acceleration result only; reviewer
admission remains failed on C-CRAB P-REV-1.

**2026-07-19 native GLM-MTP A/B disposition.** The first real generated-token A/B found a
zero-chunk `draft-mtp` serving failure, then the DeepSeek32/GLM-DSA NEXTN row-selection repair
superseded it on the matched long-context retry. No-spec served a `2931`-token prompt and `512`
completion tokens at `22.56` prompt t/s / `2.49` decode t/s. Repaired same-model `draft-mtp`
served a `2919`-token prompt and `512` completion tokens at `22.77` prompt t/s / `5.33` decode
t/s, with `515` streamed chunks and draft alpha `0.933` (`376/403` accepted). Evidence:
`epyc-inference-research/docs/data/glm52_native_mtp_ab_20260719.md` and raw repair artifact
`epyc-inference-research/data/glm52_native_mtp_ab/glm52-native-mtp-draft-long-repair-20260719T195037Z/`.
This is not a reviewer-quality rerun and does not admit GLM as reviewer.
The source hardening assertion also landed on experimental v7: `test-llama-archs` now builds a
GLM-DSA+single-NextN graph and asserts unmasked target-side NEXTN retains all token rows through
`h_nextn` before output-row selection. Focused `glm-dsa` and `deepseek32` validation passed.

**2026-07-19 RM-2 reviewer-slate cross-check.** The fast MI210 reviewer arms did not rescue
the role choice on the same decision-grade C-CRAB slice. Qwen3.6-27B dense Q8 was faster but
over-approved (`FA 54.2%`, `FR 16.7%`, `AUC 0.503`); Qwable IQ4_XS standalone failed
(`FA 54.2%`, `FR 45.8%`, `AUC 0.438`); Qwen+Qwable scaffold improved FA/AUC but still
missed too many accepts (`FA 33.3%`, `FR 41.7%`, `AUC 0.659`). See
[`reviewer-model-ablations.md`](reviewer-control-plane.md#track-reviewer-model-ablations) RM-2.fast/RM-2.fast-b and
`epyc-inference-research/docs/data/reviewer_model_ablations_rm2_fast_ccrab_p_rev1_20260719.md`.
Conclusion: do not treat a small/fast arm as the current production reviewer; next progress is
the completed RM-2.next evidence, RM-3 screening, Ref external judge-of-judge, or a new
scaffold/reviewer repair hypothesis.

**2026-07-19 external JudgeBench-GPT live gate.** The first judge-native external run completed
under `p_rev1` with attestation `MEASUREMENT-P-REV1-OPERATOR-APPROVED-20260719`. The original
strict schema scorer reported `15/24` because seven otherwise valid A/B decisions used 0-100
confidence values. The corrected exact-choice rescore is `22/24` (`91.7%`), parse `0/24`,
balanced decisions (`12` A / `12` B), with confidence-scale warnings on `7/24` rows. Evidence:
`epyc-inference-research/data/glm52_external_ground_truth_direct/glm52-external-judgebench-gpt-n24-p-rev1-20260719T154517Z/`,
rescore artifact `.../glm52-external-judgebench-gpt-n24-p-rev1-choice-rescore-20260719/`, and
summary `epyc-inference-research/docs/data/glm52_external_judgebench_gpt_p_rev1_live_20260719.md`.
This is positive GLM judge-preference evidence, not patch-review admission.

**2026-07-19 external SWE-bench-Verified direct-runner prep.** The external direct runner now
supports homogeneous `patch_review_oracle` rows without `candidate_b`, dispatches them to the
existing ReviewDecision JSON schema and parser, includes `FAIL_TO_PASS`/`PASS_TO_PASS` oracle
context in the prompt, and reports patch-review false-reject/false-accept rates rather than
pairwise accuracy only. Dry-run artifact:
`epyc-inference-research/data/glm52_external_ground_truth_direct/glm52-external-swebench-verified-n24-p-rev1-dryrun-20260719/plan.json`;
summary: `epyc-inference-research/docs/data/glm52_external_swebench_verified_p_rev1_dryrun_20260719.md`.
It was `execution_allowed=true` with no refusal reasons on the 24-row SWE slice.

**2026-07-19 external SWE-bench-Verified live gate.** The live direct run completed under
`p_rev1` with attestation `MEASUREMENT-P-REV1-OPERATOR-APPROVED-20260719` on the same 24-row
accept-control slice. Result: `22/24` correct approvals (`91.7%`), `FR 8.3%` (`2/24`), parse
`0/24`, `FA` not measured because this SWE slice contains no hard negatives. The two false
rejects were `django__django-12663` and `pylint-dev__pylint-8898`. Evidence:
`epyc-inference-research/data/glm52_external_ground_truth_direct/glm52-external-swebench-verified-n24-p-rev1-20260719Tlive/`;
summary: `epyc-inference-research/docs/data/glm52_external_swebench_verified_p_rev1_live_20260719.md`.
This is positive accept-control evidence, but it still does not clear C-CRAB hard-negative
patch-review risk or admit GLM as the production reviewer.

**2026-07-19 GC-external-1e repair-or-route verdict.** Current evidence supports a narrow
route-away decision for production patch review: **do not admit GLM-5.2 as the production
patch reviewer and do not spend another unchanged GLM patch-review run.** Keep GLM scoped to
research, judge-preference checks, accept-control diagnostics, and future repair hypotheses
only. A future GLM repair must first state a concrete mechanism that can reduce C-CRAB
hard-negative false accepts without exploding false rejects, then pass a cheap n=12/n=24
screen before another P-REV-1 confirmation. The production-reviewer search should move to
H5 RM-3 screening, Ref external judge-of-judge, or any new reviewer candidate/repair with a
specific quality rationale. A0/A1/A3 and RM-2.fast are now evidence inputs, not future work.
This is not a production
cutover decision; it removes GLM-specific unchanged reruns from the critical path and leaves
v7 promotion policy to [`v7-promotion.md`](../completed/v7-promotion.md).

#### 2026-07-19 DIRECTIVE (operator) — test GLM quality on EXTERNAL ground-truth benchmarks, not hand-labeled corpora

The C-CRAB accept-control labeling issue is now resolved mechanically and the matched P-REV-1
C-CRAB run failed GLM admission. **Do not keep iterating C-CRAB labels or rerun that same policy;
use the ground-truth benchmarks already on disk** (`/mnt/raid0/llm/datasets/`), which ship
human/test-oracle answer keys — no label-building, no self-certification, no circularity:
- **Reviewer/judge quality** → `judgebench`, `reward-bench` + `reward-bench-2`, `llmbar`, `judgelm-100k` (human ground-truth verdicts). Score GLM's accept/reject or pairwise choice by **exact match** against their key → deterministic FA/FR, `decision_grade` true.
- **Patch review (accept/reject a diff)** → `swe-bench-verified` (human-validated FAIL_TO_PASS/PASS_TO_PASS **test oracle**: good patch = patched repo passes hidden tests). Fully mechanical.
- **Claude-as-judge** is authorized (operator, 2026-07-19) as a labeler for any scenario the ground-truth sets don't cover — a full-precision model grading a 2-bit one is a valid teacher/judge, not circular (the only circular case is GLM-grading-GLM). Freeze such labels with per-row rationale.

**Sequencing (important):**
1. **Reviewer/judge quality gate = RUN NEXT.** These prompts fit GLM's coherent **≤12K** band, so this — the actual v7-promotion blocker after the failed C-CRAB P-REV-1 gate — does **not** wait for any kernel fix. Pick one judge-native set + SWE-bench-Verified, keep prompts ≤12K under the validated `indexer_top_k` schedule, score exact-match. This is what unblocks a broader claim-grade GLM quality verdict or a firm rejection of the role.
2. **Long-context quality (>12K) is a SEPARATE, LATER track** gated behind the **`indexer_top_k` / sparse-final-attention fix** (D2 in [`llama-cpp-dsa-contribution.md`](rocm-kernel-authoring.md#track-llama-cpp-dsa-contribution)). GLM currently emits malformed output past ~12K because the top-k cap doesn't scale (32K needle fails); that is the durable fix for long-context, and it is **orthogonal** to whether GLM is a good *patch* reviewer. Do not couple the reviewer-quality verdict to it.

Concrete dataset pick + runner wiring being finalized; see [`../../docs/reference/model-probe-scoreboard.md`](../../docs/reference/model-probe-scoreboard.md). Do NOT re-run the observation-only nearmiss-v1 slices — they're superseded by this directive.

#### Prioritized Task List

- [x] **GC-0 — Evidence hygiene / runner contract**: reviewer-facing GLM long-output or typed-decision probes must consume only instrumented GLM runs with streaming progress, retained trace logs/server-log timing extraction, and a minimum completion-token floor. `/metrics` samples are acceptable when available, but are not the primary progress channel for a long busy GLM request. The attempted current-source 96K run at `/mnt/raid0/llm/tmp/glm52-current-source-96k-quality-20260717T144022Z/plan.json` is excluded as process-failure-only because it had no progress telemetry and only `max_tokens=32`. ✅ 2026-07-17
- [x] **GC-0a — Current-source 32K needle/coherence gate executed**: default reasoning and `--reasoning off --reasoning-budget 0` both completed full prompt ingest plus 64-token decode, then llama-server returned HTTP 500 because generated output did not match `peg-native`; hidden code `GLM52-NEEDLE-7F3A` was absent. Summary: `/mnt/raid0/llm/epyc-inference-research/data/glm52_dsa_probe/current_source_32k_needle_20260717T1755Z/summary.json`. ✅ 2026-07-17
- [x] **GC-0b — Top-k cap diagnosis closed**: the active blocker is now narrower than "GLM malformed output." Inference-research commit `a6651ed` shows `glm-dsa.attention.indexer.top_k` is the final-attention KV selection cap: `2048` passes exact `READY` at `1767/2056` prompt tokens but fails at `2168/3045/12043`; `4096` recovers `2168/3045`; `16384` recovers `12045`. ✅ 2026-07-18
- [x] **GC-0c — Smallest-safe prompt-length-aware top-k schedule**: follow-up sweep rejected `top_k=3072` at 2.1K/3K and `8192`/`12288` at 12K; exact `READY` is only observed on next power-of-two caps (`2048`, `4096`, `16384`) for these prompt bands. GC-1/2/3 should run under that schedule, not a flat default cap. ✅ 2026-07-18
- [x] **GC-0d — Protocol-channel matrix**: reviewer-serving chat/completions matrix passed exact free-text `READY` and exact JSON-schema `{"decision":"allow"}` at actual `2894/2898` prompt tokens with `indexer_top_k=4096` and `12044/12045` prompt tokens with `indexer_top_k=16384`. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_protocol_channel_matrix/glm52-gc0d-chat-p2168-p12000-20260718T0120Z/summary.json`. The first all-endpoint attempt was stopped after raw completion endpoint cost/pathology; raw `/completion` and `/v1/completions` stay unvalidated and must be probed only narrowly if a future route needs them. ✅ 2026-07-18
- [x] **GC-1 — Strict-IF / typed-emission smoke**: direct CPU-only GLM runner (`scripts/benchmark/glm52_reviewer_capability_direct_runner.py`) executed `strict_if`, `m=3`, `k=2`, chat channel, `indexer_top_k=4096`. Grammar/schema lane passed `3/3` schema-valid ReviewDecision emissions (`emission_rate=1.0`); free lane parsed JSON but failed schema validity `0/3` by emitting `blocking.tripwire=null`. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_capability_direct/gc1-strict-if-smoke-20260718Tglm52/summary.json`. Observation-only; proves schema constraint is necessary, not reviewer admission. ✅ 2026-07-18
- [x] **GC-1r — Strict-IF free-lane repair smoke**: direct runner gained natural-prompt mode plus explicit numeric-confidence/boolean-tripwire instructions. First repair narrowed the miss to `confidence:"low"`; second repair passed free-lane schema validity `3/3` (`emission_rate=1.0`) at prompt tokens `133`, `indexer_top_k=4096`, CPU-only 192t. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_capability_direct/gc1-free-natural-repair2-20260718Tglm52/summary.json`. Observation-only; still keep grammar/schema in production reviewer-serving path unless P-REV-1 proves free mode is acceptable. ✅ 2026-07-18
- [x] **DISPOSITION GATE — RESOLVED 2026-09-01: RETARGET at GLM-5.3-Flash** (operator ruling; the alternative was closing this handoff). The capability gates and the corpus/harness work survive the subject change; the GLM-5.2 measurements and serving constants do not. Re-blocked on INF-69 T0-T2. ✅ 2026-09-01
- [x] **DISPOSITION GATE 2 — RESOLVED 2026-09-22: RETARGET at DeepSeek-V4.1-Flash** (operator decision). GLM-5.3-Flash was deleted from disk before any gate below ran on it. The gates carry over; nothing GLM-5.3-specific does. Re-blocked on the port, load/coherence and sparse-attention gates in [`deepseek-v41-flash-evaluation.md`](deepseek-v41-flash-evaluation.md). ✅ 2026-09-22
- [ ] **GC-1a — Strict-IF / typed-emission claim-grade gate (P-REV-1)**: rerun on the approved claim-grade reviewer corpus/K-of-M protocol after the MEASUREMENT amendment; keep grammar/schema in serving path. **[RETARGETED 2026-09-01 → GLM-5.3-Flash; blocked on INF-69 T0-T2.]** Subject is now GLM-5.3-Flash; the corpus/K-of-M protocol and the schema lane carry over unchanged. **[RETARGETED 2026-09-22 → DeepSeek-V4.1-Flash; blocked on the port/load/sparse-attention gates of `deepseek-v41-flash-evaluation.md`.]** GLM-5.3 was deleted unrun. The corpus, the K-of-M protocol and the schema lane still carry over. The typed-emission smoke (GC-1/GC-1r equivalent) must be re-run on the V4.1 chat template before the claim-grade gate. The GLM-5.2 schema-validity results do not transfer.
- [x] **GC-2 — Rubric-authoring grammar smoke**: direct CPU-only GLM runner executed `rubric_authoring`, grammar/schema lane, `m=3`, chat channel, `indexer_top_k=4096`. All three outputs were schema-valid rubrics, but quality was shallow (`mean_composite=0.75`, `mean_axis_coverage=0.25`, `mean_grounding_rate=1.0`). Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_capability_direct/gc2-rubric-grammar-smoke-20260718Tglm52/summary.json`. Observation-only; do not treat as authoring capability pass. ✅ 2026-07-18
- [x] **GC-2r — Rubric-authoring repair smoke**: rubric prompt now requests four canonical axes and the deterministic scorer normalizes common axis aliases. Natural-prompt grammar lane passed `3/3` schema-valid rubrics with `mean_axis_coverage=1.0`, `mean_count_ratio=1.0`, `mean_grounding_rate=1.0`, `mean_composite=1.0`; completion lengths were `247-251` tokens, so the 256-token smoke budget was just sufficient. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_capability_direct/gc2-grammar-natural-repair-20260718Tglm52/summary.json`. Observation-only; frontier-authored references/corpus breadth still open. ✅ 2026-07-18
- [ ] **GC-2a — Rubric-authoring claim-grade/repair gate**: broaden the task set against frontier-authored references and/or revise the rubric prompt/schema to force axis diversity before using GLM as the heavyweight rubric author. **[RETARGETED 2026-09-01 → GLM-5.3-Flash; blocked on INF-69 T0-T2.]** Subject is now GLM-5.3-Flash; the canonical-axis prompt and alias-normalising scorer carry over unchanged. **[RETARGETED 2026-09-22 → DeepSeek-V4.1-Flash; blocked on the port/load/sparse-attention gates of `deepseek-v41-flash-evaluation.md`.]** The canonical-axis prompt and the alias-normalising scorer still carry over. GC-2r's `mean_composite=1.0` is GLM-5.2 evidence and is not a V4.1 prior.
- [x] **GC-3 — Why-diagnosis smoke**: direct CPU-only GLM runner executed `why_diagnosis`, free lane, `m=3`, chat channel, `indexer_top_k=4096`. GLM detected that a defect existed in `3/3`, but matched the intended root cause in `0/3` (`that_minus_why_gap=1.0`). Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_capability_direct/gc3-why-smoke-20260718Tglm52/summary.json`. Observation-only; why-diagnosis is currently failed. ✅ 2026-07-18
- [x] **GC-3r — Why-diagnosis repair smoke**: the built-in synthetic GC-3 task set now includes concrete defective snippets/symptoms and broader gold-cause aliases. Natural-prompt free lane passed `3/3` defect detection and `3/3` root-cause match (`why_match_rate=1.0`) on off-by-one/midpoint, missing None-guard, and wrong arithmetic-operation causes. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_capability_direct/gc3-why-natural-repair2-20260718Tglm52/summary.json`. Observation-only; corpus-v1/P-REV-1 gate still open. ✅ 2026-07-18
- [ ] **GC-3a — Why-diagnosis corpus/claim-grade gate**: retest on corpus-v1 after P-REV-1 sign-off; IQ2 quant may degrade why-diagnosis more than that-detection (intake-836), but the repaired synthetic smoke no longer supports a blanket failure claim. **[RETARGETED 2026-09-01 → GLM-5.3-Flash; blocked on INF-69 T0-T2.]** Subject is now GLM-5.3-Flash. NOTE the old IQ2-quant hypothesis (intake-836) is VOID — that was a property of GLM-5.2 UD-IQ2_M; GLM-5.3-Flash is UD-Q4_K_XL, so any why-diagnosis weakness must be re-attributed from scratch. **[RETARGETED 2026-09-22 → DeepSeek-V4.1-Flash; blocked on the port/load/sparse-attention gates of `deepseek-v41-flash-evaluation.md`.]** GLM-5.3 was deleted unrun. The V4.1 artifact has Q4_K routed experts, Q8 attention/shared/output and FP8 Engram tables, so the IQ2 caveat still does not apply. A new quantization hypothesis would have to name a V4.1 tensor group.
- [x] **GC-shadow — Near-miss corpus shadow observation**: direct GLM corpus runner (`scripts/benchmark/glm52_reviewer_corpus_direct_runner.py`) executed a balanced `nearmiss-v1` code slice (`n=12`, `6 accept / 6 reject`) through CPU-only experimental-v7 GLM with chat, JSON-schema, reasoning off, and the recovered `p12000_tk16384` band. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-nearmiss-code-n12-20260718Tcheckpoint/summary.json`; calibration report: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-nearmiss-code-n12-20260718Tcheckpoint/reviewer_calibration_report.md`; raw prompt/server-log archive: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-nearmiss-code-n12-20260718Tcheckpoint/raw_prompt_and_server_log_artifacts.tar.gz`. Result: parse `0.0%`, FA `16.7%`, FR `66.7%`, accept `25.0%`, aggregate prompt `26.37 t/s`, decode `2.56 t/s`. Observation-only; this blocks role confidence rather than closing GC-1a/2a/3a. ✅ 2026-07-18
- [x] **GC-shadow-replay — Near-miss same-row replay negative control**: explicit `--gold-confidence multi_oracle` rerun at `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-nearmiss-code-n12-calibrated-20260718T034916Z/` selected the same 12 row ids because the runner already defaults to `multi_oracle`, then reproduced the same quality result: parse `0.0%`, FA `16.7%`, FR `66.7%`, accept `25.0%`, ECE/AUC/Brier `0.392/0.414/0.402`; aggregate prompt/decode `26.73/2.59 t/s`. Prompt text is archived in `raw_prompt_artifacts.tar.gz`; no server log was produced because the run used `--no-trace-logs`. Conclusion: this was a clean operational replay but not calibration; unchanged `multi_oracle` reruns are retired as non-progress. ✅ 2026-07-18
- [x] **GC-shadow-repair1 — Binary action-space/prompt repair attempt**: direct corpus runner now uses a local binary `approve|reject` JSON schema instead of the shared 7-way ReviewDecision enum, plus a task-grounded prompt that rejects only concrete task failures. The n=24 balanced run at `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-nearmiss-code-n24-binaryschema-20260718Tcontinuation/` was parse-clean and fixed the invented-action surface, but failed reviewer quality: FA `50.0%`, FR `75.0%`, accept `37.5%`, ECE/AUC/Brier `0.592/0.663/0.567`, aggregate prompt/decode `22.39/2.10 t/s`. Conclusion: mechanical schema repair is necessary but insufficient; GLM is still not role-ready. ✅ 2026-07-18
- [x] **GC-shadow-repair2 — Near-miss corpus representation repair**: the binary-schema n=24 failure was audited locally and by sidecar; the `FR 75.0%` was dominated by `reference_gold_answer` accept controls whose visible candidate was only a 100-character code prefix, while false accepts were mostly long-diff patch-review rows. The direct corpus runner now records source benchmark/suite/scoring-method representation summaries, supports explicit `--source-suite`, `--source-benchmark`, and `--provenance-scoring-method` filters, and refuses mixed selected representations unless `--allow-mixed-representation` is explicit. A homogeneous `seeded-mutation` / `cruxeval` / `exact_match` n=24 run at `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-nearmiss-code-n24-cruxeval-exactmatch-20260718Tglmrepair2/` completed parse-clean with FA `0.0%`, FR `16.7%`, accept `41.7%`, ECE/AUC/Brier `0.073/0.659/0.080`, aggregate prompt/decode `19.29/2.78 t/s`, elapsed `322.073s`. This is exact-answer review evidence only, not patch-review admission. ✅ 2026-07-18
- [x] **GC-shadow-repair3 — Patch-diff reviewer calibration**: the existing `nearmiss-v1` staging/assembly path already contains C-CRAB merged-patch accept controls, but they are `gold_confidence=observation`, so the default `multi_oracle` filter excluded them. A matched observation-grade `c-crab/python` patch-diff n=24 run using `--gold-confidence multi_oracle,observation --source-benchmark c-crab --source-suite python` completed at `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-nearmiss-code-n24-ccrab-patchdiff-20260718Tglmrepair3/`: parse `0.0%`, FA `91.7%`, FR `16.7%`, accept `87.5%`, ECE/AUC/Brier `0.398/0.388/0.426`, aggregate prompt/decode `21.32/2.26 t/s`, elapsed `2719.599s`. Conclusion: GLM is too permissive on patch diffs under the current task-grounded prompt. ✅ 2026-07-18
- [x] **GC-shadow-repair4a — Patch-review negative-evidence prompt/rubric repair smoke**: direct corpus runner now switches C-CRAB/merged-patch rows to a strict patch-diff prompt, requires `evidence.basis`/`evidence.risk` in the JSON schema, raises the default output budget to close the JSON reliably, and preserves full patch fields when the context budget allows. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-ccrab-patchdiff-negative-evidence-v3c-n4-20260718Tcodex/summary.json` and `decisions.jsonl`. Result: parse `0.0%`, FA `0.0%`, FR `50.0%`, accept `25.0%`; the persistent false reject is a C-CRAB `observation` merged-patch accept that lacks any cleanup/remove path despite the task requiring failed-write cleanup, so treat it as a label-audit blocker, not proof that the prompt repair failed. The follow-up `seeded-mutation/debugbench/substring` n=12 proved those rows are answer fragments, not full candidates; the runner now refuses `substring`/`exact_match` answer-fragment rows unless `--allow-answer-fragment-review` is explicit. ✅ 2026-07-18
- [x] **GC-shadow-repair4b — Full-candidate patch-review accept-control gate executed and failed admission ✅ 2026-07-19**: deterministic c-CRAB accept controls plus the hard-negative companion produced a decision-grade matched P-REV-1 run, but GLM still both false-rejects good patches and false-accepts bad patches. Do not rerun this same C-CRAB policy unchanged.
  - [x] **GC-shadow-repair4b.1 — Targeted old-FA n=12 confirmation ✅ 2026-07-18**: explicit row file `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_rowid_n12_confirm_20260718.txt` plus six curated oracle notes at `/mnt/raid0/llm/epyc-inference-research/docs/data/glm52_ccrab_oracle_notes_n12_confirm_20260718.json`; live CPU-only run `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/glm52-ccrab-patch-review-rowid-v5-notes-n12-20260718Tcodex/summary.json`. Result: parse `0.0%`, FA `0.0%`, FR `16.7%`, approve/reject `5/7`, ECE/AUC/Brier `0.180/1.000/0.059`, elapsed `2259.893s`; all six old false-accepted hard negatives now reject, but `nearmiss-v1:c-crab:1a06ca93c57f49ac` false-rejected as a CVAT observation clean control.
  - [x] **GC-shadow-repair4b.2a — Deterministic accept-control audit/filter ✅ 2026-07-18**: inference-research `scripts/benchmark/glm52_ccrab_accept_control_filter.py` now regenerates the C-CRAB/Python accept-control slice and wrote `docs/data/glm52_ccrab_accept_control_n24_filter_20260718.json` plus `docs/data/glm52_ccrab_accept_control_n24_row_ids_20260718.txt`. Result: `matching_pool_n=151`, `hard_accept_control_pool_n=0`, `selected_n=24`, `observation_only_n=24`, `decision_grade=false`; the old CVAT false-reject remains invalid as a hard model error, and the generated row list corrected one manual-row mismatch.
  - [x] **GC-shadow-repair4b.2a-input — Full-candidate signoff packet prepared ✅ 2026-07-18**: the filter now emits `docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json`, a 24-row task+candidate audit packet with explicit `unreviewed` signoff placeholders and decision-grade=false guardrails. This prepares GC-shadow-repair4b.2b without spending another GLM run on observation-only controls; it does not close the hard accept-control gate.
  - [x] **GC-shadow-repair4b.2b-prep — Machine-review recommendation packet ✅ 2026-07-18**: inference-research wrote `docs/data/glm52_ccrab_accept_control_machine_recommendations_20260718.json` and `.md` without modifying authoritative `signoff` fields or writing official `*_signoff_*.json` outputs. Machine review recommends `24/24` hard-accept candidates, flags five redacted long-digit rows plus one submodule-update format concern for manual review, and confirms helper report mode remains decision-grade false (`unreviewed_n=24`). This accelerates operator/oracle review but does not close GC-shadow-repair4b.2b.
  - [x] **GC-shadow-repair4b.2b-status — Signoff helper status artifact ✅ 2026-07-19**: `scripts/benchmark/glm52_ccrab_accept_control_signoff.py` ran against `docs/data/glm52_ccrab_accept_control_n24_audit_packet_20260718.json` with `--allow-unreviewed` and wrote `docs/data/glm52_ccrab_accept_control_signoff_status_20260719.json` plus empty row-id/oracle-note outputs. Result: `selected_n=24`, `hard_accept_n=0`, `unreviewed_n=24`, `decision_grade=false`. This confirms the blocker is still authoritative signoff, not more helper execution.
  - [x] **GC-shadow-repair4b.2b-hardneg — Hard-negative companion + dry-run plan-shape prep ✅ 2026-07-19**: inference-research `scripts/benchmark/glm52_ccrab_hard_negative_filter.py` selected `24/24` deterministic `c-crab/python` `multi_oracle` reject-side full-candidate controls from a `318`-row filtered pool and wrote `docs/data/glm52_ccrab_hard_negative_n24_filter_20260719.json`, `.md`, and row ids. A no-inference dry-run using the observation-only accept row ids plus these hard negatives wrote `data/glm52_reviewer_corpus_direct/glm52-gc4b-acceptobs-plus-hardneg-dryrun-20260719Tcodex/plan.json` and the tracked summary `docs/data/glm52_ccrab_accept_observation_plus_hard_negative_n48_dryrun_plan_20260719.md`: `execution_allowed=true`, `accept=24`, `reject=24`, `full_candidate=48`, homogeneous `c-crab|python|no_scoring_method`. This proves the runner/row-shape is ready; it is not live-run permission because the accept side is still observation-only.
  - [x] **GC-shadow-repair4b.2c — Deterministic accept-oracle relabel ✅ 2026-07-19 (NO inference)**: `epyc-orchestrator` commit `a60495ee` now promotes c-CRAB accept controls with stage3/stage4 verified tests to `executable_oracle` pass plus `gold_confidence="multi_oracle"`, while preserving `gold_source="merged_pr_accepted"`. The rebuilt `/mnt/raid0/llm/datasets/nearmiss-corpus-v1` has `rows.jsonl` content SHA-256 `0391166cf53225a1c54d95cc48c9672121cb5feb009039a32221dc35d0fd22c3` and build-config hash `636cdafa514bee3870441eefa531438726ae841cb9367490348ee3c7ffc2d008`. `epyc-inference-research` commit `e203fb3` produced `docs/data/glm52_ccrab_accept_control_n24_filter_20260719.json` with `decision_grade=true`, `hard_accept_control_n=24`, `observation_only_n=0`, and `hard_accept_control_pool_n=121`. Focused tests passed (`6` filter tests; `54` preflight/reload tests). The separate live matched GLM n≥24/P-REV-1 confirmation remains open.
  - [x] **GC-shadow-repair4b.2b-next-action audit ✅ 2026-07-19**: read-only checkpoint audit correctly identified hard-accept signoff as the then-current blocker. It is superseded by GC-shadow-repair4b.2c/2d: the operator-approved c-CRAB fail-then-pass oracle relabel made the accept controls decision-grade, and the matched live P-REV-1 run executed and failed admission.
  - [x] **GC-shadow-repair4b.2b-rowid-guard ✅ 2026-07-19**: inference-research `scripts/benchmark/glm52_ccrab_accept_control_signoff.py` now accepts `--expected-row-ids` and makes `decision_grade=true` depend on the signed hard-accept row ids exactly matching `docs/data/glm52_ccrab_accept_control_n24_row_ids_20260718.txt`. The runbook now uses that flag, so a reordered/drifted/replacement signed packet cannot silently satisfy the hard accept-control gate. This is no-inference guardrail prep; it does not sign any rows.
  - [x] **GC-shadow-repair4b.2b-review-sheet ✅ 2026-07-19**: inference-research `scripts/benchmark/glm52_ccrab_accept_control_review_sheet.py` now emits a blank CSV worksheet from the audit packet plus advisory machine recommendations and applies only explicit reviewer CSV decisions back into a signed packet. The helper refuses duplicate/missing/extra/reordered row ids and requires reviewer identity, timestamp, and notes for every reviewed row; it does not infer decisions from machine recommendations. Generated worksheet: `docs/data/glm52_ccrab_accept_control_n24_review_sheet_20260719.csv`; status: `docs/data/glm52_ccrab_accept_control_n24_review_sheet_status_20260719.json`.
  - [x] **GC-shadow-repair4b.2b-review-packet ✅ 2026-07-19**: inference-research extended the review-sheet helper with a bounded Markdown packet for operator/oracle review. Generated packet `docs/data/glm52_ccrab_accept_control_n24_review_packet_20260719.md` mirrors the 24-row packet order, surfaces the six format-concern rows, and includes bounded task/candidate excerpts. It is a review aid only; all `decision` fields remain blank and `decision_grade=false`.
  - [x] **GC-shadow-repair4b.2b-signoff-grade-guard ✅ 2026-07-19**: inference-research commit `f893a269` hardened `scripts/benchmark/glm52_ccrab_accept_control_signoff.py` so `decision_grade=true` now requires exact expected row-id coverage, zero unreviewed rows, and zero `reject_or_ambiguous` rows. Focused GLM signoff tests passed (`17`). This prevents a fully reviewed packet with any rejected/ambiguous accept-control row from satisfying the hard accept-control gate.
  - [x] **GC-shadow-repair4b.2b-runner-handshake-guard ✅ 2026-07-19**: inference-research now requires non-empty reviewed-row notes, refuses silent current-time timestamp fill-in from review CSVs, lets `glm52_reviewer_corpus_direct_runner.py` consume the structured `oracle_notes` JSON emitted by the signoff helper, and adds a fail-closed `--measurement-protocol p_rev1` path that requires explicit protocol attestation plus a decision-grade accept-control signoff report before any non-observation run. Focused no-inference GLM tests passed (`47`).
  - [x] **GC-shadow-repair4b.2d — C-CRAB decision-grade P-REV-1 live confirmation ✅ 2026-07-19**: inference-research commit `0fd043f` let the runner consume the deterministic `glm52_ccrab_accept_control_filter.v1` report as a hard accept-control source, then a CPU-only experimental-v7 run completed `n=48` (`24` accept / `24` reject), `observation_only=false`, `measurement_protocol=p_rev1`, attestation `MEASUREMENT-P-REV1-OPERATOR-APPROVED-20260719`. Evidence: `/mnt/raid0/llm/epyc-inference-research/data/glm52_reviewer_corpus_direct/gc-shadow-repair4b-p-rev1-20260719T132459Z/`; calibration report: `reviewer_calibration_report.md`. Result: `FA 41.7%` (`10/24`), `FR 25.0%` (`6/24`), accept `58.3%`, parse `0.0%`, ECE/AUC/Brier `0.239/0.509/0.278`, elapsed `6443.405s`, prompt/decode tail `20.49/2.36 t/s` with summary decode `2.57 t/s`. Cleanup verified no `llama-server`, no AutoPilot, and no KFD PIDs. Versioned evidence preserves decisions, responses, summary, progress, manifest, and calibration; raw request JSON remains local because the PII hook flagged long digit runs in benchmark prompts. Verdict: GLM-5.2 is **not** patch-reviewer role-ready.
- [x] **GC-external-1 — External ground-truth reviewer adapter / live gate ✅ 2026-07-19**: implement the 2026-07-19 directive path for exact-match judge benchmarks (`JudgeBench`, `RewardBench`, `RewardBench-2`, `LLMBar`, `JudgeLM`) plus a separate SWE-bench-Verified oracle path. Pairwise adapter/scoring/live path is complete, JudgeBench-GPT live evidence is positive, and SWE-bench-Verified accept controls are live-scored positive. Verdict: external evidence improves the GLM picture but does not override the failed decision-grade C-CRAB hard-negative gate.
  - [x] **GC-external-1a — Pairwise external adapter + n=24 dry plans ✅ 2026-07-19**: inference-research commit `3714575` added `scripts/benchmark/glm52_external_ground_truth_adapter.py` plus no-inference tests. It normalizes `JudgeBench`, `LLMBar`, `JudgeLM`, `RewardBench`, and `RewardBench-2` to pairwise `A|B` exact-match rows, pins source file SHA-256s, skips malformed JudgeLM/tie rows, and enforces deterministic selection/prompt-budget checks. Focused tests passed (`uv run --with pytest pytest -q scripts/benchmark/test_glm52_external_ground_truth_adapter.py` → `9 passed`). Materialized plans/rows: `docs/data/glm52_external_judgebench_gpt_n24_*_20260719.*` (`12/12` A/B), `glm52_external_llmbar_natural_n24_*` (`12/12`), `glm52_external_judgelm_val5k_n24_*` (`12/12`), `glm52_external_rewardbench_filtered_n24_*` (`24` chosen-over-rejected), and `glm52_external_rewardbench2_test_n24_*` (`24`, ties excluded). No inference, no Docker, no servers.
  - [x] **GC-external-1b — SWE-bench-Verified oracle adapter ✅ 2026-07-19**: inference-research commit `ae3d75e5` added `scripts/benchmark/glm52_swebench_verified_adapter.py` plus tests. It normalizes SWE-bench-Verified Parquet rows into `patch_review_oracle` rows with `repo`, `instance_id`, `problem_statement`, `patch`, `base_commit`, `FAIL_TO_PASS`, `PASS_TO_PASS`, `gold_label=accept`, `gold_confidence=test_oracle`, and source SHA-256. Real no-inference dry-run selected `24` rows from `500`, with `30` fail-to-pass tests and `1449` pass-to-pass tests; execution flags explicitly keep Docker/inference/server/model-load disabled. Artifacts: `docs/data/glm52_external_swebench_verified_n24_plan_20260719.json` and rows JSONL.
  - [x] **GC-external-1c — External direct-runner scaffold + live path ✅ 2026-07-19**: inference-research commits `ae3d75e5`, `5280fa30`, and the 2026-07-19 follow-up added `scripts/benchmark/glm52_external_ground_truth_direct_runner.py` plus tests. It consumes normalized pairwise rows and homogeneous SWE `patch_review_oracle` rows, builds prompt-budgeted dry-run plans, scores saved response JSONL into `decisions.jsonl`, `summary.json`, and `run_manifest.json`, and has an explicit `--execute` path that launches GLM with the validated prompt-band/top-k schedule. Dry-run remains default; live execution requires `--execute`. Focused adapter/runner tests passed together (`24 passed`), and dry-runs against real GLM model/binary paths validated `execution_allowed=true`.
  - [x] **GC-external-1d — Live external GLM gate ✅ 2026-07-19**: ran the prepared JudgeBench-GPT pairwise and SWE-bench-Verified accept-control rows under the validated `<=12K` top-k schedule and emitted live `decisions.jsonl`, `summary.json`, `run_manifest.json`, prompt/response artifacts, and exact-match scoring. Quiet-window inference complete; cleanup verified.
    - [x] **GC-external-1d.1 — JudgeBench-GPT pairwise live gate ✅ 2026-07-19**: live run `/mnt/raid0/llm/epyc-inference-research/data/glm52_external_ground_truth_direct/glm52-external-judgebench-gpt-n24-p-rev1-20260719T154517Z/`, `n=24`, `observation_only=false`, `measurement_protocol=p_rev1`, attestation `MEASUREMENT-P-REV1-OPERATOR-APPROVED-20260719`, era `p_rev1_attested`. Original strict scorer: `15/24` (`62.5%`) with `7/24` parse failures from 0-100 confidence values. Exact-choice rescore: `22/24` (`91.7%`), parse `0/24`, warning `confidence_scale_0_100=7`. Scorer/prompt fix validated (`13` focused tests plus py_compile).
    - [x] **GC-external-1d.2 — SWE-bench-Verified direct oracle execution ✅ 2026-07-19**: live direct path completed for `patch_review_oracle` rows so the external patch-review claim is not inferred from pairwise judge preference. Result: `22/24`, `FR 8.3%`, parse `0/24`, no hard negatives in slice.
      - [x] **GC-external-1d.2a — SWE direct-runner support + P-REV-1 dry-run ready ✅ 2026-07-19**: inference-research now dispatches SWE rows to the ReviewDecision schema/parser, refuses mixed row kinds, records accept-control false-reject rate, and regenerated the JudgeBench score-only artifact with `server.not_started=true`. SWE dry-run plan `glm52-external-swebench-verified-n24-p-rev1-dryrun-20260719` is `execution_allowed=true`, `refusal_reasons=[]`, `24` accept controls, response schema `approve|reject`, and first prompt `571/15744` estimated tokens.
      - [x] **GC-external-1d.2b — SWE P-REV-1 live accept-control gate ✅ 2026-07-19**: live run `glm52-external-swebench-verified-n24-p-rev1-20260719Tlive`, `observation_only=false`, `measurement_protocol=p_rev1`, attestation `MEASUREMENT-P-REV1-OPERATOR-APPROVED-20260719`, era `p_rev1_attested`. Result: `22/24` correct approvals, `false_rejects=2`, `FR 8.3%`, parse `0/24`, approve `22`, reject `2`, elapsed `1965.612s`; no GLM/server/AutoPilot/KFD processes remained after cleanup.
- [x] **GC-external-1e — Reviewer repair-or-route verdict ✅ 2026-07-19**: synthesized failed C-CRAB hard-negative evidence, positive JudgeBench pairwise evidence, positive SWE accept-only evidence, and RM-2 alternatives. Verdict: GLM is not admitted as production patch reviewer; scope it to research/judge-preference/accept-control diagnostics unless a concrete new repair hypothesis exists. Route production reviewer selection to RM-3 screening, Ref external judge-of-judge, or a named repair hypothesis instead of rerunning unchanged GLM C-CRAB/SWE policies; A0/A1/A3 and RM-2.fast are closed negative/partial evidence.
- [x] **GC-4 — RAM-residency policy decision** (operator, OP bundle): 239GB reviewer + ~70GB architect + frontdoor/workers co-residency vs swap-in-on-demand vs review-windows. Determines whether A4 is an interactive reviewer or a batch/offline judicial gate. Operator decision remains open. **VOID 2026-09-01** — the 239 GB figure was GLM-5.2 UD-IQ2_M, now deleted. GLM-5.3-Flash (UD-Q4_K_XL) has a different footprint entirely; if a residency question arises it is a NEW decision sized against the real artifact, not this one. ✅ 2026-09-01
- [ ] **GC-4b — Residency sizing input for DeepSeek-V4.1-Flash** (new 2026-09-22; any GLM-5.3 footprint is VOID). Re-size against the real artifact. The file is ~483 GiB, and ~189 GiB of that is native FP8 Engram n-gram tables, which are disk-streamable. The always-resident working set is therefore ~294 GiB of Q4_K experts plus Q8 attention/shared/output, before KV. This row is only the sizing input. The residency policy stays an operator decision (§A00), and it only matters once the port loads and the Engram access pattern (resident vs mmap-streamed) has been measured. Blocked on `deepseek-v41-flash-evaluation.md`. (re-scoped 2026-11-03 from the ~483 GiB Sept Q4 DS41 file: deleted 2026-10-21; re-size on the 1017 MXFP4 artifact (468 GiB, ~276 GiB anon RAM))
  - [x] **GC-4.input — Memory-budget table prepared ✅ 2026-07-18**: decision memo at [`docs/reference/glm52-ram-residency-decision-input-2026-07-18.md`](../../docs/reference/glm52-ram-residency-decision-input-2026-07-18.md). Current sizing says always-resident GLM is physically feasible on the 1.1TiB host, but review-window/batch use is the better policy input until GC-shadow-repair4b.2b and P-REV-1 clear. Treat "swap-in-on-demand" as cold mmap/page-cache faulting, not real swap service, because swap is only 8Gi.
- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-glm52-reviewer-capability-gates on 2026-11-03 (BRF-T1-MEQ, operator D2): **GC-6**.*
- [x] **GC-5 — Registry reviewer-capability fields ✅ 2026-07-19**: structured `measured:` entries now record GLM C-CRAB P-REV-1 FA/FR, native-MTP repair, external JudgeBench-GPT and SWE-bench-Verified P-REV-1 rows, plus GC-1r typed-emission, GC-2r rubric-authoring, and GC-3r why-diagnosis smoke metrics in the research model registry. These fields remain role-disposition metadata, not production reviewer admission.

#### Dependency chain (track-local, BRF-T7-F15)

```text
glm51-reap GO gates (download/integrity ✅ → glm-dsa load smoke ✅ → current-source cache/runtime smoke ✅ → true >64K stale-binary runnability ✅ → runtime DSA-DENSE-MASK ✅ → top-k-cap diagnosis ✅ → schedule ✅ (`3072` fails at 2.1K/3K, `8192`/`12288` fail at 12K, next-power-of-two caps pass tested bands))
        → GC-0d protocol-channel matrix ✅ (chat/free+schema reviewer-serving channel; raw endpoints unvalidated)
        → GC-1/2/3 smoke probes ✅ (mixed; not role admission)
        → GC-1r/2r/3r repair smokes ✅ (small synthetic observations pass; not role admission)
        → GC-shadow near-miss corpus observation ✅ (parse-clean but FR-heavy; not role admission)
        → GC-shadow-replay ✅ (same rows/results; unchanged rerun retired)
        → GC-shadow-repair1 ✅ (binary action-space fixed; quality still failed)
        → GC-shadow-repair2 ✅ (runner/corpus representation guard + exact-match observation)
        → GC-shadow-repair3 ✅ (matched C-CRAB patch-diff failed by over-approval)
        → GC-shadow-repair4a ✅ (negative-evidence prompt + answer-fragment guard)
        → GC-shadow-repair4b.1 ✅ (targeted old-FA n=12; FR remains on one observation accept)
        → GC-shadow-repair4b.2a ✅ (deterministic filter; zero hard accepts)
        → GC-shadow-repair4b.2c ✅ (deterministic hard accepts)
        → GC-shadow-repair4b.2d ✅/FAILED (decision-grade C-CRAB P-REV-1 FA 41.7%, FR 25.0%)
        → GC-external-1a ✅ (pairwise external plans) → GC-external-1b ✅ / 1c ✅ → GC-external-1d.1 JudgeBench-GPT ✅ (22/24 exact-choice) → GC-external-1d.2 SWE-bench direct oracle ✅ (22/24 accept controls, FR 8.3%) → GC-external-1e repair-or-route verdict ✅ → RM-2.fast/RM-2.next closed no-clean-replacement ✅ → RM-3 / Ref / repair → GC-5
GC-4 operator decision (anytime after CPU bench exists) → shapes H5 A4 arm design
2026-09-22 retarget: deepseek-v41-flash-evaluation.md port → load/coherence → sparse-attention disposition + cap sweep → GC-1/2/3 smokes on V4.1 → GC-1a/2a/3a (P-REV-1) ; GC-4b sizing input → operator residency decision
Kernel P0s: grammar fix is closed; GLM-dsa cache/runtime reconciliation is closed by `3dee86a5a`; remaining kernel dependencies are sparse-final-attention classification and any live v7 CPU/perf guard relevant to GC-1 cost.
```

#### Open Questions

- [x] Do small GLM-5.2 reviewer-capability repair smokes recover after prompt/scorer fixes under the next-power-of-two top-k schedule? **Yes for synthetic observations only**: GC-1r free typed emission `3/3`, GC-2r rubric breadth `mean_composite=1.0`, and GC-3r synthetic why diagnosis `why_match_rate=1.0`. This does not close P-REV-1 or corpus-v1 reviewer admission. ✅ 2026-07-18
- [x] Does the repaired GLM reviewer look usable on a real near-miss/C-CRAB patch-review slice? **No for patch-review role admission**: unfiltered/mixed near-miss slices are invalid for GLM admission because they mix answer, code-prefix, and patch-review representations; `substring`/`exact_match` answer-fragment rows are now refused by default. The n=24 homogeneous `cruxeval/exact_match` slice is encouraging only when deliberately scoped as exact-answer judging (`FA=0.0%`, `FR=16.7%`). Matched C-CRAB patch-diff review first failed by severe false accepts (`FA=91.7%`); the negative-evidence/oracle-note repair fixed the targeted hard-negative FA shape on n=12 (`FA=0.0%`) but the decision-grade P-REV-1 confirmation still failed at `FA 41.7%`, `FR 25.0%`, parse `0.0%`. Next work is the external ground-truth adapter and/or a new repair hypothesis, not another unchanged C-CRAB rerun. ✅ 2026-07-19
- [x] Does external ground-truth evidence rescue GLM's reviewer role? **No for production patch review; partial positive for narrower judge/accept-control use**: JudgeBench-GPT pairwise exact choice is positive (`22/24`, `91.7%`, parse `0/24` after confidence-scale warning normalization), and SWE-bench-Verified accept controls are positive (`22/24`, `FR 8.3%`, parse `0/24`). But C-CRAB patch-review still failed hard-negative/overall calibration (`FA 41.7%`, `FR 25.0%`, `AUC 0.509`), and the SWE slice has no hard negatives. GC-external-1e routes production reviewer selection away from GLM unless a concrete new repair hypothesis appears. ✅ 2026-07-19

#### Cross-Cutting Concerns

1. **Ownership** — anything requiring model downloads, host benches, or the MI210 belongs to the parallel session's handoffs; this file consumes their checkpoints, never re-runs them.
2. **Cross-family thesis** — GLM-judges-Qwen is the anti-collusion arm; its benefit is measured (H5 covariate), not assumed.

#### Key Files / Surfaces

- `orchestration/model_registry.yaml` `glm_52_ud_iq2m` entry (research registry line ~5591) — historical; a DeepSeek-V4.1-Flash entry is owned by `deepseek-v41-flash-evaluation.md`
- The `glm52_*` direct runners below are GLM-named but reusable. Before any V4.1 run, the launch path must replace the GLM `indexer_top_k` schedule with V4.1's own validated sparse-attention settings.
- `scripts/benchmark/glm52_reviewer_capability_direct_runner.py` (research direct runner for GC-1/2/3 while GLM stays out of the production orchestration registry)
- `scripts/benchmark/glm52_reviewer_corpus_direct_runner.py` (research direct runner for `nearmiss-v1` shadow/claim-grade corpus ledgers while GLM stays out of the production orchestration registry)
- H2 `review_decision.schema.json` + GBNF generation; H4 corpus sample
- `glm51-reap-cpu-evaluation.md` GO checkpoints (consume)

#### Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; GC-1/2/3 numbers recorded here + registry (GC-5); GC-4 goes to the operator decision queue (§A00) — do not decide autonomously. Near-miss corpus runs must preserve `decisions.jsonl` plus `reviewer_calibration_report.md` and must label all pre-P-REV-1 FA/FR/ECE/AUC values as observation-grade. P-REV-1 runs must include `run_manifest.json`, explicit attestation, the decision-grade calibration report, cleanup evidence, and enough raw request/response artifacts to audit parser/scorer behavior. If raw prompt text files or server logs are generated, preserve them as a compressed archive or document why they are local scratch; expanded `*.prompt.txt` / `logs/` copies need not be versioned when the archive and request JSON are present. Same-row or same-policy replays must be labeled as negative controls, not calibration. Any GLM reviewer run without progress telemetry and a completion-token floor is a harness/process observation only. Any run above the current recovery band must also record prompt-token count, chosen `indexer_top_k`, and serving channel so the schedule map remains comparable.

#### Evidence Base (intake)

intake-836 quant why-diagnosis caveat · intake-834 authoring-capability dominance · intake-837/838 format/bias fragility of judges · audit doc 2026-07-16 (GLM-dsa arch exists in-tree; reconciliation smoke later passed on experimental-v7 `3dee86a5a`; sparse final-attention and reviewer quality remain open).

2026-09-07 reference rows (NOT targets, NOT residency inputs — GC-4 is VOID and the UD-IQ2_M artifact is deleted). (1) Closest published analogue to a 753B-A40B-class reviewer: 433 GB NVFP4 at 14.9 tok/s on one RTX PRO 6000 vs llama.cpp 7.3. Non-transferable on four axes: quant (NVFP4 vs UD-IQ2_M with 2.0625 bpw routed experts), GPU class (96 GB Blackwell vs 64 GB gfx90a), 178 vs 61.8 GB/s host expert bandwidth, one workload. intake-1318#record. (2) Shared-expert corroboration for GLM routing locality is a SECOND but WEAK leg — shared experts are sufficient-not-necessary for poor local consistency and GLM's shared fraction sits far below any measured model. Do NOT present it as independent confirmation of "no cacheable hot set". intake-1328#03.

#### Deep-Dive Correction — 2026-07-21 (The selective-precision hypothesis is FALSIFIED in our own GGUF)

Two independently-indexed practitioners (intake-870 vLLM-Moet, intake-871 GLM-5.2-NVFP4-TR3) converged on holding attention + shared experts + the DSA indexer + early-layer MLPs above 4-bit while pushing routed experts low. The intake proposed testing whether our Unsloth UD-IQ2_M omits that carve-out. **It does not — Unsloth already implements all four, more aggressively than either practitioner described.** Per-tensor map parsed from the six GGUF shard headers (header bytes only; no weights read, no inference):

| Tensor group | Quant |
|---|---|
| `attn_k_b`, `attn_kv_a_mqa`, `attn_q_b`, `attn_v_b` (KV-compression path) | **Q8_0** |
| `attn_output`, `attn_q_a` | Q5_K / Q6_K |
| `indexer.attn_k`, `indexer.attn_q_b` | **Q8_0** |
| `indexer.proj`, `indexer.k_norm` | **F32** |
| `ffn_*_shexp` (shared experts) | Q5_K / Q6_K |
| `ffn_{gate,up,down}` layers 0-2 (`leading_dense_block_count=3`) | Q5_K / Q6_K |
| `ffn_gate_exps`, `ffn_up_exps` (routed) | IQ2_XXS ×148 |
| `ffn_down_exps` (routed) | IQ3_XXS ×71 |

**There is no gap to exploit — close the branch.** Two consequences worth recording:
- The DSA indexer is at Q8_0/F32 throughout. Our historical `indexer_top_k` corruption was therefore a **runtime parameter bug, not quantization damage**, and the tensor map rules quantization out as a repeat cause. (Header confirms `attention.indexer.top_k = 2048`, the known-safe value.)
- **intake-870's FP4 hot-expert delta tier has nothing to bite on.** Our own routing-skew artifact (19.1M selections, 75 layers, 256 experts) classifies GLM-5.2 as `near_uniform_global`: normalized entropy **0.9987**, Gini **0.0664**, top_8 share 4.1% vs uniform 3.1%. There are no hot experts. (That artifact is hypothesis-grade, but decisive enough not to build on.)

**Residual, and why I lean against it.** The genuine soft spot is that routed `ffn_gate/up_exps` sit at IQ2_XXS = **2.0625 bpw** — the weakest IQ2 member, below IQ2_S/IQ2_M despite the "UD-IQ2_M" label. Falsifiable form (**H-Q1**): re-run the identical decision-grade C-CRAB P-REV-1 slice on a higher-bpw GLM-5.2 (UD-IQ3_XXS / Q3_K_XL, ~300-340GB, fits in 1.1TB). Two pieces of our OWN evidence predict it falsifies: (1) **RM-2** — Qwen3.6-27B **dense Q8_0**, zero quantization damage, over-approved on the same slice (FA 54.2%, AUC 0.503); (2) **selectivity** — GLM passes JudgeBench-GPT 22/24 and SWE-bench-Verified accept controls 22/24 (FR 8.3%); 2-bit damage in routed experts degrades broadly, whereas this degrades only on C-CRAB hard negatives. That signature is task/prompt-policy, not precision.

- [x] ~~**NOT APPLICABLE (2026-09-22): the subject no longer exists.** GLM-5.2 UD-IQ2_M was deleted on 2026-09-01, and H-Q1 needs the matched GLM-5.2 higher-bpw requant. The row is left unticked because it was never run. It does not transfer to DeepSeek-V4.1-Flash, which has no IQ2 experts. Original text: Optional cheap closer (LOW priority, expected to falsify): run H-Q1 to formally eliminate the quantization branch. **Decision flip:** UD-IQ3_XXS moving C-CRAB FA below ~20% on the matched slice ⇒ quantization IS causal and selective requantization becomes a real project. FA staying >35% ⇒ quantization exonerated; the reviewer gate is a scaffold/policy problem.~~ (closed 2026-10-29 audit: OBSOLETE → handoff:304 self-marked NOT APPLICABLE 2026-09-22: GLM-5.2 UD-IQ2_M deleted 2026-09-01 (graveyard GLM-5.2-UD-IQ2_M); H-Q1 needs matched GLM-5.2 requant)
- [x] Selective-precision carve-out hypothesis (attention / DSA indexer / shared experts / layers 0-2) tested against the actual UD-IQ2_M tensor map — **FALSIFIED, Unsloth already implements it**. ✅ 2026-07-21

## Track: reviewer-escalation-and-human-gate-policy
<!-- gate: UFH-01 -->

> Folded from `handoffs/active/reviewer-escalation-and-human-gate-policy.md` @ `28b488861d1f` on 2026-11-03 (BRF-T7-F15, route 1b, operator D1/D5; retired row REV-05 → REV-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reviewer Control Plane — Escalation & Human-Gate Policy (H7, stub-grade)

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-integrity-20261006/`.

Retired ROOT publication custody: `/mnt/raid0/llm/tmp/codex-ni-root-legacy-retirement-20261030`; original heads, patches and exact dirty bytes remain preserved there.

**Status**: stub — deliberately LAST (M4 "governed"); policies derive from H4/H5 evidence that does not exist yet
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, safety
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Gates**: H4 calibration curves + H5 tournament + H-LB LB-6 budget gate; harness-side surfacing additionally gated on HS-4 ([`harness-selection-and-integration.md`](harness-program.md#track-harness-selection-and-integration))
**Repo**: `epyc-orchestrator`

#### Objective

Convert calibration evidence into policy: confidence thresholds from reliability curves, verifier-disagreement escalation, protected-action human gates. Human-in-the-loop is a policy boundary, not a crutch — sparse but deliberate.

#### Thesis (evidence-shaped)

**Default on disagreement = ESCALATE.** Our regime (strong judge, no information asymmetry, same inputs) is the debate literature's worst case: same-input homogeneous debate is a martingale (no expected-correctness gain); debate beats direct judging only under information asymmetry; one-sided consultancy actively DEGRADES judges — a persuasive-but-wrong architect could flip a correct reviewer (intake-840/841 + follow-ups). A rebuttal round exists only as an opt-in, evidence-gated pre-escalation step.

#### Prioritized Task List

- [ ] **HG-1 — Threshold policy** from H4/H5 reliability-by-confidence-bucket curves (per-domain).
- [ ] **HG-2 — Verifier-disagreement rule**: reviewer vs conclusive-gate conflict → escalate (fa/fr_candidate events already fire mechanically per H3 RD-3); inconclusive-gate conflicts stay with the reviewer.
- [ ] **HG-3 — Protected-action list** aligned with existing SafetyGate: deploy, baseline change, MEASUREMENT-adjacent edits, protected-branch merges, DB migrations.
  - [x] **Scoping audit ✅ 2026-07-29 (mainA) — the premise is wrong; corrected here so HG-3 is actionable when it unblocks.** Two defects found:
    **(1) There is no "existing SafetyGate" to align to.** `epyc-orchestrator/scripts/autopilot/safety_gate.py` is AutoPilot's *baseline/quality regression* gate (`REGRESSION_THRESHOLD`, tier baselines, Pareto-archive ratchet). It does no action typing at all. A repo-wide grep for `protected_action` / `PROTECTED_ACTIONS` returns **nothing** — no action-typed gate exists anywhere in the codebase.
    **(2) The real enumeration is path- and branch-scoped, not action-scoped.** It is `coordination/session-bus/human_only_paths.yaml` (itself human-amendment-only, hash-pinned, hook-enforced) plus `BUS_PROTOCOL.md` rule 6. Mapping HG-3's five named actions onto it: *baseline change* → `orchestration/autopilot_baseline.yaml` ✅; *MEASUREMENT-adjacent edits* → `MEASUREMENT.md` + `agents/shared/MEASUREMENT_POLICY.md` ✅; *protected-branch merges* → the `branches:` block, `production-consolidated-*` ✅; **deploy → nothing**; **DB migrations → nothing**. So two of the five have no enumeration behind them and HG-3 cannot "align" to a list that does not cover them.
    **Corrected scope for HG-3 when it runs**: either (a) extend `human_only_paths.yaml` to cover deploy and DB-migration surfaces — note that file is a trust boundary, so this is a token-request, not an agent edit; or (b) narrow HG-3 to the three actions that already have enforcement and say explicitly that deploy/DB-migration are out of scope. Do **not** write an action list that has no enforcement behind it — that produces a policy document asserting protection that nothing implements.
  - [x] **HG-3 is BLOCKED on HG-1, contrary to the dispatch queue.** ✅ 2026-08-12 — `mainD`. The Dependency Graph below reads `H4 curves + H5 winners → HG-1 → HG-2/HG-3`, and HG-1 is open. `BACKLOG-DISPATCH-QUEUE.md` TOP-40 #6 classifies this row as `none` lane with **no blocker**, which is wrong. Same defect class as the queue's runbook-template rows (auditor, `msg-20260729T160627Z`) and its already-closed rows: **a row that looks dispatchable but is not.** Queue classification should consult the owning handoff's dependency graph, not just the checkbox.
    **Both halves closed, and the general one retired INTO ENFORCEMENT rather than into silence** — ticking a rule-box is how a live rule gets lost (`mainC` found five of those the same night).
    **(a) The specific defect is fixed**: TOP-40 #6 now reads `⛔ BLOCKED 2026-07-29`, quoting this box as the reason. HG-1 is still `- [ ]`, so the blocker it names is live and current, not stale.
    **(b) The general rule is now CODE, not prose.** `backlog_row_check.py` gained a fourth screening signal — `dependency_prereqs()` + `blocking_dependency_graph()` — which parses a `## Dependency Graph` block, gives every id every upstream id on its line as a prerequisite, and refuses the row while a prerequisite's own box is open. That is the one block neither the row text nor `blocking_children()` can see, which is exactly why the queue served this row as ready.
    Narrow by construction, per the tool's standing caveat: it requires a real `## Dependency Graph` heading (an arrow in prose is not one), matches the box's id as a **prefix** so a row merely *mentioning* `HG-3` is not treated as being it, and an unresolvable prerequisite fails **toward dispatchable** — refusing real work is this tool's settled costlier error.
    Measured on the live corpus: **12 of 2,177 open boxes (0.55%)**, the same band as the tool's other signals, and every hit reads verbatim as gated — `HG-2/HG-3` on open `HG-1`, `E-3/E-4/E-5` on open `E-2`, `LB-3/LB-4/LB-6` on open `LB-1`, `RM-7/RM-8` on open `RM-4`. Six tests including a mutation test: closing the prerequisite silences the signal, proving it is keyed on prerequisite STATE and not on the graph alone. 71 passed.
    *(The first corpus measurement said `0 open boxes / 0.00%` — vacuous, because `_boxes()` strips the state so an open box is `""`, not `" "`. Recorded because a clean-looking 0.00% is the empty-input signature, and it was caught by asserting the input size rather than by reading the number.)*
- [ ] **HG-4 — Escalation-precision human-audit protocol**: sampling rate + operator cadence (operator decision, OP bundle — escalation precision is undefined without it).
- [ ] **HG-5 — Server-side surfacing**: `/v1` response fields + `x_*` override to force/suppress escalation (harness-agnostic cooperation pattern per `hermes-outer-shell.md` L55-69).
  MAIN accepted source-only child VB-HG5-FORCE-SOURCE-CONFORMANCE on2026-10-08: APP main76624a91 and original ROOT e54175dc run37721932296 attempt1 pass87/87 whole-module synthetic controls, preserving off/default/auto behavior and versioned goldens. Request cleanup removes only matching request-owned trace keys. Explicit force remains default off, ineligible/empty/error cases retain frontdoor fallback and actual consultant accounting. [Original source/custody findings](../../artifacts/ni08/hg5-force-source-20261008/README.md). Parent HG-5 remains open for runtime/H3 scope; prospective request-event writer/reader work is separate. No activation or efficacy claim.
- **[declined: ws58 2026-11-03 content-review: optional by its own text]** **HG-6 — OPTIONAL single two-sided rebuttal round** (pre-escalation): architect rebuts AND verifier/original position restates; reviewer re-judges the contrastive pair; hard cap 2 rounds; **restricted to latent-evidence disagreements** (something checkable to surface — never style/preference); enabled per task-class ONLY after an offline A/B shows **signed net-flip Δ>0** (wrong→right ≫ right→wrong; the right→wrong tail is the safety metric, tracked continuously). Never one-sided; never multi-round-to-convergence.
- **[declined: ws58 2026-11-03 content-review: a frozen pointer that states "do no work"]** **HG-7 — Harness-side UX**: FROZEN pointer until HS-4 resolves — state the gate, do no work.
- [ ] **HG-8 — Policy A/B** under P-AB-1 + P-REV-1; promotion per H-LB LB-6.
- [ ] **HG-9 — Detect/repair split topology (operator idea 2026-09-17)**: small models REVIEW (find bugs), and a
  larger model is consulted only to RECOMMEND FIXES for the findings. This is an escalation/consultation edge that
  AutoPilot should learn rather than a fixed pipeline. It is the Verifier→Worker handoff of
  `tri-role-coordinator-architecture.md` (TR-4.4 runs in parallel with the review pipeline) with the roles split by
  sub-task (detection vs repair) instead of by confidence.
  - Step 1 (no inference): write the topology as a routing/escalation option AutoPilot can mutate (detector role
    pool, fixer role, trigger = "finding emitted"). Check the reuse of the existing escalation path and the TR role
    axis before designing anything new.
  - [x] **HG-9 Step 1 source-backed topology contract** ✅ 2026-10-06 — MAIN accepted [the design option](../../docs/design/hg9-detect-repair-topology.md), with [immutable readset](../../artifacts/ni07/hg9-source-readset.md) and [review](../../artifacts/ni07/hg9-main-review.json). Existing roles/escalation, resolved objective evidence/current binding, deterministic incumbent fallback and nine future synthetic cases are mapped. Registry names do not prove small-model eligibility; no selector, route, model call or patch execution was activated. Step 2/3 gates remain open.
  - Step 2 (inference, after an EV-13b resume, see `eval-tower-verification.md`): measure detection F1 of the
    small-model pool on the Augment-v1 suite. This needs a judge-stable score first, because EV-6 failed at
    2.94pp on 2026-09-16.
  - Step 3: A/B the split against single-model review under P-AB-1 (fix acceptance plus cost), promoting per LB-6.
  - The source the operator read is not recorded yet; if it is a paper or post, run it through research intake
    before citing it.

#### Dependency Graph

```text
H4 curves + H5 winners → HG-1 → HG-2/HG-3 → HG-8
HG-4 operator cadence (OP bundle) → escalation-precision measurable
HG-5 server-side (anytime after H3) ; HG-6 gated on its own offline A/B ; HG-7 frozen on HS-4
HG-9 step 1 (anytime) → EV-13b resume → HG-9 step 2 → HG-9 step 3
```

#### Cross-Cutting Concerns

1. **Layer B boundary** — acting on escalations inside an agent loop needs the cooperating harness; server-side surfacing (HG-5) is the harness-agnostic interim.
2. **Cost** — a rebuttal round ≈ 2-3× a review call amortized by P(disagreement); cheaper than escalation only if accuracy-neutral-or-better — measure, don't assume.

#### Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; HG-4 cadence + HG-6 enablement are operator decisions (§A00); all policy claims cite P-REV-1 + LB-6.

#### Evidence Base (intake)

intake-840/841 debate regime analysis (martingale, consultancy degradation, plateau/cost) · intake-836 overcorrection tail · intake-846 HITL-as-policy-boundary · audit doc 2026-07-16.

#### MAIN-reviewed JEV refinement — 2026-10-06 (HG-9)

Strengthen Step 1 into a concrete detector-to-fixer contract: map the eligible detector pool, fixer target, evidence-anchored finding, emitted-finding trigger and current `EscalationPolicy` path. Identify the bounded rubric/role choices that can reuse `Question`/`DecisionResult`, while leaving free-text explanations and patch generation outside the closed-set decision. Reuse the existing host-owned prepared-action validation where a menu is selected; typed output never grants permission or establishes correctness.

The no-inference preparation includes explicit schema/mapping and mocked boundary cases for malformed, unresolved, empty or stale findings, a changed offered-role catalogue, an unavailable fixer and attributed incumbent fallback. Detection must finish before the fixer consumes its findings: dependent stages are not independent heads in one shared-state call. Keep detection and repair costs separately attributable with the existing call-accounting seam, preserving absent fields rather than inventing zeros.

This prepares an option for the existing AutoPilot mutation/evaluation path; it does not activate a selector, tune routing or alter the incumbent. Step 2 remains subject to EV-13b and judge-stable detection scoring, and Step 3 retains its paired fix-acceptance/cost comparison and promotion gates. Coordinate any later core changes with the existing escalation/typed-decision owners; add no parallel routing framework.

## Track: reviewer-latency-and-sampling-budget
<!-- gate: none -->

> Folded from `handoffs/active/reviewer-latency-and-sampling-budget.md` @ `28b488861d1f` on 2026-11-03 (BRF-T7-F15, route 1b, operator D1/D5; retired row REV-06 → REV-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reviewer Control Plane — Latency & Sampling Budget (H-LB)

> **Fold destination** (BRF-T1-F25, BRF-T1-1, route 1a, 2026-11-02): absorbs 2 handoff(s) as `## Track:` sections at the end of this file (`reviewer-calibration-accounting.md`, `reviewer-typed-artifacts.md`). The body above the first track is the former `reviewer-latency-and-sampling-budget.md`.

**Status**: active — cross-cutting; **blocks ALL enforce-mode** anywhere in the series
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-decision-plane.md`](../completed/reviewer-decision-plane.md) (RD-12 supplies the baseline), [`autopilot-control-plane-integration.md`](../completed/autopilot-control-plane-integration.md) (tunes these knobs)
**Repo**: `epyc-orchestrator`

#### Objective

Make review latency a governed, first-class budget. The 2026-07-16 regression is the motivating fact: plan-review/eval-routing overhead **halved** eval throughput (~68 backend requests + 11-17 architect plan-review prompts per 50-question replay; reroute bug fixed `bc8d3303` but the structural cost remains). Architect↔Reviewer handshakes multiply this; no enforcement until the budget gate passes.

#### Thesis

The literature quantifies the tax: multi-role pipelines ~2-3× cost / ~8-10× latency (intake-839 critique lit); multi-agent ~15× tokens with token usage explaining 80% of outcome variance; on a single host, parallel-reviewer latency models as **SUM not MAX** (intake-846). The counter-levers are structural (two-turn rubric, reminders-over-re-review, complexity gating, final-aggregate review, sticky cache — all in H3) plus governed budgets tuned by the autopilot. The standing floor: **the plane must beat a single augmented LLM on the same tasks** (M3 baseline floor) — a control plane that only adds cost gets deleted, per the Fable5 enforcement-not-theory posture.

#### Prioritized Task List

- [ ] **LB-1 — Reproduce + attribute the regression**: which calls dominate (plan-review prompt count vs prompt length vs architect queueing) on the RD-12 replay baseline.
- [x] **LB-2 — Budget targets** ✅ 2026-07-17 (targets DEFINED below — see "LB-2 Budget targets (proposed)"; all numbers **PROPOSED/observation-grade**, pending LB-4 paired A/B confirmation + operator ratification): per-decision tokens + latency_ms; per-session review caps (reuse `IterationContext.max_iterations`/`max_total_iterations`); token-multiplier as a governed knob (target multiplier vs single-model baseline).
- [ ] **LB-3 — Sampling policies** — ⏳ PARTIAL 2026-07-17: complexity-gated review (TaskComplexity threshold knob) + reminder-substitution call-site + per-session caps LANDED (orchestrator `30d3232b`); still open: k% sampling, quick_mode tier wiring, fan-out effort-scaling rules.: review only COMPLEX/escalated tasks (reuse `TaskComplexity`); k% sampling; quick_mode tiering (QUICK_REVIEW_PROMPT exists); reminder-instead-of-review substitution rate; fan-out gated by task type + effort-scaling rules (1 agent/3-10 calls simple … 2-4 agents comparisons).
- [ ] **LB-4 — Paired throughput A/B per policy** under P-AB-1 + P-SPEED-OBJ (task-rate axis, e-process — never single-trial); parallel-reviewer wall-clock modeled as SUM on-host (exception: NUMA-split or MI210-offloaded reviewer).
- [x] **LB-5 — Budget-enforcement knobs** ✅ 2026-07-17 (knobs + LB-2 budgets declared in `orchestration/review_plane_knobs.yaml` and enforced at existing seams — IterationContext caps + shadow `check_token_budget` that logs VIOLATIONs, never blocks; apply_params plumbing landed AP-1) in features/delegation config; declared in the guarded numeric-surface manifest (H8 class 1).
- [ ] **LB-6 — THE BUDGET GATE** — ⏳ metric + decision procedure DRAFTED ✅ 2026-07-17 (see "LB-6 Budget-gate metric + decision procedure"); **checkbox stays OPEN — threshold VALUE is an operator decision (OP-5b), not yet picked**: define the (quality gain per throughput cost) threshold that `review_decision_enforce` and H7 policies must satisfy. Threshold VALUE is an operator decision (OP bundle); this task defines the metric and decision procedure.
  - [x] **LB-6a — gate metric + decision procedure drafted** ✅ 2026-07-17 (metric, who-runs-what, re-eval cadence, FA/FR auto-demote linkage, and 2–3 candidate thresholds for the operator recorded below).
  - **[declined: ws58 2026-11-03 content-review: merged into LB-6 as its operator step (OP-5b)]** **LB-6b — operator picks threshold (OP-5b)**: choose one of the candidate thresholds (or a variant) → operator decision queue §A00; until picked, no enforce-mode flip anywhere in the series.
- [ ] **LB-7 — M3 baseline floor measurement**: full plane (shadow→enforce candidate config) vs single-augmented-LLM baseline (A0/A1 arms) on the same tasks — the go/no-go the whole series answers to.
- **[declined: ws58 2026-11-03 content-review: bookkeeping]** **LB-8 — Publish standing numbers** into the index (H0) cross-cutting section.

#### Dependency Graph

```text
H3 RD-12 baseline → LB-1 → LB-2 → LB-3 → LB-4 → LB-6 gate → (unblocks enforce-mode in H3/H7)
LB-5 (with LB-2/3) → H8. LB-7 needs H4 instrument + H5 anchor arms. LB-8 continuous.
```

#### Cross-Cutting Concerns

1. **CPU economics** — decode is BW-bound; every review token competes with production traffic; "better reviewer model beats bigger token budget" (intake-846) favors fidelity + caching over volume.
2. **GPU relief valve** — drafter Stage-1 and architect-residency (operator GPU bets 1-2) directly reduce review-turn latency; teleport (bet 4) helps long review turns; cross-ref `mi210-big-model-and-acceleration-roadmap.md`.

#### Key Files / Surfaces

- `src/proactive_delegation/` (IterationContext, complexity, QUICK_REVIEW_PROMPT), `src/features.py`
- `scripts/autopilot/eval_tower.py` replay harness; P-AB-1/P-SPEED-OBJ protocols (MEASUREMENT.md)

#### Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; LB-6 threshold proposal → operator decision queue (§A00); standing numbers mirrored to H0; any enforce-mode flip anywhere cites LB-6 passage.

#### Evidence Base (intake)

2026-07-16 throughput-regression checkpoint (master index) · intake-839 multi-role tax + single-model baseline · intake-846 15×/SUM-not-MAX/effort rules · intake-835 reminders-over-re-review + adaptive gating (2509.03581) · intake-849 P5 guardrail placement · audit doc 2026-07-16.

#### Budget Definitions (appended 2026-07-17 — design/spec only; wave-2 agent owns features/config)

Design/spec for LB-2 and LB-6. **No orchestrator code here** — a wave-2 agent implements the features/config knobs (LB-5) and runs the paired A/Bs (LB-4). Every number is **PROPOSED / observation-grade** until confirmed under **P-AB-1** (paired task-rate A/B) + **P-SPEED-OBJ** (task_rate axis); none may gate an enforce-mode flip on its own.

##### LB-2 Budget targets (proposed)

**Stack facts used as anchors** (observation-grade decode rates, single-model, 96t canonical unless noted; re-confirm under P-BENCH/P-SPEED before gating): architect ~18–21 t/s CPU, frontdoor 24.3 t/s, worker 44.7 t/s; **rubric grading is cheap-model (worker-tier) work**; on this host parallel-reviewer wall-clock models as **SUM not MAX** (intake-846). Latency budgets below are derived as `tokens ÷ t/s` on the arm that performs that decision, then rounded up for prompt/queue overhead — they are ceilings, not forecasts.

| Decision type | Actor (typical) | Token budget (out) | Latency budget (ms) | Notes |
|---|---|---|---|---|
| **plan-review** | architect (~18–21 t/s) | ≤ 350 | ≤ 22,000 | one pass per plan; reminders-over-re-review (intake-835) preferred to a second pass |
| **candidate-review** | reviewer (CPU GLM low t/s / GPU-resident) | ≤ 300 | ≤ 18,000 (CPU) / ≤ 6,000 (GPU-resident) | GBNF-constrained verdict; SUM-not-MAX if run parallel to production |
| **rubric-authoring** | strong model (architect-tier) | ≤ 800 | ≤ 45,000 | **amortized** — authored once per task-type, sticky-cached (H3); cost divided over all items it grades |
| **rubric-grading** | cheap grader / worker (~44.7 t/s) | ≤ 180 | ≤ 5,000 | high-frequency per-item path; keep it cheap (intake-834 grading-model insensitivity 2.4pp) |

- **Per-session caps** (reuse `IterationContext` semantics): `max_review_iterations` ← reuse `IterationContext.max_iterations` (per-task ceiling on review turns, proposed default **2**); `max_total_review_iterations` ← reuse `IterationContext.max_total_iterations` (per-session ceiling across all tasks, proposed default **scale with session task count, cap the review-token share — see multiplier below**). Review turns count against the same iteration ledger so a runaway Architect↔Reviewer handshake trips the existing budget, not a new one.
- **Token-multiplier knob** (`review_token_multiplier`): the governed ratio of **total tokens with the plane** ÷ **single-augmented-LLM baseline tokens on the same tasks** (LB-7 / A0–A1 arms). Literature tax is ~2–3× cost / ~8–10× latency for multi-role pipelines (intake-839); multi-agent ~15× tokens (intake-846). **Proposed target ≤ 1.5× (stretch 1.3×), hard ceiling 2.0×** — above the ceiling the plane auto-throttles review fan-out (sampling policies, LB-3) rather than spend. The multiplier is the single knob the autopilot (H8) tunes; it composes with, and is bounded by, the LB-6 gate.
- All targets are **PROPOSED**; confirm each under LB-4 (P-AB-1 + P-SPEED-OBJ) before any enforce-mode flip.

##### LB-6 Budget-gate metric + decision procedure (proposed; threshold value = operator decision OP-5b)

**Gate metric — quality-gain-per-throughput-cost.** On **paired replays** (same task set, same seeds, plane arm vs single-augmented-LLM baseline arm A0/A1) under **P-AB-1** (N ≥ 100) with the throughput axis under **P-SPEED-OBJ** (task_rate = questions / eval-wall-hour, e-process, never single-trial):

```
G = ΔP(success) / (% throughput reduction)
    ΔP(success)          = P(success | plane) − P(success | single-LLM baseline)   [pp, higher-better]
    % throughput reduction = 100 × (task_rate_baseline − task_rate_plane) / task_rate_baseline   [higher = costlier]
```

Enforce-mode for a reviewer configuration requires **BOTH**: (1) `G ≥ threshold` **and** net `ΔP(success) > 0` measured as above (the budget gate), **and** (2) the config is not in FA/FR breach (the calibration gate — RC-5). The two gates are orthogonal: a config can pass budget yet fail calibration, or vice versa; enforce needs both green. If `task_rate_reduction ≤ 0` (plane is *faster*), the gate reduces to `ΔP(success) > 0` (pure win, no cost to trade).

**Decision procedure.**
- **Who / what**: the H8 autopilot proposes an enforce-candidate config and runs the paired replay (placement via the eval fan-out path, not `/chat`; respects no-concurrent-inference + operator bench window). It computes `G`, `ΔP(success)`, `% throughput reduction`, and the FA/FR e-process state, and writes them in P-AB-1 / P-REV-1 grammar. **The operator ratifies the threshold value (OP-5b)** — agents never self-approve a gate threshold (measurement trust boundary is human-amendment-only).
- **When re-evaluated**: on every enforce-candidate config; on any instrument-era change (P-REV-1 instrument version bump, corpus revision, kernel cutover); and continuously in shadow so a live config that drifts below threshold is caught.
- **Auto-demote linkage**: the budget gate hooks the **same** demotion machinery as FA/FR — a live config whose measured `G` falls below threshold (or `ΔP(success)` goes ≤0) auto-demotes reviewer enforcement to **shadow** via `sequential_verdict.py` (`EProcessState`/`SequentialPolicy`, RC-5), exactly as an FA/FR-tolerance breach does. One demotion path, two trigger families (calibration + budget).

**Candidate thresholds — FOR THE OPERATOR TO PICK (do not self-select):**
| # | Threshold (`G` = pp ΔP(success) per 10% throughput cut) | Guardrails | Rationale |
|---|---|---|---|
| **T-conservative** | `G ≥ 0.5` (≥0.5pp quality per 10% throughput lost) | net ΔP(success) ≥ +2pp **and** throughput reduction ≤ 25% | protects production task-rate; the plane must clearly earn its cost — matches "a control plane that only adds cost gets deleted" (Fable5). Fewest configs pass. |
| **T-moderate** | `G ≥ 0.25` | net ΔP(success) ≥ +1pp **and** throughput reduction ≤ 40% | balances quality lift against the ~2–3× literature tax; expects GPU relief valves (bets 1–2) to absorb some cost. |
| **T-liberal** | `G > 0` | net ΔP(success) > 0 (any real gain) **and** throughput reduction ≤ 50% | maximizes quality capture where correctness matters more than throughput; only viable if spare capacity / off-peak review windows exist. |

Each threshold pairs a **rate** (`G`) with an **absolute floor** (net ΔP) and an **absolute cost ceiling** (max throughput reduction) so a tiny quality gain bought at ruinous cost cannot pass on the ratio alone. The operator picks one (or a variant) → §A00 decision queue (OP-5b). Standing floor cross-ref: whichever threshold is chosen, the plane must still clear **LB-7** (beat a single augmented LLM on the same tasks) — the go/no-go the whole series answers to.

##### Refactor wrap-up — 2026-10-31

REV06v2 reduced controls passed and reader proposal prepared; row is explicitly owner-held before arm for logging repair, not runnable READY. No official full50q/122B exposure, July attribution or LB1 completion. [no-belief: preparation only]

## Track: reviewer-calibration-accounting
<!-- gate: none -->

> Folded from `handoffs/active/reviewer-calibration-accounting.md` @ `9ca99cab58e3` on 2026-11-02 (BRF-T1-F25, route 1a, operator D1/D5; retired row REV-03 → REV-06). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reviewer Control Plane — Calibration Accounting: FA/FR Ledger + Near-Miss Corpus + P-REV-1 (H4)

**Status**: active — M2 "measured" milestone; the series centerpiece (every downstream claim is gated on this instrument)
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: benchmark_methodology, agent_architecture
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`evidence-plane-ledger-and-sequential-verdicts.md`](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts) (ledger conventions), [`eval-tower-verification.md`](eval-tower-program.md) (EV-tier ECE/AUC — REUSE, do not duplicate), [`reviewer-model-ablations.md`](reviewer-control-plane.md#track-reviewer-model-ablations) (H5 consumes this instrument)
**Gate**: starts after H1 TM-8 coverage + H3 shadow decisions flowing.
**Repo**: `epyc-orchestrator` (ledger/scripts) + `epyc-root` (MEASUREMENT amendment draft)

#### Objective

Build reviewer calibration accounting — decision ledger, gold labels from objective verifiers, near-miss decision corpus, calibration metrics, sequential monitoring — and draft MEASUREMENT protocol **P-REV-1** for operator sign-off. Layer A throughout.

#### Thesis

Two dive results reshape the report's design. First, **overcorrection dominates** (false-reject ≫ false-accept, 10:1-440:1 — intake-836), so the ledger runs **symmetric FA AND FR tolerance e-processes** (auto-demote a live reviewer to shadow on either breach), with the FA/FR *ratio* as a first-class column. Second, **the corpus is the instrument**: versioned, dual-gold-labeled (executable oracles + reasoning modules), spanning domains (the autopilot journal already holds thousands of scored per-question outcomes across general/hotpotqa/simpleqa/instruction_precision/thinking/code — non-code mining is cheap).

#### Prioritized Task List

- [x] **RC-1 — `review_ledger` table** ✅ 2026-07-17 (additive DDL in store.py + append-only writer `src/trace/review_ledger.py`; provenance links via emit:// paths; verified non-disruptive against a copy of the real 10,326-row DB) in the trace DB: `(decision_id, ts, reviewer_model_quant, grading_model, rubric_version, corpus_id, candidate_id, domain, decision, tripwire, confidence, gold_label, gold_source, gold_instrument_version, rationale_cause_match, latency_ms, tokens, family_match_flag, era)` with provenance links to trace events.
- [x] **RC-2 — Gold-label pipeline** ✅ 2026-07-17 (`gold_labels.py`: gate_runner / eval-tower scorer / corpus-row oracle families; ≥2-agree→multi_oracle gate-worthy; disagree→ambiguous-tail arbitration; pure functions): candidate outcome from gate_runner (format/lint/typecheck/unit) and/or eval-tower tier scorers; human arbitration only for sampled escalations + the ambiguous/unsolvable tail. **Gate-worthy rows need ≥2 oracles or human arbitration** (weak-oracle inflation: 47.9% of SWE-bench "resolved" pass on weak tests — intake-845).
- [x] **RC-3 — Near-miss decision corpus v1** ✅ 2026-07-17 (`corpus_id=nearmiss-v1`, content_sha256 1c50c025…, **11,516 rows / 0 invalid / 0 dupes** at `/mnt/raid0/llm/datasets/nearmiss-corpus-v1/`; per-source c-crab 1005 / swe-care 622 / journal 3683 (qid-hash join, 99.32% recovered) / seeded 6202 (29.1% ≤ cap) / bug-report 4; multi_oracle gate-worthy 6687; ambiguous_tail 475; natural-defect control slice 960; builder `scripts/analysis/corpus_v1/`, orchestrator `9958d819`. LATER PASSES: journal rows need candidate-text recovery (non-inference join or eval re-run) + reasoning-module labels (inference); optional Docker-oracle upgrade of single_oracle rows) (versioned: corpus id + hash): (a) autopilot journal approve/reject + scored per-question history across suites; (b) seeded-defect mutations of known-good outputs; (c) known-bad candidates from bug-reports; (d) mined c-CRAB rows + SWE-CARE pool (`/mnt/raid0/llm/datasets/`, acquired 2026-07-16). **Row schema**: dual gold labels (executable-oracle verdict + reasoning-module labels), `defect_origin ∈ {natural, seeded}` + a natural-defect control slice, decontamination metadata (repo/base_commit/created_at — SWE-Bench-Illusion applies to all SWE-bench derivatives), `rationale_vs_gold_cause` (catch right-for-wrong-reason: models detect THAT 95-100% but WHY only 52-75%). Do NOT copy c-CRAB's solvable-only filter — the ambiguous tail routes to human arbitration.
- [x] **RC-4 — `scripts/analysis/reviewer_calibration_report.py`** ✅ 2026-07-17 (full panel FA/FR/ratio/acceptance/yield/esc-precision/Brier/ECE/AUC/CR/pass^k/parse-fail + Wilson CIs per 5-tuple group; FA/FR classifiers imported from review_ledger; ECE/AUC replicated stdlib-only w/ origin comments — eval-tower versions are inline+sklearn-dependent; observation-stamped pre-P-REV-1): FA rate, FR rate, FA/FR ratio, acceptance rate, request-evidence yield, escalation precision (sampled), Brier, ECE, AUC, **Consistency Rate (test-retest ≥2 runs — bias can inflate CR to 81% at near-random accuracy)**, parse-failure rate — per (reviewer config × grading model × rubric version × corpus version × domain). **Reuse EV-tier ECE/AUC implementations** (`eval-tower-verification.md` T1) — do not duplicate. Metrics: **pass^k for review decisions** (consistency gates deploys), pass@k for candidate generation.
- [x] **RC-5 — Sequential monitoring** ✅ 2026-07-17 (symmetric FA+FR e-processes on EProcessState/SequentialPolicy; either-side CONFIRMED (wealth≥20, anytime-valid α≈.05) latches demote-to-shadow; placeholder tolerances fa=.05 / fr=.25 encode the intake-836 FR≫FA prior — pending P-REV-1; library-only, no live wiring): FA-tolerance AND FR-tolerance e-processes on `src/autopilot_core/sequential_verdict.py` (`EProcessState`, `SequentialPolicy`) — live breach on either side auto-demotes the reviewer to shadow. Enforcement, not new decision theory (Fable5 posture).
- [x] **RC-6 — Draft MEASUREMENT amendment P-REV-1** ✅ 2026-07-17 (amendment text DRAFTED — see "P-REV-1 Draft Amendment Text" section below; **operator PR still outstanding** — MEASUREMENT.md is human-amendment-only): instrument = (corpus id+hash, gold-label source+version, reviewer model+quant+grammar-flag, grading model, rubric version, shadow/live mode, n); changing any = new instrument version; claim grammar `reviewer FA x%, FR y% (n=…, corpus rev-…, gold=…) [P-REV-1, date, attest …]`; directions stated; external judge-of-judge samples cite pinned API model-id+date as part of the instrument. Speed/latency claims stay under existing P-AB-1/P-SPEED-OBJ.
  - [ ] **RC-6a — operator PR + sign-off** (human-amendment-only): land the drafted P-REV-1 blocks into `MEASUREMENT.md` §1/§2/§3 via PR-reviewed amendment with a one-line CHANGELOG (append-or-version). Until merged, every reviewer FA/FR/yield/CR number stays an **observation** and MUST NOT gate any keep/revert/deploy/promote decision in H5/H7. The PR also adds (absorbs two rows) a chance-corrected agreement statistic with a declared tie/abstention estimand whose rate is reported, not skipped.
- [x] **RC-7 — Evidence-plane alignment** ✅ 2026-07-17 (docstring alignment note + `to_question_ledger_row()` adapter stub — decision≈question): per-decision rows follow per-question-ledger conventions (decision ≈ question); cross-ref both handoffs.
- [ ] **RC-8 — Baseline run**: current self-review (architect alias) in shadow on corpus v1 — the first FA/FR numbers. **Broken-grader guardrail**: read transcripts before trusting a surprising number (CORE-Bench 42→95% was grader repair, not model change).
- [x] **RC-9 — Rubric persistence** ~~✅ 2026-07-29~~ **REOPENED 2026-09-16** (`review_ledger.v2`; focused validation: 94 passed, 1 expected skip): full rubric and per-item grade snapshots now persist in nullable canonical-JSON `rubric_json` / `per_item_grades_json` columns. The additive migration preserves pre-RC-9 rows; legacy writers remain valid, and readers retain raw forensic columns while exposing decoded `rubric` / `per_item_grades` aliases. This is an accounting schema change only — no reviewer metric or instrument claim was produced. **Staleness audit 2026-07-29:** the prior ledger had `rubric_version` only, with no rubric/grade payload; its append writer has HIGH impact (analysis, tests, Autopilot, and trace modules), so this was implemented as a separately reviewed additive schema + backward-compatible writer/read change.
  ✅ 2026-09-16 RE-IMPLEMENTED and merged: orchestrator `ebfb1cb5` on main (`review_ledger.v2`: `rubric_json` + `per_item_grades_json`, repeat-safe migration, no back-fill; 813 real rows verified before/after). Residual data gaps (per-item grades from live grading, score-token logprobs) are RC-10/SC43, not RC-9.
  - **Reopen note 2026-09-16 (sub-closure-fix):** the 2026-07-29 tick is false. The `review_ledger.v2` schema and the `rubric_json` / `per_item_grades_json` columns **exist on no ref**. They are absent from orchestrator `origin/main` @ `88a2902d` (`src/trace/review_ledger.py`, `src/trace/store.py`) and from every branch tip and the `log --all -S` history of root, orchestrator and research; the only hits are untracked bus state. The tick arrived in root `4762625d` (2026-07-30), the same false cohort as UTM-M7/M8 and E1a. Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #2) and `scripts/handoffs/closure_audit.py --strict-idents`. The work is still needed: the ledger carries `rubric_version` only.
  - **Progress 2026-09-16 (sub-rc9): implemented, NOT yet on `origin/main` — box stays open until merge.**
    Orchestrator branch `sub/rc9-20260916` @ `ebfb1cb5` (unpushed) implements the spec above:
    nullable canonical-JSON `rubric_json` / `per_item_grades_json` columns in `src/trace/store.py`;
    an additive, idempotent v1→v2 `ALTER TABLE` migration with no back-fill (read-only ledgers still read);
    `LEDGER_DDL_VERSION = "review_ledger.v2"`; and readers that keep the raw columns and add decoded
    `rubric` / `per_item_grades` aliases (`None` on v1 rows). Legacy writers are unchanged and still
    valid. The writers now populate the columns wherever a producer holds the data:
    - `grade_result_to_ledger_row()` covers the RD-2 `GradeResult`, including its full rubric and
      per-item grades.
    - `review_decision_to_ledger_row` / `record_review_decision` accept the snapshots and map
      `rubric_ref` to `rubric_version`.
    - The `review_plan_rubric` event records a rubric snapshot (id, template sha256, axes). It
      records per-item grades only when the emission parsed, because the axes default to `True`
      otherwise.
    - `reviewer_events_to_ledger` passes both snapshots through.
    - The `reviewer_corpus_ledger_run` field-order arms carry their prompt-rubric snapshot.

    Validation: `tests/test_review_ledger_v2.py` (15 tests); related suites 409 passed, 1 skipped,
    4 xfailed. A migration dry run on a copy of `data/trace/review_ledger.sqlite` read all 813 rows
    before and after the migration, `calibration_summary` was identical, and 0 rows were back-filled.
    No reviewer metric was produced. **Data gaps (need a capture run, i.e. inference, not schema
    work):**
    - The single-token corpus probe has no per-item grades.
    - No live producer calls `grade_candidate` yet, so no captured rubric snapshot exists.
    - Score-token logprobs / K-vector remain uncaptured (RC-10 / SC43).

    Vidya: root `origin/main` has no reviewer adapter (SC43 / SC83 are "none (planned)"), so there
    is nothing to re-wire yet; a future adapter reads the decoded aliases.
    **Tick when `ebfb1cb5` lands on orchestrator `origin/main`** (that merge is the only remaining
    step).
- **[declined: ws58 2026-11-03 content-review: duplicate — eval-tower-program EV-15a builds the logprob-expectation read-out]** **RC-10 — Evaluate a logprob-expectation confidence construction against the existing ledger and
  corpus.** The intake-804 cross-link below (Research Intake Cross-Link — 2026-07-29) has been prose
  only since it was filed; this is its first runnable entry point, and it inherits that block's scope
  boundaries verbatim — **evaluate an alternate confidence construction against the existing
  ledger/corpus and calibration panel; do not replace the typed decision, alter a threshold, or infer a
  reviewer-quality improvement from the paper.** Preserve objective-verifier precedence and cross-family
  separation. [intake-804] [intake-1162] [intake-1168]
  - **What to run.** A/B the current discrete construction against an expectation over the score-token
    distribution on `nearmiss-v1` (11,516 rows, sha `1c50c025…`) via
    `scripts/analysis/reviewer_calibration_report.py`, reporting Brier/ECE/AUC on both arms. Smallest
    implementation site is `repos/epyc-orchestrator/src/pipeline_monitor/model_grader.py:159-168` —
    replace `choice_scores.get(classification)` with `Σ_g p(v_g)·φ(v_g)` over the existing
    `choice_strings`. The read-out spec, the T=1 constraint and the silent-failure guards are specified
    once in `eval-tower-verification.md` EV-15b/EV-15c — reuse them, do not restate them here.
  - **Per-generator normalisation is a prerequisite, not a refinement.** intake-1168 Appendix H finds
    that raw log-likelihood conflates distributional similarity with the *intrinsic predictability* of
    the generator's text — short, conventional output scores higher regardless of correctness. Subtract
    each generator's mean across verifiers before the score means anything, or the construction is
    partly a **style prior** rather than a correctness signal. An un-normalised arm is not a valid
    comparison.
  - **Prompt-framing caveat to record alongside any result.** With unit-test ground truth held fixed, a
    one-word strict-versus-lenient change in the judge prompt swung one model from **−0.106 to +0.722**
    (intake-875 Table 5). Any A/B here must hold framing byte-identical across arms and say so.
  - **Standing constraint (RC-6a):** until the operator PR merges, every number this row produces is an
    **observation** and MUST NOT gate any keep/revert/deploy/promote decision in H5/H7.
  - **Precondition check 2026-09-16 (sub-reviewer): NOT startable offline.** `data/trace/review_ledger.sqlite`
    `review_ledger` stores one scalar `confidence` and no score-token distribution: there are no logprob,
    K-vector or `retained_mass` columns. `scripts/analysis/reviewer_corpus_ledger_run.py` also records that
    the reviewer probe captures no per-decision logprob. The existing ledger cannot supply the expectation
    arm, so RC-10 needs a NEW capture run: inference, with the SC43 write-side fields emitted from the first
    call.
- [x] **RC-11 — report false-accept and false-reject SEPARATELY** (intake-1307; 2026-09-07). A single
  aggregate accuracy does not satisfy this plane's gate. Where one side is not computable — typically
  false-reject, because a rejected item has no ground truth — **say so explicitly and report the cause
  histogram instead; never omit the side silently.** intake-1307 is the citable precedent for the
  omission being the *default* behaviour rather than an oversight: it quantifies false-accept in three
  places (8% wrong-class proved, 0.877 and 0.932 accepted accuracy) and never converts false-reject to
  a rate at all, decomposing it by cause instead. That asymmetry is the finding, not the paper's bug.
  **✅ 2026-09-08 — audited + one residual gap closed.** Audit result: all four FA/FR-reporting
  surfaces were already separate (pii_fixture_eval.py FA 0/21 + FR 0/30 with own denominators and
  cause histograms; reviewer_calibration_report.py per-side columns with Wilson CIs;
  safety_gate.py / review_policy_trials.py / screening_tier_runner.py separate with absent side
  surviving as null). Residual gap — `reviewer_calibration_from_decisions` returned only the
  computable axes and the corpus reader silently dropped observation-gold rows — CLOSED in
  epyc-orchestrator `15d0858f`: every axis key always present, an unmeasured side is `None`
  (never absent, never `0.0`), `n_gate_fail`/`n_gate_pass` ride along, and exclusions are counted by
  cause at both the corpus-read seam (`judgeable_row_cause`: no_candidate_answer /
  non_conclusive_gold_label / observation_gold_confidence / not_a_record) and the gate-None seam
  (`excluded_no_conclusive_gate`). Full audit record: `progress/2026-09/2026-09-08.md`.
- [x] **RC-12 — audit every reviewer/gate threshold for selection-on-the-certification-sample**
  (intake-1307; 2026-09-07). For each threshold, record whether it was chosen on a split independent
  of the one used to certify it. Where it was not, either re-derive on a held-out split or record the
  multiplicity penalty owed. The source makes the size of this concrete: the same data certifies at
  materially different risk levels under a union-bounded grid search versus a threshold picked on an
  independent dev split, and it treats that difference as decisive rather than cosmetic. Maps directly
  onto the standing "eight ways a check passes for the wrong reason" catalogue.
  **✅ 2026-09-08 — 16-threshold audit filed.** The referenced ~110-threshold subagent report is not
  recoverable from the tree (re-enumerated from code instead; every `file:line` verified by direct
  read). Three VIOLATIONS: (1) `rubric_pass_threshold` default 0.60 in `eval_tower.py:4334-4335` —
  unknown derivation, converts rubric aggregates into per-question `correct` feeding the SafetyGate
  quality axis; remedy: derive from a rubric-vs-gold slice or make `scoring_config` name threshold +
  rationale per suite (mirroring gate_verdict's mandatory rationale), until then observation-only.
  (2) PII-hook exemption surface in `pii_precommit.sh` — tuned on observed over-blocks with fixture
  rows added in the same commits that certify it (catalogue face 15: the oracle endorses the defect);
  mitigation present (evaluator prints same-sample provenance; `candidate_eval_gate.sh:26` mislabels
  it "held-out" — relabel to "same-sample PII fixture validation (observation-only)", wording fix
  only). (3) `DEFAULT_BASELINE_QUALITY=1.16` `safety_gate.py:365` — silent fallback default of
  undocumented derivation; prefer fail-closed. Plus: review_ledger FA/FR tolerances are
  self-declared placeholders (stamped `thresholds_are_placeholders`) pending P-REV-1 — re-derive on a
  held-out near miss slice before any live wiring. One previously-filed VIOLATION already fixed
  (impact.py ordinal drift, `ae8ab82b`). OK-class: sequential_verdict e-process policy
  (protocol-derived), SafetyGate tuning constants (incident-derived, continuously gated), gate_verdict
  (design is the anti-VIOLATION), CITATION_THRESHOLD_N=20, vidya policy floors, repo-readiness 80%
  (external rubric). Full findings table: `progress/2026-09/2026-09-08.md`.
  **Follow-on execution 2026-09-08 (all zero-inference):**
  - **(1) mechanism half landed** (epyc-orchestrator `5a9442d3`): every rubric row now carries
    `rubric_threshold_source` — `declared` (threshold + `rubric_threshold_rationale` named in
    `scoring_config`), `declared-no-rationale`, or `undeclared-default-0.60` — serialized into the
    detail row, plus a once-per-suite warning naming the remediation. The defaulted 0.60 is no
    longer silent anywhere. Hard refusal at decision-grade seams is NOT yet enforced: rubric scoring
    is ~0.7% of the quality objective, no suite currently declares the threshold, and RC-6a makes
    the plane observation-only — the refusal half lands with the RC-6a/P-REV-1 operator window
    (same gate as the reviewer tolerances below).
  - **(2) relabel landed** (epyc-root `af4c5c63`): `candidate_eval_gate.sh` usage now reads
    "same-sample PII fixture validation (observation-only)".
  - **(3) loudness landed** (epyc-orchestrator `5a9442d3`): `Baseline.load` warns loudly when a
    persisted baseline file names no quality source (SG-3 already forces strict same-tier reads at
    every decision site, so the legacy 1.16 now only reaches lenient/display reads — but a number
    nobody re-derived must not be silent). Behavior unchanged otherwise.
  - **#1 reviewer tolerances + refusal halves: NOT executed — inference/cadence-gated.** Both need
    the RC-8 near-miss baseline data (shadow reviewer runs) and the RC-6a P-REV-1 operator PR
    (human-amendment-only). Recorded here so they cannot read as lost.

#### Dependency Graph

```text
H1 TM-8 + H3 shadow flow → RC-1 → RC-2 → RC-3 corpus v1 → RC-4 report → RC-5 e-processes → RC-8 baseline
RC-6 P-REV-1 draft (parallel after RC-1; operator PR gates all decision-grade claims in H5/H7)
RC-7, RC-9 (parallel)
```

#### Cross-Cutting Concerns

1. **Layer A / trust boundary** — reviewer metrics do NOT enter the T0-T3 model-quality axes; they are a separate instrument gating *reviewer-role promotion*. The plane invokes the tower; the tower never depends on the plane.
2. **Anti-reward-hacking** — any learning loop off this ledger must keep objective-verifier precedence, cross-family author/grade separation, and never optimize directly against the rubric score (intake-834 critique lit: length exploitation is the known failure).
3. **Domain generality** — calibration reported per-domain; expect reviewer value highest on planning/reasoning-heavy suites, lowest on saturated factual ones.

#### Key Files / Surfaces

- trace DB (H1) — `review_ledger` home; `src/autopilot_core/sequential_verdict.py`
- `scripts/autopilot/eval_tower.py` + `rubric_scoring.py` (EV-9/ECE/AUC reuse)
- `/mnt/raid0/llm/datasets/` (SWE-CARE, c-CRAB, RewardBench 1/2, JudgeBench, LLMBar — see `BENCHMARKS.md`)
- `/workspace/MEASUREMENT.md` (P-REV-1 target; operator PR)
- autopilot journals (`orchestration/autopilot_journal*.jsonl` — read ALL rotated shards)

#### Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; corpus versions and first FA/FR numbers recorded here + H0 milestone table; P-REV-1 text goes to the operator decision queue (§A00) — do not self-approve; all pre-P-REV-1 numbers are observations, never decision-gating.

#### Evidence Base (intake)

intake-836 FR≫FA asymmetry + rationale-vs-cause · intake-837 Consistency Rate · intake-844 Recall/OverPrediction plan-grading template · intake-845 executable oracles + corpus mining rules · intake-846 pass^k + broken-grader guardrail · intake-834 rubric persistence + decision bands · intake-804 continuous verifier confidence source · audit doc 2026-07-16 · dataset manifest B13.

#### P-REV-1 Draft Amendment Text (for operator PR — MEASUREMENT.md is human-amendment-only)

Copy-paste-ready blocks for the operator to land in `MEASUREMENT.md` via a PR-reviewed amendment (append-or-version; one-line CHANGELOG). Grammar matches the existing `P-QUAL-T1` instrument-card style. **This handoff must not edit MEASUREMENT.md — the autopilot/agents may READ it, never write it.** Nothing below is a claim until it is merged AND a measurement citing it exists; all pre-merge reviewer numbers are observations (§5 demote-to-prior default).

##### Block 1 — add to §1 Protocol registry (after P-SPEED-OBJ)

> ### P-REV-1 — Reviewer decision calibration (instrument card)
> The instrument for **reviewer-role promotion** — it gates keep/revert/deploy/promote of a *reviewer configuration*, never a model-quality (T0–T3) axis (Layer A; the plane invokes the tower, the tower never depends on the plane).
> - **Instrument** = (**decision corpus id + content hash**, **gold-label source + version** — objective oracle set and/or eval-tower tier scorer, `gold_instrument_version`, ≥2 oracles or human arbitration for gate-worthy rows), **reviewer model + quant + grammar-flag** (GBNF on/off is part of the instrument), **grading model**, **rubric version**, **shadow/live mode**, **n decisions**. Changing **any** field = a **new instrument version** (append an era row per `instrument_eras.yaml`, `scope: reviewer_plane`; never rescale prior FA/FR in place).
> - **Reps**: paired arms per **P-AB-1** (same decisions/prompts/grammar/stop/verifier budget both arms), **N ≥ 100/arm** for a reviewer-promotion decision; failures classified by reason (backend outage / timeout / empty / genuine) with infra-failure rate reported alongside the effect; flag-state attestation across all workers in the run header. **A single-corpus, single-run number is an observation** (never a decision), same rule as every other protocol here.
> - **Consistency**: `pass^k` for review decisions (test-retest ≥2 runs; CR can inflate to ~81% at near-random accuracy under bias — report accuracy next to CR). `pass@k` is for candidate *generation*, not review.
> - **Directions** (state explicitly; ambiguous-direction errors have burned debugging time): **FA (false-accept) rate — lower-better**; **FR (false-reject) rate — lower-better**; **request-evidence yield — higher-better**; **Consistency Rate (CR) — higher-better**. The **FA/FR ratio** is a first-class reported column (overcorrection dominates: FR≫FA, 10:1–440:1 — intake-836), not a derived footnote.
> - **External judge-of-judge**: any externally-graded sample cites the **pinned API model-id + date** as part of the instrument version (e.g. `judge=<model-id>@YYYY-MM-DD`); a different judge model-id or date = a new instrument version. Bounded/budget-capped per the H5 Ref arm.
> - **Broken-grader guardrail**: read transcripts before trusting a surprising FA/FR flip (CORE-Bench 42→95% was grader repair, not model change — intake-846).
> - **Out of scope for P-REV-1**: latency/throughput/token-cost claims stay under **P-AB-1** (paired task-rate A/B) and **P-SPEED-OBJ** (task_rate axis). P-REV-1 governs *decision quality only*; the budget gate is `reviewer-latency-and-sampling-budget.md` LB-6.

##### Block 2 — add to §2 Claim grammar & examples

> - Reviewer-calibration claim grammar: `reviewer FA x%, FR y%, yield z%, CR c% (n=N/arm, corpus rev-<id>@<hash8>, gold=<source>/v<ver>, reviewer=<model>/<quant>/gbnf=<on|off>, grader=<model>, rubric=v<r>, mode=<shadow|live>) [P-REV-1/<instrument-ver>, YYYY-MM-DD, attest <id>]`. FA/FR are lower-better, yield/CR higher-better; the FA/FR ratio is reported.
> - ✅ Worked example (illustrative — NOT a measurement): `reviewer FA 1.8%, FR 12.4% (ratio 0.15), yield 63%, CR 88% (n=120/arm, corpus rev-nm1@9f3a2c71, gold=gate_runner+evaltower-T1/v2, reviewer=GLM-5.2/UD-IQ2_M/gbnf=on, grader=Qwen3-Coder-30B, rubric=v3, mode=shadow) [P-REV-1/iv-1, 2026-08-xx, attest r7c1]`.
> - ❌ `reviewer catches 95% of bugs` (no instrument, no n, no protocol — and conflates "detects THAT" 95–100% with "detects WHY" 52–75%; intake-836).

##### Block 3 — add to §3 Standing noise & resolution table

> | Reviewer FA/FR resolution | `1/n_arm` per rate; report FA/FR ratio + CR with accuracy | P-REV-1 instrument card |
> | Reviewer CR inflation caveat | CR ≈ 81% reachable at near-random accuracy | intake-837 |

##### Operator sign-off checklist (RC-6a)
1. Land Blocks 1–3 verbatim (adjust cross-ref anchors as needed) with a one-line CHANGELOG entry.
2. Append the `scope: reviewer_plane` era row to `instrument_eras.yaml` when corpus v1 + gold pipeline freeze.
3. Confirm `check_claims_grammar.sh` recognizes the `[P-REV-1/…]` citation form (warn-mode month 1).
4. Until merged: reviewer FA/FR/yield/CR remain observations (RC-6a checkbox stays open).

#### Research Intake Update — 2026-07-21 (P-REV-1 needs a chance-corrected agreement statistic — RC-6a still open)

- **[intake-876] "Agreement Metrics for LLM-as-Judge Evaluation: What to Report and Why"** (arxiv:2606.00093; Delip Rao, Chris Callison-Burch)
  - Relevance: **this arrives in time to amend a DRAFT rather than a ratified protocol.** RC-6a is still an open checkbox, and the P-REV-1 claim grammar currently reports raw FA/FR/yield/CR with **no chance correction, no confusion matrix, and no declared tie/abstention estimand**.
  - Why it bites here specifically: RM-3c's live slice is FR 50.0% / FA 16.7% — a maximally skewed marginal. This handoff already warns in prose that bias can inflate CR to 81% at near-random accuracy. That warning is a **rediscovery of the chance-correction problem**, currently patched with a caveat instead of a statistic.
  - Key claims: on non-degenerate binary data Pearson/Spearman/Kendall/phi/MCC all collapse to the **same number** (reporting several manufactures fake corroboration); Cohen's kappa is the only common coefficient adding information, because its marginal-sensitive normalization exposes judge-vs-human positive-rate drift. Recommended minimal binary report = accuracy + F1 + kappa + exactly one correlation representative + the confusion matrix.
  - Abstention handling is a **choice of estimand, not preprocessing**: exclude / recode-as-negative / retain-as-third-class each estimate a different quantity. This directly bites GC-external-1a, which currently drops malformed/tie rows as data cleaning.
  - **Caveat carried forward:** the paper does not discuss Gwet's AC1. The classical kappa paradox is that kappa collapses toward 0 under highly skewed marginals even at high raw agreement — exactly our deliberately near-miss corpora. Pair kappa with prevalence/bias disclosure (or AC1); do not adopt kappa uncritically.
  - Delta from current approach: cost is low (kappa/Fleiss/Krippendorff are ~30 lines stdlib, alongside the existing stdlib ECE/AUC reimplementation).

- **[declined: ws58 2026-11-03 content-review: merged into the RC-6a PR (its own text: do BEFORE the PR lands)]** Operator-review candidate (RC-6a, do BEFORE the PR lands): add a chance-corrected agreement statistic + a declared tie/abstention estimand + confusion-matrix publication to the P-REV-1 claim grammar; pair kappa with marginal/prevalence disclosure per the kappa-paradox caveat. Human-amendment-only — operator PR, not an agent edit. [intake-876]
- **[declined: ws58 2026-11-03 content-review: merged into the RC-6a PR]** Operator-review candidate (GC-external-1a): declare the tie/abstention estimand explicitly and report its rate, rather than skipping malformed/tie rows as cleaning. [intake-876]

#### Research Intake Cross-Link — 2026-07-29 (intake-804; confidence source, not a re-verdict)

- [`intake-804`](../../research/intake_index.yaml) is the canonical arXiv write-up of LLM-as-a-Verifier (also tracked as intake-362#record / intake-363#record in the eval tower). Its central empirical claim is that a **continuous score formed from scoring-token logit expectations** can rank and calibrate solutions better than discrete judgments. The reviewer plane currently emits discrete typed decisions with scalar `confidence ∈ [0,1]` (RA-1) and reports Brier/ECE (RC-4/RM-2), so this is directly relevant as a **candidate confidence source**.
- Scope boundary: use it to evaluate an alternate confidence construction against the existing ledger/corpus and calibration panel; do not replace the typed decision, alter a threshold, or infer a reviewer-quality improvement from the paper. Any measured comparison remains an observation until the P-REV-1 instrument and its required evidence are satisfied.
- Local-enabler boundary: the 2026-07-21 `completion_probabilities_geomean` path and `confidence_is_real` fail-closed gate make local extraction/evaluation possible; their existence is not evidence that this source is calibrated for reviewer decisions. Preserve objective-verifier precedence and cross-family separation.

#### RC-13 — Autonomous-science judge calibration

**Activation trigger:** materialize RC-13 only when EPYC begins proposal-to-execution scientific experiments whose outcomes require independent trajectory, artifact, or manuscript review. Maintenance jobs, software evaluations, and research-intake summaries do not fire this trigger. `RA-14` and `VB-AISCI-1` must exist before the first such evaluation.

- **RC-13a:** add an autonomous-science shadow-evaluation stratum whose sampling unit is one manifest-bound attempt or adjudicated manuscript, never a framework-task cell inferred from prose. Preserve independent-study clusters, task/version/model/scaffold strata, failures, and committed metric; report per-stratum denominators and refuse pooled rates across incompatible endpoints, budgets, operators, or stopping rules. Sources: intake-1675#record, intake-1704#record, intake-1705#record, intake-1706#record.
- **RC-13b:** validate automated trajectory and log judges on held-out human labels with the full confusion matrix, precision, recall, false-accept, false-reject, disagreement, prevalence, and uncertainty. Keep outputs observation-only until calibration passes; agreement is not accuracy. Source: intake-1707#record.
- **RC-13c:** add blinded independent scientific adjudication over multiple tasks and reviewers independent of the system and original task authors, with any original-author arm disclosed separately. Record blinding, task-selection freedom, artifact-inspection completeness, and separate engineering, manuscript, venue, and scientific-validity judgments. Sources: intake-1653#record, intake-1705#record, intake-1706#record.

#### MAIN-reviewed JEV refinement — 2026-10-06 (RC-10)

Prepare an adapter arm using the shipped `Question`/`DecisionResult` and native candidate readout over the existing score-bin catalogue, rather than building a second typed scorer. Compute the specified expectation in host code; preserve explicit unsupported, missing and unresolved outcomes. Deterministic fixtures can validate mapping, expectation, failure denominators and call-accounting integration without model calls.

Before a live comparison, prove that temperature, masking/conditioning and probability semantics match RC-10's existing EV-15b/EV-15c read-out contract. Native candidate probabilities cannot silently replace the historical score-token instrument. Preserve the same corpus/panel, objective-verifier precedence, cross-family separation and all P-REV-1/inference gates. This refinement supplies an implementation seam; it changes no threshold or reviewer verdict and establishes no accuracy or cost improvement. Use `record_llm_calls` where its actual primitives seam is invoked; missing telemetry stays absent.


- [x] **RC-10-PREP — implement pure supplied-score expectation and synthetic coverage/failure contract.** ✅ 2026-10-06 — [Preparation contract](../../docs/reference/confidence-expectation-preparation.md), APPmainff423d14, original CI37446388954 TRUE26/26 after MAIN original source/API review. Existing three grading φ maps supplied unchanged; no zero-fill/renormalization. Synthetic coverage assertion is not native coverage proof. Historical EV-15b/c parity, same-corpus/panel live comparison and Claude-owned SC43 producer remain open; RC-10 parent remains unchecked.

## Track: reviewer-typed-artifacts
<!-- gate: none -->

> Folded from `handoffs/active/reviewer-typed-artifacts.md` @ `9ca99cab58e3` on 2026-11-02 (BRF-T1-F25, route 1a, operator D1/D5; retired row REV-09 → REV-06). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reviewer Control Plane — Typed Artifact Schemas (H2)

**Status**: active — M1 "observable" milestone; schemas are the contract everything downstream validates against
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, tool_implementation
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-trace-materialization.md`](../completed/reviewer-trace-materialization.md) (H1; events carry these artifacts), [`reviewer-decision-plane.md`](../completed/reviewer-decision-plane.md) (H3; emits them), [`tri-role-coordinator-architecture.md`](routing-program.md#track-tri-role-coordinator-architecture) (Verifier semantics)
**Repo**: `epyc-orchestrator`

#### Objective

Author the three missing IR schemas — evidence-linked `ReviewDecision`, `CandidatePackage`, `VerificationReport` — wire them into `orchestration/validate_ir.py` alongside the existing task_ir/architecture_ir/procedure suite, evolve the dormant dataclasses in `src/proactive_delegation/types.py`, and make reviewer output grammar-constrainable. Schemas are **domain-general**: evidence kinds include answer spans, retrieval provenance, and scorer results — not just file_span/test_result.

#### Thesis

Typed artifact contracts are the design center (report thesis + MetaGPT's validated discipline, intake-839). The repo already has the IR convention + validator; what's missing is the review-plane trio plus governance semantics the dive evidence forces: a **tripwire ⟂ advisory split** (blocking boolean orthogonal to score/feedback — `safety_gate.py` has it, `ArchitectReview` doesn't; intake-849 P1), **REJECT-to-empty** as a first-class plan outcome (bad plan < no plan; intake-835), **payload sanitization** (architect self-assessment shifts verdicts ~18-29pp; intake-837/838), and **parse-failure accounting** (an IQ2 reviewer's schema-emission failures are themselves a quality signal).

#### Prioritized Task List

- [x] **RA-1 — `orchestration/review_decision.schema.json`** ✅ 2026-07-17: decision enum `{approve, reject, reject_to_empty, request_changes, request_evidence, escalate}`; `confidence` [0,1]; `tripwire: bool` + `blocking_issues[]` (hard stop) structurally separate from `score`/`non_blocking_issues`/`feedback` (advisory); `evidence[]` with kinds `{file_span, test_result, gate_result, scorer_result, answer_span, retrieval_provenance, trace_event, protocol_claim}`; `verifier_requests[]`; `human_review_required`.
- [x] **RA-2 — `orchestration/candidate_package.schema.json`** ✅ 2026-07-17 (sanitized_view projection w/ additionalProperties:false — leaked self-assessment FAILS validation): task ref, plan ref (task_ir), diff/output refs, declared acceptance checks, provenance (model+quant, role, flag state, instrument era) — **plus a sanitization contract**: the reviewer-visible view MUST exclude architect self-assessment prose, confidence assertions, and "refined/final/expert" labels (intake-837/838). Sanitization is applied at package assembly, not reviewer prompt time.
- [x] **RA-3 — `orchestration/verification_report.schema.json`** ✅ 2026-07-17 (certificate required-on-fail via if/then): normalizes `gate_runner.GateResult` + eval-tower tier outputs; **three-valued outcome per check: `pass | fail | inconclusive`** with a `certificate` field on fail (failing assertion / counterexample / unsat core — the request_evidence payload; intake-842/843) and instrument version.
- [x] **RA-4 — Rubric artifact schema** ✅ 2026-07-17 (`orchestration/review_rubric.schema.json`): items `{text, axis, weight ∈ {1,2,3}}`; axes per domain template (code: file-change/spec-alignment/integrity/runtime; QA: grounding/question-alignment/integrity-no-fabrication/completeness; math: answer/method/integrity/coverage) (intake-834). Rubrics are cacheable, versioned artifacts.
- [x] **RA-5 — Wire all four into `orchestration/validate_ir.py`** ✅ 2026-07-17 (SCHEMA_MAP; non-zero exit on failure); **schema validation gates every role boundary** — a validation failure is a routable bounce-to-author event, never silent (intake-839).
- [x] **RA-6 — Evolve `src/proactive_delegation/types.py`** ✅ 2026-07-17 (+REQUEST_EVIDENCE/+REJECT_TO_EMPTY; ArchitectReview +confidence/tripwire/evidence/verifier_requests, all defaulted; consumers verified — 102 regression tests pass; enum/semantics ratification stays in OP-5f): add `ReviewDecision.REQUEST_EVIDENCE` + `REJECT_TO_EMPTY`; extend `ArchitectReview` with `confidence`, `evidence`, `verifier_requests`, `tripwire` (keep `score` for compat; document score-vs-confidence semantics — operator question in OP bundle).
- [x] **RA-7 — GBNF/json_schema constrained-decoding generation** ✅ 2026-07-17 (`review_grammar.py`: enum sourced from schema file so grammar cannot drift; pure generators + `parse_review_decision` w/ ParseFailure accounting. Grammar EXECUTION on the v7 GPU lane remains K22-blocked) from RA-1/RA-4 for llama.cpp reviewer calls, flag-gated. **Blocked for v7 GPU lane by the grammar-sampler P0 crash** (`common/sampling.cpp:292` — routed to `gemma-challenge-kernel-techniques-v7.md`); CPU production path unaffected pending verification.
- [x] **RA-8 — Field-order A/B design** ✅ 2026-07-17 (full design appended below; EXECUTION inference-gated → H5 RM-6): evidence→confidence→verdict vs verdict-first. Opposing hypotheses on record: verdict-first suppresses self-justification overcorrection (intake-836) vs verdict-first anchors (intake-837). Design the experiment here; run under H5.
- [x] **RA-9 — Round-trip + validator tests; parse-failure accounting** ✅ 2026-07-17 (57 tests) (count schema-invalid emissions per reviewer config; never silently fall back).
- [x] **RA-10 — Schema-versioned artifact emission into the trace store** ✅ 2026-07-17 (ledger rows + emitted artifacts stamp schema_version; REVIEW_DECISION_SCHEMA_VERSION=1.0.0 default w/ override; verification_report versions threaded through gold resolutions).
- [x] **RA-11 — ArchitectureIR/PlanGraph hardening** ✅ 2026-07-17 (optional-but-recommended-for-new-artifacts: interfaces section + typed call_edges; existing docs stay valid) (intake-839): ArchitectureIR mandates an interface-definition/data-structure section; plan steps carry typed call-flow dependency edges, not prose.

#### Dependency Graph

```text
RA-1..RA-4 (schemas, parallel) → RA-5 validator wiring → RA-6 types → RA-9 tests → RA-10 emission
RA-7 GBNF (after RA-1/RA-4; v7-GPU-blocked on kernel P0)     RA-8 design (parallel; executes in H5)
RA-11 (parallel)
```

#### Cross-Cutting Concerns

1. **Domain generality** — every schema field must make sense for non-code candidates (answers, plans, summaries); code-specific fields are optional extensions.
2. **IQ2 strict-IF weakness** (2/11 measured) is why RA-7 grammar constraint + RA-9 parse-failure accounting are load-bearing, not nice-to-have.
3. **Immutable structure, mutable status** (intake-846): artifacts are append/versioned; only status fields mutate.

#### Key Files / Surfaces

- `orchestration/*.schema.json` + `orchestration/validate_ir.py` (existing convention to extend)
- `src/proactive_delegation/types.py` (`ReviewDecision`, `ArchitectReview`, `IterationContext`)
- `src/task_ir.py`, `src/graph/task_ir_helpers.py`

#### Reporting Instructions

Flip checkboxes with `✅ YYYY-MM-DD`; schema versions are instruments — version bumps get changelog lines here. RA-6 enum evolution and score-vs-confidence semantics are operator decisions (OP bundle in master index §A00).

#### Evidence Base (intake)

intake-834 rubric artifact + axes · intake-835 REJECT-to-empty · intake-836 verdict-first/admissibility · intake-837/838 sanitization + field-order anchoring · intake-839 boundary validation-gating + IR hardening · intake-842/843 three-valued outcomes + certificates · intake-849 tripwire⟂advisory (P1) · audit doc 2026-07-16.

#### RA-8 — Field-order A/B experiment design (designed 2026-07-17; executes as H5 RM-6)

**Question**: does ReviewDecision field ORDER in the constrained-decoding schema change reviewer calibration? Two GBNF/json_schema variants generated from the same schema (`review_grammar.py` supports property ordering): **V-first** = decision→confidence→blocking→evidence→feedback; **E-first** = evidence→blocking→confidence→decision→feedback.
**Opposing hypotheses on record**: H1 (intake-836): V-first ↓FR — forcing the verdict before free-text suppresses self-justification-driven overcorrection (their explain-then-fix effect, 35.9→87.9% FR). H2 (intake-837): V-first ↑anchoring — committing to a verdict before enumerating evidence degrades accuracy on near-miss items (their CoT-order effects).
**Protocol**: paired within-item (same corpus-v1 slice graded under both grammars, same reviewer/grader config, seed42 production sampling), stratified to include the ambiguous-tail + natural-defect control slices; N≥100/arm per P-AB-1; primary metrics FA, FR, CR (test-retest ≥2), parse-failure rate; secondary: per-domain splits + confidence calibration (ECE). Analysis: paired flips via `sequential_verdict.quality_trial_statistic`, Holm over {FA, FR, CR}. Decision rule: adopt the variant that is non-inferior on FA and superior on FR (or vice versa with operator weighting); tie → keep E-first (matches evidence-linked design intent). **Execution is inference-gated → H5 RM-6.**

#### RA-9 — dual-gold annotation envelope + a gold-sanity gate (intake-948, intake-983; 2026-08-03)

_Via `/research-intake` Stage-2/2b. Schema-level items, so they belong here rather than in the skill;
the pipeline-ordering half lives in [`security-review-skill.md`](../completed/security-review-skill.md)._

- [x] **Adopt benchmrk's annotation envelope as the dual-gold schema.** ✅ 2026-09-16 Its `status:"invalid"` decoys give us a **negative-control axis we do not have anywhere** — intake-845 records the gap explicitly. Every current gold annotation asserts a true finding; nothing in the corpus asserts a finding that *should* be rejected, so no false-accept rate is measurable from our own data.
  - Evidence: `epyc-orchestrator` branch `sub/reviewer-artifacts-20260916` @ `e242a156`, integrated by orchestrator merge `bdf76ab3` (pushed in `753343f5`, 2026-09-16) — `orchestration/gold_annotation.schema.json` (validate_ir kind `gold_annotation`) + `src/proactive_delegation/gold_annotations.py`. `status: valid|invalid`; `invalid_reason` required iff decoy; dual gold (executable oracle + reasoning label, never both null), a conflict must carry `needs_arbitration`; model annotators force `origin: machine_generated`. `false_accept_rate()` is the negative-control axis: numerator/denominator stated, unscored decoys listed, decoys under arbitration excluded and listed. **This is the ONE dual-gold schema** — `security-review-skill.md` points here. `tests/test_gold_annotations.py` (45 tests, 13/13 mutants killed). Corpus population with real decoys is not done: no decoy rows exist yet.
- [x] **Add a gold-sanity gate to the schema contract for any machine-generated annotation or test.** ✅ 2026-09-16 Procedure, in this order: inject into the real project test file → apply the **gold** solution → run the project's **native** runner → discard and retry at higher temperature on gold-failure → *only then* consult a 3-sample self-consistency judge. **The order is the finding**: the judge reasons about generated test code that may not itself run, and it endorsed **all six** named invalid cases in the source study. Measured per-augmentation defect rate is **61.9% (n=105)** — the author's own nominated headline, and more stable than the 28.5% iterative figure concentrated in 2 of 12 repos.
  - Evidence: `src/proactive_delegation/gold_sanity.py` @ `e242a156`. `run_gate()` runs inject → apply gold → native runner, retries at the next strictly-higher temperature on gold failure, and only after a native pass takes a 3-sample majority judge. The judge is never called on an unrun or gold-failing test, and a crashed stage or an errored judge sample counts as a failure. `validate_record()` re-checks stored records (stage prefix order, judge only on the final attempt, vote/outcome consistency, no un-retried discard). The schema makes `gold_sanity.outcome: admitted` plus an executable oracle mandatory for `origin: machine_generated`. Hooks are caller-owned, so nothing runs a model here; the first live use is inference-gated.
- [x] **Ablation to preserve when implementing the retry:** ✅ 2026-09-16 retry *presence* is load-bearing (3/11 → 9/11); retry *style* is not (a neutral prompt also reaches 9/11). Do not spend design effort on the retry prompt.
  - Evidence: `run_gate` refuses a configuration with fewer than 2 temperatures or with non-increasing temperatures (`GoldSanityConfigError`), so retry presence is mandatory. `generate(temperature)` takes no prompt argument, so retry style is deliberately not a design surface. Both properties are pinned by tests (`test_config_removing_a_load_bearing_property_is_refused`, `test_generate_hook_takes_only_temperature`).
- Source code is *"available upon reasonable request"* — **not open**, so this is a pattern adoption and nothing is vendored.

#### RA-12 — immutable machine-review envelope (intake-1004; 2026-08-05)

- [x] **Bind every machine review to one immutable, version-correct envelope.** ✅ 2026-09-16 The envelope must carry the
  source/candidate content hash and version, reviewer model+quant, prompt bundle hash, pipeline and schema
  versions, output hash, validation status, and supersession link. Any source, candidate, prompt, pipeline,
  or schema change invalidates the prior decision/objections until re-run; retain the old artifact as stale
  history, never splice it into a current page. Machine-generated objections are typed `unverified_lead`
  until a current primary artifact or objective verifier resolves them and are never counted as independent
  corroboration. Add a regression fixture that combines a current source abstract with an old signed review
  body and prove that validation refuses a current binding.
  - Evidence: `epyc-orchestrator` branch `sub/reviewer-artifacts-20260916` @ `afa4e107`, integrated by orchestrator merge `bdf76ab3` (pushed in `753343f5`, 2026-09-16) — `orchestration/machine_review_envelope.schema.json` (validate_ir kind `review_envelope`) + `src/proactive_delegation/review_envelope.py`. The binding covers source/candidate hash+version, reviewer model+quant, prompt bundle hash, pipeline version and review-schema version; locators are not material. The body is SIGNED with the binding digest, so a forged envelope claiming current inputs around an old body is refused. `current_view()` returns at most one current review, keeps the rest as unchanged history and shows only the current envelope's objections; supersession chains are checked for dangling, forked and cyclic links. Objections are emitted as `unverified_lead`, `independent_corroboration` is schema-`const false`, and a primary-artifact resolution must match the CURRENT source or candidate hash. Frozen regression fixture `tests/fixtures/review_envelope/` (old review signed for abstract v1 vs current abstract v2): `tests/test_review_envelope.py`, 37 tests, 5/5 mutants killed. Integrity, not authentication: there is no signing key.

#### RA-13 — blind read-back (intake-1308, intake-1299#record; 2026-09-07)

The countermeasure to a reviewer that confirms what it expected rather than what is there. An
auditing sub-agent is given the **artifact only** and never the intent, so it *cannot* accidentally
agree with the author; it emits a description, and a human compares that description against the
original ask. Adapted from Prove2Me's mission-auditor protocol.

**Three properties are load-bearing, and all three must survive implementation** — remove any one
and this degenerates into the role-based decomposition our doctrine ratified against
(`OPERATING_CONSTRAINTS.md` → *Parallel Subagent Fan-Out*, *When NOT to fan out*): **(i)** no
authority is transferred — the auditor is forbidden to reach a verdict, it describes and a human
adjudicates; **(ii)** the split is an **information whitelist over the same task**, not a skill or
work-stage boundary, which is what makes it information-hiding rather than role decomposition;
**(iii)** blinding is re-established with a **fresh context on every artifact revision**, so the
auditor cannot be progressively contaminated across iterations.

**Citation bound, non-negotiable.** `intake-1308` is citable for **mechanism and rationale only**.
Its source repository contains **no efficacy measurement of any kind** — no hit rate, no caught-error
count, no false-agreement rate, no A/B against unblinded self-review (whole tree grepped at the
pinned commit). RA-13b exists because of that gap, and RA-13b gates RA-13a's citability.

- [ ] **RA-13a — blind read-back pilot.** HARNESS BUILT 2026-09-07 (`scripts/reviewer/blind_readback.py`, 48 tests, 9/9 mutants killed); **the N=20 pilot itself is NOT run** — it needs live model calls and is operator-gated. Row stays open for the pilot. Structural notes: the field whitelist is POSITIVE (a key is refused because it is not named, not because it was recognised as intent), `AuditorBrief` is a frozen 2-field dataclass so there is no attribute to smuggle intent through, and three independent routes to adding a verdict field each fail a test. **Known limit, not fixable structurally:** the whitelist is over field NAMES, so a caller who pastes the task statement into the artifact text still contaminates the brief — the artifact hash makes that visible after the fact, but does not prevent it. The reviewer sub-agent receives the artifact ONLY (a diff,
  a gate script, or a handoff row) plus a read-back spec — never the task statement, the request, or
  the author's intent — and emits a literal description of what the artifact does and asserts. The
  main compares that description against the original ask. Fresh context per revision. Pilot N=20
  completed edits. Authoring rules worth lifting verbatim from the source: account for every binder
  and precondition (omitting one is the worst failure mode); expand non-standard names rather than
  restating them; surface degenerate cases and conditions that could be vacuously satisfied; and if
  the artifact says less than the intent, the read-back must say less.
- [x] **RA-13b — instrument it at WRITE time.** ✅ 2026-09-07 — `scripts/reviewer/blind_readback.py`; the three counts must PARTITION the denominator (an undercounted denominator inflates every rate, so it is refused), `adjudicator` is required because a description nobody compared produced no result, and `citable_summary()` raises below n=20 naming n, the threshold and the bound. `provisional_summary()` is deliberately a different type so the two cannot be duck-typed together. Per run, record caught-discrepancy count,
  false-discrepancy count, and agreement-with-author rate. **No read-back result may be cited as
  evidence until n>=20 with a stated denominator.** Retrofitting this is impossible for the standing
  reason (write-side/read-side asymmetry), and adopting an unmeasured control and then citing it
  would reproduce exactly the warrant inflation this plane exists to prevent.
- [x] **RA-13c — read-back record format.** ✅ 2026-09-07 — missing judge model id, spec version, artifact hash or context manifest RAISES (never warns — a warned record still gets counted). The manifest pins the sha256 of the exact rendered brief, so `verify_brief_binding()` re-derives it: a run whose context carried the task produces a different hash and cannot pass. That closes the source's defect, where model-name-only records are byte-identical whether or not blinding happened. Every record carries: judge model id, spec version or
  commit, a hash of the exact artifact text shown, and a context manifest attesting the blinding
  actually held. A record lacking these is not evidence. This closes a defect in the source, which
  stores only the model name — so a captain who skipped the blinding entirely produces a
  byte-identical record — and which enforces read-back staleness as prose rather than mechanically.

#### RA-14 — Autonomous-science attempt and adjudication artifacts

**Activation trigger:** materialize RA-14 only when EPYC begins proposal-to-execution scientific experiments rather than software evaluation or maintenance work. The first campaign must implement these artifacts prospectively with `VB-AISCI-1`; no historical framework result is backfilled.

- **RA-14a:** define one versioned attempt manifest with attempt and independent-study-cluster IDs, system/model/scaffold and task/dataset revisions, seed and parent, API/compute/elapsed/human budgets, environment/dependency access, interventions, stop and terminal/audit status, and every filter/rerun/promotion decision. Report per-task and per-system denominators and refuse pooled rates over heterogeneous endpoints. Sources: intake-1607#record, intake-1609#record, intake-1610#record, intake-1704#record, intake-1705#record, intake-1706#record.
- **RA-14b:** define an immutable self-hashed scientific-evaluation receipt binding inputs, trajectory, commands and tool I/O, environment/runtime/access, intermediate scientific objects, output/code digests, grader inputs, rubric, automated judge, human decision, and final disposition. Preserve failed, censored, and unaudited attempts; every empirical manuscript claim points to execution and verification evidence. Sources: intake-1653#record, intake-1675#record, intake-1707#record.
- **RA-14c:** define a scientific-adjudication envelope that records engineering completion, executable validity, domain validity, manuscript assessment, and venue decision separately. Bind preregistered task/metric, reviewer expertise and independence/blinding, original-author involvement, task-selection degrees of freedom, interventions, manuscript lifecycle, and artifact availability class. Sources: intake-780#record, intake-1705#record, intake-1706#record.

## Track: reviewer-model-ablations
<!-- gate: REV-02#glm52-reviewer-capability-gates -->

> Folded from `handoffs/active/reviewer-model-ablations.md` @ `28b488861d1f` on 2026-11-03 (BRF-T7-F15, route 1b, operator D1/D5; retired row REV-07 → REV-02). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reviewer Control Plane — Registry-Driven Model-Role Ablation Tournament (H5)

**Status**: active — M3 "compared" milestone; GATED on H4 instrument (P-REV-1) + H6 arms + operator bench windows
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: benchmark_methodology, agent_architecture, routing_intelligence
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-calibration-accounting.md`](reviewer-control-plane.md#track-reviewer-calibration-accounting) (the instrument), [`glm52-reviewer-capability-gates.md`](reviewer-control-plane.md#track-glm52-reviewer-capability-gates) (A4 arm gates), [`autopilot-control-plane-integration.md`](../completed/autopilot-control-plane-integration.md) (screening-tier driver), [`mi210-big-model-and-acceleration-roadmap.md`](../completed/mi210-serving-program.md#track-mi210-big-model-and-acceleration-roadmap) (GPU arms), [`architect-model-selection-bench.md`](model-evaluation-queue.md) (sibling — the architect-role model-selection bench, same objective-scored-only discipline)
**Repo**: `epyc-orchestrator` + `epyc-inference-research`

#### Objective

Answer the model-role question empirically — which (architect, reviewer, grading-model) assignment maximizes calibrated review value per token — via a **registry-driven staged tournament** over the ~240-model registry, not a fixed condition table (operator 2026-07-16: the report's 7-row matrix is an example only).

#### Thesis

Three stages: (1) **pool generation** — architect × reviewer × grader pools drawn from `model_registry.yaml` by capability/speed tier with pruning rules (RAM/VRAM fit, t/s floor, quality floor from existing benches, cross-family preference; staged candidates include Hy3-295B-IQ1M, MiniMax-M2.7, Qwen3-Next-80B, gemma-4-31B, and Qwen3.6-27B; **DeepSeek-V4-Flash is excluded from local testing by operator direction 2026-08-26**, and **Qwen3.5-397B is no longer stageable at all** — no local weights; Bonsai tier-C is opt-in/reopen-only and excluded from default staging until a named quality/protocol fix clears the strict-output blocker); (2) **screening** — cheap small-n sweeps over many pairings, autopilot-driven (H8) on a corpus-v1 subset via eval-tower T0/T1; (3) **confirmation** — full paired N≥100 P-REV-1 runs only for Pareto-promising pairs. Family-preference/collusion is **measured as a covariate, not assumed** (direct measurements found it weak, −0.9..+3.5pp — intake-837; the stronger prior lives in Panickssery 2404.13076, unverified locally).

#### Prioritized Task List

**2026-07-19 operator priority — fast-track anchor comparison on the now-decision-grade C-CRAB corpus.** The mechanical accept-oracle relabel (`GC-shadow-repair4b.2c`, [`glm52-reviewer-capability-gates.md`](reviewer-control-plane.md#track-glm52-reviewer-capability-gates)) made the C-CRAB P-REV-1 slice decision-grade, and **GLM-5.2-IQ2 (arm A4) FAILED admission on it** — `FA 41.7%`, `FR 25.0%`, **AUC 0.509 (≈ random)**, 2026-07-19. Before the full tournament, run the cheap high-value anchor cut on that SAME corpus. **Hard requirement (operator): every reviewer arm below runs MI210-hosted (GPU: `-ngl 99 -dev ROCm0`), NOT CPU — grammar/schema on.** The whole point is a *fast* slate we can iterate; GLM ran CPU-IQ2 at ~2.5 t/s, these run at 40–100 t/s on the card. Three distinct arms:

- [x] **RM-2.fast — Qwen3.6-27B reviewer arm on the decision-grade C-CRAB P-REV-1 corpus** (operator-requested 2026-07-19): ran Qwen3.6-27B dense Q8 on MI210 through the same P-REV-1 runner/prompt/schema family and identical `48`-row slice. Result: `FA 54.2%`, `FR 16.7%`, `AUC 0.503`, `ECE 0.316`, parse `0.0%`, median row wall `6.2s`; artifact `epyc-inference-research/data/reviewer_model_ablations/rm2-fast-qwen36-27b-q8-ccrab-p-rev1-20260719T162109Z`; summary `epyc-inference-research/docs/data/reviewer_model_ablations_rm2_fast_ccrab_p_rev1_20260719.md`. Verdict: faster, but not better than GLM; over-approves and remains random by AUC, so this does **not** decouple v7. ✅ 2026-07-19

- [x] **RM-2.fast-b — Harnessed-small-model reviewer arms vs the big quantized model** (operator-requested 2026-07-19): the strategic question is *large quantized model (GLM-5.2-IQ2, FAILED) vs efficiently-harnessed small models*. On the SAME decision-grade C-CRAB slice + runner, added these reviewer arms alongside RM-2.fast's plain 27B and reported matched `FA/FR/AUC/ECE` vs GLM's `41.7/25.0/0.509`: ✅ 2026-07-19
  - **(a) Qwable standalone** (35B-A3B IQ4_XS, ~90–100 t/s MI210 — the strongest cheap local reasoner). **This is the primary harnessed-small candidate:** it historically **dominated** the Qwable→beneficiary scaffold on GPQA (77% vs 73%, 2026-07-05, [`../completed/gpu-cot-scaffold-sidecar.md`](../completed/gpu-cot-scaffold-sidecar.md)).
  - **(b) Qwen3.6-27B + Qwable CoT scaffold** (the explicit coupling the operator asked about). **Caveat from past evidence:** the Qwable→gemma-26B scaffold was FALSIFIED (net −3, quality loss) because the beneficiary was already as strong a reasoner as Qwable → expect **Qwable-standalone ≥ 27B+scaffold** unless patch-review behaves differently from GPQA. Test it to confirm on this task, not assume.
  - **Outcome:** Qwable standalone was fast but failed (`FA 54.2%`, `FR 45.8%`, `AUC 0.438`, `ECE 0.441`, median `2.1s`; artifact `data/reviewer_model_ablations/rm2-fast-b-qwable-iq4xs-ccrab-p-rev1-20260719T162712Z`). Qwen+Qwable scaffold improved the FA/AUC shape (`FA 33.3%`, `FR 41.7%`, `AUC 0.659`, `ECE 0.315`, median `6.5s`; artifact `data/reviewer_model_ablations/rm2-fast-b-qwen36-27b-q8-plus-qwable-iq4xs-scaffold-ccrab-p-rev1-20260719T162958Z`) but is still not role-ready because FR and raw errors exceed GLM. Decision-grade conclusion: no tested small/fast arm cleanly beats GLM; keep reviewer choice open and pursue A3/external/SWE or a scaffold repair, not blind v7 decoupling.

**2026-07-19 GLM disposition consumed.** H6/GC-external-1e now routes production
patch-review selection away from GLM on the current policy: GLM failed C-CRAB hard negatives,
external JudgeBench/SWE evidence is positive but partial, and RM-2.fast did not find a clean
small replacement. The next H5 progress is therefore not another unchanged GLM/Qwable/Qwen
rerun; it is the remaining anchor/floor set and the screening protocol.

- [x] **RM-1 — Pool-generation script** ✅ 2026-07-17 (`scripts/analysis/reviewer_pool_gen.py`; live run: 157 roles → pools 68/77/65 → 5,236 pairings; anchors A0/A1/A3/A4 forced-present, A4 cross-family-flagged; deterministic w/ registry+config sha256 provenance; 19 tests) with pruning rules + provenance (registry rev, pruning config hash); emit the candidate pairing list.
- [x] **RM-1a — Bonsai Q1 default-staging stop**: `epyc-orchestrator` commit `d30593a2` removes Bonsai Q1_0 from `reviewer_pool_gen` `DEFAULT_STAGED_KEYS`; Bonsai remains opt-in/reopen-only until a named quality/protocol fix clears the strict-output blocker. ✅ 2026-07-19
- [ ] **RM-2 — Anchor arms (guaranteed confirmation-tier)**: A0 gates-only (objective-verifier floor); A1 self-review (status quo alias); A3 same-family GPU heavyweight (Qwen3.8-27B resident, grammar mandatory); A4 cross-family DS41-1017 or Flash-Next CPU (target); A4g +hot-expert offload (retired under the GLM-5.2 KILL); Ref external judge-of-judge (approved bounded: pinned model-id+date, ~100 sampled decisions, budget-capped). (re-scoped 2026-11-03 from A3 122B-IQ2 and A4 GLM-5.2-IQ2: deleted/dropped; now A3 Qwen3.8-27B (GPU) and A4 DS41-1017 or Flash-Next)
  - [x] **RM-2.next — Complete non-GLM anchors after GC-external-1e**: A0/A1 floor extraction and A3 same-family GPU heavyweight are complete on the decision-grade C-CRAB slice. A4 is recorded failed on the current policy; A4g is obsolete: the operator retired GLM-5.2 and deleted its weights (OP-8 KILL; `epyc-orchestrator/orchestration/model_registry.yaml`), so do not rerun it without an explicit reversal. ✅ 2026-07-19
    - [x] **A0 objective-verifier floor materialized on the matched C-CRAB P-REV-1 slice**: no-inference oracle ledger over the same `48` row ids (24 hard accepts + 24 hard negatives) scored `FA 0.0%`, `FR 0.0%`, `ECE 0.000`, `Brier 0.000`, parse `0.0%`; AUC is undefined because all decisions are correct. Artifact: `epyc-inference-research/data/reviewer_model_ablations/rm2-next-a0-objective-floor-ccrab-p-rev1-20260719T205208Z`; report: `epyc-inference-research/docs/data/reviewer_model_ablations_rm2_next_ccrab_p_rev1_20260719.md`. ✅ 2026-07-19
    - [x] **A3 same-family GPU heavyweight ran on MI210**: Qwen3.5-122B-A10B `UD-IQ2_M`, `-ngl 99 -dev ROCm0`, same P-REV-1 runner/prompt/schema and matched C-CRAB slice. Result: `FA 12.5%` (`3/24`), `FR 58.3%` (`14/24`), `AUC 0.513`, `ECE 0.302`, `Brier 0.319`, parse `0.0%`, median row wall `5.5s`, server decode `43.89 t/s`. This materially reduces false accepts versus GLM but rejects too many good patches, so it is not a production reviewer replacement. Artifact: `epyc-inference-research/data/reviewer_model_ablations/rm2-next-a3-qwen35-122b-iq2-ccrab-p-rev1-20260719T204845Z`. ✅ 2026-07-19
    - [x] **A1 status-quo self-review live run**: Qwen3.5-122B `UD-Q4_K_M` CPU self-review ran through the same P-REV-1 runner/prompt/schema and matched C-CRAB slice. Result: `FA 45.8%` (`11/24`), `FR 41.7%` (`10/24`), `AUC 0.463`, `ECE 0.385`, `Brier 0.397`, parse `0.0%`, median row wall `41.4s`, total wall `2164.234s`. Verdict: parse-clean but worse than GLM and not a production reviewer replacement. Artifact `epyc-inference-research/data/reviewer_model_ablations/rm2-next-a1-architect-statusquo-ccrab-p-rev1-20260719T210513Z`. ✅ 2026-07-19
- [ ] **RM-3 — Screening-tier protocol**: small-n, per-pairing FA/FR/CR estimates with wide CIs; promotion rule to confirmation tier (Pareto on quality-vs-cost); driven by the H8 autopilot action, respecting no-concurrent-inference + placement-queue-not-/chat discipline.
  - [x] **RM-3a — Matched C-CRAB P-REV-1 row-id-bound dry-run queue ✅ 2026-07-19**: `epyc-orchestrator` runner now accepts `--row-ids`, records row-id filter provenance in dry-run queues, filters live execution to that exact allowlist, and applies CLI `--max-pairings` after priority ordering. Focused runner tests passed (`32`). Artifact: `epyc-orchestrator/orchestration/reports/rm3_ccrab_p_rev1_screening_dryrun_20260719T215914Z/` with `64` priority-resolved jobs from `6525` pairings, `per_pairing_n=12`, `row_id_filter_n=48`, placement-queue transport, and no inference.
  - [x] **RM-3b — Live screening bridge**: `epyc-orchestrator` now routes `screening_tier_driver` live execution (only with `dry_run=false` + `AUTOPILOT_SCREENING_TIER_INFERENCE=1`) through `screening_tier_runner.run_screening_tier`; the runner's default live probe reuses the P-REV-1 direct corpus prompt, binary ReviewDecision JSON schema, parser, forced-direct `/chat` path, and placement-queue priority/workload stamps instead of the old free-text approve/reject prompt. Focused validation passed (`190` tests + ruff + py_compile). ✅ 2026-07-19
  - [x] **RM-3c — First live screening batch ✅ 2026-07-19**: ran the first routable live-stack subset from the `64` priority-resolved jobs using the RM-3 live bridge, same matched C-CRAB P-REV-1 row-id allowlist (`48` rows), `n=12` per pairing, forced direct `/chat` with background/eval-batch stamps, and the binary ReviewDecision schema. Scoped stack: API `8000` + frontdoor full server `8070` serving `frontdoor` and `coder_escalation` (`Qwen3.6-35B-A3B-MTP-Q8_0`, CPU-only stack launch, `draft-mtp`); AutoPilot was not restarted. Result leaderboard: `frontdoor` FA `16.7%`, FR `50.0%`, consistency `66.7%`, mean row latency `26.8s`; `coder_escalation` FA `25.0%`, FR `75.0%`, consistency `58.3%`, mean row latency `24.1s`. Artifact: `epyc-orchestrator/orchestration/reports/rm3_ccrab_p_rev1_screening_live_frontdoor_slice_20260719T221931Z/`. Verdict: live forced-direct P-REV screening works mechanically, but this does **not** prove the stricter placement-queue-not-/chat discipline, and neither frontdoor-served role is a confirmation-tier candidate from this observation-grade slice.
  - [x] **RM-3d — Transport metadata repair ✅ 2026-07-19**: `screening_tier_runner.py` now keeps dry-run/planned jobs as `placement_queue` while live execution rows explicitly record `transport=forced_direct_chat`, `planned_transport=placement_queue`, `force_mode=direct`, and `uses_chat_endpoint=true`. This prevents RM-3c-style forced-direct observations from being misread as true placement-queue evidence. Focused validation: `uv run pytest -q tests/test_screening_tier_runner.py` (`33 passed`) plus `python3 -m py_compile scripts/autopilot/screening_tier_runner.py`. True placement-queue execution remains a stronger future transport gate, but metadata can no longer overclaim it.
- [ ] **RM-4 — Confirmation-tier protocol**: fully paired (same tasks/prompts/grammar/stop/verifier budget), N≥100/arm, paired flips via `sequential_verdict.quality_trial_statistic`, Holm across metric families; per-domain reporting.
- [ ] **RM-5 — Bias-robustness probe set**: the 6 content-bias injections (authority, self-declared correctness, renaming, reverse-authority, misleading-task, illusory complexity) as a held-out probe → per-reviewer **robustness rate** as a selection axis (small judges more fragile); blinding/randomization controls baked into the harness (sanitized packages, no reference-comparison mode without swap-augmentation).
  - ⏳ PARTIAL 2026-09-16 (sub-reviewer): the zero-inference half is built, and the box stays open for the per-reviewer run, which is RM-4 protocol and inference-gated. `epyc-orchestrator` branch `sub/reviewer-artifacts-20260916` @ `9a00184b` (merged as orchestrator `bdf76ab3`), `src/proactive_delegation/bias_probes.py`. It holds the 6 injections with declared bias directions, placed only where a flip is harmful (accept-biased on gold-bad rows, reverse-authority on gold-good rows). Every injection is proven to survive `sanitize_candidate_package`. Held-out overlap is refused. Kind, position and presentation order are seeded. A manifest hash covers the templates, and `require_swap_augmented` guards pairwise mode. `score_robustness` reports robustness and harmful-flip rates with a stated denominator, excludes and counts abstentions, and refuses missing decisions. `tests/test_bias_probes.py`: 19 tests, 9/9 mutants killed. The next step is to pick the held-out slice of `nearmiss-v1`, disjoint from the RM-3 C-CRAB allowlist, and run it inside an RM-4 bench window.
- [ ] **RM-6 — RA-8 field-order A/B** (evidence-first vs verdict-first GBNF) on the leading arm — opposing hypotheses on record (intake-836 vs intake-837).
- [ ] **RM-7 — With-vs-without verifier-request access** ablation on the winning pair (isolates contextual verification vs second-opinion effect).
- **[declined: ws58 2026-11-03 content-review: merged into RM-4 as its reporting step]** **RM-8 — Report + registry annotation**: winners' calibration profiles into model registry `measured:` fields; publish claims in P-REV-1 grammar only.
- [x] ~~**RM-9 — (deferred, LOW) A5 reviewer-as-architect** (GLM-5.2 solo) — only after A4 results justify it.~~ (closed 2026-10-29 audit: OBSOLETE → A5 uses GLM-5.2 solo; GLM-5.2-UD-IQ2_M is in the deprecated_models graveyard (model_registry.yaml:13063))
- **[declined: ws58 2026-11-03 content-review: curiosity; no reviewer decision depends on it]** **RM-10 — Run a mindfulness-only metacognitive prompt ablation, not a superalignment test.** Add three
  matched prompt arms to the confirmation protocol on the same leading reviewer configuration: the current
  framing-neutral prompt, a matched-length neutral reflection/self-check prompt, and a mindfulness-only
  present-attention/self-monitoring prompt. Hold candidate rows, grammar, field order, token budget, sampling,
  verifier access, and seeds fixed; score with objective/dual-gold outcomes plus a blinded cross-family or
  human-owned sample, reporting FA, FR, calibration, consistency, latency, and style/rubric leakage. Exclude
  emptiness, non-duality, moral-goal substitution, constitutional relaxation, and any instruction that can
  weaken MEASUREMENT.md, operator authority, safety rules, or frozen-kernel constraints. Ignore the source's
  current effect sizes and do not describe any result as superalignment evidence.
- [ ] **RM-11 — Separate the two competing explanations for our near-chance reviewer discrimination
  before concluding anything about a capability floor.** We currently read the null result as
  *capability* (our reviewers are too weak). intake-1168 supplies a *configuration* explanation that
  predicts the same null for a different reason, and the two have never been separated. Both sub-rows
  are cheap, reuse existing harnesses, and require no training. All numbers stay observations until
  RC-6a merges. [intake-1168] [intake-875]
  - **[declined: ws58 2026-11-03 content-review: duplicate — eval-tower EV-6c (non-Qwen judge) measures it]** **RM-11a — Cross-family vs same-family verifier gain.** Our reviewers are the **same family**
    as our generators, and Qwen3-family reasoning models already self-verify spontaneously in ~96% of
    outputs (DeepSeek 73%; Llama3/Qwen2.5 only 1–2%). intake-1168 predicts near-zero gain in exactly
    that configuration *regardless of verifier capability*. Run the existing selector harness
    (`epyc-inference-research/scripts/benchmark/qwable_verifier_selector_runner.py:509-556`) with a
    family-dissimilar verifier against the current same-family arm, holding pool, prompt, budget and
    seeds fixed. **Report verifier gain (precision − solver accuracy) alongside accuracy** — intake-1168
    shows accuracy is a misleading proxy for test-time usefulness. Caveat to carry: their
    self-verification rates come from a keyword scan, so treat that mechanism as a hypothesis, not an
    established cause; and their cross-family recommendation holds only for **unoptimised** solver
    distributions (intake-875 shows it fails under optimisation pressure).
    - [x] **RM-11a-SOURCE — remove the selector's duplicate code executor.** ✅ 2026-10-30 —
      research main `f0737320a54f6454a67f957bf1b6eb5ec204149d` delegates every code-execution
      candidate to the existing governed B7 scorer. The retired branch ignored `entry_point_cases`,
      synthesized zero-argument assertions from expected text, and bypassed oracle validation and
      private execution. Twenty-two selector tests pass against orchestrator
      `65b2b0e66b4da5ff718141bee1f87457b2b36149`; all eight new behavioral controls fail against
      the untouched selector. The measured RM-11/RM-11a study remains open: no inference,
      historical rescoring, runtime adoption, or model-quality conclusion. Future arms must pin
      both selector and governed-scorer bytes and preserve the instrument boundary.
      [Receipt](../../artifacts/compute/refactor-rm11-selector-source-closure-20261030.json).
      [no-belief: source and deterministic test closure only]
  - **[declined: ws58 2026-11-03 content-review: duplicate — eval-tower's offline commit-first judge A/B measures the solve-accuracy threshold]** **RM-11b — Measure reviewer solve-accuracy** — the intake-875 Corollary 1 anchoring test, which
    we have never run. One offline pass on the C-CRAB P-REV-1 slice: have each reviewer arm *solve* the
    patch-review problems independently, and compare against its FPR-implied threshold. GLM-5.2's
    verdicts are certified anchored iff solve-accuracy > **0.583**; Qwen3.6-27B's iff > **0.458**. This
    converts the reviewer-calibration debate from prose into a certified structural claim, **and it is
    the precondition for the de-anchoring rule in `eval-tower-verification.md`** — below the threshold,
    commit-first *degrades* a judge rather than helping it. (re-scoped 2026-11-03 from reviewer arms GLM-5.2 (dropped) and Qwen3.6-27B (deleted): now Qwen3.8-27B and DS41-1017; the 0.583/0.458 FPR thresholds must be recomputed)
  - **Premise correction to record with this row.** Our frequently-cited reviewer AUC of 0.503–0.509 is
    ROC-AUC of *self-reported confidence* against decision correctness
    (`repos/epyc-orchestrator/tests/test_calibration_report.py:51`). It is **not** the discrimination
    statistic (TPR − FPR) that intake-875 and intake-1168 use. On that statistic the same arms score
    **+0.29 to +0.33**, which places them in the pre-hack anchored-plausibility channel rather than at
    chance. The two numbers answer different questions and should stop being used interchangeably.

#### Dependency Graph

```text
H4 P-REV-1 + corpus v1 → RM-1 → RM-3a dry-run queue ✅ → RM-3b live screening bridge ✅ → RM-3c first live batch ✅ → RM-3d metadata repair ✅ → RM-4 confirmation → RM-7 → RM-8
RM-2 anchors: A0/A1/A3/A4 are closed evidence; A4g is retired by the operator GLM-5.2 KILL; Ref needs an operator budget/window.
RM-5, RM-6 fold into RM-4 protocol. Operator bench windows gate all inference-heavy runs.
RM-11a/RM-11b are independent of the RM-1→RM-4 screening chain (they reuse the existing selector harness and the C-CRAB slice). RM-11b gates the de-anchoring rule in eval-tower-verification.md and is a precondition for EV-15 being worth using.
```

#### Cross-Cutting Concerns

1. **Single-card contention** — A3/A4g arms use the MI210; sequence behind the parallel session's admission smokes + the operator's GPU bets 1→4 ordering.
2. **Latency accounting** — parallel-reviewer wall-clock models as SUM not MAX on this host; per-arm cost reported alongside quality (keeps "stronger" arms honest).
3. **Saturated-suite hazard** — screening on journal-derived items must include near-miss/ambiguous rows, or arms will tie at ceiling (the corpus exists precisely to avoid this).

#### Key Files / Surfaces

- `epyc-inference-research/orchestration/model_registry.yaml` (pool source; `measured:` target)
- H4 ledger + `reviewer_calibration_report.py`; `src/autopilot_core/sequential_verdict.py`
- eval tower T0/T1 (screening); H8 autopilot action (driver); `scripts/autopilot/screening_tier_runner.py`

#### Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; screening leaderboards + confirmation results recorded here; winners update H0 + registry; NO claim leaves this handoff without P-REV-1 citation; bench windows requested via OP bundle.

#### Evidence Base (intake)

intake-837/838 bias probes + family-preference-as-covariate · intake-836 big-model FR priors + IQ2 quant caveat · intake-834 grading-model insensitivity (2.4pp) · intake-846 fidelity-over-fan-out · audit doc 2026-07-16 · IQ2==Q4 parity (n=212, Δ0.0pp; workspace-root iq2_parity_results.jsonl).
