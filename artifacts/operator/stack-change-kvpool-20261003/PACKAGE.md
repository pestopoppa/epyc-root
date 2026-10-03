# STACKCHG-KVPOOL-20261003: :8083 unified KV pool 196608 → 393216, per-request cap 262144, DFlash2 n-max 8 → 7

**Status: PREPARED (phases 0–5). The operator signs next (phase 6).**
Nothing was applied to a real tree. No commit, push or branch switch was made. No process was started, stopped or reloaded. No inference was sent: the only HTTP calls were read-only `GET /props` on :8083. Everything below lives in `/mnt/raid0/llm/tmp/stack-change-kvpool-20261003/`.

**Signing token:** `RATIFY-STACKCHG-KVPOOL-20261003`. Signing script: `ratify_stackchg_kvpool_20261003.sh`. It is TTY-gated and the **operator runs it** (§9).

**Three findings changed the package during preparation.** Each is fixed in the patch and covered by a test.
1. **The v10 server already caps every request at 262144.** `server-context.cpp:1316-1322` sets `n_ctx_slot = min(n_ctx_seq, n_ctx_train)`, logs a WARN, and `/props` then reports 262144.
   - DECISION.md said the server "would only warn" above n_ctx_train. So did the step-1 commit 2586a7bb, which landed during preparation. Both are wrong.
   - Consequence: the cap reaches **every** client, including the direct ones that bypass the orchestrator.
2. **With that server cap, step 1's context limits would have disarmed pool admission on :8083 after the relaunch.**
   - `parse_props` reads a server as unified only when `n_ctx >= -c`. After the relaunch that is 262144 ≥ 393216, which is false, so :8083 would be read as **split**.
   - Effects: `shared_pool` turns False, so both `SharedKVPoolAdmission` and the scout token gate turn **off**. `pool_tokens` would report 1,048,576.
   - Step 1's own test assumed `/props` reports 393216. That assumption is now kept as the "non-clamping build" case.
3. **One `stack_change_pipeline.py update` writes stale priors for this change.** The pipeline imports `stack_manifest` before it rewrites the lean, so `effective_context_tokens` is compiled from the old lean.
   - Reproduced in `evidence/pipeline-stale-priors-repro.txt`: `update` reported green and wrote 196608; the next `check` failed with "stack-prior artifact is stale" plus 9 guard errors.
   - Phase 7 would have hit this.

## 0. Intent (phase 0: `intent.yaml`)

The operator approved this on 2026-10-03 ("yes"). It is option (a) at 393216 from `/mnt/raid0/llm/tmp/kv-sizing-8083-20261003/DECISION.md`.
- :8083 (Qwen3.8-27B-Q8_0, MI210; host `architect_critic`; aliases `coder_escalation` and `ingest_long_context`; drafter DFlash2 chosen by `drafter_selection`):
  - `-c` 196608 → **393216**;
  - np 4, `--kv-unified` and q8_0 K/V are unchanged.
- The per-request cap is **262144**, which is n_ctx_train. It was re-read from the GGUF header for this package (`qwen35.context_length = 262144`).
- `roles.qwen38_27b_q8_local.drafters.dflash2.draft_max` 8 → **7**. This is the DRAFT-SEL-1 entry. The canonical recipe JSON keeps 8 (see §1).
- `serving_shape.vram_non_kv_gib` and the capacity leg are re-derived (§4).

Bases:
- Orchestrator `main@2586a7bb`. It moved during preparation, 5265e09d → 4e23e553 → 2586a7bb. The patch was rebuilt on 2586a7bb and re-verified there.
- Research `main@be2cc414`, which equals origin/main.
- Phase-1 scratch: `scratch/PROVENANCE.json`. The research working tree is dirty, but not in `orchestration/`. The master is byte-identical at HEAD and in the working tree.

## 1. The patch set (ONE per repo), verified to apply on the current HEADs

| repo | file | content |
|---|---|---|
| research | `patches/research/stackchg-kvpool-20261003.research.patch` | master registry |
| orchestrator | `patches/orchestrator/stackchg-kvpool-20261003.orchestrator.patch` | 7 files |

