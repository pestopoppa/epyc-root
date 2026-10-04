# Research-intake practical applications — follow-up review

**Date**: 2026-10-04. Operator-requested investigation and retrospective, not a new intake.
**Read context**: root `0dc61a2809a817efedc10d7ec5a5441a9371d163`;
orchestrator `f8c9c0a392731d487fee5e35e90659a996d3301a`;
research `412e8fc11d153554354f51c9f9f70b9c984578f8`.
Research has unrelated tracked modifications; findings refer to inspected working files,
not an assertion that HEAD identifies every byte read.

**Outcome:** two missed operational applications, one refinement of existing runner enforcement,
and one bounded skill refinement are filed as four proposals. No application implementation
or measured gain is claimed; selected-source scope does not establish exhaustive completeness.

## Question and existing recovery

Can a useful application disappear before it receives a recommendation ID, or be replaced by
enabling work while ID coverage remains perfect? The already-landed opportunity gate does not
make that independent semantic question disappear. Revalidation passed 25 tests and 29 subtests;
this proves structural conformance, not absence of omissions.

Decision-tools already has unchecked implementation/probe tasks for killable execution and
Monty (`D-RI-CONTAIN`, `D-RI-MONTY-SLICE`), runtime routing
(`LRC-SDM-ACTION-SCORER` and its cached comparison), actual cross-harness execution and SFT
selection (`TU-MH-1`, `S2-CGE-1`), and native looped feasibility
(`RC-XLLM-PREFILL-1`). These are recovered opportunities, not new missing tasks or measured gains.

## Selection of the preceding three completed campaigns

Newest first, selected using the checkpoint predecessor chain and completed Stage-4 commits:

| Campaign | Completion | Plans and source scope |
|---|---|---|
| HipKittens/GEMM ladder, September 26–27 | `e43a7589`; checkpoint `1175b2ba` | [Plan](../research-intake/hipkittens-gemm-ladder-stage3-plan-20260926.md), [checkpoint](../../research/sessions/intake-hipkittens-gemm-ladder-20260926.json); five entries: intake-1822#record through intake-1826#record. |
| Orchestration prior art, September 26 | `0c8e227e` | [Plan](../research-intake/orch-prior-art-stage3-plan-20260926.md); P4 reconciliation R1–R6 is authoritative; 39 entries: intake-1783#record through intake-1821#record. |
| EXL3/SGLang throughput, September 25–26 | `0bb2e96b` | [Follow-up](../../research/intake-stage3-plan-2026-09-25-exl3-throughput-followup.md) plus [base plan](../../research/intake-stage3-plan-2026-09-25-exl3-cpu-mi210.md); 88 campaign entries: intake-1563#record through intake-1575#record and intake-1708#record through intake-1782#record. |

The HipKittens checkpoint explicitly names both predecessors. Their completed checkpoints remain
under `/mnt/raid0/llm/tmp/dive-hipkittens-gemm/previous-research-session-{orch-prior-art,exl3}-stage4.json`.
The base plan's 35 earlier EXL3 entries are contextual predecessors, not a fourth selected campaign.
Intervening HyperQwen/LABD is Stage-2 complete, not a completed Stage-4 campaign.
This sample differs from the earlier four-campaign audit; GEPA, ParEval and PAW historical
omissions recovered there are not newly missing work here. Neither review estimates index-wide prevalence.

## Main-reviewed operational omissions

### HipKittens: existing coverage, with one enforcement refinement

No new unfiled kernel technique was demonstrated in the inspected sample. MFMA/VALU interleave,
register prefetch, LDS fill/double buffering, tile/thread sweeps, the compiler-form arm and Zen5
gemm4xN work have concrete owners and retained parking rulings. J-cap has a retained negative
experiment; its timing-output and MoE-invariance follow-ups are already filed.
The nonconstant-scale correctness behavior is present; grouped-projection observation is retained.

The reviewer identified a narrower enforcement gap in existing `INF03-REGAUDIT-2` coverage.
The policy requires a static ISA audit before timing, but the retained MMQ `window_ab.sh`
hashes libraries and proceeds to correctness/timing without checking that they match the passing
audit. Main read the runner, audit README, promotion instructions and H10a/H10b's explicit rerun
consumer. The historical experiment has a passing static audit: this is not evidence it bypassed
the gate or invalidation of that run.

