# Audit — orchestration stack wiring, 2026-07-30 / 07-31

**Auditor:** Fable 5 session, 2026-07-31. Read-only: no repo writes outside this file, no commits,
no process started or stopped, no branch switched in any shared clone.

**Scope:** every commit on 07-30 and 07-31 across `epyc-root`, `epyc-orchestrator`,
`epyc-inference-research` touching the registry compile chain, the NUMA topology, the
stack-change gate, the speculative-decoding recipe, the measurement constitution, and the
ggml/speech-kernel freeze — plus the uncommitted working-tree state of all three repos.

**Stack state at audit time:** DOWN. No `llama-server` process is running and no stack port is
listening. Every production-impacting finding below is therefore *latent*, and fires at the next
`orchestrator_stack.py start`.

---

## Summary

The work of these two days is, in substance, good: real defects were found, root-caused with
genuine rigour, and honestly retracted when the evidence turned. The failures are almost entirely
in **mechanical completion** — changes made at the source layer that were never propagated to the
compiled layer that production actually reads, and guards written to enforce the new rules that
cannot fail.

Two systemic patterns account for most of what follows:

1. **Source-layer edits that never reached the consumed layer.** The master registry is the source
   of truth; `derived/stack_priors.yaml` is what the launcher reads verbatim. Three separate
   changes were made in master and never compiled down. In each case the commit message *correctly
   documented* that the propagation step was required.
2. **Guards that cannot fail.** Five independent guards written or touched in this window return
   success on the exact condition they were created to detect.

---

## P0 — production would launch a speculative recipe that was falsified the same day

**Confirmed.** Four-layer chain, three states, disagreeing.

| Layer | Value | Commit |
|---|---|---|
| master registry (source of truth) | `production_recipe: draft-mtp` — "ngram nowhere" | `a126e43d` 07-31 **17:38** |
| lean registry (7 sites) | `ngram-mod,draft-mtp` | `6390b871` 07-31 14:16 |
| `model_descriptors.yaml` (3 sites) | `ngram-mod,draft-mtp` | `6390b871` |
| **`derived/stack_priors.yaml`** — read verbatim by the launcher | `ngram-mod,draft-mtp` | `6390b871` |

Five roles carry the composed recipe at
`roles.<role>.serving.launch.runtime.flags.spec.type`: **architect_general, frontdoor, toolrunner,
worker_general, worker_math**. `orchestrator_stack.py:296` passes that string straight to
`--spec-type`, and the frozen v8 binary accepts the comma syntax
(`common/arg.cpp:3935`, `common/speculative.cpp:36-46`), so the servers will start and run it.

**Why this matters.** The composed recipe was adopted at 11:57 and **reversed at 17:38 the same
day** on direct evidence: on 12 matched long-context coding prompts at 15k–28k context, composed
won **0 of 12** — mean −4.06% against the first `draft-mtp` baseline and −8.24% against a replicate
of the same config; composed drafts *more* and accepts *less* (extend_3: 518 → 708 drafts,
acceptance 0.734 → 0.540). On gemma, n-gram produced **zero drafts on 9 of 12 prompts**.

`a126e43d`'s own body states the required follow-up and it was not done:

> NOTE: a master-registry edit alone does not change production behaviour — stack_change_pipeline.py
> must regenerate derived/stack_priors.yaml first.

**Partial self-heal, which does not save it.** `orchestrator_stack.py start` recompiles the *lean*
registry from master by default (`--compile-registry`, cache-aware), and the cache key is stale
(`.lean_cache_key` = `0e441d3d…`, recomputed `61109fcc…`), so layers 1→2 will self-heal.
`--compile-descriptors` defaults to **off**, and `stack_priors.yaml` is regenerated **only** by
`stack_change_pipeline.py`. The layer the launcher reads is the one that does not heal.

**Also unresolved:** the reversal never reached the human-readable record. Handoff
`speculative-decoding-mtp-refresh.md` (mtime 14:14, clean in git) still closes **SR-1** as
"Now set to the composed value on all affected entries" and leaves **SR-5** open asserting the
composed recipe "is what is now committed and launching". `progress/2026-07/2026-07-31.md` says the
same. The root repo has no commit after 16:43. A reader of the handoff and a reader of the master
registry get opposite answers.