Sizes and sha256 values are in the ratify script's PINS. **Proof of apply** is in `evidence/apply-proof.txt`:
- Both patches pass `git apply --check` on the REAL working trees (read-only).
- `sandbox-pristine/` was built as `git archive HEAD` plus `git apply` of both patches. It is byte-identical to the edited sandbox.
- Everything in §3–§5 was run on that tree (`tools/verify.sh`).

**Research master (`orchestration/model_registry.yaml`):**
- `server_mode.architect_critic.serving_shape.n_ctx: 393216`, carrying the marker **UNVALIDATED** (it has never been served at this size). The comment records:
  - the 17-episode evidence;
  - the server-side cap;
  - that two concurrent full-262144 requests do **not** fit (A-1).
- `serving_shape.vram_non_kv_gib` 37.92 → **39.15**, DERIVED and UNVALIDATED. The full derivation is in the comment and in §4. `vram_non_kv_drafter: dflash2` is unchanged, so the DRAFT-SEL-1 compile check still holds.
- `roles.qwen38_27b_q8_local.drafters.dflash2.draft_max` 8 → **7**, with a source-cited note:
  - The block yields at most block_size−1 = 7 draft tokens, and v10 already clamps 8 to 7.
  - The GDN ring is sized from the *unclamped* value (`need_n_rs_seq()` = `draft.n_max`).
  - n_rollback ≤ 7 = n_rs_seq, so the checkpoint fallback stays off.
  - The canonical recipe `qwen3.8-27b-q8-gpu-dflash2-np4.json` is **left at 8** on purpose. It is the AutoKernel measurement identity (ctx 16384, f16, split), serving-floor identity tests pin it, and at block_size 8 it drafts the same 7.
- Prose that would otherwise state a false deployed pool:
  - the `ingest_long_context` shape comment and `alias_note`;
  - `roles.ingest_long_context.model.ctx_max`, now marked load-bearing as the cap;
  - one-line notes on the `coder_escalation` and `architect_critic` `ctx_max` entries.

**Orchestrator:**
- `src/backends/context_limits.py`, built on step 1's `request_cap`, `server_n_ctx` and `cap_binding`:
  - The unified/split inference now compares the live n_ctx with the **midpoint of the two capped expectations**: `min(-c, cap)` against `min(-c/np, cap)`.
  - A new `pool_n_ctx` carries the declared `-c` when a unified server has clamped its slots, so `pool_tokens` is 393216 rather than 262144.
  - `observe()` keeps or drops that clamped pool consistently.
  - The module docstring is corrected: the server clamps, it does not only warn.
- `scripts/registry/stack_change_pipeline.py`: when `update` changed the lean that `stack_manifest` reads, `_lean_registry_step` evicts `scripts.server.stack_manifest` from `sys.modules`. Later steps then re-import it against the new lean, and its import-time gates run for real.
  - Measured: with the fix, one `update` followed by `check` is green, apart from the 2 expected drift lines.
- `stack_templates/default.yaml`: deleted `architect_critic.full.spec_overrides {draft_max: 4, p_split: 0}`. It was a third, stale copy of this server's draft depth.
  - Nothing launches from the template today.
  - The day DS-7 phase 2 lands, it would have rewritten DFlash2's n-max to 4.
- Tests:
  - New: `tests/unit/test_context_limits_model_cap.py` (18). It covers the clamped server, the regression arithmetic, split, the not-yet-reloaded server, the non-clamping build, frontdoor and single-slot no-ops, the registry path, the resolver, `observe`, this tree's compiled priors, and a frozen-source re-derivation of the server cap.
  - New cases in `test_stack_change_pipeline.py` (2): the eviction scope, and evicting only when the lean changed.
  - `test_stack_templates_v2.py::test_hot_vs_loaded_breakdown`: **failing on HEAD since d3233170**, because it asserted "all-HOT" but worker_vision is now WARM. It is now recomputed from the template, at the same strength.
  - `test_kv_pool_long_prefill.py::test_the_cap_comes_from_the_compiled_stack_priors` (step 1): it pinned the literal `context_tokens == 196608`, which this change moves. It now recomputes the expected value from the lean's `server_mode.architect_critic.serving_shape.n_ctx`. Nothing is loosened.
