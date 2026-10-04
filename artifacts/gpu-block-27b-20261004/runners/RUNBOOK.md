# 27B GPU window — 2026-10-03 — RUNBOOK

Prepared by a subagent for **workspace-ec** (the session that owns :8083 inference and its reloads).
Nothing here has been run against :8083 or the GPU: every script was dry-run only, and the RUN
paths were checked against an in-process mock (`selftest_mock.py`, see the end of this file).

Directory: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/`. All scripts use only the Python stdlib
(`/usr/bin/python3`). Every runner refuses to send traffic without `--i-own-the-window`, and
each one prints its full plan with `--dry-run`.

| Script | Task | Talks to | :8083 state |
|---|---|---|---|
| `deploy_ec2_lease.py` | UFH14-DEPLOY-EC-2: KVU-15a lease + KVU-15c credit | :8000 → :8083 | serving, **not parked**, production flags |
| `q38_t7.py` | Q38-T7 DFlash2 speed + correctness + coherence | :8083 direct | serving, **parked** |
| `kvu16b_residency.py` | KVU-16b concurrent residency ≥ 300k | :8083 direct | serving, **parked** |
| `b4g_entry_cost.py` | UFH14-B4g prompt-cache entry cost | log (+ :8083 if a trigger is needed) | serving, **parked** |
| `b4i_idle_slots_ab.py` | UFH14-B4i `--no-cache-idle-slots` A/B | scratch :18083 | **stopped** (VRAM) |

`lib_gpublock.py` holds the shared helpers: SSE client, /slots and KFD samplers, log windows,
the INF-70 coherence classifier, and the prompt builders.

## 0. Before the window (main, ~3 min)

```bash
cd /mnt/raid0/llm/epyc-orchestrator
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
G=/mnt/raid0/llm/tmp/gpu-block-27b-20261003
# (a) The GPU must be ours. At prep time KFD also listed PID 722898
#     "./build-hip/bin/test-backend-ops test -o FLASH_ATTN_EXT -b ROCm0" (0.54 GiB, another session).
#     Confirm with its owner that it has finished. It is not ours to kill.
ls /sys/class/kfd/kfd/proc/
# (b) End the SLOTS_DEBUG window (UFH14-DIAG-EC-a). A plain reload restores the declared env.
$PY scripts/server/orchestrator_stack.py reload architect_critic
$PY -m scripts.server.env_override readback --port 8083 --expect-declared
P=$(ss -ltnp 'sport = :8083' | grep -o 'pid=[0-9]*' | cut -d= -f2); echo $P
tr '\0' '\n' < /proc/$P/environ | grep SLOTS_DEBUG || echo "SLOTS_DEBUG unset (required)"
$PY -c "import json;d=json.load(open('logs/server_launches/8083.json'));print(d['argv_sha256'][:8],d['pid'])"   # expect b865820d
curl -s localhost:8083/health
# (c) Regenerate the B4i launch scripts from the now-clean live environ (they filter SLOTS_DEBUG anyway).
/usr/bin/python3 $G/b4i_idle_slots_ab.py --print-launch
```

## 1. DEPLOY-EC-2 proofs (KVU-15a + KVU-15c): :8083 SERVING, NOT parked (~4 min)

```bash
$PY -m src.runtime.gpu_window status          # must not show 8083 / architect roles parked
/usr/bin/python3 $G/deploy_ec2_lease.py --i-own-the-window          # phases lease,credit
```

The run must follow step 0's reload directly, with no :8083 relaunch between the two credit
calls, because history entries are per launch. The credit phase refuses while
`LLAMA_SERVER_SLOTS_DEBUG` is set.

- **PASS (lease).** Both calls return 200. The lease is seen held in at least one sample and never
  by more than one holder (`/proc/locks`, passive). :8083 never prefills two slots at once. The
  records show `passthrough.long_prefill: true`, or the later call's wait is at least half the
  earlier call's prefill time.
- **PASS (credit).** Call 2's record has `kv_admission.cache_credit_source == "fp_history"` and
  `cache_credited_tokens > 0`, and credited / `timings.cache_n` is between 0.5 and 1.5.
- Also reported: whether the primitives-lane record carries `request.prefix_fp` (the open B4
  half), and a known gap: primitives records have no `long_prefill` field, only
  `queue.pre_dispatch_wait_ms`.

## 2. Park :8083's roles (server stays up) (~10 s)

```bash
$PY -m src.runtime.gpu_window park --roles architect_critic,coder_escalation,ingest_long_context \
    --ports 8083 --holder autokernel --expected-end +100m
