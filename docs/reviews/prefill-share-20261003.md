> **Caveat (main session, 2026-10-03):** almost all :8083 and :8074 traffic in this window was the DS41 planner seat (09-23 to 09-29) and the C95 harness experiment (10-01), not organic production use. Per-role shares describe agentic-planner load, which DS41 has since moved to external models.

## 0. Sources and anchoring

**Logs and timestamps**
- **Logs:** `/mnt/raid0/llm/epyc-orchestrator/logs/{llama-server-8070,8080,8180,8074,8083,vision-worker-8086,embedder-8090..8095}.log`.
- **No rotation:** `orchestrator_stack.py` opens these logs with mode "a" (`scripts/server/orchestrator_stack.py:2153/1926/1997`), so there are no rotated shards to collect.
- **Timestamp format:** `M.SS.mmm.uuu`, counted from process start.

**Wall-clock anchors** (all listed in `parse.py:ANCHORS`)
- **STATE:** `started_at` in `logs/orchestrator_state.json.pre-archswap-20260928T041545Z`.
  - 8070, 8080, 8180 and 8074 at 09-24 18:46–18:48Z.
  - 8083 at 09-27 02:51:37Z.
  - 8086 at 09-22 14:51 and 09-27 02:51:41Z.
  - Embedders at 09-27 11:25Z.
- **CHAIN:** each earlier segment is placed using the exact "cleaning up before exit" time of the segment after it.
  - The frontdoor, 8074 and embedder chains land on 09-22 14:50–14:52.
  - The 8083 chain starts from ":8083 stopped 15:36Z" in `progress/2026-09/2026-09-24-inference.md` and lands on 09-22 14:49.
  - Both agree with the lineup relaunch.
- **External checks:**
  - 8074 exits at 10-01 18:11, matching `ds41-c95/peer-load.log` archswap4 relaunch at 18:10:45.
  - 8070's last line is at 18:53, matching ri18-revise END at 18:53:22.
- **8083 segments anchored from DS41 artifacts:**
  - The 09-29 07:11 to 10-01 12:16 segment comes from `ds41-c95/diagnosis-27b-report.md` (±1–3 min).
  - The 10-01 12:16 segment is anchored to the probe end in `probe-decode-vs-context.mtp.json` (19:10:46Z).
  - The segment starting 09-24 19:30 assumes a back-to-back relaunch, so it may be a few minutes off.

**Fields derived per request**
- **cache_n** = n_tokens at release − prompt_n − (predicted_n − 1). This was exact on rows I checked by hand.
- **Slot selection** (LCP vs LRU) and f_keep come from the preceding `get_availabl` line.
- **Cancelled requests:** the time they burned is estimated from launch to release, split at the last "prompt processing t=" line.

**Not usable**
- `epyc-orchestrator/logs/progress/*.jsonl`:
  - `prompt_eval_ms` is 0.0 on 54/54 completions checked.
  - It records only about 20–40 tasks per day.
  - The files for 09-26 and 09-28–30 are missing.
- `orchestrator.log` has no per-call timings.

## 1. Totals (window 09-24 00:00Z to 10-01 21:00Z)

See the table above. Additional figures:

**Prompt and generated tokens**

| port | new prompt tokens | generated tokens |
|---|---|---|
| 8070 | 0.97M | 1.16M |
| 8074 | 1.20M (86.9M cached) | 0.28M |
| 8083 | 28.1M (162.7M cached) | 5.28M |
| embedders | 12.24M | – |

**Requests that never finished**
- **8083:** 125 requests, about 20.6k s of prefill and 28.1k s of decode. In 8083 log lines 35063–213100 there are:
  - 131 cancels;
  - 39 "Context size has been exceeded" errors;
  - 456 "failed to find a memory slot" warnings;
  - 929 prompt-cache evictions;
  - 5 state-restore failures.
- **8070:** 37 requests, about 240 s of prefill and 5.4k s of decode.

**Wall-clock occupancy**
- 8083 was busy 272k s, 40% of the window. Prefill was active in 30.4% of that busy time.
- Prefill was active in 38% of 8074's busy time and 7.4% of 8070's.

**Traffic attribution** (from timestamps cross-checked with progress notes)
- **8074:** 09-23 06–09Z and 09-24 00–08Z were the DS41 local Flash-Next planner, replaced by the 27B at 09-24 ~09:16. The rest of the window has 4 requests.
- **8083:**
  - 09-24 to 09-29, DS41 planner seat (opencode / codex / Hermes): 3,281 requests, prefill 28.2%.
  - 10-01 before 12:16, C95: 1,331 requests, 17.7%.
  - After 12:16, probe: 27 requests.
- **8070:**
  - 1,265 of its 1,614 requests ran on 10-01. They are most likely the C95 orchestrator (orv) arm at 03–13Z, plus RI-18 revise at 18:10–18:53.
  - About 156 requests are a synthetic probe (30-token prompt, 256-token output), replayed identically on 8080 and 8180. That probe is essentially all of the halves' traffic.
- **Embedders:** about 26k instance-seconds on 09-26/27 (bulk work plus the placement arms in `data/embedder_placement/arms/*20260927*`) and about 1.7k s on 10-01.

## 2. Distributions