**Remediation is blocked — see P0-4.**

---

## P0-2 — routing still decides on throughput priors that were corrected but never propagated

**Confirmed.** `5dfc339e` (07-31 12:11) corrected four priors in master, stating the reason
plainly: *"routing has been deciding on figures well below the ratified production optima."*
The correction never reached the file the router reads.

`RegistryLoader` reads the **lean** registry (`src/registry/registry_loader.py:28-29`);
`src/cli.py:464` and `src/mcp_server.py:74,122` read `optimized_tps or baseline_tps`;
`scripts/graph_router/train_graph_router.py:79,141` reads `optimized_tps`.

| role | lean (what routing reads) | master (corrected) | error |
|---|---|---|---|
| frontdoor | 24.3 / 24.3 | null / **40.22** | −40% |
| coder_escalation | 24.3 / 24.3 | null / **40.22** | −40% |
| worker_summarize | 24.3 / 24.3 | null / **40.22** | −40% |
| worker_general | 38.46 / 38.46 | 37.63 / **56.86** | −32% |

The `optimized_tps_attest` provenance field added by the commit is absent from the lean registry
entirely, so the attestation does not travel with the number.

**The correction is also incomplete at the source.** `q_scorer.registry_baseline_tps_by_role`
(`orchestration/repl_memory/q_scorer.py:556-566`) prefers `server_mode.<key>.throughput` over
`roles.*.performance`. In master those are still `frontdoor: 24.3` and `worker: 38.46` — untouched
by `5dfc339e`. So even a clean full recompile leaves the q_scorer cost model on the stale figures
while the CLI/MCP/router surfaces move to the corrected ones: a split brain, not a fix.
(This is the two-source-of-truth hazard already recorded for `baseline_tps_by_role`.)

**SUSPECTED side effect, unanalysed in the commit:** `scripts/lib/registry.py:534-544` uses
`baseline_tps` as a divisor in `get_timeout_multiplier`; `None` returns the conservative `2.0`.
Setting `baseline_tps: null` on the three Qwen3.6-35B roles will double their timeout multiplier
once it propagates. Conservative, non-crashing, but unintended.

---

## P0-3 — the topology cutover finished in code and stopped before the data

**Confirmed.** `982adb0c` / `270cf9ea` (07-31) retired the quarter fleet and deployed 1 full +
2 halves. The Python layer is correct and well-executed; the compiled artifacts around it still
describe 4 quarters.

**The arithmetic is right** (independently verified against `numactl -H` and
`thread_siblings_list`; sibling of *N* is *N+96*):

| instance | cpuset | physical cores | `-t` | policy |
|---|---|---|---|---|
| full | `0-95` | 96 | 96 | `--interleave=all` |
| half A | `0-47,96-143` | 48 (nodes 0,1) | 48 | `--interleave=0,1` |
| half B | `48-95,144-191` | 48 (nodes 2,3) | 48 | `--interleave=2,3` |

48 + 48 = 96 = the full; every interleave list matches its cpuset; `-t` equals physical-core count
for all 13 instances, enforced at import by `_assert_instance_invariants`.

**What was not finished:**

- **The lean registry was never recompiled.** Its header reads `Compiled at: 2026-07-30T19:44:20Z`;
  the master change (`519b96d1`) landed at **20:33:03**, 49 minutes later. Lean still declares
  `numa_instances: 4` with the retired ports `8280/8380/8282/8382`, and omits
  `ingest_long_context.numa_ports` entirely. This is the root cause of most of the rest.
- **The `2x48t_half_instances` branch added by `270cf9ea` is dead code.** It keys off
  `numa_instances == 2`; lean still says 4. `grep -c "2x48t_half_instances"
  orchestration/model_descriptors.yaml` → **0**. The descriptor committed *in that same commit*
  still reads `4x48t_quarter_instances` and advertises the retired ports — which the cutover's own
  reasoning says must not be revived, because several fail-open paths treat an unknown port as
  lock-free.
- **23 unit tests are red** (independently reproduced: `23 failed, 189 passed` across
  `test_full_slot_demotion`, `test_fleet_layer_build`, `test_quarter_stack_smoke`,
  `test_stack_priors_compiler`, `test_build_server_command_helpers`, `test_dynamic_stack`,
  `test_gpu_shadow_lane_p2`). Every assertion is a retired port literal, a count of 4 quarters, or
  the pre-cutover `-t`/policy shape.
