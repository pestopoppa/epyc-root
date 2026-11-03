"""AutoKernel reliance review (VB-AK-RELIANCE-REVIEW): flag recorded proposals whose relied-on
claims have since been retracted or corrected.

The reader (`loop_beliefs.py`) tells a planner which claims are flagged NOW. This is the other
direction: AutoKernel keeps every accepted `relies_on_claims` id on the experiments row
(`controller/experiments.py`, table `experiments`, JSON `payload`; the id sits at
`payload.relies_on_claims` or, for a row that nests the hypothesis, `payload.hypothesis.
relies_on_claims`). After the ledger moves, this lists the rows that depended on a claim that no
longer stands.

No grade is computed here. Flags are fold output only (`fold.Belief`):
  * retracted -- support retracted with no live support left (`loop_beliefs.global_flags`'s
    "withdrawn" rule, verbatim);
  * corrected -- a correction is recorded against the claim's source entry (`Belief.corrections`).
Opposing evidence ("contested") is deliberately NOT a flag: it is not a retraction or correction.
A relied-on id is resolved through the fold's alias map first, so a row that cited a since-merged
alias is still found. A row with an empty/absent field is never flagged; a payload that does not
decode is reported as `undecodable`, never guessed at.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SCHEMA = "epyc.vidya.reliance_review.v1"
RELIANCE_FIELD = "relies_on_claims"


def flagged_claims(result: Any) -> dict[str, str]:
    """canonical claim id -> "retracted" | "corrected" from a `fold.FoldResult`."""
    out: dict[str, str] = {}
    for claim_id, belief in result.beliefs.items():
        if belief.retracted_support and not belief.pro_witnesses:
            out[claim_id] = "retracted"
        elif belief.corrections:
            out[claim_id] = "corrected"
    return out


def declared_reliance(payload: Any, field: str = RELIANCE_FIELD) -> list[str]:
    """The claim ids a decoded experiments payload declared, wherever the row carries them."""
    if not isinstance(payload, Mapping):
        return []
    hyp = payload.get("hypothesis")
    raw: list[Any] = list(payload.get(field) or [])
    if isinstance(hyp, Mapping):
        raw += list(hyp.get(field) or [])
    seen: dict[str, None] = {}
    for item in raw:
        if isinstance(item, str) and item:
            seen.setdefault(item, None)
    return list(seen)


def review(rows: Iterable[Mapping[str, Any]], flags: Mapping[str, str],
           aliases: Mapping[str, str] | None = None, field: str = RELIANCE_FIELD,
           ) -> dict[str, Any]:
    """`rows`: `{attempt_id, payload (dict or JSON text or None), ...}`. Returns the flagged rows
    (each with the exact relied-on ids that carry a flag) and the count of undecodable payloads."""
    aliases = aliases or {}
    flagged, undecodable, scanned, relied = [], [], 0, 0
    for row in rows:
        scanned += 1
        payload = row.get("payload")
        if isinstance(payload, (str, bytes)):
            try:
                payload = json.loads(payload)
            except ValueError:
                payload = None
        if payload is None:
            undecodable.append(str(row.get("attempt_id")))
            continue
        ids = declared_reliance(payload, field)
        if not ids:
            continue
        relied += 1
        hits = []
        for claim_id in ids:
            canon = aliases.get(claim_id, claim_id)
            if canon in flags:
                hits.append({"claim_id": claim_id, "canonical_id": canon, "status": flags[canon]})
        if hits:
            flagged.append({"attempt_id": row.get("attempt_id"),
                            "mechanism_id": row.get("mechanism_id"),
                            "status": row.get("status"), "flagged_claims": hits})
    return {"schema": SCHEMA, "scanned": scanned, "with_reliance": relied,
            "undecodable": undecodable, "flagged": flagged,
            "flagged_attempt_ids": [r["attempt_id"] for r in flagged]}


def read_experiments(db_path: str | Path) -> list[dict[str, Any]]:
    """Read-only dump of experiments rows (attempt_id, mechanism_id, status, payload text)."""
    conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(
            "SELECT attempt_id, mechanism_id, status, payload FROM experiments "
            "ORDER BY recorded_at, rowid")]
    finally:
        conn.close()


def review_ledger(rows: Iterable[Mapping[str, Any]], ledger_path: str | Path, *,
                  as_of: str | None = None, field: str = RELIANCE_FIELD) -> dict[str, Any]:
    """Verify the ledger chain, fold it (as the reader does), and review `rows` against it."""
    import loop_beliefs as lb
    from fold import fold
    from ledger import Ledger
    ledger = Ledger(ledger_path)
    errors = ledger.verify()
    if errors:
        raise ValueError(f"ledger chain broken: {errors[0]}")
    as_of = as_of or lb._now()
    result = fold(lb.visible_frames([r.frame for r in ledger.read_all()], as_of), as_of=as_of)
    out = review(rows, flagged_claims(result), dict(result.alias_map), field)
    out.update(as_of=as_of, ledger_path=str(ledger_path))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--experiments-db", required=True, help="AutoKernel experiments.db (read-only)")
    p.add_argument("--ledger", default=None, help="default: the canonical Vidya ledger")
    p.add_argument("--as-of", default=None)
    p.add_argument("--field", default=RELIANCE_FIELD)
    args = p.parse_args(argv)
    import loop_beliefs as lb
    out = review_ledger(read_experiments(args.experiments_db), lb.resolve_ledger(args.ledger),
                        as_of=args.as_of, field=args.field)
    print(json.dumps(out, sort_keys=True, default=str))
    return 3 if out["flagged"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
