# C22 W66 request replay

The largest reproducible penalty came from prefill overlapping another request's decode. ON 28's equal-256-token control took 2.38 s to decode alone and 71.60 s with OFF 56 prefilling. OFF 56's isolated prefix-preservation treatment saved about 64.5 s of native prefill in each reversed block. Its output quality varied across those blocks. The standalone two-pass A3B gate remains parked. The next performance target is the recorded mixed prefill/decode workload.

The run replayed all four pinned targets against their primary recorded peers on C22. Each target used three comparison blocks, including a fixed-length final block when natural generation lengths diverged. Native execution ran from 16:41:01 to 17:04:58 UTC on 2026-11-27 and exited with rc=0. [Numeric results and source identities](../../artifacts/analysis/ap-w66-pair/summary.json) · [Pre-replay state plan](../../artifacts/analysis/ap-w66-pair-states/plan.json)

## Matched inputs and recipe

The model was Qwen3.6-35B-A3B-MTP Q8_0, C22 `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`, four split-KV slots of 131,072 tokens each, f16 K/V, MTP draft maximum two, batch/microbatch 2,048 and the original per-request sampling and template settings. The driver and server used the recorded CPUs 88–95 and NUMA node 3. `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0` constrained ROCr helper threads to that allocation. This explicit environment difference applied to every arm. Loaded executable and all eight llama/ggml shared objects matched the sealed C22 store hashes. Each request retained in-window own-PID KFD, mapped HIP library and VRAM evidence.

| Target | Historical fresh / cached tokens | Primary peer | Controlled overlap |
|---|---:|---|---|
| ON 28 | 38 / 75,077 | OFF 56 | Peer prefill during target decode |
| OFF 56 | 107,912 / 4,334 | ON 28 | Target prefill during peer decode |
| OFF 52 | 512 / 108,476 | ON 27 | Both requests decoding |
| ON 29 | 38 / 76,143 | OFF 56 | Both requests decoding after peer prefill |

All original-input scored visits reproduced these fresh/cached counts. Four pinned archive bodies, their decoded bytes and canonical receipt hashes were independently verified. The fifth request, ON 27, supplied OFF 52's recorded peer. [Input custody](../../artifacts/analysis/ap-w66-replay-inputs/requests.json) · [Native token proof](../../artifacts/analysis/ap-w66-pair-states/native-prefix-ids.json)

Historical KV snapshots were unavailable. The replay computed exact native C22 target token IDs, preloaded their leading tokens to the recorded cached depth, and saved a native slot snapshot. Each arm independently erased and restored that snapshot, verifying its hash and restored-token count. This reconstructs observable cache equivalence. Historical draft and KV bytes were unavailable for comparison. Peer launch was triggered by the first visible delta to create the intended phase overlap under current speed. ON 28's historical OFF 56 offset was +35.29 s; the controlled visits used +0.33 to +0.42 s. The state plan retains all eleven historical overlaps, while these visits isolate the primary peer. The receipts retain achieved offsets.

## Timing attribution

The question was whether long fresh prefill, isolated decode, or concurrent-request interference accounted for the excess seconds. The stopping rule required reversal, effects above observed same-arm variation, or a maximum of three blocks per target. Request order was alone then peer in block one and peer then alone in block two. OFF 56 inserted preservation between those arms to reverse its isolated preservation comparison too. No target exceeded the three-block cap. Natural output divergence triggered equal-256-token controls for ON 28, OFF 56 and OFF 52.

| Equal-256-token control | Alone prefill s | Peer prefill s | Alone decode s | Peer decode s | Added decode s |
|---|---:|---:|---:|---:|---:|
| ON 28 | 0.253 | 0.252 | 2.379 | 71.596 | 69.217 |
| OFF 56 | 66.403 | 71.450 | 2.646 | 5.066 | 2.420 |
| OFF 52 | 0.600 | 0.716 | 2.550 | 3.731 | 1.181 |

ON 28's natural decode time increased from 2.677 to 77.343 s in the first block and from 8.296 to 71.318 s under reversal. Generated lengths differed substantially. The equal-length control corroborates the large interference penalty. The native log records mixed batches containing decode rows and OFF 56 prompt tokens. Estimated peer-prefill overlap was 71.014 s in the fixed control. Delivered TTFT remained about 0.42 s because the peer was launched after ON 28's first delta.