- **Two of those red tests forbid the fix** —
  `test_build_server_command_helpers.py:1036` asserts the half instances carry *no* numactl policy,
  and `:839` asserts `-t 96` on a 48-physical-core cpuset. These pin the exact two defects the
  cutover corrected. They must be replaced, not adjusted.
- `stack_templates/default.yaml` is entirely un-migrated (4-quarter ports, plus an NPS2-era header
  describing a 2-socket / 2-node machine) and fails its own validator.
- `scripts/smoke/quarter_stack_smoke.py:31-33` hardcodes the 15 quarter-era ports and now returns
  exit 2 unconditionally, regardless of endpoint health. This is an operator script.
- `docs/chapters/04-production-server-stack.md` documents the *pre-cutover defect* as live
  ("no numactl policy … 10.83 ± 0.04 t/s as-wired"), because `78e9d109` annotated it on 07-30 and
  `982adb0c` fixed the wiring on 07-31 without touching the chapter.

**Unflagged behaviour change:** `max_safe_concurrency` silently dropped **3 → 1** for frontdoor and
ingest_long_context. Because each role's full instance now covers all four NUMA regions, no half can
co-place. `scripts/autopilot/eval_tower.py:1209` caps eval fan-out on this value, so autopilot eval
concurrency for those roles falls 3× outside `quarter` mode. Correct under full-first semantics,
but named in neither commit message.

**Landmine left in place:** `scripts/server/stack_numa.py:84-87` still defines `NUMA_Q0A..Q1B` with
48 threads declared for 24 physical cores — a 2× SMT oversubscription that
`_assert_instance_invariants` would reject. It does not fire only because the two remaining
consumers hardcode `24` rather than unpacking the tuple. `982adb0c` added an explicit "do not reuse"
warning to `NUMA_NODE0/NUMA_NODE1` but left these, which are the ones actually wrong by 2×.

**Design question worth an operator answer:** the halves' cpusets include SMT siblings
(`0-47,96-143`) while the full's does not (`0-95`). Correctness rests on `-t 48` rather than on the
mask, so thread→physical-core placement is left to CFS. The strictly-canonical form (`0-47` / `48-95`)
passes both import-time invariants unchanged. Half B's mask also *literally contains* logical CPUs
184–191, which the GPU shadow lane pins to — so half B and the GPU lane contend on identical
logical CPUs, not merely SMT siblings.

**Also unbudgeted:** `--no-mmap` is now declared on ten roles and correctly reaches the command line
(traced end to end and verified). It gives every instance a private copy of the weights: roughly
**373 GB resident vs ~190 GB** under the previous shared-mmap fleet. No mlock/RAM-budget preflight
exists anywhere in `src/` or `scripts/`. Worth a headroom check before the next start on a 1.1 TB host.

---

## P0-4 — the single fix for P0-1/2/3 is blocked, and the obvious workaround is dangerous

One action resolves the spec-recipe drift, the throughput priors, and the topology artifact
staleness: recompile lean from master, then regenerate descriptors and `stack_priors.yaml` via
`stack_change_pipeline.py update`.

It currently **refuses**, by design and correctly:

```
stack_priors: failed
  error: refusing to compile stack priors: no quarterable-role port is listening, so the
  realized NUMA mode cannot be determined (stack down or probe unavailable). Not defaulting
  to 'full' — ESC-8 kill chain A4 would rewrite stack_priors.yaml to the dead full lineup.
```

So the derived layer cannot be repaired while the stack is down, and starting the stack is what
deploys the falsified recipe. Three further hazards sit on the obvious ways around it:

1. **The `check` output is misleading.** A clean-shell `check` reports **39 errors** and
   "fix 39 error(s) before promotion". Those errors are largely spurious: with the fleet down,
   `stack_change_guard.py:839-841` falls back to `env_stack_numa_mode()` = `full` and compares the
   half-fleet priors against a phantom full lineup. Under the intended mode the gate is green:
   `both` → OK · `full` → 12 errors · `quarter` → 21 · clean shell → 39. The pipeline's
   `_check_stack_priors` step got the fail-closed ESC-8 treatment; the `guard` step did not.
