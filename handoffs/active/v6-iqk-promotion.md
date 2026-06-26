# v6+iqk → production cutover (full ik_llama deprecation)

**Status:** ✅ **CUTOVER COMPLETE (autonomous bar met) 2026-06-26.** v6 in production: every hot role healthy on the v6 binary, `runtime_attestation` clean, all governance gates green, ik_llama deprecated. Worker/architect/frontdoor garbage-checked (no garble, MTP 81/93%, no M-RoPE assert), GGML_IQK=1 everywhere. Throughput observed (throttle-caveated). **Operator-pending** (human trust boundary): formal eval-parity (P-QUAL-PROMO), era-row (E5-cpu-kernel draft), clean post-reboot bench — package `/mnt/raid0/llm/tmp/v6_operator_package.md`. **N12 attempted + reverted** (not a config flip — launcher work needed; see `numa-private-weights-quarter-roles.md`).
Commits (no push, 4): orchestrator `ce789b11` (config convergence) + `897cead2` (live-cutover fixes: frontdoor roles, architect abs-path, n-max 24→4, ctx_max); research `23867f3` (master registry + canonical_recipe, on main); epyc-root `44a2a411` (verify_llama_cpp v6, handoffs, indices N13, wiki, progress). Operator: fetch+rebase before any push (research/root on main).

### Cutover verification log (Phase I/J)
- **Worker** (gemma-26B ORIG base + v6 head, draft-mtp): healthy on canonical v6 binary; `/v1/chat/completions` (gemma sampling + repeat_penalty 1.05) → correct memoized-Fibonacci + O(n); **NO garble** (raw-/completion garble was a test-method artifact — `feedback_verify_test_method_before_calling_it_a_bug`); `[iqk]`/GGML_IQK=1; MTP **81% draft-accept** (123/152), 48.8 t/s.
- **Architect** (Qwen3.5-122B NEXTN self-draft): healthy; `common_speculative_impl_draft_mtp` wired, **NO M-RoPE assertion** (the gate that put it in NO_SPEC is resolved on v6); correct relative-speed reasoning; GGML_IQK=1. Fixed two cutover bugs: ABSOLUTE model path (relative resolved to wrong `/lmstudio/models` base) + `stack_numa.py:101` n-max 24→4 (stale 0.8B-draft sweep value; NEXTN optimal=4).
- Pending: frontdoor/ingest/vision garbage-check + per-role throughput (throttle-caveated; operator post-reboot formal gate is authoritative).
**Owner:** active session `ses_20260626_120925`
**Supersedes the standing verdict** in [`llamacpp-v6-consolidation.md`](llamacpp-v6-consolidation.md) ("do NOT cut gemma worker to v6", 2026-06-25) — overturned by the iqk-port +11%-vs-ik result. Cutover-execution sibling of [`iqk-port.md`](iqk-port.md) and [`numa-private-weights-quarter-roles.md`](numa-private-weights-quarter-roles.md) (N12).

