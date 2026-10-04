# Earlier research intakes: operational-outcome retrospective

2026-10-04. Operator-requested parallel investigation during wrap-up. This is a selected-source
review of three older completed campaigns, not an exhaustive intake audit, omission-rate estimate,
new intake wave, or permission to execute the application proposals below.

## Findings and applied dispositions

| Earlier campaign | Operational outcome lost or weakened | Applied owner disposition |
|---|---|---|
| Jev/EXL3, September 23 | Shared-state, question-isolated readout became a mechanism note and a Kev-dependent integration, without an independent implementation/comparison outcome. | Refine existing open **TD-1d.3**, not a second cache or scoring platform. |
| Jev/EXL3, September 23 | CPU BF16 versus HIP quantized target confounds precision and backend. | Refine existing open **Missing control for the target-precision hypothesis**, not a second speculative-decoding campaign. |
| Dream-RSI, September 17 | Checkpoint-pruned harness allocation was mapped to a branch/worktree collaboration-spec task. | New PROPOSED **AC-CHECKPOINT-ALLOC**, fixture-first, at most three eligible existing configurations. |
| MI210 compiler/VGPR, September 15 | Multi-token MoE fusion was filed only under an IQ-residency trigger, although the mechanism also covers a concrete Q8 MoE recipe. | New PROPOSED **INF37-MOE-Q8-FUSION**, one GLU compatibility/correctness slice and conditional matched screen. |

Two new application checkboxes, two same-owner/task refinements, and four prospective capture
profiles under existing **VB-RI-OPS-WIRE** were applied by main. One own review checkbox closes
the investigation only. Filing is not application implementation, activation, measured benefit,
resource permission or production promotion. Original approved plans, intake records and completed
campaign checkpoint were not edited.

## 1. Jev/EXL3: implement isolated readout, not just cache reuse

Original filing: `facb730c383c77ea943e71b2df07dbd54aae509b`, entries 1495–1527.
Retained plan: `/home/node/.claude/plans/cryptic-crafting-flurry.md`, SHA-256
`25fe5d1148f81bc89e261784d0bda9bc1ff7b446ccdacb3af6bbb2af4978ba69`.
Record discussion: intake-1498#record and intake-1514#record.

Retained espetro source `common__decision.cpp`, upstream
`5b651c62c54cec86ea0747b3242f7b157142f569`, decodes the shared state into sequence zero,
copies it to question sequences, then decodes question branches (lines 497–555). Its retained
bytes at `/mnt/raid0/llm/tmp/dive-2b-kevserve/espetro/files/common__decision.cpp` hash to
`8c185f3fec9fe2253593d8c487f5c435749f065fe203541df0c389edee293852`.
That supports a mechanism, not transfer of Kev's trained-pointer accuracy or serving speed.

Current orchestrator `src/typed_decisions/runner.py:179` selects serial native scoring.
`native.py` builds a catalogue containing sibling questions and an interleaved answer grammar;
the parked parallel helper also shares that catalogue. Prefix stability/cache telemetry does not
remove sibling visibility. The original plan conditioned the concrete state-once integration on
the model-selection path; TD-1d.3 retained the fork mechanism as a note.

Strong counter-coverage: TD-31 prefix layout/pinned slots, TD-29.M0a actual prefill/cache counts,
KPF-11–16 checkpoint-safe sharing, TD-23 sibling-perturbation/quality/cost fixtures and TD-1d.2b
serialization constraints. CJ-15's implemented prerequisite is parser/fallback conformance,
not a live isolated-question runtime comparison. Reuse all of these; do not claim they are absent.

The refined [TD-1d.3](../../handoffs/active/typed-decision-plane.md) requires an actually selected
question-only runtime path, checkpoint-safe restoration, and three matched arms: cold singletons,
current serial native, isolated shared prefix. Independent questions only; dependent actions stay
host-staged. Singleton equivalence within a measured same-backend floor, sibling invariance,
held-out correctness and positive paired whole-call cost improvement are the deciding outputs.
Unsupported hybrid restoration is unavailable, never a successful zero-cost case.

