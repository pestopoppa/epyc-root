# 2026-08-31 — Disk-reclaim decision package (OP-31)

Read-only investigation, dispatched by the operator during the INF-68 session (array at 98%, 87-90 G
free). Nothing was deleted, moved, or killed. Classification per the operator's three-bucket keep
test (production-registry / novel-under-test: glm-5.3-flash + qwen3.8-next-flash / small smoke
models), against the master registry (`epyc-inference-research/orchestration/model_registry.yaml`,
artifact_status + deletion ledger) and the lean runtime registry (active-role authority). The
operator has stated the excess-model bucket (Tier D) is purgeable **in principle**; the pick-list
below awaits the concrete selection. Structural fact: `/`, `/home`, `/tmp`, `/workspace`, and
`/mnt/raid0/llm` are ONE array — ~316 G lives outside the llm root (`/home` 193 G, `/tmp` 123 G).

## Headline

| Tier | Size | Sign-off needed |
|---|---|---|
| A. RETIRED-per-registry models | ~177 G | none — registry already records retirement |
| B. SAFE-scratch (debris, closed scratch, dup caches) | ~149 G | none |
| C. STALE-candidate (old, unreferenced, mostly gitignored) | ~235 G | operator glance |
| D. CANDIDATE models — registry-known, zero active consumer | ~698 G | operator pick-list (purgeable in principle per operator 2026-08-31) |
| E. NEEDS-OWNER (live sessions / ambiguous) | ~470 G | named owners |
| **A+B+C dispatchable on operator approval alone** | **~560 G** | |

## Tier A — RETIRED-per-registry models (~177 G)

| Path (under `/mnt/raid0/llm/models/`) | Size | Evidence |
|---|---|---|
| `lmstudio-community/Qwen2.5-Coder-32B-Instruct-GGUF` | 51 G | master:878 former coder_escalation, retired |
| `Qwen3.6-27B-MTP-Q8_0.gguf` | 27 G | master:906 — swapped to Qwen3.8-27B-Q8_0 08-20 |
| `supergemma4-26b-abliterated-multimodal-8bit` | 26 G | master:4919 deprecated; vision → Qwen3-VL-30B |
| `nemotron-cascade-2` | 23 G | master:1819 deprecated |
| `unsloth/Qwen3.5-35B-A3B-GGUF` | 18.5 G | superseded as frontdoor 05-04 |
| `Qwable-v1-GGUF` | 17.6 G | ledger says deleted 07-26 — re-appeared 07-28 |
| `lmstudio-community/DeepSeek-R1-Distill-Qwen-14B-GGUF` | 8.4 G | master:5878 records this copy deleted; bartowski Q6_K_L retained |
| `lmstudio-community/Qwen2.5-VL-7B-Instruct-GGUF` | 5.6 G | displaced incumbent 07-31 |

## Tier B — SAFE-scratch (~149 G, highlights)

HF/cache debris bundle ~62 G (byte-verified dups + aborted downloads + pip/fasttext/uv caches) ·
11 abandoned `/tmp` audit worktrees 21 G (08-19→21) · stale kernel trees ~20 G incl.
`llama.cpp-experimental-preserved-20260724…` 14 G (NIB2-66 pre-approves; verify detached/branch
trees are pushed first) · autokernel closed attempts ~20 G (`ak-build` 4.2 G, closed occupancy-v*
attempts, probes/controls/historical) · `llm/tmp` closed scratch ~12 G · models download debris
4.7 G (`.incomplete` stubs only — NOT `.cache/trees/`, registry cites those as provenance) ·
`epyc-orchestrator/core` 1.9 G — the one core dump on the array (policy: NEVER core dumps) ·
misc logs/scratch ~4 G.

## Tier C — STALE-candidate (~235 G, highlights)

