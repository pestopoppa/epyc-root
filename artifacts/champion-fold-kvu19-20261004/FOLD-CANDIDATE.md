# FOLD-CANDIDATE: KVU-19a + KVU-19b commit 1 into the ONE champion

Prepared and verified 2026-10-04 by a fold subagent. **workspace-ec (KV-kernel owner) reviews this and moves the
champion ref itself.** Nothing here has moved `ak/champion/llama-cpp-ffc1bac82eec` or written
`/mnt/raid0/llm/autokernel/loop-memory`.

## 1. Candidate

| | |
|---|---|
| **candidate sha** | **`1bceceb0514d423ad220888313eafcddc30e485e`** (build 10311) |
| branch | `fold/champion-kvu19-20261004`, pushed to `fork` (github.com/pestopoppa/llama.cpp) |
| worktree | `/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/src` (linked worktree of `/mnt/raid0/llm/llama.cpp`, clean) |
| base = champion tip | `90c12df4247e417053ffc59e2188294826d04ca2`, local and `fork`. Re-resolved at 05:1xZ and again at hand-off (§9). |
| relation | **fast-forward** of the champion: `90c12df42` is the parent of `ac97e305a` |

Cherry-picks, in order, with `git cherry-pick --ff`. Every pick's parent was already HEAD, so git fast-forwarded and
**kept the original shas**. The candidate is therefore byte-for-byte the commits the KVU-19a/19b evidence was made on:

| # | sha | what | files |
|---|---|---|---|
| 1 | `ac97e305a26a11b1bf486d8c9118f4633011a01a` | KVU-19a GPU: skip fully masked KV blocks in FA (unified KV), + `test_flash_attn_ext_unified` (52 cases) | `ggml-cuda/fattn-{common,vec,tile,mma-f16}.cuh`, `fattn-wmma-f16.cu`, `tests/test-backend-ops.cpp` |
| 2 | `a0d0ae238e714aaab04e973ef4b5a4b7c9917744` | KVU-19a CPU: 64-cell -INF run tests in FA | `ggml-cpu/ops.cpp` |
| 3 | `1bceceb0514d423ad220888313eafcddc30e485e` | KVU-19b commit 1: one query row per block for batched decode across sequences (`ggml_flash_attn_ext_{set,get}_n_seq` hint, `GGML_CUDA_FA_SEQ_ROWS`) + 29 hint test cases | `ggml.h`, `ggml.c`, `src/llama-graph.cpp`, `ggml-cuda/fattn*.cu[h]`, `tests/test-backend-ops.cpp` |

KVU-19a is a single GPU commit plus a single CPU commit, so nothing else needed folding.

**Not folded:** `c7f5ac9ad` (KVU-19b commit 2, WMMA sequence tiles, `flash_attn_plan_seq_tiles`). It is on hold. One
reason that bears on the hold: in the KVU-19b GPU slot (`fa-maskskip-batched-20261004/slot2-20261004T044448Z/exact.txt`)
the c7f5ac9ad build broke the skip-on == skip-off invariant on 6 cases (110/111/118/119/126/127: hs=128, 8 rows per
sequence, WMMA seq tiles; nmse ≤ 8.3e-10). The same comparator (`cmp_fold.py`) passes the commit-1-only layouts.

