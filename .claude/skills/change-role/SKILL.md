---
name: change-role
description: Move a role onto a different server, swap the model a host role serves, or turn an alias into its own server — classify which of the three it is first, then edit every surface that restates the binding. Use when a role changes host or model, when editing shared_with / alias_of / model_role, or when following the role-alias change runbook.
---

# change-role

A sub-skill of [`stack-change`](../stack-change/SKILL.md), invoked from its
**phase 2 (transform)**; its assertions run in **phase 3 (preflight)** and its
proof in **phase 8 (bring up)**. It never runs against a real tree before the
operator signs — pass `--scratch <dir>`.

It **absorbs** `epyc-orchestrator/docs/runbooks/role-alias-change-runbook.md`
(2026-07-22, WP-13). Everything load-bearing in that runbook is below; what is
not below is superseded or is WP-12 context the runbook itself flags.

Read [`stack-change/DERIVATION.md`](../stack-change/DERIVATION.md) first.

## Concepts, in one place

- A **host role** owns a physical llama-server fleet. An **alias role** has no
  process of its own — it rides its host's server(s). Same GGUF, one server:
  same-model roles share ONE server, and roles are a remappable logical layer
  over servers.
- **The single declarative truth is the host's `shared_with` list** in
  `server_mode` of the master registry. `registry_compiler.py` reads THAT to
  resolve an alias to its serving process.
- **`alias_of` is documentation.** It is not a binding and never has been.
- Aliases keep their role-layer identity elsewhere — `roles:` entry, timeouts,
  prompts, sampling. Those stay per-role.
- `evidence.alias_overrides` exists ONLY for model-conflict aliases (ghost
  bindings). Same-model aliases are declared ONLY by `shared_with`; tooling that
  treats "has alias_overrides" as "is an alias" silently exempts the HOST from
  validation, because descriptors are model-keyed and the host carries a copy.

## Phase 2a — CLASSIFY FIRST. This is the whole point.

```bash
scripts/classify.py <role> --alias-of <host>     # candidate (a)
scripts/classify.py <role> --to <model-row-id>   # candidate (b)
scripts/classify.py <role> --own-server          # candidate (c)
```
Exit `0` (a)/(b) · `3` it is (c), **route to `change-topology`** · `2` the
request contradicts the sources · `1` usage. It prints the change set.

**The blast radius differs by an order of magnitude**, which is why the shape is
decided before anything is edited rather than discovered from the third error
message:

| shape | what it is | reaches |
|---|---|---|
| **(a) alias re-point** | the role moves onto another host's server | 8 restatements, launches nothing new |
| **(b) model swap on a host** | same role, new model | the serving shape, capacity on both legs, drafter pair, fresh evidence |
| **(c) alias becomes its own server** | it gains a process | cpusets, ports, the contention-matrix recert cascade — **not this skill** |

### (a) alias re-point
`shared_with` on the new host (append) and the old (remove) · the alias's own
`server_mode` row deleted, or kept ONLY as routing metadata carrying the host's
port/url/`model_role` and **no** `numa_ports` · **delete** its `numa_config`
block and its `role_launch_meta` entry · `roles.<alias>.model` set to the host's
artifact · `port_map` · `models.py` `ServerURLsConfig` delegation to
`_server_url_default("<host>")` · `src/roles.py` `_FALLBACK_MAP` (do not add
same-fleet edges — they are retry-the-same-metal no-ops that produced 90x churn)
· procedure enums regenerated.

### (b) model swap on a host
`server_mode.<role>` model / `model_path` / `model_role` / `serving_shape` ·
**`serving_shape` is DERIVED from the GGUF header, never hand-computed** ·
drafter compatibility re-validated (`draft-compat`) · `roles.<role>.model` and
every rider's `roles.<alias>.model` · capacity recomputed on both legs · quality
and speed evidence for the new model **in this role** → `needs-measurement`.

> `kv_kib_per_token_f16` hand-computed from the documented formula over-declared
> six models by **4.06x** on 2026-09-22: Qwen3.6/3.8 set
> `full_attention_interval: 4` and the formula counted every layer. Two hours,
> one discarded lineup revision, one wasted GPU sweep.

### (c) alias becomes its own server
`change-topology`. It gains a `server_mode` row, a `numa_config` block, a
`role_launch_meta` entry and a port; that changes cpusets, so the §H
contention-matrix recert cascade applies. Treat it as a lineup event, not an
alias edit.

## Phase 3 — assert, before the package is built

```bash
scripts/assert_alias_clean.py --alias A --host H [--scratch DIR]
scripts/assert_alias_clean.py --all                # sweep every declared alias
```
Exit `2` on any refusal below. Every check recomputes the binding from
`shared_with` and diffs; none compares one restatement to another.

