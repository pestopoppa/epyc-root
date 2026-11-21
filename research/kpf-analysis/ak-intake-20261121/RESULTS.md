# ak-intake-20261121 KPF non-inference boxes — results (2026-11-21)

Scripts here are zero-inference (log readers / models). Data: `/mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log` (27 MB, verbosity 3, Qwen3.6-27B-MTP-Q8_0 on the MI210, np 2, n_batch=n_ubatch=2048, n_rs_seq=8, 1708 timed requests, 2026-10-26/27 session) and `logs/serving_calls/serving_calls.jsonl` (215 records, 2026-10-03..11-19). The 8183 log (April, no timestamps) gives counts only and was not used.

Caveat for every table: ONE recipe, ONE agentic (opencode-style) traffic pattern, ONE server build older than C17. A second recipe with a verbose log does not exist on disk; the verdicts below say so.

## KPF-64-CUTS (`kpf64_cuts.py`, `kpf64_result.json`)
Batch i spans [K_i, K_i+1) between consecutive `cached n_tokens` lines; cut kind = distance N-K of the checkpoint boundary. Extra wall of a cut = fixed part of the partial batch it ends, max(0, T - rho*L), rho = the request's own full-ubatch s/token (global 1.649 ms/tok); plus checkpoint creation wall.

| cut kind | cuts / req | share of reqs | extra wall (s) | % of prefill wall |
|---|---|---|---|---|
| user-message start / junction | 0.233 | 18.9% | 1604.9 | 5.22 |
| near-end other (batch-budget split, N-36..N-40) | 0.374 | 36.5% | 669.5 | 2.18 |
| n-(4+n_ubatch) (capped at n_batch: N-2048) | 0.396 | 39.6% | 786.5 | 2.56 |
| n-4 | 0.997 | 99.7% | 1641.8 | 5.34 |
| total | 2.0 | | 4702.7 | 15.3 (upper-ish) |

Extra ubatches per request 1.616 = extra server iterations per request 1.616 (n_batch == n_ubatch so every break is a ubatch). Checkpoint creation: 1.75 per request, 198 s = 0.64% of prefill wall (~53 ms each). By size: n_proc <= 200 tokens (28% of requests, 220 s): cuts cost 77% of their prefill; 200-2048: 51%; > 2048 (94% of the wall): 12.8%. Prefill wall 30,764 s.
Verdict: **material** (>= 3% on the one served recipe observed, and the n-4 cut alone is 5.3%). Upper-ish because each interval includes other slots' co-scheduled work; a lower bound was not separable from the log. Triggers the Monitor item "per-sequence export-offset input" (kv-cache-program.md Monitor line).

## KPF-18.4 (`kpf18_4_overlap.py`, `kpf184_result.json`)
No `n_fork_tokens` exists in served traffic (slot fork off; 0 hits in logs and serving_calls). Overlap depth d := LCP of the request with its routed slot = sim_best * N. 1716 requests: 252 zero overlap, 1464 with overlap; d in 16k-131k for 94%; deciles 33.5k..98.2k; modal 512-token bin holds 1.4% of mass. Not one spike (the criterion "90% in one spike" is far from met): the depth is a continuum because d is the previous turn's end, which moves every turn. Expected recompute (tokens/request beyond restore point), absolute-position DP over the empirical d: none 54,660; M=1 26,015; M=2 17,216; M=4 10,546; M=8 5,840; dense-every-8192 3,393 (6.3 ckpts needed mean); dense-every-2048 865 (26 ckpts); single checkpoint at the modal depth 54,444. Actual server (turn-end checkpoint after generation, PFXC-A1 plus n-4): mean 319 tokens/request beyond restore, 33% of requests lose > 16 tokens.
Verdict: **not a single spike -> trigger the multi-boundary checkpoint_at policy** (Monitor item). Reading: the right boundaries are relative (turn ends / system-prompt end), not absolute positions; the absolute DP is a bound showing M=8 absolute positions cannot beat the already-deployed turn-end rule (319 tokens). Per-role split impossible: the log is one server; all roles on :8083 share it.

## KPF-22-QUEUE-SHARE (`kpf22_queue_share.py`, `kpf22_result.txt`)
serving_calls.jsonl: 215 calls. `kv_admission` (SharedKVPoolAdmission record) present on 12; queue_wait_ms median ~6 ms; ONE queued event (48.9 s of a 58.4 s request = 83.7%, a long-prefill-lease wait behind another long prefill). Orchestrator `queue.pre_dispatch_wait_ms` (a different, earlier queue) = 57.4% of wall across all 215 calls but those are autopilot/batch calls with no fan-out.
| in-flight on server at start | calls | pre-dispatch wait / wall | kv-pool records | kv queue / wall |
|---|---|---|---|---|
| 0 | 214 | 57.4% | 11 | 0.03% |
| 1 | 1 | 84.0% | 1 | 83.7% |
Verdict: **precondition NOT established.** No load level with real fan-out exists in the persisted data (214/215 calls started on an idle server); head-blocked share of kv-queue time is 99.8% but from a single event (n=1), and `admission_record` does not record the wait cause, so head-blocked share per load level cannot be computed. Needed (design only, not published): add `wait_cause` (lease|tokens|fcfs-head) and queue-position to `admission_record`, then one np>=2 fan-out row on the served stack; until then queue-time compaction stays unmotivated.