- **Derived files are NOT in the patch.** Phase 7 `update` regenerates them. `evidence/derived-delta.GENERATED.diff` is for review only.
  - Only the three :8083 roles change, in `n_ctx`/`context_tokens`/`effective_context_tokens`, `draft_max`/`k`, and `vram_non_kv_gib`, plus provenance stamps.

**Surfaces not touched, and why:**
- `stack_topology.yaml`: placement, port, drafter selection and NUMA are unchanged.
- `launch_manifest.yaml`: no port or tier change.
- `stack_numa.py`: no shape change.
- `src/config/models.py` and `src/roles.py`: no alias change.
- Kernel store: unchanged (v10 ffc1bac82).
- The contention matrix: placement is unchanged, so `topology_hash` is unchanged and no recert is needed.

## 2. Rendered :8083 argv (compiled from the patched tree; `evidence/argv_8083-pristine.txt`)

```
/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
  --host 127.0.0.1 --port 8083 -np 4 -c 393216 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified
  --no-mmap -ngl all --cache-ram 65536 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja
  -md /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 7
  --device ROCm0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_critic --device-draft ROCm0
```

- The unpatched render (`evidence/argv_8083-base.txt`) is **byte-identical** to the live PID 3793153 cmdline (`evidence/live-state.txt`).
- The patched render differs in exactly two tokens: `-c 196608` → `-c 393216` and `--spec-draft-n-max 8` → `7`.

## 3. Preflight report (phase 3; `evidence/preflight-classified.txt`, `evidence/pipeline-check-pristine.txt`)

`check` on the pristine tree:
- **Every** compile and guard step is `ok`: numa_mode, shared_with_derivations, lean_registry, descriptors, stack_priors, procedure_enums, operator_summary, guard, guard_strict, reasoning_effort_certifications, serving_shape_capacity, stack_manifest_registry, q_scorer_priors and declared_env_attestation.
- `guard_all_surfaces`: 13 warnings, identical to the baseline.
- `runtime_attestation`: 2 errors.

The baseline (unpatched HEAD against the same live fleet) is fully green: "acceptance: no-inference checks passed" (`evidence/pipeline-check-base.txt`).

| # | line(s) | class | disposition |
|---|---|---|---|
| 1–2 | `live process drift: architect_critic pid 3793153 runtime context_tokens expected 393216; live cmdline has 196608` and `… spec.draft_max expected 7; live cmdline has 8` | expected pre-relaunch drift | They are the change itself. They clear at `reload architect_critic` (§7.2); `check --run-promotion-gate` must then be green. |
| 3–15 | 13 `hardcoded_surface` warnings (retired-role strings in tests and docs) | pre-existing | Byte-identical in the baseline; not this change. |
| — | fixable-by-transform | **0** | — |
| — | needs-measurement (pipeline) | **0** | — |

The skill classifier exits 5, "operator decision", only because it puts unmatched lines into needs-operator. Under the skill's definitions none of the 15 lines is an operator decision. The real needs-operator items are in §8.

Sub-skill checks:
- `change-topology/capacity.sh` (local venv copy, `evidence/capacity_sh.txt`): **CAPACITY PASS**.
- `change-topology/topology_check.py --intent intent.yaml`: **FAIL on base and candidate alike**, on `worker_vision device='none'`. That is the DFLASH2 package's root patch, which **was never applied**: it still `git apply --check`s on /workspace.
  - With that patch applied to a scratch copy of the checker, both base and candidate **PASS** (`evidence/topology_check_rootpatched.txt`).
  - This is not this change. The owner of the DFLASH2 wrap-up should land `stackchg-dflash2-20261003.root.patch`.
- `retire-model` and `change-role`: not invoked; nothing is retired and no role moves.