Then the pipeline gates that already exist, in the documented order — **lean
first, and a failure there stops everything**:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/registry/stack_change_pipeline.py check --numa-mode <declared>
```
Alias semantics the guard enforces: alias `serving.ports`/endpoint **==** the
host's launch row; alias launch entries port-contained in the host's; runtime
validated on the host row only — an alias's stored runtime is historical residue,
because it RUNS under the host's runtime.

## Phase 8 — prove it, with the before/after snapshot

```bash
scripts/url_snapshot.sh capture <before.tsv>     # BEFORE any edit lands
#   ... stack-change phase 7 applies and recompiles ...
scripts/url_snapshot.sh capture <after.tsv>
scripts/url_snapshot.sh diff <before.tsv> <after.tsv> <the role you moved>
```
Exit `2` if **any other role's URL moved** — the change reached further than the
intent did. Do not reload; go back to the transform. The field list is
enumerated from the dataclass, not typed into the script, because a hand-kept
role list is one more restatement and goes stale on exactly the change this
script is used for.

Then a **real completion through the alias name** — not a `healthy` status.
Give it a real token budget: with thinking enabled, reasoning bills against the
same budget as content, so a small `max_tokens` returns EMPTY content and looks
exactly like a broken role.

If the alias carries real traffic, prove the spread with per-port task counts
from the llama logs, **not** instantaneous busy-slot sampling — short
generations make instant busy counts near-zero even at full 4-wide spread.

## REFUSES

- **`alias_of` without `shared_with`.** `server_mode.worker` had the first and
  not the second on 2026-09-22; the registry validator could not resolve its
  `numa_ports` to any launching topology and refused to start the stack — *"a
  fleet nothing launches is a phantom"*. `alias_of` is documentation; the list is
  the binding.
- **An alias that still declares its own process** — its own `numa_ports` /
  `numa_instances`, or a `port` differing from its host's. The dead-:8070
  `coder_escalation` row was exactly this. (A routing-metadata row carrying the
  host's own port is legal and several aliases use it.)
- **An alias with a `numa_config` block or a `role_launch_meta` entry.** A role
  with no process must carry no NUMA wiring. Leaving `worker_general`'s and
  `ingest_long_context`'s blocks in place kept the launcher declaring
  :8072/:8082/:8182 and :8085/:8185/:8285 against a master that no longer had
  those ports — the declaration-parity violation that blocked the cutover.
- **A `model_role` pointing at an artifact that differs from the host's.**
  `frontdoor.model_role` named the NON-MTP `qwen36_q8_0` while the process ran
  the MTP artifact; `compile_descriptors` refused it with `Role-server conflict`
  the moment the worker lane joined via `shared_with`. `model_role` is
  load-bearing — `model_descriptors.py` substitutes that row's config for an
  alias.
- **`roles.<alias>.model` naming an artifact from a previous lineup.**
  `roles.worker_math` named Qwen2.5-Math-7B and `roles.toolrunner` named
  Qwen3-Coder-30B — artifacts those roles had not been served by for two
  lineups. Same `Role-server conflict`.
- **`port_map` disagreeing with the host's port.** It is a restatement of
  `shared_with`; the manifest's own header says Phase 2 stops restating it.
- **Assigning a live role to a deprecated model.** The mirror of the defect that
  blocked the 2026-09-22 cutover; see `retire-model`.
- **A reasoning-effort setting that trips the L0–L4 ladder without
  certification** (`orchestration/reasoning_effort_certifications.yaml`).
- **Pointing an alias at another alias.** Name the host that owns the process.

## Never

- **Never hand-edit `stack_priors.yaml`, the runtime-facts manifest, the lean
  registry, descriptors or the procedure enums.** Regenerate. A stale derived
  file reports a *content* error — "Role-server conflict" sends you hunting a
  wrong model name when the real answer is that you have not recompiled.
- **Never reload while an eval or measurement is running.** SIGSTOP the eval
  runner, reload, SIGCONT. The eval client has no reconnect backoff; a naked
  reload burned 532 questions on 2026-07-22 and ~680 before that.
- **Never restart llama servers for an alias change.** No process moves:
  `orchestrator_stack.py reload orchestrator` only, and do not stop autopilot
  (it reconnects). Reload is executed by the session that owns the inference, at
  its own boundary.
- **Never add a same-fleet `_FALLBACK_MAP` edge.** Retry-the-same-metal
  masquerading as failover.
- **Never read the NUMA mode with a bare `env_stack_numa_mode()`** — it defaults
  to full. Any new reader uses `scripts/server/realized_fleet.py`.
- **Never fix one surface per pipeline run.** Nine runs in sixteen minutes with
  the stack down, while the package's own text had already named `numa_config`
  and `launch_manifest` as consequences. Classify, enumerate, patch once.
- **Never declare the change done on a green `/health`.** That is transport-only.

## Composes with

`retire-model` (re-point live roles off a model before it is deprecated) ·
`change-topology` (shape (c), and any cpuset or device move) ·
`stack-change` (the only entry point, the only signature).