Research-repo **gitignored** profile dumps ~120 G (Apr–Jul: `2026-04-24-q8-profile` 51 G,
`op2_…_20260719` 24 G, `cpu_prefill_compute/*` 24 G, BOLT/streaming misc) · two superseded
ROCm-6.2 torch venvs 36 G (`geak-v1-rocm62-py312`, `apex-rocm62-venv`; keep `train-rocm63-py313`) ·
repl_memory `.pre-reseed/.pre-repair` snapshots ~20 G (incl. 8 identical 514 M retries) ·
`/home/node/.codex/sessions/2026/{04..07}` ~15 G (08 is live — keep) · July autopilot checkpoints
10.7 G (production_best → multitier_v10_20260810) · closed audit worktrees 8.6 G + 6.8 G
(**git-registered — remove via `git worktree remove`, never bare rm, never prune**) · `dsenv`
5.2 G (17 months idle) · small residue ~8 G · conditional: non-mains closed-epic worktrees 21.3 G.

## Tier D — CANDIDATE models, zero active consumer (~698 G — pick-list)

| Path | Size | Evidence |
|---|---|---|
| `models/GLM-5.2-UD-IQ2_M/UD-IQ2_M` | **222 G** | master:7642 terminal C-CRAB admission failure; single largest item (note standing OP-8 GO/WAIT/KILL) |
| `models/hy3-angelslim` | 85.5 G | research candidate, never a role; needed patched build recorded ARTIFACT LOST |
| `models/Qwen3.6-27B-Fable-Fusion-711-GGUF` | 56 G | zero registry/script hits |
| Qwen3.6-27B generation (4 loose quants + 35B Q8_0) | ~93 G | generation swapped out 08-20 for Qwen3.8-27B |
| `Qwen3.5-122B-A10B-MTP UD-IQ2_M` 37.6 G · DFlash conversion intermediates 36.8 G · `unsloth/Qwen3.5-27B` 36.5 G · `ThinkingCap-Qwen3.6-27B` 27.1 G · `Nemotron-Nano-9B-v2` 25.4 G · `DeepSeek-R1-Distill-32B` 25 G · gemma-4-26B extra quants 41.6 G + ORIG-Q8_0 25 G · `Qwen3-Next-80B IQ2_M` 24.3 G · ~20 more 5-21 G rows | ~340 G | each registry-checked, none bound to a lean role |

## Tier E — NEEDS-OWNER (~470 G, highlights)

**`/home/node/.local/share/opencode/opencode.db` 186 G** — single SQLite file, 2 live PIDs, written
today; the biggest single lever on the box (VACUUM/session-prune conversation with the opencode
owner) · `/tmp/qwen4exp-builds` 74 G (INF-67 session's debug logs; 70.7 G older than 24 h —
one-line ack prunable) · `hf_models/Ring-mini-linear-2.0` 71 G (sole copy, internally ~33 G
self-duplicate) · live-HF_HOME FP16 Qwen3.5-35B 67 G · registry-vs-disk conflict models 51 G
(Goedel-Prover ledger-spared, root Qwen3-VL-8B smoke-consumed, gemma-4-31B) · pre-consolidation
HF roots ~69 G · claude-backups old tarballs ~22 G (root-owned) · kernel-tree build dirs + loop
scratch ~23 G · orchestrator venv/data adjacents ~22 G.

## Recommended minimal set → ~311 G (no session-owner dependencies)

1. Tier A retired models (8 paths) — 177 G (two already recorded deleted in the ledger).
2. Gitignored profile dumps (3 dirs) — 99 G.
3. 11 abandoned `/tmp` audit worktrees — 21 G.
4. `llama.cpp-experimental-preserved-20260724…` — 14 G (NIB2-66 pre-approved).

Fastest single-decision alternative: **GLM-5.2 (222 G, one dir; interacts with OP-8) + Tier A ≈ 399 G in nine paths.**

## Surprises / follow-ups (independent of space)