Not visible to the pipeline but required by the skill (**needs-measurement**, all queued post-bring-up, none blocks apply):
- **M-1:** the load-time KFD peak at `-c 393216`, sampled DURING the load. Replace 39.15 with the measured figure.
- **M-2:** the concurrency proof: 4 × ~90k concurrent, zero memory-slot failures (`tools/concurrency_probe.py`, §7.3 item 8).
- **M-3:** decode speed against pool fill, to decide unified vs split. DECISION.md §4 step 1 does this with zero compute, by regression on the existing log.
- **Belief kernel (CLAUDE.md):** M-1 and M-2 are new measurement sources (VRAM components per -c and draft depth; pool-concurrency verdicts). The owning session adds an adapter row and a task when they are produced.

## 4. Capacity report: both legs, per instance (`evidence/capacity-pristine.txt`, `evidence/capacity_sh.txt`)

| role | port | shape class | leg | n_ctx | KV GiB | non-KV GiB | slots |
|---|---|---|---|---|---|---|---|
| architect_critic | 8083 | gpu_host_lane | **GPU** | **393216** (was 196608) | **12.75** (was 6.38) | **39.15** (was 37.92) | 4 |
| architect_general | 8074 | full | host | 262144 | 24.00 | — | 1 |
| frontdoor | 8070 / 8080 / 8180 | full / half / half | host | 262144 | 2.66 each | — | 4 / 1 / 1 |
| worker_vision (cold, WARM) | 8086 | half | host | 65536 | 3.19 | (19.26 kept, unused) | 1 |

| leg | baseline (HEAD) | candidate | verdict |
|---|---|---|---|
| **GPU ROCm0** | 44.30 / 62.00 GiB | **51.90 / 62.00 GiB** | PASS, **10.10 GiB** slack under the gate (2.0 GiB headroom on a 64 GiB nominal). Physically 63.98 − 51.90 = 12.08 GiB free. |
| **host RAM** | 254.46 / 1069.42 GiB | 254.46 / 1069.42 GiB | PASS, unchanged |

**The VRAM derivation for 39.15 GiB.** [M] = measured; [D] = derived.

| term | GiB | source |
|---|---|---|
| live KFD, PID 3793153 (stack-launched at 196608, d8), runtime | 44.61 | [M] 47,899,860,992 B at 05:18:12Z and 05:18:17Z. Earlier pair: 47,716,892,672 B at 05:01:32Z and 05:02:41Z. It is still ratcheting under traffic, so the larger pair is used. |
| − attention KV @196608 (34,816 B/token q8_0) | −6.375 | [M] log :35256 |
| = non-KV at 196608 | 38.24 | |
| + KQ mask, 196,608 more cells × 4,096 B (f16 × ub 2048) | +0.75 | [D] measured slope (np2 split vs np4 kvu, target compute 1472.33 → 1856.33 MiB) |
| + FA F16 conversion scratch for q8_0 K+V, 196,608 × 4,096 B | +0.75 | [D] source `fattn.cu:619-627` and `ggml-cuda.cu:917-918`; slope confirmed below |
| − GDN rollback ring n_rs_seq 8 → 7, 4 × 149.625 MiB | −0.58 | [D] RS buffer = np × (1 + n_rs_seq) × 149.625 MiB, log :21631 and :35260 |
| **= vram_non_kv_gib** | **39.15** | |
| + attention KV @393216 | +12.75 | |
| **= process at 393216** | **51.90** | conservative bound if the drafter also carried a -c-sized mask: 52.65 |

- **Correction to DECISION.md §1.2:** the marginal cost of one pool token on this process is **43,008 B (42.0 KiB)**, not 38,912 B. DECISION's two-launch slope compares split and unified at the same `-c`, so it cannot see the FA conversion scratch, which is sized by total cells in both.
- The full-slope proof is measured: `np_context_kvu_study_20260924/q38_27b_q8_loadonly`, np4 kvu, -c 196608 → 262144, 40,522 → 43,858 MiB.
  - That is **53,376 B/token**: target KV 34,816 + mask 4,096 + FA scratch 4,096, plus MTP-draft KV 2,176 + draft mask 4,096 + draft FA scratch 4,096. The sum is exact.
  - The DFlash2 drafter has a 4096-cell SWA cache and 0 non-SWA layers (`tmp/mmvq-probe3.log:6409-6425`), so only the three target terms scale.
