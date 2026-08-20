#!/bin/bash
set -euo pipefail
#
# Operator-applied edits from the 2026-08-19/20 research-intake batch.
#
# WHY THIS SCRIPT EXISTS: four approved Stage-4 items land on human-only trust-boundary
# paths (CLAUDE.md, agents/AGENT_INSTRUCTIONS.md, agents/shared/*.md). The agent session was
# correctly BLOCKED by scripts/hooks/check_trust_boundary_edit.sh. Per that hook's own guidance
# -- "raise a token-request with a pre-validated command" -- this is that command, batched into
# one run rather than trickled.
#
# Usage:
#   bash research/sources/intake-20260819/ratify_intake_20260820_trust_boundary_edits.sh --check
#   bash research/sources/intake-20260819/ratify_intake_20260820_trust_boundary_edits.sh --apply
#
# Idempotent: --apply is safe to re-run; already-applied edits are reported and skipped.
# Nothing is committed. Review `git diff` before committing, with explicit pathspecs.

MODE="${1:---check}"
cd "$(git rev-parse --show-toplevel)"

PY=repos/epyc-orchestrator/.venv/bin/python
[ -x "$PY" ] || PY=python3

"$PY" - "$MODE" <<'PYEOF'
import sys, pathlib
mode = sys.argv[1]
apply_ = mode == "--apply"
if mode not in ("--check", "--apply"):
    print("usage: --check | --apply"); raise SystemExit(2)

EDITS = []

# ---------------------------------------------------------------- 1. CLAUDE.md (defect D3)
EDITS.append((
    "CLAUDE.md",
    "D3 - GitNexus counts stale (claimed 42864/57165/462; live 45391/62296/523)",
    "Indexed as **epyc-root** (42864 nodes, 57165 edges, 462 clusters, 300 execution flows).",
    "Indexed as **epyc-root** (~45k nodes, ~62k edges, ~520 clusters, 300 execution flows; "
    "exact counts drift with every commit -- run `gitnexus status` for the live figure rather "
    "than trusting this line).",
))

# ------------------------------------------- 2. AGENT_INSTRUCTIONS.md (W5.2, operator decision)
EDITS.append((
    "agents/AGENT_INSTRUCTIONS.md",
    "W5.2 - dual prose standard with an explicit boundary rule (operator decision 2026-08-20)",
    """Write all text for the operator in ASD-STE100 Simplified Technical English. This applies to
chat replies, status reports, decision packages, handoff prose, and commit messages.
""",
    """**Two standards apply, and the boundary between them is a rule, not a preference.**
(Operator decision, 2026-08-20. Previously STE-100 was mandated for *all* operator-facing prose.)

| Standard | Applies to |
|---|---|
| **ASD-STE100** Simplified Technical English | Incident procedures, runbooks, safety and caution notes, operational steps followed under pressure -- anywhere a misreading is costly and a controlled vocabulary earns its constraint. |
| **Google developer-documentation style** | Reports, findings, deep-dive write-ups, decision packages, plans, handoff prose, status summaries, chat replies, commit messages -- the explanatory register. |

**When a text spans both, or you cannot tell: use Google style.** It is the broader class and the
one the operator reads most. Do not split a single document between registers -- pick by the
document's dominant purpose. A runbook that opens with two paragraphs of rationale is still a runbook.

**Why both rather than one.** STE-100's controlled vocabulary is worth its cost exactly where
ambiguity is dangerous and the reader is executing, not deciding. It is a poor fit for analysis,
whose job is to convey uncertainty, weigh evidence and state what is not known -- registers STE-100
has no vocabulary for. Google style covers that, is maintained, and is freely readable.

The STE-100 rules below apply to the first column of that table.
""",
))