## What this is
Cut the ENTIRE production inference stack onto ONE kernel — `production-consolidated-v6` (upstream framework + native MTP/EAGLE3 + our CPU kernels + ik_llama's iqk AVX-512 GEMM kernels, `GGML_IQK`-gated) — and **retire ik_llama entirely** (today only the gemma worker runs on it). Every stack model runs at maximum optimization: iqk on, MTP on, private-quarter NUMA topology.

## Operator decisions (locked 2026-06-26)
- Production branch = **`production-consolidated-v6`** (no `-iqk` suffix); ik-kernel integration documented in prod docs.
- **Full ik_llama deprecation** — every ik dependency handled.
- **Architect = MTP** (NEXTN draft-mtp, operator-chosen; +58–89% measured). Expert-reduction is a **no-op** (experts=8=GGUF default) → dropped. ngram-lookup is OFF in prod today, fully supported in v6 — recorded as the architect's zero-RAM fallback.
- **Reboot = operator's job, separately, later** — NOT an autonomous step. Cutover doesn't need it. Pre-reboot throughput numbers are throttle-caveated/holding; the clean decision set comes from the operator's post-reboot formal gate. (memory: `feedback_operator_owns_host_reboots`)
- **Autonomous boundary:** proceed through *v6-in-production + throughput-confirmed + garbage-sanity-checked*. The **formal eval-parity suite, era-registry row, attestation are operator/human steps** (MEASUREMENT.md trust boundary). I prepare; I don't author.

## Source of truth
- Full procedure: session plan `/home/node/.claude/plans/fix-index-edits-and-cuddly-gadget.md`.
- **Line-level execution annex:** `/mnt/raid0/llm/tmp/v6_promotion_audit.md` (every `file:line` re-verified 2026-06-26).
- iqk-port branch state: clean, 0-behind/7-ahead FF of production-consolidated-v6 (merge-base==v6 HEAD `a4e2b4f8`). v6-iqk lib = `0.15.2`; v5 = `0.9.11` (SONAME-collide on `libggml-cpu.so.0`).

## ⚠ ANNEX CORRECTION (verified 2026-06-26, `stack_commands.py:644-655`)
The audit annex's "edit MASTER → recompile lean, never hand-edit lean" is **WRONG for the current state**: `--compile-registry` is **default OFF** (master has an unreconciled architect_general acceleration dual-source bug: `roles.X.acceleration=speculative_decoding` vs `server_mode.X.acceleration=moe_expert_reduction`). So the **LEAN registry is hand-maintained + authoritative**; runtime reads `derived/stack_priors.yaml` (compiled from LEAN, not master, by `stack_change_pipeline.py update`) + LEAN via RegistryLoader. **Corrected mechanism:** edit LEAN (`epyc-orchestrator/orchestration/model_registry.yaml`) as the authoritative source + sync MASTER for the record (reconcile the architect dual-source while we're touching it), then `stack_change_pipeline.py update` → diff `stack_priors.yaml`/`model_descriptors.yaml` to verify. Keep `--compile-registry` OFF (turning it on is out of scope). Worker base/head also have `stack_manifest.py:267/276` fallback hardcodes (Phase D).

## ⚙ CONVERGENCE ORACLE + worker dual-source (verified 2026-06-26 via `check`)
The promotion guard enforces **compiled `stack_priors.yaml` == `stack_manifest` launch manifest** — two sources that must AGREE per role. Run the read-only oracle during convergence:
`cd /mnt/raid0/llm/epyc-orchestrator && uv run python scripts/registry/stack_change_pipeline.py check`
**Worker is dual-source:** it reads its **binary** from the lean registry `runtime_requirements` (my Phase-C lean edit flipped binary→`llama.cpp`, env_policy→`canonical`, ld_library_path→[]) but its **spec.type / draft-head / base** from `stack_manifest.py` hardcodes (`WORKER_MTP_SPEC_TYPE`, `EXPLORE_DRAFT_MODEL`, `WORKER_POOL_MODELS`) — so the compiled spec.type is STILL `mtp` + old head until **Phase D edits the manifest**. The 3 worker-pool roles (worker_general/worker_math/toolrunner share the gemma worker) all show the same registry↔manifest disagreement. Converge lean+manifest together, re-run `check` until green, THEN `update` (writes artifacts). **`update` not yet run → on-disk `stack_priors.yaml` unchanged → runtime/production config inert until recompile (safe).**

### RESUME STATE (2026-06-26, post-convergence)
- **DONE + committed + tested** (Phases C/D/E/F/G/H): all registry/manifest/launcher/compiler/test/bench edits landed via a 10-agent parallel workflow + a serial gate-convergence loop. `stack_change_pipeline update` writes clean; **all no-inference gates green** (guard/guard_strict/runtime_attestation/q_scorer_priors); **174 promotion-gate pytest pass**.
  - Key resolutions during convergence: worker `model_id` swap needed `--allow-descriptor-model-removal` (old base garbles on v6, retired — coverage clean); frontdoor/coder/worker_summarize → Qwen3.6-MTP NEXTN (aliases inherit host, `acceleration: none`); compiler patched so **alias roles null their own draft** (`stack_priors.py` draft-mtp branch gated on `role == primary_role`); `ctx_max: 262144` re-added to qwen3.6 MTP blocks (closed a new known_gap); architect test updated to NEXTN-self-draft reality.
  - The worker base + the qwen3.6/architect models now carry NEW model_ids (`...-orig-...`, `...-mtp-...`) — intentional (distinct GGUFs). q_scorer baselines travel with the descriptor; routing is dynamic.
- **REMAINING:** B (branch strings, at cutover) · **I cutover** (build v6 in canonical → staging garbage-check + architect MTP smoke-gate → `stop/swap/start --hot-only` → assert `[iqk] ACTIVE`+draft-accept+`GGML_IQK` env+lib) · J verify · K N12 · L operator package · M docs/wiki/index close-out. Model files all on disk. `.bak` snapshots in `/mnt/raid0/llm/tmp/`.

