#!/usr/bin/env python3
"""owner_watch.py - owner-watcher liveness (AK row-robustness RCA 2026-11-24 item 6b / F10).

The row-owner-loop watcher (`watch_rows.sh`) is a `while true` loop with no heartbeat; when it died nobody noticed and the
smoke-fail inbox went undrained for hours. watch_rows.sh now touches <flags>/state/owner-watch/<owner>.hb every loop; the
keeper calls check() each tick:

    owner has live rows (ready/ manifests) AND <owner>.hb older than STALE_S  -> OWNER-WATCHER-DEAD <owner>, once per change
                                                                                 (re-armed when the heartbeat is fresh again)
    owner has live rows and NO <owner>.hb (never ran the watcher)            -> one INFO log line, no alert

State: <flags>/state/owner-watch/.alerted.json. Never raises into the keeper (the caller wraps it too)."""
from __future__ import annotations

import json
import os
import time

STALE_S = 600


def hb_dir(flags):
    return os.path.join(flags, "state", "owner-watch")


def _state_path(flags):
    return os.path.join(hb_dir(flags), ".alerted.json")


def _load(p):
    try:
        with open(p) as f:
            v = json.load(f)
        return v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f, indent=1, sort_keys=True)
    os.replace(tmp, p)


def check(flags, allrows, notify_mod=None, log=print, now=None):
    """Returns the list of owners alerted this call."""
    now = time.time() if now is None else now
    owners = sorted({str((d or {}).get("owner") or "") for d in (allrows or {}).values()} - {""})
    st = _load(_state_path(flags))
    dead, info = dict(st.get("dead") or {}), set(st.get("info_logged") or [])
    alerted = []
    for o in owners:
        hb = os.path.join(hb_dir(flags), o + ".hb")
        try:
            age = now - os.path.getmtime(hb)
        except OSError:
            if o not in info:
                log(f"INFO OWNER-WATCHER-NONE {o}: live rows but no {hb} (watcher never ran); no alert")
                info.add(o)
            continue
        if age <= STALE_S:
            dead.pop(o, None)
            continue
        if o in dead:
            continue   # once per change
        n = sum(1 for d in allrows.values() if str((d or {}).get("owner") or "") == o)
        msg = f"OWNER-WATCHER-DEAD {o}: heartbeat {int(age)} s old (> {STALE_S} s) with {n} live row(s); re-arm watch_rows.sh"
        log(msg)
        if notify_mod is not None:
            try:
                notify_mod.emit(flags, "owner-watcher-dead", "", f"{o}:{int(os.path.getmtime(hb))}", msg, "warning", o,
                                {"owner": o, "heartbeat": hb, "age_s": int(age), "live_rows": n})
            except Exception as e:  # noqa: BLE001
                log(f"OWNER-WATCHER-DEAD {o}: notify failed: {type(e).__name__}: {e}")
        dead[o] = now
        alerted.append(o)
    new = {"dead": dead, "info_logged": sorted(info)}
    if new != {"dead": dict(st.get("dead") or {}), "info_logged": sorted(st.get("info_logged") or [])}:
        _save(_state_path(flags), new)
    return alerted