- DECISION's own projection for 393216 at d8 was 51.42 GiB. This package's figure is 51.90 at d7: +0.75 from the FA scratch, +0.31 from the later live reading, −0.58 from d7.

## 5. Tests (phase 3)

Run serially, no xdist, on the pristine tree and on HEAD. Results: `evidence/tests.txt` (candidate) and `evidence/tests-baseline.txt` (HEAD).

| set | baseline (HEAD 2586a7bb) | candidate |
|---|---|---|
| promotion-gate targets (= `PROMOTION_GATE_TARGETS`: simulated_fixtures, build_server_command_helpers, 4× seeding) | 202 passed | **202 passed** |
| related: pipeline, compiler, priors, validator, orchestrator_stack ×4, stack_manifest, guard, template parity + templates_v2, descriptors, stack_numa ×3, drafter selection + external drafter launch, context overflow, **kv_pool_long_prefill (step 1)**, scouts, admission, compaction, openai_compat ×2, topology aliases | 828 passed, **1 failed** (`test_hot_vs_loaded_breakdown`, pre-existing since d3233170) | **831 passed, 0 failed** (the pre-existing failure fixed; the step-1 literal re-pinned by recomputation) |
| new: `test_context_limits_model_cap.py` | n/a | **18 passed** |

**Blast radius** (`evidence/gitnexus_impact.txt`). The orchestrator gitnexus index is STALE: it was built from `/workspace/repos` and is 841 commits behind, and `context_limits` and `_lean_registry_step` are not in it. It was not re-indexed, because analyze writes into the real tree.
- gitnexus: `run_stack_change_pipeline` is LOW (2: `main` plus unit tests); `observe` resolves to an unrelated symbol.
- Structural consumers of the changed `ContextLimit` semantics (git grep), all exercised by the related set:
  - `inference.py` (max_tokens clamp, cap refusal, pool admission gate);
  - `scout_stage.py` (scout token gate, `shared_pool`);
  - `kv_pool_admission.py` (`pool_tokens`);
  - `routing_decision.py`, `context_recovery.py`, `compaction.py`, `openai_compat.py` (`limit_for_role`, `per_request_n_ctx`).
- Every non-:8083 server is unchanged by construction. Its cap is ≥ its slot context, so the midpoint rule gives the old verdict (tests: frontdoor split 65536, single-slot no-op, the no-cap baseline).

## 6. Effect on the API (what the reload changes)

| `/props` reading | per-request | unified | shared_pool | pool_tokens | pool admission |
|---|---|---|---|---|---|
| live today (196608, d8) | 196608 | yes | yes | 196608 | armed |
| after reload, HEAD code (step 1 only) | 262144 | **no** | **no** | **1,048,576** | **OFF** (and the scout gate) |
| after reload, this patch | 262144 | yes | yes | **393216** | armed |
| API reloaded before :8083 (196608 live, priors 393216) | 196608 | yes | yes | 196608 | armed (the "not-yet-reloaded" test) |

## 7. Phase 7 (apply) and phase 8 (bring-up)

**Run only after the receipt exists.** The owner is the session that owns :8083 inference, and it performs every reload at its own boundary. Never run `start --dry-run`. Do not stop autopilot; the API reload is API-only.

### 7.1 Apply (phase 7)

