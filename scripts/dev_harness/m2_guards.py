#!/usr/bin/env python3
"""DHM-2 — retrospective guard audit predicates and the hook-denial / tool-error census.

Every predicate answers "would today's rule fire on this call?" over a historical tool call.
Where a production hook already implements the rule, the predicate IS that hook's scanner
(scripts/hooks/*_scan.py): process_pattern_kill_scan, filesystem_containment_scan,
llama_cli_guard_scan, shell_scan — never a second parser. The others are new text-scoped
predicates built on shell_scan.segments() (quoted text, heredoc bodies and comments are data).

Outcome of a would-fire call, from its paired tool result:
  blocked_hook   the result is a hook denial
  blocked_user   the operator rejected the call
  errored        the call ran (or tried to) and failed for another reason
  slipped_through the call returned normally
  no_result      no paired result (session ended, interrupted, or result lost)

``hook_era``: whether a production hook for the class existed on that harness at the call's
timestamp (dates = git add-date of the hook file; fidelity=inferred: a hook can be added
before it is registered).
"""
from __future__ import annotations

import functools
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/hooks"))

import filesystem_containment_scan as fcs  # noqa: E402
import llama_cli_guard_scan as lcg  # noqa: E402
from process_pattern_kill_scan import pattern_kill_verdict  # noqa: E402
from shell_scan import segments, strip_comments, strip_heredocs, strip_quoted  # noqa: E402

from m2_common import Call, Unit  # noqa: E402

DEFAULT_CWD = "/workspace"
# The hook re-reads its allowlist YAML per call (right for a hook, ~1.5 ms); the audit reads it once.
fcs.load_allowlist = functools.lru_cache(maxsize=4)(fcs.load_allowlist)

# class -> (hook file, harnesses the hook covers, git add-date of the hook file). None = prose-only.
HOOK_COVERAGE: dict[str, tuple[str, tuple[str, ...], str] | None] = {
    "pattern_kill": ("scripts/hooks/check_process_pattern_kill.sh", ("claude_code",), "2026-08-12"),
    "pgrep_pattern": ("scripts/hooks/check_process_pattern_kill.sh", ("claude_code",), "2026-08-12"),
    "write_outside_allowlist": ("scripts/hooks/check_filesystem_containment.sh",
                                ("claude_code", "codex", "opencode"), "2026-08-23"),
    "write_tool_outside_allowlist": ("scripts/hooks/check_filesystem_path.sh", ("claude_code",), "2026-02-25"),
    "wholesale_git_add": ("scripts/hooks/check_commit_hygiene.py", ("claude_code",), "2026-07-27"),
    "git_stash": ("scripts/hooks/check_commit_hygiene.py", ("claude_code",), "2026-07-27"),
    "llama_cli_unbounded": ("scripts/hooks/check_llama_cli_guard.sh", ("claude_code",), "2026-09-01"),
    "pytest_xdist_auto": ("scripts/hooks/check_pytest_safety.sh", ("claude_code",), "2026-02-25"),
    "piped_gate_push": None,
    "glob_rm": None,
    "git_clean": None,
    "git_worktree_prune_or_force": None,
    "git_reset_hard": None,
    "no_verify": None,
    "hooks_path_null": None,
    "test_skip_added": None,
    "test_deleted": None,
    "test_deselect": None,
    "edit_running_script": None,
    "bare_gitnexus_analyze": None,
    "run_benchmark_invocation": None,
}
CLASSES = tuple(HOOK_COVERAGE)
INFERRED_CLASSES = {"edit_running_script", "test_deselect", "test_deleted"}

