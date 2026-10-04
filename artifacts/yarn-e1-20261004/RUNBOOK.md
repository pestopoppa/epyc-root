# INF-59 E1 runbook: YaRN f2 (524,288) on Qwen3.8-27B, dedicated single-slot MI210 instance

Prepared 2026-10-04 by a subagent for **workspace-ec** (owner of :8083 inference and its reloads). Operator
approval for E0 + E1: 2026-10-04. Nothing here has touched the GPU or :8083. The harness was exercised end to
end against a mock server only (`selftest.sh`). Background: `/mnt/raid0/llm/tmp/rope-ctx-assessment/ASSESSMENT.md`
and `RESEARCH.md` in this directory.

## 0. Files

| file | what |
|---|---|
| `yarn_needle.py` | E0 runner: `--build-inputs` (done), `--dry-run`, `--arm A0/A1/A2 --i-own-the-window`, `--gate` |
| `inputs/` | frozen inputs with a sha256 `manifest.json`: 4 haystack segments (50 GovReport documents, 520k tokens), 20 needles + 4 smoke needles, 84-item short suite + 79 truth rows |
| `launch_arm.sh A0/A1/A2` | the scratch launch (section 3), with KFD sampler, proof-line grep, residency and linkage checks |
| `kill_arm.sh A0/A1/A2` | kills only the captured :18083 PID; TERM, then KILL; verifies it is dead |
| `kfd_sampler.py` | 1 Hz own-PID + card VRAM sampler; exits when the server dies; writes `<out>.summary.json` |
| `selftest.sh`, `selftest_mock.py` | harness test against a mock llama-server (no model, no GPU) |
| `vendor/` | `coherence_gate` snapshot @ `95157ad7` (branch `feat/coherence-gate-ec`, **not yet on research main**). Use `--cg-path <research>/scripts/lib` once it is merged. |
| `source_findings.md` | v10 source read: KV types, `-nkvo`, log strings, overflow audit (hazards H-1..H-8) |
| `research_hybrid.md` | literature on hybrid-model context extension |
| `RESEARCH.md` | the research note: (a) hybrids, (b) 1M options ranked, (c) incremental-context cost |
| `cpu_leg/` | the CPU leg (section 9): `yarn_cpu_leg.py`, `cpu_window_gate.py`, `fa_depth_bench.cpp` + `fa_depth.sh`, `prep_inputs.sh` |

`PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python` (it has `tokenizers`). `D=/mnt/raid0/llm/tmp/yarn-e1-20261004`.

## 1. What changed from the assessment's E0/E1 sketch, and why

1. **Prefix reuse is engineered, not assumed.** v10 can only roll a hybrid model's GDN state back to a context
   checkpoint. It creates one at the start of the LAST user message (`server-context.cpp:3640-3700`, plus
   end−(4+ub) and end−4). Q38-T7 put document and question in ONE user message, so each follow-up question
   re-prefilled from token 154 (its report: `cache 154`). Here each haystack segment is its own user turn followed by a
   fixed assistant acknowledgement, and the question is the last user turn. As a result:
   - each further question re-processes ~60 tokens;
   - **the stages chain**: 128k → 240k → 400k → 500k is ONE 500k prefill, not four. That saves about 45–70 min on A1.
   - The runner checks `prompt_n` on every call and **aborts** rather than silently re-prefilling. A 4k/7k smoke chain
     proves reuse on the live instance before any long prefill.
2. **Neutral haystack.** The haystack is US government reports (ZeroSCROLLS GovReport). The needles are declarative
   sentences about fictional entities in the same register (codes such as `BG-8216-U`, names such as `Philippa
   Quennell-Ibsen`). Each value occurs exactly once (dry-run verified). The question is an ordinary reading
   question. The Q38-T7 abstention confound (an AutoKernel haystack with a "vault code") cannot recur.
3. **YaRN proof in the log.** CLI rope flags alone leave `print_info` showing `rope scaling = linear`,
   `freq_scale_train = 1` and `n_ctx_orig_yarn = 524288` (source_findings H-7). A1 therefore also passes the same
   parameters as `rope.scaling.*` metadata overrides. Both routes set identical values, and the model-info lines then
   prove YaRN.
4. **Added diagnostics from the literature** (research_hybrid.md section 3):
   - a local-coherence probe per stage: state collapse or numerics damage local text, while RoPE out-of-distribution
     damages only far retrieval;
   - needle relative distance in the verdict (at 500k, N15/N16 are 448k/349k back and N18/N19 are 149k/50k back);
   - an instant-EOS counter for llama.cpp #27756.