2. **The uncommitted working tree re-arms ESC-8 kill chain A4.**
   `scripts/registry/stack_change_pipeline.py:520-525` and `:561-566` now honour an explicit
   `ORCHESTRATOR_STACK_NUMA_MODE` and skip `_realized_compile_numa_mode` entirely — including its
   documented "env contradicts realized → prefer realized" rule. This sits *directly beneath* the
   comment at `:558-560` forbidding exactly that. Both 07-30 gate repairs were performed using this
   bypass; committed HEAD would have honoured the realized probe instead.
3. **`half` is not a valid mode.** `VALID_STACK_NUMA_MODES = {"full", "quarter", "both"}`
   (`scripts/server/stack_numa_mode.py:9`) was not updated by the cutover — `quarter` now means
   "the sub-full shape", which is halves. `normalize_stack_numa_mode` **silently** falls back to
   `full` for anything unrecognised, so an operator typing `half` gets the dead full lineup with no
   diagnostic. That is kill chain A4 triggered by a plausible typo.

**Recommended sequence** (operator-owned; the session that owns the inference executes the reload):
set the mode explicitly to the intended value, regenerate, verify the emitted argv, *then* start.
Do not run a bare `pipeline update` from an ambient shell while the uncommitted change is in place.

---

## P1 — five guards written or touched in this window cannot fail

This is the most consequential cross-cutting pattern found.

| Guard | Failure |
|---|---|
| `stack_change_guard.py:827-830`, `:1184-1185` | `_launch_manifest_targets` swallows any import error and returns `{}`; the caller then returns `[]`. Measured: with `scripts.server.stack_manifest` un-importable, `validate_stack_priors()` on the currently-failing priors returns **`ok=True, errors=0`** — 12 genuine alignment errors vanish with no warning. Not hypothetical: *every* guard invocation in this audit printed live circular-import failures for `stack_paths.LLAMA_SERVER` and `stack_manifest.HOT_SERVERS`. |
| `verify_speech_kernels.sh:27-29`, `:33-36` | A dirty working tree and a binary whose SHA-256 differs from the ratified one are **WARN only** — neither sets `RC`. The script prints `PASS`. Those two conditions *are* the state the freeze was ratified to make impossible. It also reads only `branch` and `binary_sha256`, never the recorded `commit` or `ggml_submodule_commit`. |
| `verify_ggml_linkage.sh:38` | Header claims it "guards against RE-INTRODUCING those entries". It does not — nothing checks `LD_LIBRARY_PATH` contents; line 86 only prints them. Re-add the dirs to `/etc/environment` and check the CPU-only `llama-server` and it prints PASS, because `build/bin` is both the poisoned entry and `$ORIGIN`. |
| `ratify_p_bench_placement_1_v2.sh:165` | `check_claims_grammar.sh >/dev/null && echo "claims-grammar validator: clean"` — the validator is warn-mode and always exits 0, and its output is discarded. The green check is incapable of being anything else. |
| `ratify_measurement_amendment_20260731.sh:143-147` | Four `grep -qF` presence checks. They passed while the apply had **torn a sentence of the constitution in half** (see P1-2), because every grepped marker string was present in the corrupted output. |

`check_claims_grammar.sh` — cited by `MEASUREMENT.md:146` as *the* validator — is wired into no
hook, no pre-commit, and no CI (the repo has only `dependabot.yml`). It also contains no check for
the `category=` field the 07-31 amendment made mandatory, so that amendment shipped with zero
enforcement. Run directly over `cpu-inference-optimization-index.md` it flags 8 lines, including the
live P0 row; nothing surfaces them because nothing runs it.

**Also unwired:** the stack-change guard runs at `orchestrator_stack.py start` but at no commit-time
hook. `002079d7`'s own message names this as the root cause of both 07-30 gate breaks — *"nothing
warns at commit time. That is two occurrences in one day"* — and ships no fix.

---

## P1-2 — the measurement constitution was corrupted by its own apply script

**Confirmed by direct reading.**

- **`MEASUREMENT.md:83` ends mid-sentence; its tail dangles at `:99`.** The line reads
  *"Cross-protocol comparisons are"*, then fifteen inserted lines of the new Category block, then
  *"analysis, labeled as such."* Cause: `ratify_measurement_amendment_20260731.sh:52-54` anchors on a
  *physical line* (`l.startswith(A1_ANCHOR)`) and inserts after it, but the target bullet wraps.
  The one clause forbidding cross-protocol comparison no longer exists as a readable sentence.
