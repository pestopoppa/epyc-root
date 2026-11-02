"""Typed loop specs (JEV-5 phase A): read, validate and diagram ``epyc.loop_spec.v1``.

The spec files live in ``docs/reference/loop-specs/`` (schema:
``loop-spec.schema.json``). They are TRACKED in this repo and derived from the
loop's code; ``tests/test_loop_spec.py`` proves every ``file:CONSTANT``
threshold still equals the code, so the diagram on ``/loop-spec`` cannot quietly
drift from what the keeper/dispatcher actually do.

Stdlib only (the hub's rule). The validator implements the subset of the JSON
Schema the spec uses — required keys, enums, cross-references — rather than
pulling in ``jsonschema``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC_DIR = REPO / "docs" / "reference" / "loop-specs"
SCHEMA_ID = "epyc.loop_spec.v1"
STATE_KINDS = ("work", "wait", "stop", "park", "pause", "yield", "fail", "done", "alert")
REASON_KINDS = ("stop", "park", "pause", "yield", "fail", "wait", "refuse", "alert")


def spec_paths() -> list[Path]:
    return sorted(SPEC_DIR.glob("*.loop.json"))


def validate(spec: dict) -> list[str]:
    """Every problem with ``spec`` as a sentence; ``[]`` means valid."""
    errs: list[str] = []
    if not isinstance(spec, dict):
        return ["spec is not a JSON object"]
    for key in ("schema", "loop_id", "title", "canonical_doc", "spec_revised",
                "machines", "thresholds", "stop_reasons"):
        if key not in spec:
            errs.append(f"missing top-level key {key!r}")
    if errs:
        return errs
    if spec["schema"] != SCHEMA_ID:
        errs.append(f"schema must be {SCHEMA_ID!r}")
    if not re.fullmatch(r"[a-z0-9-]+", str(spec["loop_id"])):
        errs.append("loop_id must match ^[a-z0-9-]+$")
    thr = {t.get("id") for t in spec["thresholds"] if isinstance(t, dict)}
    for t in spec["thresholds"]:
        for k in ("id", "value", "unit", "source"):
            if k not in t:
                errs.append(f"threshold {t.get('id')!r}: missing {k!r}")
    machines = {}
    for m in spec["machines"]:
        mid = m.get("id")
        for k in ("id", "title", "actor", "code", "initial", "states", "transitions"):
            if k not in m:
                errs.append(f"machine {mid!r}: missing {k!r}")
        states = {s.get("id") for s in m.get("states", [])}
        machines[mid] = states
        for s in m.get("states", []):
            if s.get("kind") is not None and s["kind"] not in STATE_KINDS:
                errs.append(f"machine {mid!r} state {s.get('id')!r}: kind {s['kind']!r} not in {STATE_KINDS}")
            if not s.get("meaning"):
                errs.append(f"machine {mid!r} state {s.get('id')!r}: meaning is empty")
        if m.get("initial") not in states:
            errs.append(f"machine {mid!r}: initial {m.get('initial')!r} is not a state")
        for tr in m.get("transitions", []):
            for end in ("from", "to"):
                if tr.get(end) not in states:
                    errs.append(f"machine {mid!r}: transition {end} {tr.get(end)!r} is not a state")
            for t in tr.get("thresholds", []):
                if t not in thr:
                    errs.append(f"machine {mid!r}: transition names unknown threshold {t!r}")
    reasons = set()
    for r in spec["stop_reasons"]:
        rid = r.get("id", "")
        reasons.add(rid)
        if not re.fullmatch(r"[A-Z][A-Z0-9-]*", rid):
            errs.append(f"stop reason {rid!r}: id must be UPPER-KEBAB")
        if r.get("kind") not in REASON_KINDS:
            errs.append(f"stop reason {rid!r}: kind {r.get('kind')!r} not in {REASON_KINDS}")
        if r.get("machine") not in machines:
            errs.append(f"stop reason {rid!r}: unknown machine {r.get('machine')!r}")
        if not r.get("condition"):
            errs.append(f"stop reason {rid!r}: condition is empty")
        for t in r.get("thresholds", []):
            if t not in thr:
                errs.append(f"stop reason {rid!r}: unknown threshold {t!r}")
    for m in spec["machines"]:
        for tr in m.get("transitions", []):
            if tr.get("reason") and tr["reason"] not in reasons:
                errs.append(f"machine {m.get('id')!r}: transition reason {tr['reason']!r} is not a stop_reason")
    return errs


def _mid(s: str) -> str:
    return "s_" + re.sub(r"[^A-Za-z0-9_]", "_", s)


def mermaid(machine: dict) -> str:
    """A Mermaid ``stateDiagram-v2`` for one machine (rendered client-side)."""
    lines = ["stateDiagram-v2", f"  [*] --> {_mid(machine['initial'])}"]
    for s in machine["states"]:
        lines.append(f'  state "{s["id"]}" as {_mid(s["id"])}')
        if s.get("terminal"):
            lines.append(f"  {_mid(s['id'])} --> [*]")
    for tr in machine["transitions"]:
        label = tr.get("log") or tr.get("reason") or tr["on"]
        label = re.sub(r"[:;\"<>{}]", " ", label)[:48].strip()
        lines.append(f"  {_mid(tr['from'])} --> {_mid(tr['to'])} : {label}")
    for s in machine["states"]:
        k = s.get("kind")
        if k in ("fail", "park"):
            lines.append(f"  class {_mid(s['id'])} bad")
        elif k in ("pause", "yield", "wait"):
            lines.append(f"  class {_mid(s['id'])} waiting")
        elif k == "done":
            lines.append(f"  class {_mid(s['id'])} good")
    lines += ["  classDef bad fill:#5a1e1e,stroke:#f87171,color:#fde2e2",
              "  classDef waiting fill:#3b2f12,stroke:#f0c088,color:#fbe7c6",
              "  classDef good fill:#123b24,stroke:#4ade80,color:#d8f5e3"]
    return "\n".join(lines)


def read_specs() -> tuple[list[dict], list[dict]]:
    """``(specs, problems)``; each spec gains ``_path``, ``_errors`` and per-machine ``mermaid``."""
    specs, problems = [], []
    for p in spec_paths():
        rel = str(p.relative_to(REPO))
        try:
            spec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append({"path": rel, "error": f"unreadable: {exc}"})
            continue
        errs = validate(spec)
        spec["_path"] = rel
        spec["_errors"] = errs
        if errs:
            problems.append({"path": rel, "error": "; ".join(errs[:5])})
        else:
            for m in spec["machines"]:
                m["mermaid"] = mermaid(m)
        specs.append(spec)
    return specs, problems
