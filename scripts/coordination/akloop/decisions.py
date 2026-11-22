#!/usr/bin/env python3
"""decisions.py -- AutoKernel parallel-loop P6: the decision-needed detector.

Scans pipeline state READ-ONLY and, per owner, lists the events that need an owner decision, each with a 3-option
decision package (context + options with tradeoffs, recommended first) as JSON and markdown, ready for the owner to
send through AskUserQuestion. It NEVER sends, publishes, acks, unparks or writes pipeline state; output goes to
stdout (or --out-dir files the caller names).

    decisions.py --owner autokernel [--json | --md] [--since-hours 72] [--flags DIR] [--root DIR] [--out-dir DIR]

Signals (every event carries `evidence`: file:line or record ids, never prose alone):
    gate-open / gate-unknown   box-index `· gate:` refs unresolved / naming nothing known   (handoff box file:line)
    hold-hit                   holds.yaml hold that targets the owner's sessions/handoffs/boxes (holds.yaml:line + boxes)
    refusal-cap                a row's lineage at 2 of MAX_FAILS=3 arming/launch refusals    (dryrun/<id>/FAIL-N.json)
    row-parked                 rowflow state `parked`, or a lineage already at MAX_FAILS     (dryrun/<id>/FAIL-N.json)
    futility                   an ended row whose RESULT verdict is FUTILITY* with no successor row and no filed verdict
                               (RESULT.json; filing-done/<id>.FILED|.verdict.json suppresses it)
    supersede-dead-end         a row superseded-by a successor that never existed / was withdrawn (grants/<id>.ended)
    smoke-fail-repeat          >=2 dry-run (smoke) FAIL records in one lineage, no PASS since   (dryrun/<id>/FAIL-N.json)

Owner resolution: rows by manifest `owner` (id, or a registry session slug whose handoff the owner owns) or by
`handoff_task` file; boxes by the owner's `Owned handoffs:` line in agents/<owner>.md (box `owner` also matches).
Exit 0 always (a detector reports, it does not gate).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
COORD = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(COORD))
DEFAULT_FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
HUB_VIEW = "/mnt/raid0/llm/views/epyc-root-main"
SCHEMA = "epyc.akloop.decisions.v1"
MAX_FAILS = 3                      # rowflow.MAX_FAILS: lineage parks at this many arming/launch failures
ARM_KINDS = ("arm", "launch")
KINDS = ("gate-unknown", "gate-open", "hold-hit", "row-parked", "refusal-cap", "futility", "supersede-dead-end",
         "smoke-fail-repeat")
_STEM = re.compile(r"(-r\d+[a-z0-9]*)?(-\d{8})?(-r\d+[a-z0-9]*)?$")
_HANDOFF_RX = re.compile(r"`?(handoffs/active/[\w.\-]+\.md)`?")


# ------------------------------------------------------------------ small helpers
def load_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def iso_epoch(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stem(rid):
    return _STEM.sub("", rid or "") or rid


def slug_of(x):
    return re.sub(r"^(handoff-|h-)", "", str(x or ""))


def eid(kind, subject):
    return kind + ":" + hashlib.sha256(f"{kind}|{subject}".encode()).hexdigest()[:10]


def ref(path, line=None, note=None, **kw):
    r = {"path": path}
    if line:
        r["line"] = line
    if note:
        r["note"] = note
    r.update(kw)
    return r


# ------------------------------------------------------------------ owner resolution
class Owner:
    def __init__(self, oid, root, flags):
        self.id, self.root, self.flags = oid, root, flags
        self.files = self._files()
        self.aliases = self._aliases()

    def _files(self):
        txt = ""
        for cand in (os.path.join(self.root, "agents", f"{self.id}.md"), os.path.join(REPO, "agents", f"{self.id}.md")):
            if os.path.isfile(cand):
                txt = open(cand, encoding="utf-8", errors="replace").read()
                break
        m = re.search(r"Owned handoffs?:(.*?)(?:\n\s*\n|\n- (?!\s)(?=[A-Z])|\Z)", txt, re.S)
        block = m.group(1) if m else ""
        return sorted(set(_HANDOFF_RX.findall(block)))

    def _aliases(self):
        out = {self.id}
        reg = load_json(os.path.join(self.flags, "handoff-sessions.json")) or {}
        for slug, s in (reg.get("sessions") or {}).items():
            if isinstance(s, dict) and s.get("handoff") in self.files:
                out.add(slug_of(slug))
        return out

    def owns_row(self, man):
        if slug_of(man.get("owner")) in self.aliases:
            return True
        ht = str(man.get("handoff_task") or "").split(":")[0]
        return bool(ht) and any(f.endswith("/" + ht) for f in self.files)

    def owns_box(self, box):
        return box.get("file") in self.files or slug_of(box.get("owner")) == self.id


# ------------------------------------------------------------------ context
class Ctx:
    def __init__(self, owner, root, flags, now, since_h, boxes=None, holds=None, status_fn=None):
        self.o, self.root, self.flags, self.now = owner, root, flags, now
        self.since = now - since_h * 3600
        self._boxes, self._holds, self._status_fn = boxes, holds, status_fn
        self._rows = None

    def manifests(self):
        """{id: manifest} for this owner's rows: live ready/ plus ready/.withdrawn (marked `_withdrawn`)."""
        if self._rows is None:
            self._rows = {}
            for sub, wd in (("ready", False), ("ready/.withdrawn", True)):
                for p in glob.glob(os.path.join(self.flags, sub, "*.json")):
                    d = load_json(p)
                    if isinstance(d, dict) and d.get("id") and self.o.owns_row(d):
                        d["_withdrawn"] = wd
                        self._rows.setdefault(d["id"], d)
        return self._rows

    def all_manifest_ids(self):
        ids = set()
        for sub in ("ready", "ready/.withdrawn"):
            ids |= {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(self.flags, sub, "*.json"))}
        return ids

    def ended(self, rid):
        """(text, epoch) of grants/<id>.ended, else None."""
        p = os.path.join(self.flags, "grants", rid + ".ended")
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
            m = re.search(r"\bat=(\S+)", txt) or re.search(r"time=(\S+)", txt)
            return txt, (iso_epoch(m.group(1)) if m else None) or os.path.getmtime(p)
        except OSError:
            return None

    def filed(self, rid):
        """True when the row's verdict is already filed (filing-done/<id>.FILED or .verdict.json)."""
        fd = os.path.join(self.flags, "filing-done")
        return any(os.path.exists(os.path.join(fd, rid + ext)) for ext in (".FILED", ".verdict.json"))

    def fails(self, rid):
        out = []
        for p in sorted(glob.glob(os.path.join(self.flags, "dryrun", rid, "FAIL-*.json"))):
            d = load_json(p)
            if isinstance(d, dict):
                d["_path"] = p
                out.append(d)
        return out

    def status(self, rid):
        if self._status_fn:
            return self._status_fn(rid)
        try:
            sys.path.insert(0, os.path.join(COORD, "rowflow"))
            import rowflow as R
            return R.status(self.flags, rid, self.manifests_full())
        except Exception as e:  # noqa: BLE001  -- degrade to file counting, say so
            return {"id": rid, "state": "unknown", "reason": f"rowflow unavailable: {type(e).__name__}"}

    def manifests_full(self):
        if not hasattr(self, "_full"):
            try:
                import rowflow as R
                self._full = R.rows(self.flags)
            except Exception:  # noqa: BLE001
                self._full = self.manifests()
        return self._full

    def boxes(self):
        if self._boxes is None:
            sys.path.insert(0, os.path.join(REPO, "scripts", "handoffs"))
            import box_index as B
            self._boxes = (B.load(self.root) or {}).get("boxes") or {}
        return self._boxes

    def holds(self):
        if self._holds is None:
            sys.path.insert(0, COORD)
            import holds as H
            self._holds = H.load(self.root) or []
        return self._holds


