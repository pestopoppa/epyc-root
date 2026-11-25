#!/usr/bin/env python3
"""family_strikes.py - AK waste audit 2026-11-25 (docs/design/ak-waste-audit-20261125.md §3) R2/R3/R5/R6/R7.

Strikes are keyed by row FAMILY (rowflow.id_stem: the id without -rN), never by row id or job sha. The per-id
SMOKE-STRIKES.json reset on every -rN (count=1 on each of devhandoff r2..r6) and the lineage MAX_FAILS park was bypassed by
fresh_attempt() on every job.py edit; this file is the one counter both paths now consult.

  state      <flags>/dryrun/.family/<stem>.json   (dot dir: never globbed as a row by dryrun/*)
  unpark log <flags>/dryrun/.family/UNPARK.log + the keeper log

R2  record_strike / record_clear (PASS, RESULT) ; park at PARK_AT strikes; publish refuses ; unpark_family resets.
R3  harness failures do not strike the candidate family.
R5  stale_fail_escalations(): a family whose last smoke FAILED and was not republished -> smoke-fail-stale at 2 h / 8 h
    (1 h / 4 h for rank <= 10 or operator_approved), stage 2 repeating every 8 h (4 h). needs_republish() for queue_status.
R6  GPU smokes per family per UTC day; the (GPU_SMOKE_BUDGET+1)-th is refused at publish unless overridden by the operator.
R7  strike_today() suppresses PREEMPT-PROPOSE for a striking family.

republish_allowed(flags, spec) is THE publish-time hook; R1 (replay receipt, ak_gate.py) extends it - add checks there.
Every reader is fail-soft (a corrupt file reads as empty); writers are atomic.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rowflow as rf  # noqa: E402

PARK_AT = 2
GPU_SMOKE_BUDGET = 3
MIN_ELAPSED_S = 60
STALE_T = (2 * 3600, 8 * 3600)
STALE_T_URGENT = (3600, 4 * 3600)
URGENT_RANK = 10
STALE_MAX_AGE_S = 3 * 86400
PREEMPT_FAIL_YOUNG_S = 2 * 3600
OPERATOR_IDS = ("operator",)
HARNESS_VERDICT_RX = re.compile(r"^(FUTILITY_HARNESS\w*|FUTILITY_WITNESS\w*|FUTILITY_RESIDENCY\w*|INCOMPLETE\w*|INCONCLUSIVE\w*)$")


def family_dir(flags): return os.path.join(flags, "dryrun", ".family")
def family_path(flags, stem): return os.path.join(family_dir(flags), stem + ".json")
def stem_of(rid): return rf.id_stem(str(rid or ""))
def _day(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")


def load(flags, stem):
    rec = rf.load_json(family_path(flags, stem))
    rec = rec if isinstance(rec, dict) else {}
    rec.setdefault("stem", stem)
    for k in ("strikes", "gpu_smokes", "history", "budget_overrides"):
        rec.setdefault(k, [])
    rec.setdefault("count", 0)
    return rec


def _save(flags, rec):
    os.makedirs(family_dir(flags), exist_ok=True)
    rec["history"] = rec["history"][-200:]
    rec["gpu_smokes"] = rec["gpu_smokes"][-100:]
    rf.atomic_json(family_path(flags, rec["stem"]), rec)


def manifest_of(flags, rid):
    for p in (rf.ready_path(flags, rid), os.path.join(rf.dry_dir(flags, rid), "unpublished.json"),
              os.path.join(flags, "ready", ".withdrawn", rid + ".json")):
        m = rf.load_json(p)
        if isinstance(m, dict) and m:
            return m
    return {}


def _meta(rec, m):
    for k in ("owner", "priority_rank", "operator_approved", "lane"):
        if m.get(k) is not None:
            rec[k] = m[k]


def record_strike(flags, rid, kind, msg, key=None, now=None, manifest=None):
    """One strike for rid's family. Idempotent per (rid, kind, key). -> the family record."""
    now = time.time() if now is None else now
    stem = stem_of(rid)
    rec = load(flags, stem)
    k = f"{rid}|{kind}|{key or ''}"
    if any(s.get("key") == k for s in rec["strikes"]) or any(h.get("key") == k for h in rec["history"]):
        return rec
    _meta(rec, manifest if manifest is not None else manifest_of(flags, rid))
    s = {"id": rid, "kind": kind, "at": now, "msg": str(msg or "")[:300], "key": k}
    rec["strikes"].append(s)
    rec["history"].append(dict(s, ev="strike"))
    rec["count"] = len(rec["strikes"])
    rec["last_fail_at"], rec["last_fail_id"] = now, rid
    _save(flags, rec)
    return rec