```bash
P=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
test -f /workspace/artifacts/operator/receipts/RATIFY-STACKCHG-KVPOOL-20261003.json || { echo "NOT SIGNED"; exit 1; }
bash $P/ratify_stackchg_kvpool_20261003.sh --validate-only        # re-verifies pins + applicability

# research
cd /mnt/raid0/llm/epyc-inference-research && git fetch origin && git merge --ff-only origin/main
git apply --check $P/patches/research/stackchg-kvpool-20261003.research.patch
git apply         $P/patches/research/stackchg-kvpool-20261003.research.patch
git commit -m "registry(STACKCHG-KVPOOL-20261003): :8083 -c 393216 (cap 262144 = n_ctx_train); DFlash2 draft_max 7; vram_non_kv_gib 39.15 derived" -- orchestration/model_registry.yaml
RES_C1=$(git rev-parse HEAD)

# orchestrator
cd /mnt/raid0/llm/epyc-orchestrator && git fetch origin && git merge --ff-only origin/main
git apply --check $P/patches/orchestrator/stackchg-kvpool-20261003.orchestrator.patch
git apply         $P/patches/orchestrator/stackchg-kvpool-20261003.orchestrator.patch
git add tests/unit/test_context_limits_model_cap.py
git commit -m "stack(STACKCHG-KVPOOL-20261003): context limits read a server-clamped unified pool; pipeline update re-imports stack_manifest after the lean; drop stale template spec_overrides" -- \
  src/backends/context_limits.py scripts/registry/stack_change_pipeline.py stack_templates/default.yaml \
  tests/unit/test_context_limits_model_cap.py tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_templates_v2.py \
  tests/unit/test_kv_pool_long_prefill.py
ORCH_C1=$(git rev-parse HEAD)

uv run python scripts/registry/stack_change_pipeline.py update; echo "update rc=$?"
#   EXPECT rc=1 with ONLY the 2 :8083 runtime_attestation drift lines (§3) and
#   "lean changed: evicted scripts.server.stack_manifest" in the lean_registry details.
uv run python scripts/registry/stack_change_pipeline.py check;  echo "check rc=$?"   # same 2 lines, nothing else
uv run python -c "import scripts.server.stack_manifest"                               # import-time gates: must be silent
uv run pytest -q tests/unit/test_context_limits_model_cap.py tests/unit/test_stack_change_pipeline_simulated_fixtures.py \
  tests/unit/test_build_server_command_helpers.py tests/unit/test_seeding_infra.py tests/unit/test_seeding_infra_additional.py \
  tests/unit/test_seeding_infra_branching.py tests/unit/test_seed_specialist_routing_main_and_retry.py; echo "pytest rc=$?"   # capture rc; do not pipe
git commit -m "derived(STACKCHG-KVPOOL-20261003): regenerate lean, descriptors, stack_priors, summary" -- \
  orchestration/model_registry.yaml orchestration/model_descriptors.yaml orchestration/derived/stack_priors.yaml \
  docs/generated/current_stack_summary.md orchestration/procedures orchestration/procedure.schema.json
ORCH_C2=$(git rev-parse HEAD)
```

Push each repo with its push lock (`coordination/push-locks`) and pathspec-limited commits. Copy this package directory into `/workspace/artifacts/operator/stack-change-kvpool-20261003/` in the root wrap-up commit.

### 7.2 Bring-up (phase 8): `reload architect_critic`, then `reload orchestrator`

```bash
cd /mnt/raid0/llm/epyc-orchestrator
P=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
# (a) VRAM sampler armed BEFORE the reload (observation window); capture its PID yourself
( while :; do echo "$(date -u +%T.%N) $(cat /sys/class/drm/card2/device/mem_info_vram_used)"; sleep 0.5; done ) \
    > $P/evidence/vram_during_reload.log 2>&1 & SAMPLER=$!
# (b) relaunch ONLY the :8083 llama-server (aliases ride it; do not stop autopilot)
uv run python scripts/server/orchestrator_stack.py reload architect_critic
# (c) API-only reload: the per-request cap and the pool reading live in the API process
uv run python scripts/server/orchestrator_stack.py reload orchestrator
kill $SAMPLER; ps -p $SAMPLER || echo "sampler stopped"
```

### 7.3 Serving-proof checklist (all must hold; `healthy` is not proof)

1. **New process:** `PID=$(ss -ltnp 'sport = :8083' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)`. It must not be 3793153. Check `ps -o lstart= -p $PID`.
2. **argv:** `tr '\0' ' ' < /proc/$PID/cmdline` equals §2 byte-for-byte. It must contain `-c 393216` and `--spec-draft-n-max 7`.
3. **Binary and store:**
   - `readlink /proc/$PID/exe` gives `/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server`.
   - `bash /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh` passes.
   - Threads are on 184-191: `grep Cpus_allowed_list /proc/$PID/task/*/status`.
