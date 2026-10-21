#!/usr/bin/env python3
"""secret_history_scan.py — SEC-SECRETS-1 one-off history scan (handoffs/active/model-exec-containment.md).

Walks EVERY commit reachable from any ref (`git log --all -p`) of the given repos and looks at each ADDED line for
Hugging Face and Weights & Biases credentials, using the same regexes as the pre-commit hook
(`scripts/hooks/pii_precommit.sh`, SEC-SECRETS-1 block; the hook is the single source: this script reads its
SECRET_PATTERNS array rather than keeping a copy). A secret that was committed and later deleted is still in
history, which is exactly what a working-tree scan cannot see (intake-2208#07: leaked tokens, not leaked weights).

NAME-ONLY OUTPUT. The report carries repo, commit, path, pattern label and a hit count. It never carries the
matched text, the line, a line number or any prefix/suffix of the value; exceptions are reported by class only.
`tests/test_secret_history_scan.py` proves the planted value appears nowhere in stdout, stderr or the JSON.

Hits under the hook's own allow-list (research/fixtures/pii_*, the hook itself: documented fake tokens) are listed
with `allowlisted: true` and do not affect the exit code. Exit codes: 0 no real finding, 3 at least one, 2 a repo
could not be scanned (a failed scan is never "clean").

    python3 scripts/audit/secret_history_scan.py --repo /workspace --repo /mnt/raid0/llm/epyc-orchestrator \\
        --repo /mnt/raid0/llm/epyc-inference-research --repo /mnt/raid0/llm/epyc-web --out scan.json

`--all-families` also applies every other secret pattern in the hook (AWS, GitHub, Slack, sk-, ...). Default is the
HF/W&B families only, which is what SEC-SECRETS-1 covers; the broad families are noisy over a long history.
Rotation of anything found is an operator action on the credential's own service; this tool never touches one.

CPU: one `git log -p` stream per repo, single threaded, regex only on lines that pass a substring prefilter in
the default mode. Run it niced and outside timing windows. Tests: tests/test_secret_history_scan.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "model-secret-history-scan/1"
HOOK = Path(__file__).resolve().parents[1] / "hooks" / "pii_precommit.sh"
# Same allow-list as the hook's ALLOW_PATTERNS (documented fake credentials live there).
ALLOWLIST = (re.compile(r"^research/fixtures/pii_"), re.compile(r"^scripts/hooks/pii_precommit\.sh$"),
             re.compile(r"^\.gitignore$"))
HFW_LABELS = ("Hugging Face access token", "Hugging Face legacy organisation token",
              "W&B API key (wandb_v1_ format)", "W&B API key (40-hex, key-name context)",
              "W&B API key (wandb login argument)")
PREFILTER = ("hf_", "api_org_", "wandb", "WANDB")
MAX_LINE = 2_000_000
_ARRAY = re.compile(r"^SECRET_PATTERNS=\((.*?)^\)", re.S | re.M)
_ENTRY = re.compile(r"^\s*\$'((?:[^'\\]|\\.)*)'\s*$", re.M)


def _ere_to_python(rx: str) -> str:
    """The hook's ERE -> Python re for the constructs those patterns use."""
    return (rx.replace("[[:space:]]", r"\s").replace("[[:alnum:]]", "[A-Za-z0-9]"))


def load_patterns(hook: Path = HOOK, all_families: bool = False) -> list[tuple[re.Pattern[str], str]]:
    """(compiled regex, label) from the hook's SECRET_PATTERNS, `$'...\\t...'` entries decoded like bash does."""
    text = hook.read_text()
    m = _ARRAY.search(text)
    if not m:
        raise ValueError(f"no SECRET_PATTERNS array in {hook}")
    out: list[tuple[re.Pattern[str], str]] = []
    for entry in _ENTRY.finditer(m.group(1)):
        raw = entry.group(1)
        decoded = re.sub(r"\\(.)", lambda c: {"t": "\t", "'": "'", "\\": "\\"}.get(c.group(1), "\\" + c.group(1)), raw)
        parts = decoded.split("\t")
        if len(parts) != 3:
            continue
        regex, _label, desc = parts
        if not all_families and desc not in HFW_LABELS:
            continue
        out.append((re.compile(_ere_to_python(regex)), desc))
    if not all_families:
        got = {d for _, d in out}
        missing = [d for d in HFW_LABELS if d not in got]
        if missing:
            raise ValueError(f"hook {hook} lacks the SEC-SECRETS-1 patterns: {missing}")
    return out


