#!/usr/bin/env python3
"""FM-4 session success/failure oracle.

Derives a machine-readable verdict per session from Claude Code JSONL
transcripts (read-only) and, best-effort, Codex rollouts. Neither corpus
carries a verdict; this reads outcome signals out of the tool traffic.

Row schema ``session_oracle.v1``::

    {session_id, path, harness, verdict, signals{...counts...},
     last_commit_sha, pushed, schema}

Signals (counts)
  tool_calls, tool_errors   every shell call / non-zero exit
  gate_pass, gate_fail      gate runs: pytest (summary line "N passed, M
                            failed"; any failed/error => fail), ``--check``
                            invocations and scripts/**/verify_*.py|sh (exit
                            status decides; "Exit code N" text or is_error)
  commits                   ``git commit`` whose output has "[branch abc1234]"
  push_ok, push_rejected    ``git push`` / serialized_push.py outcomes
                            (ref-update line / up-to-date = ok; "[rejected]",
                            "failed to push", non-fast-forward, or non-zero
                            exit = rejected)
  malformed_lines           unparseable JSONL lines (counted, never fatal)

Verdict rule (events evaluated in transcript order; G = last gate result,
C = a commit landed, P = last push outcome):
  1. unknown  - no gate, commit or push events at all.
  2. failure  - G is fail and no commit landed after that failing gate.
  3. partial  - G is fail but a commit landed after it (fixed forward
                unverified); or the work is only half evidenced: commit with
                no gate, gate pass with no commit, push only, or otherwise
                successful but the last push was rejected.
  4. success  - C and G is pass (a later pass supersedes earlier failures),
                and the last push (if any) was not rejected.
``pushed`` is true iff the last push outcome is ok.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = "session_oracle.v1"
_LEAD = r"(?:^|[;&|\"'(]\s*)"
_PYTEST_CMD = re.compile(r"-m\s+pytest\b|" + _LEAD + r"pytest\b", re.M)
_GATE_CMD = re.compile(
    _PYTEST_CMD.pattern + r"|(?:python3?\s+|bash\s+|\./)\S*verify_[\w-]+\.(?:py|sh)\b|"
    r"\.py\s+(?:\S+\s+)*--check\b", re.M)
_COUNT = re.compile(r"\b(\d+) (passed|failed|errors?)\b")
_COMMIT_SHA = re.compile(r"(?:^|[\s\"])\[([^\]\n\"]+?) ([0-9a-f]{7,40})\]", re.M)
_PUSH_CMD = re.compile(
    _LEAD + r"(?:git\s+(?:-C\s+\S+\s+)?push\b|(?:python3?\s+)?\S*serialized_push\.py)", re.M)
_PUSH_REJ = re.compile(r"\[rejected\]|remote rejected|failed to push|non-fast-forward", re.I)
_PUSH_OK = re.compile(
    r"^\s*[0-9a-f]{7,40}\.\.[0-9a-f]{7,40}\s+\S+\s+->|\[new (?:branch|tag)\]|Everything up-to-date",
    re.M)
_EXIT = re.compile(r"^Exit code (\d+)", re.M)


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") in ("text", "input_text"))
    return ""


def _exit_status(text, is_error=False):
    m = _EXIT.search(text or "")
    if m:
        return int(m.group(1))
    return 1 if is_error else 0


def _iter_json(path, stats):
    with Path(path).open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                stats["malformed_lines"] += 1
                continue
            if isinstance(r, dict):
                yield r
            else:
                stats["malformed_lines"] += 1


def _claude_events(records):
    """Yield (cmd, output, exit_status) for each Bash tool call, in order."""
    pending = {}
    order = []
    for r in records:
        msg = r.get("message")
        if not isinstance(msg, dict) or not isinstance(msg.get("content"), list):
            continue
        for b in msg["content"]:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and b.get("name") == "Bash":
                cmd = (b.get("input") or {}).get("command", "")
                pending[b.get("id")] = len(order)
                order.append([cmd, None, None])
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                text = _text_of(b.get("content"))
                ev = order[pending[b["tool_use_id"]]]
                ev[1] = text
                ev[2] = _exit_status(text, bool(b.get("is_error")))
    for cmd, out, st in order:
        if out is not None:
            yield cmd, out, st


def _codex_events(records):
    pending = {}
    order = []
    for r in records:
        p = r.get("payload")
        if not isinstance(p, dict):
            continue
        t = p.get("type")
        if t in ("custom_tool_call", "function_call"):
            cmd = p.get("input") if isinstance(p.get("input"), str) else p.get("arguments", "")
            pending[p.get("call_id")] = len(order)
            order.append([str(cmd).replace("\\n", "\n"), None, None])
        elif t in ("custom_tool_call_output", "function_call_output") and p.get("call_id") in pending:
            text = _text_of(p.get("output")) if not isinstance(p.get("output"), str) else p["output"]
            text = text.replace("\\n", "\n")
            codes = [int(x) for x in re.findall(r'exit_code\\?"?\s*[:=]\s*(-?\d+)', text)]
            ev = order[pending[p["call_id"]]]
            ev[1] = text
            ev[2] = max(codes, key=abs) if codes else 0
    for cmd, out, st in order:
        if out is not None:
            yield cmd, out, st


def _gate_result(cmd, out, status):
    """'pass' | 'fail' | None (not a gate)."""
    if not _GATE_CMD.search(cmd):
        return None
    if _PYTEST_CMD.search(cmd):
        counts = {}
        for n, kind in _COUNT.findall(out):
            k = "failed" if kind.startswith(("failed", "error")) else "passed"
            counts[k] = counts.get(k, 0) + int(n)
        if counts.get("failed"):
            return "fail"
        if counts.get("passed"):
            return "pass"
    return "fail" if status else "pass"


def judge(events):
    """events -> (verdict, signals-without-malformed, last_sha, pushed)."""
    sig = {"tool_calls": 0, "tool_errors": 0, "gate_pass": 0, "gate_fail": 0,
           "commits": 0, "push_ok": 0, "push_rejected": 0}
    last_gate = None
    commit_after_gate = False
    sha = None
    last_push = None
    for cmd, out, st in events:
        sig["tool_calls"] += 1
        if st:
            sig["tool_errors"] += 1
        g = _gate_result(cmd, out, st)
        if g:
            sig["gate_" + g] += 1
            last_gate = g
            commit_after_gate = False
        if "git commit" in cmd and "--dry-run" not in cmd:
            m = _COMMIT_SHA.findall(out)
            if m:
                sig["commits"] += 1
                sha = m[-1][1]
                commit_after_gate = True
        if _PUSH_CMD.search(cmd):
            if _PUSH_REJ.search(out) or (st and not _PUSH_OK.search(out)):
                sig["push_rejected"] += 1
                last_push = "rejected"
            elif _PUSH_OK.search(out) or not st:
                sig["push_ok"] += 1
                last_push = "ok"
    has_commit = sig["commits"] > 0
    if not (last_gate or has_commit or last_push):
        verdict = "unknown"
    elif last_gate == "fail":
        verdict = "partial" if commit_after_gate else "failure"
    elif has_commit and last_gate == "pass" and last_push != "rejected":
        verdict = "success"
    else:
        verdict = "partial"
    return verdict, sig, sha, last_push == "ok"


def _detect(path):
    try:
        with Path(path).open("r", encoding="utf-8", errors="replace") as fh:
            first = fh.readline()
        r = json.loads(first)
        if r.get("type") == "session_meta" or "ordinal" in r:
            return "codex", (r.get("payload") or {}).get("id")
    except (OSError, json.JSONDecodeError, AttributeError):
        pass
    return "claude", None


def assess(path):
    stats = {"malformed_lines": 0}
    harness, sid = _detect(path)
    records = list(_iter_json(path, stats))
    if harness == "claude":
        for r in records:
            if r.get("sessionId"):
                sid = r["sessionId"]
                break
        events = _claude_events(records)
    else:
        events = _codex_events(records)
    verdict, sig, sha, pushed = judge(events)
    sig["malformed_lines"] = stats["malformed_lines"]
    return {"session_id": sid or Path(path).stem, "path": str(path), "harness": harness,
            "verdict": verdict, "signals": sig, "last_commit_sha": sha,
            "pushed": pushed, "schema": SCHEMA}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--files", nargs="+")
    ap.add_argument("--root", default=str(Path.home() / ".claude/projects/-workspace"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.files:
        paths = [Path(p) for p in a.files]
    else:
        paths = sorted(Path(a.root).rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if a.limit:
        paths = paths[:a.limit]
    out = open(a.out, "w", encoding="utf-8") if a.out else sys.stdout
    try:
        for p in paths:
            try:
                row = assess(p)
            except OSError as e:
                print(f"skip {p}: {e}", file=sys.stderr)
                continue
            out.write(json.dumps(row, sort_keys=True) + "\n")
    finally:
        if a.out:
            out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
