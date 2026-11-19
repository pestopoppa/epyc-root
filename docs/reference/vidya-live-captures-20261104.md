# Vidya live capture results, 2026-11-04

The native records, row manifests, end records, filed verdicts and SHA-256 manifest are retained in
[`data/vidya/run-filings/2026-11-04/`](../../data/vidya/run-filings/2026-11-04/).

## Serving steps estimate: capture accepted

`vb-sl2-steps-r1-20261103` completed two same-image C5 A/A pairs (four launches). Its sealed receipt
`5e835e05a215372fe5895e8122dd0807a4f4a82f5476251d12e27c0db76aa4f0` carries
`target_sample_steps_est`. Canonical `autokernel-serving` ingest emitted 15 frames for five claims,
including two steps estimates; `steps_projected=2`, `refusals=[]`.

The estimator is `predicted_n_minus_draft_n_accepted`, not the server's `n_draft_verif_steps`.
The anchor and candidate estimates are respectively 9.567504218686695 and 7.0034427083189925 steps/s.
Both are reporting observations, with no floor and `decisive=None`. This A/A capture establishes
the producer/reader path, not a performance improvement or a preferred recipe. The reader's
missing-estimator refusal was already implemented before this live run.

Canonical claims:

- `clm_legacy-serving-steps:5e835e05a215372fe5895e8122dd0807a4f4a82f5476251d12e27c0db76aa4f0:anchor`
- `clm_legacy-serving-steps:5e835e05a215372fe5895e8122dd0807a4f4a82f5476251d12e27c0db76aa4f0:candidate`

## Actor-wire matrix: projection accepted, planning gate open

`vb-ak-wire-matrix-r1-20261103` finalized PASS for all 15 requested seats from Research producer
`ec9307280129940c7c85493df622427a4e287f88`. The finalization file SHA-256 is
`efe1d67cc1dd2beb551a3ad9d2af5643b13bb413a758b85b1af00286bd348f94`.
Canonical `ak-actor-wire` ingest projected 31 verifier findings and emitted 93 frames, with no
refusals, missing records or declines. Six native-provider checks and three mocked process controls
remain separate. The installed clients used a scripted loopback provider; this establishes neither
model quality, timing nor merge validity.

The run passes its capture/projection decision rule. `VB-AK-WIRE-MATRIX-LIVE` and its parent remain
open until the actual AK planning context lists the decided proposition for its target.

The follow-up `vb-ak-wire-canary-r1-20261104` is filed **FAIL**. The real reader returned `ready`,
ingest projected all 31 findings without refusals, and the protected ledger hash was unchanged,
but the matrix proposition was absent from the Q38FN CPU planning target's
evidence section. Projection of the matrix tuple retains `source_class=verifier`,
`binding_kind=identity` and empty applicability. The native request identifies client seats and
their wire suite; it does not author applicability to a Q38FN model. The selector must not acquire
that scope from the canary's requested model. The missing operational-verifier consumption path
therefore remains a wiring gap; neither the live capture nor this failed canary closes the loop.

The new unregistered `scripts/vidya/actor_wire_subject.py` names that operational identity from the
strictly re-read native record and matches producer/request/suite/seat exactly. Its controls run
alongside the native adapter tests (58 passed). It adds no ledger selection, admissibility or
grading policy and has no production caller; actual planner integration remains required.

## Canary B: failed keep recovery

`vb-canary-b-r1-20261103` successfully used the live BGE-large embedder (1024 dimensions, two calls,
no embedding or assembly errors). Protected ledger/state hashes remained unchanged and the
embedder teardown was verified. Frontier assembly with T1 count zero is valid after the rebase.
The required trial-1472 keep containing `2.025` and `ingest_triviality_guard` was absent:
`observed_1472_keep_with_numbers=false`, `canary_exit=1`. The row verdict is FAIL; its completion
checkbox and the parent canary gate remain open. The process wrapper's rc=0 does not override the
canary's failed predicate. No retry was performed in that run.

