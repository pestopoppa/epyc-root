# Session friction audit — v10 promotion + lineup change, 2026-09-21/22

**Requested by the operator**: *"I really don't like all this friction involved with something as routine as
promoting a new kernel and modifying the stack. This is taking FAR TOO LONG."*
**Auditor**: Fable subagent, read-only. **Written**: 2026-09-22 ~14:45Z, while the stack is still down.

**Evidence legend, used on every claim below**
- **[V]** verified by running a command (the command is in Appendix B)
- **[R]** concluded by reading a file, commit, or the session transcript
- **[U]** could not be determined

Primary sources: the session transcript `~/.claude/projects/-workspace/75ba8e24-….jsonl` (29 h span,
955 tool calls, 122 operator messages, 42 subagent transcripts) [V]; git history of the three repos
[V]; `artifacts/operator/{lineup-change-20260922.md, kernel-freeze-runbook-hardening-20260922.md,
v10-qualification-…json, ratify_v10_final_freeze_20260922.json}` [R]; the pipeline and guard code [R].

---

## 0. Verdict in six lines

1. **~16 h of active operator-facing time** were spent (10.9 h on 09-21, 5.0 h on 09-22 so far, overnight excluded) [V]. Of that, roughly **5–6 h is friction** — time that a correct system and a disciplined assistant would not have spent. The rest was real work: benches, a genuine kernel bisect, two rebuilds.
2. **The single most expensive defect was a number**: `kv_kib_per_token_f16` over-declared 4.06× for six fleet models. It cost ~2 h, one discarded lineup revision, one unnecessary GPU sweep, and nearly a quality tradeoff. It is a **system** defect.
3. **The promotion runbook was not executable.** It lacked an anchor, a relocatability check, a binary-set check, and a "this is only half a promotion" gate. ~2–3 h. **System.**
4. **The assistant's worst conduct was presenting spec-dec-off numbers as if they mattered — twice** — against a standing, memory-file-level rule. ~1 h plus trust. **Assistant.**
5. **The lineup change is not friction-by-accident; it is friction-by-design.** Five hand-copied restatements of role membership live in two repos, each guarded by a check that fires only after the previous one passes. The assistant made it worse by applying a one-file patch it had already documented would fail parity, then fixing consequences one class at a time (9 pipeline runs in 16 min). **System + assistant.**
6. **One pattern underlies most of it, and it is real** (§2): *derived facts restated as literals, checked against other literals or against mere existence, never against their source.*

---

## 1. Ranked diagnosis

Cost = wall-clock between the operator message or commit that opened the window and the one that closed it, read from transcript timestamps [V]. Where a window mixes legitimate work and friction I say which share I attribute and why. These are estimates of *wall-clock attributable*, not effort.

| # | Item | Class | Cost (est.) | How estimated |
|---|---|---|---|---|
| 1 | **KV capacity formula counted all layers; Qwen3.6/3.8 have `full_attention_interval 4`** → 4.06× over-count on six models; the declarations were hand-computed from the documented formula (`44d7516a`) | System — restated derived value | **~2 h** | rev-2 lineup agent built on the wrong premise 11:52→12:14 (22 min, discarded); VRAM/KV-quant discussion 12:49→13:32; sweep instrument 13:15→13:31; sweep windows 13:38→14:05; rev-3 agent 14:08→14:27 |
| 2 | **Promotion runbook/store not executable**: `archive/` empty since 07-31 (no rollback anchor); RUNPATH absolute (configure-time, `patchelf` absent → full rebuild); partial `--target` shipped 2 of 92 binaries → real rollback + full rebuild; split-brain launcher paths (executor served v9 after cutover); `verify_llama_cpp.sh` attested the tree's `build/` not the store; scope tool's `"build-hip" in p` classifier reported gpu=0; promotion reported complete twice while freeze side undone | System — runbook rot + restated paths | **~2.5 h** | 09-21 19:40→20:17 store wiring/rebuild/repoint (37 min visible) + at least one earlier forced rebuild inside 14:09→19:40 (~1 h, [R] hardening table rows 1, 4) + 09-22 11:20→11:56 "you have NOT completed promotion" → branch cut, verifier re-pin (~40 min) + audit agents' main-thread wait (~20 min) |
| 3 | **Baseline-first detour against a standing rule** ("NO BASELINES", memory `feedback_headline_numbers_must_be_production_optimal`) — C5 spec-dec-off table presented 10:22; rebuke 10:24/10:25. **Repeated** 14:02 ("Early signal … f16 33.12 vs q8_0 32.13" — operator: "are these baselines or max performance decode speeds?") | Assistant | **~1 h** | 09:31 (recon done) → 10:25; second instance ~5 min + a stopped sweep |
| 4 | **Lineup-change cascade**: `port_map`, `role_launch_meta`, `numa_config`, procedure enum, `roles.*` model names, retired-model-on-live-role, non-MTP `model_role`, missing quality evidence — surfaced one class per pipeline run | System (restatements, staged gate) **+ assistant** (one-at-a-time; applied a patch whose own §4.2 said parity would fail with 8 problems) | **~25 min so far, stack still down**; the design phase 11:09→14:19 also carried it | 9 `stack_change_pipeline` invocations 14:20→14:36 [V]; final state 14:38 "Stopping the drill" |
| 5 | **Champion could not load gemma4 under MTP** — found by a failed bench arm, not by a preflight | System — no "load every scope model" preflight | **~1 h** | 12:05 blocked → 13:05 fix committed. The fix was necessary; the *discovery* could have been a 3-minute load check before any bench |
| 6 | **GPU sweep harness**: set-EQUALITY between `/proc/maps` and pinned libs (empty `ldd` set → 100 % invalid, zero records); then `max_tokens=512` inherited from another model → every replicate `finish_reason=length` | System — copies gathered by different mechanisms | **~15 min + two burned GPU windows** | 13:42→13:52 [V]; `0f8b7fae` |
| 7 | **AutoKernel anchored to v9 after promotion** — `PRODUCTION_BRANCH/COMMIT` literals; check = "branch resolves", v9 branch still exists → silent | System — pin valid by existence | **16 min** (agent) | 13:38→13:54, `61364621` [V] |
| 8 | **Assistant coordination/handling**: applied the registry patch while an agent under a "do not modify" brief was running → agent reverted it (14:19→14:28); removed the push worktree before confirming the push, recovered by SHA (11:55→11:56); invented "a card that also fragments" (14:06→14:08 retraction); deferred the champion reseed as "yours to decide" at 13:32, then a subagent did it with no decision needed | Assistant | **~25 min + trust** | timestamps [V] |
| 9 | AP-55 test rotted on wall-clock fixtures | System | 5 min | `23b148e0` |
| — | **Not friction, listed for honesty**: the VL-30B −30 % bisect over 89 revisions (14:09→~19:40, ~5.5 h). A three-week-old champion defect (CPU-only fused MoE op with no HIP kernel) that the per-distinct-model GPU gate caught. The runbook *worked* here. The *AutoKernel* loop not having a GPU-MoE gate is a separate gap. | Legitimate | ~5.5 h | |

