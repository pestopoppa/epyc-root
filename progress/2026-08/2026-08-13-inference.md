# 2026-08-13 — AutoKernel r41 and discovery-throughput checkpoint

## Outcome

The post-reboot CPU IQK path has its first rankable known-real intervention, but not yet a matched
archive. Campaign `ak-iqk-v9-20260813-r41` reached terminal `decided`: T0 passed, production remained
byte-identical, both resources released, all 15 precommitted paired blocks favoured IQK, and median
relative prefill gain was **+27.6481989%**. Its T1 event is speed-rank-admissible and records e-value
`321.1221863` against threshold `10`. The durable journal is
`/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-20260813-r41/events.jsonl` (SHA-256
`7085ab228ae0839d0c82301cfd573db519113981c5c9d42ce7613f69c6cba469`).

The paired A/A control is not a negative result. Campaign
`ak-iqk-v9-aa-control-20260813-r41` passed its substantive T0 gates, then stopped before T1 solely
because evaluator identity changed during the evaluation window. Its terminal state is honestly
`t0_failed`, decision is null, pairs are empty, production is unchanged, and both resources released.
The journal is SHA-256 `4aa9786a4ba24dd8d6909fde9170e17bea12afec88df6719819b1b158488d353`.
It cannot pair with the intervention or populate AK-WM-2a.

## Root cause and implementation closure

The control read evaluator identity from a live research checkout after campaign start; research
advanced between those two reads. Research main `a65e638ad9dae750c9cda815cf2d8a7eb392e516` seals the
identity at campaign start and carries that immutable value through the evaluation window. The next
empirical step is therefore a repaired matched-control replay, not another speculative implementation
round.

The same research series also makes the discovery/confirmation cost split executable:

| Commit | Durable behavior |
|---|---|
| `28e7c41a` | Adds a bounded, explicitly nonpromotable screening tier |
| `59a4ec91` | Requires an immutable exact-frame amortized baseline bank and emits uncertain top-K nominations |
| `eb898bd0` | Accepts sealed matched-pair T0 evidence |
| `c376853d` | Proves sealed T0 frame tampering fails closed |
| `de464126` | Produces independently calibrated held-out decode cells |
| `0f137f50` | Resolves the decode control frame at runtime |
| `a65e638a` | Seals evaluator identity at campaign start |
| `c8971a6b` | Executes actual candidate-only screening subprocess batches |
| `6661ca25` | Removes anchor subprocesses from candidate-only screening |
| `9a4bca3b` | Requires an inference-only witness before screening evidence is accepted |
| `c81b67db` | Prepares recipe-bound decode IQK pairs |
| `8a701354` | Binds each decode pair envelope to its calibrated cell |

The governing rule is now explicit in AutoKernel decision AK-D40: only competing model inference on
claimed compute blocks discovery. Services, agents, builds, and every other ordinary system load must
never block or pause it; those conditions are measured as noise/uncertainty. Discovery nominates
top-K, and strict calibrated confirmation is rare and reserved for that shortlist. Screening remains
unable to KEEP, bank, archive, promote, or authorize release.

The candidate-only execution primitive is implemented, but it has not run as a live screen. One
derived empirical-producer task remains explicit rather than hidden: measure and seal the first real
exact-frame amortized anchor bank, including its inference witness, before candidate-only screening.
Synthetic fixture banks remain regression tests and cannot substitute for that evidence.

At this checkpoint `megasync` PID `8860` was resumed and verified in `Sl` state. It is ordinary
service load under AK-D40, recorded for host context and never a reason to block or pause discovery.

## Next empirical chain

1. Rerun the r41 A/A control under research `a65e638a` and the same matched frame.
2. Execute the clean governed decode holdout using the new decode-cell producer.
3. Execute the heldout-bound pair.
4. Project the first strict real matched archive through AK-WM-2a.
5. Run AK-WM-2b/AP-WM-1 observe-only.

This wrap-up session performed documentation and validation only. It ran no inference, build, service
reload, process mutation, research-code change, kernel-tree mutation, or release action.

## Wrap mechanics

- Root documentation base: `a7d6e13788ed95bd684e31a31ceca6c5c4e91259`.
- Research evidence base: `9a4bca3bbdef31d8a4a2a60b5fe0e6f02906b64e`.
- The inference work plane was materialized at `/mnt/raid0/llm/worktrees/mains/inference` on
  `lane/inference`; `check_lane_worktree.py --strict` passed there before edits.
- GitNexus was current. The markdown target has no executable symbol; related consumers are the
  handoff index generator and Kernel-R&D dashboard reader, so validation covers those generated
  contracts rather than claiming a code blast radius.

## R36/r41 handoff divergence reconciliation

The unmerged local checkpoint `23bc70c1` and pushed checkpoint `e1781969` share base `0e3035376`;
the former uniquely recorded the r4 calibration and terminal r34/r35/r36 attempts, while the latter
correctly advanced current state through rankable r41. The active handoff now keeps r4–r36 as a dated
historical checkpoint and completed checklist item, retains r41 as the first rankable intervention,
and advances current execution state to the dry-run-clean fresh r42 pair. It also records the terminal
decode-r2 calibration rejection without treating it as holdout authority.

