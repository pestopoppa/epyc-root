# m4-srpf-pbhol (M4.2): pass/fail criteria (written 2026-10-23, BEFORE any run)

Item: M4 measurement half (`handoffs/active/gpu-serving-tie-in-program.md`, M4 / M4.2; trigger PB-HOL-1: B/A 22.05x budget off, 23.2x on).
Owner: workspace-f8. GPU class: mi210_0 + host threads 184-191. Nothing here has run when this file is written.

## What is tested
M4 (`experimental/m4-srpf-batch-fill-20261023` @ `c6ca031ac`, HIP build from `m4-srpf-gpu-build`, base `141e4bcf5`): `--prefill-order {slot,srpf}`
(default slot) visits slots with pending prompt tokens shortest-remaining first, and `--prefill-contend-cap N` (default 512, 0 = off) caps
prompt tokens per iteration while >= 2 splittable prompts are pending. The claim is that a short prompt in a HIGHER slot than an in-flight long
prefill no longer waits out the whole remaining prefill (PB-HOL-1 arm B).

## Harness
`pb_hol_1.py` in this directory is a COPY of `/mnt/raid0/llm/tmp/pb-hol-1/pb_hol_1.py` (original untouched). Same collision protocol as
PB-HOL-1: Qwen3.8-27B-Q8_0 + DFlash2 on the gate argv (`/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt`, np 3 here), ROCm0,
prompt set sha256 `dc37cdf1c407956d83d7b7354f4e48964306228793fc9095add945a17f2994de`; long = 64000 tokens (group 6 trunk), short = 128 tokens
(group 3 suffix 0); the short is sent when the long prefill reaches 50% (server-log progress); cache_prompt=false; slots erased between runs;
the long request is aborted once the short has answered. Arm A = short slot 0 / long slot 2. Arm B = short slot 2 / long slot 0.
Per phase the order is C, A,B,A,B,A,B, C (3 reps each; C = solo short on the idle server). One server load per phase.

| phase | binary | -b = -ub | server args beyond the gate argv |
|---|---|---|---|
| srpf512 | M4.1 build | 512 | `--prefill-order srpf` |
| srpf2048 | M4.1 build | 2048 | `--prefill-order srpf` (cap = default 512) |
| off512 | M4.1 build | 512 | none (the off-identity arm) |
| comp-champion | `gpu-20261023-141e4bcf5-lbh` | 512 | none |
| comp-m4off | M4.1 build | 512 | none |
| srpf2048cap0 | M4.1 build | 2048 | `--prefill-order srpf --prefill-contend-cap 0` (informational) |

Completion set (comp-*): 6 prompts from the same prompt set, fixed order `short128` (128 tok), `p512` (512), `p4000` (4000), `t8000` (8000),
`t16000` (16000), `pair4k` (two 4000-token prompts sent at once on slots 0 and 2); `n_predict` 96, temperature 0, seed 42, ignore_eos,
cache_prompt=false, slots erased before each; the token ids and the `/detokenize` text of every completion are retained. Each comp server
runs the whole set TWICE (pass 1, pass 2).

Per-server conditions (a phase whose server fails any of these is void and re-run on the next grant): `verify_ggml_linkage.sh` rc 0 with
`LD_LIBRARY_PATH=<bin>:/opt/rocm/lib...`; the LISTEN socket on the port belongs to our pid; **HIP graphs ON, read from `/proc/<pid>/environ`**
(no `GGML_CUDA_DISABLE_GRAPHS`; that is the production condition) and `HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0`; **residency by own-pid KFD VRAM**
>= 40 GiB (never log text); own-pid VRAM above **60 GiB aborts and kills that pid** (GPU-LEAK-1: graphs ON leaks ~0.29 GiB per request; one
server here sees <= 20 requests, ~51 GiB + ~6 GiB worst case). Host threads: `numactl --membind=3 -- taskset -c 184-191`.

## Conditions (mechanical: `verdict.py`, selftest proves each can FAIL; constants below are the ones in the file)
A collision run is VALID only if the short answered (HTTP 200, a first token), the long was not finished before the short was answered, and the
logged long progress at the time of sending was >= 0.40. EVERY run is counted: `verdict.json` lists attempted vs valid per phase and the
reason for each invalid run; a phase that was aborted and re-run keeps its earlier directory (`out/<phase>.attempt-*`), listed in
`ATTEMPTS.txt`, and the verdict reads the latest complete attempt only. A ratio needs >= 2 valid reps of both A and B.

- **C1 (the M4 effect).** median(B short TTFT) / median(A short TTFT) < 2.0 in phase **srpf512 AND** in phase **srpf2048**. FAIL if either ratio >= 2.0.
- **C2 (off-identity timing).** In phase off512 the same ratio is within PB-HOL-1's recorded **22.05x +-10%** (19.85 .. 24.26). Basis: PB-HOL-1
  off arms A 3193/3218/3220 ms, B 70809/70932/71033 ms (rep-to-rep ratio spread 21.99..22.25, +-0.6%); the +-10% allows for the different
  base image (dd3d9721c then, 141e4bcf5 now), the ~3% host drift seen over hours, and a 3-rep sample. Outside the band = FAIL (a ratio far
  below means the off path changed behaviour; far above means a regression).
- **C3 (off-identity bytes).** For each completion for which the CHAMPION's two passes are byte-identical (token-id sha256 and
  detokenized-text sha256), BOTH passes of comp-m4off must be byte-identical to the champion's. Any mismatch on such a prompt = FAIL.
  A completion on which the champion disagrees with itself is excluded and reported. If fewer than **4 of the 7 completions** (6 prompts; `pair4k` yields two) are champion-deterministic,
  C3 is INCONCLUSIVE (not PASS). A completion counts only with HTTP 200 and exactly 96 tokens.
- **Overall.** `PASS` iff C1 AND C2 AND C3 all PASS. Any FAIL = `FAIL`. Otherwise (a NOT_MEASURED or INCONCLUSIVE) = `INCOMPLETE`: no claim.
  This is the M4 measurement half only; the M4 done-condition's "no regression in the production gate" is a separate later step and this
  PASS does not discharge it.

## Reported, never gating
srpf2048cap0 (cap off): its B/A and per-arm medians; solo 64K prefill per phase vs PB-HOL-1's 119.9 s and C-solo medians vs 279.8 ms (a large
shift would be reported as a host or build effect, not used in the verdict); peak own-pid VRAM per server; the `iter_interval_s_per_512` and
the server log window of every collision run.

## Claim class
INDICATIVE on a shared host (gpu-quiet shared, q3 host threads claimed; the GPU belongs to this job for the window). Three reps per arm. The
srpf ratio is a same-day, same-server-shape A/B against the same binary's own arm A, so host drift cancels to first order; the C2 band absorbs the rest.

## Window
Planner estimate 70 min (conservative: long prefill modelled at 137 s vs 119.9 s measured); PB-HOL-1's recorded wall time (one off phase,
3 reps of A and B, 11.8 min) gives about 53 min for all six phases. Recommended grant >= 75 min; `--min-window` 30 min because the job is
resumable per phase (priority order: srpf512, srpf2048, off512, comp-champion, comp-m4off, srpf2048cap0; a cut phase is re-run whole).
