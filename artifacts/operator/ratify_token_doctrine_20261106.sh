#!/bin/bash
# human-only: operator ratifies the token-efficiency doctrine (token-audit recs 1-5 agreed 2026-11-06, plus the
# 2026-11-06 fan-out refinement: width is a CEILING, one canonical policy, every other file points at it).
#   Edits (all human-only paths): agents/shared/OPERATING_CONSTRAINTS.md (2 token lines + canonical fan-out policy),
#   CLAUDE.md "Agents & Automation" and agents/AGENT_INSTRUCTIONS.md (fan-out bullet -> ceiling + pointer).
# Idempotent (each edit is skipped when already present); --dry-run prints the unified diff and writes nothing.
# Refuses if an anchor moved or a target file has uncommitted changes. Commits with a pathspec; push is printed, not run.
set -euo pipefail

DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1
ROOT="${ROOT:-/workspace}"
export ROOT DRY

python3 - <<'PY'
import difflib, os, subprocess, sys

ROOT, DRY = os.environ["ROOT"], os.environ["DRY"] == "1"
OC, CM, AI = "agents/shared/OPERATING_CONSTRAINTS.md", "CLAUDE.md", "agents/AGENT_INSTRUCTIONS.md"

ANCHOR = "## Token-Efficiency Operating Rules (operator, 2026-10-05)"
L1 = "- Every spawn carries model + effort + token budget, or it is a defect."
L2 = "- Each wrap-up reports budget fraction per outcome."

OLD_WIDTH = ("- **3–5 subagents run CONCURRENTLY.** Independent work issued one agent at a time is serial working\n"
             "  with extra steps; put the independent calls in one block.\n")
NEW_WIDTH = """- **Fan-out width is a CEILING of 3-5 subagents, never a floor.**
  Spawn up to 3-5 concurrent subagents only when the work is genuinely parallel, and put the independent calls
  in one block. Do not fan out for a handful of tool calls or a lookup whose target you already know: do it inline.
  This is the ONE canonical statement of the policy; every other file points here instead of restating it.
- **Every spawn sets model, effort and a token budget explicitly** (ratified token line in *Token-Efficiency
  Operating Rules*). Pick the cheapest model that can do the job and the lowest adequate effort; Opus/Fable only
  where the reasoning needs it (`agents/README.md` -> Model Routing).
- **Briefs carry only the context the task needs, never a context dump.** Do not use `fork` for cheap work.
- **Zero-token watchers, never LLM polling** (*Token-Efficiency Operating Rules*).
- **Main threads rotate or compact early** (about 60k tokens for dispatched sessions; `token_guards` G4).
- **Each wrap-up reports budget fraction per outcome** (ratified token line in *Token-Efficiency Operating Rules*).
"""
CM_OLD = "execution goes to **3–5 subagents running concurrently**."
CM_NEW = ("execution goes to subagents, **up to 3–5 concurrently as a ceiling, never a floor**, on the cheapest capable\n"
          "  model and lowest adequate effort, set explicitly.")
AI_OLD = "execution goes to 3–5 concurrent subagents. Working serially is the defect."
AI_NEW = ("execution goes to subagents (up to 3–5 concurrent: a ceiling, never a floor; no fan-out for a handful of tool\n"
          "  calls). Serial execution of parallel work is the defect.")

def read(rel):
    return open(os.path.join(ROOT, rel)).read()

def dirty(rel):
    return subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", rel], capture_output=True, text=True).stdout.strip()

new, old = {}, {rel: read(rel) for rel in (OC, CM, AI)}
t = old[OC]

if L1 not in t.split("\n") or L2 not in t.split("\n"):
    if t.split("\n").count(ANCHOR) != 1:
        sys.exit("Refusing: token-efficiency anchor heading not found exactly once")
    lines = t.split("\n")
    i = lines.index(ANCHOR)
    j = i + 1
    while j < len(lines) and not lines[j].startswith("### "):
        j += 1
    add = [x for x in (L1, L2) if x not in lines]
    lines[j:j] = add + [""]
    t = "\n".join(lines)
if NEW_WIDTH not in t:
    if t.count(OLD_WIDTH) != 1:
        sys.exit("Refusing: Parallel Subagent Fan-Out width bullet not found exactly once")
    t = t.replace(OLD_WIDTH, NEW_WIDTH)
new[OC] = t

for rel, o, n in ((CM, CM_OLD, CM_NEW), (AI, AI_OLD, AI_NEW)):
    s = old[rel]
    if n not in s:
        if s.count(o) != 1:
            sys.exit(f"Refusing: fan-out sentence not found exactly once in {rel}")
        s = s.replace(o, n)
    new[rel] = s

changed = [r for r in (OC, CM, AI) if new[r] != old[r]]
if not changed:
    print("Already applied: nothing to change.")
    sys.exit(0)
for r in changed:
    sys.stdout.writelines(difflib.unified_diff(old[r].splitlines(True), new[r].splitlines(True), f"a/{r}", f"b/{r}"))
if DRY:
    print(f"\n--dry-run: {len(changed)} file(s) would change; nothing written.")
    sys.exit(0)
for r in changed:
    if dirty(r):
        sys.exit(f"Refusing: {r} has uncommitted changes")
for r in changed:
    open(os.path.join(ROOT, r), "w").write(new[r])
c = new[OC].split("\n")
assert c.count(L1) == 1 and c.count(L2) == 1 and NEW_WIDTH in new[OC], "Verify failed"
subprocess.check_call(["git", "-C", ROOT, "commit", "-m",
                       "doctrine: token-efficiency lines + fan-out ceiling, one canonical policy (operator 2026-11-06)", "--", *changed])
print("Committed. Push: python3 %s/scripts/coordination/serialized_push.py --agent operator --repo %s --push --fetch" % (ROOT, ROOT))
PY
