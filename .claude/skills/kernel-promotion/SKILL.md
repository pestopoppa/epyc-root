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
1. derive scope      scripts/scope.sh — never quote prose
2. build candidate   relocatable ($ORIGIN), COMPLETE target set, in kernels/builds/
3. pre-flight        RUNPATH assertion · standalone linkage · binary-set parity vs the anchor
3b. LOAD-ONLY        scripts/loadcheck.sh — open every in-scope (model, drafter) pair, once
4. gates             promotion_gates.yaml: speed + quality per derived model, vs the CURRENT floor
5. package           scripts/package.sh — one artifact, fixed key set, the REWIND (all 3 steps)
6. OPERATOR SIGNS    one signature, one place  ← the only human gate
7. freeze            branch cut · overlay bake · verifier constants · CLAUDE.md block · repoint
8. stack change      hand to `stack-change` phases 7–8; do not re-implement them
9. post-promotion    marker sweep · champion reseed · serving proof
```

**The promotion is not complete until step 9's serving proof passes.** A store repoint alone is a
HALF promotion: production serves the new kernel while `verify_llama_cpp.sh` still attests the old
one and passes. Never report a repoint — or a freeze with the derived layer unregenerated — as a
completed promotion. (2026-09-22: reported complete twice while the freeze side was undone.)

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
scripts/scope.sh                       # both backends, reconciled against the store
scripts/scope.sh --backend gpu --json scope-gpu.json
```

It refuses three things, each of which produced a WRONG derived answer rather than an
absent one: an **empty** backend scope (a gate of zero roles silently skips half a
promotion); a scope whose `binary_path` does not resolve to the current
`kernels/production/<backend>` target (the priors pin the RESOLVED build dir, so between
a repoint and the phase-9 regeneration they name the OUTGOING kernel); and a role
pointing at a GGUF that no longer exists.

Never trust prose counts. Derive scope BEFORE the repoint and again AFTER the step-8 regeneration
— never in between, when the priors still name the outgoing build dir. `scope.sh` refuses a scope
taken in between rather than returning it.

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

## Step 3b — load-only preflight, BEFORE any bench

```bash
scripts/loadcheck.sh <build-dir> --backend cpu          # dry run: asserts, loads nothing
scripts/loadcheck.sh <build-dir> --backend cpu --apply  # one load per (model, drafter)
```

One load per **distinct (model, draft model) pair** in the derived scope, at a small
context, `--no-warmup`, no requests. Minutes.

The pair, not the model, is the unit: on 2026-09-22 the champion could not load the
**gemma4 MTP drafter** — contradictory `n_layer_nextn` invariants for a standalone NextN
head — and four of eight gated CPU roles were unservable. A target-only load passes that.
It was found by a failed bench arm an hour into a bench window; this check would have
found it before the window opened.

`--apply` starts one server at a time and stops **the PID it captured**: SIGTERM, confirm
dead, escalate to SIGKILL. It never matches a process name.

## Step 4 — gates

