#!/usr/bin/env python3
"""done_when.py — parse a box's `· done when:` and check a tick's evidence against it (handoff standard Stage C, C2;
AK audit B13; DESIGN.md §2.5 verifier).

parse(text) -> {"kind": cmd|file|verdict|artifact_class|free, ...}
    cmd             `pytest …` / `python3 …` / `bash …` / `make …` / `cmd: …`  -> {"cmd"}
    file            `file: <path>[#field]` or a backticked path with `#field`    -> {"path", "field"}
    verdict         `verdict: PASS|FAIL|<regex>` / `row PASS` / `tick verdict …`  -> {"pattern"}
    artifact_class  names an artifact class (loop-built kernel / registered recipe / build receipt / row PASS)
                    -> {"artifact_class"}
    free            anything else (never machine-checked; the reviewer turn judges it)

check(done_when_text, evidence, root) -> ("ok" | "fail" | "unchecked", reason)
    evidence = {"verdict": str, "paths": [repo-relative], "commands": [{"cmd", "rc"}], "artifact_class": str}
    cmd: ok when evidence.commands has the same command with rc 0, fail on rc != 0, unchecked when it was not run
         (wrapup never runs arbitrary shell at tick time; the verifier/turn runs it and records rc).
    file: ok when <root>/<path> exists (and, with #field, the JSON/YAML file has that dotted key truthy).
    verdict: ok when the tick verdict matches the pattern (case-insensitive regex / literal).
    artifact_class: the evidence must name an artifact OF THAT CLASS. `kernels/production/*` is never "loop-built"
         (AKX-ALL-14, reopened 55b5733c1); a champion / ak-* / experimental build receipt or keep record is.

Readers: churn/wrapup.py (before apply_ticks), worker_checkpoint.py (/log completed), churn/file_result.py (row
ticks), taskflow verifier (DESIGN §2.5). One rule, one implementation.
"""
from __future__ import annotations

import json
import os
import re
import sys

_CMD = re.compile(r"^\s*(?:cmd:\s*)?`?((?:pytest|python3?|bash|make|scripts/\S+|\./\S+)\b[^`]*)`?\s*(?:pass(?:es)?|exits? 0|green)?\s*$",
                  re.I)
_CMD_INLINE = re.compile(r"`((?:pytest|python3?|bash|make)\s[^`]+)`")
_FILE = re.compile(r"^\s*file:\s*`?([^`#\s]+)(?:#([\w.\-]+))?`?", re.I)
_PATH_FIELD = re.compile(r"`([\w./\-]+\.(?:json|ya?ml))#([\w.\-]+)`")
_VERDICT = re.compile(r"^\s*(?:tick\s+)?verdict:?\s*(.+?)\s*$", re.I)
_ROW_PASS = re.compile(r"\brow\b.*\bPASS\b|\bPASS\b.*\brow\b")
LOOP_BUILT = re.compile(r"loop-built|gpu_build_receipt|build[_ ]receipt|keep record|recipe registered", re.I)
PRODUCTION = re.compile(r"(?:^|/)kernels/production(?:/|$)")
LOOP_EVIDENCE = re.compile(r"champion|(?:^|[/_-])ak[-_]|autokernel|experimental|build[_-]receipt|keep[_-]record", re.I)


def parse(text: str | None) -> dict:
    t = " ".join(str(text or "").split())
    if not t:
        return {"kind": "free", "text": ""}
    m = _FILE.match(t)
    if m:
        return {"kind": "file", "path": m.group(1), "field": m.group(2), "text": t}
    m = _VERDICT.match(t)
    if m and not LOOP_BUILT.search(t):
        return {"kind": "verdict", "pattern": m.group(1), "text": t}
    if LOOP_BUILT.search(t):
        return {"kind": "artifact_class", "artifact_class": "loop-built kernel", "text": t}
    m = _CMD.match(t) or _CMD_INLINE.search(t)
    if m:
        return {"kind": "cmd", "cmd": " ".join(m.group(1).split()), "text": t}
    m = _PATH_FIELD.search(t)
    if m:
        return {"kind": "file", "path": m.group(1), "field": m.group(2), "text": t}
    if _ROW_PASS.search(t):
        return {"kind": "verdict", "pattern": "PASS", "text": t}
    return {"kind": "free", "text": t}


