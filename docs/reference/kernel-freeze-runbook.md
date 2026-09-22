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
python scripts/validate/kernel_freeze_scope.py --backend cpu
```

Since 2026-07-31 each role's `binary_path` is resolved from its declared `device`
through the stable kernel layer (`/mnt/raid0/llm/kernels/production/<backend>`), so
this projection is exact rather than inferred.

**This is what makes the four kernels independently upgradable.** A whisper.cpp
upgrade cannot regress a role that never calls whisper.cpp, so it is not gated on
one. Today the `cpu` backend serves 10 roles across 5 distinct models; `gpu`, `stt`
and `tts` serve none, so a kernel freeze for those gates on nothing from the stack
and needs only its own functional evidence.

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

4. **Pair every speed number with a correctness check.** A kernel that is faster and
   wrong is a regression. Speculative decoding must not change output.

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
   readelf -d <build>/bin/llama-server | grep RUNPATH   # must be $ORIGIN[:/opt/rocm/lib]
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

   6d. **Archive the outgoing target by its RESOLVED path, then repoint:**

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

   Neither registry changes. No launcher changes. The binary name is unchanged by
   design — that is what lets the orchestration apparatus keep working untouched.

7. **Re-verify after promotion** (step 5 again, against the new target), then record
   the freeze with its ratification artifact and evidence hashes.

## Gate

A regression outside tolerance on any cell blocks the freeze **for that backend
only**. Roll back by repointing the symlink to the archived target — no config edit,
no recompile, no restart of anything that was not already serving that backend.

## What this does not cover

Changing *which* backend a role uses is a topology change, not a kernel freeze. That
is a `stack_topology.yaml` / role-assignment edit plus a recompile, and it gates on
the stack-change pipeline rather than on this runbook.