4. **Load log** (`logs/llama-server-8083.log`, last block) shows:
   - `n_slots = 4, n_ctx_slot = 262144, kv_unified = 'true'`;
   - `the slot context (393216) exceeds the training context of the model (262144) - capping`;
   - `block_size=8 … n_extract=5`;
   - **NO** `clamping to 7` WARN (n-max is now 7);
   - no `failed to load draft model`.
5. **`/props` and `/slots`:**
   - `curl -s localhost:8083/props` gives `total_slots 4` and `default_generation_settings.n_ctx 262144`.
   - `/slots` lists 4 slots with n_ctx 262144 and speculative type draft-dflash.
6. **API reading** (the fix in §6). Run this from the orchestrator root; it is a read-only `GET /props` plus the compiled priors:
   `uv run python -c "from src.backends.context_limits import get_context_limit_resolver as g; print(g().limit_for_url('http://localhost:8083').to_dict())"`
   It must show:
   - `per_request_n_ctx 262144`, `kv_unified True`, `shared_pool True`, `pool_tokens 393216`.
7. **Load-time VRAM peak (M-1):**
   - The peak of `evidence/vram_during_reload.log`, sampled DURING the load, must stay ≤ 62 GiB. Expect about 51.4–52.7 GiB. Card total is 63.98 GiB, and whisper and TTS hold 0.
   - After load, KFD `/sys/class/kfd/kfd/proc/$PID/vram_*` is about 51 GiB.
   - Record peak − 12.75 as the measured `vram_non_kv_gib` and replace 39.15 in a follow-up.
8. **Concurrency (M-2), at the owner's chosen window:** `/usr/bin/python3 $P/tools/concurrency_probe.py --i-own-the-window`.
   - It sends 4 distinct ~90,000-token prompts **directly to :8083**, concurrently, with `cache_prompt false` and `n_predict 64`.
   - It goes direct on purpose: step 1's one-long-prefill rule would serialize them through the orchestrator, and the 393216 pool is what is under test.
   - **PASS** requires all of: 4 × HTTP 200; **zero** `failed to find a memory slot` and zero `Context size has been exceeded` after the start offset; `/slots` saw ≥ 3 slots processing with ≥ 300,000 cells in flight; KFD peak ≤ 62 GiB.
   - Results go to `evidence/concurrency-probe-<ts>.json`.
9. **Real completion** through an alias, with a generous budget (thinking bills the same budget):
   `curl -s localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"coder_escalation","messages":[{"role":"user","content":"Write a Python function that returns the n-th Fibonacci number iteratively, then explain it in two sentences."}],"max_tokens":4096}'`
   The content must be non-empty and correct. The server log must show `draft acceptance` for it.
10. **Attestation:** `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` reports `runtime_attestation: ok` and `promotion_gate: ok`, and acceptance passed.

## 8. What the operator signs (phase 6): needs-operator items and acknowledgements

