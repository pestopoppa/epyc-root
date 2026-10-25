# Stage-3 plan: TensorFold 1.1.4 intake (prepared 2026-10-24; awaiting operator approval)

This plan is **prepared, not applied**. The owning sessions apply it at Stage 4, after operator approval:
- the research-intake session applies the intake-1924 edit;
- ak-ds41-main applies the AKX handoff lines;
- each campaign owner writes its AK store inbox note.

The AK operator launch hold (2026-10-24, "DO NOT LAUNCH AUTOKERNEL") gates every AK run in it. It does not gate
filing the text.

**Inputs.**
- `REPORT` content: delivered in the subagent hand-back. The harness refused a `.md` report file from a subagent.
- `INTAKE-ENTRIES-PROPOSED.yaml`.
- `inbox-drafts/` (three AK notes).
- `SOURCES.md`.

**Stage-2 gate.** Closed. Wave 1 dived the v1.1.4 diff and wave 2 the kernel contract plus `ggml.cu`. The surfaced
sources not dived were declined under the 2-wave cap and are recorded in intake-1924 `dive_corrections`. A per-claim
second reader found two locator/scope defects; both were fixed, and four claims gained second anchors.

**Not run** (the hard rules allow no python): `validate_intake.sh --plan-file … --session-file …` and
`index_state.py --check`. The applying session owes both.

## Opportunity scan (source-first, before IDs)

| Scan | Verified passage | Current consumer read | Disposition | Ledger |
|---|---|---|---|---|
| S1 | #1219 grid swap, `a56d0ce2fa` L10 | `fattn-common.cuh:1176-1178` grid (y = KV chunks before z = heads) @ ffc1bac82 | actionable | TF114-1 |
| S2 | #1080/#1168 `F8` in-tile widening | `fattn-common.cuh:1022-1041` whole-view to-f16 convert; rocprof B kv_convert 8 ms | actionable | TF114-2 |
| S3 | #1168 L13/L20/L22 (query heads as m16 tile lines, tile read once per round, row-invariant) | `fattn-wmma-f16.cu:100-103` (no GQA packing); `fattn.cu:113-150` (CUDA mma `ncols2` exists) | actionable | TF114-3 |
| S4 | `e475e90fb9` drafter vocabulary spans | DFlash2 drafter head in `src/models/dflash.cpp` (shape not read) | actionable, low | TF114-4 |
| S5 | #1138, #1079 L42, `11e9b4db18` | 27B inbox note 10 H3/H4/H7/H13 | covered (evidence only) | TF114-5 |
| S6 | `b9b23ec9ca`, `11e9b4db18`, `e72a34ae38` | Q38FN note 62: CPY 9.4% feeding matmuls; norm-to-q8 KEEP | actionable | TF114-6 |
| S7 | #1217 `d0d179497e`, `eb0d391600` | `ops.cpp:11134-11154` (in-kernel GDN snapshots); `qwen4exp-fused.cpp` | actionable, conditional | TF114-7 |
| S8 | `aa6fbd8903` blocked DSA scan | DS41-C123 (`deepseek-v41-flash-evaluation.md:1211-1224`) | actionable, record-only | TF114-8 |
| S9 | `docs/kernel-contract.md` L4-5, gates 1-5 | AK gate: H2 RI self-test, AKX-ALL-29.5 guard bands (opt-in), 29.4 | actionable | TF114-9 |
| S10 | #1069 L5, #1155 | `server-context.cpp:500, 3143, 3193` | declined (already integrated) | TF114-D1 |
| S11 | `69e491cbc5` L9 (4× int8 rate on 5090) | note 10 §0 (CDNA2 int8 = f16 rate); q8_1 MMQ / VNNI | declined (already integrated) | TF114-D2 |
| S12 | #1195 PLE pool | ggml persistent threadpool `get_rows` | declined | TF114-D3 |
| S13 | `0c73b158de` routed + shared pair | Q38FN note 62 seed 3 (0% recoverable) | declined | TF114-D4 |
| S14 | #1219 on CPU | AKX-ALL-LB3 (a); discarded `akm-cpu-fa-query-major-row-schedule` | covered | TF114-D5 |
| S15 | `14ae735699` min-of-reps cost table | AK runtime-arm tables (H6, none built) | context-only | TF114-D6 |
| S16 | #1080 4096-row chunks | KVU-16f/g, AKX-ALL-13 (`-b/-ub`) | covered | TF114-D7 |
| S17 | Gemma 4 / Drama / speech / serving | not in the DS41/Q38FN/27B lanes | declined for AK | TF114-D8 |
| S18 | `ggml.cu` L1 (bf16 exact-integer, weights as A) | note 10 §3.2 | declined | TF114-D9 |
| S19 | intake-1924 record vs v1.1.4 | `research/intake_index.yaml` L246326-246390 | actionable | TF114-10 |