- **The §5 supersession pointer was invalidated by its own commit.** `MEASUREMENT.md:129` declares
  superseded *"the protocol-scoped statement at `measurement/protocols/bench-cpu.md:216-220`"*. At
  `0b92049e^` those lines *were* the intended target (P-BENCH-PLACEMENT-1 gate 6). The same commit's
  other edit shifted it to `:221-224`. Lines 216–220 now read **"Decode rate from `predicted_n` /
  `predicted_ms` only. A wall-clock rate is never a decode rate"** and **"Achieved concurrency
  measured per rung against nominal, and floored."** The constitution now declares superseded the
  exact gate that research commit `fcfe0b8c` was written to introduce. Verified line-by-line.
- **The mandate is structurally unsatisfiable as documented.** `:94` states "An unlabelled
  measurement is not decision-grade", but none of the three ✅ exemplars carries `category=`, and no
  protocol grammar line in any annex was updated to include it. The new ✅ exemplar at `:95-96`
  additionally contains a literal `attest …` ellipsis and quotes `10.12 tok/s` for
  ingest_long_context, where the measured optimum recorded on 07-30 is **22.92**.

**The agent digest has drifted from the constitution**, which matters because agents read the digest:

- `MEASUREMENT_POLICY.md:97` lists the trust boundary as "`MEASUREMENT.md`, the eval tower, scoring
  contracts, and this file". The constitution (`MEASUREMENT.md:119-120`) includes **"its `protocols/`
  annexes"** and the era registry. Since v2 moved *all* normative protocol text into the annexes,
  the digest tells agents the entire body of protocol law is editable. (The mechanical guard
  `human_only_paths.yaml:34-36` does cover them; the doctrine an agent reads does not.)
- `MEASUREMENT_POLICY.md:18` states OPTIMUM is *"The **ONLY** category a promotion may be decided
  on."* That sentence is nowhere in the constitution, and a promotion is by definition the adoption
  of a CANDIDATE. Read literally, the digest forbids all promotions.
- The whole of §1's metric-scoping rule (`MEASUREMENT.md:23-41`) and all of P-BENCH-PLACEMENT-1 are
  absent from the digest.

**The three-way category partition is neither exhaustive nor exclusive.** A winning kernel-promotion
run at its own best config is simultaneously CANDIDATE and OPTIMUM. Arm A0 "production as-wired"
during the 07-30 defect — and the *mandatory* P-SHED-1 arm A1 "lane resident, idle" — fall into no
category at all, which by `:94` makes a decision-load-bearing arm not decision-grade.

**Trust-boundary gap (SUSPECTED, not an accusation).** All three measurement ratifications
(`a9647a7a`, `07b7dcab`, `0b92049e`) emitted **no receipt** — no evidence hashes, no state diff, no
signature — which violates `MEASUREMENT.md:138-145`, the very clause they were amending. The
enforcement hook `check_trust_boundary_edit.sh:36` only intercepts `Write|Edit`, and every amendment
lands via `bash <ratify script>` — a path an agent can take identically. There is no content pin on
`MEASUREMENT.md` itself. I found **no positive evidence of self-ratification**; the decision-package
flow (`137accf7` propose → `0b92049e` ratify) is correct and the proposal document exists. The gap is
that no artifact can distinguish an operator apply from an agent apply on the one boundary declared
human-only.

**"Every prior headline was a baseline" was executed in the registry, declared in the indices.** The
machine-read surface was properly retagged with categories and attestation refs — genuinely good work.
The human-read surface was not: `cpu-inference-optimization-index.md:75` (a live **P0** row) and
`master-handoff-index.md:259` still present the spec-dec-off `23.36` figure as the headline damage
number with no category, and `cpu-inference-optimization-index.md:79` still ranks on tasks/hour after
`07b7dcab` made tok/s the ranking key.

---

## P1-3 — the speech-kernel freeze is real, but survives on one disk

