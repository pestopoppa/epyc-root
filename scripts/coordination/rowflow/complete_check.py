#!/usr/bin/env python3
"""complete_check.py - WARN-only preflight COMPLETE-REGEX-EXCLUDES-DECIDE (AK bug 2026-11-24).

A row's check_complete.py that accepts only some verdict prefixes (PASS/KEEP/DROP/FAIL/FUTILITY) ends a row whose
job.py decide() returns a descriptive verdict (CEILING_OPEN, ANSWERED, ...) as rc=75 partial-native-incomplete, and the
keeper re-ran it. Statically: read the verdict prefixes / regexes the check REQUIRES in its sys.exit(...) expression and
the string literals decide() returns, and flag each literal the check cannot match. Pure, static, never raises."""
from __future__ import annotations

import ast
import json
import os
import re

CODE = "COMPLETE-REGEX-EXCLUDES-DECIDE"


def _strs(node):
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def check_patterns(src: str):
    """(prefixes, regexes) positively required by the sys.exit(...) expression. Empty both = no verdict constraint."""
    tree = ast.parse(src)
    rx_vars = {}
    for n in ast.walk(tree):   # NAME = re.compile("...")
        if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                and n.value.func.attr == "compile" and n.value.args and isinstance(n.value.args[0], ast.Constant)):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    rx_vars[t.id] = n.value.args[0].value
    prefixes, regexes = [], []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "exit"):
            continue
        negated = {id(c) for u in ast.walk(n) if isinstance(u, ast.UnaryOp) and isinstance(u.op, ast.Not)
                   for c in ast.walk(u.operand)}
        for c in ast.walk(n):
            if id(c) in negated or not isinstance(c, ast.Call) or not isinstance(c.func, ast.Attribute):
                continue
            if c.func.attr == "startswith" and c.args:
                prefixes += _strs(c.args[0])
            elif c.func.attr in ("match", "fullmatch", "search"):
                if isinstance(c.func.value, ast.Name) and c.func.value.id in rx_vars:
                    regexes.append(rx_vars[c.func.value.id])
                elif isinstance(c.func.value, ast.Name) and c.func.value.id == "re" and c.args:
                    regexes += _strs(c.args[0])[:1]
    return prefixes, regexes


def decide_literals(src: str):
    """String literals decide() can return as its verdict: `return "X"`, `return ("X", ...)`, `{"verdict": "X"}`,
    `verdict = "X"` inside decide()."""
    out = []
    for f in ast.walk(ast.parse(src)):
        if not (isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name == "decide"):
            continue
        for n in ast.walk(f):
            if isinstance(n, ast.Return) and n.value is not None:
                v = n.value
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    out.append(v.value)
                elif isinstance(v, ast.Tuple) and v.elts and isinstance(v.elts[0], ast.Constant) and isinstance(v.elts[0].value, str):
                    out.append(v.elts[0].value)
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    if isinstance(k, ast.Constant) and k.value == "verdict" and isinstance(v, ast.Constant) and isinstance(v.value, str):
                        out.append(v.value)
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                if any(isinstance(t, ast.Name) and t.id == "verdict" for t in n.targets):
                    out.append(n.value.value)
    return list(dict.fromkeys(x for x in out if x))


def excluded(check_src: str, job_src: str):
    try:
        prefixes, regexes = check_patterns(check_src)
        lits = decide_literals(job_src)
    except (SyntaxError, ValueError):
        return []
    if not prefixes and not regexes:
        return []
    bad = []
    for lit in lits:
        ok = any(lit.startswith(p) or lit.upper().startswith(p) for p in prefixes)
        for r in regexes:
            try:
                ok = ok or bool(re.match(r, lit) or re.match(r, lit.upper()))
            except re.error:
                ok = True
        if not ok:
            bad.append(lit)
    return bad


def check_paths(spec: dict):
    txt = json.dumps(spec)
    return list(dict.fromkeys(re.findall(r"(/[^\s\"'\\]+/check_complete\.py)", txt)))


def warnings(spec: dict):
    out = []
    for cp in check_paths(spec or {}):
        jp = os.path.join(os.path.dirname(cp), "job.py")
        try:
            with open(cp) as f:
                cs = f.read()
            with open(jp) as f:
                js = f.read()
        except OSError:
            continue
        bad = excluded(cs, js)
        if bad:
            out.append(f"{CODE}: {cp} cannot accept decide() verdict(s) {bad} from {jp}; the row would end rc=75 "
                       f"partial-native-incomplete. FIX: complete = complete is True and 'polar' in RESULT (mk_ak_row v2 template)")
    return out
