#!/usr/bin/env python3
"""F4 (AK audit B4, D9 2026-11-20): write-once migration of handoff-sessions.json operator_gate entries into holds.yaml.

Each gated session becomes one hold {id: <slug>, sessions: [<slug>], handoffs: [<handoff basename>], scope: loop-launch,
since, reason}. Prints the YAML (dry run) unless --write; --write refuses when the target already holds any of those ids
(write-once: the operator owns the hold list after the migration). The registry's operator_gate stays the dispatcher's
launch gate; publish_row reads holds.yaml first and the registry only as a derived view of the same holds.
"""
import argparse
import json
import os
import sys

DEFAULT_FLAGS = "/mnt/raid0/llm/" + "tmp/compute-flags"


def gates_to_holds(reg):
    out = []
    for slug, e in sorted((reg.get("sessions") or {}).items()):
        if isinstance(e, dict) and e.get("operator_gate"):
            g = e["operator_gate"] if isinstance(e["operator_gate"], dict) else {}
            h = {"id": slug, "sessions": [slug], "scope": str(g.get("scope") or "loop-launch"),
                 "since": g.get("since"), "reason": g.get("reason")}
            if e.get("handoff"):
                h["handoffs"] = [os.path.basename(str(e["handoff"]))]
            out.append(h)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--holds", required=True, help="target holds.yaml (handoffs/active/holds.yaml in a lane worktree)")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    import yaml
    reg = json.load(open(os.path.join(a.flags, "handoff-sessions.json")))
    new = gates_to_holds(reg)
    doc = {"holds": []}
    if os.path.exists(a.holds):
        doc = yaml.safe_load(open(a.holds)) or {"holds": []}
        have = {str(h.get("id")) for h in doc.get("holds") or [] if isinstance(h, dict)}
        dup = sorted(have & {h["id"] for h in new})
        if dup:
            print(f"REFUSED: {a.holds} already holds {dup}; the migration is write-once", file=sys.stderr)
            return 3
    doc.setdefault("holds", []).extend(new)
    text = yaml.safe_dump(doc, sort_keys=False)
    if not a.write:
        print(text)
        return 0
    tmp = a.holds + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, a.holds)
    print(f"wrote {len(new)} holds to {a.holds}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
