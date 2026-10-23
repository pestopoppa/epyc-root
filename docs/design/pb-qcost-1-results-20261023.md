# PB-QCOST-1 results, offline re-analysis (2026-10-23, workspace-f8)

Task: `handoffs/active/gpu-serving-tie-in-program.md` PB-QCOST-1 (the n = 1 / n = 4 re-validation, per-n intercept with
noise floor and unit, held-out P99 absolute residual). Logs and recorded data only; no inference was run today.

## Headline

- **The recorded 2026-10-21 run already contains everything the task text asks for; this analysis re-derives it from the
  raw per-interval records and reproduces it exactly** (n = 1: A = 766.85 ms/iter, held-out P99 abs 72.29 ms/iter; n = 4:
  A = 871.40 ms/iter, held-out P99 abs 210.69 ms/iter). Request-level held-out MAPE: frozen model 12.84 % (n = 1) and
  26.32 % (n = 4) against the predeclared 10 % bar, so the frozen model FAILS; the per-n refit passes (2.40 %, 3.83 %).
- **New, from the same data:**
  1. The refit identifies only the c-slope at one fixed q (504 tokens at n = 1, 480 at n = 4). The q coefficient is NOT
     identified by this run. See "What the refit does not identify".
  2. Slope and intercept are monotone in decode rows across the three n values (table below), which is the pattern a
     real decode-batch effect would give and a contention artifact would not obviously give.
  3. Leave-one-length-out (LOLO) over all five lengths gives a pooled P99 abs residual of 73.8 ms/iter (n = 1) and
     122.4 ms/iter (n = 4), against 72.3 and 210.7 for the predeclared 3/2 split. The n = 4 split figure is the more
     pessimistic one; max abs residual at n = 4 is 282 ms/iter.
  4. Conditional replay of the 80k neighbour with n-specific coefficients: the fitted constant-ms budget cuts the worst
     iteration by 26.3 % (n = 1), 27.2 % (n = 3, offline fit), 27.8 % (n = 4) at iso neighbour-prefill time, with decode
     proxy ratio 1.005 / 1.005 / 1.000 (no mean decode gain, as in the 2026-10-20 result).
- **Done: NO.** The checkbox needs the live A/B ("follows KVU-16g's A/B"); the confirm row needs an uncontended re-run.
  Nothing ticked. A dated note was written to the handoff.

## Method

1. Parsed `pb_qcost_1.jsonl` (35 run records: n in {0, 1, 4}, L in {4k, 8k, 16k, 32k, 64k}, 3 reps for n = 1 and 4,
   1 rep for the n = 0 control). Each record carries per-interval server iteration timings (`c` = cached prefix, `dn` =
   tokens processed, `iter_ms`).
2. Re-ran the predeclared fit exactly as `pb_qcost_1.py` does: TRAIN lengths {4k, 16k, 64k}, HELD-OUT {8k, 32k}, per-n OLS
   `iter_ms = A + B*c`. Compared against `summary.json` (match to the printed precision).
3. Added LOLO cross-validation over all five lengths (fit on four, residuals on the fifth, pooled).
4. Replay: 80k neighbour prefill, linear 512-token budget versus a constant-ms budget whose target T is solved so the
   total prefill time equals the linear arm (iso neighbour TTFT). Cost model `t = a0 + b*q + d*q*c` with `d = B/q0` and
   `a0 = A - b*q0` from the per-n fit, and **b = 0.9865 ms/token ASSUMED from the 2026-10-20 offline fit** (the 2026-10-21
   run cannot identify it). The n = 3 row uses the original offline coefficients and reproduces the 2026-10-20 replay
   (206.4 s linear, max iteration 1808 ms).
5. Decode proxy ratio = ratio of mean iteration time (the 2026-10-20 proxy: decode work per iteration is constant, so
   decode-under-prefill throughput tracks 1 / mean iteration time). It cannot show per-token jitter.