def record_clear(flags, rid, verdict, now=None):
    """PASS / RESULT: the family's strike count resets (only these do, besides unpark)."""
    now = time.time() if now is None else now
    rec = load(flags, stem_of(rid))
    if not rec["strikes"] and not rec.get("last_fail_at"):
        return rec
    rec["history"].append({"ev": "clear", "id": rid, "verdict": verdict, "at": now})
    rec["strikes"], rec["count"] = [], 0
    rec.pop("last_fail_at", None); rec.pop("last_fail_id", None); rec.pop("escalated", None)
    _save(flags, rec)
    return rec


def park_reason(flags, stem):
    rec = load(flags, stem)
    if rec["count"] < PARK_AT:
        return None
    ids = ",".join(dict.fromkeys(s["id"] for s in rec["strikes"]))
    return (f"PARKED {stem}: {rec['count']} failed smokes ({ids}); unpark with "
            f"rowflow.py unpark --family {stem} --by <owner> --reason R")


def gpu_smokes_today(flags, stem, now=None):
    now = time.time() if now is None else now
    d = _day(now)
    return [g for g in load(flags, stem)["gpu_smokes"] if _day(float(g.get("at") or 0)) == d]


def record_gpu_smoke(flags, rid, verdict, now=None):
    now = time.time() if now is None else now
    rec = load(flags, stem_of(rid))
    rec["gpu_smokes"].append({"id": rid, "verdict": verdict, "at": now})
    _save(flags, rec)


def budget_reason(flags, stem, now=None):
    now = time.time() if now is None else now
    used = gpu_smokes_today(flags, stem, now)
    extra = sum(1 for o in load(flags, stem)["budget_overrides"] if o.get("day") == _day(now))
    if len(used) < GPU_SMOKE_BUDGET + extra:
        return None
    return (f"SMOKE-BUDGET {stem}: {len(used)} GPU smokes today (UTC {_day(now)}; budget {GPU_SMOKE_BUDGET}/family/day: "
            f"{','.join(g['id'] for g in used)}); override with publish_row.py <spec> --smoke-budget-by operator --reason R")


def override_budget(flags, stem, by, reason, now=None, log=None):
    now = time.time() if now is None else now
    rf.need(by in OPERATOR_IDS, f"--smoke-budget-by must be the operator, not {by!r}")
    rf.need(str(reason or "").strip(), "--reason required for a smoke-budget override")
    rec = load(flags, stem)
    o = {"day": _day(now), "by": by, "reason": reason, "at": now}
    rec["budget_overrides"].append(o)
    rec["history"].append(dict(o, ev="budget-override"))
    _save(flags, rec)
    _log(flags, f"SMOKE-BUDGET-OVERRIDE {stem} by={by} reason={reason}", log)


def is_gpu(spec):
    return str((spec or {}).get("lane") or "") == "gpu"


def replay_receipt_status(flags, spec):
    """R1 (pipeline-mgmt, ak_gate 2026-11-25): (enforced, valid, why) of the replay-receipt gate for this republish, via
    preflight.check_replay_receipt (receipt = out/REPLAY-RECEIPT.json from job.py --replay, spec.replay_receipt, or the R4
    replay preflight already recorded in spec.preflight.replay_decide). valid = the family's last smoke FAILED and the
    receipt binds to that failure with a different failure class (or spec.fix_ref names a new kernel store). Never raises."""
    try:
        import preflight as PF
        row = PF.Row(spec)
        last = PF.family_last_smoke(flags, row.id)
        rd = ((spec or {}).get("preflight") or {}).get("replay_decide")
        res = PF.check_replay_receipt(row, {"flags": flags, "replay_decide": {row.id: rd} if rd else {}})
        fails = [f"{c}: {m}" for lv, c, m in res if lv == "FAIL"]
        valid = bool(last and last["kind"] == "FAIL" and not fails)
        return bool(PF.PREFLIGHT_ENFORCE.get("replay_receipt")), valid, "; ".join(fails)
    except Exception as e:  # noqa: BLE001 - the receipt gate never crashes a publish (WARN-first)
        return False, False, f"replay receipt not judged: {type(e).__name__}: {e}"


def republish_allowed(flags, spec, now=None):
    """-> (ok, reason). THE publish-time family gate (R2 park, R6 GPU budget, R1 replay receipt). A validated R1 receipt is
    an automatic unpark reason for R2 (one attempt: the receipt binds to the family's latest FAIL, so the next FAIL needs
    a new one). The R1 refusal itself applies only once preflight.PREFLIGHT_ENFORCE["replay_receipt"] is True."""
    stem = stem_of((spec or {}).get("id"))
    enforced, valid, rwhy = replay_receipt_status(flags, spec)
    why = park_reason(flags, stem)
    if why and not valid:
        return False, why
    if is_gpu(spec):
        why = budget_reason(flags, stem, now)
        if why:
            return False, why
    if enforced and rwhy:
        return False, "replay receipt (R1): " + rwhy
    return True, ""


