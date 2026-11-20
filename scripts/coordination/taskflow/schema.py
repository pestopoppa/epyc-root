#!/usr/bin/env python3
"""taskflow/schema.py — build an `epyc.task.v1` record from a `.box-index.json` record (DESIGN.md §2.2, Stage 1).

The task record is what a worker sees and what the verifier checks. It is deterministic (no LLM) and carries:

  goal         the box's own block, VERBATIM from the handoff (first line + continuation lines). The identity is
               `text_sha` (box_index.text_sha of the first line); `file:line` is a hint only.
  done_when    the `· done when:` field, else an inline "done when …" clause, else None (verifier -> reviewer only)
  test_cmds    runnable commands the box names for its done-condition (backticked `pytest|python3|bash|make …`)
  inputs       paths the box names that exist in `repo` (excerpted into the prompt), plus box_index `inputs`
  forbidden    globs the worker must never touch (FORBIDDEN + any `holds.yaml` `files` targets)
  repo         the git tree the paths resolve in (epyc-root | epyc-orchestrator | epyc-inference-research | …)
  tier/budget  model tier hint and hard caps (turns, tokens, wall seconds)

    python3 scripts/coordination/taskflow/schema.py <box-key> [...]     # print task records as JSON
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

SCHEMA = "epyc.task.v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
REPOS = {  # name -> working path; the first repo in which a named path exists wins (root on a tie / no path)
    "epyc-root": Path(os.environ.get("TASKFLOW_ROOT_REPO", "/workspace")),  # lanes come from the shared clone's origin/main
    "epyc-orchestrator": Path("/mnt/raid0/llm/epyc-orchestrator"),
    "epyc-inference-research": Path("/mnt/raid0/llm/epyc-inference-research"),
    "epyc-web": Path("/mnt/raid0/llm/epyc-web"),
}
# Never touched by a taskflow worker unless the box itself names the path as an input (DESIGN §2.5).
FORBIDDEN = (
    "handoffs/**", "agents/shared/**", "CLAUDE.md", "**/CLAUDE.md", ".claude/**", "coordination/session-bus/**",
    "scripts/coordination/rowflow/**", "scripts/coordination/keeper*", "scripts/coordination/taskflow/**",
    "scripts/hooks/**", "artifacts/**", "docs/reports/**", "kernels/**", "progress/**", "MEASUREMENT.md",
    "measurement/**", ".git/**",
)
DEFAULT_BUDGET = {"turns": 30, "tokens": 120000, "wall_s": 900,  # r1: 14 steps all went to exploration
                  "excerpt_chars": 9000}
TIER_BY_CLASS = {"non-inference": "terra", "inference": "terra"}

_PATH = re.compile(r"`([A-Za-z0-9_.][\w./-]*(?:\.[A-Za-z0-9]{1,6}|/))(?::\d+(?:-\d+)?)?`")
_BARE_PATH = re.compile(r"(?<![\w/.])((?:src|scripts|tests|docs|orchestration|research|dashboard|benchmarks)/[\w./-]+\.[A-Za-z0-9]{1,6})")
_CMD = re.compile(r"`((?:pytest|python3?|bash|make)\s[^`]+)`")
_INLINE_DW = re.compile(r"\bdone\s+when\b[:\s]+(.+?)(?:\.\s|;|\[no-belief|\[belief|$)", re.I | re.S)


def own_block(lines: list[str], i: int) -> str:
    """Box at 0-based line i plus its continuation lines (deeper-indented or blank-then-deeper), verbatim."""
    first = lines[i]
    ind = len(first) - len(first.lstrip())
    out = [first]
    for ln in lines[i + 1:]:
        if not ln.strip():
            break
        if len(ln) - len(ln.lstrip()) <= ind:
            break
        out.append(ln)
    return "\n".join(out)


def text_sha(first_line: str) -> str:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "handoffs"))
    try:
        import box_index
        return box_index.text_sha(first_line)
    except Exception:  # noqa: BLE001 - fixture roots without box_index
        return hashlib.sha256(" ".join(first_line.split()).encode()).hexdigest()[:16]
    finally:
        sys.path.pop(0)


def find_box(lines: list[str], rec: dict) -> int:
    """Resolve the box by TEXT (text_sha), using the line as a hint only. -1 when it no longer exists."""
    hint = int(rec.get("line") or 0) - 1
    want = rec.get("text_sha")
    order = ([hint] if 0 <= hint < len(lines) else []) + [j for j in range(len(lines)) if j != hint]
    for j in order:
        if re.match(r"\s*[-*] \[ \] ", lines[j]) and (not want or text_sha(lines[j]) == want):
            return j
    return -1


_SKILL = re.compile(r"`?([a-z0-9][a-z0-9-]+)`?\s+skill\b", re.I)


def named_paths(text: str) -> list[str]:
    seen: list[str] = []
    for m in _SKILL.finditer(text):           # "the kernel-promotion skill" -> .claude/skills/kernel-promotion/
        seen.append(f".claude/skills/{m.group(1).lower()}/")
    for m in list(_PATH.finditer(text)) + list(_BARE_PATH.finditer(text)):
        p = m.group(1).rstrip(".")
        if p not in seen and not p.startswith("/"):
            seen.append(p)
    return seen


def pick_repo(paths: list[str], text: str) -> str:
    hits = {name: sum((root / p).exists() for p in paths) for name, root in REPOS.items() if root.exists()}
    for name in ("epyc-orchestrator", "epyc-inference-research", "epyc-web"):
        if re.search(rf"\b{name.split('-', 1)[1].split('-')[0]}\b `", text) and hits.get(name):
            return name
    best = max(hits.items(), key=lambda kv: (kv[1], kv[0] == "epyc-root"), default=("epyc-root", 0))
    return best[0] if best[1] else "epyc-root"


def done_when_text(goal: str, rec: dict) -> str | None:
    if rec.get("done_when"):
        return str(rec["done_when"])
    m = _INLINE_DW.search(goal)
    return " ".join(m.group(1).split()) if m else None


def build(rec: dict, root: Path | None = None, held_files: list[str] | None = None,
          budget: dict | None = None) -> dict:
    """epyc.task.v1 from a box-index record. Raises LookupError when the box text no longer resolves."""
    root = root or REPO_ROOT
    lines = (root / rec["file"]).read_text(encoding="utf-8").split("\n")
    i = find_box(lines, rec)
    if i < 0:
        raise LookupError(f"box {rec.get('key') or rec.get('id')} no longer resolves by text in {rec['file']}")
    goal = own_block(lines, i)
    paths = named_paths(goal)
    repo = pick_repo(paths, goal)
    rroot = REPOS[repo]
    inputs = [p for p in paths if (rroot / p).exists()]
    for p in rec.get("inputs") or []:
        if p not in inputs and (rroot / p).exists():
            inputs.append(p)
    dw = done_when_text(goal, rec)
    cmds = _CMD.findall(dw or "") or _CMD.findall(goal)
    return {
        "schema": SCHEMA,
        "key": rec.get("key") or rec.get("id") or f"{rec['file']}#{rec.get('text_sha')}",
        "id": rec.get("id"),
        "text_sha": text_sha(lines[i]),
        "handoff": rec["file"],
        "line_hint": i + 1,
        "owner_slug": Path(rec["file"]).stem,
        "track": rec.get("track"),
        "class": rec.get("class") or "non-inference",
        "goal": goal,
        "done_when": dw,
        "test_cmds": [" ".join(c.split()) for c in cmds][:3],
        "inputs": inputs,
        "outputs": [p for p in paths if p not in inputs],   # named but not yet existing = may be created
        "forbidden": list(FORBIDDEN) + list(held_files or []),
        "repo": repo,
        "tier": rec.get("tier"),   # the box `tier:` hint only; dispatch.pick_tier fills the default by kind
        "budget": dict(DEFAULT_BUDGET, **(budget or {})),
    }


def main(argv=None) -> int:
    keys = list(argv if argv is not None else sys.argv[1:])
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "handoffs"))
    import box_index
    doc = box_index.load(REPO_ROOT)
    out = []
    for k in keys:
        rec = (doc.get("boxes") or {}).get(k)
        if rec is None:
            print(f"unknown box key {k}", file=sys.stderr)
            return 2
        out.append(build(dict(rec, key=k)))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
