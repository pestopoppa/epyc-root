"""KEEP-FAILED-EVIDENCE: a FAIL*/FUTILITY* row's out/logs, out/prof and out/servers/*.log survive reclaim until the row's
successor (same id_stem, higher -rN) has ended, or HOLD_HOURS after the row's own end record when no successor appears.
Origin: ak-c22-vattn-rf7-op-gpu-20261125 (FAIL_CORRECTNESS_TBO) lost out/logs at filing and was diagnosed blind.
Read-only helpers; reclaim_row applies the keep set, filing.run_deferred_reclaims releases the marker. Stdlib only."""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import time

HOLD_HOURS = 72
PROF_MAX_BYTES = 2 * 1024 ** 3
PROF_KEEP_NEWEST = 20
_ATTEMPT = re.compile(r"-r(\d+)(?:[-_]|$)")


def _stem(rid):
    here = os.path.dirname(os.path.abspath(__file__))
    rf = os.path.join(os.path.dirname(here), "rowflow")
    if rf not in sys.path:
        sys.path.insert(0, rf)
    import rowflow
    return rowflow.id_stem(rid)


def _attempt(rid):
    m = _ATTEMPT.search(rid)
    return int(m.group(1)) if m else 0


def verdict_of(flags, rid, m=None):
    """Filed row_verdict, else RESULT.json `verdict` at the manifest result_path; '' when unknown."""
    try:
        with open(os.path.join(flags, "filing-done", rid + ".verdict.json")) as fh:
            v = json.load(fh).get("row_verdict")
            if v:
                return str(v)
    except (OSError, ValueError, AttributeError):
        pass
    rp = (m or {}).get("result_path")
    if isinstance(rp, str) and rp:
        try:
            with open(rp) as fh:
                return str(json.load(fh).get("verdict") or "")
        except (OSError, ValueError, AttributeError):
            pass
    return ""


def is_failed(verdict):
    return str(verdict or "").upper().startswith(("FAIL", "FUTILITY"))


def successor_ended(flags, rid):
    """True when a row with the same id_stem and a higher -rN has grants/<id>.ended|.complete."""
    stem, n = _stem(rid), _attempt(rid)
    for suf in (".ended", ".complete"):
        for p in glob.glob(os.path.join(flags, "grants", "*" + suf)):
            o = os.path.basename(p)[:-len(suf)]
            if o != rid and _stem(o) == stem and _attempt(o) > n:
                return True
    return False


def hold_active(flags, rid, end_record, now=None):
    """True while the evidence must be kept: no ended successor and the end record is younger than HOLD_HOURS."""
    if successor_ended(flags, rid):
        return False
    try:
        age = (now or time.time()) - os.path.getmtime(end_record)
    except OSError:
        return True
    return age < HOLD_HOURS * 3600


def evidence_paths(root, log=print, rid="?"):
    """Paths to keep under scratch_root: out/logs (always whole), out/prof (newest PROF_KEEP_NEWEST files when over 2 GiB),
    out/servers/*.log."""
    keep = []
    logs = os.path.join(root, "out", "logs")
    if os.path.exists(logs):
        keep.append(logs)
    prof = os.path.join(root, "out", "prof")
    if os.path.isdir(prof):
        files = []
        for dp, _d, fns in os.walk(prof):
            for f in fns:
                p = os.path.join(dp, f)
                try:
                    st = os.lstat(p)
                    files.append((st.st_mtime, st.st_size, p))
                except OSError:
                    pass
        total = sum(s for _t, s, _p in files)
        if total > PROF_MAX_BYTES:
            files.sort(reverse=True)
            keep.extend(p for _t, _s, p in files[:PROF_KEEP_NEWEST])
            log(f"RECLAIM-KEEP-TRIM {rid}: out/prof {total} bytes > 2 GiB; keeping newest {min(PROF_KEEP_NEWEST, len(files))} files")
        else:
            keep.append(prof)
    keep.extend(sorted(glob.glob(os.path.join(root, "out", "servers", "*.log"))))
    return keep