INF-06 now points to the actual next imperative: execute the fresh r42 matched prefill pair, then
recalibrate decode and complete the held-out/archive/evaluation chain. The obsolete instruction to
rerun the immutable terminal r41 control is removed. The reconciliation also collapsed duplicate and
fragmented checkpoint prose introduced by the divergent edits; no empirical claim, production state,
or campaign artifact was mutated by this documentation repair.

## Discovery throughput, strict-path failure, and controller-first correction

### Outcome

The manual discovery campaign demonstrated the intended throughput plane on both processors. These
records are all `nonpromotable_candidate_only_discovery`; they rank hypotheses but cannot bank,
archive, promote, or authorize release.

| Lane | Exact screen | Median relative effect | Durable result SHA-256 |
|---|---|---:|---|
| CPU prefill pp512 | `ak-iqk-screen-20260813-s7` | `+31.247%` | recorded in its sealed result/b4 bank lineage |
| CPU decode tg128 | `ak-iqk-decode-screen-20260813-s1` | `+7.939%` | recorded in its sealed result/b1 bank lineage |
| MI210 prefill pp512 | `ak-gpu-mmq-mfma-screen-20260813-s2` (`MMQ_MFMA ON→OFF`) | `+26.5965%` | `9508396b5793568b9a458f1bc9374d6cf3855ca0872ab613768099e2654c0887` |
| MI210 prefill pp512 | `ak-gpu-flash-attn-screen-20260813-s1` (`flash_attention OFF→ON`) | `+4.8791%` | `0caa563c2b9f35e3edc66c6550b6175dcf456c8e5d302f2a1cdcadb91c16cdfa` |

The GPU lane went on to emit a broad candidate-only corpus over HIP graph mode, batch/ubatch,
helper-thread counts, polling, mmap and op/KV offload, rocWMMA attention, rope/RMS, and quant-kernel
shape knobs. Large provisional deltas in that corpus remain search signals relative to their own
sealed banks; they are not promoted here as comparable headline claims. Small-model GPU discovery was
allowed to overlap CPU work through the ratified live-governance receipt, while larger model loads
remain scheduled around CPU inference because shared memory bandwidth can materially perturb it.

### Strict execution failure and repair

The strict chain did not fail because the candidate was merely noisy. r49 exposed a real seeded
correctness violation:

`IQ3_XXS MUL_MAT_ID(type_a=iq3_xxs,type_b=f32,n_mats=4,n_used=2,b=0,m=512,n=15,k=256)`

The candidate reported `0.000528677`, exceeding the unchanged `0.0005` bound; the native baseline
passed. The capture parser had also missed failed rows whose console prefix carried diagnostics such
as NaN/inf/sentinel/value/stateful failures. Research parser repair now recognizes that full emitted
schema. Experimental kernel commit `894ec4dc55c829b11b663a46bc9b089d861b73a4` makes the smallest
evidence-backed dispatch correction: IQ3_XXS MMID retains IQK when `ids->ne[1] == 1` and uses native
for `ids->ne[1] > 1`. The exact former failure then passed within the full 1,216-case command; the n=1
IQK engagement check stayed active. Neither the threshold nor seed was weakened.

That source change required a new measurement era. The old f744 calibration was correctly rejected;
fresh decode calibration `ak-controls-v9-894ec4dc-decode-20260813-r6` used the new canonical build and
durably checkpointed:

- AA calibration: `200/200`
- neutral calibration: `60/60`
- anchor-motion calibration: `15/15`

Before controls and terminal composition, the operator requested an immediate stop. The exact sealed
watcher PID `553989` was terminated first, followed by r6 PID `190609` and its captured benchmark child
PID `1119941`. Three follow-up samples found all three absent and all q0-q3 GLOBAL, autokernel, and
autokernel-windowed-control locks acquirable. SIGTERM preempted r6's final `claim_receipt.json` and
summary publication, so the complete checkpoint prefix is recoverable input but **not** accepted
calibration authority. No r51 pair, prefill calibration, heldout pair, archive, champion, promotion,
package, or release ran.

### Root cause of slow progress

The work had become a hand-authored sequence of campaign IDs, manifests, preflight repairs, recovery
watchers, and strict calibration retries. Each individual guard was defensible, but the aggregate was
not AutoKernel: manual orchestration serialized progress and repeatedly spent the main thread on
plumbing instead of hypothesis throughput. The correction is to land the controller before resuming
campaign execution.

The controller implementation is still in progress in an isolated Terra worktree. Its required
authority boundary is explicit:

- discovery cannot load calibration, heldout, champion, readiness, package, or release authority;
- a screening threshold may nominate top-K but cannot mint promotion state;
- small governed MI210 models may overlap CPU discovery, while large GPU loads require a bandwidth
  window;
- planner narrative is never evidence: only a sealed measured result owns observed effect and strategy
  disposition;
- accepted, abandoned, active, and unexplored strategies persist across controller rounds.

This wrap-up does not commit or describe unfinished controller code as landed. The next action is to
finish its tests and independent review, then resume from the controller's governed discovery queue—not
by reviving the stopped manual watcher.