5. **A2 is cheap and does double duty.** It chains through 128k and 240k, where it must match A0 (this proves the
   context_length override alone is inert), then runs 400k as the discrimination control.

## 2. Before the window (main, ~5 min, :8083 still serving)

```bash
cd /mnt/raid0/llm/epyc-orchestrator
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python; D=/mnt/raid0/llm/tmp/yarn-e1-20261004
RL="/workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role build --tag yarn --"   # every CPU test, per the coordinator
$RL $PY $D/yarn_needle.py --dry-run | tail -5        # must end "DRY-RUN OK" (inputs unchanged, needles, budgets, gate self-test)
$RL bash $D/selftest.sh | head -6                    # A0/A0Q4/A1/A2 rc=0, gate rc=0 (mock server on :18999, no GPU)
bash /workspace/scripts/session/verify_llama_cpp.sh  # v10 tree + store integrity
ls /sys/class/kfd/kfd/proc/                          # the GPU must be ours: list every PID with ps; other sessions' PIDs are not ours to kill
cat /mnt/raid0/llm/tmp/gpu-window/mi210.json 2>/dev/null; # and the AutoKernel window state (cpu-window.json is not needed: no CPU regions)
```
At prep time (04:59Z), :8083 was **not listening**, and KFD held another session's
`gpu-20261004-c7f5ac9ad/bin/test-backend-ops -o FLASH_ATTN_EXT` (PID 2539565). Re-check this at window time.

## 3. Launch lines (exact), VRAM per arm, and startup proof

All arms share the production :8083 environment and argv (`logs/server_launches/8083.json`, argv `b865820d`),
with these changes: `-np 1`, no `-md`/`--spec-*` (no drafter), `--cache-ram 0` (no host prompt cache; this also
disables `--cache-idle-slots`), no `--kv-unified` (irrelevant at np 1: `n_ctx_seq` = `-c` either way), port 18083,
and a scratch slot path. The binary is `kernels/production/gpu` → `builds/gpu-20260921-ffc1bac82/bin`, build 10303.
`launch_arm.sh` refuses if `:8083` is listening, if `:18083` is taken, or if the store does not resolve to the v10 build.

Common prefix (shown once):
```
env -u LLAMA_SERVER_SLOTS_DEBUG -u GGML_CUDA_GDN_STATE_BF16 -u GGML_CUDA_FA_MASK_SKIP \
 LD_LIBRARY_PATH=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib \
 HIP_PATH=/opt/rocm ROCM_PATH=/opt/rocm OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false GGML_IQK=1 \
 numactl --membind=3 -- taskset -c 184-191 /mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server \
 -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 18083 -np 1 -t 8 -ub 2048 --flash-attn on --jinja \
 -ctk q8_0 -ctv q8_0 --no-mmap -ngl all --cache-ram 0 \
 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja --device ROCm0 \
 --slot-save-path /mnt/raid0/llm/tmp/yarn-e1-20261004/results/kv_slots_scratch \
```
| arm | arm-specific flags | VRAM estimate [D] |
|---|---|---|
| **A0** native | `-c 262144` | 27.9 fixed + 262,144 × 42 KiB = **≈ 38.4 GiB** |
| **A1** YaRN f2 | `-c 524288 --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 --override-kv qwen35.context_length=int:524288,qwen35.rope.scaling.type=str:yarn,qwen35.rope.scaling.factor=float:2,qwen35.rope.scaling.original_context_length=int:262144` | 27.9 + 524,288 × 42 KiB = **≈ 48.9 GiB** |
| **A2** control | `-c 524288 --override-kv qwen35.context_length=int:524288` | **≈ 48.9 GiB** |

- **VRAM model.** Fixed 27.9 GiB = weights 25.36 + GDN state 0.15 + compute 1.06 + runtime 1.28 (ASSESSMENT section 3). The
  42 KiB per cell is 34,816 B q8_0 KV + 4 KiB KQ mask at ub 2048 + 4 KiB WMMA f16 scratch. At 524,288 that is
  17,408 MiB KV + 2 GiB mask + 2 GiB scratch. Expect ±2 GiB. **The gate is ≤ 55 GiB**, against 64 GiB physical and
  the 62 GiB house limit.