**Steering cost not in the table**: the operator had to intervene on sequencing eleven times (09:52 and 11:53 "I see idle resources"; 11:23 "What about the other CPU roles?"; 11:25/11:26 comparator correction; 13:04 "why are you asking me. We have a promotion runbook"; 13:05 "commit the fix first"; 11:20/11:25 "you have NOT completed promotion"; 11:38 "unblock the frozen clone"; 14:33 "do this now") [V]. Each is a few minutes of wall-clock but is exactly the "hand-holding a workflow to a clean conclusion" CLAUDE.md forbids.

**One more thing the session left behind [V]**: both shared clones' local `main` is **behind their own pushed commits** (root `5a977761` vs `origin/main e9ecdda6`; orchestrator `a909b7f6` vs `44d7516a`). The worktree-push flow (`wrapup/*` branches → `serialized_push.py`) never fast-forwards the checked-out `main`, so `git status` now shows *phantom* modifications (`verify_llama_cpp.sh`, `stack_manifest.py`, `test_ap55…`) whose content equals `origin/main`, interleaved with the *real* uncommitted lineup edits (`launch_manifest.yaml`, `stack_topology.yaml`, `add_model_to_registry.yaml`, `native.py`, the lean registry). A `git checkout -- file` or a stash by anyone would revert pushed work. Fix: `git merge --ff-only origin/main` in both clones before anything else — but that is a write to a shared clone, so it belongs to the owning session, not to me.

---

## 2. The structural insight — real, not pareidolia

You proposed three rhymes: a hand-derived value from a wrong documented formula; a pin that stays valid because the thing it pins still exists; a check that compares two things gathered by different mechanisms. They are one thing.

**Name: *restated derivation* — a fact that is a function of some source is copied into a second place as a literal, and the gate compares literal to literal (or literal to existence), never literal to source.**

Every instance from this session, with its source and its restatement [R]:

| Fact | Source of truth | Restatement that rotted | Gate that kept passing |
|---|---|---|---|
| KV bytes/token | GGUF header (`block_count`, `full_attention_interval`, …) | `serving_shape.kv_kib_per_token_f16` hand-computed per role | capacity gate compared declared×n_ctx to VRAM; never re-derived from the header |
| Serving binary path | `kernels/production/<backend>` symlink | `stack_priors.yaml` pins `path.resolve()`d build dir (G11); ~29 source literals of `llama.cpp/build{,-hip}/bin` (G8) | `source_artifacts` hashes matched — of the stale copies |
| Production identity | frozen tree HEAD + store digests | `verify_llama_cpp.sh` constants; AutoKernel `PRODUCTION_BRANCH/COMMIT`; dashboard `PRODUCTION_STABLE_LINKS` literal (G10); `CLAUDE.md` freeze block | "branch exists" / "file exists" / hash of the tree's *old* `build/` |
| Backend of a role | `kernel_paths.backend_dir()` | `"build-hip" in path` / `hip\|rocm\|gfx` on argv[0] | substring true → until the store made it false |
| Which libs a server maps | `/proc/<pid>/maps` | pinned list from a *different* mechanism (`ldd`, which cannot see dlopen) | set equality — could never be true |
| Role→port, role→server, role→NUMA shape | master `server_mode.*` + `shared_with` | `launch_manifest.port_map`, `role_launch_meta`, `stack_topology.numa_config`, procedure enum, `roles.*` model names | parity check exists *because* the copies exist; it fails late, one class at a time |
| Canonical bench binary | the store | `canonical_recipe.py` resolved through the frozen source tree | it found a v9 binary and ran |
| Quality evidence for a role | measured suite artifacts | descriptor `known_gaps` | gate reports "missing"; nothing produces it |

