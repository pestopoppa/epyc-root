"""PROPOSED pure policy; not installed, no authority to grant or bypass a HOLD."""
from datetime import datetime, timezone
import re

UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z\Z")

def epoch(value):
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise ValueError("strict UTC Z required")
    return int(datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ" if len(value) == 20 else "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).timestamp())

def admit(*, notes, booking_class, substrate, regions, start, end, now,
          holds, adopted=False):
    """holds: immutable {HOLD_basename: full text}; remaining guards run separately.

    Every present HOLD must authorize the interval. Missing/malformed fields refuse.
    Caller must bind these exact times/regions to the actual canonical grant and
    re-read the snapshots immediately before writing, after claim acquisition,
    and before the job body. No environment variable or launcher flag grants pool status.
    """
    try:
        s, e, n = epoch(start), epoch(end), epoch(now)
    except (TypeError, ValueError):
        return False, "invalid-grant-time"
    if not s <= n < e:
        return False, "outside-live-grant"
    if not holds:
        return True, "no-hold; other-guards-required"
    if not adopted:
        return False, "owner-policy-not-adopted"
    if "pool:gap-filler" not in re.split(r"[\s;]+", notes.strip()):
        return False, "not-pool"
    if booking_class != "block-correctness" or substrate != "cpu":
        return False, "not-model-free-cpu-correctness"
    if not 600 <= e - s <= 2700:
        return False, "pool-window-out-of-range"
    if canonical_quarter(regions) is None:
        return False, "not-one-quarter"
    for name, text in holds.items():
        if not name.startswith("HOLD_") or "/" in name:
            return False, "invalid-hold-name"
        fields = [line[len("quiet_not_before="):] for line in text.splitlines()
                  if line.startswith("quiet_not_before=")]
        if len(fields) != 1:
            return False, "missing-or-duplicate-quiet-time"
        try:
            quiet = epoch(fields[0])
        except (TypeError, ValueError):
            return False, "malformed-quiet-time"
        if e > quiet - 300:
            return False, "quiet-margin"
    return True, "pool-fits-all-holds; other-guards-required"

def canonical_quarter(region):
    """Normalize only complete canonical one-quarter tokens; no partial expansion."""
    return {"q0": "q0", "0-23": "q0", "q1": "q1", "24-47": "q1",
            "q2": "q2", "48-71": "q2", "q3": "q3", "72-95": "q3"}.get(region)
