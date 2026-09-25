# Kernel freeze runbook

**Scope:** freezing a new production kernel for any of the four backends —
`cpu`, `gpu` (llama.cpp), `stt` (whisper.cpp), `tts` (qwentts.cpp).

The question a freeze must answer is narrow: *which models must show no regression
before this kernel may serve?* Everything else is process around that.

## The answer is derived, never curated

A hand-maintained list of "models to re-bench" goes stale the moment a role is
repointed, and a stale gate is worse than none — it passes while testing the wrong
thing. The correct set is a projection of the compiled stack priors:

> the models that matter for backend **B** are exactly the models whose roles
> resolve to backend **B**.

```bash
uv run python scripts/validate/kernel_freeze_scope.py --backend cpu
```

Since 2026-07-31 each role's `binary_path` is resolved from its declared `device`
through the stable kernel layer (`/mnt/raid0/llm/kernels/production/<backend>`), so
this projection is exact rather than inferred.

**This is what makes the four kernels independently upgradable.** A whisper.cpp
upgrade cannot regress a role that never calls whisper.cpp, so it is not gated on
one.

**Never quote a scope from this page.** A previous revision of this paragraph named
per-backend counts in prose ("`gpu`, `stt` and `tts` serve none"). By 2026-09-21 that
sentence was false — `--backend gpu` resolved four roles across two distinct models,
and one of them (Qwen3-VL-30B) is the cell that caught a -30% MoE regression in the
v10 candidate. A reader who trusted the prose would have skipped half the GPU gate.
The count is a *projection of the registry as it is today*; the only admissible form
of it is the command's output, pasted into the freeze record:

```bash
for B in cpu gpu stt tts; do
  echo "== $B"; uv run python scripts/validate/kernel_freeze_scope.py --backend "$B"
done
```

A backend that genuinely resolves zero roles still needs its own functional evidence;
"zero" is a result the command must produce, never an assumption the reader may carry
in.

> **Path-substring backend markers break on every promotion — never add one, and cross-check
> the tool.** Two consumers classified backend by sniffing a build path
> (`kernel_freeze_scope.py` on `"build-hip" in p`; `dashboard_topology.py` on `hip|rocm|gfx` in
> argv[0]). The v10 store path carries neither marker, so the scope tool reported `gpu: 0 roles`
> and every GPU role reported substrate `cpu` — silently, with no error. Both now resolve through
> `kernel_paths.backend_dir()`, substring kept only as a fallback for pre-store paths. Two
> consequences:
>
> * **Derive the scope BEFORE the repoint and again AFTER the derived-artifact regen — never
>   between them**, because in that window the priors still name the outgoing build dir and the
>   fallback misclassifies it.
> * Reconcile the tool against the priors before trusting it, counting `binary_path` lines only:
>
> ```bash
> cd /mnt/raid0/llm/epyc-orchestrator
> for B in cpu gpu; do
>   printf '%s tool=%s priors=%s\n' "$B" \
>     "$(uv run uv run python scripts/validate/kernel_freeze_scope.py --backend $B | grep -oE '[0-9]+ role' | head -1)" \
>     "$(grep -cE "binary_path: .*/kernels/builds/$B-" orchestration/derived/stack_priors.yaml)"
> done   # the two numbers must match per backend, or the freeze is not scoped
> ```


## Pre-flight — refuse to start a promotion that cannot finish

Every item below was learned by violating it during the v10 promotion (2026-09-21/22).
Each is cheap before the build and expensive after it. **All five must pass before any
bench time is spent**, because a candidate that fails any of them is unpromotable and
every number measured against it is thrown away.

**P1. The build must be relocatable.** `production/<B>` is a symlink whose target is
meant to move; a binary carrying an absolute RUNPATH into its own build directory keeps
loading *that* directory's ggml forever, wherever you copy it to.

```bash
cmake -B <build> -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON ...      # configure-time, not fixable later
readelf -d <build>/bin/llama-server | awk -F'[][]' '/RUNPATH/{print $2}' | tr ':' '
' \
    | grep -vxE '\$ORIGIN|/opt/rocm/lib' | grep -q . \
    && { echo "FAIL: non-relocatable or EMPTY RUNPATH element (empty = loader searches CWD)"; exit 1; }
```

