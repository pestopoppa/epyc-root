# Fold plan: INF-70 CPU kernel work → the AutoKernel champion aggregate (2026-09-07)

Read-only investigation (subagent, 2026-09-07) into folding `inf70-audit`'s CPU kernel work for
Qwen3.8-Flash-Next (qwen4exp) into THE champion (`ak/champion/llama-cpp-0db32c06e3e5`) so
promotion ships ONE full candidate build. Owning program: `handoffs/active/autokernel-champion-aggregate.md`.

## Headline findings
1. **Same lineage — a normal aggregate merge, not a base fold.** `inf70/champion` forked from `270b48ed6`,
   a commit ON the champion branch. Merge-base with the live tip `fe881991f` is `270b48ed6`, not v9.
2. **Textually clean.** Only `ggml/src/ggml-cuda/ggml-cuda.cu` is touched on both sides since the fork,
   in different hunks. `git merge-tree 270b48ed6 fe881991f 6f032c48d` → **0 conflict markers**.
3. **Two default-ON blockers on the CPU side must be fixed BEFORE the fold** (invisible to the loop's
   gates, which measure a dense 27B):
   - `GGML_OP_MOE_TOPK_NORM` (`ae6031aaa`): fleet-wide MoE op, **no CUDA/HIP kernel, no
     test-backend-ops case**. On the HIP build every GPU-served MoE model falls back to CPU per layer,
     splitting the graph and defeating HIP-graph capture. CPU benefit only "+1.4% pp512". → opt-in.
   - INF-64 fused decoder (`src/models/qwen4exp-fused.cpp`): **default-ON** (`supports_fused_decode()
     { return true; }`, opt-OUT via `GGML_FUSED_DECODE_OFF`) yet ledger-classified **NO-GO** (~3.9×
     slower, MoE NaN open) and **every INF-70 measurement was taken with it OFF**. → opt-in or drop hook.
4. **Operator-state conflict:** INF-70 ledger records PROD-2 *"DEFERRED BY THE OPERATOR 2026-09-06:
   'we're not folding into autokernel champion just yet.'"* The 2026-09-07 request reverses it; the
   reversal must be written into the ledger by `inf70-audit`, not inferred.