Recovered refinement: `INF03-REGAUDIT-RUNNER` in the
[ROCm authoring owner](../../handoffs/active/agentic-rocm-kernel-authoring.md).
Bind the next/reused MMQ timing runner to exact selected-library audit hashes, nonempty relevant
coverage, and the existing passing diff or explicitly accepted named failures.
Missing/stale/empty/failing evidence must stop before timing. Preserve historical evidence;
reuse the current comparator/source, not a new grading rule or measurement campaign.
This improves robustness against unusable future measurements; no performance benefit is established
and no parked GPU experiment is reopened. Record discussion: intake-1826#record.

The retained LLVM anchors, selected ladder/DS-V4 passages, mappings, current implementations and later
owner rulings were inspected. Complete original final-dive/derived-ledger transcripts for 1822/1823
were not recovered, so exhaustive pre-ledger completeness remains unestablished.

### Orchestration: C1-A6 closed against the wrong cost boundary

The approved plan and LRC's retained C1-A6 paragraph say the small MLP satisfies the amortization
concern. The saved RouteBalance source instead batches embedding, KNN lookup and estimation together.
Current `src/api/routes/chat.py:_handle_chat` synchronously calls `_route_request`;
`retriever.py:retrieve_for_routing` embeds before retrieval, and
`hybrid_router.py:_build_classifier_features` embeds before the classifier.
`parallel_embedder.py:embed_sync` waits on `future.result()` when called from an event loop.
Main read these implementations and the source passage. A cheap MLP does not establish that the
complete route is nonblocking. This is an uncovered concurrency concern, not a measured production
saturation result.

Recovered proposal: `LRC-RI-CONCURRENCY` in the
[routing owner](../../handoffs/active/learned-routing-controller.md). Use delayed fake embeddings
and an independent event-loop sentinel through the actual routing seam, count every concurrent
request, and repair only the demonstrated blocking operation while preserving shared state,
request-local metadata and deterministic route results. No inference, policy change, DAR-LAT
reactivation or production rollout is part of this proposal. Lower event-loop stall/queue delay
is the hypothesis; no gain is claimed. Record discussion: intake-1796#record.

Source: `/mnt/raid0/llm/tmp/dive-intake-1796/sources/2606.17949v1.txt`, Algorithm 1;
approved plan's C1-A6 filing and current LRC C1-A6 paragraph. Frontdoor/backpressure/lifecycle,
capacity/static-prior, residency, GPU-prefill/KTransformers and grounded shared-note opportunities
inspected by the reviewer already have owners. Later freezes and the retired-runner recovery stand.
This was selected-source review, not exhaustive reading of all 39 entries.

### EXL3: capture safeguards substituted for valid capture/replay

The original `/mnt/raid0/llm/tmp/dive-1569/REPORT.md` recommends device-resident verification
metadata and changed-length replay checks. The saved outer-graph patch lets the serving runtime own
capture. Approved follow-up P2/P3 retained plan/bind arenas, capture-time fallback refusal and graph
overhead attribution. Current `scripts/kernel_rnd/exl3_gfx90a/kernels.hip:run` rejects every
actual capture and uploads route/count/order from host arrays; `test_runtime.hip` tests refusal,
not successful replay. Main read the source, patch, plan, current code and owner; no inspected
task assigns the valid captured-execution behavior.

Recovered proposal: `EXL3-GRAPH-1` in the
[EXL3 owner](../../handoffs/active/exl3-cpu-mi210-implementation.md). Implement a bounded
device-resident metadata interface for caller-owned outer capture on the standalone unified path,
retain eager execution and refusal guarantees, and qualify changed routing/lengths within a declared
capture envelope against the existing full-output oracle. Reuse the live EXL3 write-side and
projection; compare eager/replay on identical frozen inputs with interleaved repetitions and retained
failures only after correctness. Dispatch-overhead reduction is a hypothesis, not a measured gain.
Existing device correctness prerequisites and coordinated hardware claims apply. This does not
reopen EXL3-6/7 on the parked 27B or alter production. Record discussion: intake-1569#record.

The reviewer inspected dives 1564, 1569, 1570, 1754, 1757, 1771 and 1778 plus saved patches,
plans, current implementation and owners. CPU/MI210 primitives, mixed-K dispatch, hybrid streaming,
paired drafter state/allocation and the acceptance-floor guard are already filed or implemented.
Direct KV gather/dequant is inconclusive: no uncovered current consumer was established, so no
additional task is filed for it. The published CIRU profile lacks exact prompt/harness/image identity.
This is selected-source review, not exhaustive coverage of the 88 campaign entries.

