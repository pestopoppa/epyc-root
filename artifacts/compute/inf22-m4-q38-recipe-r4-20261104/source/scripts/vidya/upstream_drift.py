"""Detect entries whose SOURCE was revised after we recorded it.

intake-110 is the motivating case and it is the purest form of the failure this substrate exists
for: nobody touched the record, and it became false anyway. The entry was ingested 2026-03-14
against arXiv v1 of a paper now at v7; the authors had found their headline accuracy gain was a
scoring artifact and revised it away. Our copy of the v1 abstract kept asserting it.

The check is cheap because arXiv reports the current version's date in the same batched query the
title backfill already uses. An entry is FLAGGED when the paper was updated after we ingested it —
that is not proof the record is wrong, it is proof nobody has looked since the source moved, which
is the only thing a machine can honestly say here.

    upstream_drift.py --limit 200          # sweep and report
    upstream_drift.py --limit 200 --json out.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX = REPO_ROOT / "research" / "intake_index.yaml"
API = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom"}
BATCH = 25


def _bare(aid: str) -> str:
    return re.sub(r"v\d+$", "", str(aid).strip().lower().removesuffix(".pdf"))


def sweep(entries: list[dict], *, limit: int, delay: float = 3.0) -> dict:
    targets = [e for e in entries
               if e.get("arxiv_id") and e.get("ingested_date")][:limit]
    by_id = {_bare(e["arxiv_id"]): e for e in targets}

    drifted, current, unresolved = [], 0, []
    ids = sorted(by_id)
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        url = f"{API}?{urllib.parse.urlencode({'id_list': ','.join(chunk), 'max_results': len(chunk)})}"
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                root = ET.fromstring(r.read())
        except Exception:
            unresolved.extend(chunk)
            time.sleep(delay)
            continue

        seen = set()
        for ent in root.findall("a:entry", NS):
            raw = (ent.findtext("a:id", "", NS) or "").rsplit("/", 1)[-1]
            bare = _bare(raw)
            version = raw[len(bare):] or "v1"
            updated = (ent.findtext("a:updated", "", NS) or "")[:10]
            e = by_id.get(bare)
            if not e:
                continue
            seen.add(bare)
            ingested = str(e["ingested_date"])[:10]
            if updated and updated > ingested:
                drifted.append({
                    "id": e["id"],
                    "arxiv_id": bare,
                    "ingested": ingested,
                    "source_updated": updated,
                    "current_version": version,
                    "title_recorded": str(e.get("title"))[:80],
                    "verification": e.get("verification"),
                })
            else:
                current += 1
        unresolved.extend(c for c in chunk if c not in seen)
        time.sleep(delay)

    drifted.sort(key=lambda d: d["source_updated"], reverse=True)
    return {
        "checked": len(targets),
        "current": current,
        "drifted": drifted,
        "unresolved": sorted(set(unresolved)),
        "note": (
            "A drifted entry is not necessarily wrong. It means the paper changed after we "
            "recorded it and nobody has looked since — which is the only thing this check can "
            "honestly assert. intake-110 is the case where it mattered: the authors revised away "
            "the exact figure our entry quoted."
        ),
    }


def main() -> int:
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--json", help="write the full report here")
    args = ap.parse_args()

    entries = yaml.safe_load(INDEX.read_text()) or []
    report = sweep(entries, limit=args.limit, delay=args.delay)

    print(f"checked {report['checked']} arXiv entries: "
          f"{len(report['drifted'])} drifted, {report['current']} current, "
          f"{len(report['unresolved'])} unresolved")
    for d in report["drifted"][:25]:
        print(f"  {d['id']}  ingested {d['ingested']}  source updated {d['source_updated']} "
              f"({d['current_version']})  [{d['verification'] or 'unverified'}]")
        print(f"      {d['title_recorded']}")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1, sort_keys=True))
        print(f"written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
