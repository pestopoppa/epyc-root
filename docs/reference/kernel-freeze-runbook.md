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

6. **Promote by moving the symlink, not by editing config:**
   ```bash
   ln -sfn <old build dir> /mnt/raid0/llm/kernels/archive/<B>-<YYYYMMDD>-<sha>
   ln -sfn <new build dir> /mnt/raid0/llm/kernels/production/<B>
   ```
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
