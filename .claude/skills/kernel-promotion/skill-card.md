# Skill card: kernel-promotion

Layout follows the AMD skill-card plus `evals/evals.json` convention adopted from intake-2745#record (amd/skills).

| Field | Value |
|---|---|
| Name | `kernel-promotion` |
| Entry point | [`SKILL.md`](SKILL.md) |
| Owner | operator-gated; executed by the session the operator asks |
| Scope | Promote a champion kernel to the next production version (v-next) |
| Evals | [`evals/evals.json`](evals/evals.json) |
| Gates | [`promotion_gates.yaml`](promotion_gates.yaml) |

## What it does
Derives promotion scope, proves the rollback anchor, builds a relocatable candidate into the kernel
store, gates it against the incumbent on speed and quality, emits ONE ratification package for the
operator to sign, then cuts the freeze and verifies it serves.

## When to use
- The operator explicitly asks to promote a champion kernel or to run the promotion runbook.

## When not to use
- Unprompted: promotion is operator-only; never start or recommend it on your own initiative.
- Experimental kernel work or benchmarks on `llama.cpp-experimental` branches.
- Patching the frozen production tree in place (forbidden; version past it).

## Inputs and outputs
- Inputs: champion ref, incumbent production version, kernel manifests (`docs/reference/kernel-manifests/`).
- Outputs: candidate build in `kernels/`, gate results, one ratification package, post-freeze serving proof.

## Bundled resources
`scripts/` (`scope.sh`, `anchor.sh`, `preflight.sh`, `loadcheck.sh`, `quality_parity.py`, `resident_plan.py`, `package.sh`, `verify_serving.sh`), `promotion_gates.yaml`.

## Safety and limits
- Stops exactly once for the operator signature; no freeze is cut without it.
- Candidate must be the full build validated as a whole, never reconciled by cherry-picks.
- Binary identity is proven by content (commit/manifest/digest), never by path or mtime.