# ------------------------------------------------------------------ collectors: each returns [event]
def ev(kind, owner, subject, summary, evidence, **facts):
    return {"event_id": eid(kind, subject), "kind": kind, "owner": owner, "subject": subject, "summary": summary,
            "evidence": evidence, "facts": facts}


def c_gates(c):
    out = []
    for key, b in sorted(c.boxes().items()):
        if b.get("state") == "done" or not c.o.owns_box(b):
            continue
        loc = ref(b["file"], b.get("line"), note=(b.get("text") or "")[:120], box=key)
        if b.get("gate_unknown"):
            out.append(ev("gate-unknown", c.o.id, key, f"box {key} gates on {len(b['gate_unknown'])} ref(s) that name nothing known",
                          [loc], gate=b.get("gate"), unknown=b["gate_unknown"]))
        elif b.get("gate_open"):
            out.append(ev("gate-open", c.o.id, key, f"box {key} is BLOCKED by unresolved gate(s) {b['gate']}",
                          [loc], gate=b.get("gate")))
    return out


def _hold_line(root, hid):
    p = os.path.join(root, "handoffs", "active", "holds.yaml")
    try:
        for i, l in enumerate(open(p, encoding="utf-8"), 1):
            if re.match(rf"^-\s+id:\s*['\"]?{re.escape(hid)}['\"]?\s*$", l):
                return i
    except OSError:
        pass
    return None