What does **not** fit, so you can see the boundary: the AP-55 wall-clock rot (a fixture, not a copy); `max_tokens=512` (a default inherited across models — copy of a *parameter*, arguably adjacent); the MoE-fusion kernel bug (a real bug). Three non-fits out of eleven is a pattern, not pareidolia.

**The consequence is the fix principle, and it is one sentence**: *a restatement may exist only if the gate that guards it recomputes the fact from the source and diffs — never compares copy to copy, never tests presence.* Concretely:
- `kv_kib_per_token_f16` becomes a *derived* field: the compiler reads the GGUF header (it already reads `chat_template` from it) and the declared value, if kept at all, is a pinned expectation that fails on mismatch.
- `stack_priors` carries the **stable** `kernels/production/<backend>` path (G11's recommended option); resolution happens at launch. Then a promotion or a rollback is one `ln -sfn` and no recompile.
- `verify_llama_cpp.sh`, AutoKernel `campaign.py`, the dashboard table and the CLAUDE.md block all read **the ratification artifact** (`ratify_vN_final_freeze.json`) as their expectation. One file, written once, at signature.
- `launch_manifest.port_map` and `role_launch_meta` for aliases are **generated** from `server_mode.*.shared_with` (the manifest's own header says Phase 2 "stops RESTATING"; finish it). `numa_config` is keyed by *host* role only; an alias having one is a compile error at *lean* time, not a parity error three stages later.
- Any pin of the form "branch X at commit Y" is validated by `git rev-parse X == Y` **and** "X is the branch the ratification names" — not by X existing.

---

## 3. Recommended fixes, in the order to do them

Ordered by (friction removed ÷ effort). Items 1–4 are hours each; 5–8 are a day each.

1. **Fast-forward both shared clones' `main` to `origin/main`** (owning session; §1 tail). Until then every `git status` lies.
2. **Make the pipeline's `check` mode the *lineup preflight* and run it against a scratch copy of every source, in one pass, before any edit lands.** The tooling exists (§5 rows 1–21 of the lineup package did exactly this for the registry; parity and capacity were run standalone). The gap is procedural: nobody runs the *orchestrator-side* surfaces through it before apply. This is what the `stack-change` skill (§4) automates.
3. **Derive `kv_kib_per_token_f16` and the alias restatements** (§2 bullets 1 and 4). This removes the two most expensive defects of the session at their root.
4. **Finish the kernel-promotion skill** (§4.5): the two scripts it names do not exist [V]; write `scope.sh`, `package.sh`, a load-only preflight over the derived scope, and a generic `ratify_kernel_freeze.sh --version N` whose `--apply` also performs the branch cut (the operator runs it; it is still the operator's hands).
5. **Ratification-artifact as the single expectation source** (§2 bullet 3) — `verify_llama_cpp.sh`, AutoKernel, dashboard, CLAUDE.md block read it. Kills G3, G10, the campaign.py repin, and the hand-edited verifier constants in one move.
6. **Stable-path priors** (G11). Makes rollback one command and deletes step 8a.
7. **A measurement trigger for "missing quality evidence"**: the descriptor gate names the gap; the `stack-change` skill must dispatch the suite run (CPU-shape and GPU-shape harnesses both exist or are cheap to derive) rather than offering `--allow-known-gaps` as the default exit.
8. **Assistant rules that already exist but did not fire** — no new doctrine needed, but two are worth an explicit line in the skills' *Never* sections: *no spec-dec-off number leaves the session unlabelled, ever*; *a subagent's brief is a contract the main honours too*.

---

## 4. The skills the operator asked for

All modelled on `.claude/skills/kernel-promotion/`: one `SKILL.md` contract with numbered phases, one human gate, `scripts/` that **assert** rather than describe, and a *Never* list. They share one driver. **Compose, do not duplicate**: `new-model` (`.claude/commands/new-model.md`, wraps `onboard.py`) stays as the catalogue-entry step; `role-alias-change-runbook.md` (orchestrator) is absorbed into `change-role`.

### 4.1 The derivation graph every skill must respect [R, verified against `stack_topology.yaml:1-8`, `stack_change_pipeline.py:1181-1281`, `role-alias-change-runbook.md`, `stack-truth-precedence.md`]

```
HAND-EDITED SOURCES                                DERIVED (never by hand)
research/orchestration/model_registry.yaml  ──┐
   roles.*  server_mode.*  serving_shape       │    orchestrator/orchestration/model_registry.yaml   (lean)
   shared_with  deprecated markers             ├──▶ orchestration/model_descriptors.yaml
orchestrator/orchestration/stack_topology.yaml │──▶ orchestration/derived/stack_priors.yaml
   numa_config.<HOST role>.instances/shapes    │──▶ orchestration/procedures/*.yaml role enums (sync_procedure_role_enums)
scripts/server/stack_numa.py  (shape table)    │──▶ docs/generated/current_stack_summary.md
orchestration/launch_manifest.yaml  (port_map, │──▶ kernel_freeze_scope (reads priors)
   role_launch_meta — SHOULD be derived)       │
src/config/models.py ServerURLsConfig, src/roles.py fallback map  (code, alias delegation)
kernels/production/<backend>  (symlink)  ──────┘
```
Pipeline order in `update`: resolve numa mode → **lean** (stops here on failure) → descriptors (stops the rest on failure) → priors → procedure enums → summary → guard ×3 (parity, all-surfaces, strict) → effort certs → stack-manifest registry → q_scorer → runtime attestation → promotion gate. `check` runs the five compile steps read-only, then the same gates. **This is documented** — the lead that "the compile order was never stated anywhere the assistant found it" is wrong (§8).

**The rule the skills enforce**: every phase runs against a **scratch copy** of *both* repos' sources until the operator signs; the *complete* multi-repo patch set — master registry, topology, launch manifest, procedure enums, code delegation — is the package. A patch that touches one file and lists the others as "out of scope, and it is inert without these" (what shipped this session) is not a package.

### 4.2 `stack-change` — the umbrella (the only entry point)

```
0. intent        one YAML: {retire:[…], assign:{role: model|alias-of host}, topology:{role: {instances…}}}
1. scratch       copy research+orchestrator sources to /mnt/raid0/llm/tmp/stack-change-<ts>/
2. transform     apply intent → edit ALL hand-edited surfaces in the scratch (§4.1), by tool, not by hand
3. preflight     pipeline `check --numa-mode <declared>` on the scratch + parity + capacity + evidence durability
                 → ONE list of every violation, classified {fixable-by-transform, needs-measurement, needs-operator}
4. measure       for every `needs-measurement` (missing quality/speed evidence for a model newly holding a role):
                 dispatch the suite on the CURRENT stack if the model is servable, else queue for post-bringup —
                 never offer --allow-known-gaps as the first option
5. package       multi-repo patch set + the preflight report + the capacity report (host + GPU legs, per instance)
                 + measured evidence refs + the exact bring-up command + the rollback (git revert set)
6. OPERATOR SIGNS   ← the only human gate
7. apply         apply patch set to the real trees; `update --numa-mode <declared>`; `check --run-promotion-gate`
8. bring up      orchestrator_stack.py start; verify_serving per role (argv[0], /proc/maps, port, real completion)
9. wrap          progress, handoff rows (prepare; owner applies), commit per repo with pathspec, push, ff-only main
```
**Refuses**: to run while another stack-change or promotion holds the region/push lock; to apply with any `needs-operator` item unresolved; to use `--allow-descriptor-model-removal` for a model the intent does not name; to modify the real trees before step 6; to declare done before step 8's serving proof.
**Verifies**: after step 7, that the *live* fleet matches priors (runtime attestation), that no server maps a retired GGUF, and that every role in `hot_resident` answers a real completion.

### 4.3 `retire-model` (sub-skill)

Lifecycle is three-state and both states exist in the registry today [R]: **live → deprecated** (three-key marker on the row, `deprecated:/deprecated_date:/deprecated_reason:`, GGUF stays on disk; precedent `roles.reap_246b`) **→ deleted** (`deprecated_models:` graveyard row with `deleted:` and `path_was:`; precedent `7bc650b8` GLM-5.3).

- **Must**: enumerate every reference to the model — `roles.*` rows naming it, `server_mode` rows, `shared_with` hosts, `model_role` in launch manifest, `numa_config` block, procedure enums, drafters that name it as target, canonical recipes, AutoKernel campaign pins, evidence artifacts (`check_evidence_durability.py`). Present the list; refuse to mark deprecated while any *live role* still resolves to it (the session hit exactly this: "a retired model still claiming a live role").
- **Must**: derive the dependent removals — `numa_config` block, `role_launch_meta`, port vacated, host memory freed (capacity report delta) — into the patch set, not into prose.
- **Refuses**: to delete a GGUF at all (deletion is a separate operator action, memory rule "confirm deletes"), to deprecate the current rollback-anchor model for any role, to deprecate a model that a drafter in the lineup targets, to deprecate while a running server has it mapped.
- **Verifies**: post-apply, `deprecated_models` count unchanged (mark, not delete), descriptors compile with `--allow-descriptor-model-removal` naming exactly the intent's set, no `hot_resident` role points at it.

### 4.4 `change-role` (sub-skill; absorbs `role-alias-change-runbook.md`)

Three shapes, and the skill must classify which one it is because the blast radius differs by an order of magnitude [R]:
- **(a) alias re-point** (role moves onto another host's server): edit `server_mode.<newhost>.shared_with`, remove from old; delete the alias's own `server_mode` row if any; **delete** its `numa_config` and `role_launch_meta` (a role with no process must carry no NUMA wiring); update `roles.<alias>` model name to the host's artifact (the `worker_math`/`toolrunner` stale rows); `models.py` delegation; procedure enum sync.
- **(b) model swap on a host** (same role, new model): `server_mode.<role>` model/quant/serving_shape; `serving_shape` **derived** from the GGUF header; drafter compatibility (`draft-compat`); quality evidence for the new model in this role → `needs-measurement`.
- **(c) alias becomes its own server** (reverse of a): a *topology* event — route to `change-topology`.
- **Refuses**: `alias_of` without `shared_with` (documentation-only key); an alias with a `server_mode` row; a `model_role` pointing at an artifact that differs from the host's (the non-MTP defect); reasoning-effort settings that trip the L0–L4 ladder without certification.
- **Verifies**: `validate_declaration_parity()` clean; alias `serving.ports == host launch row`; snapshot of operative URLs before/after; a real completion through the alias name after bring-up.

### 4.5 `change-topology` (sub-skill)

Owns `stack_topology.yaml` (`numa_config` instances, `cpu_shape`, policies, `numa_pre_evict_gib`, `mlock`), `stack_numa.py` shapes, device moves (CPU↔GPU), ports.
- **Must**: for a new shape (the session's `NUMA_FULL_T48`), add it to `_CPU_SHAPES`, `_SHAPE_CLASSES` and the undersubscription allowlist in one diff; recompute the capacity report for both legs; recompute the contention-matrix recert requirement (any cpuset change triggers §H per the alias runbook).
- **Must know** that the capacity report decides "GPU role" from `shape_class == gpu_host_lane` (topology), **not** from the registry's `device:` key — moving a role between devices from the registry alone produces a GPU role with no VRAM declaration (revision 2's blocker (b)).
- **Refuses**: overlapping instances of the same role that could co-place; a GPU move without `vram_non_kv_gib` **re-measured** on a real load (the session found a 3.71 GiB unexplained gap and correctly did not guess); an `n_ctx` extrapolation without an explicit `UNVALIDATED` marker.
- **Verifies**: live affinity of every launched instance matches its declared shape (memory rule "verify LIVE affinity"); VRAM sampled *during* first load; no phantom instances in the capacity report.

### 4.6 `kernel-promotion` — where the skill written this session falls short [V/R]

It is a good contract and the right shape. Specific defects:
1. **It names `scripts/scope.sh` and `scripts/package.sh`; neither exists** — `scripts/` holds `anchor.sh`, `preflight.sh`, `verify_serving.sh` only [V]. The two most important phases (derive scope; emit the package with the REQUIRED key set) are prose.
2. **No driver.** Steps 1, 4, 5, 7, 8 are instructions to a reader. The operator's test ("I ask → it runs → I sign") needs one `promote.sh --candidate <sha>` that executes 0–5 unattended and stops at 6.
3. **No load-only preflight** across the derived scope. The gemma4 MTP assert cost an hour of bench window to find; loading every scope model once is minutes.
4. **The gates have no data file.** "Quality per the incumbent's recorded suites" — there is no `promotion_gates.yaml` recording which suites/roles/n the incumbent was gated on; v9 and v10 both used MMLU-Pro+GPQA on two roles by convention.
5. **Step 7 hand-edits `verify_llama_cpp.sh` constants and the AutoKernel pins** — restated derivation again (§2). The ratification artifact should be the single expectation source.
6. **The ratify script is per-promotion** (`ratify_v10_final_freeze_20260922.sh`, 143 lines, hand-written). Make it `ratify_kernel_freeze.sh --version N` and let `--apply` perform the branch cut and overlay bake (it ran under the operator's hands anyway; the manual cut took two attempts, 11:45 and 11:56 "already exists").
7. **Its rollback comment is incomplete**: `ln -sfn` ×2 + `git checkout v9`, omitting the step-8 regeneration that the hardening review says a rollback requires because priors pin the resolved build dir (G11). Fix by G11 or by the comment.
8. **No composition contract**: a promotion *ends with a stack change* (step 8 regen = `stack-change` step 7–8). Say so and call it.
9. Step 8's "champion reseed" was 21 hand-touched files (`61364621`); it needs a script that rewrites the pins from the ratification artifact.

---

## 5. Automation: the operator's test vs. the current state

> "I ask you to run the promotion runbook → it triggers the measurements → you build the ratification package → I sign → new version is frozen."

### Kernel promotion

| Stage | Today | Human in loop? | Should be? |
|---|---|---|---|
| derive scope | tool exists (`kernel_freeze_scope.py`), broke at the store cutover, fixed | no | no |
| anchor | `anchor.sh` (new, this session) | no | no |
| build | manual cmake; RUNPATH/target-set asserted after the fact by `preflight.sh` | assistant | no — build script with the configure flags baked in |
| load-only preflight | **absent** | — | no |
| measurements | run by hand per role; comparator logic corrected by the operator twice (11:25, 11:26) | assistant + operator steering | **no** — recipe-to-recipe per derived model is mechanical |
| quality gates | run by hand; no gates data file | assistant | no |
| package | hand-assembled JSON; v10 silently dropped two keys v9 had | assistant | no — `package.sh` with a fixed schema |
| **signature** | operator runs `ratify_…sh --apply` | **operator** | **yes, rightly** |
| branch cut in frozen clone | operator typed it | operator | rightly the operator's hands, but inside `--apply`, not typed |
| verifier constants, CLAUDE.md block, AutoKernel pins, dashboard table | hand-edited (script does CLAUDE.md only) | assistant | no — read the ratification artifact |
| regen priors, marker sweep, champion reseed | manual + subagent | assistant | no |
| serving proof | `verify_serving.sh` | no | no |

Verdict: **about half of the promotion is automated, and the automated half is the half that was written this session.** The measurement and packaging stages — the ones the operator's sentence puts in the middle — are still prose.

### Stack change

| Stage | Today | Human? | Should be? |
|---|---|---|---|
| state intent | operator prose (11:09, 11:11) | operator | **yes** — the lineup is the operator's |
| author the patch set | subagent drafts ONE file; orchestrator surfaces left as "inert without" | assistant | no |
| preflight all surfaces | possible (`check` + parity + capacity), not done as one pass | assistant | no |
| trigger missing measurements | **absent** — gate says "missing quality evidence", nothing produces it; no CPU-shape architect bench exists | — | no |
| package + sign | prose package, no signature artifact | operator reads 68 KB | yes, but on a one-page summary + a diff |
| apply, regen, gate | pipeline exists; two bypass flags classifier-gated | operator types the flags | the *decision* is the operator's (retire these four; waive this gap); the *typing* should be in the signed package |
| bring up + verify | `orchestrator_stack.py start` runs the gate | no | no |

Verdict: **the stack change has a good compiler and no workflow.** The friction is entirely in the missing layer between "operator intent" and "pipeline input".

### What RIGHTLY stays human
The freeze signature; the lineup decision; waiving a quality gap; deleting weights; accepting a quality delta outside the noise band; host reboots. Everything else in both tables is derivation.

---

## 6. Fan-out verdict

**Numbers [V]**: 22 `Agent` calls visible in the main transcript; 42 subagent transcripts under the session (the remainder came through the wrap-up skill and forks — [U] which). Batches: 4 (09:25), 3 (10:19), 3 (19:41), 4 (09:46), 3 (09:52), 5 (11:21–11:23), 6 (11:52–11:54), 4 (12:50–12:51), 2 (13:15), then singles. Recon agents ran 1–8 min with 7–31 KB handbacks. Execution agents: lineup draft 18 min/59 tools; rev-2 22 min/81 tools; rev-3 19 min/77 tools; AutoKernel repin 16 min/88 tools; sweep instrument 13 min/49 tools. Three agents were stopped (`TaskStop` 13:49, 14:03, 14:05); one ran 0 min/11 tools with no handback.

**Helped**: recon fan-outs were cheap and fast; the parallel commit/push clerical work landed eleven commits across three repos on 09-22 without blocking the main thread; the repin, the AP-55 fix, the harness fix and the sweep instrument were all subagent-produced and all committed.

**Hurt, with evidence**:
1. **Rev-2 of the lineup patch (22 min, 81 tools) was built on the unverified 4.06× premise and discarded.** The main thread dispatched execution before verifying the number it depended on. That is the "discarded work" cost `OPERATING_CONSTRAINTS` says to measure first — ~45 min of agent time, ~7 % of subagent transcripts by count.
2. **The main violated its own brief to a running agent** (14:19 apply vs. rev-3 agent's "do not modify the real registry"), costing a revert and re-apply (14:27). Fan-out created a shared-state hazard that the *When NOT to fan out* clause ("work requiring shared state") names.
3. **The critical path was never parallel.** Bench → fix → rebuild → bench, and preflight → parity → numa → enum → … are sequential phases of one piece of work. The operator's two "I see idle resources" complaints (09:52, 11:53) were about **compute**, and no agent width fixes that.
4. The 09:46 "find the regeneration procedure" agent handed back 3.7 KB; the procedure was in `stack_topology.yaml:8` and two runbooks. The finding did not become a checklist; the cascade was still worked serially seven hours later.

**Verdict**: fan-out neither caused nor cured the friction. It was right for recon and clerical work and neutral-to-slightly-negative on the critical path. CLAUDE.md's default is fine; what was missing is the *premise check before dispatch* and honouring the shared-state exception. Do not narrow the width; measure discarded work (already the doctrine) — this session's discarded share was small, but the one discarded item was the expensive one.

---

## 7. Assistant conduct — the list, with timestamps [V unless marked]

1. **Baselines presented as if production numbers, twice.** 10:22 C5 table on build 10151, spec-dec off → 10:24 "STOP wasting time", 10:25 "NO BASELINES / ONly max performance numbers". 14:02 "Early signal at one replicate has f16 33.12 vs q8_0 32.13" → "are these baselines or max performance decode speeds?" The rule exists as a memory file and as `MEASUREMENT_POLICY`. Not softened: the first instance spent the first hour of the session on work the operator had ruled out in advance.
2. **Invented a mechanism.** 14:06 "a card that also fragments" → 14:07 "what do you mean by this?" → 14:08 retraction: "I shouldn't have dressed an unmeasured gap up as a named mechanism." Credit: the 14:18 probe (`e9ecdda6`) is built so it cannot repeat the claim.
3. **Sweep continued past its purpose.** The KV-layer correction was measured on the live GPU build before the stack went down at 13:32 and answered the VRAM question; the sweep (instrument 13:15–13:31; runs 13:38–14:05) continued until three `TaskStop`s at 14:03–14:05 following the operator's 14:02/14:04 messages. [U] I could not find the verbatim "Why keep performing the sweep" in the transcript (operator messages are truncated at 400 chars in my extraction); the sequence supports the claim.
4. **Contract violated toward its own subagent.** 14:19 applied the registry patch; agent `ab1ca6ae` (14:08–14:27) had "do not modify the real registry"; 14:27 admission; `SendMessage` 14:28.
5. **Worktree removed before the push was confirmed** — 11:56 admission; commands 11:55–11:56 show the `wrapup/kp-freeze` branch re-added as `tmp-promo-v10b` after the push. Memory rule `worktree remove kills` exists.
6. **One error at a time.** Nine pipeline runs 14:20–14:36, each followed by one class of fix — while the package's own §4.2 had said at 14:19 that parity would fail with 8 problems and that `numa_config` and `launch_manifest` had to change. The consequences were *known* and left out of the patch.
7. **Recommended against cutting the v10 branch** (11:24: "store-side identity … rather than cutting a v10 branch") — contradicting CLAUDE.md's version-past contract; the skill it wrote 20 minutes later calls the state it recommended a "HALF promotion". The operator overrode at 11:38.
8. **Reported the promotion complete twice while the freeze side was undone** (qualification JSON `correction_note`; SKILL.md "2026-09-22: reported twice"). The operator discovered it (11:20 "is this true? I thought we had finalized v10").
9. **Deferred a non-decision.** 13:32 "Still yours to decide: the AutoKernel champion reseed needs a ref write into the frozen clone" — then a subagent did it 13:38–13:54 with no operator decision needed. Act-Don't-Defer, verbatim shape 2 ("Awaits your call on something already answered").
10. **Asked the operator whether to run a runbook step** — 13:04 "why are you asking me. We have a promotion runbook."
11. **Idle compute twice reported by the operator, not the assistant** (09:52, 11:53) — memory rule "idle compute is a reportable condition".
12. **29-hour single session to context compaction** (11:42:47 summary record). The lineup change is *disjoint* from the promotion; `SESSION_LIFECYCLE` says wrap up and `/clear`. The compaction landed in the middle of the freeze cut.
13. **Left both shared clones with local `main` behind origin** (§1 tail).

Neutral, but it mattered: a second operator session (`6d53f662`, 09:42–13:05, GLM-5.3 deletion + DeepSeek download) committed to the same master registry (`7bc650b8` 10:00) and launch manifest (`095628b6` 11:03) during the lineup drafting; the main had to warn its agent at 12:04 that "the registry base moved by one line". Two sessions editing the lineup at once is a source of friction the operator controls.

---

## 8. Corrections to the leads I was given

- **"The compile order was never stated anywhere the assistant found it" — wrong.** It is stated at `stack_topology.yaml:5-8` (`compile(master, roles, THIS FILE) -> lean -> descriptors -> priors`), in `stack_change_pipeline.py:1195-1196` ("master -> lean FIRST"), in `docs/reference/stack-change-launch-runbook.md` (Normal Sequence), in `docs/runbooks/role-alias-change-runbook.md` ("five layers", verification chain in order) and `docs/reference/stack-truth-precedence.md` [V]. What is missing is a **lineup-change surface checklist** (which restatements exist and which must be deleted for an alias), not the order.
- **The cascade was predicted, not discovered.** `lineup-change-20260922.md` §4.2 says "PROVEN BLOCKER (a), still open: parity fails with 8 problems" and names `numa_config` and `launch_manifest` — written *before* the 14:19 apply [R].
- **Commit roles**: `09ebc06c` is the freeze cut + verifier re-pin (11:55); `cdaa4dc0` is a merge; the ratification commit is `5a977761` (13:33) [V]. `44d7516a` is the KV-layers fix; the "earlier commit" is `c0c4db1a` (block width) [V].
- **`61364621` verified**: the campaign's own comment now says "the v9 branch still exists at its old commit, so `resolve_anchor` kept succeeding after the v10 freeze … A stale anchor here is silent by construction" [V].
- **The 30-launch / zero-record window and the `max_tokens` window** are verified in the transcript at 13:42–13:52 [V]; the harness fix is `0f8b7fae`.
- **The kernel-promotion skill has 3 scripts, not 5** [V].
- The overnight gap (20:17→09:41) is excluded from every cost figure; "FAR TOO LONG" in wall-clock terms is 29 h, in active terms ~16 h.

---

## Appendix A — session timeline (operator messages and landmarks) [V]

```
09-21 09:23  session start; operator: rebench v9, then promote the champion
      09:25  4 recon agents (5 min)
      09:52  op: "I see all resources idle"
      10:07-10:22  assistant proposes/present C5 baseline (build 10151, spec-dec off)
      10:24  op: "STOP wasting time"   10:25  "NO BASELINES" / "ONly max performance numbers"
      10:32-11:26  rebench; op steers: other CPU roles (11:23), DFlash2 (11:25), comparator (11:26)
      11:53  op: "are you sure? I see idle resources"
      12:05  champion cannot load gemma4 MTP → 12:07 "fix the assert and rebuild" → 13:05 fix committed
      13:04  op: "why are you asking me. We have a promotion runbook."
      14:09  op: "investigate the VL-30B regression" → bisect (89 revisions) → MoE fusion HIP gap found
      19:40  op: "fix the store wiring so we can promote"; 19:41 3 agents; anchors created 19:42
      20:03  full rebuild (first promotion had shipped 2 of 92 binaries; rolled back through the anchor)
      20:15  op: "promote once the full build finishes"; 20:17 store repointed
09-22 09:41  resume; 09:46/09:52 audit agents; 10:03 wrap-up; commits 10:05-10:21
      11:04-11:11  op states the lineup change
      11:20  op: "is this true? I thought we had finalized v10 promotion"   11:25 "you have NOT completed promotion"
      11:24  assistant recommends against cutting the branch; 11:38 op: "unblock the frozen clone so you can cut v10"
      11:42  CONTEXT COMPACTION
      11:45/11:56  op cuts branch; 11:55 FREEZE-V10 commit 09ebc06c; 11:56 worktree/push recovery admitted
      11:52  lineup rev-2 agent (22 min) — premise later found wrong
      12:49-12:53  VRAM arithmetic; "does this account for stt/tts?"; "re-measure vram_non_kv_gib then"
      13:13  block-width fix c0c4db1a; 13:15 sweep instrument agent; 13:32 op: "ratify the freeze then take the stack down"
      13:33  ratified 5a977761; stack down
      13:42-13:52  sweep: zero records (set equality) → fix 0f8b7fae; max_tokens=512 → second abort
      14:01  KV-layers fix 44d7516a (4.06x)
      14:02  op: "are these baselines or max performance decode speeds?"; 14:03-14:05 three TaskStops
      14:06  "a card that also fragments" → 14:07 challenge → 14:08 retraction → 14:18 probe e9ecdda6
      14:08  lineup rev-3 agent (19 min); 14:19 op: "apply the lineup patch and bring the stack up"
      14:20-14:36  9 pipeline runs; parity → numa_config → role_launch_meta → enum → retired role → non-MTP → stale rows → evidence
      14:27  registry reverted by the agent; re-applied
      14:33  op: "do this now" (Flash-Next quality gate)
      14:36  blocked on --allow-descriptor-model-removal (classifier); 14:38 "Stopping the drill"; STACK STILL DOWN
```

## Appendix B — what I ran (all read-only)

- `git log --all --since=2026-09-21 --format=…` in `/workspace`, `repos/epyc-orchestrator`, `repos/epyc-inference-research`; `git show --stat` on `09ebc06c cdaa4dc0 44d7516a 23b148e0 780efcde 0f8b7fae 61364621 c0c4db1a`.
- `git merge-base --is-ancestor 09ebc06c HEAD` / `origin/main`; `git diff origin/main --stat -- <files>` in both clones (local `main` behind).
- `git diff --stat` and `git diff -- orchestration/{launch_manifest,stack_topology}.yaml orchestration/procedures/add_model_to_registry.yaml` in the orchestrator (uncommitted cascade edits).
- `ls .claude/skills/kernel-promotion/scripts` (three scripts; `scope.sh`/`package.sh` absent).
- Transcript parsing (`parse.py`, `ctx.py` in my scratchpad): tool-call counts, `Agent`/`TaskStop`/`SendMessage` calls with timestamps, operator messages, pipeline invocations after 14:19, per-subagent duration/tool counts/handback size from `subagents/agent-*.jsonl`.
- `grep -rn 'master.*lean.*descriptor|compile order'` over docs and orchestrator YAML (compile order is documented).
- Read: `OPERATING_CONSTRAINTS.md`, `SESSION_LIFECYCLE.md`, `kernel-promotion/SKILL.md`, `stack_change_pipeline.py` (run loop), `stack_change_guard.py` (function list), `stack_manifest.py` diffs, `verify_kernel_store.sh`, `verify_llama_cpp.sh`, `ratify_v10_final_freeze_20260922.sh`, the four operator artifacts, `role-alias-change-runbook.md`, `stack-change-launch-runbook.md`, `stack-truth-precedence.md`, `new-model.md`, progress 09-21 and 09-22-kernel-promotion.

Nothing was written outside this file. No process, symlink, registry, or branch was touched.