Existing `decision_receipt.v1`/HS-TD-4, VB-TDP-1 and the research-screen envelope are producer reuse,
not full evidence coverage: decision receipts alone lack probability vectors, branch lineage and
prefill/cache accounting; VB-TDP-1 accepts named studies. VB-RI-OPS-WIRE owns the bounded native
extension before a new measured comparison. No second grading ladder.

### Target precision: remove the backend confound

Retained `/mnt/raid0/llm/tmp/dive-1505/DIVE-RESULT.yaml:121` action D3, SHA-256
`30b335b096f30fe2540419e499c8ef48bf8dbf89b994d4431de47115f86e90ae`, proposed a target-precision
control. The filed control compared CPU full precision with HIP quantized targets. That cannot
separate quantization from backend/verification-shape numerics.

The existing [mtp-refresh control](../../handoffs/active/speculative-decoding-mtp-refresh.md) now
specifies BF16/F16, Q8 and Q4 targets with the same BF16-trained drafter on one backend/build,
fixed verification shape, KV, sampling and target lineage. A CPU-only matrix is permissible if
full precision cannot fit the MI210 envelope; a CPU–HIP bridge is separate. Use a bounded
Qwen3.8-27B/DFlash2 panel, fresh interleaved arms and untouched prompt/seed holdout; retain
weighted/per-position acceptance, numerical divergence and every failed cell. Do not attribute
cross-device throughput or unresolved shape effects to precision.

Counter-coverage: DF2-8 already identifies verification-shape numerical effects; DF2-11 is the
distinct drafter-precision axis; DF2-12/13 own concurrency/parity/checkpoint correctness. Existing
SC44 `dflash2_beliefs.py` and its adapter are integrated, but the current writer seals a named
MI210 concurrency protocol, not a CPU precision matrix. Extend that bounded capture/profile with
reviewed producer-pin changes; do not assume the generic envelope validates causal controls.
Record discussion: intake-1505#record.

### Historical over-decline, not another routing campaign

The old plan grouped prefill activations and foreign-encoder routing under a freeze/no-hidden-state
decline. Those reasons do not establish irrelevance: a foreign encoder need not expose the target's
hidden states, and LRC permits BUILD/MEASURE under the freeze while retaining promotion gates.
Current P2 already owns both routing-feature designs; EP-5 owns label repair, and recent observed-
outcome SDM screens own the classifier comparison. EP-3 documents suite/writer confounding and
unsupported multi-observation failure labels. No separate task was filed because those next steps
are already owned, not because routing features are disallowed. This review did not establish a
specific small encoder's incremental value or extraction cost. Calibration/OOD TD-16–19 and the
consolidated decision contracts are also existing coverage, not newly discovered gaps.

## 2. Dream-RSI: allocate budgets across harness trajectories

Original filing: `1e418919541efd05672a9bf6b8f00d16331310c7`, entries 1435–1459.
Retained `/workspace/tmp/intake-dreamrsi/stage3-plan.md` SHA-256
`02f6322583d1c2d4ca3c748916b599eb17a208d2e9ca519d1eb0ed15c68d67fd`.
Its lingering DRAFT heading does not authenticate approval; the filing commit/progress does.
`merge_stage4.py:37` mapped checkpoint-pruned allocation into AC-branch-per-agent; that task drafts
a collaboration spec, while HS-E1 only requests an evidence packet.