$PY -m src.runtime.gpu_window status
```

`autokernel` is the only `park` holder value the CLI accepts; here it just means "lent out". A
real request to a parked role gets 503 `role_parked` and writes `preempt_requested_at`. Every
runner records `window_at_end`, so check that field and decide whether to yield.

## 3. Q38-T7: :8083 PARKED (~23 min)

```bash
/usr/bin/python3 $G/q38_t7.py --i-own-the-window            # phases A,B,C
```

- **Phase A.** The codified 24-prompt production mix (`inf70/agents/e3-alpha/prompts.json`) with
  the recipe WORKLOAD settings (greedy, max_tokens 200, thinking off, cache_prompt false). It runs
  the DFlash2 arm and a `speculative.n_max: 0` arm. Outputs are classified with the INF-70
  classifier. Greedy identity between the two arms is informational only.
- **Phase B.** The `probe_decode.py` method at ~2k/16k/50k/80k on C2+C4: 2 drafted reps of 1500
  tokens with thinking on, one no-draft row on the cached prompt, and one greedy needle question
  per length. The needle is the paired correctness check. Rows compare 1:1 with the 2026-10-01
  MTP table. That table was taken on the pre-KVU-16 196608 pool, so the comparison crosses server
  shapes.
- **Phase C.** 4 concurrent ~16k streams.
- **Draft acceptance** is recorded for every call.
- **PASS** (exit 0) requires:
  - every needle answer contains both facts;
  - phase A's DFlash2 arm has no SALAD, EARLY-EOS, EMPTY or HTTP-ERROR;
  - every phase B and C drafted output is COHERENT or SHORT.

  If correctness fails, the speed numbers are marked INVALID. A SALAD whose only trigger is the
  ascii-share rule (code-heavy text) goes to `eyeball_required` and does not fail the gate on its
  own. Eyeball those, and eyeball the `text_head` / `content_head` samples anyway.
- No MTP arm and no n-max 8 arm: the operator ruled 27B always runs DFlash2, and the kernel clamps
  n-max to 7.

## 4. KVU-16b: :8083 PARKED (~36 min, cap 70 min)

```bash
/usr/bin/python3 $G/kvu16b_residency.py --i-own-the-window
# if it aborts with "budget < min" because idle slots still hold cells and the purge did not clear them:
/usr/bin/python3 $G/kvu16b_residency.py --i-own-the-window --erase-idle-slots
```

- **Prompts.** 4 distinct × **80k** tokens, not 90k. 4 × 90k = 360k leaves only ~25k decode
  headroom in 393216 cells. 4 × 80k = 320k already clears 300k and leaves ~65k for the
  no-overflow `n_predict` budgets [27310, 19507, 12354, 5852].
- **Sending.** Streamed `/completion` with `ignore_eos`. Each request is sent when the previous
  one streams its first token. The streams are closed 90 s after the PASS sample.
- **Purge evidence.** If idle slots hold cells from T7, a 1-token probe runs first. Its
  before/after `/slots` and the `clearing prompt with N tokens` lines are recorded as live
  idle-purge evidence at production flags (`idle_purge_evidence`), which also feeds B4i.
- **PASS** (exit 0) requires all of:
  - one `/slots` sample with 4 slots decoding and resident ≥ 300,000 (Σ `n_prompt_tokens`, which
    includes generated tokens);
  - 0 lines matching "failed to find a memory slot" or "Context size has been exceeded" after the
    start offset;
  - KFD peak ≤ 62 GiB;
  - no failed request.
- **Also reported.** Per-slot decode tok/s while all 4 decode at ~320k fill: the neighbour decode
  tax, data for KVU-17/19.

## 5. B4g: :8083 PARKED (~1 min parse, ~7 min if it must trigger)

```bash
/usr/bin/python3 $G/b4g_entry_cost.py --i-own-the-window          # --trigger auto
```

- **Window.** The log is parsed from the start of the current launch, so the saves from T7 and
  KVU-16b count.
- **Trigger.** Only if fewer than 3 distinct save lengths ≥ 4k exist. It sends 8k/24k/48k/72k
  prompts, each followed by idle time and then a new task.
- **Fits.** `prompt_save` total, target-only and draft parts, plus entry-with-checkpoints and
  checkpoint size. The result is MiB per 1k tokens, fixed MiB and R².
- **Prior and parser check.** On the prior shape (np4/196608, n_max 4) the parser reproduces
  37.155 MiB/1k + 149.6 MiB fixed (R² 1.0) and draft 3.93 MiB/1k. That is the handoff's
  "≈ 40-42 KiB/token" (38.05 KiB/token).
- `--parse-only` sends nothing and can be re-run any time.

## 6. B4i: :8083 STOPPED, scratch :18083 (~16 min ON/OFF; ~25 min ON/OFF/ON)

```bash
$PY scripts/server/orchestrator_stack.py stop architect_critic
ps -p $P || echo "8083 PID $P dead"; ls /sys/class/kfd/kfd/proc/; cat /sys/class/drm/card2/device/mem_info_vram_used
# arm ON (v10 default cache_idle_slots)
bash $G/results/b4i/launch_ON.sh          # PID -> results/b4i/scratch-ON.pid; prints KFD + linkage proof
/usr/bin/python3 $G/b4i_idle_slots_ab.py --i-own-the-window --arm ON --rep r1
bash $G/results/b4i/kill_ON.sh            # kills ONLY the captured PID; TERM -> KILL; verifies dead
# arm OFF (--no-cache-idle-slots)
bash $G/results/b4i/launch_OFF.sh
/usr/bin/python3 $G/b4i_idle_slots_ab.py --i-own-the-window --arm OFF --rep r1
bash $G/results/b4i/kill_OFF.sh
# optional ABA (host drift): ON again as r2
bash $G/results/b4i/launch_ON.sh && /usr/bin/python3 $G/b4i_idle_slots_ab.py --i-own-the-window --arm ON --rep r2 && bash $G/results/b4i/kill_ON.sh
/usr/bin/python3 $G/b4i_idle_slots_ab.py --compare $G/results/b4i/ON-r1-*/report.json $G/results/b4i/OFF-r1-*/report.json
```

- **Launch scripts.**
  - Argv is the production argv from `logs/server_launches/8083.json` with three changes:
    `--port 18083`, a scratch `--slot-save-path`, and `--no-cache-idle-slots` on arm OFF.
  - The binary is the kernel-store `kernels/production/gpu` binary
    (`builds/gpu-20260921-ffc1bac82`).
  - `LD_LIBRARY_PATH` and env come from the live :8083 environ, minus SLOTS_DEBUG, with the same
    `numactl --membind=3 -- taskset -c 184-191` placement.
  - They refuse if :8083 is still listening.
- **Traffic per arm.** 3 conversations × 6 turns on distinct ~20k contexts, with ~1.5k new
  tokens per turn, 200 tokens generated, and staggered 30–36 s pauses.
- **Measured per turn.** TTFT, prompt_n, cache_n and prompt_ms against the exact shared prefix.
  Per arm: hit_tok, missed_prefill_share, restores, restore failures, evictions and KFD VRAM.
- **Arm ON must SHOW the purge** (non-zero `clearing prompt` lines or `/slots` idle drops), or the
  report says the A/B has nothing to compare.
- **Decision rule** (handoff): the winner becomes a PFX-SEL-1 field. Lower turn≥2 TTFT and
  missed_prefill_share win, provided OFF's VRAM headroom stays acceptable.

## 7. Restore production (~3 min)

```bash
$PY scripts/server/orchestrator_stack.py reload architect_critic
P=$(ss -ltnp 'sport = :8083' | grep -o 'pid=[0-9]*' | cut -d= -f2)
$PY -c "import json;d=json.load(open('logs/server_launches/8083.json'));print(d['argv_sha256'][:8],d['pid'])"   # b865820d, == $P
tr '\0' '\n' < /proc/$P/environ | grep SLOTS_DEBUG || echo clean
$PY -m src.runtime.gpu_window restore && $PY -m src.runtime.gpu_window status
curl -s localhost:8000/v1/passthrough/architect_critic/chat/completions -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"What is 7*8? Answer with the number."}],"max_tokens":32,"chat_template_kwargs":{"enable_thinking":false}}'
```

## Timeline (estimates)

| # | Step | :8083 | Est. |
|---|---|---|---|
| 0 | preconditions + plain reload | reload | 3 min |
| 1 | DEPLOY-EC-2 (lease + KVU-15c credit) | serving, not parked | 4 min |
| 2 | park | parked | <1 min |
| 3 | Q38-T7 | parked | 23 min |
| 4 | KVU-16b | parked | 36 min (cap 70) |
| 5 | B4g | parked | 1–7 min |
| 6 | B4i ON/OFF (+ON) | **stopped** | 16 (25) min |
| 7 | restore + verify | reload | 3 min |
| | **total** | | **~1 h 30 min – 1 h 55 min** |

The production :8083 roles are unavailable from step 2 to step 7 (~1 h 25 min – 1 h 50 min).
The server itself is down only during step 6.

## Where results go

`results/<script>/<ts>/`, as follows:

| Script | Files |
|---|---|
| `q38_t7` | `calls.jsonl` (written per call), `report.json`, `report.md` |
| `kvu16b` | `slots.jsonl`, `requests.jsonl`, `report.json`, `report.md` |
| `b4g` | `report.json`, `report.md` |
| `ec2_lease` | `lease_samples.jsonl`, `report.json`, `report.md` |
| `b4i/<ARM>-<rep>-<ts>` | `turns.jsonl`, `slots.jsonl`, `report.json`, plus scratch logs `results/b4i/scratch-<ARM>.log` |

Each report records the server log byte window, so a reader can re-derive any figure. Exit codes
are 0 for PASS, 1 for FAIL, 2 for refused/aborted and 3 for a dry-run input problem.

**Belief-kernel write side, to wire.** The report schemas are `epyc.gpublock.*.v1/v2`. Q38-T7
asks for VB-SERVING-DF2, which needs a row in `scripts/vidya/adapters/README.md` plus a task in
`vidya-belief-substrate-program.md`. The owning session applies index or adapter rows.

## Finding made while preparing (no inference): the idle-slot purge DID happen in production

`logs/llama-server-8083.log` already holds **211 idle-slot purges of non-empty slots**: each is
a `saving idle slot to prompt cache` line followed by `clearing prompt with N tokens` with N > 0,
11.5 M tokens in all, between log lines 35430 and 130878. The latest example is line 130621:
`id 2 | clearing prompt with 84951 tokens`. All of them are at the previous kv-unified shape
(np4, n_ctx_slot 196608), on organic traffic. So the "code read only, not reproduced" status in
UFH14-B4i and KVU-16b understates the evidence. The purge was real in production before the
393216 relaunch. B4i arm ON still has to show it at the current shape, and KVU-16b's purge probe
records it too.

## Self-test (no server, no GPU)

`selftest_mock.py` runs all five runners' RUN paths against an in-process mock HTTP server and
writes only to `./_selftest` (deleted after the run). Last result: `SELFTEST OK`.

| Runner | Result |
|---|---|
| T7 | PASS |
| KVU-16b | PASS |
| B4g | fit 37.153 MiB/1k |
| EC-2 | lease FAIL by design (no real flock); credit PASS on mock records |
| B4i | report written |

## Dry-run outputs

### `deploy_ec2_lease.py --dry-run` (exit 0)

```text
=== DRY RUN: deploy_ec2_lease.py (UFH14-DEPLOY-EC-2: KVU-15a lease + KVU-15c credit) (no requests sent) ===