def c_holds(c):
    out = []
    boxes = c.boxes()
    for h in c.holds():
        hid = h["id"]
        sess = {slug_of(s) for s in h.get("sessions") or []}
        by_session = bool(sess & c.o.aliases)
        launch_only = h.get("launch_only") is True   # gates loop launch only; its handoffs are provenance, not targets
        by_file = not launch_only and any(f.endswith("/" + x) or f == x for f in c.o.files for x in (h.get("handoffs") or []))
        held = [(k, b) for k, b in sorted(boxes.items())
                if hid in (b.get("holds") or []) and b.get("state") != "done" and c.o.owns_box(b)]
        if not (by_session or by_file or held):
            continue
        evid = [ref("handoffs/active/holds.yaml", _hold_line(c.root, hid), note=str(h.get("reason") or "")[:140], hold=hid,
                    scope=h.get("scope"), since=str(h.get("since") or ""))]
        evid += [ref(b["file"], b.get("line"), box=k) for k, b in held[:6]]
        out.append(ev("hold-hit", c.o.id, hid, (f"hold `{hid}` (loop-launch, launch-only) gates launching/relaunching the owner's loop sessions; "
                       f"{len(held)} open box(es) held" if launch_only else
                       f"hold `{hid}` ({h.get('scope')}) stops {len(held)} open box(es) / the owner's sessions"),
                      evid, hold=hid, scope=h.get("scope"), held_boxes=len(held), reason=h.get("reason"), since=str(h.get("since") or ""),
                      launch_only=launch_only))
    return out


def c_rows(c):
    """refusal-cap, row-parked, smoke-fail-repeat: per lineage, from dryrun FAIL records + rowflow's own row state."""
    out, seen_lin = [], set()
    for rid, man in sorted(c.manifests().items()):
        if man["_withdrawn"] or c.ended(rid) or os.path.exists(os.path.join(c.flags, "filing-done", rid + ".FILED")):
            continue
        st = c.status(rid)
        fails = c.fails(rid)
        arm = [f for f in fails if f.get("kind") in ARM_KINDS]
        smoke = [f for f in fails if f.get("kind") not in ARM_KINDS]
        lin = st.get("lineage") or stem(rid)
        lf = int(st.get("lineage_fails") or 0)
        evid = [ref(os.path.relpath(f["_path"], c.flags), record=f"{rid}@{f.get('at')}", note=str(f.get("fix_task") or f.get("reason") or "")[:160])
                for f in fails[-3:]]
        if st.get("state") == "parked" or lf >= MAX_FAILS:
            out.append(ev("row-parked", c.o.id, lin, f"row `{rid}` (lineage {lin}) is PARKED: {st.get('reason') or lf} ",
                          evid or [ref(f"ready/{rid}.json", record=rid)], row=rid, lineage=lin, lineage_fails=lf, state=st.get("state"),
                          reason=st.get("reason"), fix_task=(fails[-1].get("fix_task") if fails else None)))
        elif lf == MAX_FAILS - 1 or (len(arm) >= MAX_FAILS - 1 and st.get("state") != "running"):
            out.append(ev("refusal-cap", c.o.id, lin, f"row `{rid}` (lineage {lin}) is at {lf or len(arm)} of {MAX_FAILS} refusals; the next parks it",
                          evid, row=rid, lineage=lin, lineage_fails=lf or len(arm), of=MAX_FAILS, fix_task=(arm[-1].get("fix_task") if arm else None)))
        if len(smoke) >= 2 and lin not in seen_lin:
            last = max(iso_epoch(f.get("at")) or 0 for f in smoke)
            p = load_json(os.path.join(c.flags, "dryrun", rid, "PASS.json")) or {}
            if last >= c.since and (iso_epoch(p.get("passed_at") or p.get("at")) or 0) < last:
                seen_lin.add(lin)
                out.append(ev("smoke-fail-repeat", c.o.id, lin, f"row `{rid}` smoke-failed {len(smoke)}x with no PASS since",
                              [ref(os.path.relpath(f["_path"], c.flags), record=f"{rid}@{f.get('at')}", note=str(f.get("fix_task") or "")[:160])
                               for f in smoke[-3:]], row=rid, lineage=lin, smoke_fails=len(smoke)))
    return out


