#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""merge_gate.py — decide whether a change may merge autonomously (rider R6).

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md §Rider R6
Gate list:      coordination/session-bus/human_only_paths.yaml (hash-pinned, R7)

THE RULE IS CONTENT, NOT CATEGORY. A merge is autonomous unless the diff touches
a human-only path, in which case it becomes a boundary token. Merges are
revertible, which is what justifies the autonomous default; the human-only list
is not, which is what justifies gating it. Production kernels are not a special
case — they are one entry on that list, differing only in what satisfies the gate
(operator approval PLUS the four-step promotion workflow).

WHAT THIS DOES NOT DO. It never merges, pushes, or commits. It classifies a diff
and, when gated, emits a ready-to-relay token-request block. Deciding and acting
are deliberately separate so that this can run in a pre-merge check, in the
coordinator-agent, or by hand, without any of them inheriting write authority.

Exit codes:
    0   autonomous — no human-only path touched
    2   gated — a token is required (details on stdout)
    3   the gate list itself is unusable (missing, or drifted from its pin);
        fail-closed, because an unverifiable gate list cannot authorise anything
    64  usage

Usage:
    merge_gate.py check                          # staged changes in epyc-root
    merge_gate.py check --repo epyc-orchestrator --range origin/main..HEAD
    merge_gate.py check --json
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_PATHS = {
    "epyc-root": Path("/workspace"),
    "epyc-orchestrator": Path("/mnt/raid0/llm/epyc-orchestrator"),
    "epyc-inference-research": Path("/mnt/raid0/llm/epyc-inference-research"),
    "epyc-llama": Path("/mnt/raid0/llm/llama.cpp"),
}
BUS_ROOT = Path("/workspace/coordination/session-bus")
GATE_LIST = BUS_ROOT / "human_only_paths.yaml"
GATE_PIN = BUS_ROOT / "human_only_paths.sha256"

EX_GATED = 2
EX_GATE_UNUSABLE = 3
EX_USAGE = 64


def load_gate_list() -> dict:
    """Load and verify the gate list. Raises RuntimeError when unusable.

    Fail-closed on purpose: a gate list that cannot be verified cannot authorise
    anything, so we refuse rather than defaulting to "autonomous". This is the
    opposite bias from the PreToolUse guard, and deliberately so — that one runs
    on every edit and blocking on uncertainty would stall the repo, whereas this
    one runs at a merge decision, where refusing costs one operator glance.
    """
    if not GATE_LIST.exists():
        raise RuntimeError(f"gate list missing at {GATE_LIST} — nothing can be authorised")
    if not GATE_PIN.exists():
        raise RuntimeError(f"gate pin missing at {GATE_PIN} — drift would be undetectable")
    actual = hashlib.sha256(GATE_LIST.read_bytes()).hexdigest()
    expected = GATE_PIN.read_text(encoding="utf-8").split()[0].strip()
    if actual != expected:
        raise RuntimeError(
            f"gate list DRIFTED: {actual[:16]}… vs pinned {expected[:16]}… — "
            f"the trust boundary changed outside the operator path")
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(f"PyYAML unavailable: {exc}") from exc
    data = yaml.safe_load(GATE_LIST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("gate list malformed (not a mapping)")
    return data


def changed_paths(repo: Path, ref_range: str | None) -> list[str]:
    args = ["git", "-C", str(repo), "diff", "--name-only"]
    args += [ref_range] if ref_range else ["--cached"]
    out = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"git diff failed: {out.stderr.strip()}")
    return [p for p in out.stdout.split("\n") if p.strip()]


