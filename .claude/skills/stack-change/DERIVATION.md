# The derivation graph — which files are SOURCE and which are OUTPUT

Read this before editing anything in a stack change. Every wasted hour on
2026-09-22 came from editing one source and leaving four others restating it, or
from hand-editing something that is generated.

## Hand-edited SOURCES

| File | What it owns |
|---|---|
| `epyc-inference-research/orchestration/model_registry.yaml` | **the master.** `roles.*`, `server_mode.*`, `serving_shape`, `shared_with`, deprecation markers |
| `epyc-orchestrator/orchestration/stack_topology.yaml` | `numa_config.<HOST role>` — instances, cpu_shape, policies, mlock, pre-evict |
| `epyc-orchestrator/scripts/server/stack_numa.py` | the cpu-shape table (`_CPU_SHAPES`, `_SHAPE_CLASSES`, undersubscription allowlist) |
| `epyc-orchestrator/src/registry/stack_priors.py` | stack-prior compilation and role resolution used by launch flags |
| `epyc-orchestrator/orchestration/launch_manifest.yaml` | `port_map`, `role_launch_meta`, fallback slots/contexts |
| `epyc-orchestrator/scripts/server/stack_commands.py`, `orchestrator_stack.py`, `stack_manifest.py` | command construction, lifecycle and manifest-backed launch defaults |
| `epyc-orchestrator/scripts/voice/` | speech launch wrappers, shim and declared layout |
| `epyc-orchestrator/src/config/models.py`, `src/roles.py` | alias delegation in CODE |
| `epyc-orchestrator/stack_templates/*.yaml` | what `start` actually launches |
| `/mnt/raid0/llm/kernels/production/<backend>` | the serving binary symlink |

The master registry is read from research origin/main by default; never sync or edit the shared research clone to make a rebuild work; pass `--research-registry` only for a deliberate alternative checkout.
The scratch package copies these source files for review. Run the pipeline from
a complete scratch **checkout**, not from this source-only package: generated
artifacts, imports, tests and dependencies are outside this list.

## DERIVED — never edit by hand

`epyc-orchestrator/orchestration/model_registry.yaml` (the LEAN copy) ·
`orchestration/model_descriptors.yaml` · `orchestration/derived/stack_priors.yaml` ·
`orchestration/procedures/*.yaml` role enums + `procedure.schema.json` ·
`docs/generated/current_stack_summary.md`

Editing a derived file is silently reverted at the next compile. Its staleness
also presents as a *content* error, which is what makes it expensive: you read
"Role-server conflict" and go looking for a wrong model name, when the real
answer is that you have not recompiled.

## Compile order — this IS documented, obey it

`stack_topology.yaml:5-8`, `stack_change_pipeline.py:1181-1281`, and
`stack-truth-precedence.md` all state it. `update` runs:

```
numa mode → LEAN registry → descriptors → priors → procedure enums → summary
          → guards (parity, all-surfaces, strict) → effort certs
          → stack-manifest registry → q_scorer → runtime attestation → promotion gate
```

Lean failing stops everything. Descriptors failing stops everything after it.
**Running a later step against an earlier stale output is the single most common
way to waste an hour**, because its error names content, not staleness.

## The rule that prevents the whole class

> **RESTATED DERIVATION.** A fact that is a function of a source must not be
> copied as a literal unless its gate RECOMPUTES it from the source and diffs.

Measured instances, all of which cost time on 2026-09-22: `kv_kib_per_token_f16`
hand-computed from a formula that ignored `full_attention_interval` (4.06x wrong
on six models); pins that stay "valid" because the branch they name still exists
(AutoKernel silently anchored to v9 after the promotion); a backend classifier
using a substring instead of resolving the path; `ldd`-vs-`/proc/maps` set
equality comparing two differently-gathered sets; and five surfaces —
`port_map`, `role_launch_meta`, `numa_config`, the procedure enums, `roles.*` —
each independently restating `shared_with`.

When you must restate, write the recompute-and-diff check in the same change.