_GIT = r"(?:^|\s)git(?:\s+-C\s+\S+|\s+-c\s+\S+)*\s+"
_RE = {
    "wholesale_git_add": re.compile(_GIT + r"add\s+(?:[^\n]*\s)?(?:-A|--all|-u|--update|\.)(?=\s|$)"),
    "wholesale_commit_a": re.compile(_GIT + r"commit\s+(?:[^\n]*\s)?(?:-a\w*|--all)(?=\s|$)"),
    "git_stash": re.compile(_GIT + r"stash(?!\s+(?:list|show))(?=\s|$)"),
    "git_clean": re.compile(_GIT + r"clean\s+(?:[^\n]*\s)?-\w*[fdx]"),
    "git_clean_dry": re.compile(_GIT + r"clean\s+(?:[^\n]*\s)?(?:-\w*n|--dry-run)"),
    "worktree_prune": re.compile(_GIT + r"worktree\s+prune"),
    "worktree_rm_force": re.compile(_GIT + r"worktree\s+remove\s+(?:[^\n]*\s)?(?:--force|-f)(?=\s|$)"),
    "git_gc": re.compile(_GIT + r"gc(?=\s|$)"),
    "reset_hard": re.compile(_GIT + r"reset\s+(?:[^\n]*\s)?--hard"),
    "no_verify": re.compile(_GIT + r"(?:commit|push|merge|rebase)\s+(?:[^\n]*\s)?--no-verify"),
    "hooks_path": re.compile(r"core\.hooksPath(?:=|\s+)(?:/dev/null|''|\"\"|\S*empty)"),
    "gate": re.compile(r"pytest|--check|\btest\b|\bcheck|validate|verify|\blint|ruff|mypy|\bmake\b|ctest|index_state"),
    "push": re.compile(_GIT + r"push(?=\s|$)"),
    "rm": re.compile(r"(?:^|\s)rm\s+((?:-[A-Za-z]+\s+|--[a-z-]+\s+)*)(.*)$"),
    "pytest_n_auto": re.compile(r"(?:^|\s)(?:python3?\s+-m\s+)?pytest\s+(?:[^\n]*\s)?-n\s*(?:auto|logical)"),
    "deselect": re.compile(r"(?:^|\s)pytest\s+[^\n]*(?:--deselect|-k\s+[\"']?not\s)"),
    "gitnexus_bare": re.compile(r"(?:^|\s)(?:npx\s+)?gitnexus\s+analyze(?=\s|$)"),
    "run_benchmark": re.compile(r"(?:^|\s|/)run_benchmark(?:\.py)?(?=\s|$)"),
    "bg_amp": re.compile(r"(?<![&|>])&\s*$"),
    "nohup": re.compile(r"(?:^|\s)(?:nohup|setsid)\s"),
    "script_tok": re.compile(r"[\w./~-]+\.(?:sh|py)\b"),
    "sed_i": re.compile(r"(?:^|\s)sed\s+(?:-\w*i\w*|--in-place)"),
    "test_file": re.compile(r"(?:^|/)(?:test_[\w-]+\.py|[\w-]+_test\.py)$"),
    "skip_marker": re.compile(r"@pytest\.mark\.(?:skip|xfail)|pytest\.skip\(|@unittest\.skip|\.skip\(\s*['\"]"),
}


def _cleaned(cmd: str) -> str:
    return strip_comments(strip_quoted(strip_heredocs(cmd)))


def shell_classes(cmd: str, cwd: str | None) -> dict[str, str]:
    """{class: detail} for every rule this shell command would trip."""
    hits: dict[str, str] = {}
    cut = cmd.find("\n…[truncated ")
    truncated = cut >= 0
    if truncated:   # agentrun caps a message at --max-msg-chars: a heredoc may have lost its terminator
        cmd = cmd[:cut]
    pk = pattern_kill_verdict(cmd)
    if pk == "kill-pattern":
        hits["pattern_kill"] = "pkill on a name pattern"
    elif pk == "grep-pattern":
        hits["pgrep_pattern"] = "pgrep on a name pattern"
    try:
        v = fcs.scan_command(cmd, cwd=cwd or DEFAULT_CWD)
    except Exception as e:  # a scanner crash is reported, never silently clean
        v = {"code": f"scanner_error:{type(e).__name__}"}
    if v.get("verdict") != "allowed":
        hits["write_outside_allowlist"] = v.get("code") or "refused"
    if "llama-cli" in cmd:
        src = strip_heredocs(cmd) if truncated else cmd   # unterminated heredoc body = data
        verdicts = [lcg.scan_segment(s) for s in lcg.segments(lcg.strip_literals(src))]
        if "unbounded-invocation" in verdicts:
            hits["llama_cli_unbounded"] = "llama-cli without timeout"
    text = _cleaned(cmd)
    segs = [s.strip() for s in segments(cmd)]
    for seg in segs:
        if _RE["wholesale_git_add"].search(seg) or _RE["wholesale_commit_a"].search(seg):
            hits["wholesale_git_add"] = seg[:80]
        if _RE["git_stash"].search(seg):
            hits["git_stash"] = "git stash"
        if _RE["git_clean"].search(seg) and not _RE["git_clean_dry"].search(seg):
            hits["git_clean"] = "git clean -f"
        if _RE["worktree_prune"].search(seg) or _RE["worktree_rm_force"].search(seg) or _RE["git_gc"].search(seg):
            hits["git_worktree_prune_or_force"] = seg[:80]
        if _RE["reset_hard"].search(seg):
            hits["git_reset_hard"] = "git reset --hard"
        if _RE["no_verify"].search(seg):
            hits["no_verify"] = "--no-verify"
        m = _RE["rm"].search(seg)
        if m and re.search(r"-\w*[rRf]|--recursive|--force", m.group(1) or "") and re.search(r"[*?\[]", m.group(2)):
            hits["glob_rm"] = "rm -r/-f with an unquoted glob"
        if _RE["pytest_n_auto"].search(seg):
            hits["pytest_xdist_auto"] = "pytest -n auto"
        if _RE["deselect"].search(cmd) and "pytest" in seg:
            hits["test_deselect"] = "pytest --deselect / -k not"
        if _RE["gitnexus_bare"].search(seg):
            hits["bare_gitnexus_analyze"] = "bare gitnexus analyze"
        if _RE["run_benchmark"].search(seg):
            hits["run_benchmark_invocation"] = "run_benchmark"
        if re.search(r"(?:^|\s)(?:git\s+)?rm\s", seg):
            for tok in seg.split():
                if _RE["test_file"].search(tok):
                    hits["test_deleted"] = "rm of a test file"
    if _RE["hooks_path"].search(cmd):
        hits["hooks_path_null"] = "core.hooksPath to null"
    if "pipefail" not in cmd and "PIPESTATUS" not in cmd:
        # INC-20260929-piped-gate-push: `<gate> | tail && git push` — the pipeline's status is the
        # last stage's, so the gate cannot stop the push. Same statement (no ; or newline between).
        for stmt in re.split(r"[;\n]", text):
            pm = _RE["push"].search(stmt)
            if not pm:
                continue
            before = stmt[:pm.start()]
            pipes = [m.start() for m in re.finditer(r"(?<!\|)\|(?!\|)", before)]
            if not pipes or "&&" not in before[pipes[-1]:]:
                continue
            head = before[:pipes[0]].split("&&")[-1]
            if _RE["gate"].search(head):
                hits["piped_gate_push"] = "pipeline status gates git push"
    return hits