def current_branch(repo: Path) -> str:
    out = subprocess.run(["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
                         capture_output=True, text=True, timeout=15)
    return out.stdout.strip()


def classify(repo_key: str, paths: list[str], branch: str, gate: dict) -> dict:
    """Which gate entries this change trips, and why."""
    hits: list[dict] = []

    for entry in gate.get("paths") or []:
        if not isinstance(entry, dict) or entry.get("repo") != repo_key:
            continue
        glob = entry.get("glob", "")
        for p in paths:
            if fnmatch.fnmatch(p, glob) or p == glob:
                hits.append({"kind": "path", "path": p, "glob": glob,
                             "why": entry.get("why", ""),
                             "extra_requirement": entry.get("extra_requirement")})

    for entry in gate.get("branches") or []:
        if not isinstance(entry, dict) or entry.get("repo") != repo_key:
            continue
        if branch and fnmatch.fnmatch(branch, entry.get("glob", "")):
            hits.append({"kind": "branch", "branch": branch, "glob": entry.get("glob"),
                         "why": entry.get("why", ""),
                         "extra_requirement": entry.get("extra_requirement")})

    return {
        "repo": repo_key, "branch": branch, "changed": len(paths),
        "verdict": "gated" if hits else "autonomous",
        "hits": hits,
        "extra_requirements": sorted({h["extra_requirement"] for h in hits
                                      if h.get("extra_requirement")}),
        "unenforceable_note": (
            "The gate list's `conceptual:` entries (eval-tower semantics, safety gates, host "
            "reboots, privileged system changes) are NOT glob-checkable and are not evaluated "
            "here. A verdict of `autonomous` means no LISTED PATH was touched — it is not a "
            "statement that no trust boundary was crossed."),
    }


def token_block(result: dict, repo_key: str) -> str:
    """A ready-to-relay token-request block for the bus."""
    gate_id = f"OP-MERGE-{repo_key.upper()}-{'-'.join(sorted({h.get('glob','') for h in result['hits']}))[:40]}"
    gate_id = "".join(c if c.isalnum() or c in "-_" else "-" for c in gate_id).strip("-")
    lines = [f"### {gate_id}", "",
             f"- [ ] **{gate_id}** — merge in `{repo_key}` touches the human-only list",
             f"  - branch: `{result['branch']}`  ·  changed files: {result['changed']}"]
    for h in result["hits"]:
        target = h.get("path") or h.get("branch")
        lines.append(f"  - trips `{h.get('glob')}` via `{target}` — {h.get('why')}")
    for extra in result["extra_requirements"]:
        lines.append(f"  - **additional requirement:** {extra}")
    lines += ["  - the reviewing agent must attach the pre-validated apply command before this is",
              "    presented; a command that fails when the operator runs it is an agent defect", ""]
    return "\n".join(lines)


def cmd_check(args: argparse.Namespace) -> int:
    repo_key = args.repo
    if repo_key not in REPO_PATHS:
        print(f"unknown repo {repo_key!r}; expected one of {sorted(REPO_PATHS)}", file=sys.stderr)
        return EX_USAGE
    repo = REPO_PATHS[repo_key]

    try:
        gate = load_gate_list()
    except RuntimeError as exc:
        print(f"REFUSING: {exc}", file=sys.stderr)
        print("A gate list that cannot be verified cannot authorise a merge.", file=sys.stderr)
        return EX_GATE_UNUSABLE

    try:
        paths = changed_paths(repo, args.range)
        branch = current_branch(repo)
    except RuntimeError as exc:
        print(f"REFUSING: {exc}", file=sys.stderr)
        return EX_GATE_UNUSABLE

    result = classify(repo_key, paths, branch, gate)

    if args.json:
        if result["verdict"] == "gated":
            result["token_block"] = token_block(result, repo_key)
        print(json.dumps(result, indent=2))
        return EX_GATED if result["verdict"] == "gated" else 0

    if result["verdict"] == "autonomous":
        print(f"AUTONOMOUS — {result['changed']} changed file(s) in {repo_key} "
              f"(branch {branch}), none on the human-only list.")
        print(f"\nNote: {result['unenforceable_note']}")
        return 0

    print(f"GATED — merge in {repo_key} (branch {branch}) touches the human-only list:\n")
    for h in result["hits"]:
        target = h.get("path") or h.get("branch")
        print(f"  · {h['kind']}: {target}  (glob `{h.get('glob')}`)")
        print(f"    {h.get('why')}")
        if h.get("extra_requirement"):
            print(f"    ADDITIONAL REQUIREMENT: {h['extra_requirement']}")
    print("\nToken-request block, ready to relay:\n")
    print(token_block(result, repo_key))
    return EX_GATED


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="merge_gate.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="classify a change as autonomous or gated")
    c.add_argument("--repo", default="epyc-root", choices=sorted(REPO_PATHS))
    c.add_argument("--range", help="git ref range (default: staged changes)")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_check)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
