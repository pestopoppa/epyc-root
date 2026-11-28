# AP-W66 C22 prefill-budget controls

Compare the archived ON28 decoder on slot 1 against the archived OFF56 prefill on slot 2, with each request at its sealed rendered prompt and archived cache depth. Use fresh C22 processes in control, budget, budget, control order. Preserve the archived trigger by forwarding OFF56 immediately after the first substantive ON28 SSE delta. Record both monotonic timestamps and require native mixed rows that prove ON28 was still decoding when OFF56 started its prefill. Actor names ON28 and OFF56 keep their archived meanings in both arms.

## Stock controller and initial state

- Use C22 source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`, its matching server and libraries, and the archived 35B A3B Q8_0 MTP2 recipe with `-b 2048 -ub 2048`, four split slots and f16 KV. Compare `--prefill-budget-decoding 0 --prefill-budget-target-ms 0` against `--prefill-budget-decoding 256 --prefill-budget-target-ms 900`. The archived argv omitted both flags, whose C22 defaults are zero. Clear `LLAMA_ARG_PREFILL_BUDGET_DECODING` and `LLAMA_ARG_PREFILL_BUDGET_TARGET_MS` for both arms so inherited settings cannot change the contrast. Verify artifact digests, linkage, MI210 residency and release for each isolated launch.
- C22 reserves existing generating rows first and applies the cap to added text prompt rows while a slot is generating. With a positive prior estimate (c), the controller selects `min(256, max(64, floor(900 / c)))`, subject to the residual batch capacity `2048 - decode_rows`. A zero estimate uses the 256 cap. With no generator, the prompt can fill the normal batch. The estimator measures `t_iter / prompt_rows` on every prompt iteration with at least 64 rows, even if no generator is present or both flags are absent. The first eligible sample seeds it and subsequent samples receive weight 0.5. `tools/server/server-context.cpp:4239–4313, 4846–4890, 5344–5416` and `common/arg.cpp:1563–1587` at `ce6fcbbde`.
- Restore `ON28.slot` and `OFF56.slot` using their archived bytes, confirmed SHA-256 values and recorded slots. Require save/restore receipts to match 75,077 and 4,334 cached tokens respectively. Verify served counts of 38 fresh / 75,077 cached for ON28 and 107,912 fresh / 4,334 cached for OFF56, as well as the rendered-input and wire-body digests across arms. The slot restore includes target state, checkpoints and drafter state. It leaves the process-global estimator unchanged. Startup model warmup uses a direct `llama_decode` outside the server-loop accounting. Keep normal startup warmup and perform no completion warmup in the timed process before ON28. If snapshots need regeneration, use a separate untimed process. `tools/server/server-context.cpp:3985–4051, 4254–4297` and `common/common.cpp:1490–1526` at `ce6fcbbde`.
- The whole ON28 prefill totals 38 rows, below the 64-row update minimum. Decode-only steps do not update the estimate. Fresh process + archived restores + only ON28 before the trigger therefore gives an exact zero estimate at the first mixed row in each arm. Record the complete native log, require no prompt rows before ON28, verify the logged pre-trigger estimate is 0.000 and require the first mixed budget to be 256 in the budget arm and 0 in the control. The first mixed line displays the estimate after that row. Small checkpoint-delimited chunks may use fewer rows than the active budget.

## Measurements and interpretation

- Bind the log to the two native task IDs. Count all native prompt iterations from ON28 launch until both tasks finish. C22 logs one `prefill-budget: iter` line for every iteration with prompt rows, including the control. Require positive decode and prompt rows with one generating slot and one prefilling slot to witness a mixed iteration. Report mixed iteration count, mixed OFF56 prompt rows, OFF56 solo prompt rows, mixed elapsed p50/p99/worst and actual applied budget values. Verify mixed plus solo OFF56 rows total 107,912. The peer can continue solo after ON28 uses its 256 tokens, so coverage is essential to interpreting a reduced mixed p99.
- The 27B harness sliced the same native log around peer prefill, from just before the neighbour's thread started until 0.5 s after its first SSE chunk. It kept rows with positive decode and prompt counts. Both native timers start after `pre_decode` and batch render and end after the decode/post-decode loop and optional worker join. C22 also includes `rs_rebuild_slots()`. Queueing, batch preparation and SSE delivery fall outside these timer boundaries. The 27B p99 selects sorted zero-based index `round(0.99 * (n - 1))`. Report it alongside C22's nearest-rank p99 at `ceil(0.99 * n) - 1`. The native timing sites are `tools/server/server-context.cpp:4187–4237` at `0a6c69991` and `4502–4554` at `ce6fcbbde`.
- The final mixed row can include work after the decoder delivered its last output. C22 prints the decoder's request timings and sends the final response before doing the conditional post-generation checkpoint and releasing the slot. Keep that row in the native distribution and report the worst row and count above 900 ms. This can matter when fewer than 100 mixed rows make nearest-rank p99 equal to the maximum. See `tools/server/server-context.cpp:3434–3454, 6752–6758` at `ce6fcbbde`.
- Report ON28 native predicted time for exactly 256 generated tokens and TTFT separately. Supplemental gaps between delivered ON28 output deltas can indicate client-visible delays and include stream buffering and delivery effects. Preserve the peer's TTFT, native prompt time, generated count, finish reason and request wall time. If both caps are 256, verify both actual counts and disclose the peer-cap change from the archival control.
- Report per-pair OFF56 TTFT ratio and the elapsed time from ON28's forward to the later stream finish. Also report elapsed from ON28 forward to OFF56 forward, each stream's elapsed and time from ON28 finish until the later finish when applicable. This distinguishes faster ON28 completion from displacement of the wait onto OFF56.
- The 27B operator accepted 256/900 on the Qwen3.8-27B Q8_0 DFlash2 C6 fork `0a6c69991`, with three 20k decoders, an 80k neighbour, `-b/-ub 512`, `--prefill-budget-align 32` and `--prefill-budget-tail-k 1.0`. That controller rounded total batch rows down to tile boundaries and subtracted an EWMA residual RMS margin from the target. Its 256/900 p99 was 896.2/899.6 ms over 365/364 mixed iterations and its neighbour TTFT ratios were 1.269/1.295. The legacy controller had p99 953/949 ms in the retune. The operator kept the neighbour ratio limit of 1.30 and accepted about 900 ms instead of the prior 670.7 ms p99 criterion for that recipe. C22 has neither tail-fix flag. Use 1.30 and about 900 ms as the requested comparison points and report actual numbers and sample sizes. Their transfer to stock C22 35B and this collision is the experiment. Sources are `origin/main` at `8d27dbd56`, `handoffs/active/kv-cache-program.md:4135–4143`, and the prior packet at `/mnt/raid0/llm/tmp/kvu16g4-overshoot-ab-900-20261106/{IDENTITY.json,job.py,out/results.jsonl,out/summary.json}`.

The prior packet at `/mnt/raid0/llm/tmp/kvu16g4-overshoot-ab-900-20261106` is pinned to source commit `0a6c699911c2ade08c26d551c8a12c4afb4e94aa` and the hashes below.

| File | SHA-256 |
|---|---|
| `IDENTITY.json` | `e62a4e10cc5966d4cfa6058708ca353695f6297d6cf6b55403007d3501b48bc8` |
| `job.py` | `3a6bfe51ba32d36b6de13490a2578bc1256d2aaf4655916441680b9172fedb1f` |
| `kvu16g2_common.py` | `4d50c3ee2fd0d2c9b7b8dfda20b0cbf8dbb0dbdfce8b8da95ccd207ee791d902` |
| `out/results.jsonl` | `8bf37e216da40fa0d3d4a18af7bcf7b1540a0bca5a916a48cdb9787f55685995` |
| `out/summary.json` | `bf8dc081ac1d271639f205a168719a3703c7b3cb6cd84af2549317a3c9bad929` |

## Archived control cross-check

The preserved ON28 p3 fixed-256 control had 83 mixed iterations carrying all 107,912 OFF56 fresh prompt rows. Its native mixed p99 was 1104.3 ms by the 27B method, and nearest-rank p99 and worst were both 1174.9 ms. The pre-trigger estimate was 0.805 ms/token because that process had handled earlier prompt work. The absent flags made the estimate inert in the archival control. OFF56 generated 1,087 tokens in that arm.

```bash
python3 count_iterations.py \
  /mnt/raid0/llm/archive/compute-evidence/ap-w66-pair-20261127-r2/r2/out/run/private/server.log \
  --on28-task 1643 --off56-task 1657 --arm control --historical