def _result(c, man):
    p = str(man.get("result_path") or "")
    d = load_json(p) if p.endswith(".json") else None
    return p, d if isinstance(d, dict) else None


def c_futility(c):
    out, mans = [], c.manifests()
    for rid, man in sorted(mans.items()):
        e = c.ended(rid)
        if not e or e[1] < c.since:
            continue
        p, d = _result(c, man)
        verdict = str((d or {}).get("verdict") or "")
        if not verdict.upper().startswith("FUTILITY"):
            continue
        if c.filed(rid):   # AKPL-P3: historical futility already filed (runend / gate_eval) needs no decision
            continue
        succ = [o for o, m in mans.items() if o != rid and (rid in ([m["supersedes"]] if isinstance(m.get("supersedes"), str) else (m.get("supersedes") or []))
                                                              or (stem(o) == stem(rid) and str(m.get("published_at") or "") > str(man.get("published_at") or "") and not m["_withdrawn"]))]
        if succ:
            continue
        out.append(ev("futility", c.o.id, rid, f"row `{rid}` ended {iso(e[1])} with verdict {verdict} and has no successor row",
                      [ref(p, record=f"{rid}.verdict={verdict}"), ref(f"grants/{rid}.ended", note=e[0].strip().splitlines()[0][:100])],
                      row=rid, verdict=verdict, handoff_task=man.get("handoff_task")))
    return out


_SUPER_RX = re.compile(r"reason=superseded-by[:-]?([A-Za-z0-9][A-Za-z0-9._\-]*?)(?=_\(|\s|$)")


def _live_ids(c):
    return {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(c.flags, "ready", "*.json"))}


def c_supersede(c):
    """One event per DEAD chain head (not per hop). Dead = the last successor has no manifest, or was withdrawn, and
    no live ready/ row shares the lineage stem (a successor published without `supersedes` still continues it)."""
    out, mans, allids, live, done = [], c.manifests(), c.all_manifest_ids(), None, {}
    live = _live_ids(c)
    for rid in sorted(mans):
        e = c.ended(rid)
        m = _SUPER_RX.search(e[0]) if e else None
        if not m or e[1] < c.since:
            continue
        hops, seen, head = [rid], {rid}, m.group(1)
        while head and head not in seen:
            seen.add(head)
            hops.append(head)
            he = c.ended(head)
            hm = _SUPER_RX.search(he[0]) if he else None
            if not hm:
                break
            head = hm.group(1)
        head = hops[-1]
        he = c.ended(head)
        if head not in allids:
            why = "successor has no manifest at all"
        elif he and re.search(r"reason=(withdrawn|stopped)", he[0]):
            why = "chain head was withdrawn with no successor"
        else:
            continue
        if any(stem(x) in {stem(h) for h in hops} and x not in hops and not c.ended(x) for x in live):
            continue                                              # lineage continues under a later live row
        if head in done:
            continue
        done[head] = True
        out.append(ev("supersede-dead-end", c.o.id, head, f"chain ending at `{head}` has no live successor ({why})",
                      [ref(f"grants/{h}.ended", record=h) for h in hops[:-1]] + [ref(f"ready/{head}.json", record=head, note=why)],
                      chain=hops, why=why))
    return out


COLLECTORS = (c_gates, c_holds, c_rows, c_futility, c_supersede)


