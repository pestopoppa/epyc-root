#!/usr/bin/env python3
"""Governance rule registry: validate, render, and check surface parity (REG-ENF-1).

The registry (docs/reference/governance/rule_registry.json) is the one source of truth
for WHICH governance rules exist, WHERE each is stated, and HOW (if at all) it is
mechanically enforced:

  enforcement_class  hard   at least one enforcement point BLOCKS (exit 2 / commit refused)
                     soft   enforced only by warn/inject points, or by a validator outside
                            the tool boundary
                     prose  stated, not enforced; no enforcement points

Surfaces and how each relates to the registry:
  prose surface      docs/reference/governance/RULE_REGISTRY.md is GENERATED (--render);
                     --check fails when it is stale.
  hook surface       .claude/settings.json is a trust boundary, so it is not rewritten;
                     --check proves PARITY instead: every claude-hook point is wired under
                     its event/matcher, and every hook wired in settings.json is owned by
                     a registry row (no unregistered enforcement).
  deny-list surface  opencode.json permission.bash is already generated from the
                     containment scanner (generate_opencode_permissions.py); the registry
                     points at it and --check proves the file carries a deny block.
  git hooks          every git-hook point's script must exist and be referenced by
                     install_git_hooks.sh or pre-commit.extras.
  sources            every row's anchor text must occur verbatim in its source file, so a
                     rule cannot silently lose its prose statement.

Usage:
  rule_registry.py --check   [--root DIR]     # validate everything; exit 1 on any defect
  rule_registry.py --render  [--root DIR]     # rewrite the generated prose surface
  rule_registry.py --list-hard                # one line per hard rule: id<TAB>points
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REGISTRY = "docs/reference/governance/rule_registry.json"
SCHEMA = "epyc.governance.rule_registry.v1"
CLASSES = {"hard", "soft", "prose"}
KINDS = {"claude-hook", "git-hook", "opencode-deny", "validator"}
MODES = {"block", "warn", "inject"}
ID_RE = re.compile(r"^[A-Z][A-Z0-9-]+$")
HOOK_PATH_RE = re.compile(r"scripts/hooks/[A-Za-z0-9_.-]+")


def load(root: Path) -> dict:
    return json.loads((root / REGISTRY).read_text(encoding="utf-8"))


def _settings_wiring(root: Path) -> dict[tuple[str, str], set[str]]:
    """(event, matcher) -> set of scripts/hooks/... paths wired in .claude/settings.json."""
    s = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    out: dict[tuple[str, str], set[str]] = {}
    for event, groups in s.get("hooks", {}).items():
        for g in groups:
            key = (event, g.get("matcher") or "")
            for h in g.get("hooks", []):
                for m in HOOK_PATH_RE.findall(h.get("command", "")):
                    out.setdefault(key, set()).add(m)
    return out


def validate(reg: dict, root: Path) -> list[str]:
    errs: list[str] = []
    if reg.get("schema") != SCHEMA:
        errs.append(f"schema: expected {SCHEMA}, got {reg.get('schema')!r}")
    rules = reg.get("rules")
    if not isinstance(rules, list) or not rules:
        return errs + ["rules: missing or empty"]
    wiring = _settings_wiring(root)
    git_install = "".join((root / "scripts/hooks" / f).read_text(encoding="utf-8", errors="replace")
                          for f in ("install_git_hooks.sh", "pre-commit.extras")
                          if (root / "scripts/hooks" / f).exists())
    seen: set[str] = set()
    owned: set[tuple[str, str, str]] = set()
    src_cache: dict[str, str] = {}
    for r in rules:
        rid = r.get("id", "<no id>")
        if not isinstance(rid, str) or not ID_RE.match(rid):
            errs.append(f"{rid}: id must match {ID_RE.pattern}")
        if rid in seen:
            errs.append(f"{rid}: duplicate id")
        seen.add(rid)
        for f in ("rule", "source", "enforcement_class", "enforcement_points"):
            if f not in r:
                errs.append(f"{rid}: missing field {f}")
        if not str(r.get("rule", "")).strip():
            errs.append(f"{rid}: empty rule text")
        cls = r.get("enforcement_class")
        if cls not in CLASSES:
            errs.append(f"{rid}: enforcement_class {cls!r} not in {sorted(CLASSES)}")
        pts = r.get("enforcement_points") or []
        src = r.get("source") or {}
        sf, anchor = src.get("file"), src.get("anchor")
        if not sf or not anchor:
            errs.append(f"{rid}: source needs file and anchor")
        else:
            if sf not in src_cache:
                p = root / sf
                src_cache[sf] = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
            if not src_cache[sf]:
                errs.append(f"{rid}: source file {sf} missing or empty")
            elif anchor not in src_cache[sf]:
                errs.append(f"{rid}: anchor not found in {sf}: {anchor!r}")
        if cls == "prose" and pts:
            errs.append(f"{rid}: prose rule must have no enforcement points")
        if cls in {"hard", "soft"} and not pts:
            errs.append(f"{rid}: {cls} rule needs at least one enforcement point")
        blocking_tool = any(p.get("mode") == "block" and p.get("kind") in {"claude-hook", "git-hook", "opencode-deny"}
                            for p in pts)
        if cls == "hard" and not blocking_tool:
            errs.append(f"{rid}: hard rule needs a blocking hook/deny point")
        if cls == "soft" and blocking_tool:
            errs.append(f"{rid}: has a blocking hook point; class should be hard")
        for p in pts:
            kind, path, mode = p.get("kind"), p.get("path", ""), p.get("mode")
            if kind not in KINDS:
                errs.append(f"{rid}: point kind {kind!r} not in {sorted(KINDS)}")
            if mode not in MODES:
                errs.append(f"{rid}: point mode {mode!r} not in {sorted(MODES)}")
            if not path or not (root / path).exists():
                errs.append(f"{rid}: point path missing on disk: {path!r}")
                continue
            if kind == "claude-hook":
                key = (p.get("event", ""), p.get("matcher", ""))
                if path not in wiring.get(key, set()):
                    errs.append(f"{rid}: {path} not wired in .claude/settings.json under {key}")
                owned.add((key[0], key[1], path))
            elif kind == "git-hook":
                if Path(path).name not in git_install and Path(path).name != "install_git_hooks.sh":
                    errs.append(f"{rid}: {path} not referenced by install_git_hooks.sh/pre-commit.extras")
            elif kind == "opencode-deny":
                try:
                    oc = json.loads((root / path).read_text(encoding="utf-8"))
                    bash = (oc.get("permission") or {}).get("bash") or {}
                    if not any(v == "deny" for v in (bash.values() if isinstance(bash, dict) else [])):
                        errs.append(f"{rid}: {path} carries no permission.bash deny entry")
                except (OSError, ValueError) as exc:
                    errs.append(f"{rid}: cannot parse {path}: {exc}")
    for (event, matcher), paths in sorted(wiring.items()):
        for path in sorted(paths):
            if (event, matcher, path) not in owned:
                errs.append(f"unregistered hook: {path} wired under ({event}, {matcher!r}) "
                            f"has no registry row")
    return errs


def render(reg: dict) -> str:
    rules = reg["rules"]
    counts = {c: sum(1 for r in rules if r["enforcement_class"] == c) for c in ("hard", "soft", "prose")}
    out = [
        "# Governance Rule Registry",
        "",
        "<!-- GENERATED by scripts/governance/rule_registry.py --render from",
        f"     {REGISTRY}. Do not hand-edit; edit the JSON and re-render. -->",
        "",
        f"{len(rules)} rules: {counts['hard']} hard, {counts['soft']} soft, {counts['prose']} prose.",
        "`hard` = a hook or deny list blocks the act; `soft` = warn/inject hook or an",
        "out-of-band validator; `prose` = stated only.",
        "",
        "| ID | Class | Rule | Source | Enforcement |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(rules, key=lambda r: ({"hard": 0, "soft": 1, "prose": 2}[r["enforcement_class"]], r["id"])):
        pts = "; ".join(
            f"{p['kind']}:`{Path(p['path']).name}`"
            + (f" {p['event']}/{p.get('matcher') or '*'}" if p.get("event") else "")
            + f" [{p['mode']}]"
            for p in r["enforcement_points"]) or "—"
        rule = r["rule"].replace("|", "\\|")
        pts = pts.replace("|", "\\|")
        out.append(f"| {r['id']} | {r['enforcement_class']} | {rule} | `{r['source']['file']}` | {pts} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--render", action="store_true")
    g.add_argument("--list-hard", action="store_true")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    a = ap.parse_args(argv)
    root = Path(a.root)
    reg = load(root)
    prose = root / reg.get("generated_surfaces", {}).get("prose", "docs/reference/governance/RULE_REGISTRY.md")
    if a.render:
        prose.write_text(render(reg), encoding="utf-8")
        print(f"wrote {prose}")
        return 0
    if a.list_hard:
        for r in reg["rules"]:
            if r["enforcement_class"] == "hard":
                print(r["id"] + "\t" + ",".join(p["path"] for p in r["enforcement_points"]))
        return 0
    errs = validate(reg, root)
    if not prose.exists() or prose.read_text(encoding="utf-8") != render(reg):
        errs.append(f"stale prose surface: {prose} (run --render)")
    for e in errs:
        print("ERROR " + e, file=sys.stderr)
    if errs:
        return 1
    print(f"OK {len(reg['rules'])} rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
