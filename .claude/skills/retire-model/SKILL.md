---
name: retire-model
description: Take a model out of the serving lineup — enumerate every reference to it across both repos, mark it deprecated with the three-key marker while its weights stay on disk, and later record the graveyard row once the operator has deleted them. Use when a model leaves the lineup, when a registry row must be deprecated, or when a deleted GGUF needs its ledger entry.
---

# retire-model

A sub-skill of [`stack-change`](../stack-change/SKILL.md). It is invoked from that
skill's **phase 2 (transform)** and its assertions run inside **phase 3
(preflight)**. It never runs standalone against a real tree: pass `--scratch
<dir>` so every check reads the same bytes the operator will sign.

Read [`stack-change/DERIVATION.md`](../stack-change/DERIVATION.md) first. The
master registry is the only source here; the lean registry, descriptors and
priors are OUTPUT and must never be hand-edited to "finish" a retirement.

## The lifecycle is three states, and both transitions already exist

```
live  ──(1) deprecate──▶  deprecated  ──(2) record deletion──▶  deleted
                          three-key marker on the row,           deprecated_models:
                          GGUF STAYS ON DISK                     graveyard row with
                          precedent: roles.reap_246b             `deleted:` + `path_was:`
                                                                 precedent: commit 7bc650b8
```

**Verified on the live registry, not quoted**: 47 `roles.*` rows carry
`deprecated:`/`deprecated_date:`/`deprecated_reason:`; `deprecated_models:`
holds 77 graveyard rows keyed `model / path_was / size_gb / reason / deleted`.
Both states are in production today; this skill adds no schema.

**The two transitions are different changes with different signatures.**
Transition 1 is a lineup change and rides `stack-change`. Transition 2 is
bookkeeping AFTER the operator has deleted weights by hand — it changes nothing
the compiler reads, and it is a lie if the file is still there.

## Phases

Numbering is `stack-change`'s. This skill owns 2, contributes to 3, and owns the
model-specific half of 9.

### 2a — enumerate, before touching anything

```bash
scripts/enumerate_refs.py <model-row-id> [--stage deprecate|delete] [--scratch DIR]
```

Exit `0` permitted · `2` refused · `1` usage. Every reference is classified
`BLOCK` / `MUST-EDIT` / `ADVISORY`, and **the MUST-EDIT rows ARE the change
set** — they go into the patch, not into prose. Surfaces enumerated:

| surface | why it is here |
|---|---|
| `roles.*` rows naming the model or its GGUF | another row keeps the same file load-bearing |
| `server_mode.*` — row key, `model_role`, `model`/`model_path` | the three ways a server resolves to a model |
| `shared_with` riders | every alias on that process is retired or re-pointed WITH it |
| `launch_manifest` `port_map` / `role_launch_meta` | the launcher's own restatements |
| `stack_topology.numa_config` | a role with no process must carry no NUMA wiring |
| `orchestration/procedures/*.yaml` role enums | generated from the registry; stale enums fail late |
| `stack_templates/*.yaml` | what `start` ACTUALLY launches |
| drafters targeting it (`draft_model`, `compatible_targets`, `dflash_drafters`) | a target/drafter pair is only valid as a pair |
| canonical recipes under `artifacts/serving-recipes/` | a recipe naming a retired artifact runs and lies |
| AutoKernel campaign pins | a pin that stays "valid" because the thing still exists |
| `src/config/models.py`, `src/roles.py` | alias delegation lives in CODE |
| evidence citations | `check_evidence_durability.py` — a hash with no artifact is an assertion |

Role names are matched with word boundaries and only on the two small
role-keyed surfaces. `worker` as a substring matched `controller-worker:` and
reported 900 AutoKernel "pins" on this script's first run — the same defect
shape as classifying a backend by `"build-hip" in path`.

### 2b — refuse while anything live holds it

```bash
scripts/assert_not_mapped.sh <gguf-path> [...]
```
Read-only `/proc` walk over **both** `cmdline` (what was asked for) and `maps`
(what is resident). Exit `2` names the holding PIDs. It never signals anything
and never matches on a process-name pattern.

### 2c — derive the dependent removals into the patch