## Work packets

| Packet | Action | Owner | Execution conditions |
|---|---|---|---|
| P1 | 27B MI210 long-context FA seeds G2, G3, G1 and G4, plus evidence for H3/H4/H7/H8, as one inbox note. Then an arbiter rocprof probe (no build) that orders them | `handoffs/active/autokernel-all-devices-all-dimensions.md` (AKX-ALL-30, AKX-ALL-30a) | Filing: after approval. Inbox write: by the campaign owner, after the hold lifts. Arbiter: MI210 window grant (GPU arming still asks). Authoring: after AKX-ALL-19 (G3) is admitted and the FA owner confirms (note 10 §4) |
| P2 | CPU seeds Q1 and Q2 (Q38FN) and D1 (DS41-1017, record-only), as two inbox notes | same owner (AKX-ALL-30) | After approval and the hold lift. D1 is actionable only on the AKX-ALL-12 depth surface |
| P3 | AK numerics gate: non-finite-class gate and integer-accumulator (fp32-sum) gate, each with a planted control that must go red, in the default CPU and HIP gate chain | same owner (AKX-ALL-31); INF-73 loop owner reviews the merge | No inference compute; a research branch under a build-role claim. Not blocked by the launch hold (harness code, not a run) |
| P4 | intake-1924 re-encounter, Stage-2 dive fields and corrections (`INTAKE-ENTRIES-PROPOSED.yaml`) | research-intake session | After approval; text edit, `validate_intake.sh` exit 0, then `vidya sync` |
| K1 | Knowledge-only: C10 min-of-reps applies to cost-table estimators only; C3 chunking is owned by KVU-16f/g and AKX-ALL-13 | none (recorded in intake-1924 `dive_corrections`) | — |