def detect(owner_id, root=None, flags=DEFAULT_FLAGS, now=None, since_h=72.0, boxes=None, holds=None, status_fn=None):
    root = root or (HUB_VIEW if os.path.isdir(HUB_VIEW) else REPO)
    now = now if now is not None else datetime.now(timezone.utc).timestamp()
    c = Ctx(Owner(owner_id, root, flags), root, flags, now, since_h, boxes, holds, status_fn)
    events = []
    for col in COLLECTORS:
        events += col(c)
    order = {k: i for i, k in enumerate(KINDS)}
    events.sort(key=lambda e: (order[e["kind"]], e["subject"]))
    for e in events:
        e["package"] = package(e)
    return {"schema": SCHEMA, "owner": owner_id, "as_of": iso(now), "root": root, "flags": flags, "since_hours": since_h,
            "owner_handoffs": c.o.files, "counts": {k: sum(1 for e in events if e["kind"] == k) for k in KINDS if any(e["kind"] == k for e in events)},
            "events": events, "never_sends": True}


# ------------------------------------------------------------------ decision packages
def _opt(label, desc, rec=False):
    return {"label": label + (" (Recommended)" if rec else ""), "description": desc}


def package(e):
    k, f, s = e["kind"], e["facts"], e["subject"]
    if k == "gate-unknown":
        unk = [u[:70] for u in f["unknown"][:3]]
        note = "Most of these look like prose fragments split at commas, so the fix is usually to rewrite the gate as box IDs." if any(" " in u for u in f["unknown"]) else ""
        ctx = f"Box {s} names {len(f['unknown'])} gate ref(s) the index cannot resolve, e.g. {unk}. A dead gate never opens, so the box is stuck and fails lint (g-gate-unknown). {note}"
        opts = [_opt("Repair the gate ref", "Point it at a real box ID / row; the box becomes dispatchable or correctly blocked. Costs one edit; needs you to know the intended dependency.", True),
                _opt("Drop the gate", "Remove `gate:` and let the box run now. Fast, but loses an ordering you may have wanted.") ,
                _opt("Park the box", "Hold it until the gate's meaning is clear. Safe, but the work waits.")]
    elif k == "gate-open":
        ctx = f"Box {s} is blocked by unresolved gate(s) {f['gate']}. Nothing is wrong with the box itself; the question is whether the gate is still the right order."
        opts = [_opt("Keep waiting", "The gate is a real prerequisite; keep working elsewhere. Zero cost, no progress on this box.", True),
                _opt("Pull the gate box forward", "Raise the gating box in backlog priority so this one unblocks sooner. Reorders other work."),
                _opt("Drop the gate", "Release the box now if the dependency is no longer real. Risks running before its input exists.")]
    elif k == "hold-hit":
        ctx = f"Hold `{f['hold']}` ({f['scope']}, since {f['since']}) stops {f['held_boxes']} open box(es). Reason on record: {f['reason']}"
        opts = [_opt("Keep the hold", "Nothing changes; held boxes stay out of dispatch. Right while the original reason stands.", True),
                _opt("Narrow the hold", "Release only the boxes whose reason has gone away, keep the rest. Needs a per-box call from you."),
                _opt("Release the hold", "Operator-ratified release (operator-ratify/<hold id>.json); everything it covers becomes dispatchable at once.")]
    elif k == "refusal-cap":
        ctx = f"Row {f['row']} (lineage {f['lineage']}) has been refused {f['lineage_fails']} of {f['of']} times; one more parks it. Last fix task: {f.get('fix_task')}"
        opts = [_opt("Fix the cause and republish as -rN", "Address the refusal reason, publish a successor with `supersedes`. Resets the count; costs a row-prep turn.", True),
                _opt("Let it park", "Accept the park; the lineage stops retrying. Cheapest, but the question the row asked stays unanswered."),
                _opt("Withdraw the row", "End it for good and drop its box tick. Use only if the question no longer matters.")]
    elif k == "row-parked":
        ctx = f"Row {f['row']} (lineage {f['lineage']}) is PARKED after {f['lineage_fails']} failures: {f.get('reason')}. Last fix task: {f.get('fix_task')}"
        opts = [_opt("Republish with the fix (new -rN)", "Fix the launcher/spec cause, publish a successor; a changed launcher sha earns one fresh attempt. Needs the cause understood first.", True),
                _opt("Unpark as-is", "`rowflow.py unpark <id>`: retries once without a change. Only sensible when the cause was transient (host contention, disk)."),
                _opt("Withdraw and record NO-GO", "End the lineage and file why. Frees the queue slot; gives up the measurement.")]
    elif k == "futility":
        ctx = f"Row {f['row']} ended with {f['verdict']} and no successor row exists (task {f.get('handoff_task')}). FUTILITY means the cell cannot answer its question as run."
        opts = [_opt("Close the box as futile", "File the FUTILITY verdict and stop. Spends no more compute; the lever stays unmeasured.", True),
                _opt("Publish a redesigned successor", "Change the arm/sample/pin that made it futile and republish `-rN` with `supersedes`. Costs another run window."),
                _opt("Ask the operator", "Escalate if the futility says the lever is not worth another cell. Slowest.")]
    elif k == "supersede-dead-end":
        ctx = f"Chain {' -> '.join(f['chain'])} ends dead: {f['why']}. The work the chain's first row asked for has no live row."
        opts = [_opt("Republish the head", "Publish the missing successor (id = the head, or -rN of it) so the chain has a live end. Restores the measurement.", True),
                _opt("Close the chain", "Record that the question was dropped on purpose and tick/withdraw the box. No compute."),
                _opt("Restore the original row", "Re-publish the first row unchanged if the supersede was a mistake. Re-pays its dry run.")]
    else:  # smoke-fail-repeat
        ctx = f"Row {f['row']} (lineage {f['lineage']}) failed its dry run {f['smoke_fails']}x with no PASS since. Repeating it without a change repeats the failure."
        opts = [_opt("Fix the smoke predicate or job, then republish", "Read launcher.out of the last FAIL, fix the cause, publish -rN. The usual cure.", True),
                _opt("Relax the smoke (first_progress_s / predicate)", "Only if the predicate itself is wrong; a loose smoke hides real failures later."),
                _opt("Drop the row", "Withdraw the lineage; stops burning dry-run windows on it.")]
    return {"question": f"{e['summary']}. What should {e['owner']} do?",
            "header": k.replace("-", " ")[:12], "multiSelect": False, "context": ctx, "options": opts,
            "send_via": "AskUserQuestion (owner sends; this tool never does)"}


