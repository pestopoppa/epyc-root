"""KT-2: the contradiction gate -- proposals in, quote-hashed queue rows out, nothing resolved.

A contradiction between two wiki or ledger-backed statements is the most expensive thing to get
wrong silently: both sides keep being cited, each by documents that never see the other. An LLM is
a cheap *proposer* of such pairs and a bad *judge* of them, so this gate takes the proposer's
output and admits a pair only when **both sides re-find verbatim** in the repository:

* each side names a repo-relative ``path``, a 1-based ``line`` and a ``quote``;
* the quote must appear in that file, on the stated line or within ``WINDOW`` lines of it
  (anchors drift as files are edited; the recorded line is the one where it was re-found);
* each side's quote is hashed (sha256 over the whitespace-normalised quote) and the pair id is the
  hash of the two side hashes in sorted order, so re-proposing a pair -- in either order -- is a
  no-op.

Admitted pairs are appended to ``QUEUE_PATH`` with ``status: pending``. That file is a sidecar of
the SC13 correction queue (``correction_queue.py``): ``vidya corrections`` reports it beside the
dive corrections, and adjudication happens the same way -- by the operator. **This module has no
code path that writes any status other than ``pending``**; there is no auto-resolve, by design.
A proposal that fails re-finding is reported back with its reasons and never filed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
QUEUE_PATH = REPO / "data" / "vidya" / "contradiction_queue.jsonl"
WINDOW = 5
SCHEMA = "epyc.vidya/contradiction_proposal/v1"


def _norm(text: str) -> str:
    return " ".join(text.split())


def quote_hash(quote: str) -> str:
    return hashlib.sha256(_norm(quote).encode("utf-8")).hexdigest()


def verify_side(side: dict, repo: Path = REPO) -> tuple[dict | None, str | None]:
    """Re-find one side. Returns (verified side, None) or (None, reason)."""
    for key in ("path", "line", "quote"):
        if not side.get(key):
            return None, f"missing {key}"
    quote = _norm(str(side["quote"]))
    if len(quote) < 12:
        return None, "quote shorter than 12 characters cannot identify a statement"
    rel = str(side["path"])
    path = (repo / rel).resolve()
    if not str(path).startswith(str(repo.resolve())) or not path.is_file():
        return None, f"path not found in repo: {rel}"
    try:
        line = int(side["line"])
    except (TypeError, ValueError):
        return None, "line is not an integer"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    order = [line] + [line + d * s for d in range(1, WINDOW + 1) for s in (-1, 1)]
    for n in order:
        if 1 <= n <= len(lines) and quote in _norm(lines[n - 1]):
            return {"path": rel, "line": n, "quote": quote, "sha256": quote_hash(quote),
                    "line_as_proposed": line}, None
    return None, f"quote not found at {rel}:{line} (+/-{WINDOW})"


def pair_id(a: dict, b: dict) -> str:
    return "ctr_" + hashlib.sha256("|".join(sorted((a["sha256"], b["sha256"]))).encode()).hexdigest()[:16]


def load_queue(path: Path = QUEUE_PATH) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]


def gate(proposals: list[dict], *, repo: Path = REPO, queue: Path = QUEUE_PATH,
         now: str | None = None, write: bool = True) -> dict:
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    existing = {r["id"] for r in load_queue(queue)}
    filed, rejected, duplicate = [], [], []
    for i, prop in enumerate(proposals):
        a, ra = verify_side(prop.get("a") or {}, repo)
        b, rb = verify_side(prop.get("b") or {}, repo)
        if a is None or b is None:
            rejected.append({"index": i, "reasons": [r for r in (ra and f"a: {ra}", rb and f"b: {rb}") if r]})
            continue
        if a["sha256"] == b["sha256"]:
            rejected.append({"index": i, "reasons": ["both sides quote the same text"]})
            continue
        pid = pair_id(a, b)
        if pid in existing:
            duplicate.append(pid)
            continue
        existing.add(pid)
        filed.append({
            "schema": SCHEMA, "id": pid, "kind": "contradiction", "status": "pending",
            "a": a, "b": b, "rationale": str(prop.get("rationale", "")),
            "proposer": str(prop.get("proposer", "unknown")), "filed_at": now,
        })
    if write and filed:
        queue.parent.mkdir(parents=True, exist_ok=True)
        with queue.open("a", encoding="utf-8") as fh:
            for row in filed:
                fh.write(json.dumps(row, sort_keys=True) + "\n")
    return {"filed": filed, "rejected": rejected, "duplicate": duplicate}


def pending(queue: Path = QUEUE_PATH) -> list[dict]:
    return [r for r in load_queue(queue) if r.get("status") == "pending"]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("file", help="gate a JSON list of proposals into the queue")
    f.add_argument("proposals", help="JSON file: list of {a:{path,line,quote}, b:{...}, rationale, proposer}")
    f.add_argument("--dry-run", action="store_true")
    f.add_argument("--queue", default=str(QUEUE_PATH))
    ls = sub.add_parser("list", help="pending contradictions")
    ls.add_argument("--queue", default=str(QUEUE_PATH))
    args = p.parse_args(argv)
    if args.cmd == "file":
        props = json.loads(Path(args.proposals).read_text())
        res = gate(props if isinstance(props, list) else [props], queue=Path(args.queue),
                   write=not args.dry_run)
        print(json.dumps({k: (len(v) if k != "rejected" else v) for k, v in res.items()}, indent=2))
        return 0 if not res["rejected"] else 4
    print(json.dumps(pending(Path(args.queue)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