## Bounded refinement proposal

One proposed owner task, `ID-RI-COVERAGE-DELTA` in the
[intake-derived owner](../../handoffs/active/intake-derived-work-2026-07-25.md), preserves three changes:

1. Independently compare selected verified mechanisms with current consumer behavior before
   declaring the actionable ledger complete. Record a concrete missing application with its source
   locator before minting its ID. Existing infrastructure may implement the behavior, supply only a
   component, or serve a different objective.
2. Bind compressed recommendations to exact owner/task text and operational acceptance outcomes.
   Wiring or an adjacent fix preserves only the behavior it supplies. Keep implementation,
   isolated probe and production activation conditions separate; review closure premises.
3. Specify plan-only actionable/steering additions; reconcile retained rows plus declared additions
   in memory during Stage 3, persisting only at approved Stage 4. Extend structural checks for
   owner-bound references and closure-review presence without auto-grading usefulness.

Exact sites: existing `SKILL.md` extraction/completeness gates,
`references/stage3-action-distillation.md`, `references/session-persistence.md`,
`validate_plan_payload` and its existing tests. The validator currently compares two existing ID
inventories, resolves task identifiers across declared owners, and mandates immediate-packet reviews.
It neither independently discovers opportunities nor proves task-outcome equivalence.
Its Stage-3 fence allows no actionable delta; instructions permit plan-only new steering, which the
validator does not inspect. Main verified these boundaries in the implementation.

Proposed regressions: an application missing from both inventories; Monty containment replaced by
timeout poisoning; SDM runtime scoring replaced by provenance repair; executable harness/SFT work
replaced by capture receipts; native looped feasibility confused with production admission;
new plan-only additions; and a closure resting solely on activation freeze or graph risk.
Mechanical and semantic expectations remain separate. These additional cases were not run here.

No new receipt platform, corpus migration, semantic grader, measurement-trust amendment, benchmark
campaign or application implementation is proposed by this workflow refinement. Future machine-check
propositions/read-set digests use the existing prospective conformance source and `VB-RI-OPS-WIRE`.
This qualitative review emits no measurement rate or promotion warrant.

## Source references

### Implementation read-set hashes

Paths are relative to their pinned repository; hashes identify the actual bytes inspected.

| Repo | File | SHA-256 |
|---|---|---|
| orchestrator | `src/api/routes/chat.py` | `a6029081c61cb96edf03fff644822b79313fd0c8dc000f17d429275814c2c2e6` |
| orchestrator | `orchestration/repl_memory/retriever.py` | `a8e374e95679301566965bec15029a9134e3a0f53961a7c41dbbb1ba5b189dde` |
| orchestrator | `orchestration/repl_memory/hybrid_router.py` | `cdd671d0e39e26abf3eebbe5d9edec573375596298f54349990c75d1dbbe4764` |
| orchestrator | `orchestration/repl_memory/parallel_embedder.py` | `2c6c7c83e7977edbdc260d53bb617c77d07ee8b40eeca874f3958ef6c0bc86d3` |
| research | `scripts/kernel_rnd/exl3_gfx90a/kernels.hip` | `180f1a37f634bd1f69e7777b9735410e92511dc583a55a9d80152c8747356d0e` |
| research | `scripts/kernel_rnd/exl3_gfx90a/test_runtime.hip` | `2733ea92d08c0231ba056e1e48c467c55ac8efa9b70a5571e2135923704bc744` |
| research | `data/gfx90a-isa-audit-20260927-mmq-jcap/window_ab.sh` | `b3400903a0ca2b0ad01ce4ed4f5b300ede7b910f1df95d3040984f75c7a00f62` |

- [Current distillation instructions](../../.claude/skills/research-intake/references/stage3-action-distillation.md).
- [Persistence and steering](../../.claude/skills/research-intake/references/session-persistence.md).
- [Structural validator](../../.claude/skills/research-intake/scripts/validate_intake.py).
- [Approved decision-tools plan](../../research/intake-stage3-plan-2026-10-03-decision-tools.md).
- [Published Stage-4 evidence](../../progress/2026-10/2026-10-04-intake-decision-tools-stage4.md).
- [Wrap-up progress](../../progress/2026-10/2026-10-04-codex-intake-wrap.md).