Source review subsequently located the invalid reference: the native journal marks trial 1472
excluded with `learning_exclusion.by=reproduction_confirmed`. The pinned orchestrator's
`experiment_journal.py` excludes that state from learning, so no eligible strategy-store row exists
for semantic retrieval. The trial also predates the current quality/Pareto era. The failure therefore
does not demonstrate an embedding or ranking defect. A future acceptance canary needs a genuinely
eligible current-era native keep as its pinned semantic sentinel; substituting another historical
keep or injecting the excluded one would invalidate the check. The original run remains FAIL under
its published rule.

## R18 symbol successor: inconclusive before comparison

`r18-belief-symbols-scratch-20261102` ended rc=70 with a partial result. The pre-comparison check
reported `pinned input changed: private_hip`; the terminal disposition is UNKNOWN. Build-complete
units do not establish a complete CPU/HIP-host/gfx90a-device symbol comparison. No symbol-equivalence
or difference finding follows, and the surviving `VB-KQROUTE-1` acceptance task remains open.

## Prospective source controls and qualification submissions

The separate EXP01 source-capture control `vidya-exp01-proxy-wire-20261104` completed on four CPUs
with four native threads. Four original speed units and the first fixed paired item produced six
native launches and four strictly rederived observations. Its first attempt exposed a parser defect:
the original validity record uses `unit=validity` without a `kind` field. That attempt is preserved;
the corrected parser has a regression built from its native record. The subsequent complete control
is filed PASS. It supplies no new pilot ratio/look, speed advantage, port/futility decision or formal
gate evidence and is not combined with r3. Canonical source registration and a real planning-context
canary remain required for `VB-EXP01-PROXY-WIRE`.

The prospective GPU-pool helper `gpu_pool_native.py` and exact actor-wire subject validator are
unregistered components. Their native writer adoption and actual planner consumption remain open;
the completed code/control subtasks do not close their parent source families.

Three other row definitions were submitted while the GPU was occupied. Their publisher outcome was
`GPU-SMOKE-QUEUED`, not a qualification PASS:

| Row | Scoped workload |
|---|---|
| `handoff-vidya-kvu19a2-wire-20261104` | Model-free attention cases 78/80, five exact-input launches per arm/case |
| `vidya-r18d-aa-wire-20261104` | Qwen3.8-27B Q8_0 pp512 A/A; original conditioning and 20 pairs per condition |
| `vidya-r234-native-sweep-20261104` | Seven-arm Qwen3.8-27B DFlash2 serving sweep; 63 predeclared requests |

The allocator owns their pending GPU smokes. R18-D smoke observations are explicitly unsettled and
cannot establish a calibration floor. Row source packets and submission snapshots are retained in
[`data/vidya/row-preparation/2026-11-04/`](../../data/vidya/row-preparation/2026-11-04/).

## Completed-smoke result glob recovery

The full EXP01 control passed smoke, but the publisher then treated its declared result glob as a
literal filename. The source publisher now resolves exactly one real result inside the scratch
root, preserving the declaration separately and archiving the resolved literal path. Missing,
ambiguous or escaped results refuse filing. `--resume-complete` verifies the original PASS and
current launcher/engine bindings, retains the no-smoke-branch and full-completion checks, and files
the already-completed job without rerunning it. Content bindings make retries reject drift and
preserve terminal bytes. A legacy PASS without a result hash gains a filing-time binding to the
currently full-validated result; it does not gain a fabricated historical hash.

This coordination/churn source fix has 24 passing focused/existing publisher tests. It changes no
allocator or admission policy. The deployed tool snapshot was not edited; recovery used the reviewed
repository source command. GitNexus could not provide a current impact graph for this lane; static
caller review and the focused tests cover the completed-smoke paths, and a wrapper refresh was
started with a completion event.

The tested publisher recovery fix is retained as a historical review patch in
[`publisher-completion-candidate-20261104`](../../data/vidya/publisher-completion-candidate-20261104/).
The coordination owner landed it in `84c3d7c869cf6056c303ebe084e5195f1f705b14` with relayed
operator D9 acknowledgment, reporting 211 passing rowflow/churn tests and five pre-existing
failures. The EXP01 source-control result remains filed.