# ------------------------------------------------- 3. OPERATING_CONSTRAINTS.md (W7 + W2)
EDITS.append((
    "agents/shared/OPERATING_CONSTRAINTS.md",
    "W7 - nimbleness doctrine; W2 - reload-drain invariants. Appended as new sections.",
    None,   # None == append
    """

## Unmerged is not a verdict -- judge upstream work on content

**Ratified 2026-08-20** (operator: *"large open-source repos have all sorts of commitment inertia.
We can afford to be much more nimble"*).

**Unmerged, unreviewed, or non-public status is a fact about AVAILABILITY. It is never on its own a
verdict about VALUE.** Judge an upstream artifact on its content; record merge status as provenance
alongside it, not as a filter before it.

The evidence is a measured outcome, not a preference. In the 2026-08-19/20 intake batch, three of the
four highest-value findings came from artifacts a merge-status filter would have discarded:

| Artifact | Status | What it gave us |
|---|---|---|
| SGLang RFC #27574 | open, unmerged | A *hint* vocabulary (Pin/Retain/Prefetch/Demote/Share) that fits our `id_slot` channel better than the merged design does |
| cordiverse/cordis PR #39 | open since 2026-08-06 | The maintainer's own statement of the correct disposal invariants |
| cordiverse/cordis PR #41 | open, unmerged | The design DeepSeek's vendored fork ports as ledger item 15 |
| deepseek-harness/cordis | **not public at all** (404) | Reached via the vendored copy inside the harness; yielded the real 18-item diff |

What DOES belong in the record: the merge state, the review state, the CI state, and whether the
branch is chasing a moving target. Those are provenance facts that bound how much weight a finding
carries -- they are not grounds for declining to read it. Full batch evidence:
`research/intake-stage2b-closeout-2026-08-20.md`.

## Reload must drain -- the five disposer invariants

**Recorded 2026-08-20** from the Cordis dive (intake-1208 / intake-1209), which measured four
reentrant disposal defects in a framework whose headline claim is reversible effects.

Our own reload path is worse and it was measured: `orchestrator_stack.py reload orchestrator` is
kill-by-port + `sleep 1` + restart, with **zero** disposer infrastructure anywhere in
`epyc-orchestrator/src/` (`disposer`, `AsyncExitStack`, `weakref.finalize`, `register_cleanup` all
return 0 files) and 22 `register*` entry points against **zero** unregister functions. This
contradicts axiom 4's quiesce-and-drain as applied to the API. **Cordis unwinds one fiber's
disposers; we replace the OS process.**

Any component-teardown or reload mechanism we build must satisfy all five:

1. **Register the inverse BEFORE the setup body runs**, and roll it back if setup throws. Registering
   after means an unload begun from inside setup misses it.
2. **Reject new registrations once the owner is UNLOADING**, re-checked under the same lock the drain
   holds. Otherwise a cleanup handler can register an effect that escapes the unload snapshot and is
   never cleaned up.
3. **Teardown JOINS an in-flight cleanup -- it never declares completion over one.** This is axiom 4
   restated as a runtime invariant: without it the supervisor is told a component unloaded while its
   teardown is still releasing, and the replacement starts on top of a resource the predecessor holds.
4. **Pop the callable before invoking it**, so single-shot is structural rather than flag-guarded.
5. **Contain teardown-notification failures per observer**, so one throwing listener cannot starve its
   peers or strand a half-built registration.

**What remains impossible in any language: verifying that a registered inverse actually inverts.**
Cordis type-checks the disposer and nothing more, and shipped a disposer that deleted the wrong map
entry for months. Do not claim a registry gives reversibility. It gives *invocation*.
""",
))

root = pathlib.Path(".")
applied = skipped = failed = 0
for path, why, old, new in EDITS:
    p = root / path
    if not p.exists():
        print(f"  MISSING  {path}"); failed += 1; continue
    s = p.read_text()
    if old is None:                                  # append mode
        marker = new.strip().split("\n")[0]
        if marker in s:
            print(f"  already  {path}  ({why})"); skipped += 1; continue
        if apply_:
            p.write_text(s.rstrip("\n") + "\n" + new)
        print(f"  {'APPLIED ' if apply_ else 'WOULD  '} {path}  ({why})"); applied += 1
        continue
    n = s.count(old)
    if n == 0:
        if new.strip().split("\n")[0][:40] in s:
            print(f"  already  {path}  ({why})"); skipped += 1
        else:
            print(f"  NO MATCH {path}  ({why})  -- text moved; re-derive before applying"); failed += 1
        continue
    if n > 1:
        print(f"  AMBIGUOUS {path}: {n} matches -- refusing"); failed += 1; continue
    if apply_:
        p.write_text(s.replace(old, new))
    print(f"  {'APPLIED ' if apply_ else 'WOULD  '} {path}  ({why})"); applied += 1

print(f"\n{'applied' if apply_ else 'would apply'}: {applied} | already done: {skipped} | problems: {failed}")
if failed:
    print("NOTE: a NO MATCH means the target text changed under us. Re-read the file and re-derive;")
    print("      do not force it.")
raise SystemExit(1 if failed else 0)
PYEOF