## Numbers

Unit for every iteration quantity: ms per server iteration (consecutive log lines, q fixed near the gate `-b 512`).

| n generating (decode_rows) | q (tokens/iter) | intercept A at c = 0 (ms/iter) | slope B (ms per cached token) | train noise floor (rmse, ms/iter) | held-out P99 abs (ms/iter), split | LOLO pooled P99 abs / P95 abs / max abs (ms/iter) | request-level held-out MAPE frozen / refit | request-level LOLO MAPE |
|---|---|---|---|---|---|---|---|---|
| 1 (8) | 504 | 766.85 | 0.010794 | 20.26 (462 intervals) | 72.29 (n = 212) | 73.84 / 52.08 / 90.41 (n = 674) | 12.84 % / 2.40 % | 3.42 % |
| 3 (24), offline fit | 504 | 821.4 (= 324.2 + 0.9865 x 504) | 0.012137 (= 2.408e-5 x 504) | 40-65 (offline, different run) | n/a | n/a | n/a | n/a |
| 4 (32) | 480 | 871.40 | 0.013798 | 28.86 (486 intervals) | 210.69 (n = 228) | 122.40 / 63.82 / 281.96 (n = 714) | 26.32 % / 3.83 % | 5.59 % |

Per-n coefficient stability (all-data fit versus split fit): n = 1 A 767.15 vs 766.85, B 0.010786 vs 0.010794; n = 4
A 878.42 vs 871.40, B 0.013664 vs 0.013798. The n = 4 intercept moves by 7.0 ms/iter, 0.24 x its noise floor of 28.86.

Rep-to-rep TTFT spread (population CV across 3 reps): n = 1 0.3 to 2.8 %; n = 4 1.3 to 4.5 %. The spread falls with L.

n = 0 control (1 rep, idle prefill, graphs on) against the frozen model, ms/token: 4k 1.3543 vs 1.3167 (+2.9 %), 8k 1.3659 vs
1.3684 (-0.2 %), 16k 1.4514 vs 1.4718 (-1.4 %), 32k 1.6132 vs 1.6786 (-3.9 %), 64k 1.9459 vs 2.0922 (-7.0 %). The frozen
model agrees with the n = 0 control to within 7 %, so the failure is specific to decode rows present, not a general
mis-scale of prefill.

Conditional replay (80k neighbour, iso neighbour-prefill time; b = 0.9865 assumed):

| n | linear-512: total s / mean iter ms / max iter ms | fitted const-ms T (ms) | fitted: total s / mean / max (ms) | max-iteration cut | decode proxy ratio |
|---|---|---|---|---|---|
| 1 | 189.9 / 1194 / 1621 | 1195 | 190.1 / 1188 / 1195 | 26.3 % | 1.005 |
| 3 | 206.4 / 1315 / 1808 | 1315 | 206.7 / 1308 / 1315 | 27.2 % | 1.005 |
| 4 | 236.8 / 1418 / 1964 | 1419 | 236.7 / 1418 / 1419 | 27.8 % | 1.000 |

Margin for KVU-16g-2: with `target_ms = TPOT target - one-sided margin`, the held-out one-sided margins are the P99
under-prediction figures, **72.3 ms/iter at n = 1 and 210.7 ms/iter at n = 4** (the refit's under-prediction equals its
abs P99 in both cases). Use the n = 4 figure on the np4 :8083 shape when four slots can generate; the LOLO P99 for n = 4
is 122.4, so 210.7 is the conservative end.

## Predeclared criterion, applied mechanically

The criterion (operator-accepted 10 % held-out request-level MAPE, in `pb_qcost_1.py`): n = 1 frozen 12.84 % > 10 %, FAIL;
n = 4 frozen 26.32 % > 10 %, FAIL; overall FAIL. Refit MAPE 2.40 % and 3.83 %, both below 10 %. The confirm row's done
condition (refit held-out MAPE <= 10 % at n = 1 and n = 4 and coefficients within the noise floor of the 21:29Z refit)
needs a NEW uncontended run and is not testable from this data. This analysis did not alter the predeclared verdict.

