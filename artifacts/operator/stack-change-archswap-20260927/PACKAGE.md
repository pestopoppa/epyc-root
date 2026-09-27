# Stack-change package: ARCHSWAP-20260927, the architect role swap (UNSIGNED)

**Decision (operator, 2026-09-27):** swap the two architect role labels. Ports and processes do not change.

| Process | Model | Before | After |
|---|---|---|---|
| `:8074` CPU, full 0-95 instance (holds all four CPU region locks) | Qwen3.8-Flash-Next UD-IQ4_XS | `architect_critic` | **`architect_general`** |
| `:8083` MI210 ROCm0 | Qwen3.8-27B Q8_0 + MTP | `architect_general` | **`architect_critic`** |
| `:8083` aliases | same 27B | `coder_escalation`, `ingest_long_context` hosted by `architect_general` | same aliases, hosted by **`architect_critic`** (operator ruling: the aliases stay on the 27B) |

**Purpose.** The frontdoor's existing escalation and delegation paths target `Role.ARCHITECT_GENERAL` by name:
- `src/graph/nodes.py` (ArchitectNode ~590-615, 695-721, 781);
- `chat_delegation.py:701`;
- the langgraph "architect" node.

After the swap those paths reach Flash-Next, the strongest model, with no new routing code. This is arm **A2** of the operator's thesis experiment:
- A0: the strongest model alone.
- A1: frontdoor alone.
- A2: frontdoor plus consultant escalation.

The consultant pin (HS-19d.P5, `docs/design/hs19-stage2-dispatch-20260927.md` A0) is `architect_general`.

**RI-21** (the graph never reaches `ARCHITECT_CRITIC`) is **deliberately not fixed**. The critic, now the 27B, stays reachable:
- by direct request (`x_force_role` / an explicit role);
- by the `critique_plan` consult skill.

Nothing is applied. No process was started, stopped or reloaded, and no inference was run.

## 1. Classification (change-role `classify.py`; `evidence/classify.txt`)

- `architect_general --to qwen38_flash_next_ud_iq4xs_local`: shape (b), a model swap on the host role.
- `architect_critic --to qwen38_27b_q8_local`: shape (b).
- `coder_escalation`, `ingest_long_context --alias-of architect_critic`: shape (a), an alias re-point.
- No shape (c): nothing gains a process.

In substance this is **a label swap over two unchanged processes**. The shape-(b) "needs-measurement" rows have nothing new to measure, because every model keeps serving in the same process at the same shape. The evidence rows moved *with* the model. The **new role-purpose** rows are the exception:
- Flash-Next has no graph-escalation-traffic measurement.
- The 27B has no critic-suite measurement.

That gap is exactly what arm A2 measures. It is recorded here and is not a gate.

## 2. The rule applied to every surface

| Fact class | Follows | Examples |
|---|---|---|
| **Binding** | the **process** | `server_mode` rows (incl. `shared_with`, `chat_template_kwargs`, recipe/threads/env, terse template, serving_shape), `numa_config`, `port_map`, `role_launch_meta`, stack_templates, stack_env blocks, URL fallbacks, dashboard GPU sets, eval-tower GPU lanes, kv_compress layer rows, `role_restart.*` knobs, contention-matrix pairs |
| **Model facts** | the **model** | `roles.<role>` model / acceleration / performance / memory / paged_attention / candidate_roles / compression point; catalogue PRIMARY roles; factual_risk tiers (by size) |
| **Identity** | the **role name** | Role enum, tier letter (general A, critic B), purpose `description`, `system_prompt_suffix`, `critique_plan` consult skill, timeouts (both 600, unchanged), `ARCHITECT_REPL_ROLES` |
| **Escalation** | **strength** (terminal = Flash-Next) | `_ESCALATION_MAP`, registry `escalation_chains`, "strongest model" routing hints, external-API hard-task fallback |

## 3. Surface inventory

### Research: `lane/archswap-20260927`

**`orchestration/model_registry.yaml` (the master)**
- `server_mode`: the two host-row keys are swapped (each row stays with its process), with a dated banner on each. `shared_with: [coder_escalation, ingest_long_context]` now sits on `server_mode.architect_critic`.
- Aliases:
  - `alias_of`, `inherits_spec_from`, `inherits_from` and `shared_gguf_with` now point to `architect_critic`.
  - The alias descriptions and current-state comments are updated.
  - The alias ports, URLs and `model_role` are unchanged (:8083, `qwen38_27b_q8_local`).