def _log(flags, line, log=None):
    stamp = rf.now_iso()
    try:
        os.makedirs(family_dir(flags), exist_ok=True)
        with open(os.path.join(family_dir(flags), "UNPARK.log"), "a") as f:
            f.write(f"{stamp} {line}\n")
        with open(os.path.join(flags, "ws58-calendar-keeper.log"), "a") as f:
            f.write(f"{stamp} {line}\n")
    except OSError:
        pass
    (log or print)(line)


def unpark_family(flags, stem, by, reason, now=None, log=None):
    """owner or operator only; logged UNPARK; resets the count (the next FAIL strikes from zero)."""
    now = time.time() if now is None else now
    rec = load(flags, stem)
    owner = str(rec.get("owner") or "")
    rf.need(by and (by in OPERATOR_IDS or (owner and by == owner)),
            f"unpark --family {stem}: --by must be the family owner ({owner or 'unknown'}) or the operator, not {by!r}")
    rf.need(str(reason or "").strip(), "unpark --family needs --reason")
    h = {"ev": "unpark", "by": by, "reason": reason, "at": now, "cleared": [s["id"] for s in rec["strikes"]]}
    rec["history"].append(h)
    rec["strikes"], rec["count"] = [], 0
    rec.pop("escalated", None)
    _save(flags, rec)
    _log(flags, f"UNPARK {stem} by={by} reason={reason} cleared={len(h['cleared'])}", log)
    return h


def strike_today(flags, stem, now=None):
    """R7: the family has a strike in this UTC day or a FAIL younger than PREEMPT_FAIL_YOUNG_S."""
    now = time.time() if now is None else now
    rec = load(flags, stem)
    if any(_day(float(s.get("at") or 0)) == _day(now) for s in rec["strikes"]):
        return True
    return bool(rec.get("last_fail_at")) and now - float(rec["last_fail_at"]) < PREEMPT_FAIL_YOUNG_S


# ---------------------------------------------------------------- R3
def _units(res, result_path):
    for k in ("units", "n_units", "units_done"):
        v = (res or {}).get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return int(v)
        if isinstance(v, list):
            return len(v)
    if result_path:
        try:
            with open(os.path.join(os.path.dirname(result_path), "results.jsonl")) as f:
                return sum(1 for ln in f if ln.strip())
        except OSError:
            pass
    return 0


def ended_elapsed(flags, rid):
    try:
        txt = open(os.path.join(flags, "grants", rid + ".ended"), errors="replace").read(4000)
    except OSError:
        return None
    t = re.search(r"(?:^|\s)time=(\S+)", txt)
    s = re.search(r"(?m)^started=(\S+)", txt)
    a, b = (rf.iso_epoch(s.group(1)) if s else None), (rf.iso_epoch(t.group(1)) if t else None)
    return (b - a) if a and b else None


def harness_strike(res, cls=None, elapsed_s=None, manifest=None, result_path=None):
    """Compatibility no-op: pipeline and harness faults must not strike a candidate family."""
    return False, ""


# ---------------------------------------------------------------- R5
def _thresholds(m):
    try:
        rank = float(m.get("priority_rank", 100))
    except (TypeError, ValueError):
        rank = 100.0
    return STALE_T_URGENT if (rank <= URGENT_RANK or m.get("operator_approved") is True) else STALE_T


def _republished_after(flags, stem, t):
    pats = [os.path.join(flags, "ready", "*.json")] + [os.path.join(flags, "dryrun", "*", n) for n in
            ("unpublished.json", "SMOKE-QUEUED.json", "GPU-SMOKE-QUEUED.json", "PASS.json", "RUNNING.json")]
    for pat in pats:
        for p in glob.glob(pat):
            rid = os.path.basename(p)[:-5] if pat.endswith("*.json") else os.path.basename(os.path.dirname(p))
            if stem_of(rid) != stem:
                continue
            try:
                if os.path.getmtime(p) > t:
                    return True
            except OSError:
                continue
    return False


def _withdrawn(flags, rid):
    dd = rf.dry_dir(flags, rid)
    return (os.path.isdir(os.path.join(dd, ".withdrawn")) or os.path.exists(os.path.join(dd, ".superseded"))
            or os.path.exists(os.path.join(flags, "withdrawn", rid + ".json"))
            or os.path.exists(os.path.join(flags, "ready", ".withdrawn", rid + ".json"))
            or os.path.exists(os.path.join(flags, "ready", ".withdrawn", rid + ".pending.json")))


def _inactive_stale_reason(flags, rid):
    if _withdrawn(flags, rid):
        return "withdrawn"
    if not os.path.isfile(rf.ready_path(flags, rid)):
        return "absent from queue"
    if park_reason(flags, stem_of(rid)):
        return "family parked"
    return ""