| port | full prompt p50/p90/p99 | new tokens p50/p90/p99 | prefill s p50/p90/p99/max | prefill > decode |
|---|---|---|---|---|
| 8070 | 392 / 1,013 / 16,931 | 228 / 834 / 16,197 | 0.54 / 1.53 / 50.5 / 56.7 | 7.4% |
| 8074 | 84,971 / 159,354 / 211,765 | 191 / 1,680 / 38,667 | 4.5 / 18.9 / 264 / 435 | 34.1% |
| 8083 | 38,673 / 86,988 / 144,846 | 721 / 20,702 / 56,271 | 3.2 / 46.3 / 326 / 878 | 32.4% |

**Large and cold prefills**
- **8083:**
  - 737 prefills of ≥8k new tokens took 79.8k s, 81% of its prefill.
  - 540 of them were cold (cache_n < 1k), taking 71.2k s.
  - 535 were LRU-selected, meaning no slot held a matching prefix: 72.7k s, 74% of prefill.
  - 96 were near-duplicates (within 2% of the same length, started within 15 min of each other): 20.9k s. Example: tasks 19630 and 19631 each prefilled 46,230 tokens at 09-29 08:05:59Z, concurrently, taking 395 s and 665 s.
- **8070:** 21 cold large prefills took 1,051 s, 40% of its prefill. 14 were near-duplicates (744 s).

## 3. Rates (tok/s)

Prefill rates use only prefills of ≥512 new tokens, bucketed by context at the end of prefill.

| port | prefill by context | decode by context |
|---|---|---|
| 8070 | 0–2k 540 · 2–8k 438 · 8–32k 309 (never ran two slots at once, so these are solo rates) | 39–44 |
| 8074 | 2–8k 179 · 32–64k 146 · ≥64k 82 (about 210 at ≤8k over the lineup era) | 16–17 |
| 8083 all | 2–8k 560 · 8–32k 448 · 32–64k 257 · ≥64k 325 | 8–32k 23.1 · 32–64k 17.3 · ≥64k 21.9 |
| 8083 solo | 2–8k 790 · 8–32k 658 · 32–64k 471 · ≥64k 346 | – |

- **Small prefills are latency-bound:** under 128 new tokens, prefill runs at 155 tok/s (8070), 32 (8074) and 58 (8083).
- **The probe agrees with the solo rates:** it measured 850 tok/s at 2k and 487 at 80k.
- **Falloff with depth:** prefill drops about 2.2–2.3× with context. GEMM cost per token does not grow with context, so this is attention cost.
- **Draft acceptance:** 65.7% on 8070, 88.2% on 8074, 53.4% on 8083.

## 4. Concurrency (8083: 4 slots, unified KV)

| what the other slots were doing during decode | decode tok/s, <32k / ≥32k context |
|---|---|
| nothing (solo) | 36.9 / 28.6 |
| decoding only | 21.1 / 19.4 |
| prefilling for ≥10% of the decode window | 9.0 / 7.8 |

- **Decode time lost to neighbour prefill:** about 60.5k s against the decode-only rate, or 74.1k s against the solo rate. That is about 22% of 8083's decode slot-seconds.
- **Cross-server CPU effects are weak in this data:**
  - 8070 decoded at 40.8 tok/s with embedders active and 45.5 with them idle. The traffic differs between those samples, so this is confounded.
  - 8070 and 8074 almost never overlapped.

## 5. Verdict

A 2× prefill speedup beats a 10% decode speedup when prefill is more than 15.4% of prefill+decode time.

- **8083:**
  - A 2× prefill speedup saves about 89k s: 49.1k direct, about 30k of stall and about 10k from killed requests.
  - A 10% decode speedup saves about 27k s.
  - For 69% of requests, the prefill speedup is the bigger win.
  - The bigger lever is still caching and admission: shared-prefix reuse, staggered arm starts, a larger `--cache-ram`, and avoiding KV pressure.
  - This is GPU HIP/FA work.
- **8074:** a 2× prefill speedup saves 5.7k s against 1.6k s for decode, but the role has been nearly idle since 09-24. If a CPU long-context seat returns, target attention at long context as well as GEMM.
- **8070 and halves:** a 10% decode speedup saves 2.5k s, against 1.3k s for 2× prefill. The current CPU-decode campaign is correct for these roles; their prefill tail is a caching fix.
- **Embedders:** all prefill-type GEMM, 34k instance-seconds at 330–380 tok/s per instance, but they are not on the latency path.

## 6. Gaps and minimal fixes (recommendations only)

1. **No wall-clock time in server logs.** Fix: the stack tool writes one banner line before exec: `=== launch <ISO-UTC> pid role argv ===`.
2. **No record of which role or client sent each request.** Fix: the orchestrator logs role, request_id and the llama.cpp `timings` object per call, and the DS41 harnesses standardize on the `wire.jsonl` schema.
3. **`progress/*.jsonl` `prompt_eval_ms` is always 0.0, and day files are missing.** Fix: fill the field from `timings` and investigate the missing files.
4. **Cancelled requests print no timing.** Fix: add a one-line cancel summary.
5. **Queue wait (arrival to slot launch) is not logged.** Fix: log it per task.
6. **Embedders log launch and release only.** Low priority.
7. **8080, 8180 and 8086 have too little real traffic to conclude anything.**

**Belief kernel:** add an adapter row in `scripts/vidya/adapters/README.md` and a task in `handoffs/active/vidya-belief-substrate-program.md` for per-request serving timings. That is for the owning session to apply; I wrote nothing.