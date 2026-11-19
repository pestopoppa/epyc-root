#!/usr/bin/env python3
"""P5-1 guard: no coordination-plane hook may emit PostToolUse classifierContext.

Greps every hook/coordination script for `classifierContext`. A relayed statement can
satisfy a consent bar for the permission classifier (never a hard boundary), so no hook
may write into that channel. Also pins the set of hookSpecificOutput emitters.
Run: python3 scripts/hooks/tests/test_no_classifier_context.py
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCAN = [ROOT / "scripts/hooks", ROOT / "scripts/coordination", ROOT / ".opencode/plugins",
        ROOT / ".claude/hooks", ROOT / ".claude/settings.json"]
SELF = pathlib.Path(__file__).resolve()
ALLOWED_HSO = {"scripts/hooks/session_start_lane_notice.py", "scripts/hooks/planner_readonly_gate.py"}
EXT = {".py", ".sh", ".ts", ".js", ".json", ".yaml", ".yml"}


def files():
    for p in SCAN:
        it = [p] if p.is_file() else (q for q in p.rglob("*") if q.is_file())
        for q in it:
            if q.resolve() != SELF and q.suffix in EXT and "/tests/" not in q.as_posix():
                yield q


def test_no_classifier_context():
    bad, hso = [], set()
    for f in files():
        try:
            t = f.read_text(errors="replace")
        except OSError:
            continue
        rel = f.relative_to(ROOT).as_posix()
        if re.search(r"classifierContext", t):
            bad.append(rel)
        if "hookSpecificOutput" in t:
            hso.add(rel)
    fail = []
    if bad:
        fail.append(f"classifierContext used (forbidden): {bad}")
    if hso - ALLOWED_HSO:
        fail.append(f"new hookSpecificOutput emitter needs P5-1 review: {sorted(hso - ALLOWED_HSO)}")
    if fail:
        raise AssertionError("FAIL\n" + "\n".join(fail))
    print(f"OK: 0 classifierContext uses; hookSpecificOutput emitters = {sorted(hso)}")


if __name__ == "__main__":
    try:
        test_no_classifier_context()
    except AssertionError as e:
        print(e); sys.exit(1)
