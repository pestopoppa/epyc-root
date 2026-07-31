<!-- Persisted 2026-07-23 from the op7-residuals workflow (5 agents: drafter +
adversarial verifier); the verifier's 6 corrections are applied inline. -->

> # ⛔ DEPRECATED — 2026-07-31 — DO NOT EXECUTE
>
> **The promotion this runbook describes is CANCELLED, and the MiniCPM-o weights it
> depends on have been DELETED from disk.** Precondition **P4 ("Artifacts on disk")
> can no longer be satisfied: `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/` no longer
> exists. Recovery would require a re-download from `openbmb/MiniCPM-o-4_5-gguf`.
>
> **Why.** Measured 2026-07-31 on the MI210 — 42 questions (OCRBench + ChartQA), each
> model at the best quantization present on disk, scored offline with a
> unit/whitespace-normalizing scorer:
>
> | model · quant | accuracy |
> |---|---|
> | Qwen3-VL-30B-A3B Q4_K_M | **36/42** |
> | Qwen2.5-VL-7B Q4_K_M (incumbent, State A) | **35/42** |
> | Qwen3-VL-8B Q8_0 | 33/42 |
> | **MiniCPM-o-4.5 Q8_0** | **31/42** |
> | Qwen3-VL-4B Q8_0 | 29/42 |
>
> Promoting MiniCPM-o would have been a **quality downgrade** against the very State-A
> alias this runbook rolls back to. Raw per-question results
> `/mnt/raid0/llm/tmp/vlquality_results.json`; harness `/mnt/raid0/llm/tmp/vlquality.py`.
>
> **The evidence that motivated it does not survive.** The earlier "+10pp" (M-1, n=10)
> was **one** discordant question, and that question was a **scoring artifact** — the
> incumbent answered `0.11 kWh` where the accepted answer was `0.11` (case
> `vl_chart_test_0563`). Corrected, the two models tied **7/10**. Verify at
> `epyc-inference-research/artifacts/minicpm-o-phase1-v8-20260726/live-20260726T174112Z-O98PrJ/escalation-{baseline,candidate}-scored.json`
> (rows carry `score.pass`). The throughput evidence cited below stands; it was never
> the binding constraint, and the 2026-07-19 slice already had Qwen2.5-VL *faster*.
>
> **The speech rationale is also dead.** A dedicated Qwen3-TTS-12Hz-0.6B (1.14 GB) is
> already on disk and Qwen3-ASR is already supported by the frozen v8 kernel, versus
> MiniCPM-o's 22 GB bundle (~9.13 GB of which was a duplicate LLM backbone plus the
> vision tower measured above).
>
> **What is still usable here.** The Step 1–7 *mechanics* — the State-A/State-B
> choreography, edit-the-MASTER-registry rule, quiesce/reload discipline, rollback
> anchor — are model-agnostic and remain the reference pattern (this is why
> `epyc-orchestrator/scripts/server/gpu_shadow_lane.py` still cites this file). If
> `vision_escalation` is ever revisited, the forward candidate is **Qwen3-VL-30B-A3B
> Q4_K_M** (36/42, the only arm measured above the incumbent) — substitute its
> `model/path/mmproj/sha256/device/runtime` block per the model-agnostic note below.
> Do not reuse the MiniCPM-o literals.
>
> Registry entry `minicpm_o_45_local_multimodal` in the master registry is marked
> `deprecated: true` and retained as the audit trail.

# Runbook — Deterministic `vision_escalation` → MiniCPM-o Promotion (port 8087, MI210)

**⛔ DEPRECATED 2026-07-31 — see the banner above. Everything below is retained as
the historical record and as a model-agnostic mechanics reference. Do not execute it
for MiniCPM-o.**

**Filed**: 2026-07-23, per operator directive in `handoffs/active/multimodal-pipeline.md:488` ("when ready, promotion into the stack must be deterministic, not bespoke").
**Status**: PARKED until operator grant. This document is mechanics only — it executes whichever model the operator picks.