def write_classes(c: Call) -> dict[str, str]:
    hits: dict[str, str] = {}
    for p in c.write_paths:
        try:
            v = fcs.check_path(p, cwd=c.cwd or DEFAULT_CWD)
        except Exception as e:
            v = {"code": f"scanner_error:{type(e).__name__}"}
        if v.get("verdict") != "allowed":
            hits["write_tool_outside_allowlist"] = v.get("code") or "refused"
    a = c.args
    old = a.get("old_string") or a.get("oldString") or ""
    new = a.get("new_string") or a.get("newString") or a.get("content") or ""
    patch = a.get("input") if c.function.lower() in ("apply_patch", "patch") else ""
    if isinstance(patch, str) and patch:
        old = "\n".join(l[1:] for l in patch.splitlines() if l.startswith("-"))
        new = "\n".join(l[1:] for l in patch.splitlines() if l.startswith("+"))
    if isinstance(old, str) and isinstance(new, str):
        if len(_RE["skip_marker"].findall(new)) > len(_RE["skip_marker"].findall(old)):
            hits["test_skip_added"] = "skip/xfail marker added"
        if any(_RE["test_file"].search(p) for p in c.write_paths) and \
                old.count("def test_") > new.count("def test_") and c.function.lower() != "write":
            hits["test_deleted"] = "test function removed"
    return hits


def _hook_era(cls: str, harness: str, ts: str | None) -> str:
    cov = HOOK_COVERAGE.get(cls)
    if cov is None:
        return "prose_only"
    _, harnesses, since = cov
    if harness not in harnesses:
        return "harness_uncovered"
    if not ts:
        return "unknown"
    return "hook_present" if ts[:10] >= since else "pre_hook"


def unit_hits(u: Unit) -> list[dict]:
    """Every would-fire (class, call) in the unit, in order."""
    out: list[dict] = []
    launched: dict[str, str] = {}   # script basename -> launch ts (background launches in this unit)
    for c in u.calls:
        found: dict[str, str] = {}
        for cmd in c.commands:
            found.update(shell_classes(cmd, c.cwd))
            text = _cleaned(cmd)
            bg = c.background or bool(_RE["nohup"].search(text)) or \
                any(_RE["bg_amp"].search(s) for s in text.split("\n"))
            touched = {os.path.basename(t) for t in _RE["script_tok"].findall(text)}
            if _RE["sed_i"].search(text) or re.search(r">\s*[\w./~-]+\.(?:sh|py)\b", text):
                for t in touched & set(launched):
                    if not bg:
                        found["edit_running_script"] = "in-place edit of a backgrounded script"
            if bg:
                for t in touched:
                    launched.setdefault(t, c.ts or "")
        found.update(write_classes(c))
        for p in c.write_paths:
            if os.path.basename(p) in launched:
                found["edit_running_script"] = "edit of a script launched in background earlier"
        for cls, detail in found.items():
            out.append({"class": cls, "detail": detail, "call": c, "outcome": c.outcome,
                        "hook_era": _hook_era(cls, u.harness, c.ts),
                        "fidelity": "inferred" if cls in INFERRED_CLASSES else "observed"})
    return out


_HOOK_NAME_RE = re.compile(r"\b(check_[a-z0-9_]+|[a-z0-9_]+_(?:guard|scan|hook))\b|\[([a-z0-9_-]{4,40})\]")


