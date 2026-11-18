#!/usr/bin/env python3
"""Descriptive character baseline using DCP-14's historical pairing rule.

Question: what parent/child prompt sizes are actually observable by role?
No sampling: one pass over the pinned trace. Stop on malformed input; exclude
truncated/unparsable pairs and later-parent fallbacks from size summaries.
These are captured characters, not token budgets or evidence of causal links.
The trace lacks a reliable operator/mode label; never manufacture one.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

from scripts.research.dcp14_enum_column import build_pairs


def summarize(events):
    pairs, orphans = build_pairs(events)
    grouped = defaultdict(list)
    excluded = Counter()
    for pair in pairs:
        if pair["status"] != "ok":
            excluded[pair["status"]] += 1
        elif pair["parent_tag"] != "before":
            excluded["later_parent"] += 1
        else:
            grouped[(pair["parent_role"], pair["delegate_role"])].append(pair)
    rows = []
    for (parent, child), group in sorted(grouped.items()):
        row = {"parent_role": parent, "delegate_role": child, "pairs": len(group)}
        for side in ("parent", "worker"):
            sizes = [p[f"{side}_prompt_chars"] for p in group]
            row[f"{side}_chars"] = {
                "min": min(sizes),
                "median": statistics.median(sizes),
                "max": max(sizes),
                "total": sum(sizes),
            }
        rows.append(row)
    return {
        "schema": "epyc.delegation.context_sizes.v1",
        "pairing": "DCP-14 latest earlier non-delegate in parent_request_id group",
        "unit": "captured Unicode characters; not tokens",
        "mode_available": False,
        "paired": len(pairs),
        "included": sum(r["pairs"] for r in rows),
        "excluded": dict(excluded),
        "no_parent_prompt": orphans,
        "by_role": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256()
    events = []
    with args.events.open("rb") as stream:
        for line in stream:
            digest.update(line)
            if line.strip():
                event = json.loads(line)
                # Sizes only need starts; retaining chunks duplicates large response text.
                if event.get("event") == "start":
                    events.append(event)
    result = summarize(events)
    result["input"] = {"path": str(args.events), "sha256": digest.hexdigest()}
    result["producer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result["pairer_sha256"] = hashlib.sha256(
        Path(__file__).with_name("dcp14_enum_column.py").read_bytes()
    ).hexdigest()
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("paired", "included", "excluded")}))


if __name__ == "__main__":
    main()