- **The key name is verified from the GGUF:** `qwen35.context_length` = 262144 (UINT32). The GGUF has no
  `rope.scaling.*` keys, and an override also applies to an absent key (source_findings section 3).
- **Hazard H-4.** The WMMA mask offset `nb31*ic0` is int32 and sits 0.4% under overflow at 524,288 × ub 2048. **Never
  raise `-c` above 524288 or `-ub` above 2048 on A1/A2.**

**Proof lines** (`launch_arm.sh` prints them; `yarn_needle.py` refuses the arm unless all of its arm's lines are present
and none of the forbidden ones appear):
```
A1  validate_override: Using metadata override (  int) 'qwen35.context_length' = 524288
    validate_override: Using metadata override (  str) 'qwen35.rope.scaling.type' = yarn        (+ factor, original_context_length)
    print_info: n_ctx_train           = 524288
    print_info: rope scaling          = yarn
    print_info: freq_scale_train      = 0.5
    print_info: n_ctx_orig_yarn       = 262144
    llama_context: n_ctx_seq     = 524288
    llama_context: freq_scale    = 0.5
    llama_kv_cache: size = 17408.00 MiB (524288 cells,  16 layers,  1/1 seqs), K (q8_0): 8704.00 MiB, V (q8_0): 8704.00 MiB
    srv  load_model: initializing, n_slots = 1, n_ctx_slot = 524288, ...
A0  n_ctx_train = 262144 · freq_scale_train = 1 · llama_context: freq_scale = 1 · n_ctx_seq = 262144 · 8704.00 MiB (262144 cells, 16 layers · n_ctx_slot = 262144
A2  override context_length 524288 · n_ctx_train = 524288 · freq_scale_train = 1 · freq_scale = 1 · 17408.00 MiB (524288 cells · n_ctx_slot = 524288
FORBIDDEN (any arm): "exceeds the training context of the model ... capping", "possible training context overflow",
    "Bad metadata override type", "failed to allocate", "out of memory", "HIP error"
```
`ext_factor` (1.0 under YaRN), `attn_factor` (1.0 for f2; the kernel mscale is 1.0693) and beta are never logged
(source_findings H-7). The overrides plus `freq_scale = 0.5` are the proof. The runner also records argv, environ
(`GGML_CUDA_GDN_STATE_BF16` must be unset, keeping the f32 GDN state), ggml libs from `/proc/PID/maps`, and KFD
residency.

## 4. The window

### 4.1 Park :8083's roles, then STOP the server (~1 min)
A parked :8083 still holds about 59 GiB, so the scratch instance cannot fit next to it. **Who waits:** the
`architect_critic`, `coder_escalation` and `ingest_long_context` roles get 503 `role_parked` from here until 4.6.
```bash
cd /mnt/raid0/llm/epyc-orchestrator
$PY -m src.runtime.gpu_window park --roles architect_critic,coder_escalation,ingest_long_context \
    --ports 8083 --holder autokernel --expected-end +190m     # core; use +250m if A2 will run
$PY -m src.runtime.gpu_window status
P=$(ss -ltnp 'sport = :8083' | grep -o 'pid=[0-9]*' | cut -d= -f2); echo "8083 PID $P"
$PY scripts/server/orchestrator_stack.py stop architect_critic
ps -p $P || echo "8083 PID $P dead"; ls /sys/class/kfd/kfd/proc/; cat /sys/class/drm/card2/device/mem_info_vram_used
```

### 4.2 A0: native anchor (~31–35 min including load)
```bash
bash $D/launch_arm.sh A0                 # check the proof block and "KFD vram MiB" (~38 GiB once warmed)
$PY $D/yarn_needle.py --arm A0 --i-own-the-window --server-log $D/results/A0.server.log
bash $D/kill_arm.sh A0
```
The order is smoke (4k→7k chain, ~1 min), then short suite (84 items, ~10 min), then needles 128k (~6–7 min
prefill) and 240k (+8–12 min).

### 4.3 A1: YaRN f2 (~64–85 min including load)
```bash
bash $D/launch_arm.sh A1                 # REQUIRED in the proof block: rope scaling = yarn, freq_scale_train = 0.5, n_ctx_orig_yarn = 262144, freq_scale = 0.5, n_ctx_slot = 524288
$PY $D/yarn_needle.py --arm A1 --i-own-the-window --server-log $D/results/A1.server.log
bash $D/kill_arm.sh A1
```
Chain increments [D], from the fit F to the micro-bench bound M: 128k 5.7–6.9 min, then +8.3–11.6, +17.3–25.9,
+14.0–21.6 min. Total prefill to 500k is 45–66 min. Watch progress with `tail -f $D/results/A1.server.log | grep -i progress`.