Not into prose. The `numa_config` block, the `role_launch_meta` entry, the
vacated port, the freed host memory (as a capacity-report delta), the procedure
enum entries, and the `roles.*` model-name corrections for every alias that rode
the retiring process.

### 3 — hand the classified list to `stack-change` preflight
`BLOCK` → the transform is not finished. `needs-measurement` for a model that
INHERITS a retired model's roles. `needs-operator` only for a genuine choice.

### 6 — the operator signs `stack-change`'s package
Retirement does not have its own signature.

### 9 — verify
```bash
scripts/verify_retired.py <model-row-id> --stage deprecate [--graveyard-was N]
```
Asserts the three-key marker is complete and parseable, the reason is not a
stub, **nothing live resolves to the row any more**, the graveyard did **not**
grow (a deprecation marks; it does not reclaim), and the weights are still on
disk. `--stage delete --graveyard-was N` instead asserts the graveyard grew by
exactly one, that row carries `deleted:` and `path_was:`, and the file is
actually gone.

## REFUSES

Each of these was earned on 2026-09-21/22 or is written into the registry rows
themselves. A rule with its origin attached survives review; a bare rule gets
optimised away.

- **To mark a model deprecated while any LIVE role still resolves to it.**
  `qwen35_122b_q4km` was marked deprecated while `architect_critic` was still
  bound to it; `compile_stack_priors` refused the *whole file* with `Missing
  live server binding`, and the cutover stopped. Re-point the role first, in the
  same package (`change-role`). Resolution follows
  `stack_priors.py::_server_for_role` exactly — direct row, then `model_role`
  back-reference, then `shared_with` — because a check that resolves differently
  from the compiler is worse than no check.
- **To delete a GGUF. At all, ever.** Deleting weights is a separate operator
  action with its own confirmation. This skill marks rows and, afterwards,
  records what the operator deleted.
- **To write a `deleted:`/`path_was:` graveyard row while the file is still on
  disk.** That is a false ledger entry, and the ledger is what the next reclaim
  sweep trusts.
- **To deprecate a rollback anchor.** `roles.qwen35_122b_q4km` says it in its own
  reason text: *"this row is RETAINED UNMODIFIED ... precisely so the 122B
  remains restorable if the Flash-Next cutover fails its load or quality proof."*
  A model that is somebody's way back cannot be retired by the change that
  depends on it being there.
- **To deprecate a model a live drafter targets.** A target and its drafter are
  valid only as a pair (`draft-compat`). Self-draft — the MTP head inside the
  same file — is the exception, and the script says which case it found rather
  than making you guess.
- **To deprecate while a running server has the weights open.** The lineup would
  disagree with the fleet and `stack-change` phase 7's runtime attestation would
  fail on it. Drain and stop the role through `orchestrator_stack.py`.
- **To proceed on a partial marker.** All three keys or none: a row with
  `deprecated: true` and no reason reads as retired to a human and carries no
  record of why, and the reason field is where the measured history survives.

## Never

- **Never `pkill`/`pgrep` on a name pattern to find or clear a holder.** Shared
  host; a name pattern is a wildcard over other sessions
  (INC-20260731 — `llama-server -m` killed another agent's server twice, and
  `earlyoom` died because its argv lists what it protects). `assert_not_mapped.sh`
  excludes *itself* for the same reason: its own argv contains every artifact it
  was asked about.
- **Never move a row to `deprecated_models:` as part of a deprecation.** That
  skips a state.
- **Never edit the lean registry, descriptors or priors to make a retirement
  compile.** Recompile instead; a stale derived file reports a *content* error,
  which is what makes it expensive.
- **Never report a retirement complete on the strength of one file.** The 2026-09-22
  patch touched one file and needed eight more; the surfaces were found one
  pipeline run at a time with the stack down.
- **Never let `--allow-descriptor-model-removal` name a model the intent does not.**
  Read the removal set it prints and diff it against the intent.

## Composes with

`change-role` (re-point every live role off the model FIRST) ·
`change-topology` (the `numa_config` block a retiring host role leaves behind) ·
`stack-change` (the only entry point, the only signature).
