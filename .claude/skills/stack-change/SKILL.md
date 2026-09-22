---
name: stack-change
description: The single entry point for changing the serving lineup — retiring a model, moving a role, changing topology. Produces one multi-repo package for one operator signature, then applies, brings up and proves serving. Use whenever a model, role or NUMA placement changes.
---

# stack-change

**Read [`DERIVATION.md`](DERIVATION.md) first.** It says which files are source
and which are generated, and it is the whole reason this skill exists.

## Why this exists

On 2026-09-22 an operator-signed lineup patch touched ONE file. Bringing it live
needed eight more, each discovered only by running the next compile step and
reading its error — nine pipeline runs in sixteen minutes with the stack down,
and one file (`stack_templates/default.yaml`) that would have relaunched all
three retired models had it not been caught by hand before `start`.

The patch was not wrong. It was **incomplete, and nothing told anyone that.**
This skill's job is to make incompleteness impossible to ship: the package is
the complete multi-repo change set or it is not a package.

## The one rule

> **Nothing touches a real tree before the operator signs.** Every phase before
> the gate runs against a scratch copy of BOTH repos. This is what lets
> preflight report every violation at once instead of one per run.

## Phases

### 0 — intent
One YAML file. Nothing else is input.
```yaml
retire:   [gemma4_26b_a4b, qwen3_next_80b, qwen35_122b_q4km]
assign:
  frontdoor:            qwen36_35b_a3b_mtp_q8_local
  worker_general:       alias-of frontdoor
  ingest_long_context:  alias-of architect_general
topology:
  architect_general: {n_ctx: 196608, kv_quant: {k: q8_0, v: q8_0}}
```

### 1 — scratch
`scripts/scratch.sh` copies both repos' hand-edited sources to
`/mnt/raid0/llm/tmp/stack-change-<ts>/`. Everything up to phase 6 happens there.

### 2 — transform
Apply the intent to **every** surface in DERIVATION.md's source list, by tool.
Delegates to the sub-skills: `retire-model`, `change-role`, `change-topology`.
A surface you did not touch is a surface you must be able to say why.

### 3 — preflight
`scripts/preflight.sh` on the scratch: `stack_change_pipeline.py check
--numa-mode <declared>`, declaration parity, capacity (both legs), evidence
durability. Output is **ONE list**, every violation classified:

| class | meaning |
|---|---|
| `fixable-by-transform` | go back to phase 2; the transform missed a surface |
| `needs-measurement` | a model newly holding a role has no evidence for it |
| `needs-operator` | a genuine choice — context/quality tradeoff, a waiver |

### 4 — measure
For every `needs-measurement`: run the suite on the CURRENT stack if the model
is servable, else queue it for post-bring-up and say so in the package.
**Never offer `--allow-known-gaps` as the first option.** A waiver is a decision
the operator makes with the number in front of them, not a way past a gate.

### 5 — package
The multi-repo patch set · the preflight report · the capacity report (host and
GPU legs, per instance) · measured evidence refs · the exact bring-up command ·
the rollback (`git revert` set + any symlink restores).

### 6 — OPERATOR SIGNS
The only human gate.

### 7 — apply
Patch set onto the real trees → `update --numa-mode <declared>` →
`check --run-promotion-gate`.

### 8 — bring up
`orchestrator_stack.py start --numa-mode <declared>`, then **serving proof per
role**: argv[0] resolves into the kernel store, `/proc/<pid>/maps`, port healthy,
and a **real completion**. Status saying `healthy` is not serving proof.

> Give the completion a real token budget. With thinking enabled, reasoning is
> billed against the same budget as content, so a small `max_tokens` returns
> EMPTY content and looks exactly like a broken role. This wasted a diagnosis
> on 2026-09-22.

### 9 — wrap
Progress, handoff rows (prepare; the owning session applies), pathspec commit
per repo, push, `ff-only` main.

## Never

- **Never modify a real tree before phase 6.** A subagent was told exactly this
  on 2026-09-22 and then watched the main violate it, and correctly reverted
  work the operator had asked for.
- **Never hand-edit a derived file.** DERIVATION.md lists them.
- **Never run while another stack-change or kernel promotion holds the region or
  push lock.**
- **Never apply with a `needs-operator` item unresolved.**
- **Never pass `--allow-descriptor-model-removal` for a model the intent does not
  name.** Read the removal set it prints and check it against the intent.
- **Never declare done before phase 8's serving proof.** Report what a command
  returned, not what it was expected to do.

## Verifies after phase 7

Runtime attestation — the *live* fleet matches priors. No running server maps a
retired GGUF. Every `hot_resident` role answers a real completion.

## Composition

A kernel promotion ENDS in a stack change: `kernel-promotion` phase 8 is this
skill's phases 7–8. Call this skill; do not re-implement it.