- `roles.architect_general` / `roles.architect_critic`: the model blocks are swapped, and tier, description and `system_prompt_suffix` are restored per role.
- `escalation_chains`:
  - `general`: worker_general → frontdoor → **architect_critic → architect_general**.
  - `reasoning`: frontdoor → **architect_critic → architect_general**. The D2 `explicit_request` triggers are unchanged.
- `routing_hints`: "boosted/deep reasoning" and the two B3 code/reasoning hints now go to `architect_general`. The critique/adversarial hints stay on `architect_critic`. (Under the live evaluator these hints are documented no-ops.)
- `external_claude_opus.fallback_role` becomes `architect_general`, following the big model.
- Catalogue PRIMARY roles: the Flash-Next row is now `architect_general`, and the 27B row is `architect_critic`.
- `process_layout`, the port-map header, the timeout comments (values unchanged), the voice-pipeline requirement (now `architect_critic`), and 27 `server_mode.`/`roles.` pointer comments are repointed.

**Other research files**
- `scripts/benchmark/prb_t4_tale_gpu.py`, `review_f1/ev13b_run.py`: they resolve the 27B's production argv by role, so they are rebound to `architect_critic`.
- `scripts/kernel_rnd/autokernel/loop/run.py:1211`: help text only (`orch:architect_critic` pins the 27B).

### Orchestrator: `lane/archswap-20260927` (82 files)
**Hand sources**
- `stack_topology.yaml`: the numa_config blocks are swapped.
- `launch_manifest.yaml`: port_map (general 8074, critic 8083, both aliases 8083), the hot list, `role_launch_meta`, voice/placement notes.
- `stack_templates/default.yaml`: entries swapped, `alias_to: architect_critic`.
- `stack_env.py`: role env blocks swapped; `arch_aliases` coder/ingest now point to `architect_critic`.
- `src/config/models.py` + `health.py`: `_LEGACY_SERVER_URL_FALLBACKS` and `_RUNTIME_SELECTED_ROLE_ALIASES`.
- `src/roles.py`:
  - Escalation: coder_escalation, thinking_reasoning and critic now go to **general**, which is **terminal**. Ingest → general is unchanged; it was a same-process null hop and is now a real hop.
  - Fallback: worker_math → [critic], ingest → [general]. general ↔ critic is unchanged. No same-fleet edge.
  - Docstrings updated.

**Process-following consumers**
- `_GPU_RESIDENT_ROLES` (dashboard).
- The eval_tower GPU lane set.
- `kv_compress` 64-layer row.
- Autopilot fallback ports.
- Escalation-prewarmer degraded ports.
- Seeding reload map.
- The 9 `role_restart.architect_*` knobs (config_applicator, review_plane_knobs) now point to `architect_critic`. They carry the 27B's q8 KV and draft geometry.
- `factual_risk` tiers.
- `context_limits`.
- The fleet / `_KV_CONTEXT_ROLES` / model-path preflight / gpu-shadow-lane `PRODUCTION_ROLE_NAMES` host lists.
- `DEFAULT_LLM_JUDGE_ROLE` (eval_tower, debug_scorer) now points to **`architect_critic`**. It is documented as "the disjoint GPU judge", and keeping it on the 27B keeps the measurement instrument unchanged (CJ-11).

**Comment-only:** chat.py `consultant_role="architect_general"` (kept; the consultant is meant to be the strongest model), `speech_layouts.yaml`, docs.

**Tests updated** (27 files).

**Derived (regenerated by the pipeline, never hand-edited):** lean `model_registry.yaml`, `model_descriptors.yaml`, `derived/stack_priors.yaml`, `docs/generated/current_stack_summary.md`. The procedure enums are unchanged, because the role names are the same.

**`orchestration/contention_matrix.yaml`:** a **declared relabel** by `tools/relabel_contention_matrix.py`.
- Names are swapped only in the stamped `pairs` / `unknown_pairs` sections.
- Each relabeled instance's `(cpu_list, port, threads)` is asserted equal to the post-swap NUMA_CONFIG.
- No measured value changed.
- `topology_hash` goes from `4893e37e5d603c80` to `5d772b2c4698b2ae`.
- `check_contention_matrix_fresh.py` passes: OK / fresh.

A stale matrix would fail closed: the contention gate would queue background traffic, the preflight gate would fail, and the safety gate would refuse the baseline.

