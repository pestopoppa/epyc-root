# OP-2 Canonical Bench Quiet-Window Package - 2026-07-18

> **2026-07-19 operator-confirmed execution gate:** OP-2 was **not reboot-gated**. Live host
> health is already bench-eligible (`numa_balancing=0`, CPU ~3.2 GHz / no severe throttle,
> 16-day uptime). The gate was a **quiet window** (pause the parallel agent's benching load)
> plus the throttle/affinity preflight. Reboot was not required.

**Status**: historical run package plus completed OP-2 provenance. This package did not amend
`/workspace/MEASUREMENT.md`, did not authorize production changes, did not authorize v6 rebuilds
or edits, and did not promote v7. The OP-2 execution completed on 2026-07-19; the live report is
`/mnt/raid0/llm/epyc-inference-research/docs/data/op2_canonical_bench_window_20260719_live5.md`.

**Scope**: prepared OP-2 evidence collection. The executed quiet-window payload was:

1. v6+iqk live throughput and garbage verification.
2. bench-clean canonical decode bench plus CPU-correctness gate.

B1 barrier-fusion `tg128` A/B and B4 DSA-D3 profile-first are retained as recorded OP-2 history,
not current window actions, unless their prerequisites change.

**2026-07-19 execution-status update:** OP-2 PASS. B1 and B4 should no longer consume quiet-window
decision time unless their prerequisites change. B1 has no current v7 fusion flag or immutable
binary pair, so record it as `skipped_not_staged` rather than run an invalid A/B. B4 already ran
the GLM-5.2 DSA-D3 profile-first gate and closed D3.1 as no-go for immediate Lightning Indexer
SIMD work (`ggml_compute_forward_lightning_indexer` was only `1.08%` of cycle samples). The
live v6+iqk role/garbage verification plus the clean canonical CPU decode bench completed in
`live5`: role smokes `6/6`, clean sentinel `status=ok`, process blockers `0`, and P-BENCH-1
frontdoor Q8 tg128 `avg_ts=12.442712` (`n=10`, `96` threads).

**2026-07-19 no-inference prep bundle:** inference-research has
`scripts/benchmark/op2_quiet_window_prep.py`, which creates the OP-2 run directory, records
host/repo/process state, stamps the narrowed stage plan, and writes
`operator_next_commands.sh` without starting inference or touching production v6. Current prep
artifact:
`/mnt/raid0/llm/epyc-inference-research/docs/data/op2_quiet_window_prep_20260719/`.
The generated operator script now includes concrete `OP2_READY` role-smoke `curl` commands for
`frontdoor`, `worker_general`, `architect_general`, `ingest_long_context`, `worker_vision`, and
`vision_escalation`, with per-role request/response/meta/check artifacts plus
`live-v6/role_smoke_aggregate.json`; it is no longer a prose-only smoke instruction. The tracked
prep directory is **not** the execution artifact root: unless the operator overrides
`OP2_RUN_ROOT`, the script creates a fresh timestamped run under
`/mnt/raid0/llm/epyc-inference-research/data/op2_canonical_bench_window/`.

Production kernel `/mnt/raid0/llm/llama.cpp` remains frozen. Experimental work, if any
arm requires it, stays in `/mnt/raid0/llm/llama.cpp-experimental` and is not deployed by
this package.

## Authority And Claim Rules

Decision-gating numbers must use the MEASUREMENT grammar:

`metric [protocol-id, n/reps, YYYY-MM-DD, attest <ref>]`

Every decision row must also state metric direction (`higher-better` or `lower-better`).
Numbers without this grammar are observations only. Live-stack garbage checks are
`P-SMOKE-1` unless a stronger protocol is explicitly cited. Canonical CPU decode rows use
`P-BENCH-1` only when produced through `bench_canonical.sh` / `canonical_recipe.py` with
the required host and binary attestations.

## Run Root

Use one run id and keep all artifacts under research data or `/mnt/raid0/llm/tmp`, not in
root handoff/progress files:

```bash
export OP2_RUN_ID="op2-canonical-bench-window-$(date -u +%Y%m%dT%H%M%SZ)"
export OP2_RUN_ROOT="/mnt/raid0/llm/epyc-inference-research/data/op2_canonical_bench_window/${OP2_RUN_ID}"
export OP2_TMP_ROOT="/mnt/raid0/llm/tmp/${OP2_RUN_ID}"
mkdir -p "$OP2_RUN_ROOT"/{approvals,preflight,attestations,live-v6,canonical-v6,b1-barrier-fusion,b4-dsa-d3,routing}
```

Required top-level artifact fields:

| Field | Required value |
|---|---|
| `run_id` | `$OP2_RUN_ID` |
| `operator_approval_ref` | approval message, ticket, or session ref for quiet window |
| `window_start_utc`, `window_end_utc` | exact UTC timestamps |
| `host_state` | uptime, kernel, CPU governor/EPP, THP enabled/defrag, `kernel.numa_balancing`, `perf_event_paranoid`, free memory, load |
| `process_state` | AutoPilot state, active `llama-server`/`llama-bench`/`llama-cli`/`perf` PIDs before and after |
| `repo_state` | branch, commit, dirty status for root, orchestrator, research, production llama.cpp, experimental llama.cpp |
| `binary_state` | path, mtime, sha256 if practical, `ldd`/mapped libraries, `llama-server --version` or `llama-bench` build fields |
| `model_state` | path, size, quant, registry role, sha256 or explicit `not_hashed` reason |
| `commands` | exact argv, cwd, env diff, stdout path, stderr path |
| `attestation_ref` | path plus sha256 for the relevant attestation JSON |
| `cleanup_proof` | post-run `pgrep`/`ps` proof and GPU/KFD proof if any HIP binary was used |

## Operator Approvals

Required before any execute step; retained here as historical gate criteria:

| Approval | Needed for | Notes |
|---|---|---|
| Quiet window | all inference/bench/profile stages | Required. Pause unrelated benching/inference load before the window. AutoPilot must not be restarted by this package; any operator-owned pause/resume happens outside the package and is recorded as process state. |
| Host reboot | only if preflight flags multi-day throttle or host-health failure | Not required for OP-2 on the 2026-07-19 operator-confirmed host state. If no reboot is approved and preflight is clean, `P-BENCH-1` remains available. |
| Stop/restart live stack | only if the operator explicitly chooses it outside this package | Full stack reload, production stack restart, and AutoPilot restart are not authorized by this document. If the quiet window cannot be obtained without those actions, abort and ask the operator. |
| `sudo` for host hygiene/perf | drop_caches, `perf`, sysctl fixes | Record every command and result. |
| B1 arm identity | barrier-fusion A/B | Must name exact flag or exact control/fusion binaries before the window. |
| B4 GLM/DSA profile | `perf record` around GLM-5.2 DSA | Must approve long CPU run and large `perf.data` artifact. |

Abort the whole package if quiet-window approval is missing, if production v6 edits/builds
are requested, if AutoPilot restart or full-stack reload is requested as part of this
package, or if another session needs the stack for production traffic.

## Preflight And Abort Gates

Run these before inference-bearing stages. The commands are part of the package; they are
not executed by this sidecar.

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python scripts/server/preflight_gate.py \
  --require-servers \
  --output-dir "$OP2_RUN_ROOT/attestations" \
  --json | tee "$OP2_RUN_ROOT/preflight/live_stack_preflight.json"

cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/perf_counter_preflight.py \
  --probe \
  --strict \
  --output-json "$OP2_RUN_ROOT/preflight/perf_counter_preflight.json" \
  --output-md "$OP2_RUN_ROOT/preflight/perf_counter_preflight.md"

python3 scripts/benchmark/cpu_bench_clean_preflight.py \
  --output-json "$OP2_RUN_ROOT/preflight/cpu_clean_record_only.json" \
  --strict
```

Abort conditions:

| Gate | Abort if |
|---|---|
| Process quiet | AutoPilot, unrelated `llama-server`, `llama-bench`, `llama-cli`, `rocprof`, or `perf` is active outside the approved plan. Do not stop/restart AutoPilot from this package; abort or wait for operator-owned quieting. |
| Host state | CPU governors/EPP, THP, `kernel.numa_balancing`, or `perf_event_paranoid` drift and operator does not approve a fix/rerun. |
| Binary identity | v6 live roles do not map `/mnt/raid0/llm/llama.cpp/build/bin` libraries or lack `GGML_IQK=1`. |
| Canonical recipe | `bench_canonical.sh --dry-run` fails, selects the wrong binary, or reports linkage drift. |
| B1 staging | no exact barrier-fusion flag, patch, binary pair, or commit pair is provided before the window. Skip B1 rather than discovering/building in-window. |
| B4 staging | GLM shards are incomplete, runner refuses production binary checks, perf events are unavailable, or `perf.data` cannot be written. |
| Correctness | any smoke output is malformed/garbled, any CPU correctness check fails, or post-run cleanup leaves stale benchmark/server PIDs. |

## Ordered Run Plan

### 1. Live v6+iqk Throughput And Garbage Verification

Purpose: verify the currently live production v6+iqk stack before reboot/bench isolation.
This is smoke/telemetry unless the runner stamps a stronger protocol.

Collect stack state:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
python scripts/server/orchestrator_stack.py status \
  | tee "$OP2_RUN_ROOT/live-v6/orchestrator_stack_status.txt"

ps -eo pid,lstart,comm,args \
  | rg 'llama-server|uvicorn|autopilot|perf|rocprof' \
  > "$OP2_RUN_ROOT/live-v6/process_snapshot.txt"

for pid in $(pgrep -f '/mnt/raid0/llm/llama.cpp/build/bin/llama-server' || true); do
  mkdir -p "$OP2_RUN_ROOT/live-v6/pid-${pid}"
  ps -p "$pid" -o pid,lstart,etime,comm,args > "$OP2_RUN_ROOT/live-v6/pid-${pid}/ps.txt"
  tr '\0' '\n' < "/proc/${pid}/environ" \
    | rg '^(GGML_IQK|LD_LIBRARY_PATH|OMP_|KMP_)=' \
    > "$OP2_RUN_ROOT/live-v6/pid-${pid}/environ.filtered.txt" || true
  rg -a 'llama.cpp/build|libllama|libggml' "/proc/${pid}/maps" \
    > "$OP2_RUN_ROOT/live-v6/pid-${pid}/maps.llama.txt" || true
done
```

For each hot role/port from stack status, issue one fixed prompt and record request,
response, timing, output hash, and pass/fail:

```bash
ROLE="<role>"
PORT="<port>"
curl -sS "http://127.0.0.1:${PORT}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"local","messages":[{"role":"user","content":"Return exactly: OP2_READY"}],"temperature":0,"seed":42,"max_tokens":32}' \
  > "$OP2_RUN_ROOT/live-v6/${ROLE}.op2_ready.response.json"
```

Evidence fields:

| Field | Capture |
|---|---|
| role/port/pid | role name, port, PID, process start time |
| v6 identity | binary path, mapped libs, `GGML_IQK=1`, branch/commit if available |
| request | endpoint, JSON body, prompt hash, seed/temp/max_tokens |
| output | response JSON, completion text, content sha256, exact `OP2_READY` pass/fail, garbage verdict |
| throughput telemetry | llama timings fields if present; otherwise wall latency and token counts |
| spec counters | draft generated/accepted counters for MTP/NEXTN roles if emitted |

Route results to `handoffs/active/v6-iqk-promotion.md` and the A2 row of
`handoffs/active/inference-acceleration-index.md`.

### 2. Bench-Clean Canonical Decode Bench / CPU-Correctness Gate

Purpose: collect the pending clean v6+iqk canonical decode evidence under `P-BENCH-1`.
Historical execution recipe: run during an operator-approved quiet window after the
throttle/affinity preflight passes.
Do not require a reboot unless the preflight flags multi-day throttle or another
host-health failure that the operator chooses to clear by reboot.

Bench-clean preflight:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/cpu_bench_clean_preflight.py \
  --run-sentinel \
  --output-json "$OP2_RUN_ROOT/canonical-v6/cpu_clean_sentinel.json" \
  --strict
```

Canonical command dry-run, then execute. The frontdoor Q8 row also serves as the B1
control baseline when B1 is staged.

```bash
FRONTDOOR_Q8="/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"

./scripts/benchmark/bench_canonical.sh \
  -m "$FRONTDOOR_Q8" \
  -p 0 \
  -n 128 \
  -r 10 \
  --dry-run \
  -- -o json \
  > "$OP2_RUN_ROOT/canonical-v6/frontdoor_q8_tg128.dryrun.txt" 2>&1

./scripts/benchmark/bench_canonical.sh \
  -m "$FRONTDOOR_Q8" \
  -p 0 \
  -n 128 \
  -r 10 \
  -- -o json \
  > "$OP2_RUN_ROOT/canonical-v6/frontdoor_q8_tg128.results.json" \
  2> "$OP2_RUN_ROOT/canonical-v6/frontdoor_q8_tg128.stderr.txt"
```

CPU-correctness gate:

| Check | Required evidence |
|---|---|
| canonical recipe | dry-run output shows taskset, NUMA interleave, `-t 96`, `-fa 1`, `-mmp 0`, `GGML_IQK=1`, LLVM-20 libomp, and v6 iqk binary |
| binary linkage | recipe/linkage validation passes and resolves to the v6 build libs |
| output validity | llama-bench JSON parse succeeds; no assert, NaN, malformed JSON, or stderr correctness warning |
| reps | `n=10` reps for `tg128`; median and MAD reported |
| host health | quiet-window approval plus bench-clean preflight/sentinel are attached as attestation refs |

Claim template:

`frontdoor_q8 decode tg128 median <value> t/s, higher-better [P-BENCH-1, n=10 reps, <YYYY-MM-DD>, attest <attestation-json-sha>]`

Route results to `handoffs/active/v6-iqk-promotion.md`. If this gate fails, do not use
later B1 numbers for a decision; route the failure to `cpu-shape-specialized-gemv-decode.md`
as host/source contamination risk.

### 3. B1 Barrier-Fusion `tg128` A/B

Purpose: test the sole live CPU decode lever: frontdoor Q8_0 operator/graph fusion to
reduce barrier count.

Pre-stage requirement: before the quiet window, the owner must provide one of:

- `B1_FUSION_ENV_FLAG=<name>` with accepted values `0` and `1` on one immutable binary.
- `B1_CONTROL_BINARY` and `B1_FUSION_BINARY`, with exact commits and `ldd` outputs.
- `B1_CONTROL_COMMIT` and `B1_FUSION_COMMIT`, with both binaries already built.

No such flag or patch was found during this package prep, and the 2026-07-18 staging audit
confirms the current v7 line has no valid B1 arm. If the fields above are still unknown at
window start, skip B1 and preserve the quiet window for stages 1 and 2. Do not report this
as a failed A/B; report it as `skipped_not_staged`.

Workload:

| Field | Value |
|---|---|
| model | `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf` |
| prompt/generation | `pp0/tg128` |
| reps | `10` |
| protocol | `P-BENCH-1` only if command shape is generated/validated by `canonical_recipe.py`; otherwise observation |
| arms | `control`, `fusion` |
| metric | decode `avg_ts`/tokens per second, median + MAD, higher-better |

Required per-arm fields:

| Field | Capture |
|---|---|
| arm identity | env flag or binary path, branch, commit, dirty status |
| command | exact argv and env, plus dry-run validation |
| host | same bench-clean attestation as stage 2 or a new attestation if state changed |
| result | raw JSON per rep, median, MAD, percent delta, stderr |
| correctness | JSON parse, no assert, no NaN, same model/quant, no output/runtime warning |

Decision template:

`B1 frontdoor_q8 barrier-fusion tg128 delta <pct>% median decode t/s, higher-better [P-BENCH-1, n=10 reps/arm, <YYYY-MM-DD>, attest <attestation-json-sha>]`

Route results to `handoffs/active/cpu-shape-specialized-gemv-decode.md` first, then the
B1 row in `handoffs/active/inference-acceleration-index.md`. If the profile notes expose
prefill-relevant compute-bound hot ops, also cross-link the observation to
`handoffs/active/cpu-prefill-compute-large-models.md`; do not close PC-0 from a decode-only
B1 run.

### 4. B4 DSA-D3 Profile-First `perf record`

Purpose: decide whether D3 AVX-512BW Lightning Indexer work is worth implementing on the
landed GLM-5.2 DSA path. This is profile-first; it does not authorize SIMD work.

2026-07-19 status: completed as a separate OP-2/B4 profile. Artifact:
`/mnt/raid0/llm/epyc-inference-research/data/op2_canonical_window/op2_b4_dsa_d3_profile_20260719T075142/b4-dsa-d3/`.
Verdict: D3.1 `CLOSED NO-GO`; Lightning Indexer share was too small for immediate SIMD work.
Only rerun B4 if a different GLM serving shape or D2 real-sparse attention changes the profile.

Dry-run the GLM runner first:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/glm52_dsa_probe_runner.py \
  --output "$OP2_RUN_ROOT/b4-dsa-d3/glm52_dsa_d3_profile_plan.json" \
  --binary /mnt/raid0/llm/llama.cpp-experimental/build-k24-cpu/bin/llama-server \
  --library-path /mnt/raid0/llm/llama.cpp-experimental/build-k24-cpu/bin \
  --only-stage kv_length_scaling \
  --kv-contexts 8192 \
  --indexer-top-k 2048 \
  --max-tokens 1 \
  --metrics \
  --trace-logs
```

Execute under `perf record` only after the dry-run says execution is allowed:

```bash
perf record \
  -F 99 \
  --call-graph dwarf \
  -o "$OP2_RUN_ROOT/b4-dsa-d3/perf.data" \
  -- \
  python3 scripts/benchmark/glm52_dsa_probe_runner.py \
    --execute \
    --output "$OP2_RUN_ROOT/b4-dsa-d3/glm52_dsa_d3_profile_plan.json" \
    --binary /mnt/raid0/llm/llama.cpp-experimental/build-k24-cpu/bin/llama-server \
    --library-path /mnt/raid0/llm/llama.cpp-experimental/build-k24-cpu/bin \
    --only-stage kv_length_scaling \
    --kv-contexts 8192 \
    --indexer-top-k 2048 \
    --max-tokens 1 \
    --metrics \
    --trace-logs

perf report --stdio \
  -i "$OP2_RUN_ROOT/b4-dsa-d3/perf.data" \
  > "$OP2_RUN_ROOT/b4-dsa-d3/perf_report.txt"
```

If `perf record` around the wrapper does not show `GGML_OP_LIGHTNING_INDEXER` or related
indexer symbols, rerun by attaching to the server PID during the request and record that the
wrapper-level profile was inconclusive.

Evidence fields:

| Field | Capture |
|---|---|
| GLM inventory | shard count, manifest status, model dir, blocker files |
| binary | experimental CPU binary path, commit, dirty status, library path; production-root refusal must remain active |
| DSA config | `glm-dsa.attention.indexer.top_k=2048`, context length, prompt tokens, `max_tokens=1` |
| perf config | `perf` binary, events available, frequency, call graph mode, `perf.data` path, `perf report` path |
| runtime | server argv, PID, logs, `/metrics` summary, request/response JSON, cleanup proof |
| profile verdict | indexer cycle share, top symbols, IPC/cycles/instructions if available, compute-bound vs BW-bound classification |

D3 decision rule:

- If the Lightning Indexer path is material and compute-bound, route as `D3.1 profile passed`
  and request a separate implementation plan.
- If it is BW-bound, negligible, missing from the profile, or confounded by host state, do not
  implement D3. Route as `D3.1 no-go` or `D3.1 inconclusive` with the exact reason.

Route results to `handoffs/active/llama-cpp-dsa-contribution.md` D3.1 first and
`handoffs/active/cpu-shape-specialized-gemv-decode.md` CPU26 second. If the same profile is
used as evidence for prefill compute-bound behavior, route only a scoped observation to
`handoffs/active/cpu-prefill-compute-large-models.md`; PC-0 still needs its own explicit
long-context large-model prefill premise check before closure.

## Output Routing Summary

| Stage | Primary handoff | Secondary routing | Completion record |
|---|---|---|---|
| v6 live verify | `handoffs/active/v6-iqk-promotion.md` | `handoffs/active/inference-acceleration-index.md` A2 | live role table, smoke verdicts, attestation refs |
| clean canonical bench | `handoffs/active/v6-iqk-promotion.md` | master OP-2 via main agent | P-BENCH-1 claim row or failure reason |
| B1 barrier fusion | `handoffs/active/cpu-shape-specialized-gemv-decode.md` | `inference-acceleration-index.md` B1; maybe CPU prefill as observation | arm table, median/MAD, delta, correctness |
| B4 DSA-D3 profile | `handoffs/active/llama-cpp-dsa-contribution.md` | `cpu-shape-specialized-gemv-decode.md` CPU26; maybe CPU prefill as observation | profile verdict: compute-bound, BW-bound, or inconclusive |

The main agent, not this sidecar, owns handoff checkbox/progress updates. Do not edit
handoffs, progress logs, MEASUREMENT, or code while preparing this package.

## Final Bundle Checklist

- [ ] Operator approval refs captured.
- [ ] Preflight artifacts captured and attached.
- [ ] Live v6+iqk role table complete.
- [ ] Bench-clean `P-BENCH-1` row produced or explicit abort reason recorded.
- [x] B1 arm identity supplied before execution, or B1 skipped with staging blocker. ✅ 2026-07-19 (`skipped_not_staged`)
- [x] B4 `perf.data` and `perf_report.txt` captured, or profile abort reason recorded. ✅ 2026-07-19 (`D3.1 CLOSED NO-GO`)
- [ ] Every decision-gating number uses `(metric, protocol-id, n/reps, date, attestation ref)`.
- [ ] No MEASUREMENT amendment made.
- [ ] No production kernel change made.
- [ ] No production promotion or config flip made.