Concurrency:
- P3 and P4 are independent of everything.
- P1's arbiter precedes P1's authoring; P2 is independent of P1.
- G1 follows G2 and G3 (it reuses G3's loader, and its value is measured after G2).

Minimum-rigor controls, P1 arbiter (an empirical probe):
1. **Baseline**: the champion incumbent binary, digest and ggml linkage proven (`verify_ggml_linkage.sh`), and its mtime
   checked against the source.
2. **Predeclared rule**: FA `FETCH_SIZE` ≥ 3× the f16 K+V view means G2 first; ≈ 1× means re-rank. Convert ≥ 4 ms means
   G3 stands.
3. **Replication**: two samples per cell (two-sample persistence).
4. **Observation window**: rocprof samples *during* FA dispatches at 1×80k, never after.
5. **Residency proof**: non-zero VRAM sampled during the run, and the KFD process count.
6. **Provenance**: argv, KV type, n-max, the rocWMMA build flag and the live FA kernel symbol, recorded in the receipt.

P2 and P3 controls are carried by the AK keep gate (P2: paired ABA, noise-floor unit, predeclared keep threshold,
correctness class per seed). P3 is deterministic infrastructure: its replacement conformance check is "each planted
control goes red and the incumbent passes".

## Handoff edits (append to `handoffs/active/autokernel-all-devices-all-dimensions.md`, after the AKX-ALL-29.x block, as a new subsection)

```markdown
### P6: TensorFold 1.1.4 seeds (research intake 2026-10-24)

- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).** The campaign owners write them (single-writer stores) after the operator lifts the 2026-10-24 launch hold: `ak-27b-gpu-verify-20261004/store/inbox/60-tensorfold-114-fa-at-depth-seeds-20261024.md` (G2 `akg-fa-gqa-adjacent-grid-order`, G3 `akg-fa-q8-kv-tile-widen-no-convert`, G1 `akg-fa-gqa-rows-packed-mfma-tile`, G4 `akg-dflash2-drafter-vocab-span-head`, plus evidence for H3/H4/H7/H8), `ak-q38fn-cpu-decode-20261003/store/inbox/65-tensorfold-114-seeds-20261024.md` (Q1 `akm-q38fn-cpy-producer-writes-consumer-layout`, Q2 `akm-q38fn-gdn-prologue-into-chain`) and `ak-ds41-1017-cpu-decode-20261021/store/inbox/32-tensorfold-114-seeds-20261024.md` (D1 `akm-ds41-1017-dsa-indexer-fused-scan`, record-only), copied byte-exact from `/mnt/raid0/llm/tmp/tensorfold-114-review-20261024/inbox-drafts/`. The GPU seeds are authored only on the AKX-ALL-19 (G3) route, with the FA owner's confirmation (note 10 §4). Done when the three notes are in the stores with their sha256 recorded here and the next planner context lists them.
  - [ ] **AKX-ALL-30a — arbiter probe before authoring the GPU FA seeds.** On the champion at 1×80k, N=8 verify, rocprof the FA dispatches (`FETCH_SIZE`, `TCC_HIT`/`TCC_MISS`) and the q8_0→f16 convert dispatches, two samples, with the residency proof (VRAM sampled during the run, KFD count) and the live FA kernel symbol recorded. Rule (predeclared): FA fetch ≥ 3× the f16 K+V view means G2 first, then G1; ≈ 1× means re-rank G1 and G2 before authoring; convert ≥ 4 ms means G3 stands. Needs a granted MI210 window. Done when the verdict JSON names the ordering.
- [ ] **AKX-ALL-31 — planted-control numerics gates for AK candidates (intake-1924#record; TensorFold `docs/kernel-contract.md` gates 1 and 4).** Add to the default CPU and HIP candidate gate chain: (1) a non-finite gate (NaN, +Inf and −Inf planted at known input rows; every output's class must equal a float64 reference, tolerance-free) and (2) an fp32-accumulator gate (integer inputs whose partial sums stay below 2^24, so fp32 is exact in any order; the harness first proves that fp16 and bf16 replays miss by ≥100× the bound). Each gate gets a planted control (a NaN-dropping `fmax` max; a half-precision dot) that must go red, and a run where a control passes fails. Reuse AKX-ALL-29.5's guard bands and the H2 RI self-test, not new machinery. The INF-73 loop owner reviews the merge. Done when both gates run by default on both legs, both controls are red and the champion incumbent passes.
```

No domain-index row changes. INF-81 already owns this handoff; its next action stays. No new stub.

## Complete recommendation mapping

| Ledger row | Source or review | Retained recommendation | Terminal plan mapping |
|---|---|---|---|
| TF114-1 | #1219 / `a56d0ce2fa` L10 | Seed G2 + arbiter | P1 / AKX-ALL-30, AKX-ALL-30a |
| TF114-2 | #1080 / #1168 F8 staging | Seed G3 | P1 / AKX-ALL-30 |
| TF114-3 | #1168 L13, L20, L22 | Seed G1 | P1 / AKX-ALL-30 |
| TF114-4 | `e475e90fb9` | Seed G4 | P1 / AKX-ALL-30 |
| TF114-5 | #1138, #1079 L42, `11e9b4db18` | Evidence for H3/H4/H7/H8 in the GPU note | P1 / AKX-ALL-30 |
| TF114-6 | `b9b23ec9ca`, `11e9b4db18`, `e72a34ae38` | Seed Q1 | P2 / AKX-ALL-30 |
| TF114-7 | `d0d179497e`, `eb0d391600` | Seed Q2 (conditional) | P2 / AKX-ALL-30 |
| TF114-8 | `aa6fbd8903` | Seed D1 (record-only) | P2 / AKX-ALL-30 |
| TF114-9 | `kernel-contract.md` L4-5 | Planted-control numerics gates | P3 / AKX-ALL-31 |
| TF114-10 | intake-1924 vs v1.1.4 | Entry dive fields and corrections | P4 / entry_updates |
| TF114-D1 | #1069, #1155 | Shared verify / batched drafting | decline: already integrated in llama-server |
| TF114-D2 | `69e491cbc5` | int8 prompt GEMM | decline: already integrated; CDNA2 int8 = f16 rate |
| TF114-D3 | #1195 | PLE worker pool | decline: no thread-spawn defect in ggml |
| TF114-D4 | `0c73b158de` | Routed + shared pairing for DS41 | decline: Q38FN analog 0% recoverable; reopen only if a DS41-1017 node profile shows shared-expert barrier cost ≥1% |
| TF114-D5 | #1219 on CPU | CPU FA reorder | decline: owned by the existing CPU long-context lane; a reorder keep was discarded on replicate |
| TF114-D6 | `14ae735699` | Cost-table min-of-reps | K1 knowledge-only |
| TF114-D7 | #1080 | Long-prompt chunking | K1 knowledge-only (owned by the KV-pool and runtime-arm tasks) |
| TF114-D8 | Gemma 4 / Drama / speech | Out of AK lanes | decline: operator lane rule 2026-10-06 |
| TF114-D9 | `ggml.cu` L1 | bf16 exact-integer MFMA route | decline: settled by note 10 §3.2 |

## Steering reconciliation

The coordinator relayed both of these rows as operator-directed. Neither is the operator's own typed text.

| seq | stage | verbatim | disposition | plan_ref | reason |
|---|---|---|---|---|---|
| 1 | 1 | "Review and audit the **TensorFold 1.1.4** release (the operator says it brings significant kernel upgrades) and distill learnings into **proposed AutoKernel (AK) hypothesis seeds** for the EPYC project." | planned | P1 | The seeds are P1/P2 |
| 2 | 1 | "Change of method from workspace-58, operator-directed: run this review through the project's /research-intake skill." | context-only | null | Method directive, followed: four-stage flow, stopped at Stage 3 |
| 3 | 2 | "STOP at the Stage-3 plan; do not apply anything." | context-only | null | Honoured: only out-of-repo prepared files were written |

## Stage-3 filing payload

```json
{
  "format_version": 2,
  "entry_updates": [
    {"id": "intake-1924", "integration_disposition": "adopt_patterns",
     "handoffs_updated": ["autokernel-all-devices-all-dimensions.md"], "handoffs_created": [],
     "disposition_evidence": ["Stage-3 plan STAGE3-PLAN.md P1-P3: AKX-ALL-30, AKX-ALL-30a, AKX-ALL-31; inbox notes 60 (27B), 65 (Q38FN), 32 (DS41-1017)."]}
  ],
  "opportunity_reviews": {
    "P1": {"project_objective": "Raise 27B MI210 decode at long context (88% of :8083 decode wall above 32k)",
           "implementation_ref": "ffc1bac82 ggml/src/ggml-cuda/fattn-common.cuh:1022-1041,1176-1178; fattn-wmma-f16.cu:100-103; rocprof B 20261004T081019Z",
           "gap": "Multi-row FA re-reads f16 K/V per GQA query head and converts the whole q8_0 view to f16 per call (FA 29 ms + convert 8 ms = 31% of the 80k step)",
           "operational_change": "Seed G2/G3/G1/G4 in the 27B AK inbox; arbiter rocprof orders them",
           "benefit_direction": "Lower ms per verify round at depth; G2/G3 bit-exact, G1 row-invariant under the ppl/KLD contract and the DF2-9 gate",
           "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
           "execution_conditions": "Filing after approval; inbox write and AK runs after the launch hold lifts; arbiter needs an MI210 window grant; authoring after the AKX-ALL-19 route and FA-owner confirmation",
           "closure_basis": "Immediate filing and probe retained; promotion stays behind the keep gate and the production-shape surfaces (AKX-ALL-LB2)"},
    "P2": {"project_objective": "Raise Q38FN and DS41-1017 CPU decode",
           "implementation_ref": "Q38FN note 62 census L10-27; ops.cpp:11134-11154; deepseek-v41-flash-evaluation.md:1211-1224",
           "gap": "CPY 9.4% of Q38FN wall unattributed beyond 'feeding matmuls'; GDN prologue nodes; DS41 indexer unfused at depth",
           "operational_change": "Seed Q1, Q2 (conditional) and D1 (record-only) as inbox notes",
           "benefit_direction": "Fewer nodes and copies per token; bit-exact",
           "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
           "execution_conditions": "After approval and the hold lift; D1 only on the AKX-ALL-12 depth surface",
           "closure_basis": "Immediate filing retained; each seed carries its own falsifier"},
    "P3": {"project_objective": "Make AK correctness gates non-vacuous for non-finite propagation and reduced-precision accumulation",
           "implementation_ref": "AKX-ALL-29.4 (open), 29.5 guard bands (done, opt-in), 27B note 10 H2 RI self-test",
           "gap": "No AK gate checks the non-finite class against float64 or proves fp32 accumulation, and none requires a planted control to go red",
           "operational_change": "Two gates with planted controls in the default chain",
           "benefit_direction": "Catches NaN-dropping or fp16-accumulating candidates that tolerance gates pass",
           "owner": "handoffs/active/autokernel-all-devices-all-dimensions.md",
           "execution_conditions": "Research branch, build role, no inference compute; INF-73 owner review",
           "closure_basis": "Immediate"},
    "P4": {"project_objective": "Keep the intake record true at the current source version",
           "implementation_ref": "research/intake_index.yaml L246326-246390 (intake-1924)",
           "gap": "Entry is stage1-unverified at v0.6.5, carries two cross-contaminated EPYC figures and two now-false claims",
           "operational_change": "Apply INTAKE-ENTRIES-PROPOSED.yaml as targeted text edits",
           "benefit_direction": "Citable dive-verified anchors; contamination removed",
           "owner": "research-intake session",
           "execution_conditions": "After approval; validate_intake.sh exit 0; vidya sync after the push",
           "closure_basis": "Immediate"},
    "K1": {"project_objective": "Record methodology learnings without creating tasks",
           "implementation_ref": "KVU-16f/g (kv-unified-stack-rollout.md), AKX-ALL-13; MEASUREMENT.md paired-ABA rule",
           "gap": "None operational: chunking and table estimation are already owned",
           "operational_change": "dive_corrections text only",
           "benefit_direction": "Prevents re-deriving",
           "owner": "research-intake session",
           "execution_conditions": "With P4",
           "closure_basis": "No immediate step remains: owners exist and no cached table has been built yet"}
  },
  "opportunity_scan": [
    {"scan_id": "S1", "source_ref": "a56d0ce2fa.patch L10", "implementation_ref": "fattn-common.cuh:1176-1178 @ ffc1bac82", "mechanism": "Grid order so blocks sharing K/V chunks co-run", "consumer": "27B multi-row FA", "application": "Seed G2", "disposition": "actionable", "ledger_ids": ["TF114-1"], "basis": "Source read on both sides"},
    {"scan_id": "S2", "source_ref": "PR #1168 L13/L20; 184a938e3a", "implementation_ref": "fattn-common.cuh:1022-1041", "mechanism": "In-tile dequant instead of whole-view convert", "consumer": "27B multi-row FA", "application": "Seed G3", "disposition": "actionable", "ledger_ids": ["TF114-2"], "basis": "Convert measured 8 ms in rocprof B"},
    {"scan_id": "S3", "source_ref": "PR #1168 L13, L20, L22", "implementation_ref": "fattn-wmma-f16.cu:100-103; fattn.cu:113-150", "mechanism": "GQA heads x rows as tile lines, each tile read once per round", "consumer": "27B multi-row FA", "application": "Seed G1", "disposition": "actionable", "ledger_ids": ["TF114-3"], "basis": "WMMA path has no GQA packing"},
    {"scan_id": "S4", "source_ref": "e475e90fb9", "implementation_ref": "src/models/dflash.cpp (head shape unread)", "mechanism": "Drafter logits over vocabulary spans with fallback", "consumer": "27B DFlash2 drafter", "application": "Seed G4", "disposition": "actionable", "ledger_ids": ["TF114-4"], "basis": "Low; falsifier reads the head shape first"},
    {"scan_id": "S5", "source_ref": "PR #1138 L72; PR #1079 L42; 11e9b4db18", "implementation_ref": "27B inbox note 10 H3/H4/H7/H13", "mechanism": "Sibling projections in one launch; wide verify; producer sums", "consumer": "existing 27B seeds", "application": "Evidence lines in the new note", "disposition": "covered", "ledger_ids": ["TF114-5"], "basis": "Same mechanisms already seeded"},
    {"scan_id": "S6", "source_ref": "b9b23ec9ca; 11e9b4db18; e72a34ae38", "implementation_ref": "Q38FN note 62 L10-27", "mechanism": "Producer writes the consumer's layout/type", "consumer": "Q38FN CPY nodes", "application": "Seed Q1", "disposition": "actionable", "ledger_ids": ["TF114-6"], "basis": "CPY 9.4% measured, unattributed"},
    {"scan_id": "S7", "source_ref": "d0d179497e L15, L25; eb0d391600", "implementation_ref": "ops.cpp:11134-11154; src/models/qwen4exp-fused.cpp", "mechanism": "Fused GDN prologue/chain/norm", "consumer": "Q38FN GDN nodes", "application": "Seed Q2 (conditional)", "disposition": "actionable", "ledger_ids": ["TF114-7"], "basis": "Snapshots already in-kernel; only prologue nodes remain"},
    {"scan_id": "S8", "source_ref": "aa6fbd8903 L17", "implementation_ref": "deepseek-v41-flash-evaluation.md:1211-1224", "mechanism": "Blocked fused indexer scan", "consumer": "DS41 lightning indexer at depth", "application": "Seed D1 (record-only)", "disposition": "actionable", "ledger_ids": ["TF114-8"], "basis": "Grows with context per DS41-C123"},
    {"scan_id": "S9", "source_ref": "docs/kernel-contract.md L4-5 @ eab85828", "implementation_ref": "AKX-ALL-29.4/29.5; note 10 H2", "mechanism": "Planted-control gates", "consumer": "AK candidate gate", "application": "AKX-ALL-31", "disposition": "actionable", "ledger_ids": ["TF114-9"], "basis": "Gates 1 and 4 absent in AK"},
    {"scan_id": "S10", "source_ref": "PR #1069 L5", "implementation_ref": "tools/server/server-context.cpp:500,3143,3193 @ ffc1bac82", "mechanism": "Cross-stream shared verify", "consumer": "llama-server", "application": "none", "disposition": "declined", "ledger_ids": ["TF114-D1"], "basis": "Already integrated"},
    {"scan_id": "S11", "source_ref": "69e491cbc5 L9", "implementation_ref": "note 10 §0; q8_1 MMQ", "mechanism": "int8 activation GEMM", "consumer": "prefill", "application": "none", "disposition": "declined", "ledger_ids": ["TF114-D2"], "basis": "Already integrated; no CDNA2 rate gain"},
    {"scan_id": "S12", "source_ref": "PR #1195", "implementation_ref": "ggml threadpool get_rows", "mechanism": "Worker pool", "consumer": "PLE gather", "application": "none", "disposition": "declined", "ledger_ids": ["TF114-D3"], "basis": "No defect"},
    {"scan_id": "S13", "source_ref": "0c73b158de", "implementation_ref": "Q38FN note 62 seed 3", "mechanism": "Routed+shared pairing", "consumer": "DS41 MoE", "application": "none", "disposition": "declined", "ledger_ids": ["TF114-D4"], "basis": "0% recoverable on analog"},
    {"scan_id": "S14", "source_ref": "a56d0ce2fa", "implementation_ref": "AKX-ALL-LB3 (a)", "mechanism": "KV reuse across rows/heads", "consumer": "CPU FA", "application": "none", "disposition": "covered", "ledger_ids": ["TF114-D5"], "basis": "Owned by LB3"},
    {"scan_id": "S15", "source_ref": "14ae735699", "implementation_ref": "none built", "mechanism": "Min-of-reps cost table", "consumer": "future crossover tables", "application": "knowledge", "disposition": "context-only", "ledger_ids": ["TF114-D6"], "basis": "No consumer yet"},
    {"scan_id": "S16", "source_ref": "PR #1080", "implementation_ref": "KVU-16f/g; AKX-ALL-13", "mechanism": "Larger prompt chunks", "consumer": "27B prefill", "application": "knowledge", "disposition": "covered", "ledger_ids": ["TF114-D7"], "basis": "Owned"},
    {"scan_id": "S17", "source_ref": "CHANGELOG L11-55", "implementation_ref": "operator lane rule 2026-10-06", "mechanism": "Gemma 4 / speech", "consumer": "none in AK lanes", "application": "none", "disposition": "declined", "ledger_ids": ["TF114-D8"], "basis": "Lane scope"},
    {"scan_id": "S18", "source_ref": "ggml.cu L1", "implementation_ref": "note 10 §3.2", "mechanism": "bf16 exact-integer MMA", "consumer": "27B GEMV", "application": "none", "disposition": "declined", "ledger_ids": ["TF114-D9"], "basis": "Settled"},
    {"scan_id": "S19", "source_ref": "v1.1.4 dive", "implementation_ref": "intake_index.yaml L246326-246390", "mechanism": "Record correction", "consumer": "intake-1924", "application": "entry_updates", "disposition": "actionable", "ledger_ids": ["TF114-10"], "basis": "Stage-1-unverified at 0.6.5"}
  ],
  "actionable_additions": [
    {"ledger_id": "TF114-1", "source": "a56d0ce2fa.patch L10", "action": "Seed G2 + arbiter", "terminal_mapping": "P1 / AKX-ALL-30, AKX-ALL-30a"},
    {"ledger_id": "TF114-2", "source": "PR #1168; 184a938e3a", "action": "Seed G3", "terminal_mapping": "P1 / AKX-ALL-30"},
    {"ledger_id": "TF114-3", "source": "PR #1168 L13, L20, L22", "action": "Seed G1", "terminal_mapping": "P1 / AKX-ALL-30"},
    {"ledger_id": "TF114-4", "source": "e475e90fb9", "action": "Seed G4", "terminal_mapping": "P1 / AKX-ALL-30"},
    {"ledger_id": "TF114-5", "source": "PR #1138; PR #1079; 11e9b4db18", "action": "Evidence for H3/H4/H7/H8", "terminal_mapping": "P1 / AKX-ALL-30"},
    {"ledger_id": "TF114-6", "source": "b9b23ec9ca; 11e9b4db18; e72a34ae38", "action": "Seed Q1", "terminal_mapping": "P2 / AKX-ALL-30"},
    {"ledger_id": "TF114-7", "source": "d0d179497e; eb0d391600", "action": "Seed Q2", "terminal_mapping": "P2 / AKX-ALL-30"},
    {"ledger_id": "TF114-8", "source": "aa6fbd8903", "action": "Seed D1", "terminal_mapping": "P2 / AKX-ALL-30"},
    {"ledger_id": "TF114-9", "source": "docs/kernel-contract.md", "action": "Planted-control numerics gates", "terminal_mapping": "P3 / AKX-ALL-31"},
    {"ledger_id": "TF114-10", "source": "intake-1924 vs v1.1.4", "action": "Entry dive fields and corrections", "terminal_mapping": "P4 / entry_updates"},
    {"ledger_id": "TF114-D1", "source": "PR #1069, #1155", "action": "Shared verify / batched drafting", "terminal_mapping": "decline: already integrated in llama-server"},
    {"ledger_id": "TF114-D2", "source": "69e491cbc5", "action": "int8 prompt GEMM", "terminal_mapping": "decline: already integrated; no CDNA2 rate gain"},
    {"ledger_id": "TF114-D3", "source": "PR #1195", "action": "PLE worker pool", "terminal_mapping": "decline: no thread-spawn defect"},
    {"ledger_id": "TF114-D4", "source": "0c73b158de", "action": "Routed+shared pairing for DS41", "terminal_mapping": "decline: analog measured 0% recoverable; reopen only if a DS41-1017 node profile shows shared-expert barrier cost of at least 1%"},
    {"ledger_id": "TF114-D5", "source": "a56d0ce2fa (CPU reading)", "action": "CPU FA reorder", "terminal_mapping": "decline: owned by the existing CPU long-context lane"},
    {"ledger_id": "TF114-D6", "source": "14ae735699", "action": "Cost-table min-of-reps", "terminal_mapping": "K1"},
    {"ledger_id": "TF114-D7", "source": "PR #1080", "action": "Long-prompt chunking", "terminal_mapping": "K1"},
    {"ledger_id": "TF114-D8", "source": "CHANGELOG 1.1.4", "action": "Gemma 4 / Drama / speech / serving", "terminal_mapping": "decline: not in the AK lanes"},
    {"ledger_id": "TF114-D9", "source": "ggml.cu L1", "action": "bf16 exact-integer MFMA route", "terminal_mapping": "decline: settled by note 10 §3.2"}
  ],
  "steering_reconciliation": [
    {"seq": 1, "stage": 1, "verbatim": "Review and audit the **TensorFold 1.1.4** release (the operator says it brings significant kernel upgrades) and distill learnings into **proposed AutoKernel (AK) hypothesis seeds** for the EPYC project.", "disposition": "planned", "plan_ref": "P1", "reason": "Seeds filed via P1/P2"},
    {"seq": 2, "stage": 1, "verbatim": "Change of method from workspace-58, operator-directed: run this review through the project's /research-intake skill.", "disposition": "context-only", "plan_ref": null, "reason": "Method directive; followed"},
    {"seq": 3, "stage": 2, "verbatim": "STOP at the Stage-3 plan; do not apply anything.", "disposition": "context-only", "plan_ref": null, "reason": "Honoured; prepared files only"}
  ],
  "outcome_reviews": {
    "TF114-1": {"required_outcome": "G2 is in the 27B inbox and the arbiter decides its order", "review_status": "preserved", "review_basis": "Task text names the seed id, file and predeclared rule",
      "task_refs": [
        {"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 60 present with sha256 recorded"},
        {"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30a", "task_text": "  - [ ] **AKX-ALL-30a — arbiter probe before authoring the GPU FA seeds.**", "acceptance": "verdict JSON names the ordering"}]},
    "TF114-2": {"required_outcome": "G3 seeded", "review_status": "preserved", "review_basis": "In note 60", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 60 present"}]},
    "TF114-3": {"required_outcome": "G1 seeded behind G2/G3", "review_status": "preserved", "review_basis": "In note 60 with ordering", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 60 present"}]},
    "TF114-4": {"required_outcome": "G4 seeded with head-shape falsifier", "review_status": "preserved", "review_basis": "In note 60", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 60 present"}]},
    "TF114-5": {"required_outcome": "Existing seeds receive the external evidence", "review_status": "preserved", "review_basis": "Evidence section of note 60", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 60 present"}]},
    "TF114-6": {"required_outcome": "Q1 seeded (attribution first)", "review_status": "preserved", "review_basis": "In note 65", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 65 present"}]},
    "TF114-7": {"required_outcome": "Q2 seeded with its overlap falsifier", "review_status": "preserved", "review_basis": "In note 65", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 65 present"}]},
    "TF114-8": {"required_outcome": "D1 recorded for the depth surface", "review_status": "preserved", "review_basis": "In note 32", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-30", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**", "acceptance": "note 32 present"}]},
    "TF114-9": {"required_outcome": "Two planted-control gates run by default", "review_status": "preserved", "review_basis": "Task acceptance requires red controls and a passing incumbent", "task_refs": [{"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_id": "AKX-ALL-31", "task_text": "- [ ] **AKX-ALL-31 — planted-control numerics gates for AK candidates (intake-1924#record; TensorFold `docs/kernel-contract.md` gates 1 and 4).**", "acceptance": "both controls red; incumbent passes"}]},
    "TF114-10": {"required_outcome": "intake-1924 is dive-verified at v1.1.4 with contamination removed", "review_status": "closed-with-basis", "review_basis": "Delivered by entry_updates and INTAKE-ENTRIES-PROPOSED.yaml, not a handoff task", "task_refs": []},
    "TF114-D1": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "server-context.cpp:500,3143,3193 batch every slot's drafts", "task_refs": []},
    "TF114-D2": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "q8_1 integer-dot path in use; CDNA2 int8 = f16 rate", "task_refs": []},
    "TF114-D3": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "ggml threadpool is persistent", "task_refs": []},
    "TF114-D4": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "Q38FN note 62 seed 3 measured 0% recoverable", "task_refs": []},
    "TF114-D5": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "The CPU long-context lane owns GQA grouping; the reorder keep was discarded on replicate", "task_refs": []},
    "TF114-D6": {"required_outcome": "methodology recorded", "review_status": "closed-with-basis", "review_basis": "K1 knowledge-only; no cached table exists", "task_refs": []},
    "TF114-D7": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "K1; owned by the KV-pool batch tasks and runtime arms", "task_refs": []},
    "TF114-D8": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "Operator lane rule 2026-10-06 (DS41/Q38FN lanes only)", "task_refs": []},
    "TF114-D9": {"required_outcome": "none", "review_status": "closed-with-basis", "review_basis": "Note 10 §3.2 settled it", "task_refs": []}
  },
  "proposed_tasks": [
    {"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_text": "- [ ] **AKX-ALL-30 — inject the TensorFold 1.1.4 seeds as three inbox notes (intake-1924#record).**"},
    {"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_text": "  - [ ] **AKX-ALL-30a — arbiter probe before authoring the GPU FA seeds.**"},
    {"owner": "handoffs/active/autokernel-all-devices-all-dimensions.md", "task_text": "- [ ] **AKX-ALL-31 — planted-control numerics gates for AK candidates (intake-1924#record; TensorFold `docs/kernel-contract.md` gates 1 and 4).**"}
  ]
}
```

Note for the applier: the JSON `task_text` values are the bold heads of the full lines in the "Handoff edits" block.
Stage 4 must paste the **full** lines from that block, and then make `proposed_tasks`/`task_refs` match the applied
line text exactly before running the validator.
