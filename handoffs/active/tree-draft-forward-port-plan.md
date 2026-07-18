# DySpec Tree-Speculation Forward-Port Plan (v6/HIP · MI210)

**Status:** Investigation-only plan (READ-ONLY scan, 2026-07-06). No code edited, nothing built, no inference run. All build/bench steps are RECORDED for the parent to run when the GPU is free.
**Scope:** Bring the DySpec tree-speculation server implementation from `feature/tree-speculation` onto the current v6/HIP experimental llama.cpp so it can be built + benchmarked on the MI210.

---

## 1. Repo / branch topology resolution (the canonical port target)

**All five experimental llama.cpp directories are worktrees of ONE shared bare repo** at `/mnt/raid0/llm/llama.cpp/.git` (confirmed: every dir's `git rev-parse --git-common-dir` resolves to `/mnt/raid0/llm/llama.cpp/.git`; `.git` in each dir is a worktree gitdir file, not an independent clone). They are therefore the **same repository, different branches/worktrees** — not independent clones. Every branch (including `feature/tree-speculation`) is visible and diffable from any worktree.

`git worktree list` (shared repo):

| Worktree | Branch | Tip |
|---|---|---|
| `/mnt/raid0/llm/llama.cpp` | `production-consolidated-v6` | `a30214db1` |
| `/mnt/raid0/llm/llama.cpp-mi210-hip` | `mi210-hip-enable` | `0ebf1b4d7` |
| `/mnt/raid0/llm/llama.cpp-experimental` | `upstream-mtp-verify` | `496e2f098` |
| `/mnt/raid0/llm/llama.cpp-v6-iqk` | `iqk-port` | `91745611f` |
| `/mnt/raid0/llm/llama.cpp-dflash` | `feature/dflash-speculation` | `1ba2140c5` |
| `/mnt/raid0/llm/llama.cpp-v6-f1` | `f1-paged-attn` | `112022a0b` |

**Canonical v6/HIP bench build = `/mnt/raid0/llm/llama.cpp-mi210-hip`, branch `mi210-hip-enable`, tip `0ebf1b4d7`.** Evidence: the HIP binaries this session printed `build: b9777-0ebf1b4d7`; `0ebf1b4d7` is the `mi210-hip-enable` tip; the built binaries under `build-hip/bin/` are timestamped 2026-07-02 20:20, matching commit `0ebf1b4d7` (2026-07-02 20:03). `mi210-hip-enable` diverges from `production-consolidated-v6` by exactly 1↔1 commit (the ROCm≥6.3 fp8-guard commit, duplicated as `a30214db1` vs `0ebf1b4d7`); they are otherwise identical. `llama.cpp-experimental` (branch `upstream-mtp-verify`, tip `496e2f098`) is a DIFFERENT branch used for the dequant/`llama-quantize` step — **not** the bench build. It is not the port target.

> **PORT TARGET (explicit): `/mnt/raid0/llm/llama.cpp-mi210-hip` @ `mi210-hip-enable` (`0ebf1b4d7`).** Do all porting work on this worktree/branch.

**Source branch:** `feature/tree-speculation`, tip `8b59e17087887a5ae8a26ca1e0145fcf2c3c3149` (`8b59e1708`, 2026-03-15), merge-base with the target `137435ff1` (2026-03-03). Confirmed: `merge-base feature/tree-speculation mi210-hip-enable == 137435ff1`; `137435ff1..mi210-hip-enable == 1585 commits`; `137435ff1..feature/tree-speculation == 22 commits`. All context claims verified.

---

## 2. Minimal changeset — what actually IS the DySpec tree port

The 22-commit `feature/tree-speculation` branch is a **feature bundle**, not pure DySpec: it also carries CPU paged-attention (`llama-kv-block.h` +403, `test-kv-block.cpp` +533), layer-skip/early-exit draft, MoE expert-count flag, OpenMP repack, SSM-checkpoint, HSD/freeze-recurrent, and an EPYC toolchain doc (`docs/epyc/`). The `+548`/`+581` figures in the prior scan are the **cumulative** branch diff, not the tree logic. **The actual DySpec tree logic is concentrated in the single tip commit `8b59e1708`.**

**Tip commit `8b59e1708` (`git show --stat 8b59e1708`) — this is the Phase-1 dense port:**

| File | +/− | What it is |
|---|---|---|
| `common/speculative.cpp` | +535 | The DySpec engine: `speculation_tree` struct (`parent[]`, `tokens[]`, `log_probs[]`), `common_speculative_state_tree` class, heap/wave frontier expansion, branching-factor schedule, `get_greedy_path()`, `common_speculative_get_tree()` accessor, `COMMON_SPECULATIVE_TYPE_TREE` enum value + name-map + dispatch |
| `common/speculative.h` | +20 | `speculation_tree` decl + `common_speculative_get_tree()` accessor decl |
| `tools/server/server-context.cpp` | +195 | Phase-3 multi-path target verification (per-path seq_id fan-out, `llama_memory_seq_cp` on target, longest-accepted-prefix win + KV copyback), `n_seq_max = 9*n_parallel` auto-config, `--kv-unified && !has_recurrent` gating |
| `common/common.h` | +3 | `p_split` plumbing (already partly present in v6 — see §3) |
| `common/common.cpp` | +2 | flag default |
| `common/arg.cpp` | +2 | `--draft-p-split` enabled for `LLAMA_EXAMPLE_SERVER` |

**Engine dependency analysis (the crucial finding):** the DySpec algorithm body calls only **stable, unchanged llama-level primitives** — `llama_batch_init/free`, `llama_decode(ctx_dft, batch)`, `llama_memory_seq_cp(mem_dft, …)` (forks draft-side KV per tree node), `llama_get_logits_ith`, `llama_sampler`, `llama_n_ctx/n_batch`, `std::log` + a `priority_queue`-style max-heap. **The tree-construction algorithm is portable as-is.** What is NOT portable is the *wrapper*: the branch's `common_speculative_state` polymorphic base class + `common_speculative_config` config-vector dispatch, which v6 deleted and replaced (see §3). Also: the engine calls `common_speculative_are_compatible(model_tgt, model_dft)` — **this helper already exists in v6** (`common/speculative.cpp:56`), so that dependency is satisfied.

**One cross-commit dependency:** the tip's server gate uses `llama_memory_has_recurrent(llama_get_memory(ctx))`, a C API added by the *earlier* SSM-checkpoint commit `dabbb4036`, not by the tip. For the Phase-1 dense port this can be trivially replaced by v6's existing memory-type introspection (or a hard `false` for the dense-only path) — it is not a blocker.

**Recurrent enabler (Phase 2) = two separate commits, NOT the tip:**
- `dabbb4036` "SSM state checkpointing" — adds `llama_memory_has_recurrent()`, `llama_memory_checkpoint_save/restore/free()`, hybrid delegation, server checkpoint-before-draft/restore-on-reject.
- `3d8a9358a` "HSD + freeze-recurrent" — adds `llama_set_freeze_recurrent()`, guarded recurrent-state writes in `qwen35/qwen35moe/qwen3next`.

**Context correction:** the prompt's `llama_memory_recurrent_clone_cell` symbol **does not exist anywhere in the branch** (`git grep clone_cell feature/tree-speculation` → empty). The recurrent mechanism is `llama_memory_seq_cp` (dense KV fork) + `checkpoint_save/restore` (recurrent state) + `freeze_recurrent` — there is no "clone_cell" API.

---

## 3. Conflict map (per-file, with evidence)

Commit counts = `git rev-list --count 137435ff1..mi210-hip-enable -- <file>` (how far v6 moved each file since the merge-base).

| File | v6 commits since base | Classification | Evidence / why |
|---|---|---|---|
| `common/speculative.cpp` | **27** | **HEAVY — reimplement** | v6 replaced the entire spec subsystem. Old branch: `common_speculative_state` virtual base + `common_speculative_config` vector dispatch + `COMMON_SPECULATIVE_TYPE_{DRAFT,EAGLE3,NGRAM_*,TREE}`. v6: `common_speculative_impl` base (`common/speculative.cpp:129`) with pure-virtual `begin/process/draft(dparams_vec)/accept` + native MTP/NEXTN embd hooks (`need_embd_nextn`); subclasses `_draft_simple` (:175), `_draft_eagle3` (:419), `_draft_mtp` (:896). The DySpec engine must be rewritten as a new `common_speculative_impl_draft_tree` subclass; the algorithm body drops in, the wrapper does not. |
| `tools/server/server-context.cpp` | **93** | **HEAVY — reimplement** | v6 server refactored into a `begin→process→draft→accept` lifecycle: `common_speculative_init` (`:1324`), `common_speculative_begin` (`:3809`), `common_speculative_process` (`:710`,`:3720`), `common_speculative_draft` (`:3023`), `common_speculative_accept` (`:3934`), KV via `common_context_seq_cp` (`:675`,`:679`). Server dir also gained new files (`server-chat.*`, `server-schema.*`, `server-tools.*`, `main.cpp`). The tip's +195 Phase-3 block was written for the old inline draft/verify loop and must be rebuilt against this lifecycle. |
| `common/common.h` | 51 | **MODERATE** | v6 already defines the enum here (`:159–169`, `NONE…NGRAM_CACHE, COUNT`) and already has `float p_split = 0.1f` under `speculative.draft` (`:315`). Add one enum value `COMMON_SPECULATIVE_TYPE_DRAFT_TREE` before `_COUNT`. |
| `common/arg.cpp` | 71 | **CLEAN / maybe untouched** | `--draft-p-split` already exists in v6 (`:3561`, writes `params.speculative.draft.p_split`). No new flag needed if gating via `--spec-type draft-tree` (preferred — see §Flag-gate). |
| `common/speculative.h` | 9 | **MODERATE** | Add a `common_speculative_get_tree()`-equivalent accessor decl if the server needs the tree for multi-path verify; otherwise header change is minimal (impl is internal to the `.cpp`). |
| `common/common.cpp` | 28 | **CLEAN** | trivial default plumbing. |
| **Phase-2 files:** | | | |
| `src/llama-memory-recurrent.cpp/.h` | — | **MODERATE** | v6 **has** the primitives: `seq_cp` (`:235`/`.h:47`) and `state_write`/`state_read` (`:736`/`:816`). It **lacks** `checkpoint_save/restore/free` — re-add on top of the existing state serialization. |
| `include/llama.h` | — | **CLEAN** | add C API decls (`llama_memory_has_recurrent`, `llama_memory_checkpoint_*`, `llama_set_freeze_recurrent`); v6 has none of these today. |
| `src/models/qwen35.cpp`, `qwen35moe.cpp`, `qwen3next.cpp` | — | **HEAVY** | v6's GDN consolidation reworked these; the freeze-recurrent guarded-write hunks from `3d8a9358a` will conflict and need re-fitting to v6's model graph. |
| `src/llama-context.cpp`, `src/llama-memory-hybrid.*` | — | **MODERATE** | checkpoint/freeze wiring re-fit. |

**Flag-gate (§5 answer, cited):** do **NOT** reuse `p_split>0` — in v6 `p_split` already defaults to **0.1** (`common/common.h:315`) and is already consumed by the linear draft acceptance path, so `p_split>0` is true by default and would silently perturb the incumbent. Instead gate on the spec-type enum: add `COMMON_SPECULATIVE_TYPE_DRAFT_TREE` to `common/common.h:159`, add `{"draft-tree", COMMON_SPECULATIVE_TYPE_DRAFT_TREE}` to the name-map at `common/speculative.cpp:25–33`, register the impl in the type→impl factory inside `common_speculative_init`, and select via `--spec-type draft-tree`. The type list defaults to `{ COMMON_SPECULATIVE_TYPE_NONE }` (`common/common.h:357`), so the tree path is **OFF unless explicitly requested** and cannot perturb the linear/MTP/EAGLE3 paths.

---

## 4. Phased plan

### Phase 1 — Dense / non-recurrent tree (the easy, testable-on-qwen-dense milestone)

Port the tip commit `8b59e1708` logic as a new v6 spec-impl. Recommend two sub-milestones:

- **Phase 1a — tree draft + greedy-path via the EXISTING linear verifier (smallest landing).** Build the DySpec tree on the draft side, but submit only `get_greedy_path()` (top-1-at-each-depth, "guarantees ≥ linear") through v6's unchanged verify path. This touches only `common/speculative.cpp` + `common/common.h` (+ header). No server-verify surgery. Lowest risk; isolates the engine port from the server rewrite. Expected gain is modest but non-negative.
- **Phase 1b — multi-path target verification (the +15.8% mechanism).** Rebuild the tip's Phase-3 server block against v6's `begin/process/draft/accept` lifecycle: fan each root-to-leaf path into its own target `seq_id`, batch-decode all paths, pick longest accepted prefix, copy winning path KV back via `common_context_seq_cp`. Set `n_seq_max = 9*n_parallel` when tree active. This is the invasive part.

**Files to touch:** `common/speculative.cpp` (new `common_speculative_impl_draft_tree` subclass — heap/wave algorithm lifted from `8b59e1708`, re-shaped to write into `common_speculative_draft_params_vec`), `common/common.h` (+1 enum value), `common/speculative.h` (tree accessor for 1b), `tools/server/server-context.cpp` (Phase 1b only). 
**Expected conflicts:** speculative.cpp = mechanical reimplementation against the new base class (not a patch-apply); server-context.cpp = Phase-1b reimplementation. Phase 1a should be near-clean.
**Flag-gate:** `--spec-type draft-tree` (OFF by default), as in §3.
**Build (parent runs when GPU-free):**
```
cmake --build /mnt/raid0/llm/llama.cpp-mi210-hip/build-hip --target llama-server -j
```
**A/B test recipe (parent runs; production sampling temp 0.2 + seed 42, on qwen dense):**
- Target: `/mnt/raid0/llm/models/Qwen3.6-27B-MTP-Q8_0.gguf` (dense, arch `qwen35`) — or `Qwen3.5-27B-MTP-Q4_K_M.gguf`. f16/Q8_0 favor tree; Q4_K_M was net-negative in the original bench, so prefer Q8_0/f16 for the first read.
- External drafter: `/mnt/raid0/llm/scratch/n5/Qwen3.5-0.8B-Q8_0.frontdoor-specials.gguf` (`-md`) — see §5 (pre-tokenizer matches the target).
- Three arms, same prompt set + temp 0.2/seed 42:
  1. **plain** — no spec (`--spec-type none`), roofline.
  2. **MTP incumbent** — `--spec-type draft-mtp`, embedded MTP head (use the `-MTP` gguf, no `-md`).
  3. **tree** — `--spec-type draft-tree -md <0.8B drafter> --draft-p-split 0.1 --kv-unified`.
- Report t/s + acceptance length; **pair every speed number with a correctness/garbage check** (per MEASUREMENT policy). Run under the codified canonical recipe with operator approval.

### Phase 2 — Recurrent clone-cell / checkpoint for the GDN leg

Re-enables tree (greedy-path only — multi-path Phase-3 is explicitly dense-only, `!has_recurrent`) on hybrid SSM/GDN targets (Qwen3.5-9B, Qwen3.6-35B-A3B).

**Files to touch:** re-port `dabbb4036` + `3d8a9358a` onto v6 — `src/llama-memory-recurrent.cpp/.h` (add `checkpoint_save/restore/free` on top of existing `state_write`/`state_read`), `src/llama-memory-hybrid.*` (delegate to recurrent sub-memory), `include/llama.h` (add `llama_memory_has_recurrent`, `llama_memory_checkpoint_*`, `llama_set_freeze_recurrent`), `src/llama-context.cpp`, `src/models/qwen35.cpp`/`qwen35moe.cpp`/`qwen3next.cpp` (freeze-recurrent guarded writes), `tools/server/server-context.cpp` (checkpoint-before-draft / restore-on-reject).
**Expected conflicts:** HEAVY on the three qwen GDN model files (v6 reworked them post-GDN); MODERATE on the recurrent/hybrid memory layer (primitives exist, API is additive). The underlying `seq_cp` + `state_write/read` hooks **do exist** in v6's recurrent layer, so the checkpoint API is buildable — feasibility is real but the model-file re-fit is the cost.
**Flag-gate:** same `--spec-type draft-tree`; on a recurrent target the impl auto-falls-back to greedy-path + checkpoint (must NOT set `--kv-unified` on hybrid — it breaks recurrent state).
**Build + A/B:** same build command; A/B target `/mnt/raid0/llm/models/Qwen3.5-9B-MTP-GGUF/Qwen3.5-9B-Q4_K_M.gguf` (GDN hybrid) vs its MTP incumbent, drafter = the 0.8B qwen35 drafter, temp 0.2/seed 42.

---

## 5. Qwen drafter resolution (embedded-MTP vs external drafter + vocab-compat)

**DySpec builds its tree from an EXTERNAL drafter model (`-md` → `ctx_dft`), not the embedded MTP head.** Evidence: the `common_speculative_state_tree` ctor takes both `ctx_tgt` and `ctx_dft`, runs `llama_decode(ctx_dft, …)` for frontier expansion, and forks per-node KV with `llama_memory_seq_cp(mem_dft, …)`. The embedded MTP head is a *separate* v6 impl (`common_speculative_impl_draft_mtp`) with no tree branching. So the tree arm needs a small external Qwen drafter; the MTP arm is the incumbent it competes against.

**Vocab-compat (GGUF header scan, no model load — `strings` over first 3 MB):**

| Model | arch | tok model | tok pre |
|---|---|---|---|
| `Qwen_Qwen3-0.6B-Q8_0.gguf` (drafter) | qwen3 | gpt2 | **qwen2** |
| `Qwen3-1.7B-Q8_0.gguf` (drafter) | qwen3 | gpt2 | **qwen2** |
| `scratch/n5/Qwen3.5-0.8B-Q8_0…gguf` (drafter) | qwen35 | gpt2 | **qwen35** |
| `Qwen3.5-27B-MTP` / `Qwen3.5-9B` / `Qwen3.6-27B-MTP` (targets) | qwen35 | gpt2 | **qwen35** |
| `Qwen_Qwen3.6-35B-A3B-Q8_0` (MoE target) | qwen35moe | gpt2 | **qwen35** |

**Verdict:**
- **Use `scratch/n5/Qwen3.5-0.8B-Q8_0` as the drafter** — same arch family + **identical `tokenizer.ggml.pre=qwen35`** as every qwen35/3.6 target. Strong compatibility; the natural choice. **[verified at header level; full n_vocab/merges identity still gated by runtime `common_speculative_are_compatible`, which the engine calls anyway.]**
- **Qwen3-0.6B / 1.7B carry `pre=qwen2`, a mismatch vs the target's `pre=qwen35`.** The Qwen3→3.5 series is widely believed to share the 151,936-token vocab, but the pre-tokenizer relabel is a yellow flag and byte-identity of merges is **UNVERIFIED** from headers. Only use these if runtime `are_compatible` passes. **[unverified]**
- **Watch-out:** `qwen3.5-35b-a3b-seal-concise.gguf` is a **control-vector GGUF (`general.architecture=controlvector`), not model weights** — do not use it as a target.

---

## 6. Risks / bottom-line

**Honest effort estimate: this is a multi-day reimplementation, not a patch-apply — but it is well-bounded.**

- **Not a cherry-pick.** v6 rewrote the spec subsystem (old `common_speculative_state`/config-vector → new `common_speculative_impl` `begin/process/draft/accept` + MTP/NEXTN embd hooks) and refactored the server (93 commits on `server-context.cpp`). `git cherry-pick 8b59e1708` will not apply; the +535 engine and +195 server block must be **re-expressed** against the v6 API.
- **De-risking is real, though.** The DySpec *algorithm* uses only stable llama-level primitives (`llama_decode`, `llama_memory_seq_cp`, samplers), and v6 already ships the two dependencies the engine needs: `common_speculative_are_compatible` (present) and recurrent `seq_cp`/`state_write/read` (present). The port is "re-shape a self-contained algorithm into a new subclass," not "invent new mechanics."
- **Effort:** **Phase 1a** (tree-draft + greedy-path via existing linear verify) ≈ **~1 day** — engine subclass + enum + flag, minimal server touch; buildable + A/B-able quickly, and it already "guarantees ≥ linear." **Phase 1b** (multi-path target verify against v6's server lifecycle) ≈ **~2–3 days** and is where the +15.8% lives and where the risk concentrates. **Phase 2** (recurrent checkpoint/freeze for GDN) ≈ **~2–4 days**, dominated by re-fitting the freeze-recurrent hunks onto v6's reworked qwen35/moe/next model graphs; and even done, tree on GDN is greedy-path-only (multi-path is dense-only by design), so the payoff is capped.
- **Biggest single risk:** the Phase-1b multi-path verify rewrite inside v6's refactored server loop (`server-context.cpp`, 93 commits of drift) — this is the hardest conflict surface and the correctness-sensitive one (KV copyback, seq_id budget, `kv_unified` interaction).
- **Recommendation:** land **Phase 1a first** (fast, low-risk, testable on qwen dense with the 0.8B/qwen35 drafter), measure, then decide whether Phase-1b's +15.8% justifies the server surgery before touching the GDN leg at all.

---

## Phase 1a RESULT (2026-07-06) — engine VALIDATED; lever uncompetitive vs MTP on MTP-equipped targets

Built into the **v7-candidate** kernel (fresh v6+iqk + 4 GPU opts + tree-draft, commit `46f876c12`; clean build, iqk+opts+tree-draft all compiled in). A/B on qwen 27B dense Q8 (external 0.8B qwen35 drafter, temp0.2 seed42, GGML_CUDA_Q8_PREFETCH=1). OBSERVATION.

| arm | t/s | draft_n | accepted | α |
|---|---|---|---|---|
| plain | 31.17 | 0 | — | — |
| draft-simple (0.8B ext) | 18.60 | 235 | 176 | 0.749 |
| draft-TREE (greedy) | 17.42 | 235 | 176 | 0.749 |
| MTP-incumbent (embedded) | **41.89** | 252 | 170 | 0.675 |

- **Engine CORRECT:** draft-tree == draft-simple bit-for-bit on draft_n/accepted/α/output — the Phase-1a greedy-path collapse works exactly as designed; the port is sound; `--spec-type draft-tree` is accepted; coherent output. Phase 1a milestone ACHIEVED.
- **Practical finding (NEGATIVE for MTP-equipped targets):** external-drafter spec-dec (simple AND tree) is **net-negative vs plain** (18 < 31) — the 0.8B drafter overhead isn't repaid on the fast Q8 decode. The **embedded MTP dominates** (41.9, +34% vs plain) because its head is near-free. Phase-1b's +15.8%-over-linear → ~21.5 t/s, still < plain and << MTP.
- **Implication:** tree-draft cannot beat MTP on our MTP-equipped production targets. Its only niche = **non-MTP targets** or **f16** (where the original +15.8% was measured, decode more BW-bound). **Phase 1b decision reopened** — not worth 2-3 days for production targets unless a non-MTP/f16 use case is in scope. NOT a hard close (f16 + a cheaper drafter untested).
- **v7-candidate kernel reconciliation DONE + validated** — see [kernel-reconciliation-audit.md](../completed/kernel-reconciliation-audit.md); branch `experimental-v7-candidate` in llama.cpp-experimental is the full build (v6+iqk+GPU-opts+tree-draft), compiles/links clean on HIP.

---

## GLM-5.2 CHECK + FINAL SHELVE DECISION (2026-07-06) — tree-draft SHELVED; native-GLM-MTP is the better future lever

Operator asked whether GLM-5.2 (the last candidate niche) lacks an MTP head, which would justify tree-draft. Investigated (on-disk metadata + fork source + upstream):
- **GLM-5.2 DOES ship a native MTP/NEXTN head** — the GLM-MoE family carries it; converter `conversion/glm.py` reads it with `skip_mtp=False`; upstream has the NEXTN tensor loaders; GLM-5.2 arch = `GlmMoeDsaForCausalLM`. So MTP dominates an external drafter there too.
- **BUT GLM's MTP head is an INERT STUB on our fork** — `src/models/glm4-moe.cpp` / `glm-dsa.cpp` LOAD the NEXTN tensors but SKIP them in the forward pass ("preserved but unused"); the functional MTP draft driver (`common/speculative.cpp`) is qwen35/qwen35moe-only. GLM has no *working* spec-dec today.
- **GLM-5.2 not runnable yet** — DSA-gated (PR#21149, dense-MLA fallback), 238 GB IQ2 parked, not on disk (only GLM-4.7-Flash present = `deepseek2` arch, no nextn head).

**DECISION: tree-draft Phase 1b SHELVED (conclusive).** Every target on our stack (qwen 27B/35B/122B, gemma, GLM-5.2) ships an MTP head; external-drafter tree-draft is dominated by MTP everywhere (measured: qwen-27B MTP 41.9 vs external-draft ~18 < plain 31). The Phase-1a engine is **validated + banked in the v7-candidate** — cheap to revive if a genuinely MTP-less target ever appears.

**Higher-value FUTURE lever surfaced (flag, do NOT drop — research-intake rule):** finish the **native GLM MTP forward graph** — it is ~90% scaffolded (tensors load, `skip_mtp=False`, the draft driver already supports `draft-mtp`; only the glm4moe/glm-dsa NEXTN *forward execution* is stubbed — a bounded port like qwen35's, which delivers +58–89% in prod). This is the right GLM-5.2 spec-dec investment, gated on GLM-5.2 becoming runnable past the DSA gate (PR#21149).

**2026-07-18 gate update (v7 lever audit).** The PR#21149 runnability gate is **stale/superseded**:
generic DSA landed via upstream #23346 and GLM-5.2 DSA cache/runtime is wired on experimental
v7 `3dee86a5a` (GLM-5.2 UD-IQ2_M loads + engages DSA). So runnability is **no longer** the
binding gate. The binding gate is now **GLM task-quality re-clear**: patch-review still
over-approves (FA up to 91.7%; GC-shadow-repair4a narrowed it but exposed a label-audit
blocker → **GC-shadow-repair4b** open in [glm52-reviewer-capability-gates.md](glm52-reviewer-capability-gates.md)).
**Do NOT spend the native-GLM-MTP port (or the real sparse final-attention path,
[llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md) D2) before GC-shadow-repair4b →
P-REV-1 clears** — the flagship GLM role (cross-family patch reviewer) is unfunded until then,
so kernel spend on a model that can't yet do its job has near-zero EV. Once quality clears, the
native-GLM-MTP port is the single highest-EV GLM acceleration lever (+34–89% decode on a
~2.5 t/s model).

## Progress checklist

- [x] Investigation complete - tree-draft Phase 1b SHELVED (uncompetitive vs MTP) ✅
- [ ] **Native GLM MTP forward-graph port** (~10% remaining: wire the already-loaded NEXTN tensors into `glm4-moe.cpp`/`glm-dsa.cpp` forward + expose the embd/nextn hooks the `draft-mtp` driver consumes; model on qwen35's NEXTN forward). **GATED behind GLM quality re-clear (GC-shadow-repair4b → P-REV-1)**, then measure α. EV +34–89% decode.
