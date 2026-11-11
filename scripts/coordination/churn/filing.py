#!/usr/bin/env python3
"""filing.py -- the ONE atomic FILED writer plus the commit-receipt / supersede / withdrawn / auto-link filers
(operator 2026-11-07 "Approve all": make filing automatic; root cause: owners record verdicts in handoff box commits or ack
the rowflow alert and treat that as done, file_result.py never runs, filing-done/<id>.FILED is never written).

  write_filed(flags, rid, summary, record)   FILED is created with link(2) from a private temp file: atomic, and exactly one of
                                             N concurrent filers wins; every other caller is a no-op (returns False). The
                                             .verdict.json is published first (os.replace) so FILED never precedes its record.
  verify_receipt(repo, receipt, rid, lineage) git checks behind `file_result.py --receipt <commit>:<handoff>#<BOX-ID>`.
  file_terminal(...)                          SUPERSEDED / WITHDRAWN filing (no result needed).
  supersede_lineage(flags, new_id|None, ...)  every earlier ended-unfiled attempt of the lineage -> SUPERSEDED-BY <later id>;
                                             new_id=None is the one-time backfill over all lineages.
  autolink(flags, repo, ...)                  janitor sweep: ONE verified origin/main commit per ended-unfiled row -> FILED.
  load_manifest / load_end                    THE readers of a row's manifest and end record (file_result, auto_file and
                                             reclaim_row import them from here; filing never imports file_result).
Stdlib only. Filing never deletes; reclaim is run_reclaim -> reclaim_row (guarded by scratch_guard.py).
"""
from __future__ import annotations

import datetime
import fnmatch
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "rowflow"))

try:
    import handoff_ref  # noqa: E402  (installed beside this file in bin/churn)
except ImportError:  # repo checkout: scripts/coordination/handoff_ref.py
    sys.path.insert(0, os.path.dirname(HERE))
    import handoff_ref  # noqa: E402
DEFAULT_FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")   # the one definition of the live flags root
TERMINAL_VERDICTS = ("SUPERSEDED", "WITHDRAWN")
BOX_LINE = re.compile(r"^\s*[-*]\s+\[[ xX~!-]\]\s")
BOX_ID = re.compile(r"\*\*([A-Za-z0-9][\w.\-]*)\*\*")   # a box id is the first **bold** token of the box line
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def filed_path(flags, rid):
    return os.path.join(flags, "filing-done", rid + ".FILED")


def is_filed(flags, rid):
    return os.path.exists(filed_path(flags, rid))


def write_filed(flags, rid, summary, record):
    """Atomic, idempotent. -> True when THIS call filed the row, False when FILED already existed (no-op)."""
    done = os.path.join(flags, "filing-done")
    os.makedirs(done, exist_ok=True)
    if is_filed(flags, rid):
        return False
    import uuid
    uid = f"{os.getpid()}.{uuid.uuid4().hex[:8]}"
    vtmp, ftmp = os.path.join(done, f".{rid}.verdict.{uid}.tmp"), os.path.join(done, f".{rid}.FILED.{uid}.tmp")
    claim = filed_path(flags, rid) + ".claim"
    try:  # a crashed winner's claim must not block forever
        import time
        if time.time() - os.path.getmtime(claim) > 300:
            os.unlink(claim)
    except OSError:
        pass
    try:
        with open(ftmp, "w") as fh:
            fh.write(summary.rstrip("\n") + "\n")
            fh.flush(); os.fsync(fh.fileno())
        try:  # the claim is held for the whole publish: one holder at a time, FILED appears last, whole
            os.link(ftmp, claim)
        except FileExistsError:
            return False
        try:
            if is_filed(flags, rid):  # lost the race to a filer that finished between our first check and our claim
                return False
            with open(vtmp, "w") as fh:
                json.dump(record, fh, indent=1, sort_keys=True)
                fh.flush(); os.fsync(fh.fileno())
            os.replace(vtmp, os.path.join(done, rid + ".verdict.json"))
            try:
                os.link(ftmp, filed_path(flags, rid))
            except FileExistsError:
                return False
        finally:
            try:
                os.unlink(claim)
            except OSError:
                pass
        return True
    finally:
        for t in (vtmp, ftmp):
            try:
                os.unlink(t)
            except OSError:
                pass


def mention(text, rid=None, lineage=None):
    """Row id (exact) or lineage (bare or with an -rN attempt suffix) named in `text`. -> matched string or None."""
    if rid and re.search(r"(?<![\w-])" + re.escape(rid) + r"(?![\w-])", text):
        return rid
    if lineage and re.search(r"(?<![\w-])" + re.escape(lineage) + r"(?:-r\d+)?(?![\w-])", text):
        return lineage
    return None


def git(repo, *args, timeout=120):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr.strip()