### Root: `lane/archswap-20260927`
- `scripts/harness/task_delegation_probe.py` (+ its test): the `27b-think` arm pins `x_force_role=architect_critic`, which serves the :8083 27B with thinking at medium.
- `.claude/skills/kernel-promotion/promotion_gates.yaml`: the CPU quality gate roles are `[worker_general, architect_general]`, following the CPU model.
- `docs/reference/speech/cpu-speech-contention-20260924.md` §6: voice turns reason on the 27B, `architect_critic`.
- This package: PACKAGE.md, the ratify script, `tools/`, `evidence/`, `patches/`.

### Not edited here: owned elsewhere, prepared text in §9
- `handoffs/active/decision-aware-routing.md:725,737,773` (DAR-LAT-3 / 3i bindings).
- `handoffs/active/conversation-stack.md:109,274,400` (CS-17 voice target, now `architect_critic`).
- `wiki/routing-intelligence.md:1260` and `wiki/multimodal.md:135`.
- `scripts/vidya/adapters/README.md:312` (label the row by model).
- Memory notes: `project_champion_promotion_and_architect_swap_plan.md`, `project_gpu_models_should_have_repl_access.md`.
- Already stale before this change: research `docs/reference/models/MODELS.md`, `docs/MODEL_MANIFEST.md`, root `docs/infrastructure/orchestration-stack-map.html:130`, `02-storage-safety.md:219`. These still show the 122B.

## 4. Operator decisions (defaults prepared; the ratify script records the choice)

**Aliases: fixed by operator ruling (2026-09-27), not an option.** Only `architect_general` moves to Flash-Next. `coder_escalation` and `ingest_long_context` stay on the 27B, and :8083 keeps its port and process.
- They are re-pointed **explicitly** so that they keep resolving to the 27B's server:
  - `server_mode.architect_critic.shared_with: [coder_escalation, ingest_long_context]`, which is the binding;
  - `alias_of: architect_critic`, `inherits_spec_from: architect_critic`, `shared_gguf_with: architect_critic`;
  - `port_map` 8083;
  - `stack_templates alias_to: architect_critic`;
  - `_RUNTIME_SELECTED_ROLE_ALIASES` → `architect_critic`;
  - `stack_env` `arch_aliases` → `architect_critic`.
- Proven by `evidence/url_diff.txt`: both aliases still resolve to :8083.
- **Schema limitation (§4a):** the schema can only bind an alias to a *role* that owns a server. The aliases therefore follow the 27B's role label (now `architect_critic`), not the 27B's server itself. A schema refactor is needed so that roles bind to a server or model instance.

**O-2: Thinking follows the MODEL (default `follow-model`, prepared).**
- Ruling C1 ("architect_general thinks at medium") was made about the 27B's template, and the `reasoning_effort` branch is a property of that Jinja template. The kwargs therefore moved with the process:
  - `architect_critic` (27B) keeps `enable_thinking: true, reasoning_effort: medium`, the terse template and `--reasoning auto`.
  - `architect_general` (Flash-Next) keeps its measured serving config: `enable_thinking: false` and `--reasoning off`. mmlu_pro 0.755 and gpqa 0.651 were measured that way.
- *Alternative `follow-role`:* turn thinking on for Flash-Next. That is unverified on its template, unmeasured, and costs CPU wall time under the whole-machine lock. Not prepared.