The source describes partial-run checkpoint ranking, pruning configurations and reallocating a
matched total budget. That is a distinct operation from proposing parent candidates or logging
width/depth. Main checked [the versioned primary §5.2](https://arxiv.org/html/2607.18235v1#S5.SS2).
External results are not EPYC measurements. The retained verification extract
`merge_stage2b.py` hashes to `4848c07e5950471a1f183201db0a5c7a6ae7719a2e26c22ca08888decd38d176`;
recorded quote hash `1d78f8a145612a0ec52f4c1b18bfd8b48554debd785ba02f37811a4cf47c1a75`.
Complete cached original HTML/PDF was not located; these hashes attest derived verification, not
original source bytes. `/tmp/dreamrsi_v1.html` is a different paper and was not substituted.

Current `run.py:1666` exposes plain/bounded actor seats and inline/variable context controls with
backend restrictions. `serial_run.py:290` supports completed-batch continuation while several
actor controls change; actor-seat is not one of its stable-resume exclusions. `resume.py:38` owns
interrupted-candidate recovery, not quality-ranked allocation. `run.py:5473` explicitly calls
`width_depth_trajectory` ordered completion points, not an adaptive policy. `pipeline.py:28` uses
one shared advancing champion, so those worker lanes are not independent harness trajectories.

New [AC-CHECKPOINT-ALLOC](../../handoffs/active/agent-collab-rnd-harness.md) reuses existing
continuations, actor-call capture, journals and selector seams. At most three eligible existing
same-model/backend configurations, separate stores/worktrees/continuations, batch boundaries,
prefix-visible score-bearing checkpoint records and a bounded allocation controller. Compare
matched incumbent repetition, unpruned diversity and simple repeated sampling; include failures
and allocation overhead across call/token/evaluator/wall budgets. Calibration and later untouched
run/seed holdout are distinct. Unsupported counterfactual continuations remain missing, not
fabricated from a selected parent's result. Fixtures first; no live policy activation.

Strongest counter-coverage: OAB-9 already compared inline/variable; OAB-9b explicitly forbids an
unchanged rerun and folds revisiting into OAB-4's orchestrator arm. DS41-C20 already covers
plain/bounded. These are constraints on eligible pool selection, not invitations to repeat losing
arms. Fewer than two comparable eligible arms returns unsupported. AK-WM-3/parent-selector replay,
AK cost credit/lineage/adaptive-search tasks, SEQ-4, AC-CORAL and existing promotion controls cover
adjacent axes, not this allocation operation. No duplicates filed for them.

HARNESS_RUN_POLICY is a template without a demonstrated runtime loader; it cannot by itself close
an executable harness-policy opportunity. Existing HIL tasks already own the operator loop.
The old blanket CPU/no-weight-update training decline was too broad given EPYC's actual router
trainer, but that does not verify advisor-RL fit for the unverified PACEvolve++ record. No new
training task is justified by this selected review. Record discussion: intake-1444#record.

## 3. MI210: distinguish compiler coverage from non-IQ fusion

Original filing: `8571fd3ebb68dde2baa128f97c7e588bd0b5a482`, entries 1398–1424 (old IDs plus 31).
Retained plan `/home/node/.claude/plans/melodic-inventing-sonnet.md` SHA-256
`5f240115c0e5fae625a0d854217b0555afdfa8cc3e13a2cf583d318e6e08d7c2`.
Retained completed checkpoint `ab/intake/research-session.bb611630.json` in
`/mnt/raid0/llm/worktrees/vgpr-compiler-ab-20260915/`, SHA-256
`a1156dd56309185fde7eaa2050215f5dbb94084146e5445d8666eb00696198e0`.

The unroll/compiler levers are already owned by AK-QL-7/8 and conditional separate-build-recipe
work S3-AKU-19. The tracked static compiler artifact
`artifacts/gpu-aux-baselines/a10_iq2_vgpr_compiler_ab_20260915.md`, SHA-256
`79e1a355ac3f1f37fe46b8dae79636b3e70a1e453898d13124734254a6670543`, does not measure end-to-end
throughput. Register reduction is not a blanket toolchain flag recommendation. No demonstrated
current ROCm-6.2 failure warrants an unpin or new toolchain migration; existing upgrade gates stand.

However, INF37-IQ-2(3) put multi-token MoE GLU/top-k fusion entirely behind IQ residency. The
[upstream change](https://github.com/ggml-org/llama.cpp/pull/27621), commit
`41ef91f7c8046087cdfbb276b79bff311ecf1c6d`, is not IQ-only. Main's added read-only qualification:

- Frozen v10 HEAD is `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, tracked-clean. The upstream commit
  is not its ancestor; `ggml-cuda.cu:1791–1820` still rejects MUL_MAT_ID with `dst->ne[2] != 1`.
- The canonical Qwen3.6-35B-A3B Q8 GPU MTP recipe uses draft width four. Its GGUF metadata has
  41 separate `ffn_gate_exps` and 41 `ffn_up_exps` Q8_0 tensors. This is static source/model
  eligibility, not actual verify width, running route/residency, full weight identity or a speedup.
- The [AMD garbage-output report](https://github.com/ggml-org/llama.cpp/issues/28113) implicates
  that change on a different AMD/ROCm configuration. Closed/bug-unconfirmed status supplies no
  fixing patch and is not a local gfx90a result.
- v10 preserves a CPU-only top-k guard after a GPU regression. A GLU slice must retain it; do not
  bundle top-k or conflate the existing MMQ scheduling/nondeterminism work with GLU fusion.

Qualification bindings: `ggml-cuda.cu` SHA-256
`1688f1ac395b89c86f386294a4d99271d9c4781dae4d72ad868e1a7b40992779`;
`mmvq.cu` `7ca6eba8866839fdb65efaf9d86dea7854577bf44860f2e83a76a8b45bb4f468`;
research `artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json`
`a9d9c5ff7945ad54b7c56cacab30b0ab0e045ae2574107234388858c4c862116`.
GGUF path `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`; full weight hash was not computed.
Metadata inspection used the existing mmap GGUF reader under CPU-region q0, no inference or GPU.

New [INF37-MOE-Q8-FUSION](../../handoffs/active/mi210-q8-dequant-gemv-roofline.md) targets that one
recipe in a fresh experimental candidate: resolve/fix AMD correctness, differential fusion-on/off/
production controls, actual runtime eligibility, then a conditional bounded paired MTP screen.
Any correctness failure, ineligible path or no cost gain beyond uncertainty stops it. This is not
a generic fusion campaign, promotion or permission to modify/build production. Record discussion:
intake-1420#record.

## Coverage, provenance and limits

Three read-only agents investigated disjoint campaigns. Main reviewed source-to-plan-to-owner
bindings, counter-coverage and concrete code, then performed the additional Q8 static qualification
after the compiler reviewer left model eligibility unresolved. Agents did not apply rows, stubs or
intake edits. All three agents were closed after review.

Read roots: root initially `3ff25ed285286b5fe531d3d1463c4405f997e0d4`; orchestrator
`c5dc4ae5e99a30636d6c4307f4f0acf2c2e59fa4`; research
`412e8fc11d153554354f51c9f9f70b9c984578f8`. Shared unrelated dirty work was preserved. Selected
consumer byte bindings: native scorer `314d345fff1c21fcc8d60cede240b1d462b9559b5de402c80e2164ea38b6be4e`,
selector replay `af9ee48011068ce6da99d80a84c76afbfb67596fb6e1c2d9982723aec20356eb`,
serial continuation `fdbf9fd6e38c65e7caf23b2ffa33af09afad71dc8773869387c42606c9fc2684`.
Line references are read hints; task text and bound bytes identify the work.

Explicit non-duplicate dispositions: activation/foreign-encoder routing, calibration/OOD, parent
selectors, operator-loop tasks, compiler falsifiers/build recipes and toolchain guardrails remain
with existing owners. Advisor training is unestablished by the inspected source/cohort, not banned.
The previously recovered GEPA/ParEval/PAW and preceding-three audit findings are not counted again.
This report does not assert that all useful actionables were found or estimate how common the
failure is across the intake corpus.

The skill refinement is already implemented in `9069c992`, promoted by `3ff25ed28`: source-first
opportunities, exact applied outcome bindings, actionable additions and full steering reconciliation.
This wrap-up reran **73 tests / 218 subtests**. Those structural checks cannot establish semantic
usefulness; the current review illustrates why source-first practical review remains mandatory.
No skill/code changes, model download/training, kernel build or application benchmark occurred.

Four prospective producer profiles are registered immediately in the
[source table](../../scripts/vidya/adapters/README.md) and
[VB-RI-OPS-WIRE](../../handoffs/active/vidya-belief-substrate-program.md). Native capture and thin
projection precede decision-bearing runs. Existing typed/kernel/actor/DFlash carriers are reused
only where their actual contracts suffice; no historical tuple backfill, new protocol or grader.
This qualitative retrospective is not an omission-rate producer.

Validation and wrap-up custody are recorded in
[the session progress shard](../../progress/2026-10/2026-10-04-intake-earlier-wrap.md).