**needs-operator, resolved by signing** (the receipt's `acknowledged` block lists each item):
- **A-1, the approval's rationale is arithmetically wrong.** "Each request may use the full 262k while two such requests still fit" does not hold: 2 × 262144 = 524288 > 393216.
  - What 393216 holds: ONE 262144 request plus 131072 of others, or 4 × 98304. Orchestrated overflow queues; a direct client can still exhaust the pool.
  - Options:
    - (i) **sign 393216 as approved. Recommended.** It is DECISION's sizing, covering four concurrent p90 prompts, 10.10 GiB gate slack, and the smaller decode-scan exposure.
    - (ii) refresh to `-c 524288`. That is about 57.2 GiB derived, 4.85 GiB gate slack, 6.8 GiB physically free, and the largest scan penalty.
  - Signing this package means (i).
- **A-2, the cap is server-enforced.** It applies to every client. Step 1's orchestrator-side cap is kept and corrected (findings 1 and 2).
- **A-3, 39.15 GiB is DERIVED and UNVALIDATED at 393216.** M-1 and M-2 are owed at bring-up, in the owner's window. Gate slack is 10.10 GiB even at the conservative 52.65.
- **A-4, decode on a unified pool scales with pool fill** ([D], DECISION §2). A fuller 393216 pool can slow every slot. It is unmeasured (M-3).
- **A-5, n-max 7 is drafting-identical.** The canonical recipe keeps 8.
- **A-6, orchestrator code changes:** context-limits fix, pipeline eviction fix, template block deleted, one stale test repaired.
- **A-7, bring-up order and ownership:** `reload architect_critic` then `reload orchestrator`, run by the :8083 inference owner at its own boundary. The window is the owner's choice.

**Signature mechanism:**
- A TTY-gated ratify script, `ratify_stackchg_kvpool_20261003.sh`, modelled on `ratify_stackchg_dflash2_20261003.sh`.
- It pins sha256 values for this file, the intent, both patches, the tools and the evidence. It re-checks `git apply --check` on the current trees.
- It writes ONE receipt to `/workspace/artifacts/operator/receipts/RATIFY-STACKCHG-KVPOOL-20261003.json`, with a copy in `receipts/` here.
- It applies nothing.

## 9. Signing command (operator, in a separate terminal; never under `!`, never chained with `&&`)

```
RATIFY_OPERATOR="<your name>" bash /mnt/raid0/llm/tmp/stack-change-kvpool-20261003/ratify_stackchg_kvpool_20261003.sh --attest RATIFY-STACKCHG-KVPOOL-20261003
```

## 10. Rollback (a `git revert` set; no symlink changes, the kernel store is untouched)

```bash
cd /mnt/raid0/llm/epyc-orchestrator && git revert --no-edit $ORCH_C2 $ORCH_C1      # derived first, then code
cd /mnt/raid0/llm/epyc-inference-research && git revert --no-edit $RES_C1
cd /mnt/raid0/llm/epyc-orchestrator && uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/registry/stack_change_pipeline.py update   # TWICE: the revert removes the eviction fix, and one update
                                                                   # writes priors from the lean it is replacing (finding 3)
uv run python -c "import scripts.server.stack_manifest"            # must import (44.30 / 62.00 GiB)
uv run python scripts/server/orchestrator_stack.py reload architect_critic   # back to -c 196608 --spec-draft-n-max 8
uv run python scripts/server/orchestrator_stack.py reload orchestrator       # step-1 context limits again
```

- The rollback argv is `evidence/argv_8083-base.txt`, which equals the live PID 3793153 argv.
- If only the API fix must go, revert `$ORCH_C1` alone and reload the orchestrator. But with :8083 at 393216 that re-disarms pool admission (§6). Roll back the pool too.

## 11. Files

- `PACKAGE.md`, `intent.yaml` and `ratify_stackchg_kvpool_20261003.sh`.
- `patches/{orchestrator,research}/*.patch`.
- `evidence/`:
  - apply proof;
  - pipeline update and check, base and pristine;
  - the stale-priors reproduction;
  - classified preflight;
  - capacity for both trees, and `capacity.sh`;
  - argv, base and pristine;
  - tests, base and candidate;
  - `topology_check`, stock and root-patched;
  - gitnexus and structural impact;
  - live state;
  - `derived-delta.GENERATED.diff` (review only).
- `tools/`: setup, build_sandbox, rebase_sandboxes, reset_derived, compile, make_patches, verify, run_tests, capacity_report, capacity_sh_local, render_argv, preflight_scratch, topology_check_patched, repro_stale_priors, impact, live_state, concurrency_probe (NOT run), and ratify_template.
- `scratch/`: the skill's `scratch.sh` output (`PROVENANCE.json`). `work/`: pre-rebase copies of the edited files.
- `sandbox-{base,new,pristine}/`: `git archive` trees. They are disposable once signed.

Observed but out of scope, not fixed here:
- The DFLASH2 root patch is unapplied (§3).
- The orchestrator gitnexus index is stale.
- `kv_pool_admission.py:25`'s 196608 example comment is illustrative only.