OFF 56's natural prefill rose from 65.969 to 71.812 s with the peer and from 65.800 to 71.029 s under reversal. The increases of 5.84 and 5.23 s exceed the observed repeat ranges. The fixed control retained that prefill penalty. OFF 52's natural lengths changed, but its equal-length control shows a smaller ordinary decode-sharing cost.

ON 29 retained 77 tokens in every isolated visit and 77–78 with its peer. Native decode rose by 0.447, 0.395 and 0.517 s. All six outputs proposed the same useful scoped read. Its short-prefill effect changed sign, +2.729, −0.954 and +0.434 s. Short-prefill attribution remains unresolved after the third block.

Native phase durations, streamed first-delta times and end times are retained separately. Per-stream wall/TTFT, sum(tokens)/sum(native seconds), request medians and aggregate rates over non-double-counted phase unions are in the numeric summary. Cross-stream phase boundaries are approximations derived from native durations and timing-print or delivery timestamps. Mixed-batch logs independently corroborate the long overlap. The pairs are diagnostic observations on a shared live host. They supply no formal speedup interval or kernel promotion gate.

## Prefix preservation and accepted output

| Isolated OFF 56 block | Original fresh / cached | Preserved fresh / cached | Original prefill s | Preserved prefill s | Original wall s | Preserved wall s |
|---|---:|---:|---:|---:|---:|---:|
| Original before preserved | 107,912 / 4,334 | 1,701 / 110,761 | 65.969 | 1.355 | 78.293 | 13.046 |
| Preserved before original | 107,912 / 4,334 | 1,701 / 110,761 | 65.800 | 1.356 | 77.465 | 14.111 |

Preservation saved 64.61 and 64.44 s of native prefill, with wall savings of 65.25 and 63.35 s. Preserved summaries were longer, so fewer generated tokens cannot explain this improvement. The treatment changes rendered input by retaining prior template material. Its benefit to a concurrent neighbor was not measured directly.

The frozen rubric reviewed the immediate task state, source contracts, exact proposed edits and summary requirements. Generated tool calls stayed inert. A valid continuation received credit for grounded next-step progress. The underlying coding repair remains unverified. Six length-stopped controls were excluded from quality grading. [Rubric and all judgments](../../artifacts/analysis/ap-w66-pair-quality/README.md) · [Output hashes and coverage](../../artifacts/analysis/ap-w66-pair-quality/output-custody.json)

| Natural target | Accepted alone | Accepted with peer | Accepted preserved |
|---|---:|---:|---:|
| ON 28 | 0/2 | 1/2 | — |
| OFF 56 | 1/2 | 1/2 | 1/2 |
| OFF 52 | 2/2 | 1/2 | — |
| ON 29 | 3/3 | 3/3 | — |

Across twenty natural outputs, the frozen rubric judged ten accepted continuations, three substantively accepted summaries, four partial and three rejected. All six OFF 56 summaries additionally emitted unwanted literal template wrappers, so none fully complied with that formatting constraint. Original and preserved OFF 56 summary judgments reversed between blocks. These observations establish neither a repeatable quality loss nor equivalent quality. Natural output length and quality variation prevent a quality-qualified goodput claim from the latency reductions.

## Decision and custody

Keep the standalone two-pass gate parked. Its reopening conditions remain a larger C22 target-workload share or a fused design that removes launches. The replay localizes the largest excess time to mixed prefill/decode execution and identifies a large cache-retention opportunity whose quality needs control. The large historical ON 28 penalty disappeared when the peer was removed at the same cached depth. ON 29's smaller decode-sharing cost and unresolved short-prefill variation remain in the receipts.

The private archive is `/mnt/raid0/llm/archive/compute-evidence/ap-w66-pair-20261127-r2/`. It retains request/stream bytes, prefix IDs, snapshots, runtime resources, original qualification attempts and source manifests. Public artifacts retain hashes and numeric records. [Runner and receipts](../../artifacts/analysis/ap-w66-pair/) · [Rowflow completion](../../artifacts/analysis/ap-w66-pair/rowflow-ended.txt)

Qualification corrected affinity inheritance, helper-thread expansion and asynchronous KFD retirement checks. The final run completed successfully. Server PID 2463874 exited with rc=0. The captured supervisor, lock, driver and server PIDs were absent after cleanup, KFD was empty and GPU busy was 0%. This replay performed no device reset.

Next: RTG-02 owns the cache-quality and mixed-phase scheduling decision using these exact C22 inputs.