**The core claim verifies.** Both trees are on `production-speech-v1`, both working trees are
**clean**, and the previously-uncommitted load-bearing gfx90a/ROCm-6.2 patches are genuinely
committed (whisper `b307379` FP8 guard; qwentts `2c1b518` → submodule `b86f660`, a real
+96/−29 thread-strided bitonic argsort for the gfx90a 1024-threads/block limit). The ratification
artifact's recorded SHA-256s match the on-disk binaries byte-for-byte, and the ggml "three
generations" premise is independently confirmed from both source and built sonames
(llama 0.16.0 · qwentts 0.17.0 · whisper 0.18.0).

**But neither freeze commit exists on any remote.** `git branch -r --contains HEAD` is empty for
both trees, and the qwentts ggml submodule is on a **detached HEAD** with no local or remote branch
pointing at `b86f660` — which does not exist upstream. A fresh clone plus `submodule update --init`
**fails**, so the patch that makes TTS work on this GPU survives only as an unreferenced object on
one disk. Contrast llama.cpp, which is properly backed up to `fork/production-consolidated-v8`.
The speech trees need an equivalent `fork` remote.

**The `/etc/environment` fix is correct and complete**, and better than advertised: the production
GPU binary really was silently linking CPU-only ggml (reproduced — `build-hip/bin/llama-server` under
the old path resolved all 7 libs from the CPU tree with `libggml-hip.so.0` absent entirely). Every
binary carries `DT_RUNPATH`, `ldconfig` has no `/mnt/raid0` entries, and every launcher that matters
sets its own path. The `94cf8d6c` retraction of the do-not-edit warning is correct: the retracted
premise was empirically false and would have blocked the real fix.

Two caveats: the fix does not take effect in processes started before 16:09 (verified — a live
service still carries the old path), and nothing records that a restart is needed. And
`CLAUDE.md:15-16` describes both trees as the "Production STT/TTS kernel", but the *running* speech
services are `faster_whisper`/CTranslate2 and PyTorch — no production code path invokes the frozen
ggml binaries at all. The freeze is of a planned cutover, documented as accomplished fact.

---

## P2 — registry-chain defects

- **`scripts/lib/env.sh:58` (both repos) reverts the model-root consolidation for every
  shell-launched stack.** It exports `ORCHESTRATOR_PATHS_MODEL_BASE=${LLM_ROOT}/lmstudio/models`,
  and an exported env var beats the Python default that `5219942d` corrected. Verified:
  clean env → `/mnt/raid0/llm/models`; with `env.sh` → the legacy root. `launch_production.sh`,
  `start_servers.sh`, `bootstrap.sh` and others source it. It works *today* only because all 9
  relative paths are publisher-prefixed and all 14 publishers are symlinked — it breaks on the first
  model registered under a publisher created after 07-30, which the project's own MRG-1 Step 0
  declares a FAIL condition.
- **The lean registry was hand-edited**, against the "compiled, never hand-edited" rule: it contains
  25 comments (the compiler uses `yaml.safe_dump`, which cannot emit any), its own banner still
  claims `Compiled at: 2026-07-30T19:44:20`, and it differs from a fresh dry-run compile by
  **34 leaves**. The edits are ephemeral — the next start recompiles and discards them.
- **Compiled artifacts carry a false provenance stamp.** `model_descriptors.yaml:8-9` records
  `repo_commit: 270cf9ea` with `sha256: cf07e29c…`, but that hash belongs to `6390b871`
  (`270cf9ea` is `e5585234…`). They were compiled from a dirty worktree at 12:48 and stamped with
  then-HEAD; the content was committed 90 minutes later. Auditing "which commit produced this" sends
  you to a commit that does not contain it.
- **`docs/generated/current_stack_summary.md` was regenerated but never committed**, so at HEAD it
  shows `draft-mtp` and quarter ports while HEAD's own `stack_priors.yaml` shows composed and halves.
  Two committed-tree files contradict each other.