def stale_fails(flags, now=None):
    """-> [{stem, id, fail_at, age_s, rank, owner, operator_approved, t1, t2}] families whose newest dry-run outcome is a
    smoke FAIL (not an arming/launch fail) with no republish/PASS after it and no withdrawal. Scans FAIL-N.json directly,
    so it does not depend on unpublished.json or the family file surviving."""
    now = time.time() if now is None else now
    last = {}
    for fp in glob.glob(os.path.join(flags, "dryrun", "*", "FAIL-*.json")):
        rid = os.path.basename(os.path.dirname(fp))
        f = rf.load_json(fp) or {}
        if rf.is_arm_fail(f):
            continue
        at = rf.iso_epoch(f.get("at")) or os.path.getmtime(fp)
        if now - at > STALE_MAX_AGE_S:
            continue
        st = stem_of(rid)
        if st not in last or at > last[st][0]:
            last[st] = (at, rid)
    out = []
    for st, (at, rid) in sorted(last.items()):
        if _inactive_stale_reason(flags, rid) or _republished_after(flags, st, at + 1):
            continue
        m = manifest_of(flags, rid)
        fam = load(flags, st)
        if fam.get("dropped"):
            continue
        t1, t2 = _thresholds({**{k: fam.get(k) for k in ("priority_rank", "operator_approved") if fam.get(k) is not None}, **m})
        out.append({"stem": st, "id": rid, "fail_at": at, "age_s": now - at, "rank": m.get("priority_rank"),
                    "owner": str(m.get("owner") or fam.get("owner") or ""), "operator_approved": m.get("operator_approved") is True,
                    "t1": t1, "t2": t2})
    return out


def stale_fail_escalations(flags, log=print, emit=None, now=None):
    """Keeper tick. -> [(id, stage)] emitted. Stage 1 (warning) at t1; stage 2 (critical, + operator) at t2, repeated every t2."""
    now = time.time() if now is None else now
    if emit is None:
        import notify
        emit = notify.emit
    # Resolve every outstanding stage, including alerts whose FAIL has aged out or disappeared.
    try:
        import notify
        for alert in notify.read_inbox(flags, unacked=True):
            rid = str(alert.get("row_id") or "")
            if alert.get("kind") != "smoke-fail-stale" or not rid:
                continue
            reason = _inactive_stale_reason(flags, rid)
            if reason:
                notify.ack(flags, str(alert["key"]), by="auto-ack-stale-inactive",
                           note=f"auto-ack: {reason}")
    except Exception as ex:  # noqa: BLE001 - notification cleanup must not stop the scan
        log(f"SMOKE-FAIL-STALE cleanup failed: {type(ex).__name__}: {ex}")
    out = []
    for s in stale_fails(flags, now):
        age = s["age_s"]
        if age < s["t1"]:
            continue
        stage = 1 if age < s["t2"] else 1 + int(age // s["t2"])
        disc = f"{int(s['fail_at'])}:{stage}"
        sev = "warning" if stage == 1 else "critical"
        h = age / 3600
        msg = (f"SMOKE-FAIL-STALE {s['id']} (family {s['stem']}, rank {s['rank']}, "
               f"{'operator-approved, ' if s['operator_approved'] else ''}owner {s['owner'] or '?'}): its smoke FAILED "
               f"{h:.1f} h ago and nothing was republished. Fix and republish (publish_row.py <spec>), or withdraw it "
               f"(rowflow.py withdraw {s['id']} --reason ...)")
        try:
            emit(flags, "smoke-fail-stale", s["id"], disc, msg, sev, s["owner"],
                 {"stem": s["stem"], "age_s": int(age), "stage": stage, "rank": s["rank"],
                  "operator_approved": s["operator_approved"], "escalate_to": "operator" if stage > 1 else ""})
            out.append((s["id"], stage))
        except Exception as ex:  # noqa: BLE001
            log(f"SMOKE-FAIL-STALE {s['id']}: notify failed: {type(ex).__name__}: {ex}")
    for rid, stage in out:
        log(f"SMOKE-FAIL-STALE {rid} stage={stage}")
    return out


def needs_republish(flags, now=None):
    """queue_status NEEDS-REPUBLISH rows for stale failed smokes (age shown)."""
    out = []
    for s in stale_fails(flags, now):
        fam = load(flags, s["stem"])
        out.append({"id": s["id"], "owner": s["owner"], "rank": s["rank"], "age_h": round(s["age_s"] / 3600, 1),
                    "reason": f"smoke FAILED {s['age_s'] / 3600:.1f} h ago, not republished; family {s['stem']} "
                              f"STRIKE {fam['count']}/{PARK_AT}" + (" (operator-approved)" if s["operator_approved"] else "")})
    return out


if __name__ == "__main__":
    print(json.dumps(stale_fails(sys.argv[1] if len(sys.argv) > 1 else rf.FLAGS), indent=1))