```

For a fresh measured log, pass its native task IDs and `--arm control` or `--arm budget`. Fresh runs require the zero estimator witness and exact mixed/solo prompt accounting.

## Six-visit audit

`audit.json` binds the final run, the six raw native logs and launch receipts, the pinned rendered prompt and prefix hashes, and the archived snapshots. The independently reconstructed wire bodies match all six visits. Both streams served exactly 256 tokens in each visit. Each visit restored 75,077 ON28 tokens and 4,334 OFF56 tokens, and each ON28 prefix ran its 38 fresh tokens before OFF56. There was no earlier prompt work. OFF56 forwarded 0.226–0.346 ms after ON28's first substantive SSE event. The budget arm used a cap of 256 on every mixed iteration, so the adaptive rule never lowered the cap in these visits.

| Pair | ON28 decode, control → budget, s | OFF56 TTFT, control → budget, s | TTFT ratio | Both finish, control → budget, s |
|---|---:|---:|---:|---:|
| 1 | 81.595 → 21.097 | 81.290 → 87.668 | 1.078 | 86.370 → 90.729 |
| 2 | 78.257 → 20.591 | 77.712 → 90.567 | 1.165 | 80.915 → 93.413 |
| 3 | 68.680 → 19.691 | 68.542 → 78.772 | 1.149 | 72.889 → 82.349 |

| Pair | Mixed rows, control → budget | OFF56 tokens in mixed rows, control → budget | Prior 27B p99 method, control → budget, ms | Nearest-rank p99 and worst, control → budget, ms |
|---|---:|---:|---:|---:|
| 1 | 83 → 97 | 107,912 → 24,496 | 1098.2 → 291.3 | 1099.9 → 981.4 |
| 2 | 83 → 94 | 107,912 → 23,728 | 1075.3 → 270.4 | 1097.6 → 988.1 |
| 3 | 83 → 91 | 107,912 → 22,960 | 1077.5 → 257.5 | 1097.9 → 259.9 |

Budget visits 1 and 2 each had a single mixed row over 900 ms, their final mixed row. Native server logs put each maximum immediately after ON28 slot release. Budget visit 3 had zero mixed rows over 900 ms. OFF56 spent another 62.241–72.413 s finishing after ON28 returned in the budget visits, versus 2.188–3.800 s in control. OFF56 TTFT stayed within the requested 1.30 ratio. The three joint times increased by 4.359, 12.497 and 9.459 s. Each increase fell within the predeclared largest within-arm joint range of 13.481 s.

Delivered ON28 output-delta nearest-rank p99 gaps for the full streams were 1964.9/1827.0/1070.9 ms in control and 270.3/272.9/254.9 ms with the budget. The gap sample counts were 255/255/154 in control and 255 in every budget visit. The third control recorded a 30.047 s maximum between delivered output deltas. These intervals measure client delivery of substantive SSE deltas and have their own buffering and parsing boundaries.