5. **Run 29 is live on champ2.** The fold must happen with the loop verified dead (it builds the
   anchor from champ2's tree and takes champion_commit from champ2 HEAD).

## 1. Inventory — fold candidate `inf70/champion @ 6f032c48d`
Clone `/mnt/raid0/llm/llama.cpp-cpu-fusion-20260829` (private, **unpushed**), worktree
`/mnt/raid0/llm/worktrees/inf70/champion`. 86 commits vs fork, ~101 files, +9.2k/−325.

**[A] Landed, measured, validated → fold** (bit-identical unless noted; ledger refs in the INF-70 handoff):
| Lever | Commit | Effect |
|---|---|---|
| D6-PLACE `GGML_NOHUGEPAGE` (madvise) | `29a5857ac` | **+35.21% served 15/15; +32.21% plain** |
| SYNC-10 `GGML_ROWCOL_SPLIT` | `2af8669ce` | +3.05% alone; +5.3% in champion |
| SYNC-2 `GGML_TINY_SOLO` | `1150140fe`,`3713f02a0` | +3.86% plain alone; ×1.0053 in champion |
| SYNC-9 `GGML_EMPTY_SKIP` | `226847752`,`20db1a5ab` | ~null |
| D8 GET_ROWS (row,col-chunk) | `bc2834a9b` | 95.5→83.4 ms/token |
| D7a CONCAT dim-0 partition | `3026caac4` | pp512 +28.2% |
| B3-k `GGML_MMID_SLAB` | `5eb7d5f05` | +3.07% bench / +3.9% served |
| D1 no batch-1 barrier | `664096408` | null (base for B3-k) |
| **P0** IQ4_XS stays on direct iqk (repack at Ny≥32 was WRONG) | `99425578d` | long-prompt garbage → coherent 27/27 |
| BE-1 `GGML_ROWEXACT_N` | `db6b715c9` | lossless mode; OFF by design |
| E2 MTP draft head port | `d83f63a45` | 23.16 t/s, 1.876× |
| E2b-2 recurrent-state rollback | `4595b1bca`,`077123843`,`8136b3221`,`540b1e697` | checkpoints 407/113 → 0/0 |
| BE-2 `GGML_FA_SPLIT_KV` knob | `c51e4dabf` | knob; `=0` free under MTP |
Combined claim (`6f032c48d`): **MTP served 23.870 → 35.407 t/s (1.4834×, 60/60); plain 12.778 →
21.638 (1.6934×); 1,457 greedy tokens 7/7 sha256-identical.** Baseline is pristine `c51e4dabf`, **not
v9** — a v9 CPU comparison is still owed.

**[C] NO-GO / neutralise before fold:** INF-64 fused decoder (default-ON), `GGML_OP_MOE_TOPK_NORM`
(fleet-wide, no HIP kernel), `GGML_VEC_SIGMOID` (already OFF), diagnostic envs in hot paths (inert),
`ggml-alloc.c` stray `AT_PRINTF` define.
**[D] NOT in 6f032c48d — exclude from this fold:** CHAMP-2 `df0f37c62` (PR_SET_THP_DISABLE, unmeasured),
SYNC-15 `56fe8ef0a`, sync12/14, B4 quantizer patch (artifact tool), diag branches.
**[B] Launch recipe production needs alongside (PROD-1 must codify):** `taskset -c 0-95 numactl
--interleave=all`; OMP PLACES=cores PROC_BIND=spread WAIT_POLICY=active; `GGML_IQK=1`; `-t 48`;
`--no-mmap`; `-fa on`; `GGML_FA_SPLIT_KV=0`; KV f16 (never quantise); `--spec-type draft-mtp
--spec-draft-n-max 4 --spec-draft-p-min 0.5` + the MTP head GGUF; per-node page-cache pre-eviction;
artifact `IQ4_XS-uniform-r16`.

## 2. Overlap / conflict
Same lineage (fork `270b48ed6`). Champion since fork: 24 commits, 10 files, all `ggml-cuda/*` +
`ggml-hip/CMakeLists.txt`. Shared file: `ggml-cuda.cu` only, disjoint hunks, merge-tree 0 conflicts.
Semantic checks (not textual): `ggml-alloc.c` changes are global (→ GPU gates must run);
`ggml_ssm_scan` +K across backends (→ `test-backend-ops -b ROCm0 -o SSM_SCAN`); new `GGML_OP_*` enum
entries shift values (→ full rebuild, `verify_ggml_linkage.sh`, no ABI mixing).

## 3. Fold mechanism
**`git merge --no-ff inf70/champion INTO ak/champion` in champ2** (not rebase — the ledger cites 86
hashes; not the reverse — violates ONE champion). Precedent: the a27287015 / CH-7 reconcile.
0. (`inf70-audit`, own branch, no loop stop) fold-ready commit on `6f032c48d`: MOE_TOPK_NORM opt-in
   (or CUDA impl + test), fused-decode opt-in, alloc define; re-run bit-identity + `test-backend-ops
   -b CPU`; record PROD-2 un-deferred; **push the branch** (private clone today).
1. Stop run 29 at a boundary (STOP file / SIGTERM; drain; verify dead). NOTE: the in-process bundle
   (2 keeps, +3.01%) is lost on restart — time after a serving fire or accept.
2. champ2: `git tag ak/pre-inf70-fold-20260907 <tip>`; `git fetch <clone> inf70/champion:refs/heads/
   inf70/champion-fold`; `git merge --no-ff inf70/champion-fold`. Rollback: `git reset --hard <tag>`.
3. House-recipe HIP build (fresh dir) + CPU-only build of the same tree.
4. Gates (§4). 5. Relaunch with `--anchor-build <new build> --allow-unverified-anchor` (not an
   `anchor-gen-*` name). The object-digest guard legitimately changes (ggml-cpu objects) — anchor and
   scratch both rebuild from the new tip, so it verifies.

## 4. Validation (before promotable) — both backends, SAME merged tree
Correctness: `test-backend-ops -b ROCm0` (full, `-o MUL_MAT`, `-o SSM_SCAN`) and `-b CPU` (fail set ==
HYG-3 baseline); greedy bit-identity CPU qwen4exp 40/90/200×256 plain+MTP vs `6f032c48d` (7/7); GPU
DFlash2 greedy parity (DF2-6); `verify_ggml_linkage.sh`.
GPU vs v9 and vs pre-fold: tg128 20 pairs merged vs anchor-gen-020 (within 0.638%); headline vs v9;
`serving.compare` under `qwen3.8-27b-q8-gpu-dflash2-np4` (floor 3.536%); DF2-10 smoke; DF2-5 grid;
**+ one GPU MoE production model** tg128 + coherence + HIP-graph capture (the fused MoE op the loop's
dense 27B never exercises).
CPU vs v9 (10125) and vs `6f032c48d`: codified recipe only (`canonical_recipe.py` + `bench_canonical.sh`,
MEASUREMENT_POLICY §37-38/54-55); served ABA harness (`/mnt/raid0/llm/tmp/inf70/reanchor2/`) 24-prompt
mix ≥3 rounds plain+MTP — expect ≈35.4 MTP / ≈21.6 plain; coherence by reason at 54-682-tok prompts;
**run with the merged tree's defaults (no `GGML_FUSED_DECODE_OFF`)** to prove the default path is the
measured path; one other served CPU model v9-vs-merged (the levers are model-agnostic, default-ON).

## 5. Risks
| # | Risk | Recommendation |
|---|---|---|
| 1 | `MOE_TOPK_NORM` fleet-wide, no HIP kernel, invisible to loop gates | Blocker: opt-in before fold; add MoE GPU gate |
| 2 | Fused decode default-ON, NO-GO, never measured ON | Blocker: opt-in or drop hook before fold |
| 3 | PROD-2 operator deferral (09-06) vs today's request | `inf70-audit` records the reversal; operator confirms |
| 4 | Ownership: CPU branch = `inf70-audit`; champ2 = loop owner | inf70-audit preps fold-ready + CPU gates; champion owner executes STOP→merge→build→GPU gates→relaunch; coordinate via bus |
| 5 | Restart wipes the 2-keep bundle | Time after a serving fire, or accept |
| 6 | Private unpushed clone | Push `inf70/champion` first |
| 7 | CHAMP-2 / SYNC-15 / B4 outside candidate | Exclude; re-fold at next boundary |
| 9 | 35.4 headline is vs pristine, not v9 (+~9% unexplained cross-day drift) | v9 CPU comparison mandatory before any promotion claim |