**O-3: Bring-up (default `B1`, then B2 at the owners' boundaries).** See §7.

**Acknowledged by signing (no option; the signature records it):**
- **A-1.** The swap makes the whole-machine-lock CPU role the **routine graph-escalation terminal**. This supersedes, for this role name, both:
  - the 2026-07-30 role definition ("not expected to carry routine traffic");
  - the D2 premise that only `explicit_request` summons it.

  `region_lock_wait_s_by_holder` telemetry still does not exist.
- **A-2.** Inline traffic that was sized for the GPU architect now lands on the serial CPU role:
  - proactive plan decomposition and repair (256 tok);
  - the chat_review verdict (80 tok);
  - `DEFAULT_REVIEWER_ROLE`;
  - review_before_commit (off by default);
  - `risk_abstain_target_role`.

  This is consistent with "the consultant is the strongest model". A zero-code override exists for the reviewer: `ORCHESTRATOR_REVIEWER_ROLE=architect_critic`.
- **A-3.** The escalation prewarm (`n_predict=0`, ~500-token prefill) and the scouts bypass `cpu_region_lock`, so they now touch the 0-95 instance unlocked. They can contend with AutoKernel CPU measurement windows.
- **A-4.** Callers that name `architect_general` expecting the 27B now get Flash-Next. The ones found were rebound (§3). INF-78 `autokernel_actor_cli --role architect_general` callers must pass `architect_critic` to keep the GPU planner. DS41 itself binds by port and is unaffected.
- **A-5 (pre-existing, not caused here).** `ingest_long_context` is in `serial_roles` while its host is not.

## 4a. What the registry schema supports today (for the refactor to be filed)

**Servers are keyed by role name.**
- `server_mode.<key>` in the master is both a role name and a server (process) declaration: port, url, model, serving_shape and the rest.
- There is no separate server-id or model-instance namespace. "The :8083 server" has no name except the name of the role whose row owns it.

**`shared_with` (the binding) is role → role.**
- `server_mode.<host>.shared_with: [<alias roles>]` binds each alias to the host row's process.
- Every consumer resolves an alias through it:
  - `src/registry/stack_priors.py:900-907` (`_server_for_role`: `if role in cfg["shared_with"] -> (server_role, cfg, "server_mode.shared_with")`);
  - `src/registry/registry_compiler.py:117-119` (which roles to keep);
  - `src/registry/model_descriptors.py:1285-1300` (alias descriptor, via `binding_kind == "shared_with"`);
  - the launcher's derived `shared_with_first_n` (`scripts/server/stack_manifest.py:1270-1274` refuses a hand-written one).
- The host must be a role with its own row. An alias pointing at another alias is refused (change-role REFUSES).

**`alias_of` is documentation only.** It is validated for coherence with `shared_with` (`scripts/validate/check_shared_with_derivations.py:400-442`: "alias_of is DOCUMENTATION; shared_with is the load-bearing binding"). Nothing routes on it.

**`model_role` names a MODEL catalogue row, not a server.** For example, `qwen38_27b_q8_local` is a `roles.*` model entry. It is used:
- for descriptor config substitution (`model_descriptors.py:1290-1297`);
- as a resolution fallback only when a *server row's* `model_role` equals the queried name (`stack_priors.py:903-904`).

It cannot make an alias bind to "whatever server runs this model". The alias's own `model_role` does not select a process.

**An alias's own `server_mode` row** (`port: 8083`, `url`) is legal routing metadata that must EQUAL the host's port (`assert_alias_clean.py`). It is a restatement, not a binding.

**Consequence.** An alias follows its host's role LABEL. When a label moves between processes, as here, every alias must be re-pointed by hand across roughly 8 restated surfaces. That is exactly the failure class this package had to enumerate.

**The refactor to file** (owner: the main session): key servers by model instance (e.g. `servers.qwen38_27b_q8_gpu0 {port, model, shape, ...}`) and make every role, host or not, bind to a server id. Then this swap would be a two-line change to `roles.architect_general.server` and `roles.architect_critic.server`, and the aliases would not move at all.

## 5. DAR-LAT-3h / 3i interaction (nothing folded into this package)

**Status (coordinator, 2026-09-27).**
- DAR-LAT-3h G1 finished with verdict **T96**: 48 threads fails parity, and there is no hugepage shim.
- **Flash-Next keeps `-t 96`.** That is exactly what this package carries: the :8074 `numa_config` block keeps `cpu_shape: NUMA_FULL`, 96 threads, now under `architect_general`.
- Nothing from DAR-LAT-3h is applied, and none of it is folded in here.

The signed DAR-LAT-3h package (`artifacts/operator/stack-change-dar-lat-3h-20260926/`, receipt `RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926`) keys its T96 merge pair on **`architect_critic`**:
- orchestrator `lane/dar-lat-3h-v2-20260927` through `074f5683`: stack_env `architect_critic: {GGML_FUSED_DECODE_OFF: "1"}`, plus tests `test_stack_env_recipe_parity.py:31,34` and `test_launch_env_strip_preserve.py:64,74`;
- research `lane/dar-lat-3h-v2-t96-20260927` @ `a969d2f9`: `server_mode.architect_critic.recipe`.

**After this swap, the DAR-LAT-3h outcome belongs to whichever role serves Flash-Next, which is `architect_general`.** DAR-LAT-3i (`GGML_FA_SPLIT_KV`, `server_mode.architect_critic.recipe.env_not_serving` on its lanes) likewise.

Ordering:
- **If this swap lands first:** DAR-LAT-3h's T96 pair must be re-keyed `architect_critic` → `architect_general` by its preparer before it merges. Merged as-is, it would put `GGML_FUSED_DECODE_OFF` on the 27B and fail `declared_env_attestation`. Its receipt pins sha256, so the re-keyed patches need re-pinning and a fresh signature.
- **If DAR-LAT-3h lands first:** `ratify_archswap_20260927.sh` detects that `scripts/server/stack_env.py` and the master moved on origin/main and **refuses**. This package is then refreshed by its preparer (the transform is re-run, which carries the populated env block to `architect_general`) and re-pinned.
- T96 changes no `(cpu_list, port, threads)` tuple, so this package's contention-matrix relabel stays valid in either order.

## 6. Gates, as run on the lanes (evidence/)

| Gate | Result |
|---|---|
| change-role `classify.py` × 4 | (b)(b)(a)(a), rc 0 |
| `assert_alias_clean.py` coder/ingest → architect_critic, and `--all` (9 aliases) | **PASS** (`evidence/assert_alias_clean.txt`) |
| Operative-URL diff, static config before (main) vs after (lane) | **PASS: only architect_general (8083→8074) and architect_critic (8074→8083) moved**; coder/coder_escalation/ingest stay 8083 (`evidence/url_diff.txt`) |
| `stack_change_pipeline.py update --numa-mode both` (lane master) | lean, descriptors, priors, summary regenerated; guard / guard_strict / effort certs / stack_manifest_registry / q_scorer_priors **ok** (`evidence/pipeline-update.txt`) |
| `check` with the live state **relabeled** (simulated on a copy) | everything ok except runtime_attestation: **exactly 2** `slot_save_path` drift lines (each process's `--slot-save-path` names its old role; they clear at B2). declared_env_attestation **ok** (`evidence/pipeline-check-relabeled-state.txt`) |
| `check` with the live state **not** relabeled | 41 attestation errors (the two servers checked against each other's contracts). **Never reload the API before `relabel_state.py`.** |
| contention matrix fresh / validate after relabel | OK, `5d772b2c` |
| Tests | see `evidence/tests.txt` |

**Pipeline gap found (documented, not fixed here).** `stack_change_pipeline.py update` cannot compile the lean registry on a **port swap**. Its lean step imports `stack_manifest`, and that runs launcher/master parity against the **old** lean at import. The documented bootstrap is to compile lean first with the explicit active-role set (§7 step 2), after which `update` runs clean.

## 6a. Lanes and commits (all pushed; nothing on any main)

| Repo | Lane | Base (origin/main) | Commits |
|---|---|---|---|
| epyc-inference-research | `lane/archswap-20260927` | `86a33a54` | `61af24fa` registry + 27B-argv scripts |
| epyc-orchestrator | `lane/archswap-20260927` | `b020a1a8` | `48a012c3` hand sources + tests · `b0d3317e` derived regen · `28cbe113` matrix relabel |
| epyc-root | `lane/archswap-20260927` | `db398a70`, merged with origin/main `dd32d852` | `3acce399` root consumers · then this package |

`patches/` carries the same commits as `git format-patch` output.

## 7. Apply and bring-up (after the receipt exists; run by the session owning the inference)

Preconditions:
- `RATIFY-ARCHSWAP-20260927.json` exists.
- No eval or measurement is running against the API. If one is, SIGSTOP its runner around step 6.
- Both `/mnt/raid0/llm/cache/kv_slots/architect_{general,critic}` are empty. They were 0 files on 2026-09-27; if not empty, move them to a dated quarantine directory.

1. Merge the three lanes ff-only to main (research, orchestrator, root) at the pinned commits. The orchestrator lane already carries the regenerated derived files and the relabeled matrix.
2. Bootstrap, then run `update` (idempotent; should report no change on the pinned commits):
   ```bash
   cd /mnt/raid0/llm/epyc-orchestrator
   .venv/bin/python src/registry/registry_compiler.py --force --roles architect_critic architect_general coder_escalation embedder embedder_1 embedder_2 embedder_3 embedder_4 embedder_5 embedder_bge_m3 embedder_granite_97m_r2 embedder_multilingual_e5_base frontdoor ingest_long_context toolrunner vision_escalation worker worker_explore worker_fast worker_general worker_math worker_summarize worker_vision
   .venv/bin/python scripts/registry/stack_change_pipeline.py update --numa-mode both
   ```
3. `python3 <pkg>/tools/relabel_state.py`: a dry run, then `--apply`.
   - It proves pid identity from `/proc/<pid>/cmdline` (27B on --port 8083, Flash-Next on --port 8074).
   - It backs up and renames atomically.
   - It repoints both aliases from the dead pid 2009477 to the live :8083 pid.
   - It signals nothing.
4. `python3 scripts/validate/check_contention_matrix_fresh.py`, expecting OK `5d772b2c`.
5. **B1:** `orchestrator_stack.py reload orchestrator`. API only; do not stop autopilot. This rewrites the runtime-facts manifest from the relabeled state. Until then, live runtime facts route `coder_escalation` to :8074 (observed in the lane snapshot), so step 3 **must** precede this step.
6. `stack_change_pipeline.py check --numa-mode both`. Expect only the 2 slot_save_path lines, plus `declared_env_attestation: ok`.
7. **Serving proof** (each with a real token budget; thinking bills reasoning against `max_tokens`):
   - **P1.** A real frontdoor escalation reaches Flash-Next. A graph request that escalates to ArchitectNode shows a completion served by :8074, confirmed by the llama log task counter on `logs/llama-server-8074.log` and the API trace `role=architect_general`.
   - **P2.** `x_force_role=architect_critic` returns a completion from :8083 (27B, reasoning_content present at medium).
   - **P3.** `coder_escalation` and `ingest_long_context` each complete on :8083 (8083 log task counter, not :8074).
   - **P4.** `url_snapshot.sh capture` on main equals `evidence/urls-after-static.tsv` for all 19 fields.
8. **B2:** clear the two slot_save_path drifts by relaunching each server under its new label, at its owner's boundary.
   - `reload architect_critic` (:8083) between DS41 batches (workspace-76's planner uses :8083).
   - `reload architect_general` (:8074) at a quiet boundary of the :8074 process's current users (AutoKernel CPU windows, DAR-LAT follow-ups). If the re-keyed DAR-LAT-3h T96 pair is applied later, its own reload of the same process can be fused with this one.
   - Then `check` should show 0 drift.

## 8. Rollback

- **Before B2:**
  1. `relabel_state.py --reverse --apply` (or restore the `.pre-archswap-*` backup).
  2. `git revert` the three merge ranges.
  3. Run the §7-step-2 bootstrap on the reverted tree, then `update`.
  4. `reload orchestrator`.

  The model servers were never touched, so nothing else moves.
- **After B2:** do the same, then `reload architect_general` and `reload architect_critic` under the reverted config, at the same owner boundaries. The kv_slots dirs must be empty or quarantined again first.
- The contention-matrix relabel reverts with the orchestrator lane. `relabel_contention_matrix.py` refuses to run twice.

## 9. Prepared text for surfaces owned by other sessions (apply by the owner)

**DAR-LAT-3 (`decision-aware-routing.md:725`).**
> "Flash-Next (`architect_general` :8074 since ARCHSWAP-20260927) … divert target `architect_critic` (:8083)"

**:737:**
> "architect_general chosen under A0 and A1"

**:773 (DAR-LAT-3i):**
> key `server_mode.architect_general.recipe.env_not_serving` (the Flash-Next row; renamed by ARCHSWAP-20260927)

**CS-17 (`conversation-stack.md:109,274`).**
> voice reasoning target `architect_critic` (the :8083 27B; renamed by ARCHSWAP-20260927)

**RI-21 / RTG-30.**
> "The escalation map now ends at architect_general (Flash-Next) and the graph targets architect_general, so they agree; the critic (27B) is reachable only by direct request and critique_plan — deliberately (operator, 2026-09-27)."

**Memory.** `project_champion_promotion_and_architect_swap_plan`: Flash-Next is `architect_general` from ARCHSWAP-20260927 (on signature and apply); the 27B is `architect_critic`.

## 10. Signing

The operator is on the remote app. Nothing here assumes immediate signing.

```bash
cd /workspace/artifacts/operator/stack-change-archswap-20260927     # after the root lane merges, or from the lane worktree
./ratify_archswap_20260927.sh --validate-only
RATIFY_OPERATOR="<your name>" ./ratify_archswap_20260927.sh --attest RATIFY-ARCHSWAP-20260927
#   optional: THINKING_OPTION=follow-model BRINGUP_OPTION=B1|B2
#   chat consent recorded by a session: add RATIFY_CONSENT_REF="<chat reference>"
```

The script **refuses** in these cases:
- `RATIFY_OPERATOR` is unset, empty or a placeholder (`operator`, `default`, `claude`, `agent`, `root`, …).
- The token is already spent.
- A pinned file changed.
- A lane commit is missing from its origin lane.
- **Any touched path moved on origin/main since the lane base.** A stale package is refreshed by its preparer and re-pinned, never signed as-is.

It applies nothing.