def hook_name(text: str) -> str:
    for m in _HOOK_NAME_RE.finditer(text or ""):
        name = m.group(1) or m.group(2)
        if name and not name.startswith("request"):
            return name
    return "unattributed"


class GuardAudit:
    """Accumulates DHM-2 counts; per-hit rows go to the private hits file via ``rows``."""

    def __init__(self) -> None:
        self.counts: dict = defaultdict(Counter)    # (cls, harness, source) -> outcome counts
        self.era: dict = defaultdict(Counter)       # (cls, harness, hook_era) -> outcome counts
        self.exposure: dict = defaultdict(Counter)  # (harness, source) -> exposure counts
        self.denials: dict = defaultdict(Counter)   # (harness, source) -> denial class / hook name
        self.tool_errors: dict = defaultdict(Counter)  # (harness, tool) -> calls/errors
        self.codes: dict = defaultdict(Counter)     # containment class -> refusal code counts
        self.rows: list[dict] = []

    def observe(self, u: Unit, hits: list[dict]) -> None:
        e = self.exposure[(u.harness, u.source)]
        e["units"] += 1
        e["main_units" if u.is_main else "subagent_units"] += 1
        e["tool_calls"] += len(u.calls)
        e["shell_calls"] += sum(1 for c in u.calls if c.commands)
        e["write_calls"] += sum(1 for c in u.calls if c.write_paths)
        e["truncated_commands"] += sum(1 for c in u.calls for cmd in c.commands if "\n…[truncated " in cmd)
        for c in u.calls:
            te = self.tool_errors[(u.harness, c.function or "?")]
            te["calls"] += 1
            o = c.outcome
            if o in ("errored", "blocked_hook", "blocked_user"):
                te["errors"] += 1
            if o.startswith("blocked"):
                d = self.denials[(u.harness, u.source)]
                d[o] += 1
                if o == "blocked_hook":
                    err = (c.result or {}).get("error") or {}
                    d["hook:" + hook_name(err.get("message") or "")] += 1
        for h in hits:
            self.counts[(h["class"], u.harness, u.source)]["would_fire"] += 1
            self.counts[(h["class"], u.harness, u.source)][h["outcome"]] += 1
            self.era[(h["class"], u.harness, h["hook_era"])][h["outcome"]] += 1
            if h["class"] in ("write_outside_allowlist", "write_tool_outside_allowlist"):
                self.codes[h["class"]]["code:" + h["detail"]] += 1
            c = h["call"]
            self.rows.append({"class": h["class"], "detail": h["detail"], "harness": u.harness,
                              "source": u.source, "unit_key": u.unit_key, "ts": c.ts, "function": c.function,
                              "outcome": h["outcome"], "hook_era": h["hook_era"], "fidelity": h["fidelity"],
                              "command_excerpt": (c.commands[0] if c.commands else ",".join(c.write_paths))[:300]})

    def aggregate(self) -> dict:
        classes: dict = {}
        for (cls, h, s), cnt in sorted(self.counts.items()):
            classes.setdefault(cls, {}).setdefault(h, {})[s] = dict(cnt)
        era: dict = {}
        for (cls, h, e), cnt in sorted(self.era.items()):
            era.setdefault(cls, {}).setdefault(h, {})[e] = dict(cnt)
        expo: dict = {}
        for (h, s), cnt in sorted(self.exposure.items()):
            expo.setdefault(h, {})[s] = dict(cnt)
        den: dict = {}
        for (h, s), cnt in sorted(self.denials.items()):
            den.setdefault(h, {})[s] = dict(cnt)
        te: dict = {}
        for h in sorted({h for h, _ in self.tool_errors}):
            tools = sorted(((t, c) for (hh, t), c in self.tool_errors.items() if hh == h),
                           key=lambda x: -x[1]["calls"])[:25]
            te[h] = {"tool:" + t: {"calls": c["calls"], "errors": c["errors"],
                                   "error_rate": round(c["errors"] / c["calls"], 4) if c["calls"] else 0}
                     for t, c in tools}
        per1k: dict = {}
        tot_calls = Counter()
        for (h, s), cnt in self.exposure.items():
            tot_calls[h] += cnt["tool_calls"]
        for (cls, h, s), cnt in self.counts.items():
            per1k.setdefault(cls, Counter())[h] += cnt["would_fire"]
        rate = {cls: {h: round(1000 * n / tot_calls[h], 4) if tot_calls[h] else 0 for h, n in v.items()}
                for cls, v in per1k.items()}
        return {"classes": classes, "containment_codes": {k: dict(v) for k, v in self.codes.items()}, "by_hook_era": era, "exposure": expo, "denial_census": den,
                "tool_error_census": te, "would_fire_per_1k_tool_calls": rate}