`patchelf` is **not installed on this host**, so a build configured without this flag
cannot be repaired — it must be rebuilt. (v10: `tmp/build-fold-ef81196d5/bin/llama-server`
carried `RUNPATH=/mnt/raid0/llm/tmp/build-fold-ef81196d5/bin:/opt/rocm/lib`. Promoting it
would have made `production/gpu` load ggml out of `tmp`.)

**P2. The target set must be complete.** `cmake --build <build>` with no `--target`, or
an explicit target list that covers every binary the incumbent ships. **`--target
llama-server llama-bench` is not a kernel** — it is two executables where production has
~90 (the incumbent's count, read from the archive — do not hardcode), and `scripts/lib/executor.py` resolves `llama-completion`,
`llama-speculative`, `llama-lookup` and `llama-mtmd-cli` through the store. Those roles
fail at *launch*, long after the gate has passed.

**P3. Binary-set parity against the incumbent, mechanically.** Diff the names, do not
eyeball the count:

```bash
OLD=$(readlink -f /mnt/raid0/llm/kernels/production/<B>)
exe() { find "$1" -maxdepth 1 -type f -perm -u+x ! -name '*.so*' -printf '%f\n' | sort; }
   comm -23 <(exe "$OLD") <(exe <build>/bin)   # MUST be empty, or justify each name in PROVENANCE.md
```

Every name present in the incumbent and absent from the candidate is a regression in
capability until someone writes down why it is not. (v10 shipped 91 executables against
v9's 92: `test-gguf-model-data` and `test-quant-type-selection` were dropped and
`llama-rowexact` added. Nothing flagged it; this diff would have.)

**P4. Build somewhere durable, not `/mnt/raid0/llm/tmp`.** `tmp` is swept, nothing
garbage-collects it and nothing promotes out of it. Build 10196 (`58c345093`) was lost
from there outright, and `check_evidence_durability.py` refuses `/mnt/raid0/llm/tmp` as a
citation path — so evidence produced there cannot be cited even when the binary survives.
Build directly under `/mnt/raid0/llm/kernels/builds/<B>-<YYYYMMDD>-<short-sha>/`.

**P5. The rollback anchor must already exist, and be proven, before anything moves.**
See step 0 below. A promotion with no anchor is not a promotion, it is a one-way door.

0. **Rollback drill — prove the anchor, then promote.** `archive/` was **empty from the
   day the store was created (2026-07-31) until 2026-09-21**, because step 6 assumed an
   "old build dir" that never existed: `production/{cpu,gpu}` pointed INSIDE the frozen
   *source* tree at accretive artifact directories holding five library generations at
   once (`libllama.so.0.0.1012{1..5}`). Step 6 had therefore never been executable and no
   freeze had ever been recorded through the store. Do not discover this again.

   ```bash
   B=<backend>; OLD=$(readlink -f /mnt/raid0/llm/kernels/production/$B)
   A=/mnt/raid0/llm/kernels/archive/$B-<YYYYMMDD>-<outgoing-sha>
   test -d "$A"                                             # the anchor EXISTS
   test -s "$A/SHA256SUMS" && ( cd "$A" && sha256sum -c SHA256SUMS >/dev/null )
   readelf -d "$A/bin/llama-server" | grep -q 'RUNPATH.*\$ORIGIN'   # it is relocatable
   env -u LD_LIBRARY_PATH epyc-inference-research/scripts/utils/verify_ggml_linkage.sh \
       "$A/bin/llama-server" "$A/bin"                       # it stands alone
   "$A/bin/llama-server" --version                          # it reports the OUTGOING build
   ```

   An anchor that has not been *executed* is not a rollback path. Record its `--version`
   line in the freeze artifact — that string is what a future rollback is checked against.
   Note that the speech anchors (`stt`, `tts`) are **not** self-contained: they carry an
   absolute RUNPATH and are rollback anchors only, not drop-in relocations.

## Procedure

1. **Build the candidate in its own experimental tree.** Never in the frozen
   production tree. Production kernels are versioned past, never patched in place.

2. **Derive the scope.** `kernel_freeze_scope.py --backend <B>` gives the distinct
   models with their declared context and speculative recipe. Bench the *distinct
   models*, not the roles — several roles share one model and one server.

3. **Bench candidate vs frozen production**, per `MEASUREMENT.md`:
   - same model, same quant, same context depth, same placement, same recipe;
   - the role's **production** acceleration recipe, not a spec-dec-off baseline —
     a baseline is never a headline and never a promotion arm;
   - `category=CANDIDATE` for the new kernel, `category=OPTIMUM` for incumbent;
   - `n>=3` with min/max reported, never a bare median.

4. **Pair every speed number with a correctness check — an EVAL, not a bit-compare.**
   A kernel that is faster and wrong is a regression. But *bitwise* identity is the
   wrong bar and was never the real gate:

   * **Frozen v9 fails a bitwise spec-dec test too.** A verify batch has `ne11 >= 2`
     while the non-speculative baseline has `ne11 = 1`, and batch shape changes float
     summation order, which flips argmax at near-ties. On gfx90a this is *deliberate*:
     v9 carries EPYC-local commit `a6b4b5263` (`ggml/src/ggml-cuda/mmvq.cu:341-344`)
     routing Q8_0 to a different kernel at `ne11 >= 2`, taken for +17.4% single-stream
     MTP and described by its own commit message as "numerically-valid (not bit-exact)".
     The same `N==1` vs `N>1` split exists on both CPU paths (`llamafile_sgemm` mnpack
     blocking, iqk `funcs[ny-1]` dispatch). **Batch invariance is not a property any of
     our three compute planes holds** — see
     `handoffs/active/dflash2-block-drafter-experimental-build.md:292-315`.
   * A runbook clause that the *incumbent* fails is not a gate. It is a clause every
     promotion must talk its way past, which is the same as no clause at all.

   **The gate is the quality eval against the incumbent**, which is what both the v9 and
   the v10 qualifications actually used:

   - **MMLU-Pro and GPQA, candidate vs incumbent, for every distinct model in the backend's scope (v9/v10 ran two representative roles; name the set in the artifact)**, `errors=0`, with the
     per-arm evidence sha256 recorded (v9: `artifacts/operator/
     v9-qualification-20260810T235723Z-0db32c06e/summary.json` `gates.quality`, n=200 /
     n=195; v10: `artifacts/operator/v10-qualification-20260921-ffc1bac82.json`
     `gates.cpu_quality`).
   - **Plus one narrow exact-token parity spot check**, scoped and labelled as such —
     v9 used `gates.dspark_q8_parity`: one model, one sidecar, `-np 1`, 18 drafted /
     9 accepted. Record the scope in the artifact; do NOT generalise it to the lineup,
     and do not expect it to hold at `np >= 2` on GPU (previous bullet).
   - A **coherence check at production prompt length** for every distinct model in
     scope, per `agents/shared/MEASUREMENT_POLICY.md`.

   Bitwise divergence is *reportable*, never *blocking*. An eval delta outside the quality suite's noise band (at n=200 a single item is 0.5pp; a delta inside the band is not a regression)
   is blocking.

5. **Verify linkage before serving.** The three trees run three different ggml
   generations; a binary that loads another tree's ggml runs silently wrong:
   ```bash
   epyc-inference-research/scripts/utils/verify_ggml_linkage.sh \
       /mnt/raid0/llm/kernels/production/<B>/<binary> \
       /mnt/raid0/llm/kernels/production/<B>
   ```

6. **Materialize a versioned build directory, then move the symlink.**

   Steps 1-5 leave the candidate in a scratch build tree (historically
   `/mnt/raid0/llm/tmp/build-*`). That tree is not a promotable target, for two
   reasons, and **both must be fixed before the symlink moves**:

   * it is not versioned and nothing keeps it — build 10196 (`58c345093`) was lost
     from `/mnt/raid0/llm/tmp` outright;
   * a scratch build bakes an **absolute RUNPATH to its own build directory**
     (`readelf -d .../llama-server` -> `/mnt/raid0/llm/tmp/build-<x>/bin:...`),
     whereas a production target must carry `$ORIGIN` — `production/<B>` is a
     symlink whose target is meant to move, and a binary that names an absolute
     lib directory silently keeps loading the old one.

   6a. **Build relocatable.** The candidate build in step 1 must be configured with

   ```bash
   cmake -B <build> -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON ...
   ```

   so that `bin/` is self-contained. Verify, not assume:

   ```bash
   readelf -d <build>/bin/llama-server | awk -F'[][]' '/RUNPATH/{print $2}' | tr ':' '
' \
    | grep -vxE '\$ORIGIN|/opt/rocm/lib' | grep -q . \
    && { echo "FAIL: non-relocatable or EMPTY RUNPATH element (empty = loader searches CWD)"; exit 1; }
   ```

   6b. **Copy it into the store under a versioned name** (copy, never move — the
   bench evidence still cites the build path):

   ```bash
   V=/mnt/raid0/llm/kernels/builds/<B>-<YYYYMMDD>-<short-sha>
   mkdir -p "$V" && cp -a <build>/bin "$V/bin"
   ( cd "$V" && find bin -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS )
   ```

   6c. **Prove the copy stands alone** — with `LD_LIBRARY_PATH` *unset*, because a
   passing check that needed the variable proves only that the variable was set:

   ```bash
   env -u LD_LIBRARY_PATH \
     epyc-inference-research/scripts/utils/verify_ggml_linkage.sh \
       "$V/bin/<binary>" "$V"
   ```

   **Create the anchor NOW, not later.** On the FIRST promotion through this store the anchor was
   hand-made minutes before the cutover; on every promotion after, the incumbent already lives in
   `kernels/builds/`, so archiving it is a free idempotent symlink and must happen BEFORE anything
   moves — a rollback drill that depends on an anchor a later step creates is not a drill:

   ```bash
   B=<backend>; OLD=$(readlink -f /mnt/raid0/llm/kernels/production/$B)   # must be under kernels/builds/
   A=/mnt/raid0/llm/kernels/archive/$B-<YYYYMMDD>-<outgoing-sha>
   [ -L "$A" ] || ln -sfn "${OLD%/bin}" "$A"
   ```

   6d. **Archive the outgoing target by its RESOLVED path, then repoint.** Re-run the
   pre-flight step 0 drill against the anchor first — an anchor that has never been
   executed is not a rollback path, and `archive/` was empty for the store's first seven
   weeks precisely because nobody checked:

   ```bash
   OLD=$(readlink -f /mnt/raid0/llm/kernels/production/<B>)
   ln -sfn "$OLD" /mnt/raid0/llm/kernels/archive/<B>-<YYYYMMDD>-<outgoing-sha>
   ln -sfn "$V/bin" /mnt/raid0/llm/kernels/production/<B>
   ```

   **One-time exception for the first promotion through this store.** Today
   `production/<B>` still resolves into the frozen *source* tree
   (`llama.cpp/build/bin`, `llama.cpp/build-hip/bin`), which is an accretive
   directory holding five generations of `libllama*.so.0.0.101xx` at once — a
   symlink into it would archive a moving, mixed-version target. For that first
   promotion only, archive a **copy**:

   ```bash
   cp -a "$OLD" /mnt/raid0/llm/kernels/archive/<B>-<YYYYMMDD>-<outgoing-sha>
   ```

   after which every subsequent promotion archives a symlink as above.

   **The binary NAME is unchanged by design — the paths are not.** A previous revision
   of this page claimed "Neither registry changes. No launcher changes." That is false,
   and believing it is what left the v10 promotion half-applied for hours. Measured on
   2026-09-21/22, the cutover touched **(see the progress log) in `epyc-orchestrator`** ((see the progress log)),
   including `orchestration/derived/stack_priors.yaml`, `orchestration/model_registry.yaml`,
   `orchestration/gpu_shadow_lane_tenancy.yaml`, `scripts/lib/env.sh`,
   `scripts/lib/executor_paths.py`, `scripts/server/orchestrator_stack.py`,
   `scripts/server/gpu_shadow_lane.py`, `scripts/server/stack_paths.py`,
   `src/registry/stack_priors.py` and `tests/unit/test_stack_priors_compiler.py`, plus
   three files in `epyc-root`. Step 8 enumerates the class.

   The structural reason is one line: `epyc-orchestrator/src/registry/kernel_paths.py:83`
   returns `path.resolve()`, so `backend_dir()` hands out the **dereferenced build
   directory**, never the stable `production/<B>` symlink. Every artifact derived from it
   therefore bakes `kernels/builds/<B>-<date>-<sha>/bin` and must be regenerated on every
   promotion *and every rollback*. Any consumer that keeps its own literal instead — and
   (see the progress log) still name `llama.cpp/build{-hip}/bin` — is a split-brain waiting to happen:
   after the v10 repoint, `scripts/lib/executor.py` was still launching v9 through the
   master registry's `runtime_defaults.binaries.base_dir` literal while `stack_priors`,
   `orchestrator_stack` and `env.sh` had all followed v10. The stale path still existed,
   so it resolved, served, and was detectable only by reading a running server's argv.

7. **Re-verify after promotion** (step 5 again, against the new target), then record
   the freeze with its ratification artifact and evidence hashes. Also run the store
   verifier, which is the only gate that attests the symlink layer itself:

   ```bash
   bash scripts/session/verify_kernel_store.sh   # must exit 0
   ```

8. **Post-promotion — the work is not done when the symlink moves.** Every item below
   was discovered *after* the v10 repoint, in production, by a human noticing. Budget for
   it in the same session; a promotion left half-applied is worse than one not started,
   because part of the stack serves the new kernel and part serves the old one.

   8a. **Regenerate every derived artifact and commit it.** The compiled priors pin the
   resolved build dir (see step 6), so they are stale the instant the symlink moves:

   ```bash
   # in epyc-orchestrator
   uv run uv run python scripts/registry/stack_change_pipeline.py update                  # regenerates orchestration/derived/stack_priors.yaml
   git diff --stat orchestration/derived/stack_priors.yaml    # expect paths-only, +N/-N balanced
   grep -c 'llama.cpp/build' orchestration/derived/stack_priors.yaml   # must be 0
   ```

   8b. **Refresh the `source_artifacts` hash pins** in the regenerated priors
   (`orchestration/derived/stack_priors.yaml`, the `source_artifacts:` block) and confirm
   the commit-time staleness gate is clean:

   ```bash
   uv run python scripts/validate/stack_change_guard.py --check-source-artifact-staleness --staleness-scope worktree --staleness-strict
   ```

   Note what this gate is and is not: it is a **commit-time** check
   (`stack_change_guard.py:74-76`, pin loop `:2908-2923`). No start path consults it —
   `orchestrator_stack.py start` will *not* refuse a stale-pin stack. So a promotion that
   skips this step fails silently at commit time, not loudly at launch.

   8c. **Sweep the literals.** A promotion is only complete when nothing still names the
   outgoing path:

   ```bash
   grep -rn 'llama.cpp/build/bin\|llama.cpp/build-hip/bin' \
     epyc-orchestrator/{src,scripts,orchestration} scripts/ dashboard/ \
     --include=*.py --include=*.yaml --include=*.sh
   ```

   Known standing offenders as of 2026-09-22 — each is a live split-brain surface:
   `epyc-orchestrator/scripts/lib/executor.py:77` and `:90` (v9 literals on the
   registry-load-failure path, which reopens exactly what `executor_paths.py` was written
   to close); `scripts/server/gpu_shadow_lane.py:49-50` and
   `orchestration/gpu_shadow_lane_tenancy.yaml:47`; and the two silent CPU fallbacks at
   `scripts/server/orchestrator_stack.py:156-167` and
   `src/registry/stack_priors.py:1930-1954`, which swallow `KernelPathError` and hand back
   a CPU-only literal — a dangling `production/gpu` then compiles a CPU path instead of
   failing.

   8d. **Expect test fallout, and treat it as signal.** Any test that encodes the old
   build path fails by design. Fix it by asserting **store resolution**, never by
   hard-coding the new path — otherwise the next promotion breaks it again:

   ```python
   # tests/unit/test_stack_priors_compiler.py  (2026-09-21)
   # was:  assert runtime["binary_path"].endswith("/llama.cpp/build/bin/llama-server")
   from src.registry.kernel_paths import server_binary as _store_server_binary
   assert runtime["binary_path"] == str(_store_server_binary("cpu"))
   ```

   8e. **Repoint the observers.** `dashboard/server.py:565-570` hard-codes
   `PRODUCTION_STABLE_LINKS` at the 2026-07-31 resolution targets and publishes
   `matches_expected`; the first legitimate promotion turns that field false for every
   repointed backend. Move the table with the freeze.

   8f. **`verify_llama_cpp.sh` attests the frozen SOURCE tree, which a store promotion does not
    touch — so after a promotion it passes on the OLD kernel while the store serves the new one.**
    Do NOT edit its constants against a tree still checked out at the old branch, and **do not
    check out or branch the frozen tree** (CLAUDE.md → *Production kernels are FROZEN*: never
    modified, rebased, built or committed to without explicit operator authorization). Instead add
    STORE-SIDE identity to the receipt — `PROVENANCE.md`'s commit and
    `production/<B>/llama-server --version` must agree — and file an operator decision package for
    (i) whether a `production-consolidated-vN` branch is cut and the tree advanced, and (ii) the
    CLAUDE.md freeze block, which the ratification writes, not an agent.

### 8g. Public distribution is downstream of the store freeze

The GitHub distribution is a convenience layer for outside users; it is not a
second production authority. Publish it only after the store cutover, store
verifier, provenance, linkage, and ratification checks above pass.

For the llama.cpp production surface, use an immutable annotated tag named
`production-consolidated-vN` pointing at the exact frozen source commit. Do not
move `main` to mean "production": `main` is a development/upstream-facing ref,
whereas the tag is the reproducibility identity. A public release may be created
from that tag, but it must never be used to select the serving binary.

The release checklist is:

1. Prove the tag, store provenance, and live production versions agree:

   ```bash
   TAG=production-consolidated-vN
   SOURCE=/mnt/raid0/llm/llama.cpp
   for B in cpu gpu; do
     TARGET=$(readlink -f "/mnt/raid0/llm/kernels/production/$B")
     SHA=$(git -C "$SOURCE" rev-parse "refs/tags/$TAG^{}")
     test "$SHA" = "$(sed -n 's/^- commit `\([0-9a-f]*\).*/\1/p' \
       "${TARGET%/bin}/PROVENANCE.md")"
     "$TARGET/llama-server" --version
   done
   bash scripts/session/verify_kernel_store.sh
   ```

2. Build release archives from the versioned store target
   (`readlink -f /mnt/raid0/llm/kernels/production/$B`), never from a source-tree
   build directory or `/mnt/raid0/llm/tmp`. Preserve the runtime layout, include
   the complete executable and library set, ship `PROVENANCE.md`, and carry the
   store `SHA256SUMS` or a manifest derived from the exact release archive.

3. Ship the release-side `QUICKSTART.md`, `verify-release.sh`, recipe files, and
   a warning that model weights are not included. The verifier must be run after a
   fresh download and extraction; it must check archive hashes, `--version`, the
   frozen commit marker, and backend-specific linkage. A package that only checks
   the archive checksum but never executes the packaged binary is incomplete.

4. Upload the CPU and HIP assets to the GitHub release for the immutable tag and
   record the release URL, asset names, and hashes in the freeze record. The
   llama.cpp release covers only the CPU/GPU surfaces; the frozen speech kernels
   (`production-speech-v1`) require their own project releases or an explicitly
   versioned kernel-set manifest. Never imply that a llama.cpp release contains
   whisper.cpp or qwentts.cpp.

5. Treat a release asset rebuild, replacement, or retag as a new release event.
   Never overwrite an asset under an existing production tag without a new
   ratification and a new tag.


## Gate

A regression outside the quality suite's noise band (at n=200 a single item is 0.5pp; a delta inside the band is not a regression) on any cell blocks the freeze **for that backend
only**. Roll back by repointing the symlink to the archived target — which restores the
*binaries* in one `ln -sfn`, but is **not** the whole rollback. Because `backend_dir()`
dereferences the symlink (step 6), every derived artifact and every literal listed in
step 8 named the promoted build dir and must be reverted with it. Plan a rollback as
"repoint + re-run step 8", and restart anything that was already serving that backend so
it re-execs the restored binary; a running server holds its own argv and will not follow
a symlink that moved underneath it.

## What this does not cover

Changing *which* backend a role uses is a topology change, not a kernel freeze. That
is a `stack_topology.yaml` / role-assignment edit plus a recompile, and it gates on
the stack-change pipeline rather than on this runbook.