**Model-agnostic note (required by the task charter)**: prior evidence is split — MiniCPM-o-4_5 validated 2026-07-18 (MI210 decode **110.81–122.18 t/s** reasoning-off (`/mnt/raid0/llm/tmp/k35-minicpm-o45-reasoning-off-20260717T1911Z/summary.json`; max 126.39 in the 07-19 longdecode run), K35 fixed fixtures **4/4**, mixed-service matrix **8/8** at 2K/8K with frontdoor overlap incl. active-overlap decode 64.19–108.08 (`/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z/summary.json`)), while the 2026-07-19 long-decode slice found the Qwen2.5-VL safe alias *faster on that run* (133.29 t/s quality mean / 118.50 t/s long-decode vs MiniCPM-o 120.54 / 109.18; artifact `epyc-inference-research/data/k35_vision_matrix/k35_worker_vs_escalation_mi210_longdecode_20260719T004016Z/summary.json`). This runbook does not adjudicate that choice. Steps 1–7 are identical for any candidate: substitute the candidate's `model/path/mmproj/sha256/device/runtime` block in Step 1 and its expected-throughput band in Step 6. All literals below are written for the operator-named default candidate, **MiniCPM-o-4_5 Q4_K_M on MI210**.

**Registry states referenced throughout**:
- **State A (safe alias / rollback state)** = the current committed state: Qwen2.5-VL-7B alias on 8087, CPU (`--device none`). Reached via orchestrator commits `139ba643` → `91cf4033` ("Align vision escalation launch alias") → `dacd15a2` ("Run vision escalation alias on CPU").
- **State B (promoted state)** = MiniCPM-o on MI210 HIP. Historical precedent: orchestrator commits `4ab4e0ee` ("Switch vision escalation to MiniCPM-o lane") + `a6f20ae1` ("Wire vision escalation to v7 HIP runtime"). The launcher code paths those commits added (**still present**: `_build_vision_command` at `epyc-orchestrator/scripts/server/orchestrator_stack.py:543-590`, `stack_runtime.runtime_requirements_for_role`, priors-driven `binary_path/device/reasoning/override_kv`) mean promotion is **data-only + 3 constant lines** — no launcher code changes.

---

## 0. Preconditions (all must hold before Step 1)

| # | Precondition | How to verify |
|---|---|---|
| P1 | **Operator grant** — explicit approval for (a) the promotion itself, (b) the Step-4 contention re-bench and Step-6 smokes (inference; MEASUREMENT policy: benchmarks run only via codified recipes with operator approval). | Written operator directive in the session. |
| P2 | **MI210 free** — the operator's external Qwen3.5-122B bench process on port **18072** is *not a stack lane and operator-owned — never kill it*; it must be finished/vacated. | `rocm-smi --showmemuse` ≈ 0% VRAM; `ls /sys/class/kfd/...` / `rocm-smi --showpids` shows no compute PIDs; `ss -ltn | grep 18072` empty. |
| P3 | **Quiet window** — no AutoPilot running, no EvalTower batch in flight, no concurrent model downloads. If an eval is mid-run at any reload/stop point: **SIGSTOP the eval runner, act, SIGCONT** (naked reloads burned 532 queued questions on 2026-07-22 — `docs/runbooks/role-alias-change-runbook.md:66-70`). | `pgrep -af autopilot.py` empty; no fresh writes under `epyc-orchestrator/orchestration/reports/`. |
| P4 | **Artifacts on disk** — model + vision projector present and hash-known. | `ls -l /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q4_K_M.gguf` (5,026,714,400 bytes; sha256 `1237a97e…bbc0932` per master registry `artifact_status.hf_metadata.q4_k_m`) and `…/vision/MiniCPM-o-4_5-vision-F16.gguf` (1,095,113,184 bytes; sha256 `1453678c…ba82f421` per lean-era commit `4ab4e0ee`). |
| P5 | **Production v8 HIP binary healthy** — `/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server --version` reports `version: 10107 (67a433bf4)`. **Deliberate deviation from the `a6f20ae1` diff**: that commit (2026-07-18, pre-cutover) pointed at `/mnt/raid0/llm/llama.cpp-experimental/build-hip/bin`; since the 2026-07-25 v8 final freeze the production HIP tree is canonical, and serving off the experimental tree would violate production-kernel discipline. All `binary_dir` literals below use the **production** tree. |
| P6 | **Clean git baselines** in `epyc-inference-research` and `epyc-orchestrator` (the rollback anchor is a git revert; uncommitted drift makes rollback nondeterministic). Fetch-before-commit rule applies on main. | `git status` / `git log @{u}..` in both repos. |
| P7 | **Realized fleet is the terminal both-mode big+quarters lineup**: frontdoor half0@8070+4q, worker full@8072+4q, ingest half0@8085+4q, architect CPU Q4@8083, worker_vision@8086, vision_escalation@8087. | `uv run python scripts/server/orchestrator_stack.py status`; runtime-facts manifest `/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json` shows realized mode `both` + non-empty `selected_servers`. |