1. 186 G `opencode.db` — pathological growth, actively written.
2. ~316 G of the array is outside `/mnt/raid0/llm` (invisible to llm-root `du`).
3. One core dump exists despite policy (`epyc-orchestrator/core`, 1.9 G, 05-28).
4. Registry-vs-disk discrepancies: Qwable re-appeared post-deletion; DeepSeek-14B present though
   recorded deleted; lean registry cites `Qwen3.6-27B-MTP-f16-upcast.gguf` which does NOT exist
   (dangling production citation — worth a handoff).
5. `env.sh` never pins `HF_HUB_CACHE` → already caused a 67 G + 13 G double download.
6. Docker's real root `/mnt/raid0/docker` is on this array but outside the container namespace —
   host-side prune unaudited.
7. claude-backups rotation broken since 08-02 (rsync EPERM) — backup-integrity issue.

## EXECUTED 2026-08-31 (operator approved the minimal set) — ~212 G freed, 87 G → 268 G (93%)

Pre-deletion re-verification caught **4 misclassifications** in the agent's minimal set; the
verified-safe subset was executed, the rest held with evidence:

**Deleted (ledgered in the master registry, one named path at a time, parents verified intact):**
1. `supergemma4-26b-abliterated-multimodal-8bit` (27 G) · 2. `nemotron-cascade-2` (24 G) ·
3. `unsloth/Qwen3.5-35B-A3B-GGUF` (19 G) · 4. `Qwable-v1-GGUF` (18 G — re-execution of the
ledgered 07-26 deletion; the copy had re-appeared 07-28) · 5. `lmstudio-community/DeepSeek-R1-Distill-Qwen-14B-GGUF`
(8.4 G — master already recorded it deleted). Then the three profile-dump dirs via **`git clean -x`
scoped to the exact paths** (~97 G) — NOT `rm -rf`: the dirs contained TRACKED evidence files
(`findings.md`, symbol lists, `commands.txt`) that the menu's "gitignored" claim missed; all
tracked files verified intact after. Then the 11 `/tmp` audit sandboxes (~19 G): 6 were REGISTERED
WORKTREES of the research repo (clean, nothing unpushed, removed via `git worktree remove`), 5
plain dirs via rm.

**HELD — the menu's safety rationale was false for these; they move to the operator pick-list:**
- `models/lmstudio-community/Qwen2.5-Coder-32B-Instruct-GGUF` (51 G): master keeps the
  `qwen25_coder_32b_q4km` launch spec pointing at it ("kept per model_not_role_indexing").
- `models/Qwen3.6-27B-MTP-Q8_0.gguf` (28 G): lean registry names it the ROLLBACK ANCHOR
  ("retained") for the 2026-08-20 coder swap, whose replacement's coder-suite quality is
  explicitly "NOT yet measured".
- `models/lmstudio-community/Qwen2.5-VL-7B-Instruct-GGUF` (5.7 G): lean registry: "Weights REMAIN
  ON DISK; this entry is the rollback target."
- `llama.cpp-experimental-preserved-20260724T135832Z` (14 G): NOT a standalone clone — a
  registered worktree **of the frozen production clone** (`llama.cpp/.git/worktrees/llama.cpp-experimental`),
  and DIRTY (uncommitted mods to ggml-backend/ggml-cpu/ggml-cuda under "Add default-off GDN timing
  hook"). Needs its owner to preserve-or-discard the hunks, then `git worktree remove` from the
  production clone — not a `--force` from an ad-hoc session, NIB2-66 notwithstanding.

Also observed during execution: a live llama-server is now serving the INF-68
`IQ4_XS-uniform` artifact (relevant to OP-30 — someone is already running the uniform file).

## Execution contract (when the operator picks)

Named paths one at a time (no wildcards, no parent-dir `rm -rf`), deletion-ledger entries in the
MASTER registry for every model artifact, `git worktree remove` for git-registered trees (never
prune), verify-pushed before deleting any git tree, and re-`df` after each tier.
