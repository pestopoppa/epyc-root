"""Freshness classification for the handoff dashboard hub.

THE ONE CLASSIFIER. Before AK6 this module held an mtime badge and ``server.py``
held two more hand-rolled copies of the same threshold ladder
(``_kernel_contract_freshness``, ``_outcome_contract_freshness``). Three copies of
one rule is three thresholds vocabularies waiting to drift, and a per-panel
freshness envelope needs one. ``classify_age`` is that rule; everything else here
and in ``dashboard/panels.py`` calls it.

The four classes, and their AK6 spellings:

    fresh    advanced within warn_s                      (AK6: fresh)
    aging    older than warn_s, within stale_s           (AK6: warn)
    stale    older than stale_s — regeneration is broken  (AK6: stale)
    missing  nothing to date it by                        (AK6: ABSENT)

SEMANTIC TIMESTAMPS, NOT MTIME. ``classify_age`` takes an AGE, and the caller is
expected to compute it from a timestamp the PRODUCER wrote (``produced_at``,
``generated_at``, ``runs[].ts``), never from ``stat()``. A no-op re-export moves
an mtime and moves nothing else, so an mtime badge reads "fresh forever" over a
producer that has stopped — the exact failure ``dashboard/panels.py`` exists to
close. ``classify`` (mtime) is kept only for artifacts that carry no timestamp of
their own, and it says so.
"""

from __future__ import annotations

import time
from pathlib import Path

CLASS_FRESH = "fresh"
CLASS_AGING = "aging"
CLASS_STALE = "stale"
CLASS_MISSING = "missing"
CLASSES = (CLASS_FRESH, CLASS_AGING, CLASS_STALE, CLASS_MISSING)


def classify_age(age_s: float | None, warn_s: float | None,
                 stale_s: float | None) -> str:
    """Classify an age in seconds against a warn/stale ladder.

    ``None`` anywhere yields ``missing``: an age nobody could compute is not
    "fine", it is undated, and every consumer in this project must read an
    undated panel as absent rather than as healthy.
    """
    if age_s is None or warn_s is None or stale_s is None:
        return CLASS_MISSING
    if age_s <= warn_s:
        return CLASS_FRESH
    if age_s <= stale_s:
        return CLASS_AGING
    return CLASS_STALE


def classify(path: Path, warn_s: float, stale_s: float, *, now: float | None = None) -> dict:
    """Return ``{staleness_class, age_s, mtime}`` for ``path`` — MTIME-BASED.

    Legacy/last-resort: only correct for an artifact that carries no timestamp of
    its own. Anything with a producer-written timestamp must be classified from
    that timestamp through ``classify_age`` instead, or a touch will read as
    progress. See ``dashboard/panels.py``.
    """
    now = time.time() if now is None else now
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {"staleness_class": CLASS_MISSING, "age_s": None, "mtime": None}
    age = max(0.0, now - mtime)
    return {"staleness_class": classify_age(age, warn_s, stale_s),
            "age_s": round(age, 1), "mtime": round(mtime, 3)}