---

## Step 1 — Registry rebind (master registry is the ONLY registry you hand-edit)

**House rule (banner of the lean file, `epyc-orchestrator/orchestration/model_registry.yaml:1-16`)**: the lean registry is **auto-compiled from the master at every `orchestrator_stack.py start`** by `src/registry/registry_compiler.py`. A hand-edit to the lean (which is how the 2026-07-18 rebind was done, commits `4ab4e0ee`/`a6f20ae1` (NOTE: lean-registry compile was already default-on by then — `6f75ceab`, 2026-06-27 — and the MASTER registry never carried the MiniCPM binding, so the 2026-07-18 rebind was a clobber-exposed lean hand-edit; this runbook's edit-the-MASTER instruction exists precisely to not repeat that)) would now be **silently clobbered on the next start**. The edit goes in the **MASTER**: `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml`.

### 1a. Replace `roles.vision_escalation` (master lines **4072–4138**, i.e. from `  vision_escalation:` up to but excluding `  worker_summarize:` at 4139)

The replacement below is the `4ab4ee0ee`+`a6f20ae1` lean state reconstructed into master style, with two deliberate deviations flagged: **(i)** `binary_dir` → production v8 HIP tree (P5); **(ii)** historical `k35_*_observation` rows are **retained** (append-only registry discipline — never erase history to "fix" it).

```yaml
  vision_escalation:
    tier: C
    port: 8087
    description: "Vision escalation - MiniCPM-o 4.5 Q4 on MI210 with reasoning disabled"
    model:
      name: MiniCPM-o-4_5
      path: /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q4_K_M.gguf
      mmproj_path: /mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/vision/MiniCPM-o-4_5-vision-F16.gguf
      quant: Q4_K_M
      size_gb: 6.2
      architecture: dense
      ctx_max: 8192
      sha256: 1237a97ee081b8abebc47aa7dad565701e8f5f904cdc92f6723ac4281bbc0932
      mmproj_sha256: 1453678cc4e4fe18de241952962e234f265cb8dda780773526103ab8ba82f421
    thinking_control:
      mode: llama_server_reasoning_off
      effective_mode: no_reasoning_trace
      evidence_strength: K35 fixed-fixture MI210 evidence
      evidence: K35.11/K35.13c passed fixed OCR/chart fixtures and mixed-service checks with --reasoning off.
    candidate_roles:
    - vision
    acceleration:
      type: baseline
      disallowed:
        - speculative_decoding
        - prompt_lookup
      reason: MiniCPM-o vision lane is served as baseline multimodal llama-server on MI210; no spec-dec evidence.
    performance:
      baseline_tps: 110.81
      optimized_tps: 110.81
      speedup: 1.0x
      vl_score: {pct: 100.0, raw: "4/4 K35 fixed fixtures"}
      benchmark_date: 2026-07-17
      evidence: /mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z/summary.json; K35.13c mixed-service matrix passed 8/8 context/fixture pairs with frontdoor overlap.
      k35_longdecode_observation: >
        2026-07-19 current experimental-v7 `ed4091266` comparison against the
        MiniCPM-o candidate found the temporary Qwen2.5-VL alias still faster
        on MI210 (`4/4`, quality decode mean `133.29 t/s`, long decode `118.50
        t/s`). MiniCPM-o also passed the same four fixtures but decoded the
        long sample at `109.18 t/s`. Superseded for the live binding by the
        <PROMOTION-DATE> operator-directed promotion recorded in notes.
    memory:
      residency: hot
      pinned: false
    server:
      endpoint: "http://localhost:8087"
      api_format: openai_multimodal  # /v1/chat/completions with image_url content
      device: ROCm0
      reasoning: 'off'
      runtime_requirements:
        binary_dir: /mnt/raid0/llm/llama.cpp/build-hip/bin
        ld_library_path:
        - /mnt/raid0/llm/llama.cpp/build-hip/bin
    escalation:
      from: worker_vision
      auto_wired: false  # NOT currently auto-triggered - request manually
      triggers:
      - math or equations in image
      - complex multi-step diagram
      - video longer than 10 minutes
      - GUI automation failure
      - cross-reference multiple image regions
    paged_attention:
      recommended: false
      reason: no K35 evidence that paged attention helps MiniCPM-o VL fixtures.
    notes: |
      <PROMOTION-DATE> operator-directed promotion (this runbook). K35.11 fixed
      OCR/chart candidate gate passed CPU 4/4 and MI210 4/4 with --reasoning
      off; MI210 decode observed 110.81-122.18 t/s. K35.12 co-residency smoke
      passed with frontdoor on MI210. K35.13c operational fixture service
      matrix passed 8/8 active fixture/context pairs; active overlap averaged
      94.77 t/s frontdoor plus 85.22 t/s MiniCPM-o. Keep port 8087 for
      call-site stability and cap serving at one active slot (-np 1 is the
      capacity cap). Rollback is the Qwen2.5-VL worker alias on the same port
      (State A of the promotion runbook; commits 91cf4033/dacd15a2 shape).
```

Also update the trailing comment on master line **249** (`vision_escalation: 60    # temporary Qwen2.5-VL alias while 30B escalation replacement is gated`) → `# MiniCPM-o MI210 escalation lane (promoted <PROMOTION-DATE>)`. The timeout value `60` itself is unchanged.

Note what you do **NOT** add: no `server_mode` row for `vision_escalation` (it has none — its binding is `stack_manifest.role`, confirmed by `binding: stack_manifest.role` in the compiled priors at `orchestration/derived/stack_priors.yaml:1087`); no `kmp_blocktime`/`env_policy` fields (the priors compiler derives `env_policy: binary_override_strip_ggml` + `kmp_blocktime: 10` automatically whenever `binary_dir` is set — `src/registry/stack_priors.py:1468-1469`). Leave the `minicpm_o_45_local_multimodal` catalogue entry (master ~7904) alone except optionally appending a dated activation observation; its `constraints.forbid: production_stack_registration_without_capacity_cap_or_controlled_reload` is *satisfied* by this runbook (controlled reload = Step 3, capacity: `-np` comes from priors `slots: 1` (orchestrator_stack.py:573-574, fallback 1); `LAUNCH_CONTEXT_TOKENS["vision_escalation"]=8192` independently feeds `-c` (line 576)).

### 1b. Launch-layer fallback constants (3 lines) — `epyc-orchestrator/scripts/server/stack_manifest.py`

These are **fallbacks** (the priors-driven launch path overrides them: `orchestrator_stack.py:558-586` reads `model_path`/`mmproj_path`/`device`/`reasoning` from stack priors first), but they also feed the model-file existence check (`stack_manifest.py:798-804`) and must not lie. Exact edit, reversing `91cf4033`+`dacd15a2`:

```python
# stack_manifest.py:297-302 — BEFORE (State A)
# Temporary 2026-07-19 safety alias: use the same validated Qwen2.5-VL lane
# for escalation until a higher-quality replacement wins the vision gate.
VISION_ESCALATION_MODEL = VISION_WORKER_MODEL
VISION_ESCALATION_MMPROJ = VISION_WORKER_MMPROJ
VISION_ESCALATION_DEVICE = "none"
VISION_ESCALATION_REASONING = "off"

# AFTER (State B)
VISION_ESCALATION_MODEL = str(
    _PATHS["models_dir"] / "MiniCPM-o-4_5-gguf/MiniCPM-o-4_5-Q4_K_M.gguf"
)
VISION_ESCALATION_MMPROJ = str(
    _PATHS["models_dir"] / "MiniCPM-o-4_5-gguf/vision/MiniCPM-o-4_5-vision-F16.gguf"
)
VISION_ESCALATION_DEVICE = "ROCm0"
VISION_ESCALATION_REASONING = "off"
```

Plus two cosmetic-but-truth anchors: `stack_manifest.py:36` port-map comment (`# Temporary VL escalation alias -> Qwen2.5-VL` → `# MiniCPM-o MI210 escalation lane`) and the status label at `orchestrator_stack.py:1279`: `model_name = "Qwen2.5-VL-7B Q4_K_M (temporary vision escalation alias)"` → `model_name = "MiniCPM-o-4.5 Q4_K_M (vision escalation on MI210)"` (this exact string existed pre-`dacd15a2`). **Unchanged and verified still present**: `ROLE_LAUNCH_META["vision_escalation"] = {"tier":"hot","mode":"vision","vision_type":"escalation"}` (`stack_manifest.py:164`), `LAUNCH_CONTEXT_TOKENS["vision_escalation"]=8192` (`stack_manifest.py:309`), NUMA cell `("72-95,168-191", 8087, 24t)` = `NUMA_Q1B` (`stack_numa.py:212-216` — comment there already documents the MiniCPM design: MI210 lane with a 24t host quarter for image preprocessing).

### 1c. Regenerate the lean registry explicitly (don't wait for `start` to do it)

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python -m src.registry.registry_compiler --force
```

(`src/registry/registry_compiler.py:319` CLI; defaults already point master→lean→`.lean_cache_key`. The master edit changes the SHA-256 cache key, so this recompiles even without `--force`; `--force` makes it unconditional.)

**Verify Step 1** (checklist):
- [ ] `grep -n "MiniCPM-o-4_5-Q4_K_M" orchestration/model_registry.yaml` (lean) shows the role block regenerated from master; banner `Compiled at:` timestamp is fresh.
- [ ] Lean `roles.vision_escalation.server` contains `device: ROCm0`, `reasoning: 'off'`, `runtime_requirements.binary_dir: /mnt/raid0/llm/llama.cpp/build-hip/bin`.
- [ ] `git diff` in orchestrator touches ONLY: lean registry (generated), `stack_manifest.py` (3 constants + 1 comment), `orchestrator_stack.py` (1 label line). Anything else = stop.

---

## Step 2 — Pipeline gates (no-inference; both must be green before any process is touched)

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

(`scripts/registry/stack_change_pipeline.py:913` — `update` regenerates `orchestration/model_descriptors.yaml`, `orchestration/derived/stack_priors.yaml`, procedure role enums, and `docs/generated/current_stack_summary.md`; `check --run-promotion-gate` additionally runs the no-inference pytest promotion gate: simulated model-swap fixtures + `tests/unit/test_build_server_command_helpers.py` launch parity + seeding preflight targets, per `PROMOTION_GATE_TARGETS` at `:63-67`.) It compiles under the **realized fleet mode** (ESC-8 Fix 6) — with the live fleet up it cannot be poisoned by a clean shell. If it refuses with `StackPriorsModeError`, nothing is listening — that means P7 failed; do not pass a manual mode override. If pre-existing `--allow-known-gaps` warnings are the *documented* known set (`model-stack-update-pipeline-audit.md`), they are acceptable; **new** gaps are not.

**Verify Step 2** (checklist) — compare the regenerated `orchestration/derived/stack_priors.yaml` `vision_escalation` block against the known-good `a6f20ae1`-era compile (reproduced below; only `binary_path/binary_dir/ld_library_path` differ, per deviation P5):
- [ ] `model_id: minicpm-o-4_5-q4_k_m`, `display_name: MiniCPM-o-4_5`
- [ ] `launch.requirements.model_path` / `mmproj_path` = the two MiniCPM paths
- [ ] `runtime.binary_path: /mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server`, `binary_dir` + `ld_library_path` same dir
- [ ] `runtime.env_policy: binary_override_strip_ggml`, `kmp_blocktime: 10` (derived — proves the binary override is active; the launcher strips `GGML_*` env for non-canonical binaries, `orchestrator_stack.py:438-449`)
- [ ] `runtime.cache: {context_tokens: 8192, slots: 1}` (slots:1 **is** the one-active-vision-request capacity cap from the K35.13 activation policy)
- [ ] `runtime.flags: {flash_attn: true, device: ROCm0, reasoning: 'off', override_kv: []}`
- [ ] `pytest` gate summary `ok`; NOTE the launch-parity witnesses in `tests/unit/test_build_server_command_helpers.py` were flipped to alias expectations by `91cf4033`/`dacd15a2` — if `check` fails there, update those test expectations to the State-B command shape (that is the designed witness mechanism, not a regression).
- [ ] Operative-URL snapshot before/after byte-identical (no URL should change — same port): snapshot command in `docs/runbooks/role-alias-change-runbook.md:52-53`.

---

## Step 3 — The 8087 server swap (single-role, no-outage for everything else)

The pattern is the 2026-07-23 additive promotion path: **explicit-arg authority, skip-healthy, no-outage** (`stack_commands.py:744-757` `_only_mode_transition_allowed` — an explicit `--numa-mode both` over the realized fleet only ADDs missing instances; skip-healthy leaves every running server untouched, `stack_commands.py:1166-1183`).

```bash
cd /mnt/raid0/llm/epyc-orchestrator

# 3a. Stop ONLY the escalation lane. Use the ROLE-name state key (state maps both
#     'vision_escalation' and 'server_8087' to the same PID; stopping the role key
#     is what lets the subsequent start re-register both cleanly).
uv run python scripts/server/orchestrator_stack.py stop vision_escalation

# 3b. Confirm death + port free (kill_process_tree is SIGTERM→wait→SIGKILL, stack_processes.py:116-146)
ss -ltn | grep 8087   # must be empty

# 3c. Start ONLY the escalation lane, additive over the live big+quarters fleet.
uv run python scripts/server/orchestrator_stack.py start --only vision_escalation --numa-mode both
```

What 3c does deterministically: recompiles the lean registry (idempotent after 1c), runs the registry validator + the same canonical stack-change gate (refusing if Step 2 wasn't green), prewarms, sees every other port healthy and **skips** them, then launches 8087 via `_build_vision_command(vision_type="escalation")` (`orchestrator_stack.py:543-590`) with the priors-driven HIP binary, `--device ROCm0`, `--reasoning off`, `-np 1 -c 8192 -t 24`, pinned to `NUMA_Q1B` cpuset `72-95,168-191`. Do **not** use `--skip-stack-change-gate` (emergency diagnostics only, `docs/reference/stack-change-launch-runbook.md:113-129`).

```bash
# 3d. API-only reload so the API re-reads regenerated priors (vision_serving/vision-role set,
#     fence, dashboards). Do NOT stop AutoPilot for an API-only reload; DO SIGSTOP any eval runner (P3).
uv run python scripts/server/orchestrator_stack.py reload orchestrator
```

**Verify Step 3** (checklist):
- [ ] `curl -s localhost:8087/health` OK; `tr '\0' ' ' < /proc/$(pgrep -f 'llama-server.*8087')/cmdline` shows the **production HIP binary path**, MiniCPM model + mmproj, `--device ROCm0 --reasoning off -np 1 -c 8192 -t 24`.
- [ ] `rocm-smi` shows the 8087 process resident, VRAM ≈ **11%** (K35.11 measured band for MiniCPM-o Q4).
- [ ] `orchestrator_stack.py status` lists `MiniCPM-o-4.5 Q4_K_M (vision escalation on MI210)`; every OTHER port shows `preserved`/healthy (no restarts — compare llama PIDs before/after for 8070/8072/8083/8085/8086 + quarters).
- [ ] Runtime-facts manifest realized mode still `both`; `curl localhost:8000/health` probe groups green.

---

## Step 4 — §H contention-matrix recert (the step the 2026-07-17 rebind SKIPPED)

`v7-promotion.md:38` records the failure this step exists to prevent: the 2026-07-17 `vision_escalation` rebind shipped **without re-certifying the contention matrix**, silently degrading EvalTower fanout and cross-role concurrency — and the topology hash will **not** save you here, because it is a function of `(cpu_list, port, threads)` only, all three of which are unchanged by this model swap. The matrix content (measured co-run ratios with the CPU lane now mostly idle while decode runs on MI210) *does* change. Current baseline to compare against: commit `cd42def3` (2026-07-23, 15 pairs, all `allow` 1.29–1.92, includes `vision_escalation` pairs at cpuset `72-95,168-191`/24t — `orchestration/contention_matrix.yaml:41-83`).

```bash
cd /mnt/raid0/llm/epyc-orchestrator
# Re-bench at minimum every pair containing the changed lane (inference — inside the operator window):
uv run python scripts/server/contention_matrix.py --roles vision_escalation worker_vision frontdoor worker_general architect_general ingest_long_context
# Validate + freshness-gate the committed artifact:
uv run python scripts/server/contention_matrix.py --validate-only
uv run python scripts/validate/check_contention_matrix_fresh.py
```

**Verify Step 4**: new `measured_at`/binary commit metadata in `orchestration/contention_matrix.yaml`; no pair containing `vision_escalation` below the catastrophic floor (0.65); freshness check exit 0. Record the refreshed pairs in the promotion commit message (precedent: `cd42def3`).

---

## Step 5 — Live-affinity + realized-first attestation

What applies vs a CPU lane: `affinity_preflight.py` certifies only the **host-side 24t quarter** (thread-union affinity of the 8087 process == cpuset `72-95,168-191`); GPU residency is **outside its scope** and is attested via rocm-smi/KFD instead. Cell-manifest mode (`6a55aeed`, ports 19000-19999) is for E5 bench cells — **not used here**; the role-keyed mode covers 8087 because `vision_escalation` is in `NUMA_CONFIG`.

```bash
cd /mnt/raid0/llm/epyc-orchestrator
# 5a. Live affinity (hard gate — live pinning, not just topology hash):
python3 scripts/server/affinity_preflight.py --roles vision_escalation
# 5b. GPU-side residency attestation (replaces affinity for the device half):
rocm-smi --showmemuse --showpids     # 8087 PID present, VRAM ~11%, no foreign compute PIDs
# 5c. Full read-only running-state attestation (v7-promotion final-attestation pattern):
uv run python scripts/attest/generate_attestation.py    # -> orchestration/attestation/latest.{md,json}
```

**Verify Step 5**: preflight artifact `data/contention_matrix/affinity_preflight_<ts>.json` has `live_affinity_verified: true`; attestation clean on feature flags/ports/model+runtime drift (gitnexus-stale warnings tolerated, precedent `v7-promotion.md` 2026-07-20 row); `/proc/<api-pid>/environ` has `ORCHESTRATOR_STACK_NUMA_MODE` matching the realized fleet.

---

## Step 6 — Smoke via the eval path (image + text) + modality fence

Three layers, all with **`message.content` scoring** (never `reasoning_content` — default reasoning mode scored 0/4 on these exact fixtures; that is why `--reasoning off` is load-bearing):

**6a. Direct 8087 fixture probe** — replicate `k35-vision-escalation-live-smoke-20260718T1225Z` (4/4, ~120 t/s): POST each K35 fixed fixture to `http://localhost:8087/v1/chat/completions` as `image_url` (base64 data URI) + text, score `all_substrings`:

| fixture_id | image | prompt | expected |
|---|---|---|---|
| ocr_digit_7500 | `epyc-orchestrator/benchmarks/images/vl/ocrbench/ocr_0237.png` | "What number is shown in the image? Answer with digits only." | `7500` |
| receipt_total_payable | `…/ocr_0713.png` | "What is the total payable amount on the receipt? Answer with the amount only." | `43.36` |
| chart_tanzania | `…/ocr_0619.png` | "Which country has 7 years of compulsory education in the chart? Answer with the country name only." | `tanzania` |
| receipt_doc_number | `…/ocr_0734.png` | "What is the Doc No. on the receipt? Answer with the document number only." | `cs00012465` |

Pass = **4/4** and decode t/s in the candidate's band (MiniCPM-o MI210: **110–127 t/s**; if outside band, stop and diagnose before proceeding).

**6b. Eval-path probe** — the pattern is the 2026-07-23 **vl truth slice**: 20 vl questions through the *real* eval path (EvalTower batch label `vl-truth-slice`, API `:8000`) scored **20/20, 0 errors** — artifact `epyc-orchestrator/orchestration/reports/vl_truth_slice_20260723/question_results.vl-truth-slice.jsonl`. Re-run that slice pattern with the route **forced to `vision_escalation`** (escalation is `auto_wired: false` — organic traffic will not exercise 8087; the EvalTower window runners expose per-arm role forcing via `--roles`, `scripts/benchmark/eval_batch_serving_evaltower_window.py:1791-1794`, with the standard `--apply --confirm-clean-window` gating). Pass = every row `route: vision_escalation`, `correct: true`, zero error rows.

**6c. Modality fence check** (both directions, commit `bb3a9ebb`):
```bash
cd /mnt/raid0/llm/epyc-orchestrator
# vision_escalation still classified vision-only from the REGENERATED priors (launch mode == "vision"):
.venv/bin/python -c "from pathlib import Path; from src.api.routes.vision_serving import vision_roles; print(vision_roles(Path('orchestration/derived/stack_priors.yaml')))"
# expect: frozenset({'worker_vision','vision_escalation'})
```
Then one text-only `/chat` request that a router might mis-aim: verify the fence strips vision-only roles (log line `Modality fence: …`, `src/api/routes/chat_pipeline/routing_decision.py:56-80`) and the answer comes from a text lane; and confirm the REL-1 behavior stands — any vision failure becomes an **excluded error row**, never a scored blind answer.

---

## Step 7 — Rollback (= this same runbook run toward State A)

Rollback is not a special path; it is Steps 1–6 with the safe-alias registry state, executable at any point after Step 1:

1. **Registry**: `git revert` the Step-1 master-registry commit in `epyc-inference-research` (restoring the exact Qwen2.5-VL block currently at master lines 4072–4138: `path: lmstudio-community/Qwen2.5-VL-7B-Instruct-GGUF/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf`, `mmproj-model-f16.gguf`, no `device`/`runtime_requirements` keys under `server:` — i.e. CPU canonical binary) and the orchestrator commit (restoring `stack_manifest.py:297-302` to `VISION_ESCALATION_MODEL = VISION_WORKER_MODEL`, `…MMPROJ = VISION_WORKER_MMPROJ`, `DEVICE = "none"`, and the `orchestrator_stack.py:1279` alias label). This is byte-for-byte the `91cf4033`+`dacd15a2` shape.
2. Re-run 1c (lean recompile), Step 2 (both pipeline commands green), Step 3 (`stop vision_escalation`; `start --only vision_escalation --numa-mode both`), Step 4 (recert — a rollback is also a lane change), Step 5, and Step 6a with the **alias** reference band (Qwen2.5-VL on this fixture set: 4/4; on-CPU alias historical band 16.9–21.3 t/s per master `performance`, MI210-era comparison 133.29/118.50 t/s — expect the CPU band, since State A serves `--device none`).
3. **Rollback triggers** (any ⇒ roll back rather than debug live): Step 3 health/cmdline mismatch; Step 6a < 4/4 or > 20% below throughput band; Step 6b any error row attributable to 8087; VRAM/KFD anomalies; any Step 4 pair < 0.65.

---

## NOT covered by this runbook (explicit)

- **Model choice.** Operator decision (07-18 MiniCPM-o validation vs 07-19 alias-faster long-decode slice); the runbook is model-agnostic mechanics.
- **Audio / TTS / omni modalities** of MiniCPM-o — vision projector only is wired; audio/tts/token2wav GGUFs remain catalogue-only (master `minicpm_o_45_local_multimodal.projectors`).
- **Escalation auto-wiring** — `escalation.auto_wired: false` stays false; routing to 8087 remains explicit/manual (routing_hints math-in-image/video rows exist but the chain is not auto-triggered).
- **Orchestrator-side vision capacity scheduling** beyond the server-side `-np 1` cap (K35.13's "one active vision request while frontdoor is resident" is enforced only by the single slot).
- **Frontdoor-on-MI210 co-residency** — the restored lineup serves frontdoor on CPU; the 66%-VRAM co-residency + service-tax evidence applies only if an MI210 frontdoor lane returns.
- **Persistent AutoPilot traffic soak** — the 07-18 flip explicitly noted persistent API/AutoPilot traffic was never observed; this runbook's Step 6 is a smoke, not a soak. Schedule a post-promotion observation window.
- **The operator's external MI210 process (port 18072)** — operator-owned; this runbook never touches it.
- **MEASUREMENT trust-boundary artifacts** (instrument eras, eval tower, scoring, safety gates) — human-amendment-only; nothing here edits them.
- **worker_vision (8086)** — untouched in both directions.
- **WP-12 fleet-layer restructuring / future `-v9` kernel work / core_v2 item composition** — out of scope; note only that `vision_escalation` has no `server_mode` row, so the fleet layer's registry-SoT fleet build does not bind it (manifest-role binding verified in priors).

**Reporting**: on execution, flip the runbook checkbox in `handoffs/active/multimodal-pipeline.md:490`, append the promotion (or rollback) to `progress/YYYY-MM/…`, and record the Step-4 matrix refresh + Step-5/6 artifact paths in the promotion commit messages (one commit per repo: research = master registry; orchestrator = constants + regenerated lean/descriptors/priors/summary/matrix).