def fetch_origin(repo):
    try:
        git(repo, "fetch", "-q", "origin", "main", timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        pass


def verify_receipt(repo, receipt, rid, lineage, ref="origin/main", fetch=True):
    """`<commit>:<handoff>#<BOX-ID>` -> (ok, info dict | error str). The commit must (1) be an ancestor of origin/main,
    (2) touch the named box line in the handoff, (3) leave a box line that mentions the row id or its lineage."""
    m = re.fullmatch(r"([0-9a-fA-F]{7,40}):([^#]+)#(\S+)", receipt or "")
    if not m:
        return False, "receipt must look like <commit>:<handoff.md>#<BOX-ID>"
    sha, handoff, box = m.groups()
    if ".." in handoff.split("/") or os.path.isabs(handoff) or not handoff.endswith(".md"):
        return False, "handoff must be a repo-relative .md path"
    if fetch:
        fetch_origin(repo)
    rc, full, err = git(repo, "rev-parse", "--verify", "-q", sha + "^{commit}")
    if rc:
        return False, f"commit {sha} not found"
    full = full.strip()
    if git(repo, "merge-base", "--is-ancestor", full, ref)[0] != 0:
        return False, f"commit {full[:12]} is not on {ref}"
    handoff = handoff_ref.repo_path(handoff)
    rc, diff, err = git(repo, "show", "-U0", "--format=", full, "--", handoff)
    if rc or not diff.strip():
        return False, f"commit {full[:12]} does not touch {handoff}"
    boxre = re.compile(r"(?<![\w.-])" + re.escape(box) + r"(?![\w.-])")
    changed = [ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++") and boxre.search(ln)]
    changed = [ln for ln in changed if BOX_LINE.match(ln)]
    if not changed:
        return False, f"commit {full[:12]} does not touch box {box} in {handoff}"
    for ln in changed:
        hit = mention(ln, rid, lineage)
        if hit:
            return True, {"commit": full, "handoff": handoff, "box": box, "box_line": ln.strip()[:600], "matched": hit}
    return False, f"box {box} line at {full[:12]} mentions neither {rid} nor lineage {lineage}"


def load_all_manifests(flags):
    """id -> (path, manifest) over ready/, ready/*/ and ready/.withdrawn/ (a withdrawn attempt is still an attempt)."""
    out = {}
    pats = ("ready/*.json", "ready/*/*.json", "ready/.withdrawn/*.json")
    for pat in pats:
        for p in sorted(glob.glob(os.path.join(flags, pat))):
            if p.endswith((".pending.json", ".done.json")):
                continue
            try:
                with open(p) as fh:
                    d = json.load(fh)
            except (OSError, ValueError):
                continue
            if isinstance(d, dict) and isinstance(d.get("id"), str):
                out.setdefault(d["id"], (p, d))
    return out


def group_of(rid, m):
    """The attempt family: the manifest's explicit `lineage`, else the id with its -rN/-date/-vN suffixes stripped. Parallel arms
    (…-r3-dense vs …-r3-pca) keep their arm name, so they are different families and never supersede one another."""
    import rowflow as rf
    return str((m or {}).get("lineage") or "").split(" ")[0] or rf.id_stem(rid)


def supersedes_ids(m, known):
    """Row ids a manifest names in `supersedes` (str, list, or an id followed by free text) that exist in `known`."""
    sup = (m or {}).get("supersedes")
    vals = sup if isinstance(sup, list) else [sup]
    out = set()
    for v in vals:
        for t in TOKEN.findall(str(v or "")):
            if t in known:
                out.add(t)
    return out


def attempt_key(rid, m):
    mm = re.search(r"-r(\d+)(?:[-_]|$)", rid)
    return (int(mm.group(1)) if mm else 0, str((m or {}).get("published_at") or ""), rid)


# ---------------------------------------------------------------- the end-record / manifest readers (pipeline audit 2026-11-10 #7)
def load_manifest(flags, rid):
    # ready/.withdrawn/ too: glob's * skips dot-dirs, and a superseded predecessor must stay fileable (2026-11-05)
    for p in ([os.path.join(flags, "ready", rid + ".json")] + sorted(glob.glob(os.path.join(flags, "ready", "*", rid + ".json")))
              + [os.path.join(flags, "ready", ".withdrawn", rid + ".json")]):
        if os.path.isfile(p):
            with open(p) as fh:
                return p, json.load(fh)
    # A complete-in-smoke row is deliberately removed from READY. Accept its
    # archived manifest only with the matching completed-smoke receipt and
    # terminal grant, never an unpublished/failed qualification manifest.
    archive = os.path.join(flags, "dryrun", rid, "completed-manifest.json")
    receipt = os.path.join(flags, "dryrun", rid, "PASS.json")
    complete = os.path.join(flags, "grants", rid + ".complete")
    try:
        with open(archive) as fh:
            m = json.load(fh)
        with open(receipt) as fh:
            p = json.load(fh)
        if ((os.path.isfile(complete) or smoke_complete_end(flags, rid)) and isinstance(m, dict) and isinstance(p, dict)
                and m.get("schema") == "epyc.row.v3" and m.get("id") == rid
                and p.get("id") == rid and p.get("job_complete") is True
                and re.fullmatch(r"[0-9a-f]{64}", str(p.get("launcher_sha256") or ""))
                and re.fullmatch(r"[0-9a-f]{64}", str(p.get("engine_sha256") or ""))
                and (m.get("launcher") or {}).get("sha256") == p["launcher_sha256"]
                and (m.get("engine") or {}).get("sha256") == p["engine_sha256"]
                and m.get("result_format") == p.get("result_format")):
            return archive, m
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None, None


def smoke_complete_end(flags, rid):
    """DEPRECATED (pipeline audit 2026-11-10 #7): read-only fallback for rows already on disk. publish_row.file_if_complete
    writes grants/<id>.ended + .complete (the engine's one end record), so a new row never needs this; it stays only for a
    smoke-completed row whose grants/ copy is missing. A dry-run smoke that completed the WHOLE job (publish_row.file_if_complete) leaves
    dryrun/<id>/{complete,ended,completed-manifest.json,completed-smoke-filing.json} and a PASS.json with
    job_complete=true. When the grants/<id>.ended copy is missing, dryrun/<id>/ended IS the end record.
    A failed smoke (no complete / no job_complete) or a smoke still in flight (no ended) never qualifies."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", str(rid)):
        return None
    dd = os.path.join(flags, "dryrun", rid)
    if not all(os.path.isfile(os.path.join(dd, n)) for n in
               ("complete", "ended", "completed-manifest.json", "completed-smoke-filing.json", "PASS.json")):
        return None
    try:
        with open(os.path.join(dd, "PASS.json")) as fh:
            p = json.load(fh)
        with open(os.path.join(dd, "completed-smoke-filing.json")) as fh:
            r = json.load(fh)
        with open(os.path.join(dd, "ended"), errors="replace") as fh:
            line = fh.readline()
    except (OSError, ValueError):
        return None
    if not (isinstance(p, dict) and p.get("id") == rid and p.get("job_complete") is True
            and isinstance(r, dict) and r.get("id") == rid and re.search(r"\brc=0\b", line)):
        return None
    return os.path.join(dd, "ended")


def end_source(path):
    """'smoke-complete' when the end record came from dryrun/<id>/ended, else 'grant'."""
    return "smoke-complete" if path and os.path.basename(os.path.dirname(os.path.dirname(path))) == "dryrun" else "grant"


def _head1(path):
    try:
        with open(path, errors="replace") as fh:
            return fh.readline().strip()
    except OSError:
        return ""


def capcut_pending(flags, rid):
    """D9 (operator "Requeue same id"): grants/<id>.ended is the engine's hard-end kill at the keeper's OWN drain cap
    (rc=75 reason=hard-end, grant cap-stamped in grants/.capcut/stamps/<id>.cap with end == cap). The keeper requeues it
    under the same id next tick, so filing must not file it. Mirrors rowflow.capcut_pending."""
    g = os.path.join(flags, "grants")
    if os.path.exists(os.path.join(g, rid + ".complete")):
        return False
    h = _head1(os.path.join(g, rid + ".ended"))
    if not (re.search(r"(^|\s)rc=75(\s|$)", h) and re.search(r"(^|\s)reason=hard-end(\s|$)", h)):
        return False
    st = _head1(os.path.join(g, ".capcut", "stamps", rid + ".cap"))
    se, ge = re.search(r"\bend=(\S+)", st), re.search(r"\bend=(\S+)", _head1(os.path.join(g, rid + ".grant")))
    return bool(re.search(r"\bcap=\d+", st) and se and ge and se.group(1) == ge.group(1))


def load_end(flags, rid):
    # An existing grants/<id>.ended|.complete always takes precedence over the smoke-complete fallback.
    if capcut_pending(flags, rid):   # D9: not an end - the keeper requeues it under the same id; nothing to file
        return None, None, ""
    for suf in (".ended", ".complete"):
        p = os.path.join(flags, "grants", rid + suf)
        if os.path.isfile(p):
            with open(p, errors="replace") as fh:
                line = fh.readline().strip()
            m = re.search(r"\brc=(\d+)", line)
            return p, (int(m.group(1)) if m else (0 if suf == ".complete" else None)), line
    p = smoke_complete_end(flags, rid)
    if p:
        with open(p, errors="replace") as fh:
            line = fh.readline().strip()
        return p, 0, line
    return None, None, ""


def run_reclaim(argv):
    """Call reclaim_row.main(argv); any exception or non-zero exit prints RECLAIM-ERROR, never raises."""
    try:
        import reclaim_row
        code = reclaim_row.main(argv)
        if code:
            print(f"RECLAIM-ERROR {argv[0]}: reclaim_row exit {code}")
        return code
    except BaseException as e:  # noqa: BLE001 — SystemExit from argparse too
        print(f"RECLAIM-ERROR {argv[0]}: {type(e).__name__}: {e}")
        return -1


def smoke_complete_ids(flags):
    """DEPRECATED fallback (see smoke_complete_end): smoke-completed rows whose end record is dryrun/<id>/ended."""
    out = []
    for d in glob.glob(os.path.join(flags, "dryrun", "*", "completed-smoke-filing.json")):
        rid = os.path.basename(os.path.dirname(d))
        ep = smoke_complete_end(flags, rid)
        if ep:
            out.append((rid, ep))
    return out


def ended_unfiled(flags):
    """ids with grants/<id>.ended|.complete (or the deprecated smoke-complete fallback) and no FILED."""
    ids = set()
    for suf in (".ended", ".complete"):
        for p in glob.glob(os.path.join(flags, "grants", "*" + suf)):
            ids.add(os.path.basename(p)[:-len(suf)])
    ids.update(rid for rid, _ in smoke_complete_ids(flags))
    return sorted(i for i in ids if not is_filed(flags, i) and not i.startswith(".") and not capcut_pending(flags, i))


def _end_info(flags, rid):
    return load_end(flags, rid)


def file_terminal(flags, rid, verdict, *, by, note="", superseded_by=None, answer=None, reclaim=True,
                  no_reclaim_globs=(), dry_run=False, log=print):
    """FILE rid as SUPERSEDED or WITHDRAWN. -> 'FILED' | 'NOOP' (already filed) | 'SKIP:<why>'."""
    verdict = verdict.upper()
    assert verdict in TERMINAL_VERDICTS
    if is_filed(flags, rid):
        return "NOOP"
    mp, m = load_manifest(flags, rid)
    ep, rc, endline = load_end(flags, rid)
    if not m or ep is None:
        return "SKIP:no manifest or end record"
    if dry_run:
        log(f"WOULD-FILE {rid}: {verdict}" + (f" SUPERSEDED-BY {superseded_by}" if superseded_by else ""))
        return "FILED"
    rec = {"$schema": "epyc.filed.verdict.v1", "id": rid, "row": rid, "owner": str(m.get("owner") or "?"), "filed_at": now_iso(),
           "at": now_iso(), "outcome_class": "NO-RESULT", "phase": "filing", "compute_burned": rc == 0, "root_cause_family": None,
           "verdict": {"status": "filed", "kind": verdict.lower(), "result": verdict, "superseded_by": superseded_by},
           "row_verdict": verdict, "superseded_by": superseded_by, "answer": answer, "rc": rc, "end_line": endline,
           "end_record": ep, "source": end_source(ep), "handoff_task": m.get("handoff_task"), "manifest": mp, "filed_by": by, "reason": note, "machine_checkable": False}
    summary = f"FILED {rid}: {verdict}" + (f" SUPERSEDED-BY {superseded_by}" if superseded_by else "") + f" rc={rc} by={by}" + (" source=smoke-complete" if end_source(ep) == "smoke-complete" else "") + (f" ({note})" if note else "")
    if not write_filed(flags, rid, summary, rec):
        return "NOOP"
    log(summary)
    pinned = next((g for g in no_reclaim_globs if fnmatch.fnmatch(rid, g)), None)
    if reclaim and pinned:
        log(f"RECLAIM-SKIPPED-SHARED {rid}: operator-named shared scratch ({pinned}); filed without reclaim")
    elif reclaim:
        run_reclaim([rid, "--flags", flags, "--apply", "--pre-filed"])
    return "FILED"


def file_legacy_no_manifest(flags, rid, verdict, *, owner, by, note="", superseded_by=None, answer=None, dry_run=False, log=print):
    """RTG-22 (operator 2026-11-09): close a LEGACY row that never had an epyc.row.v3 manifest, from its .ended record alone.

    Explicit opt-in only (file_result --no-manifest). -> 'FILED' | 'NOOP' (already FILED) | 'REFUSED:<why>'.
    Refuses when a manifest exists for rid (use the normal path), when there is no owner or no .ended/.complete record.
    verdict: SUPERSEDED|WITHDRAWN (no note needed) or pass|fail|inconclusive (non-empty `note` required; `pass` needs end rc==0).
    The record carries manifest=null, legacy_no_manifest=true, outcome_class LEGACY-NO-MANIFEST. science_scoreboard reads the
    FILED *text* (first line) and the .verdict.json it parses: credit needs a SCIENCE/PARTIAL/DIAGNOSTIC class with a native
    sha (absent here), and the literal token FAILED-RUN in the FILED text can DEBIT the owner via legacy_failed, so that token
    is scrubbed from the note/summary. Never reclaims."""
    if is_filed(flags, rid):
        return "NOOP"
    if not str(owner or "").strip():
        return "REFUSED:--owner is required with --no-manifest"
    mp, m = load_manifest(flags, rid)
    if m:
        return f"REFUSED:a manifest exists ({mp}); --no-manifest is only for rows that never had one"
    ep, rc, endline = load_end(flags, rid)
    if ep is None:
        return "REFUSED:no grants/<id>.ended|.complete end record"
    v = str(verdict)
    v = v.upper() if v.upper() in TERMINAL_VERDICTS else v.lower()
    if v not in TERMINAL_VERDICTS + ("pass", "fail", "inconclusive"):
        return f"REFUSED:bad verdict {verdict!r}"
    note = str(note or "").replace("FAILED-RUN", "failed run")
    if v in ("pass", "fail", "inconclusive") and not note.strip():
        return f"REFUSED:verdict {v} needs a non-empty rationale (--verdict-json)"
    if v == "pass" and rc != 0:
        return f"REFUSED:pass with end rc={rc} (pass needs rc=0)"
    if dry_run:
        log(f"WOULD-FILE {rid}: {v} legacy-no-manifest owner={owner}")
        return "WOULD-FILE"
    rec = {"$schema": "epyc.filed.verdict.v1", "id": rid, "row": rid, "owner": str(owner), "filed_at": now_iso(), "at": now_iso(),
           "outcome_class": "LEGACY-NO-MANIFEST", "phase": "filing", "compute_burned": rc == 0, "root_cause_family": None,
           "verdict": {"status": "filed", "kind": v.lower() if v in TERMINAL_VERDICTS else "legacy", "result": v,
                       "superseded_by": superseded_by},
           "row_verdict": v, "superseded_by": superseded_by, "answer": answer, "rc": rc, "end_line": endline,
           "end_record": ep, "source": end_source(ep), "handoff_task": None, "manifest": None, "legacy_no_manifest": True, "filed_by": by, "reason": note,
           "machine_checkable": False}
    summary = (f"FILED {rid}: {v}" + (f" SUPERSEDED-BY {superseded_by}" if superseded_by else "")
               + f" rc={rc} legacy-no-manifest owner={owner} by={by}" + (f" ({note})" if note else ""))
    if not write_filed(flags, rid, summary, rec):
        return "NOOP"
    log(summary)
    return "FILED"


def successor_of(rid, mans, wd, new_id=None, explicit=()):
    """The LATER attempt that supersedes `rid`, or None: a non-withdrawn row that names rid in `supersedes`, or one in rid's
    attempt family with a higher attempt key. `explicit` = ((glob, successor-id), ...) operator/coordinator-named pairs."""
    m = mans[rid][1]
    for g, succ in explicit:
        if fnmatch.fnmatch(rid, g) and succ != rid:
            return succ
    fam = group_of(rid, m)
    best = None
    for o, (op, om) in mans.items():
        if o == rid or op.startswith(wd) or (new_id is not None and o != new_id):
            continue
        if rid in supersedes_ids(om, mans) or (group_of(o, om) == fam and attempt_key(o, om) > attempt_key(rid, m)):
            if best is None or attempt_key(o, om) > attempt_key(best, mans[best][1]):
                best = o
    return best


def _names_as_superseded(mans, succ, rid):
    """True when the successor's manifest lists rid in its `supersedes` (a list, or one id)."""
    named = (mans.get(succ, (None, {}))[1] or {}).get("supersedes") or []
    return rid in ([named] if isinstance(named, str) else named)


def supersede_lineage(flags, new_id=None, *, by="filing.supersede", reclaim=True, no_reclaim_globs=(), explicit=(), dry_run=False, log=print):
    """Publish-time (new_id given): every ended-unfiled attempt that new_id supersedes (named in its `supersedes`, or an earlier
    attempt of the same family, unless that attempt ended complete and is not named) -> SUPERSEDED-BY new_id. Backfill (new_id None): every ended-unfiled row that has a LATER
    attempt -> SUPERSEDED-BY that attempt. Ended-unfiled rows in ready/.withdrawn -> WITHDRAWN. A different family is never touched.
    -> {'superseded': [...], 'withdrawn': [...], 'noop': [...], 'skipped': [...]}"""
    mans = load_all_manifests(flags)
    rep = {"superseded": [], "withdrawn": [], "noop": [], "skipped": []}
    wd = os.path.join(flags, "ready", ".withdrawn") + os.sep
    for rid in ended_unfiled(flags):
        if rid not in mans:
            continue
        path, m = mans[rid]
        pick = next((sc for g, sc in explicit if fnmatch.fnmatch(rid, g) and sc != rid), None)
        if path.startswith(wd) and not pick:
            reason = _end_info(flags, rid)[2]
            mm = re.search(r"reason=superseded-by:(\S+)", reason)
            if mm:   # rowflow.withdraw recorded WHY: a predecessor withdrawn by a successor's publish is SUPERSEDED-BY it
                r = file_terminal(flags, rid, "SUPERSEDED", by=by, superseded_by=mm.group(1), note="withdrawn by successor publish",
                                  reclaim=reclaim, no_reclaim_globs=no_reclaim_globs, dry_run=dry_run, log=log)
                (rep["superseded"] if r == "FILED" else rep["noop" if r == "NOOP" else "skipped"]).append(rid)
                continue
            r = file_terminal(flags, rid, "WITHDRAWN", by=by, note="manifest in ready/.withdrawn", reclaim=reclaim,
                              no_reclaim_globs=no_reclaim_globs, dry_run=dry_run, log=log)
            (rep["withdrawn"] if r == "FILED" else rep["noop" if r == "NOOP" else "skipped"]).append(rid)
            continue
        succ = pick or successor_of(rid, mans, wd, new_id, explicit)
        if not succ:
            continue
        if not pick and os.path.exists(os.path.join(flags, "grants", rid + ".complete")) and not _names_as_superseded(mans, succ, rid):
            rep["skipped"].append(rid)   # a complete result is its owner's to file; only an explicit supersedes retires it
            continue
        r = file_terminal(flags, rid, "SUPERSEDED", by=by, superseded_by=succ, note=f"family {group_of(rid, m)}",
                          reclaim=reclaim, no_reclaim_globs=no_reclaim_globs, dry_run=dry_run, log=log)
        (rep["superseded"] if r == "FILED" else rep["noop" if r == "NOOP" else "skipped"]).append(rid)
    return rep


def supersede_on_publish(flags, new_id, log=print):
    """Hook for publish_row: never raises (a publish must not fail because filing the predecessor did)."""
    try:
        globs = read_no_reclaim(flags)
        rep = supersede_lineage(flags, new_id, no_reclaim_globs=globs, log=log)
        if rep["superseded"] or rep["withdrawn"]:
            log(f"SUPERSEDE-FILED {new_id}: superseded={rep['superseded']} withdrawn={rep['withdrawn']}")
        return rep
    except BaseException as e:  # noqa: BLE001
        log(f"WARN supersede_on_publish {new_id}: {type(e).__name__}: {e}")
        return None


def read_no_reclaim(flags):
    try:
        with open(os.path.join(flags, "filing-no-reclaim.globs")) as fh:
            return [g for g in (ln.split("#", 1)[0].strip() for ln in fh) if g]
    except OSError:
        return []


def _tree_entry(repo, commit, path, cache):
    """-> (mode, blob sha) of `path` in `commit`'s tree, or (None, None) when absent there."""
    if path not in cache:
        rc, out, _e = git(repo, "ls-tree", commit, "--", path)
        meta = out.split("\t")[0].split() if rc == 0 and out.strip() else []
        cache[path] = (meta[0], meta[2]) if len(meta) >= 3 else (None, None)
    return cache[path]


def scope_patterns(repo, m, handoff):
    """The row's filing scope as repo-relative globs. A declared `scope` (list of globs, or one str) wins; otherwise the default
    is the row's own output/scratch dirs (scratch_root, workdir, output_dir, result_path's dir) where they sit inside the repo,
    plus the handoff named in the receipt. The receipt's handoff is always in scope (the box tick itself touches it)."""
    pats = []
    declared = (m or {}).get("scope")
    if isinstance(declared, str):
        declared = [declared]
    if isinstance(declared, list) and declared:
        pats += [str(x) for x in declared]
    else:
        root = os.path.realpath(repo)
        for k in ("scratch_root", "workdir", "output_dir", "result_path"):
            v = (m or {}).get(k)
            if not isinstance(v, str) or not os.path.isabs(v):
                continue
            d = os.path.dirname(v) if k == "result_path" else v
            rel = os.path.relpath(os.path.realpath(d), root)
            if rel != "." and not rel.startswith(".."):
                pats.append(rel.rstrip("/") + "/**")
    pats.append(handoff)
    return pats


def _in_scope(path, pats):
    import fnmatch
    for p in pats:
        if p.startswith("./"):
            p = p[2:]
        if p.endswith("/**") or p.endswith("/"):
            base = p[:-3] if p.endswith("/**") else p.rstrip("/")
            if path == base or path.startswith(base + "/"):
                return True
        elif fnmatch.fnmatchcase(path, p):
            return True
    return False


def check_scope(repo, commit, m, handoff):
    """CHURN-CONT-SCOPE: None when every path the receipt commit changes lies inside the row's scope, else a refusal string.
    Refuses `..`/absolute paths, gitlinks (mode 160000), a path under a symlinked directory, and a symlink whose target
    resolves outside the scope."""
    rc, out, err = git(repo, "diff-tree", "-r", "-m", "--first-parent", "--no-renames", "--root", "--no-commit-id", "-z", "--raw", commit)
    if rc:
        return f"scope check could not read the diff of {commit[:12]}: {err[:200]}"
    toks = [t for t in out.split("\0") if t != ""]
    entries = []
    for i in range(0, len(toks) - 1, 2):
        meta = toks[i].lstrip(":").split()
        if len(meta) < 5:
            return f"scope check: unparseable diff entry {toks[i]!r}"
        entries.append((meta[0], meta[1], toks[i + 1]))
    pats = scope_patterns(repo, m, handoff)
    cache, bad = {}, []
    for old_mode, new_mode, path in entries:
        norm = os.path.normpath(path).replace(os.sep, "/")
        if os.path.isabs(path) or ".." in path.split("/") or norm == ".." or norm.startswith("../"):
            bad.append(f"{path} (path traversal)")
            continue
        if "160000" in (old_mode, new_mode):
            bad.append(f"{path} (gitlink/submodule)")
            continue
        parts = norm.split("/")
        link_parent = next(("/".join(parts[:j]) for j in range(1, len(parts))
                            if _tree_entry(repo, commit, "/".join(parts[:j]), cache)[0] == "120000"), None)
        if link_parent:
            bad.append(f"{path} (under symlinked directory {link_parent})")
            continue
        if "120000" in (old_mode, new_mode):
            mode, blob = _tree_entry(repo, commit, norm, cache)
            if mode == "120000":
                _rc, target, _e = git(repo, "cat-file", "blob", blob)
                target = target.strip()
                tnorm = os.path.normpath(os.path.join(os.path.dirname(norm), target)).replace(os.sep, "/")
                if os.path.isabs(target) or tnorm == ".." or tnorm.startswith("../") or not _in_scope(tnorm, pats):
                    bad.append(f"{path} (symlink to {target[:80]!r} escapes scope)")
                    continue
        if not _in_scope(norm, pats):
            bad.append(f"{path} (outside scope)")
    if bad:
        return (f"commit {commit[:12]} changes paths outside the row's scope {pats}: " + "; ".join(bad[:10])
                + (f" (+{len(bad) - 10} more)" if len(bad) > 10 else ""))
    return None


def file_receipt(flags, rid, receipt, *, repo, verdict="RECEIPT", answer=None, by="file_result --receipt", reclaim=True,
                 fetch=True, log=print):
    """Path 1. -> (code, msg). code: 0 filed, 1 noop (already FILED), 2 refused."""
    if is_filed(flags, rid):
        return 1, f"NOOP {rid}: already FILED"
    mp, m = load_manifest(flags, rid)
    ep, rc, endline = load_end(flags, rid)
    if not m or ep is None:
        return 2, f"REFUSED {rid}: no manifest or no end record"
    mans = load_all_manifests(flags)
    lin = group_of(rid, mans.get(rid, (None, m))[1])
    ok, info = verify_receipt(repo, receipt, rid, lin, fetch=fetch)
    if not ok:
        return 2, f"REFUSED {rid}: {info}"
    serr = check_scope(repo, info["commit"], m, info["handoff"])
    if serr:
        return 2, f"REFUSED {rid}: scope: {serr}"
    verdict = verdict.upper() if verdict.upper() in TERMINAL_VERDICTS else verdict
    rec = {"$schema": "epyc.filed.verdict.v1", "id": rid, "row": rid, "owner": str(m.get("owner") or "?"), "filed_at": now_iso(),
           "at": now_iso(), "outcome_class": "RECEIPT", "phase": "filing", "compute_burned": True, "root_cause_family": None,
           "verdict": {"status": "filed", "kind": "receipt", "result": verdict}, "row_verdict": verdict, "answer": answer,
           "rc": rc, "end_line": endline, "handoff_task": m.get("handoff_task"), "manifest": mp, "filed_by": by,
           "receipt": info, "reason": f"verdict commit {info['commit'][:12]} box {info['box']}", "machine_checkable": False}
    summary = (f"FILED {rid}: {verdict}" + (f" answer={answer}" if answer else "") + f" rc={rc} by={by} receipt={info['commit'][:12]}:"
               f"{info['handoff']}#{info['box']} box-line: {info['box_line']}")
    if not write_filed(flags, rid, summary, rec):
        return 1, f"NOOP {rid}: already FILED"
    log(summary)
    if reclaim:
        run_reclaim([rid, "--flags", flags, "--apply", "--pre-filed"])
    return 0, summary


# ------------------------------------------------------------------ janitor auto-link sweep
def _parse_log(repo, since_ts, ref="origin/main"):
    """One `git log -p -U0` pass over handoffs/: yield (sha, ts, handoff, [added box lines])."""
    p = subprocess.Popen(["git", "-C", repo, "log", ref, f"--since=@{int(since_ts)}", "--no-merges", "-p", "-U0",
                          "--format=@@C %H %ct", "--", "handoffs/"], stdout=subprocess.PIPE, text=True, errors="replace")
    sha = ts = handoff = None
    for ln in p.stdout:
        if ln.startswith("@@C "):
            _, sha, ts = ln.split()
            handoff = None
        elif ln.startswith("+++ b/"):
            handoff = ln[6:].strip()
        elif ln.startswith("+") and not ln.startswith("+++") and sha and handoff and BOX_LINE.match(ln[1:]):
            yield sha, int(ts), handoff, ln[1:].rstrip("\n")
    p.stdout.close()
    p.wait()


def box_id_of(line):
    m = BOX_ID.search(line)
    return m.group(1) if m else None


def autolink(flags, repo, *, apply=False, fetch=True, reclaim=True, no_reclaim_globs=(), log=print):
    """Zero-token janitor sweep. Files a row ONLY when exactly one (commit, handoff, box) on origin/main, committed after the
    row ended, ticks or annotates a box line naming the row id. Ambiguous matches are listed, never filed.
    -> {'filed': [...], 'ambiguous': {id: [...]}, 'none': n, 'refused': {id: why}}"""
    todo = ended_unfiled(flags)
    rep = {"filed": [], "ambiguous": {}, "none": 0, "refused": {}}
    if not todo:
        return rep
    if fetch:
        fetch_origin(repo)
    ends = {}
    for rid in todo:
        ep, _rc, _l = _end_info(flags, rid)
        if ep:
            ends[rid] = os.path.getmtime(ep)
    if not ends:
        return rep
    ids = set(ends)
    hits = {}
    for sha, ts, handoff, line in _parse_log(repo, min(ends.values()) - 3600):
        bid = box_id_of(line)
        if not bid:
            continue
        for tok in {t.rstrip(".") for t in TOKEN.findall(line)} & ids:
            if ts >= ends[tok] - 60:
                hits.setdefault(tok, set()).add((sha, handoff, bid))
    rep["none"] = len(ids - set(hits))
    for rid, hs in sorted(hits.items()):
        if len(hs) != 1:
            rep["ambiguous"][rid] = sorted(f"{s[:12]}:{h}#{b}" for s, h, b in hs)
            continue
        (sha, handoff, bid), = hs
        receipt = f"{sha}:{handoff}#{bid}"
        if not apply:
            rep["filed"].append(rid)
            log(f"WOULD-FILE {rid} <- {receipt}")
            continue
        code, msg = file_receipt(flags, rid, receipt, repo=repo, verdict="RECEIPT", by="auto_link", reclaim=reclaim, fetch=False, log=log)
        if code == 0:
            rep["filed"].append(rid)
        elif code == 2:
            rep["refused"][rid] = msg
    return rep


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="filing.py: backfill-supersede | autolink")
    ap.add_argument("cmd", choices=["backfill-supersede", "autolink"])
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--repo", default=os.path.abspath(os.path.join(HERE, "..", "..", "..")))
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-reclaim", action="store_true")
    ap.add_argument("--no-reclaim-glob", action="append", default=[])
    ap.add_argument("--supersede-to", action="append", default=[], metavar="GLOB=ID",
                    help="coordinator-named pair: ended-unfiled rows matching GLOB are SUPERSEDED-BY ID (ID must have a manifest)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    explicit = [tuple(x.split("=", 1)) for x in a.supersede_to]
    globs = list(a.no_reclaim_glob) + read_no_reclaim(a.flags)
    if a.cmd == "backfill-supersede":
        rep = supersede_lineage(a.flags, None, by="filing.backfill", reclaim=not a.no_reclaim, no_reclaim_globs=globs, explicit=explicit, dry_run=not a.apply)
        counts = {k: len(v) for k, v in rep.items()}
    else:
        rep = autolink(a.flags, a.repo, apply=a.apply, reclaim=not a.no_reclaim, no_reclaim_globs=globs)
        counts = {"filed": len(rep["filed"]), "ambiguous": len(rep["ambiguous"]), "none": rep["none"], "refused": len(rep["refused"])}
    print(("APPLIED " if a.apply else "DRY-RUN ") + a.cmd + " " + json.dumps(counts, sort_keys=True))
    if rep.get("ambiguous"):
        for k, v in rep["ambiguous"].items():
            print(f"AMBIGUOUS {k}: {' | '.join(v)}")
    if a.json:
        print(json.dumps(rep, sort_keys=True, default=list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
