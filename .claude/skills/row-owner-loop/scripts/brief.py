#!/usr/bin/env python3
"""brief.py — render a subagent brief with the versioned HARD RULES block (row-owner-loop, step 6).

  brief.py --goal "…" --box handoffs/active/x.md:123 --model sonnet --effort low \
           --build claim|row|none [--build-detail "q0 0-23, 40 min"] --report "field; field" \
           [--paths /abs/a /abs/b] [--worktree NAME] [--owner autokernel] [--trailer-file F]

The build clause is mandatory (`--build none` must be explicit). The report contract always asks for
proof of every claim and for the agent's own background tasks to be stopped before hand-back.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "..", "references", "hard-rules.md")
REPO = "/workspace"

BUILD = {
    "claim": ("BUILD: compile only under a region-lock claim you acquire first "
              "(`rowflow.py claim`/region lock on {d}); never bare `taskset`, never on a quarter granted to a "
              "timing row; release the claim when done and report it."),
    "row": ("BUILD: the build runs as a booked build row ({d}); do not compile locally at all."),
    "none": "BUILD: none — no compiles of any kind in this task.",
}

REPORT_FIXED = [
    "commits: sha + branch, and `git cherry origin/main <branch>` output proving they landed",
    "rows: id + `ls /mnt/raid0/llm/tmp/compute-flags/ready/<id>.json` (or the SMOKE-QUEUED marker with age)",
    "smoke state: quoted from the LAST block of dryrun/<id>/launcher.out, never from memory",
    "background tasks: confirm every one you started is stopped",
]


def hard_rules(path: str = RULES) -> str:
    t = open(path).read()
    m = re.search(r"<!-- HARD-RULES-BEGIN -->\n(.*?)<!-- HARD-RULES-END -->", t, re.S)
    if not m or not m[1].startswith("HARD-RULES v"):
        raise SystemExit("hard-rules.md has no versioned HARD-RULES block")
    return m[1].strip()


def box_text(spec: str, repo: str = REPO) -> str:
    f, _, line = spec.rpartition(":")
    p = f if os.path.isabs(f) else os.path.join(repo, f)
    try:
        lines = subprocess.run(["git", "-C", repo, "show", f"origin/main:{os.path.relpath(p, repo)}"],
                               capture_output=True, text=True, check=True).stdout.splitlines()
    except (subprocess.CalledProcessError, ValueError):
        lines = open(p).read().splitlines()
    i = int(line) - 1
    j = i + 1
    while j < len(lines) and lines[j].startswith(("  ", "\t")) and not re.match(r"\s*[-*] \[", lines[j]):
        j += 1
    return "\n".join(lines[i:j])


def render(a, box: str | None = None) -> str:
    if a.build not in BUILD:
        raise SystemExit("--build must be claim|row|none")
    if a.build != "none" and not a.build_detail:
        raise SystemExit("--build claim|row needs --build-detail (region/row id and duration)")
    box = box if box is not None else (box_text(a.box) if a.box else "")
    wt = a.worktree or "<name>"
    out = [f"Goal: {a.goal}", ""]
    if a.box:
        out += [f"Box ({a.box} — the TEXT is the identity, the line is a hint):", "```", box, "```", ""]
    out += [f"Model/effort: {a.model} / {a.effort}. Owner session: {a.owner}.", ""]
    if a.paths:
        out += ["Literal paths:"] + [f"- {p}" for p in a.paths] + [""]
    out += ["Git: `git -C /workspace worktree add /workspace/.worktrees/" + wt + " origin/main -b " + wt + "`; "
            "pathspec commit; message file in /mnt/raid0/llm/tmp/; push via serialized_push.py; "
            "plain `git worktree remove` + `git branch -D`.", ""]
    out += [BUILD[a.build].format(d=a.build_detail or ""), ""]
    out += [hard_rules(), ""]
    rep = REPORT_FIXED + [r.strip() for r in (a.report or "").split(";") if r.strip()]
    out += ["Report contract (prove every claim; unverified claims are treated as false):"] + [f"- {r}" for r in rep]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--goal", required=True)
    ap.add_argument("--box")
    ap.add_argument("--model", required=True, choices=["haiku", "sonnet", "opus", "fable"])
    ap.add_argument("--effort", required=True)
    ap.add_argument("--build", required=True, choices=list(BUILD))
    ap.add_argument("--build-detail")
    ap.add_argument("--report", default="")
    ap.add_argument("--paths", nargs="*")
    ap.add_argument("--worktree")
    ap.add_argument("--owner", default="autokernel")
    a = ap.parse_args(argv)
    sys.stdout.write(render(a))
    return 0


if __name__ == "__main__":
    sys.exit(main())