## Ordered phases (gate in brackets)
- [x] **A** Pre-staged v5 rollback (`/mnt/raid0/llm/llama.cpp-v5-build-backup` binaries + detached `/mnt/raid0/llm/llama.cpp-v5` source worktree); FF-merged `iqk-port`→`production-consolidated-v6` (now `91745611f`); canonical still on v5; build reproducibility proven by validated `-v6-iqk` 0.15.2 build (authoritative canonical build at cutover, recipe captured: Release/clang-20/`GGML_NATIVE=ON GGML_OPENMP=ON GGML_LLAMAFILE=ON`).
- [ ] **B** (executes AT cutover, atomic w/ binary swap) Flip `verify_llama_cpp.sh:14` EXPECTED_BRANCH + 5 stale branch strings.
- [ ] **C** Master registry edits → recompile lean [lean recompiles clean]. (3 ik binary_dir blocks, 3 spec_type→draft-mtp, draft-head repoints, worker base→ORIG, **architect→MTP NEXTN variant + drop no-op expert override + drop 0.8B draft**, frontdoor+dense MTP, remove worker ik binary_dir.)
- [ ] **D** Manifest hardcodes (`stack_manifest.py:267/276/307/308`) + worker off worker_pool/binary_override [GGML_IQK in worker `/proc/environ`].
- [ ] **E** Launcher v6 grammar: 4 draft-max sites→`--spec-draft-n-max`+`draft-mtp`; wire `--no-mmap` into generic builder; null `--kv-hadamard`; `GGML_IQK=1` in stack_env (unstripped); drop vestigial `GGML_CCD_*`; mirror `server_lifecycle.py` if live.
- [ ] **F** `stack_priors.py` spec-dict `n_max` field + frontdoor/architect spec + `no_mmap`; `stack_change_pipeline update` THEN `check --run-promotion-gate` [gate green].
- [ ] **G** Governance tests + attestation reader → v6 grammar (lockstep w/ E/F); **remove architect from `NO_SPEC_DECODE_ROLES:325`**; add GGML_IQK env-attestation [pytest gate-targets pass].
- [ ] **H** `canonical_recipe.py` V6_IQK bench entry + `GGML_IQK=1` candidate-arm env [bench loads v6 lib].
- [ ] **I** Cutover: host hygiene (NO reboot) → staging garbage-check + architect MTP smoke-gate (fallback base-iqk) → checkout v6 in canonical + rebuild + free v6 branch → `stop→swap→start --hot-only` [`[iqk] ACTIVE` + draft-accept>0 + `GGML_IQK` env + loaded-lib v6 + verify_llama_cpp].
- [ ] **J** Autonomous verify: per-role throughput (throttle-caveated) + garbage sanity [bar = all healthy + within expectation + no garbage].
- [ ] **K** N12 `no_mmap:true` for frontdoor/ingest/vision quarters, one per window [`/proc/numa_maps` node-local placement].
- [ ] **L** STOP → prepare operator package (P-QUAL-PROMO cmd, era-row draft, attestation) — do NOT author.
- [ ] **M** Docs/wiki/index close-out + supersede stale verdict; per-repo commits (no push, report hashes).

## Blocking gaps (resolved-in-plan; see annex for line detail)
1. PG-1 checkout (FF merge → checkout-in-canonical at cutover; v5 rollback pre-staged) · 2. SONAME lib-shadow (scrub LD_LIBRARY_PATH + `/proc/maps` assert) · 3. v6 CLI arg-parse (`--draft-max`→removed; 4 sites→`--spec-draft-n-max`) · 4. promotion-gate pytest fails-closed (rewrite lockstep) · 5. GGML_* strip kills worker iqk (migrate off binary_override) · 6. worker base-lineage garble (base→ORIG, head→v6-Q8) · 7. canonical_recipe prefers ik (add v6 entry).

## Rollback
R0 `GGML_IQK=0`+reload (→v6-clean) · R1 drop spec block · R2 restore ik binary_dir (kept inert) · R3 swap canonical→pre-staged `/mnt/raid0/llm/llama.cpp-v5` + flip EXPECTED_BRANCH back.

## Reporting
Tick the phase boxes here as each gate passes; append blockers inline. Phase M does the progress-log + master/domain-index rows + memory updates + per-repo commits. Do NOT push.
