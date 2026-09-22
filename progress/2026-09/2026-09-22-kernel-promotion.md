# 2026-09-22 — v10 kernel promotion (store cutover) + promotion-runbook hardening

Session: post-BIOS rebench → champion qualification → v10 store cutover → runbook audit.
Host: EPYC 9655 NPS4, memory interleave ON, 5600 MT/s (operator-applied at reboot).

## What landed

| Area | Change |
|---|---|
| Champion defects | `llama-model.cpp` nextn read/assert restored to v9 ordering (gemma4-assistant exempted from the early generic read); `llama-graph.cpp` MoE fusion gated on all-CPU backends |
| Kernel store | `kernels/production/{cpu,gpu}` → `builds/{cpu,gpu}-20260921-ffc1bac82`; `archive/{cpu,gpu}-20260810-0db32c06e` populated for the first time since 2026-07-31 |
| Store wiring | `scripts/lib/env.sh` (root + orchestrator) store-resolved, fail-closed; `scripts/lib/executor_paths.py` `base_dir` from `backend_dir("cpu")` (fixed a split-brain where executor launched v9 while everything else ran v10) |
| Verification | NEW `scripts/session/verify_kernel_store.sh` (symlink → target → binary → ggml linkage, per backend, incl. companion tools); wired into `session_init.sh` §0.55 |
| Freeze scope | `scripts/validate/kernel_freeze_scope.py::_backend_of()` resolves via `backend_dir()` instead of a `"build-hip" in p` substring — fixed gpu 0→4 roles, cpu 12→8 |
| Dashboard | `src/api/routes/dashboard_topology.py` `_is_gpu_binary()` resolves through the store — GPU roles no longer report substrate `cpu` |
| Skill | NEW `.claude/skills/kernel-promotion/` — 9-phase contract, rollback anchor as phase 0, plus `anchor.sh` / `preflight.sh` / `verify_serving.sh` |
| Provenance | `PROVENANCE.md` written into both `builds/*-20260921-ffc1bac82/`; `artifacts/operator/v10-cutover-20260922-ffc1bac82/` holds 4 manifests (448 files) + `journal.json` |

## Measurement discipline

Operator ruling, binding: **no baselines — max-performance numbers only.** An unlabelled
spec-dec-off table was presented early in the session and retracted; both banked artifacts now
carry warning banners. Comparison grammar for promotion is *max-performance recipe on v9 vs
max-performance recipe on the candidate*.

## Rollback was exercised for real

A first promotion attempt shipped a partial build (`--target llama-server llama-bench` → 2
binaries vs 92). It was rolled back through the archive anchor, rebuilt in full, and the verifier
was extended to count companion tools so the same shape cannot recur.

## Status: promotion is INCOMPLETE

The **store side** is done and serving. The **freeze side** is not: there is no
`production-consolidated-v10` branch, no `FREEZE-V10` ratification, and `verify_llama_cpp.sh`
still attests v9/10125 while the store serves 10303.
`artifacts/operator/v10-qualification-20260921-ffc1bac82.json` records this as `INCOMPLETE`,
including both earlier overstatements rather than erasing them.

Blocked on one operator-run command (the branch cut in the frozen tree); the command has been
handed over verbatim. Everything downstream — ratification artifact, verifier constants, the
CLAUDE.md freeze block, and the champion reseed off the newly frozen kernel — is sequenced
behind it.

## Known residue

The v10 binaries' RUNPATH ends in an empty element (`$ORIGIN:`), so the loader also searches
CWD; v9's archive is clean. Harmless here, fix at the next rebuild. (My own RUNPATH check
initially had the very bug it was written to catch — `tr ':' '\n'` drops the trailing empty
field; fixed with awk field splitting.)

## Deferred to the stack-change window

R23-65 CPU floors (42 launches), R23-64 thread sweep (18 launches), speech `$ORIGIN` rebuild,
Flash-Next quality gate, the lineup change (C1–C4 decisions outstanding), and the disk deletion
of the deprecated gemma4 / Qwen3.5-122B / Next-80B weights at session end.

---

## Addendum — the freeze was cut (operator, 2026-09-22)

The operator ran `git branch production-consolidated-v10 ffc1bac82`; I completed the checkout.
Promotion is now **COMPLETE on both sides**, store and freeze.

| Check | Result |
|---|---|
| frozen tree branch / HEAD | `production-consolidated-v10` @ `ffc1bac82` |
| ancestry | `git merge-base --is-ancestor 0db32c06e ffc1bac82` → true: a clean version-past, not a patch in place |
| tracked state | clean — **no commit was made in the frozen tree** (see overlay note) |
| store binaries | cpu + gpu both `version: 10303 (ffc1bac82)`, digests match the attestation |
| ggml linkage | launch-recipe AND ambient both resolve in-tree, per backend |
| live residency | `/proc/<pid>/exe` and `/proc/<pid>/maps` on three running servers all point into `builds/{cpu,gpu}-20260921-ffc1bac82/bin`; the GPU server maps `libggml-hip.so.0.16.0`, is in `/sys/class/kfd/kfd/proc/`, VRAM 94% |
| serving | a real completion through `frontdoor` returned the exact requested string |
| AutoKernel | `production.resolve_frozen()` returns `('ffc1bac82…', 'production-consolidated-v10')` with **zero intervention** — it reads the tree live and checks only the branch prefix. This confirms the operator's expectation that promotion should not have to do anything to AutoKernel. |

### The overlay bake: deliberately NOT a commit

`ffc1bac82` already carries the EPYC overlay `CLAUDE.md`, inherited through the v9 bake, and its
text is branch-generic (*"production-consolidated-vN; check `git branch --show-current`"*). The
staged overlay differs only in two lines of an HTML comment. Committing that into the frozen tree
would have broken the `HEAD == binary-embedded-commit` correspondence — the binaries report
`version: 10303 (ffc1bac82)` — to change a comment. The two-line drift is carried forward to the
next promotion's experimental-branch bake, where it costs nothing. Recorded in the attestation.

### `verify_llama_cpp.sh`: re-pinned, and re-pointed at the store

Two changes, and the second is the substantive one. v10 is the **first production kernel served
from the kernel store rather than the source tree's own `build/` and `build-hip/`** — those dirs
still hold the v9 binaries. The verifier was checking them, so left alone it would have attested
a kernel that serves nothing. Source identity (branch, commit, clean tree) still comes from the
frozen tree; binary identity (version, digest, ggml linkage) now comes through
`kernels/production/{cpu,gpu}`.

One subtlety cost a false failure first: `check_linkage` used a logical `pwd`, so it compared the
symlink spelling against the loader's `$ORIGIN`, which expands to the **real** directory. Every
correctly-resolved library reported BAD on a pure string mismatch. Fixed with `pwd -P`, which
makes the spellings agree without weakening the check.

### Ratification is prepared, not self-signed

`artifacts/operator/ratify_v10_final_freeze_20260922.json` + `scripts/operator/ratify_v10_final_freeze_20260922.sh`.
`--apply` verifies the live freeze first and refuses on mismatch, then stamps `ratified_at`, then
hashes the stamped artifact and rewrites CLAUDE.md's freeze paragraph with that digest. The hash
has to be written in the same transaction as the file it describes, which is why it is a script
and not a hand edit.

**Known transient**: the verifier attests v10 from this commit while CLAUDE.md still names v9.
That is the correct direction — the verifier must describe the kernel that is actually serving —
and `--apply` closes it.
