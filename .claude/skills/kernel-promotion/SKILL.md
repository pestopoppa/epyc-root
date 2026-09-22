---
name: kernel-promotion
description: Run the production kernel promotion end to end — derive scope, prove the rollback anchor, build a relocatable candidate, gate it against the incumbent on speed and quality, emit ONE ratification package for the operator to sign, then cut the freeze and verify it serves. Use when promoting a champion kernel to production (v-next), or when asked to run the kernel promotion runbook.
---

# Kernel Promotion

One entry point for promoting a champion kernel to production. The operator asks for a promotion;
this skill derives every fact it needs, runs the gates, and stops ONCE for a signature.

## The contract

```
0. rollback anchor   archive the OUTGOING kernel, versioned + self-contained, and PROVE the rewind
1. derive scope      run kernel_freeze_scope.py — never quote prose
2. build candidate   relocatable ($ORIGIN), COMPLETE target set, in kernels/builds/
3. pre-flight        RUNPATH assertion · standalone linkage · binary-set parity vs the anchor
4. gates             speed + quality per derived model, against the CURRENT floor
5. package           one artifact: gates, digests, manifests, the ln -sfn diff, the REWIND command
6. OPERATOR SIGNS    one signature, one place  ← the only human gate
7. freeze            branch cut · overlay bake · verifier constants · CLAUDE.md block · repoint
8. post-promotion    derived-artifact regen · marker sweep · champion reseed · serving proof
```

**The promotion is not complete until step 7 finishes.** A store repoint alone is a HALF
promotion: production serves the new kernel while `verify_llama_cpp.sh` still attests the old one
and passes. Never report a repoint as a completed promotion. (2026-09-22: reported twice.)

## Why this is a skill and not a runbook

Every factual claim a prose runbook makes about this system rots. Measured 2026-09-21/22, all in
one promotion: the scope counts in the prose were stale AND the promotion then broke the scope
tool itself; "Neither registry changes. No launcher changes." was false (21 files); the guard's own
remediation string pointed at a numa-blind wrapper that compiles the wrong lineup; there was no
binary-set check, so a 2-binary kernel was promoted where the incumbent shipped 92; and there was
no relocatability assertion, so the candidate was not promotable at all.

So: **derive, never describe.** Run the tool instead of quoting its output. Assert mechanically
instead of eyeballing a grep. Diff against the anchor instead of trusting a hardcoded list.

## Step 0 — the rollback anchor, FIRST

The most load-bearing step, and the one the old runbook made impossible. `kernels/archive/` sat
empty from 2026-07-31 to 2026-09-21 because step 6 said to archive "the old build dir" while
`production/<B>` pointed INSIDE a source tree at an accretive artifact directory — there was no
old build dir. The anchor was materialised on 09-21 and **needed within hours**, when a promoted
kernel turned out to be incomplete.

```bash
scripts/anchor.sh <backend>     # archive + verify the OUTGOING kernel; refuses if it cannot rewind
```

The anchor must be a versioned, self-contained directory (`$ORIGIN`, linkage proven with
`LD_LIBRARY_PATH` UNSET), carry `PROVENANCE.md` + `SHA256SUMS`, and the rewind must be
**demonstrated**, not assumed. A drill that depends on an anchor a later step creates is not a drill.

## Step 1 — derive scope

```bash
scripts/scope.sh                # both backends, reconciled against the derived priors
```

Never trust prose counts. Derive scope BEFORE the repoint and again AFTER the step-8 regen —
never in between, when the priors still name the outgoing build dir.

**Never add a path-substring backend marker.** Two consumers classified backend by sniffing a
build path (`"build-hip" in p`; `hip|rocm|gfx` on argv[0]). The moment the store pointed at a
versioned dir, one reported `gpu: 0 roles` and the other reported every GPU role as `cpu` —
silently. Resolve through `kernel_paths.backend_dir()`.

## Steps 2-3 — build and pre-flight

`scripts/preflight.sh <build-dir> <backend>` asserts, and FAILS on:
- RUNPATH is exactly `$ORIGIN[:/opt/rocm/lib]` — no absolute paths, **no empty element** (an empty
  element makes the loader search the CWD). `grep RUNPATH | grep ORIGIN` passes on
  `/abs/path:$ORIGIN` and is not an assertion.
- ggml resolves inside the tree with `LD_LIBRARY_PATH` **unset**.
- **binary-set parity vs the anchor**, executables only. Sonames are versioned and will always
  differ; comparing `ls -1` can never be empty.
- the companion tools the orchestrator resolves through the store exist.

## Step 4 — gates

Speed per derived model, candidate vs incumbent, **each at its own best recipe** (recipe-to-recipe;
never force one kernel through the other's configuration). Quality per the incumbent's recorded
suites, same pinned questions and seed.

**Do not gate on text equality.** Spec-dec-on vs -off is not bitwise stable and the INCUMBENT fails
it too — different batch shapes change float summation order and flip argmax at near-ties. Quality
evals are the gate; `P-PARITY-1` (n>=5) if parity is wanted, never a 1-prompt smoke check.

## Step 5 — the package

`scripts/package.sh` emits one artifact with a REQUIRED key set:
`relocatable_runtime`, `rollback_rehearsal`, `binary_set_parity`, `linkage`, `speed`, `quality`,
`serving_floor`, plus digests, manifests, the exact `ln -sfn` diff, and the **rewind command**.

The required keys exist because v9's qualification carried `relocatable_runtime` and
`rollback_rehearsal` and v10's silently dropped both. A fixed schema makes a gate impossible to lose.

## Step 6 — the signature

Stop. A production freeze/cutover is a human-only trust boundary. Present the package; do not move
the symlink, cut the branch, or edit a verifier without it.

## Step 7 — the freeze (operator-authorized)

Branch cut at the candidate commit, frozen tree checked out to it, **agent-file overlay baked**
(`docs/reference/agent-config/llama-tree-overlay/`), cutover manifests, ratification artifact
mirroring the previous freeze's schema, `verify_llama_cpp.sh` constants, the CLAUDE.md freeze
block, and the store repoint.

Expect the permission classifier to gate writes to the frozen clone. That is correct — surface it
rather than routing around it.

## Step 8 — post-promotion

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py update
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

The derived layer pins a resolved `binary_dir`/`binary_path`/`ld_library_path` PER ROLE, so it goes
stale the instant the symlink moves. **Never** use `python -m src.registry.stack_priors` or the
guard's `RECOMPILE_PRIORS_COMMAND`: no `--numa-mode`, compiles the legacy single-instance lineup
while production declares `numa_mode: both`.

Then: marker sweep, champion reseed off the newly frozen kernel, and prove it serves —
`scripts/verify_serving.sh` checks argv[0], **`/proc/<pid>/maps`** (three ggml generations live on
this host; a binary inheriting the wrong tree's ggml answers normally and computes wrong, and `ldd`
cannot settle it because llama.cpp dlopens `libggml-hip.so`), per-port health, and real inference.

## Never

- report a store repoint as a completed promotion
- skip the stack-change gate (`accepted_gaps.yaml`: "A bypass used four times running is not an
  escape hatch, it is the new default")
- promote a candidate built with a partial `--target`
- trust a scope number you did not just derive