- **The frontdoor alias relation is prose, not data.** `server_mode.frontdoor.shared_with: []` in
  **master**, while `server_mode.worker.shared_with: [worker_math, toolrunner]` is correct.
  `model_descriptors.py:807-809` populates `runtime_aliases` *only* when `binding_kind ==
  "shared_with"`, so frontdoor's model gets `server_roles: [coder_escalation, frontdoor]` with
  `runtime_aliases: []` — no declared host. This is the root cause of the guard's
  `coder_escalation`/`worker_summarize` port and runtime errors, and it is why
  `stack_priors.yaml` gives `roles.frontdoor.acceleration.spec_type: 'none'` while the same role's
  launch flags say `ngram-mod,draft-mtp` — two fields of one derived file disagreeing on whether
  frontdoor speculates. `45a75d0c` documented coder_escalation as "an alias that inherits
  frontdoor's recipe" in a **comment**, where the compiler needed the `shared_with` field.
  The uncommitted `_manifest_alias_host` fallback papers over this guard-side and, as a side effect,
  disables launch-runtime validation for three roles (`stack_change_guard.py:1353`).
  **Fix is declarative and one line of data** in master.
- **Two live benchmark scenarios still point at deleted MiniCPM-o weights**
  (`k35_vision_matrix_runner.py:214-215,235-236`), and their guarding tests assert only that the argv
  *strings* contain those paths — they never stat the file, so the suite gives zero signal that the
  model is gone.
- **`REGISTRY_STANDARDS.md` contradicts itself**: *"Paths must be absolute (not relative to any
  base)"* alongside the Storage Root section added by `fd198dbf` documenting `model_base_path` — which
  exists solely to resolve relative paths. 208 of master's declared paths are relative.
- Research-repo twins of the two files `a1318585` fixed were missed;
  `epyc-inference-research/scripts/lib/onboard.py:53` is a live default.
- `a1318585` ("consolidate defaults") also rewrote `_server_for_role` alias→primary projection
  (+17 lines) — an undeclared compiler-semantics change in a path-defaults commit.
- **Every path in `derived/stack_priors.yaml` and `model_descriptors.yaml` exists on disk.**
  The launch-critical layer is clean. Master's 53 missing paths are all deprecated or
  catalogue-only entries, matching the validator's 12 known warnings.
- The MiniCPM-o registry deprecation itself is complete and well done: deprecated in place with
  reason and date, prior observations superseded-in-place rather than stripped, weights confirmed
  gone, zero routing dangle.

---

## Hygiene

**Verified safe, do now:**

- **1.37 GB of abandoned pack files** in `/workspace/.git/objects/pack/tmp_pack_{QlMjgI,WJ8KfU,hhZMcY}`.
  `git count-objects -vH` reports them itself as `garbage: 3 / size-garbage: 1.37 GiB`; orphaned by an
  interrupted `index-pack` at 16:25–16:28 (the next fetch succeeded at 16:43) and held open by no
  process. Prefer the explicit three-path `rm` over `git gc`, which would repack a clone other
  sessions share.
- **`llama.log` and `main.log`** are tracked and show as deleted; they were re-added by accident in a
  broad restore on 07-29. `/workspace/.gitignore:11` covers `logs/*.log` but not repo-root logs.
  Commit the deletion pathspec-limited and add `/*.log`.
- **`.devcontainer/Dockerfile.orig`** — verified the *older* file; the live `Dockerfile` is a strict
  superset. Nothing worth keeping.

**Operator judgement:**

- **4.5 GB of stale backup clones** (`repos/*.bak-2026-05-22*`). I verified the thing that would make
  deletion dangerous: all three have **zero commits not on origin, zero dirty files, zero stashes**.
  Ten weeks stale, left by the 05-22 symlink migration. They live under a gitignored path, so
  `git status` never showed them.
- **~5 GB from a recursive snapshot-nesting bug that is still active.** Snapshot dirs copy prior
  snapshot dirs with no base case — one contains 20 copies of the same 14.4 MB file up to 7 levels
  deep (`predecessor_snapshot/predecessor_snapshot/failed_mixed_snapshot/…`). **Fixing the generator
  is the higher-value half and is independent of any deletion** — it re-creates the waste every run.
- **~4 GB of byte-identical preimages**: four `question_pool.jsonl.before` copies, identical size and
  hash. Hardlink or replace with `.sha256` pointers — these are rollback evidence, so dedupe rather
  than delete, and let the owning E8 lane confirm the transactions are terminal.
- **`coordination/session-bus/advisory.jsonl` is 842 MB** — 99.6% of the bus directory.
  `BUS_PROTOCOL.md:33-34` documents rotation past all cursors into `archive/`; `archive/` holds
  160 KB. The policy is correct and simply is not running. Coordinator-owned.