def is_allowlisted(path: str) -> bool:
    return any(p.search(path) for p in ALLOWLIST)


def iter_added(repo: str) -> Iterator[tuple[str, str, str]]:
    """Yield (commit, path, added_line_text) for every added line in every commit of every ref."""
    proc = subprocess.Popen(
        ["git", "-C", repo, "-c", "core.quotepath=off", "log", "--all", "-p", "-U0", "--no-color", "--no-textconv",
         "--no-ext-diff", "--diff-filter=AM", "--format=%x01%H"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace", bufsize=1 << 20)
    assert proc.stdout is not None
    commit, path = "", ""
    for line in proc.stdout:
        if line.startswith("\x01"):
            commit, path = line[1:].strip(), ""
        elif line.startswith("+++ "):
            path = line[6:].rstrip("\n") if line.startswith("+++ b/") else ""
        elif line.startswith("+") and path:
            yield commit, path, line[1:]
    if proc.wait() != 0:
        raise RuntimeError(f"git log failed in {repo} (rc {proc.returncode})")


def scan_repo(repo: str, patterns: list[tuple[re.Pattern[str], str]], prefilter: bool) -> dict[str, Any]:
    hits: Counter[tuple[str, str, str]] = Counter()
    lines = skipped = 0
    commits: set[str] = set()
    for commit, path, text in iter_added(repo):
        commits.add(commit)
        lines += 1
        if len(text) > MAX_LINE:
            skipped += 1
            continue
        if prefilter and not any(tok in text for tok in PREFILTER):
            continue
        for rx, label in patterns:
            if rx.search(text):
                hits[(commit, path, label)] += 1
    findings = [{"commit": c, "path": p, "pattern": lab, "hits": n, "allowlisted": is_allowlisted(p)}
                for (c, p, lab), n in sorted(hits.items())]
    return {"repo": repo, "commits_with_added_lines": len(commits), "added_lines": lines,
            "lines_skipped_oversize": skipped, "findings": findings}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="name-only secret scan of full git history (never prints a value)")
    ap.add_argument("--repo", action="append", required=True, help="repository path (repeatable)")
    ap.add_argument("--out", help="write the JSON report here (default: stdout summary only)")
    ap.add_argument("--all-families", action="store_true", help="every hook secret pattern, not just HF/W&B")
    ap.add_argument("--hook", type=Path, default=HOOK)
    a = ap.parse_args(argv)
    try:
        patterns = load_patterns(a.hook, a.all_families)
    except (OSError, ValueError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    report: dict[str, Any] = {"schema": SCHEMA, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                              "families": "all" if a.all_families else "hf+wandb",
                              "patterns": sorted({lab for _, lab in patterns}), "repos": [], "errors": []}
    for repo in a.repo:
        if not os.path.isdir(os.path.join(repo, ".git")) and not os.path.isfile(os.path.join(repo, ".git")):
            report["errors"].append({"repo": repo, "error": "not a git repository"})
            continue
        try:
            report["repos"].append(scan_repo(repo, patterns, prefilter=not a.all_families))
        except Exception as exc:  # noqa: BLE001 - class only: an exception string could quote a line
            report["errors"].append({"repo": repo, "error": type(exc).__name__})
    real = [f for r in report["repos"] for f in r["findings"] if not f["allowlisted"]]
    report["real_findings"] = len(real)
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=2) + "\n")
    for r in report["repos"]:
        n_real = sum(1 for f in r["findings"] if not f["allowlisted"])
        print(f"{r['repo']}: {r['commits_with_added_lines']} commits, {r['added_lines']} added lines, "
              f"{n_real} real finding(s), {len(r['findings']) - n_real} allowlisted")
    for f in real:
        print(f"FINDING {f['commit']} {f['path']} [{f['pattern']}] x{f['hits']}")
    for e in report["errors"]:
        print(f"ERROR {e['repo']}: {e['error']}", file=sys.stderr)
    if report["errors"]:
        return 2
    return 3 if real else 0


if __name__ == "__main__":
    sys.exit(main())