### 4.3b A0Q4: q4_0 KV at native length (optional, ~31–35 min). This is the cheap pre-test for 1M option (a).
Run it only if the window has the time; it is not part of the YaRN verdict.
```bash
bash $D/launch_arm.sh A0Q4               # proof: llama_kv_cache: size = 4608.00 MiB (262144 cells, 16 layers ... K (q4_0)
$PY $D/yarn_needle.py --arm A0Q4 --i-own-the-window --server-log $D/results/A0Q4.server.log
bash $D/kill_arm.sh A0Q4
```
VRAM ≈ 27.9 + 262,144 × (18 + 8) KiB ≈ 34.4 GiB. The gate reports C5 = q4_0 KV vs q8_0 KV (A0), paired on the short
suite and the 10 needles. C5 decides only whether option (a) proceeds.

### 4.4 A2: no-YaRN control (optional, ~49–62 min). Run it ONLY if A1 at 400k scored ≥ 4/5.
```bash
bash $D/launch_arm.sh A2
$PY $D/yarn_needle.py --arm A2 --i-own-the-window --server-log $D/results/A2.server.log --suites smoke,needle
bash $D/kill_arm.sh A2
```
A2 is only needed to show the test discriminates. If A1 failed at 400k, discrimination is moot, so skip it and go to 4.6.

### 4.5 Stop rules (pre-registered)
- **Smoke reuse failure.** The runner exits with code 4 before any long prefill. Do not pass
  `--no-abort-on-reuse-fail` on a long stage: a re-prefill per question at 500k costs 45–66 min each. Check
  `checkpoint` lines in the server log (`created/restored context checkpoint`), then stop and report.