def _field(path: str, dotted: str):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    try:
        doc = json.loads(raw)
    except ValueError:
        import yaml
        doc = yaml.safe_load(raw)
    for k in dotted.split("."):
        if not isinstance(doc, dict) or k not in doc:
            return None
        doc = doc[k]
    return doc


def check(done_when: str | None, evidence: dict | None, root: str = ".") -> tuple[str, str]:
    p = parse(done_when)
    ev = evidence or {}
    kind = p["kind"]
    if kind == "free":
        return "unchecked", "free-text done-when (reviewer judges it)"
    if kind == "cmd":
        want = p["cmd"]
        runs = [c for c in ev.get("commands") or [] if isinstance(c, dict) and " ".join(str(c.get("cmd", "")).split()) == want]
        if not runs:
            return "unchecked", f"command not in evidence: {want}"
        rc = runs[-1].get("rc")
        return ("ok", f"{want} rc=0") if rc == 0 else ("fail", f"{want} rc={rc}")
    if kind == "file":
        fp = os.path.join(root, p["path"])
        if not os.path.exists(fp):
            return "fail", f"file {p['path']} does not exist"
        if p.get("field"):
            try:
                v = _field(fp, p["field"])
            except Exception as exc:  # noqa: BLE001
                return "fail", f"{p['path']} unreadable for #{p['field']}: {type(exc).__name__}"
            if not v:
                return "fail", f"{p['path']}#{p['field']} missing or false"
        return "ok", f"file {p['path']}" + (f"#{p['field']}" if p.get("field") else "")
    if kind == "verdict":
        v = str(ev.get("verdict") or "")
        if not v:
            return "fail", f"done-when needs a verdict matching {p['pattern']!r}; the tick has none"
        try:
            hit = re.search(p["pattern"], v, re.I)
        except re.error:
            hit = p["pattern"].lower() in v.lower()
        return ("ok", f"verdict {v!r}") if hit else ("fail", f"verdict {v!r} does not match {p['pattern']!r}")
    # artifact_class
    paths = [str(x) for x in ev.get("paths") or []] + ([str(ev["artifact"])] if ev.get("artifact") else [])
    if any(PRODUCTION.search(x) for x in paths) and not any(LOOP_EVIDENCE.search(x) for x in paths
                                                            if not PRODUCTION.search(x)):
        return "fail", ("done-when names a loop-built artifact; the evidence names kernels/production/*, which is never "
                        "loop-built (AKX-ALL-14)")
    if str(ev.get("artifact_class") or "").lower().startswith("loop-built") or any(
            LOOP_EVIDENCE.search(x) for x in paths if not PRODUCTION.search(x)):
        return "ok", "loop-built artifact named"
    return "fail", "done-when names a loop-built artifact; the evidence names none (champion / ak-* build receipt)"


def done_when_of(box_text: str) -> str | None:
    """The `· done when:` value of a box's own block (task_lint.parse_fields)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import task_lint as tl
    finally:
        sys.path.pop(0)
    return tl.parse_fields(box_text).get("done when")


def check_box(lines: list[str], i: int, evidence: dict | None, root: str = ".") -> tuple[str, str, str | None]:
    """(result, reason, done_when) for the box at 0-based line i of a handoff."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import task_lint_core as L1
    finally:
        sys.path.pop(0)
    own, _ = L1.own_block(lines, i)
    dw = done_when_of(own)
    if not dw:
        return "unchecked", "box has no done-when", None
    r, why = check(dw, evidence, root)
    return r, why, dw


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("done_when")
    ap.add_argument("--evidence", default="{}")
    a = ap.parse_args()
    print(json.dumps({"parse": parse(a.done_when), "check": check(a.done_when, json.loads(a.evidence))}, indent=1))