**Blast radius, currently unguarded:** `artifacts/` (root, ~14 GB), `data/` (research, 31 GB) and
`benchmarks/prompts/` (3.2 GB) are all *partially tracked and not ignored*, so a single
`git add artifacts/` stages tens of GB. This quantifies the standing "never `git add` a shared path
wholesale" rule. `.gitignore` additions are the durable fix; concrete proposed lines are in the
hygiene appendix of this audit's working notes.

**Already-caused bloat:** `epyc-orchestrator/.gitignore` has `autopilot_journal.*` and
`autopilot_state.json*`, which do not match the rotated `autopilot_journal_1.jsonl` (already in
history at 16.79 MB and 15.37 MB) or `autopilot_state.<ts>.json`. Both untracked variants are present
right now and will be re-committed on the next broad `git add`.
`orchestration/repl_memory/kuzu_db/failure_graph` is likewise in history at 14.19 MB × 4 versions.

**Clean bills of health (verified, no action):** no secrets in any diff line of the last two days
across all three repos; all three repos exactly in sync with origin, nothing unpushed, nothing at risk
of loss; the 7 GB `embeddings.npy` blob in orchestrator history is a false alarm (packs to 7.3 MB, no
longer tracked, now ignored — **no history rewrite needed**); the `*.superseded-*`/`*-aborted-*`
convention is used consistently and totals only 19 MB.

**Process notes:**

- **`.git/hooks/pre-commit` is not version-controlled**, and it was modified at **17:42 today** — four
  minutes after the master reversal — to scope the contention-matrix check to a path allowlist. That
  is a real improvement to a governance control, living on one disk with no history and no backup.
  It also means the two `--no-verify` commits in this window predate the scoping: `2874ed73` would not
  need a bypass under the current hook, while `6390b871` (which touched `model_registry.yaml`) would —
  and its bypass also skipped the PII and hermes-drift checks, as the hook's own comment at line 18
  warns.
- **The contention-matrix gate is still red** (`live topology hash=bc28e15d`), so
  `safety_gate.py:1929-1931` blocks the speed-metric gate and eval fan-out falls back to
  certifications keyed to the old shapes. Refreshing it needs live inference. Tracked as N25 P0-3;
  the topology cutover is un-recertified until then.
- **An outstanding bus item is routed to `auditor`** (`msg-20260730T113024Z-88`, `action_required`,
  `corr_id msg-20260729T190635Z-50-coordinator-agent`) carrying three unresolved asks, including the
  retracted `27.06 t/s` exemplar in `MEASUREMENT.md`. Not cleared by this audit — it belongs to
  whichever session holds the `auditor` roster id.
- The session scratchpad at `/tmp/claude-1000/…` is blocked for Write/Edit by
  `scripts/hooks/check_filesystem_path.sh`, which requires `/mnt/raid0` (root FS is a 120 GB SSD).
  Shell redirects still work. Worth knowing before delegating work that writes scratch files.
- A wedged Codex session in another container has been blocked ~9.5 h on
  `git rebase --continue` → `git commit -e` → an interactive `vim` on `COMMIT_EDITMSG` that nobody
  will ever save. Different uid, not ours to touch; flagged for its owner. Preventive fix for our own
  tooling: set `GIT_EDITOR=true` for any automated `rebase --continue`.

---

## Credit

The retraction discipline is the strongest thing in this window. `84067a6e` withdrew a 2.80×
headline the same day it was published, correctly identified the mechanism (a warm-context self-copy
across repeated prompts), noted that the control had been in the data all along, left the raw logs
unedited, and filed four durable amendments so the shape cannot recur. `a126e43d` then reversed a
recipe adopted six hours earlier when the confirming test falsified it, and recorded the confound
(+4.17% monotonic host drift between replicates) that makes its own magnitudes soft. `5dfc339e`
refused to invent a `baseline_tps` where none was measured. `ratification_queue_20260730.md` derives
every threshold from measured population separation with a stated cost of being wrong, and
`wiki/benchmark-methodology.md:56-57` publishes an unresolved governance contradiction rather than
burying it.

The defects above are concentrated in mechanical application — anchor matching, cross-file line
references, propagation steps, and verification that structurally cannot fail — not in judgement.