# ------------------------------------------------------------------ rendering
def ev_str(r):
    s = r["path"] + (f":{r['line']}" if r.get("line") else "")
    return s + (f" [{r['record']}]" if r.get("record") else "") + (f" - {r['note']}" if r.get("note") else "")


def render_md(rep):
    L = [f"# Decisions needed: {rep['owner']}", "", f"As of {rep['as_of']} (window {rep['since_hours']:g} h). {len(rep['events'])} event(s): "
         + (", ".join(f"{k} {n}" for k, n in rep["counts"].items()) or "none") + ". Nothing is sent by this tool.", ""]
    for i, e in enumerate(rep["events"], 1):
        p = e["package"]
        L += [f"## {i}. {e['kind']}: {e['subject']}", f"`{e['event_id']}`", "", p["context"], "", "Evidence:"]
        L += [f"- {ev_str(r)}" for r in e["evidence"]]
        L += ["", f"Question: {p['question']}", ""]
        L += [f"{n}. **{o['label']}** - {o['description']}" for n, o in enumerate(p["options"], 1)] + [""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--root", default=None, help="epyc-root tree for handoffs/holds/agents (default: hub view, else this checkout)")
    ap.add_argument("--since-hours", type=float, default=72.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--out-dir", default=None, help="also write <owner>.decisions.json/.md here (caller-named path only)")
    a = ap.parse_args(argv)
    rep = detect(a.owner, root=a.root, flags=a.flags, since_h=a.since_hours)
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)
        open(os.path.join(a.out_dir, f"{a.owner}.decisions.json"), "w").write(json.dumps(rep, indent=1, sort_keys=True) + "\n")
        open(os.path.join(a.out_dir, f"{a.owner}.decisions.md"), "w").write(render_md(rep))
    print(json.dumps(rep, indent=1, sort_keys=True) if a.json else render_md(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