**Conflicts: none.** The champion has not moved since 19a was based (`ac97e305a`'s parent is `90c12df42`), so no
resolution was needed, minimal or otherwise. Combined diff vs the champion: 11 files, +744/-36.

## 2. Builds (store, champion recipes, all under region-lock 0-95 / nice 19 / ionice idle / -j24)

Script: `/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/build_store.sh`. It copies the KVU-19b `build_store.sh`
verbatim, changing only `SRC` and `taskset` (to the locked 0-95 region).

| build | recipe | built | result |
|---|---|---|---|
| `/mnt/raid0/llm/kernels/builds/gpu-20261004-1bceceb05` | gfx90a-house-v1 (`GGML_HIP=ON`, gfx90a, `GGML_HIP_ROCWMMA_FATTN=ON`, native, `$ORIGIN;/opt/rocm/lib`) | 06:27:38-06:29:07Z | OK, `version: 10311 (1bceceb05)` |
| `/mnt/raid0/llm/kernels/builds/cpu-20261004-1bceceb05` | native-openmp-gcc15-cpu-v1 (gcc-15, OpenMP, native, `LLAMA_CURL=OFF`, `$ORIGIN`) | 06:29-06:31Z | OK, `version: 10311 (1bceceb05)` |

- **Recipe parity.** The CMakeCache `GGML_*`, `LLAMA_*`, compiler and build-type entries are IDENTICAL to the champion
  builds `gpu-20260929-90c12df42` and `cpu-20260925-90c12df42`.
- **Executable set** is identical to the champion builds, for both GPU and CPU.
- **Linkage** (`verify_ggml_linkage.sh` on `llama-server`): GPU PASS, CPU PASS. Logs: `linkage_{gpu,cpu}.txt`.
- **`strings libggml-hip.so`** (`strings_gpu.txt`):
  - `GGML_CUDA_FA_MASK_SKIP` 1, `GGML_CUDA_FA_MASK_SKIP_MIN_KV` 1, `GGML_CUDA_FA_SEQ_ROWS` 1. The champion build has 0 of each.
  - Commit 2's planner `plan_seq_tiles`: **0** in strings, 0 in `nm`, 0 in `nm -D`.
  - The probe discriminates: the c7f5ac9ad build shows 319 string and 78 `nm` hits.
  - `libggml-base.so` exports `ggml_flash_attn_ext_set_n_seq`.
- Each build dir carries `SHA256SUMS`, `CONFIGURE.log` and `BUILD.log`. `BUILD.log` records the source sha.

## 3. Checks run

### G0, kernel feature preservation (the ONE-champion fold gate)
- Implementation: `scripts/kernel_rnd/autokernel/loop/kernel_coverage.py`, `fold-check` subcommand. It is wrapped as G0
  in `fold2_gates.py` `run_preservation`, and `cross_target.fold_onto_champion` calls it before every loop fold.
- Read from research **origin/main `be23ac25`** in a detached worktree (`.../research-main`), not from the shared
  clone's checkout.

```bash
cd /mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/research-main
python3 -m scripts.kernel_rnd.autokernel.loop.kernel_coverage fold-check \
  --repo /mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/src \
  --base 90c12df4247e417053ffc59e2188294826d04ca2 --candidate 1bceceb0514d423ad220888313eafcddc30e485e \
  --base-build /mnt/raid0/llm/kernels/builds/{gpu-20260929,cpu-20260925}-90c12df42 \
  --candidate-build /mnt/raid0/llm/kernels/builds/{gpu,cpu}-20261004-1bceceb05 --json ../g0/g0_{gpu,cpu}.json
```

| pair | layers | result |
|---|---|---|
| source only | git inventory | **PASS**, 0 losses; gained `env_knob:GGML_CUDA_FA_{MASK_SKIP,MASK_SKIP_MIN_KV,SEQ_ROWS}` |
| GPU builds | source + static | **PASS**, 0 losses |
| CPU builds | source + static | **PASS**, 0 losses |

**G0 does not cover the GPU kernels.** `static_manifest` does list `libggml-hip.so`, but `classify_symbol` only knows CPU
families: repack traits, gemm/gemv, OpenMP regions, tinyBLAS, iqk and `ggml_compute_forward_*`. The candidate's
`libggml-hip.so` therefore yields **0 classified keys** (`g0/manifest_gpu_cand.json`; `libggml-cpu.so` yields 348).
The source layer does see the HIP env knobs and the `tests/` list. For the FA kernels themselves, G0 is vacuous.
**The real GPU gate is test-backend-ops ROCm0 plus the exactness harness in `gpu_slot_fold.sh`.**

No `KERNEL-REPLACES:` declaration is needed: nothing was lost.

### CPU-side exactness (candidate CPU build, under region-lock, 24 threads)
Script: `cpu_checks.sh`. Outputs are in `cpu/`.

| check | result |
|---|---|
| harness v1 (`fa-maskskip-20261003/harness/fa_harness`, 86 cases) | `ALL b5b8addc17c7e4f4`. Equals the KVU-19a CPU store build. **86/86 bit-identical** to the 19a CPU store and to the **unpatched champion CPU base** (`out_cpu_base`) |
| harness v2 (`fa-maskskip-batched-20261004/harness/fa_harness2`, 141 cases incl. 54 multi-sequence with the hint) | `ALL ed83734139ab0d56`. **141/141 bit-identical** to the 19b CPU store (`out_cpu_store`), the 19a CPU (`out_cpu_k19a`) and the GPU-slot reference (`out_cpu`) |
| `test-backend-ops -o FLASH_ATTN_EXT -b CPU` | **5178/5178 passed**. Not vacuous: in this tree the CPU backend is compared against itself in reference mode (`ggml_backend_cpu_set_use_ref`) |

The CPU change is exact. As KVU-19a's FOLD.md says, it is **not a claimed speedup**.

### Already-measured GPU evidence that transfers (and what does not)
- **KVU-19a GPU** (`fa-maskskip-20261003/slot-20261004T022552Z`): test-backend-ops ROCm0 2920/2920, also with
  `MIN_KV=0`; skip off == on, 64/64 bit-identical. The GPU code of commits 1-2 is unchanged in the candidate.
- **KVU-19b** (`slot2-20261004T044448Z`) measured **c7f5ac9ad**, i.e. commit 2 included. That does NOT transfer for
  multi-row-per-sequence batches. It does predict the commit-1 paths:
  - every-row-its-own-sequence decode is routed to vec: 4×1 kvu kernel 1083 us vs 1732 us champion; batched-bench
    `-kvu` S_TG 522 vs 424 base and 435 k19a.
  - with `SEQ_ROWS=0`, the build equals 19a: 119/119 bit-identical.
- **Not yet measured on GPU for this exact build:** everything in §4.
- **Caveat for the 27B smoke.** KVU-19a changes arithmetic order for six FA shapes *even with skip off*: hs=128 WMMA
  nb=32 (f16/q8_0/q4_0/bf16), hs=40 tile and hs=192, all at nmse ≤ 3e-7 (19a slot `exact.txt`, base vs off). hs=256,
  the 27B's attention, was bit-identical. So candidate-skip-off vs champion is *expected* to be byte-identical, but a
  divergence there is not proof of a defect. The slot scores that comparison DIVERGED → INCOMPLETE (read the texts),
  not FAIL. The exact criterion is candidate skip on == skip off in one binary.

## 4. GPU slot for workspace-ec: `/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/gpu_slot_fold.sh`

- One MI210 window, about 19 min plus any region-lock wait (bounded by `RL_TIMEOUT`, default 900 s).
- :8083 and every other GPU user must be down. The script refuses if any KFD process exists (`FORCE=1` overrides).
- No llama-server. Output goes to `slot-<ts>/summary.txt`, whose first line is `VERDICT PASS|FAIL|INCOMPLETE`.

| step | what | criterion |
|---|---|---|
| 0 | linkage, 3 knobs present in `libggml-hip.so`, `plan_seq_tiles` absent | abort on failure |
| 1 (~1.5 min) | harness v2 on ROCm0, arms k19a / on / skipoff / seqoff / alloff; harness v1 on / skipoff / MIN_KV=0 | E1 on==skipoff, E2 seqoff==alloff, E3 seqoff==k19a build: all bit-identical. E4: only vec-routed cases differ, on vs seqoff. E5-E7: nmse < 5e-4 vs the CPU reference and vs this candidate's own CPU build. E8: v1 `ALL` hash equal for on / off / MIN_KV=0 |
| 2 (~3.5 min) | perf2 (`fa_harness2 ROCm0 perf`), arms champ / on / seqoff, 2 rounds | informational. Expect: 4 seqs×1 row kvu ≈ 1080 / 5530 us (vs champ ~1730 / 8770); 4×8 aligned ≈ k19a ~2100 / 10400 (commit 1 leaves these on WMMA per-tile); uneven ≈ k19a ~2690 / 13650 (commit 2's gain there is NOT in this candidate); single-sequence rows ≈ k19a |
| 3 (~4.5 min) | 27B DFlash2 smoke with `llama-speculative-simple`: Qwen3.8-27B-Q8_0 + Qwen3.8-27B-DFlash2-Q8_0, `--spec-type draft-dflash --spec-draft-n-max 8`, ngl/ngld 99, f16 KV, `-fa on`, greedy, 160 tokens, host 184-191, VRAM sampled during the run | S2: candidate skip on (MIN_KV=0) == candidate skip off, byte-identical, else FAIL. S1: candidate skip off == champion `gpu-20260929-90c12df42`, byte-identical PASS, else DIVERGED → INCOMPLETE with offset and both texts |
| 4 (~9 min, **CPU half under `region-lock run --cpu-list 0-95 --role build --tag champion-fold`**) | `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0` (its CPU reference runs on 0-95, OMP 24); then the `n_seq=\|hint=` cases with `MIN_KV=0` and with `MASK_SKIP=0`, and the `hint=` cases with `SEQ_ROWS=0` | all `N/N tests passed`, no FAIL lines; lock timeout → INCOMPLETE, never PASS |

Comparator: `cmp_fold.py`. It was validated on the c7f5ac9ad slot data: it FAILs exactly the 6 commit-2 cases and
PASSes the controls. The bash script passes `bash -n`, but has not been executed, since that needs the GPU.

Not in the slot, because of the budget: batched-bench `-kvu` vs `-no-kvu`, p3batch, and the full-scale P3 27B
re-measurement. That last one is still required before any production throughput claim (KVU-19a/19b FOLD.md).

## 5. Champion-advance procedure (workspace-ec runs it, after `gpu_slot_fold.sh` says PASS, or INCOMPLETE with S1 reviewed)

Fast-forward by compare-and-swap. This mirrors `cross_target.fold_onto_champion`: ref CAS, then a two-tree refresh of
the attached checkout. That function itself is NOT used because it re-picks the commits, which would mint new shas
that no build was made from.

```bash
set -euo pipefail
L=/mnt/raid0/llm/llama.cpp
OLD=90c12df4247e417053ffc59e2188294826d04ca2
NEW=1bceceb0514d423ad220888313eafcddc30e485e
REF=refs/heads/ak/champion/llama-cpp-ffc1bac82eec
T=/mnt/raid0/llm/tmp/ak-loop-tree          # the one worktree that has the champion branch checked out

# 0. preconditions (each must hold; set -e stops on the first that does not)
test "$(git -C $L rev-parse $REF)" = $OLD
test "$(git -C $L ls-remote fork $REF | cut -f1)" = $OLD
test "$(git -C $L ls-remote fork refs/heads/fold/champion-kvu19-20261004 | cut -f1)" = $NEW
git -C $L merge-base --is-ancestor $OLD $NEW
test "$(git -C $T rev-parse HEAD)" = $OLD
test -z "$(git -C $T status --porcelain --untracked-files=no)"
test "$(git -C $L branch --show-current)" = production-consolidated-v10     # frozen tree untouched

# 1. move the ref, guarded by the old value
git -C $L update-ref -m "fold: KVU-19a (ac97e305a, a0d0ae238) + KVU-19b commit 1 (1bceceb05) [champion-fold-kvu19-20261004]" $REF $NEW $OLD

# 2. refresh the attached checkout (otherwise HEAD=NEW over an OLD index/worktree, which reads as staged REVERTS
#    of the fold and would publish them on the next commit there)
git -C $T read-tree -m -u $OLD $NEW
test -z "$(git -C $T status --porcelain --untracked-files=no)"

# 3. publish, fast-forward only (git rejects a non-ff push without --force; never add it)
git -C $L push fork $NEW:$REF
test "$(git -C $L ls-remote fork $REF | cut -f1)" = $NEW

# 4. the ONE-champion standing receipt (§6): champion-only, ~15 min GPU window, AFTER steps 1-3 (row 4a)
/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/standing_receipt.sh
```

- The precompiled champion builds already exist: `kernels/builds/{gpu,cpu}-20261004-1bceceb05`. That satisfies "ref
  move and rebuild together".
- The AutoKernel loop's anchor slot is workspace-89's to reseed. `champion.verify_startup` keeps accepting the old
  anchor, because `90c12df42` stays an ancestor of HEAD, but the anchor will then not BE the champion.
- Ledgering the fold (the prose fold table in `handoffs/active/autokernel-champion-aggregate.md`) is the owning
  session's write.

## 6. The ONE-champion standing receipt: single arm, per operator ruling 2026-10-04

The ruling, relayed by workspace-89: *"why are you doing this. We have the production numbers already. You just need
to measure the champion."* The receipt therefore measures ONLY the champion, and takes production from an existing
record.

**Rule** (`agents/shared/OPERATING_CONSTRAINTS.md` § *The Single Champion*): every champion change updates the
measured aggregate vs the CURRENT frozen production, resolved live.

**Writer:** `epyc-inference-research` `scripts/kernel_rnd/autokernel/loop/production.py` → `production.refresh()`.
- It is the same on origin/main `be23ac25` and the shared clone.
- It resolves the freeze LIVE with `resolve_frozen()`: `production-consolidated-v10` @ `ffc1bac82eec`.
- It writes atomically via `status.write_json` to:
  - `loop-memory/champion-vs-production.json`, schema `epyc.autokernel.champion_vs_production.v1`;
  - `champion-vs-production.<sha12>.json`, the evidence file.
- `refresh()` does not measure the baseline itself. It only checks that the baseline slot is built, then calls the
  injected `compare(slot, champion)`.
- **The bypass is done there:** `standing_receipt.py` injects a single-arm `compare` that measures only the champion
  and returns a `bench.Comparison` whose `anchor_samples` are the cited record.
- The writer itself is unchanged, and nothing is hand-written.
- The baseline slot passed is the v10 serving build `kernels/builds/gpu-20260921-ffc1bac82`. It is recorded as
  `baseline.build` and is **not run**.
- In the loop, `refresh()` is called by `run.py publish_headline()` on every keep. A hand fold never calls it, which
  is why the v10 lineage has no receipt. The last receipt is `.json.pre-v10-20260922`, `bff30cebe` vs v9, +5.633%.

**Baseline record: the search result.**
No recorded v10 (`ffc1bac82`) tg128 measurement on the 27B exists under the loop protocol, before or after the
2026-09-21 BIOS change. The loop reset at the v10 promotion (`accumulator-bundle.json`: `keeps: []`) and has not
measured on the GPU since.

Records checked:
- `ratify_v10_final_freeze_20260922.json` and `v10-qualification-20260921-ffc1bac82.json` gate the 27B GPU on
  **serving** ratios only (DFlash2 vs v9 MTP, np 1/2/4/8 = 1.319/1.268/1.239/1.088), with no tg128 number.
- `kernels/builds/gpu-20260921-ffc1bac82/PROVENANCE.md`: no tg128 number.
- `docs/design/champion-max-performance-20260908.md`: only a pre-v10 `ef81196d5` caveat figure of 31.0.
- The only v10 tg128 reading on the 27B, `/mnt/raid0/llm/tmp/lb1-profile-20261003/results/trace_q8_27b_tg128.stdout`
  (2026-10-03), ran **under rocprof tracing** with `-r 3` and no numactl: [17.2, 12.3, 26.5]. It is trace-perturbed
  and unusable.

**Cited baseline (closest record, identical protocol):**
- `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`, sha256
  `71344d345080388fd181b6bbbe99bac4ba791e9b0e95c634e7b2c2fb48f434b0`, pinned and verified on every run.
- Arm: `g5_full.candidate_samples`.
- Source: FOLD-2 gate G5, 2026-09-08 (file mtime 11:16:25Z), written up in
  `progress/2026-09/2026-09-08-ak-rebuild-20260828.md` (the G5 row).
- Build and commit: `ef81196d5`, `/mnt/raid0/llm/tmp/build-fold-ef81196d5`.
- Samples: 20 launches, median **31.301** tok/s, mean 31.291. All 40 launches of that A/B were resident.
- Exact protocol: `bench.compare` at research `4ede0e03`, 20 alternating pairs plus 1 warm-up pair. Each launch is
  `taskset -c 184-191 numactl --interleave=all llama-bench -m Qwen3.8-27B-Q8_0.gguf -p 0 -n 128 -r 9 -ngl 99 -fa 1 -o json`,
  with `LD_LIBRARY_PATH=<bin>:/opt/rocm/lib`. The value is the tg128 row's `avg_ts`.

Fields that differ from "v10 now", and how each is handled:

| field | record | handling |
|---|---|---|
| commit | `ef81196d5` | v10 = `ef81196d5` + `d0d70c5fe` (NextN hparam read order, gemma4-assistant only) + `ffc1bac82` (MoE top-k fusion gated to CPU-only graphs, inside `build_moe_ffn`). The dense 27B GPU graph runs neither, so it is code-identical. Disclosed in the note. |
| build | `build-fold-ef81196d5` | every `GGML_*` / `LLAMA_*` option and the compilers are identical to the v10 store build; only install-dir paths differ |
| `--autokernel-harden` | absent (added to `run_once` 2026-09-15, `13f8e63a`; it changes what is measured) | **the champion run is adapted to match the record**: `standing_receipt.py` reproduces `run_once`@`4ede0e03` verbatim and refuses any row with `autokernel_hardened=true` |
| pairing | alternating against `bff30cebe` | **unpaired**: the champion runs 1 warm-up plus 20 consecutive launches |
| host state / date | 2026-09-08, before the 2026-09-21 BIOS change (memory interleave on, 5600 MT/s) | not correctable. Caveat in the note: unpaired and 26 days apart; the host drifts ~3% over hours, so the effect carries at least that uncertainty. `noise_floor_pct: null`, `calibrated: false`; the 0.638% paired floor does not apply |

**Champion measurement:** `gpu-20261004-1bceceb05`, 1 warm-up plus 20 launches of the identical argv.
**Estimated device time ~14.4 min** (the record took 41.2 s per launch), down from about 29 min for the paired
version. Residency is sampled on every launch, and the run refuses if any launch is not resident.

**Provenance field** (bundle key `anchor_guard_excursion`, the writer's only free-text slot; the full text is in
`standing_receipt.sh` `NOTE=`):
- the hand advance `ffc1bac82 → 90c12df42` (5 folds, no receipt), then `→ 1bceceb05`;
- the bypass;
- the substitution of `ef81196d5` samples under the v10 baseline label;
- the unpaired comparison;
- the host-drift and BIOS caveat;
- a warning that the writer's `confidence_interval` (`paired_bootstrap_median_ratio`, pairing ordinals) is not a
  valid paired interval here.

Two more writer artefacts to read correctly: the bundle says `pairs: 20` and `launches: 40`, but they are 20 measured
plus 20 recorded.

**Invocation.** The run is under `region-lock run --cpu-list 0-95 --role bench --tag champion-standing`, as
workspace-89 required. The wrapper refuses unless:
- the ref is `1bceceb05` locally and on `fork`;
- the frozen tree is v10 and clean;
- `kernels/production/gpu` points at the v10 build;
- the champion build's linkage is OK;
- 0 KFD processes are on the GPU.

```bash
/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/standing_receipt.sh --dry-run   # 2026-10-04: record sha verified, ~14.4 min, nothing written
/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/standing_receipt.sh             # advance step 4 (row 4a), after §5 steps 1-3
```

- Exit codes: 0 = published; 4 = refresh declined, previous state stands; 2/3 = refused before measuring.
- The write path was self-tested with a stubbed llama-bench call into a scratch store, and that store was then deleted.
  `production.refresh` accepted the injected comparison and wrote a schema-valid bundle naming the v10 freeze.
- The set-aside `.pre-v10-20260922` and `.pre-reconcile` files are never touched.

**Scope of the number:**
- tg128 is single-sequence decode at n_kv ≈ 128, so the FA mask skip never fires on it.
- The receipt reflects the champion's 27B decode aggregate over `ffc1bac82..1bceceb05`, not a KVU-19 effect.
- The writer holds one bundle, so a CPU-side standing would overwrite this one.

## 7. Promotion vehicle

**Chosen: v11 via the `kernel-promotion` skill**, agreed by workspace-89 and the coordinator. The champion tip, with
this fold, is the v11 candidate. The skill (`/workspace/.claude/skills/kernel-promotion/`) needs:
- **0** rollback anchor: archive v10 (`gpu/cpu-20260921-ffc1bac82`) with `scripts/anchor.sh`, and demonstrate the rewind.
- **1** `scripts/scope.sh`.
- **2** relocatable build with the complete target set. The `kernels/builds/*-1bceceb05` builds are already
  `$ORIGIN`-relocatable and binary-set-identical to the champion builds.
- **3/3b** `preflight.sh` and `loadcheck.sh`.
- **4** the `promotion_gates.yaml` gates (incumbent v10 `ffc1bac82eec`, 10303):
  - speed recipe-to-recipe: CPU n=5 per arm, ratio ≥ 0.95; GPU ctx 65536 at np 1/2/4/8 with residency proven;
  - quality: MMLU-Pro n=200 and GPQA n=195 on worker_general and architect_critic;
  - serving floor, relocatable runtime, binary-set parity and rollback rehearsal.
- **Extra acceptance riding this champion:**
  - V6R-4a: `25132e042` and `90c12df42` are ancestors (true); `test-repack-parallel` passes (present in the CPU
    build); a CPU load A/B vs v10; the decode A/B at full pair count.
  - KVU-19: `gpu_slot_fold.sh` PASS, plus the full-scale P3 27B re-measurement before quoting any production
    multi-sequence number.
- **5** `package.sh`, then **6** ONE operator signature.
- **7** freeze: cut `production-consolidated-v11`, bake the overlay, update the `verify_llama_cpp.sh` constants and
  the CLAUDE.md block, repoint.
- **8** `stack-change` phases 7-8.
- **9** marker sweep, champion reseed (a new `ak/champion/llama-cpp-<v11 sha12>`), and `verify_serving.sh`.

**Interim v10.x (noted only, not recommended):**
- No interim path is documented anywhere: no `v10.1`/`v10.x` hits in root, research or orchestrator.
- The tooling treats the version as a label: `promotion_gates.yaml` `version`/`branch`, the `verify_llama_cpp.sh`
  `EXPECTED_*` constants, and `production.py`'s `production-consolidated-*` prefix.
- So a "v10.1" would be the SAME full skill run under a different branch name: same anchor, gates, signature, freeze
  and stack change, at the same cost.
- It would also add a naming scheme that CLAUDE.md does not ratify (CLAUDE.md lists `-v10`, `-v11`, …), and would
  need operator ratification of that scheme.
- It buys nothing over v11. Production is versioned past, never patched, so there is no cheaper "patch v10" vehicle
  either.

## 8. Files

All in `/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/`:
- **Scripts:** `build_store.sh`, `cpu_checks.sh`, `pipeline.sh` (+ `pipeline.log`), `cmp_fold.py`,
  `gpu_slot_fold.sh`, `standing_receipt.{sh,py}`.
- **Results:** `cpu/` (CPU harness outputs, `exact_v{1,2}.txt`, `tbo_cpu.log`), `g0/` (`g0_source.json`,
  `g0_gpu.json`, `g0_cpu.json`, `manifest_gpu_cand.json`), `linkage_{gpu,cpu}.txt`, `strings_gpu.txt`.
- **Worktrees:** `src/` (the candidate worktree) and `research-main/` (detached research origin/main `be23ac25`,
  read-only use). Remove both with `git worktree remove` once the fold is settled, never `prune`.

## 9. Champion tip at hand-off
Re-resolved 2026-10-04T06:48:53Z: `90c12df4247e417053ffc59e2188294826d04ca2` locally AND on `fork`; frozen tree on
`production-consolidated-v10` @ `ffc1bac82`, clean; candidate worktree clean at `1bceceb05`; `fork/fold/champion-kvu19-20261004` = `1bceceb05`. §5 applies unchanged while the champion still reads `90c12df42`.