## What the refit does not identify (caveat)

- `dn` is 504 (n = 1) and 480 (n = 4) in the median and the maximum; the only variation is short tail intervals (minimum 368
  and 288). The run swept c, not q. So the per-n fits give `A_n + B_n*c` at one q, and the offline q coefficient (0.9865
  ms/token) and the q*c cross term at other q are carried over, not re-validated. The budget that KVU-16g-2 enables varies q.
  The cheapest way to close it is a second q point per n (for example `-ub 256` or `-ub 1024` for one rep per L), which
  needs compute.
- Shape departure: `-np 5` rather than 4 (4 feeders plus the prefill slot).
- Contention: the run is graded INDICATIVE (it shared the host with the KVU-12 np8 CPU timing). The n = 0 control agreeing
  with the frozen model within 7 % argues the GPU prefill path itself was not strongly perturbed, but one rep cannot show
  that, and the n = 1 / 4 numbers were taken in the same contended window.
- The n = 4 interval-level residual has a heavy tail (P95 abs 63.8 versus max 282 ms/iter in LOLO). This is why the P99 is
  reported, not the rmse.

## Data provenance

All paths absolute; sha256 of inputs.

- `/mnt/raid0/llm/tmp/pb-qcost-1/runs/20261021T212922Z/pb_qcost_1.jsonl` a82cdf93dc8ca304703f057822586d61f746600bc8791036a3d7023e41c2699e
- `.../summary.json` c8b2de65bb3564d8da8685023cc198ccec31a880a7cd4159eadd200c943d6686; `.../summary.md` 4c1bd91e6439591dfa33dc28bd8423da66263955ed9ea66c0d21bf3184af398a; `.../run_meta.json` f3eddb50a98c62b6ab5067dd62f5480c0b8b5d61a14e55fae279248fc8939a2c
- `/mnt/raid0/llm/tmp/analytics-20261020/PB-QCOST-1/results.json` 8955180e6ea473bbab601cb5e1eb31cf86d8ead53ddd50266f4ea5ac1bff08e2 (offline coefficients)
- Server: `gpu-20261020-dd3d9721c` llama-server, Qwen3.8-27B-Q8_0 plus DFlash2 draft, `-np 5 -b 512 -ub 512 --kv-unified --cache-ram 65536`, graphs ON (log shows `graphs reused`).
- Analysis scripts (not committed, scratch): `/mnt/raid0/llm/tmp/f8-prodstack-20261023/{pbq.py,pbq_replay.py}` sha256 39fc00d3d9bfbac05bfc5e9d67cfa14f3d7bfc536bd5be7976e8cb9c732b4d6c and ec830f3cd305a58f9c39266c2a3261ce0c0a678609a26ce4a3acd42167c9a268; outputs `pbq.json` 97ace79c1f14e3a5efee022319eff37dc69fb9fbf0b755aea076645fc4e2bb4b, `pbq_replay.out`.

## Compute proposals (NOT armed)

1. **Confirm run (already filed as the PB-QCOST-1 confirm row).** Same harness `/mnt/raid0/llm/tmp/pb-qcost-1/pb_qcost_1.py`,
   same predeclared rule, MI210 plus threads 184-191 with the SMT siblings held idle by a region claim, about 30 min.
2. **Add a q axis to the confirm run (proposal, extends 1).** One extra block per n at `-ub 256` and `-ub 1024` (1 rep per L is enough for
   the q coefficient; 3 reps at L = 16k and 32k for noise), about 20 min more. It makes the refit identify
   `b` and the q*c term at n = 1 and 4 and removes the assumed b = 0.9865. Predeclare: the q coefficient at each n is
   within the 2026-10-20 value +/- its noise floor, else the budget's q-dependence is refit per n.
