#!/usr/bin/env python3
"""Write one markdown brief per work package from the audit data.

Usage: python3 mkpkg.py wave1.json <outdir>   (or wave2.json). Briefs are the input the implementer
prompt contract (impl_workflow_w2.js) expects at <scratch>/pkg/<ID>.md.
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SOURCES = [DATA / f"findings-{n}.json" for n in ("orchestrator-core", "autopilot", "autokernel")]

findings, summaries = {}, {}
for src in SOURCES:
    for u in json.load(open(src)):
        summaries[u["unit"]] = u.get("summary", "")
        for f in u.get("findings", []):
            findings[f["id"]] = f

pkgs = json.load(open(sys.argv[1]))
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for pid, spec in pkgs.items():
    L = [f"# Work package {pid}: {spec['title']}", "", spec.get("notes", ""), ""]
    missing = [i for i in spec["ids"] if i not in findings]
    if missing:
        raise SystemExit(f"{pid}: unknown ids {missing}")
    for i in spec["ids"]:
        f = findings[i]
        s = f.get("safety") or {}
        L += [f"## {i} — {f['title']}",
              f"- severity {f.get('severity')} | {f.get('dimension')}/{f.get('kind')} | effort {f.get('effort')} | behavior_change {f.get('behavior_change')} | audit verdict: {f.get('verdict')} | est. loc_delta {f.get('loc_delta')}",
              f"- files (as of 2026-10-07; line numbers have DRIFTED): {', '.join(f.get('files', []))}",
              "", f"**Evidence:** {f.get('evidence', '')}", "", f"**Proposal:** {f.get('proposal', '')}"]
        if f.get("corrected_proposal"):
            L += ["", f"**Verifier's corrected proposal (takes precedence):** {f['corrected_proposal']}"]
        if f.get("verify_reason"):
            L += ["", f"**Verifier notes:** {f['verify_reason']}"]
        if s:
            L += ["", f"**Production-safety review:** {s.get('safe_to_implement')}. Risk: {s.get('production_risk', '')} Conditions: {s.get('conditions', '')}",
                  "", f"**Safety reviewer's implementation plan:** {s.get('implementation_plan', '')}"]
        L += ["", f"**Suggested verification:** {f.get('verification', '')}", ""]
    (out / f"{pid}.md").write_text("\n".join(L) + "\n")
    print(pid, len(spec["ids"]), "findings")
