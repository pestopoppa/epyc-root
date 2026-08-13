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