- **A0 at 128k with ≥ 3/5 empty answers** (the #27756 instant-EOS signature, which is native and not YaRN). Stop E1. The
  native baseline is broken on this kernel, and that is a production finding, because :8083 serves 262K per request.
  Restore production and report it.
- **A1 at 400k ≤ 1/5.** Let 500k run (14–22 min incremental, which completes the curve), skip A2, then restore.
- **Overrun.** If the window passes its `expected-end`, stop after the current stage. The rows are persisted per call.
- **Any forbidden log line or a server death.** Record it. The #27090 "silent exit near 520K" belongs to the H-4 class
  (a crash is a bug, not a quality result). Our 500k stage peaks at about 499.1k tokens, under the 524,288 KV size.

### 4.6 Restore production (~3–5 min)
```bash
bash $D/kill_arm.sh <last arm>; ls /sys/class/kfd/kfd/proc/       # no :18083 PID left
cd /mnt/raid0/llm/epyc-orchestrator
$PY scripts/server/orchestrator_stack.py reload architect_critic
P=$(ss -ltnp 'sport = :8083' | grep -o 'pid=[0-9]*' | cut -d= -f2)
$PY -c "import json;d=json.load(open('logs/server_launches/8083.json'));print(d['argv_sha256'][:8],d['pid'])"   # b865820d, == $P
tr '\0' '\n' < /proc/$P/environ | grep SLOTS_DEBUG || echo clean
$PY -m src.runtime.gpu_window restore && $PY -m src.runtime.gpu_window status
curl -s localhost:8000/v1/passthrough/architect_critic/chat/completions -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"What is 7*8? Answer with the number."}],"max_tokens":32,"chat_template_kwargs":{"enable_thinking":false}}'
```
Production never saw rope flags. The scratch instance used `--cache-ram 0` and its own slot path, so production's
`/mnt/raid0/llm/cache/kv_slots/architect_critic` and `tmp/kv_prefix_history.local_8083.json` hold no YaRN-geometry
entries (intake-1347#record pattern), and there is nothing to purge.

## 5. Timeline

| step | :8083 | est. (F – M) |
|---|---|---|
| 2 pre-window checks | serving | 5 min |
| 4.1 park + stop | **down** | 1 min |
| 4.2 A0 (load, smoke, short, 128k, 240k) | down | 31–35 min |
| 4.3 A1 (load, smoke, short, 128k→500k chain) | down | 64–85 min |
| kills (×2) | down | 2 min |
| 4.6 restore + verify | reload | 3–5 min |
| **core total (A0 + A1)** | | **≈ 1 h 45 min – 2 h 10 min**; roles unavailable ≈ 1 h 40 min – 2 h 05 min |
| 4.4 A2 (optional, conditional) | down | +49–62 min (**≈ 2 h 35 min – 3 h 10 min** with A2) |
| 4.3b A0Q4 (optional, option-a pre-test) | down | +31–35 min |

- **F** is the assessment's prefill fit (Q38-T7 554 t/s @16k, 439 t/s @80k).
- **M** is the KVU-19a micro-bench quadratic (+0.052 s per 1k occupied cells per 2048-token chunk). M over-predicts the
  measured 80k prefill by about 15%, so treat it as an upper bound.
- Chaining makes the core run cheaper than the assessment's ~2.5 h even though the ranges are wider.
- No CPU regions are used (`numactl --membind=3`, `taskset 184-191`, as in production :8083), so no AutoKernel CPU
  window is needed.

## 6. Pre-registered pass criteria (decided before any run; `yarn_needle.py --gate` applies them)

Greedy decoding throughout (temperature 0, top_k 1), thinking off, and real token ids (server `/tokenize`) for
coherence_gate degeneracy.v2.

| # | criterion | rule | role |
|---|---|---|---|
| C1 | short context | coherence_gate A1 vs anchor A0 over 84 items: **0 REGRESSION** at tier 0/1 (gsm8k numeric, mmlu/mmlu_pro/letter, f1, degeneracy.v2). The 14 production-mix items with no ground truth go to NEEDS_REVIEW, so the gate itself will read INCOMPLETE; the regression count decides. Improvements and graded accuracy are reported alongside. | **Informational.** A failure confirms YaRN can only ever be a separate mode, which is already the plan. |
| C2 | within native (128k + 240k, 10 paired needles) | A1 correct ≥ A0 correct − 1, and no A1 needle answer degenerate | decides |
| C3 | beyond native | A1 ≥ 4/5 at 400k AND ≥ 4/5 at 500k, with no degeneracy. If A2 ran: A2 ≤ A1 − 2 at 400k, otherwise the test is "not discriminating" and C3 is not a pass. | decides |
| C4 | memory | KFD own-PID peak ≤ 55 GiB for every arm (`results/kfd_<arm>.jsonl.summary.json`) | decides |
| — | A2 inertness | A2 vs A0 at 128k/240k: expected byte-identical (tier 0) | sanity: if it is not identical, the override is not inert and C2 is confounded |

**Overall** = PASS iff C2, C3 and C4 all pass. FAIL if any of them fails. INCOMPLETE otherwise.

```bash
$PY $D/yarn_needle.py --gate --a0 $D/results/A0/<ts> --a1 $D/results/A1/<ts> [--a2 $D/results/A2/<ts>] [--a0q4 $D/results/A0Q4/<ts>] \
    --kfd $D/results/kfd_A0.jsonl.summary.json $D/results/kfd_A1.jsonl.summary.json [$D/results/kfd_A2.jsonl.summary.json]
# -> gate/verdict.json, gate/VERDICT.md, gate/short_A1_vs_A0.json, gate/needle_{128k,240k}_A1_vs_A0.json
```

**Outcomes** (from ASSESSMENT section 6):
- **PASS:** prepare a stack-change package for an on-demand "long-context mode" profile (who waits during the swap;
  the per-request cap in `src/backends/context_limits.py`; the DFlash2 acceptance question, where metadata-override
  YaRN does not leak into the `dflash` drafter but CLI flags do, H-6). 1M becomes the RESEARCH.md section b item.
- **FAIL:** archive INF-59 with this evidence. 262K stays the ceiling.

## 7. Reading a failure (research_hybrid.md section 3)

| observed | points at |
|---|---|
| far needles (> 262k back: N10/N11 at 400k, N15/N16 at 500k) lost, near ones (N13/N14, N18/N19) kept | attention reach: YaRN insufficient at f2 |
| near needles also lost; local probe DEGENERATE/garbled | the long prefix: GDN state saturation/drift or numerics, not RoPE |
| empty answers (`predicted_n` ≤ 1) also in A0 ≤ 262k; non-monotonic in length | #27756 numerics/implementation fault |
| A2 ≈ A1 at 400k | the test does not discriminate (filler too easy, or the model generalises without YaRN) |
| abstentions | haystack/needle confound; should not occur with this design, so re-read the stored answers |

## 8. After the run (owning session)

- Rewrite INF-59 with the verdict and its evidence paths. The draft row is in ASSESSMENT section 5.
- Recompile `wiki/context-extension.md` (stale facts listed in ASSESSMENT section 1 row 5).
- **Belief kernel (CLAUDE.md):** E1 produces measurements. Add a source row to `scripts/vidya/adapters/README.md` and a
  task in `handoffs/active/vidya-belief-substrate-program.md` for `results/<arm>/<ts>/calls.jsonl` and
  `gate/verdict.json`. The schema `inf59.yarn_e1.gate.v1` carries the arm, kernel build, inputs manifest sha256 and
  coherence_gate version, which is the claim tuple an adapter needs.
- Results are under `$D/results/<arm>/<ts>/`: `preflight.json`, `calls.jsonl` (every call, full text, token ids,
  timings, KFD), `short.jsonl`, `needle_<stage>.jsonl`, `local_<stage>.jsonl`, `report.json`.

## 9. CPU leg: run BEFORE the GPU E1 where a window allows (coordinator/operator directive 2026-10-04)

**Why and what.** RAM is abundant on the CPU side, so 524k and 1M can be tested there without a GPU window. The model
is **Qwen3.6-35B-A3B Q8_0** (`qwen35moe`), the CPU-served hybrid with the 27B's architecture family: 3 GDN : 1 gated
full attention, 64/256-dim interleaved-MRoPE rotary, θ 1e7, native 262,144, 10 attention layers × 2 KV heads × 256
[M, GGUF header]. Its q8_0 KV at 1M is 10.6 GiB of host RAM. Qwen3.8-Flash-Next (`qwen4exp`, QSA sparse attention + GDN)
is an optional arm (FY2), and it requires `GGML_FUSED_DECODE_OFF=1`: the fused decode hardcodes `freq_scale=1,
ext_factor=0` and would decode without YaRN until the DCA/fused-fix patch lands.

| arm | launch (scratch :18070, np 1, no drafter, `--cache-ram 0`, CPU store `builds/cpu-20260921-ffc1bac82`) | builds to | probes at |
|---|---|---|---|
| CN | `-c 262144` | ~248k | 32k, 64k, 128k, 192k, 248k |
| CY2 | `-c 524288` + YaRN f2 (CLI flags + `qwen35moe.rope.scaling.*` / `context_length` overrides) | ~512k | 32k, 128k, 248k, 320k, 400k, 510k |
| CY4 | `-c 1048576` + YaRN f4 (same, factor 4) | ~1.03M | 32k … 1.03M (9 depths), **plus one cold prefill at 128k** |
| FY2 (opt) | Flash-Next IQ4_XS, f16 KV, `GGML_FUSED_DECODE_OFF=1`, f2 | ~512k | as CY2 |

**Measured per arm, built the way an agent session builds context.** The context grows in 8k-token turns; each turn is
its own user message plus a fixed acknowledgement, with prefix reuse verified on every turn.
- the **append cost** of every turn versus depth;
- at each probe depth:
  - **decode-at-depth**: 128 forced tokens with `ignore_eos`;
  - 5 needles at relative distances 0.1–0.9 × depth;
  - a **local-coherence probe** that checks the recurrent state past 262k (degeneracy.v2);
- the **84-item short-text suite**, paired against CN with coherence_gate (YaRN's short-text warning, at both f2 and f4);
- **one cold prefill** (CY4 at 128k), compared against the sum of its incremental turns (the compaction case).

**Governance (built into the code).**
- AutoKernel's campaign is CPU-only and holds q0–q3 (cpus 0–95). The SMT siblings 96–191 are the same physical cores, so
  **no non-overlapping NUMA budget exists while it runs.** `--budget-cpus` is honoured only if it does not overlap.
- Every CPU command goes through `region-lock run --cpu-list 0-95 --role build --tag yarn --`. That covers the server
  inside `yarn_cpu_leg.py`, `fa_depth.sh` build/run and `prep_inputs.sh`. The flock is the truth: region-lock waits for
  held windows.
- The runner starts a step (one 8k turn, one probe set, the short suite, or the cold point) only when
  `cpu_window_gate.py` reports `state == open`, a fresh heartbeat, and a **known** `est_close_at` that leaves the
  step's ETA plus a 5-min margin. An open window with `est_close_at: null` is treated as "no".
- The ETA comes from a cost model seeded by C0 and refit online from the arm's own turns and decode probes.
- At a window boundary the runner **saves the slot right after a turn**, so the saved tokens are an exact prefix of
  the next request. A hybrid model cannot roll back without a checkpoint, and restoring a probe-state slot would force
  a full re-prefill. It then stops **only its own** server: the PID on :18070 is verified by cmdline, TERM then KILL,
  and the region-lock wrapper exits. In the next window it relaunches and restores with `/slots/0?action=restore`.
  Turns are persisted per call, and `state.json` makes the run resumable.

**Sequence.**
```bash
D=/mnt/raid0/llm/tmp/yarn-e1-20261004; PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
bash $D/cpu_leg/prep_inputs.sh 0            # C-1, ~2 min under region-lock: freeze cpu_leg/inputs (1.04M tokens, 8k turns, 42 needles) + dry-run
bash $D/cpu_leg/fa_depth.sh build           # C0a, ~20 s compile, gated + region-locked
bash $D/cpu_leg/fa_depth.sh run             # C0b, ~15-30 min: CPU FA us/op at n_kv 16k..1M, nb 1 and 2048, 35B and 27B shapes, q8_0/q4_0, 24/48/96 threads
$PY $D/cpu_leg/yarn_cpu_leg.py --arm CN  --i-own-the-window --wait   # each arm: resumable, window-hopping
$PY $D/cpu_leg/yarn_cpu_leg.py --arm CY2 --i-own-the-window --wait
$PY $D/cpu_leg/yarn_cpu_leg.py --arm CY4 --i-own-the-window --wait
$PY $D/cpu_leg/yarn_cpu_leg.py --gate       # results/VERDICT.md: decode tok/s and turn cost vs depth, needles by distance, local probes, C1 short (CY2/CY4 vs CN), C3 (>= 4/5 beyond 262k)
```
`bash $D/cpu_leg/fa_depth.sh run-gpu` (optional) puts the same micro-bench on the MI210 for the 27B shape, including q4_0, and
confirms q5_1 is unsupported on v10. It runs inside the GPU E1 window, after A1, in ~5 min.

**Time [D, before C0; C0 replaces the bracket with measured numbers].**
- C-1 + C0 take ≈ 35 min of one open window.
- The build integral is dominated by CPU flash-attention at depth: 2048 × n × 16,384 FLOP × 10 layers per ubatch, at an
  assumed 1.5–3 TFLOPS effective. That gives ≈ 4–7.5 min per 8k turn at 512k and 7.5–15 min at 1M.
- Per arm, including probes and the short suite:

  | arm | estimate |
  |---|---|
  | CN to 248k | ≈ 1–1.5 h |
  | CY2 to 512k | ≈ 2.5–4.5 h |
  | CY4 to 1M | ≈ 9–17 h |
  | **total** | **≈ 13–23 h of open-window CPU time**, spread over many windows |

- Each window costs ~2–6 min of relaunch and restore (37 GB load from page cache plus a ≤ 11 GiB slot restore).
- **Ordering versus GPU E1.**
  1. Run C-1, C0, CN and the CY2 short suite in the first open windows, before E1. Together they take ≈ 2 h and give the
     CPU-side short-text verdict plus the decode/append-vs-depth curves.
  2. Do **not** hold the GPU E1 behind the 1M CPU build. It uses disjoint resources (MI210 plus host cpus 184–191, the
     production :8083 placement) and needs no CPU window.
  3. Let CY2 and CY4 continue window by window. If windows are scarce, drop CY2: CY4 also passes 512k, and the GPU E1
     already supplies f2 at 512k on the 27B.
- **Cost-model check.** If C0 shows CPU FA at 1M worse than ~0.3 µs per cell per layer at 96 threads, cap CY4 at 768k
  and record why.

**Blocker found at prep time: AutoKernel's open windows are far too short for this leg.**
- Measured from `/mnt/raid0/llm/autokernel/cpu-window.events.jsonl` (64 windows): the last 20 lasted **1.8–5.3 min**
  (est_close_at − opened_at), spaced 1–3 h apart. The median over all 64 is 5.4 min.
- Outside those windows region-lock reports q0–q3 HELD by `autokernel-cpu`. On 2026-10-04 at 05:12Z the input build
  (`prep_inputs.sh`, ~2 min of tokenising) timed out after 900 s waiting for the lock. Exit 75, blocker
  `autokernel-cpu`.
- At that cadence, a single 8k turn at 512k (4–7.5 min) does not fit any window. Neither does the 37 GB model load
  (~3–6 min). The 13–23 h build would take weeks of windows.
- **Decision for the operator / coordinator** (this is the only thing blocking the CPU leg):

  | option | what it costs | recommendation |
  |---|---|---|
  | (i) a dedicated CPU block: pause the AK CPU campaign for one contiguous block | CN + CY2 + short suites ≈ 4–6 h, or + CY4 to 1M ≈ 13–23 h | **CN + CY2 in one ~6 h block**, ideally overnight. CY4 to 1M only if CY2 passes |
  | (ii) carve one NUMA node out of AK's claim (e.g. node 3: 72–95 + 168–191) | AK runs on 3/4 of the host; the CPU leg runs at ~1/4 speed, so ≈ 4× the hours | not recommended: 1M becomes days |
  | (iii) skip the CPU leg's long builds | the GPU E1 still answers 512k for the 27B | keep only C-1 + C0 (≈ 35 min, the per-step attention numbers for option (b)) |

- Option (i) means running the same runner with `--block-until <ISO end of block>` while AK is paused. This replaces the
  window gate with the block deadline, and the runner still takes region-lock.
- `cpu_window_gate.py` keeps the leg from ever starting in a window it cannot finish. With 2–5 min windows it will
  correctly wait forever, so `--wait` alone does not make progress.

**SCHEDULED (coordinator, 2026-10-04; `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` row 9, agreed by ak-ds41-main).**
- **Inputs:** built 2026-10-04 by `prep_inputs.sh`, which is self-wrapped in region-lock on quadrant q0 only
  (`--cpu-list 0-23 --role build`, pinned with `taskset -c 0-23`, nice 19). Do NOT wrap it
  in a second region-lock: a nested acquire on q0–q3 deadlocks.
- **Step-3 CPU window, after workspace-89's c1/c2 (~07:40–07:55Z) and before the fold GPU slot: the CPU attention
  micro-bench, ~15–35 min, one command.** `fa_depth_bench` is already compiled. The `bench-locked` mode takes no
  nested lock and does no AK window check:
  ```bash
  /workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role bench --tag yarn -- \
      bash /mnt/raid0/llm/tmp/yarn-e1-20261004/cpu_leg/fa_depth.sh bench-locked
  # -> cpu_leg/results/fa_depth.txt (us/op and ns/cell per attention layer; 35B + 27B shapes; q8_0/q4_0; nb 1 and 2048; 24/48/96 threads at 1M)
  ```
- **The dedicated ~6 h block (AK CPU lanes parked; after the GPU block and the :8083 restore, before the AK lanes
  relaunch): one command.** Do NOT wrap it in region-lock: the runner launches its own server under
  `region-lock --cpu-list 0-95 --role bench` (a measurement claims the full 0–95).
  ```bash
  bash /mnt/raid0/llm/tmp/yarn-e1-20261004/cpu_leg/block.sh <ISO end of block, e.g. 2026-10-04T18:30:00Z>
  # CN (native, to ~248k) then CY2 (YaRN f2, to ~512k) -> cpu_leg/results/{CN,CY2}/, block.log, VERDICT.md
  ```
  - The runner stops each step that would overrun the end time and keeps the slot saved. Re-running with a new end
    time resumes.
  - CY4 (1M, 9–17 h) does not fit a 6 h block. Run it in a later block:
    `$PY $D/cpu_leg/yarn_cpu_leg.py --arm CY4 --i-own-the-window --block-until <ISO>`.

**Pre-registered CPU criteria.** These mirror E1:
- C1: 0 REGRESSION on the short suite (CY2, CY4 vs CN; informational).
- C2: at ≤ 248k, CY2 and CY4 correct ≥ CN − 1, paired by depth.
- C3: CY2 ≥ 4/5 at every probe depth > 262k; CY4 likewise to 1.03M; local probe OK at every depth.
- Recorded, not gated: decode tok/s and append seconds vs depth, and cold-vs-incremental.

A CPU pass is evidence for the 35B, not for the 27B. It de-risks the GPU E1 and informs 1M option (b) (host-side
attention cost), but it does not replace the GPU E1.