Speed per derived model, candidate vs incumbent, **each at its own best recipe** (recipe-to-recipe;
never force one kernel through the other's configuration). Quality per the incumbent's recorded
suites, same pinned questions and seed.

**Which suites, which roles, what n: [`promotion_gates.yaml`](promotion_gates.yaml).**
Before it existed, "the incumbent's recorded suites" resolved to nothing — v9 and v10
both ran MMLU-Pro + GPQA on `worker_general` and `architect_critic` at n=200/195 by
convention carried in someone's head. `package.sh` reads that file and refuses a package
that gates on less than the incumbent did. Adding a gate there makes every later package
fail until it carries one; removing one, or lowering an n, is an operator decision and
goes in `waivers` with the signature that carried it.

**Do not gate on text equality.** Spec-dec-on vs -off is not bitwise stable and the INCUMBENT fails
it too — different batch shapes change float summation order and flip argmax at near-ties. Quality
evals are the gate; `P-PARITY-1` (n>=5) if parity is wanted, never a 1-prompt smoke check.

## Step 5 — the package

```bash
scripts/package.sh --candidate <sha> --out <file> [--evidence <dir>]
scripts/package.sh --check <file>       # validate one that already exists
```

The required key set is **not a list in the script** — it is every gate marked
`required: true` in `promotion_gates.yaml`, so the schema and the gates cannot drift
apart. `package.sh` derives the store facts itself (resolved target, `llama-server`
digest, `--version`, the newest archive anchor, the rewind commands) and folds in one
`<gate>.json` per gate from `--evidence`. It exits non-zero naming every missing gate,
every gate whose result carries numbers but **no `status`**, and a `rollback` section
without its `regeneration_command`.

The required keys exist because v9's qualification carried `relocatable_runtime` and
`rollback_rehearsal` and v10's silently dropped both. Run against v10's own qualification
artifact on 2026-09-22 it named exactly those two, plus `binary_set_parity` and the
`store`/`rollback`/`scope` sections. A fixed schema makes a gate impossible to lose.

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

## Step 8 — the stack change. COMPOSE, do not re-implement.

**A promotion ENDS IN A STACK CHANGE.** Moving the store symlink changes what every role
launches, which is the same event as changing the lineup: same compile order, same guards,
same serving proof. So this phase is [`stack-change`](../stack-change/SKILL.md) **phases
7–8**, called, not copied. Do not re-derive its order here and do not write a second
bring-up path.

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py update --numa-mode <declared>
uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate
```

The derived layer pins a resolved `binary_dir`/`binary_path`/`ld_library_path` PER ROLE, so it goes
stale the instant the symlink moves — **in either direction**, which is why a rewind is three steps,
not two (`anchor.sh` prints all of them). **Never** use `python -m src.registry.stack_priors` or the
guard's `RECOMPILE_PRIORS_COMMAND`: no `--numa-mode`, compiles the legacy single-instance lineup
while production declares `numa_mode: both`.

If the promotion also changes which models serve, it is not two workflows: state the intent and run
`stack-change` from its phase 0, with this skill's phases 0–7 as its kernel input.

## Step 9 — post-promotion

Marker sweep, champion reseed off the newly frozen kernel, and prove it serves —
`scripts/verify_serving.sh` checks argv[0], **`/proc/<pid>/maps`** (three ggml generations live on
this host; a binary inheriting the wrong tree's ggml answers normally and computes wrong, and `ldd`
cannot settle it because llama.cpp dlopens `libggml-hip.so`), per-port health, and real inference.

## Never

- report a store repoint as a completed promotion
- skip the stack-change gate (`accepted_gaps.yaml`: "A bypass used four times running is not an
  escape hatch, it is the new default")
- promote a candidate built with a partial `--target`
- trust a scope number you did not just derive
- bench before `loadcheck.sh` has passed over the derived scope

## Known gaps — code changes outside this skill (audit §4.6)

These are recorded, not deferred-and-forgotten: each needs a change in a repo this skill
does not own, so the skill names them at the point where it hits them.

- **§4.6.5 — step 7 hand-edits `verify_llama_cpp.sh` constants and the AutoKernel
  `PRODUCTION_BRANCH/COMMIT` pins.** Restated derivation: the ratification artifact
  should be the single expectation source that all of them read. Until then, re-pin every
  one of them in the same commit as the freeze and check them by `git rev-parse X == Y`
  **plus** "X is the branch the ratification names" — never by the branch existing, which
  is how AutoKernel stayed silently anchored to v9 after the v10 promotion.
- **§4.6.6 — the ratify script is per-promotion** (`ratify_v10_final_freeze_20260922.sh`,
  143 hand-written lines). It should be `ratify_kernel_freeze.sh --version N`, with
  `--apply` performing the branch cut and overlay bake under the operator's hands — the
  manual cut took two attempts (11:45, then 11:56 "already exists").
- **§4.6.9 — the champion reseed was 21 hand-touched files** (`61364621`). It needs a
  script that rewrites the pins from the ratification artifact.