[target]
  orchestrator http://127.0.0.1:8000 -> :8083; :8083 must be SERVING and NOT parked (window now: {"file": "/mnt/raid0/llm/tmp/gpu-window/mi210.json", "exists": false, "parked_8083": false})
  live :8083 PID 1083497, LLAMA_SERVER_SLOTS_DEBUG='1' now (credit phase refuses while set; the main session's plain reload clears it)

[inputs]
  ok /mnt/raid0/llm/epyc-orchestrator/logs/serving_calls/serving_calls.jsonl (20827 bytes)
  ok /proc/locks (0 bytes)
  lease file /mnt/raid0/llm/tmp/kv_prefill_lease.local_8083.lock: absent (created by the first long prefill; fine); holders now []
  prefix history /mnt/raid0/llm/tmp/kv_prefix_history.local_8083.json: absent (created by the first ok record after KVU-15c deploy; fine)
  lane passthrough:architect_critic: POST http://127.0.0.1:8000/v1/passthrough/architect_critic/chat/completions keys ['chat_template_kwargs', 'max_tokens', 'messages']
  lane v1client:coder_escalation: POST http://127.0.0.1:8000/v1/chat/completions keys ['max_tokens', 'messages', 'model', 'x_tool_mode']

[phase lease]
  2 distinct ~24000 real tokens; chars [76899, 76899]; gate estimate (chars/3) [25633, 25633] vs threshold 16384
  lane A first, lane B +2.0 s; streamed; max_tokens 64
  samples /proc/locks 0.1 s (passive), :8083 /slots 1 s, serving records in the window
  PASS: both 200; lease held >= 1 sample, never > 1 holder; never 2 slots prefilling; long_prefill=true or later wait >= half the earlier prefill

[phase credit (KVU-15c)]
  call 1: ~24000 tok via passthrough:architect_critic; wait for its ok record
  call 2: call 1's prompt + ~3000 tok + new task, same lane
  PASS: call 2 kv_admission.cache_credit_source == fp_history, cache_credited_tokens > 0, credited / timings.cache_n in [0.5, 1.5]

[phases selected]
  credit, lease

[estimate]
  lease ~2 min; credit ~1 min

[outputs]
  /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/ec2_lease/<ts>/lease_samples.jsonl, report.json, report.md

[input validation] OK
```

### `q38_t7.py --dry-run` (exit 0)

```text
=== DRY RUN: q38_t7.py (Q38-T7) (no requests sent) ===

[target]
  http://127.0.0.1:8083 directly; orchestrator roles PARKED (window file /mnt/raid0/llm/tmp/gpu-window/mi210.json)
  preflight (run mode): /props, /slots spec types (expect draft-dflash), slot n_ctx 262144, live argv -c 393216 / n-max 7, SLOTS_DEBUG env unset, KFD process list, busy slots

[inputs]
  ok /mnt/raid0/llm/tmp/inf70/agents/e3-alpha/prompts.json (18278 bytes)
  ok /mnt/raid0/llm/tmp/ds41-c95/contexts/C2/prompt.inline.txt (143510 bytes)
  ok /mnt/raid0/llm/tmp/ds41-c95/contexts/C4/prompt.inline.txt (119288 bytes)
  ok /mnt/raid0/llm/tmp/ds41-c95/probe-decode-vs-context.mtp.json (22369 bytes)
  ok /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log (27109033 bytes)

[phase A — coherence/correctness mix]
  24 prompts, 233-2303 chars (~72-719 tokens est.), suites ['bigcodebench', 'coder', 'debugbench', 'gpqa_diamond_cot', 'instruction_precision', 'livecodebench', 'math', 'mmlu_pro', 'mode_advantage', 'physics', 'real_suite_v1', 'simpleqa', 'thinking']
  arms: dflash2 (server default) | nodraft (speculative.n_max 0); greedy, max_tokens 200, cache_prompt false, enable_thinking false = recipe WORKLOAD
  48 calls; classifier = INF-70 gdn-rowexact/classify.py

[phase B — decode vs context + needle]
  targets [2000, 16000, 50000, 80000] tokens of C2+C4 (261788 chars); reps 2 drafted (gen 1500, thinking on) + 1 no-draft on cached prompt (gen 500) + 1 greedy needle question per target
  needles at 1/3, 2/3 depth, e.g. expected ['80-4-1-9-ORCHID', 'Mbeki Larsen']
  calls: 16

[phase C — 4 concurrent]
  4 x ~16000 tok distinct prompts (rotated C1..C7 + TASK), gen 1000

[phases selected]
  A, B, C

[estimate]
  ~23 min (A ~4 min, B ~16 min, C ~3 min)

[outputs]
  /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/q38_t7/<ts>/calls.jsonl (per call, flushed), report.json, report.md
  verdict: correctness PASS/FAIL + speed VALID/INVALID; exit 0 PASS, 1 FAIL

[input validation] OK
```

### `kvu16b_residency.py --dry-run` (exit 0)

```text
=== DRY RUN: kvu16b_residency.py (KVU-16b) (no requests sent) ===

[target]
  http://127.0.0.1:8083 directly (bypasses the one-long-prefill gate on purpose: the pool is under test); :8083 roles PARKED
  preflight (run): live pid/argv, window parked, all slots idle (waits <= 10 min)

[inputs]
  ok /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log (27109145 bytes)
  ok /sys/class/drm/card2/device/mem_info_vram_used (4096 bytes)
  ok /sys/class/kfd/kfd/proc (0 bytes)
  7 contexts, 928820 chars (~290256 tok est.)

[prompts]
  4 x 80000 tokens (est. offline [80045, 80045, 80045, 80045]; RUN mode trims to +-1% via /tokenize)
  sum 320000 vs threshold 300000

[budgets (no-overflow guarantee)]
  pool 393216 - prompts 320000 - margin 8192 - residual (measured) = headroom 65024
  n_predict budgets by weight [0.42, 0.3, 0.19, 0.09]: [27310, 19507, 12354, 5852]
  for reference, 4 x 90000 would leave headroom 25024 -> budgets [10510, 7507, 4754, 2252]

[send pattern]
  optional 1-token purge probe if idle slots hold tokens (records idle-purge evidence)
  streamed /completion, ignore_eos, staggered on first token; hold 90 s after the PASS sample, then close streams
  max wall 4200 s

[sampling]
  /slots every 2.0 s; KFD VRAM every 0.5 s; server log offset scan

[PASS]
  4 slots decoding in one sample with resident >= 300000; 0 bad lines; KFD peak <= 62.0 GiB; no request failed

[estimate]
  prefills ~32 min (scaled from the 13:51Z probe) + hold 1.5 min + setup ~2 min = ~36 min

[outputs]
  /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/kvu16b/<ts>/slots.jsonl, requests.jsonl, report.json, report.md; exit 0 PASS, 1 FAIL

[input validation] OK
```

### `b4g_entry_cost.py --dry-run` (exit 0)

```text
=== DRY RUN: b4g_entry_cost.py (UFH14-B4g) (no requests sent) ===

[inputs]
  ok /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log (27109481 bytes)

[current log window (read-only parse, done now)]
  window from byte 26889964 (current launch: 0.51.728.286 I srv    load_model: initializing, n_slots = 4, n_ctx_slot = 262144, kv_unified = 'true') to 27109481
  prompt_save lines 0 (lengths >= 4k: []); entry lines 0; checkpoint lines 0; events {'idle_saves': 0, 'clear_nonzero': 0, 'clear_nonzero_tokens': 0, 'restores_better': 0, 'restore_failures': 0, 'evictions': 0, 'evicted_mib': 0.0, 'prompt_saves': 0, 'last_cache_state': None}
  fit now: total {'n': 0, 'points': [], 'fit': None}
  prior (np4/196608, n_max 4): {'n': 2, 'mib_per_1k_tokens': 37.155, 'kib_per_token': 38.05, 'fixed_mib': 149.6, 'r2': 1.0, 'points': [(39875, 1631.2), (84951, 3306.0)]}

[trigger]
  trigger mode auto: WOULD TRIGGER (today's window; re-evaluated after T7/KVU-16b have run)
  sizes [8000, 24000, 48000, 72000]: per size 1 x /completion (n_predict 8, distinct nonce) + 5 s idle + 1 x 1-token task
  prefill ~5.6 min at ~450 tok/s

[estimate]
  parse < 1 min; trigger (if needed) ~6.8 min

[outputs]
  /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4g/<ts>/report.json, report.md (MiB per 1k tokens, fixed MiB, R^2)

[input validation] OK
```

### `b4i_idle_slots_ab.py --dry-run` (exit 0)

```text
=== DRY RUN: b4i_idle_slots_ab.py (UFH14-B4i) (no requests sent) ===

[inputs]
  ok /mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json (1730 bytes)
  ok /mnt/raid0/llm/kernels/production/gpu/llama-server (17984 bytes)
  ok /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh (8875 bytes)
  argv from /mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json (launched_at 2026-10-03T15:43:08.178Z); env from live :8083 PID 1083497 environ

[arm ON (main session runs these)]
  bash /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/launch_ON.sh
  bash /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/kill_ON.sh
  command: env -u LLAMA_SERVER_SLOTS_DEBUG LD_LIBRARY_PATH=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib HIP_PATH=/opt/rocm ROCM_PATH=/opt/rocm OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false GGML_IQK=1 numactl --membind=3 -- taskset -c 184-191 /mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 18083 -np 4 -c 393216 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified --no-mmap -ngl all --cache-ram 65536 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja -md /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 7 --device ROCm0 --slot-save-path /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/kv_slots_scratch --device-draft ROCm0

[arm OFF (main session runs these)]
  bash /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/launch_OFF.sh
  bash /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/kill_OFF.sh
  command: env -u LLAMA_SERVER_SLOTS_DEBUG LD_LIBRARY_PATH=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib HIP_PATH=/opt/rocm ROCM_PATH=/opt/rocm OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false GGML_IQK=1 numactl --membind=3 -- taskset -c 184-191 /mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 18083 -np 4 -c 393216 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified --no-mmap -ngl all --cache-ram 65536 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja -md /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 7 --device ROCm0 --slot-save-path /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/kv_slots_scratch --device-draft ROCm0 --no-cache-idle-slots

[traffic per arm]
  3 conversations x 6 turns; base ~20000 tok distinct; +~1500 tok per turn; gen 200; pauses 30+3c s; conv starts staggered 12 s; greedy, thinking off
  samples /slots 2 s, KFD VRAM 1 s; scratch log scanned for idle saves / clears / restores / evictions

[run]
  b4i_idle_slots_ab.py --i-own-the-window --arm ON --rep r1   (after launch_ON.sh is healthy)
  b4i_idle_slots_ab.py --compare results/b4i/ON-r1-*/report.json results/b4i/OFF-r1-*/report.json

[estimate]
  traffic ~5.7 min per arm + load ~2 min + kill ~0.5 min; ON/OFF ~16 min; ABA (ON/OFF/ON) ~25 min

[outputs]
  /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/<ARM>-<rep>-<ts>/turns.jsonl, slots.jsonl, report.json; scratch logs /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/b4i/scratch-<ARM>.log

[input validation] OK
```
