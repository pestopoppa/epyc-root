#!/usr/bin/env python3
"""publish_row.py <spec.json> [--migrate] | publish_row.py --repair <row-id>   [--flags DIR] - the owner's ONE tool.

publish   LINT the spec, then rowflow.publish derives the rest. The lint rewrites the two defects that used to cost a dry
          run plus an agent turn (CAF-4): a result_path that is a completion marker (.complete/.ended/.done/.FILED,
          grants/, COMPLETE*/TERMINAL*) becomes the declared results file in the same run dir (result_format json ->
          RESULT.json, jsonl -> results.jsonl; no declared format -> refused in one line), and the derivable fields
          lane (launcher --class), scratch_root (the launcher's job dir), keep (result_path relative to scratch_root) and
          kind=compute are filled when missing. Every rewrite is printed as one LINT line.
--repair  after a dry-run FAIL of a known class: rebuild the spec from ready/<id>.json, apply the fix, lint, republish
          under the SAME id (a spec change makes the keeper re-dry-run it; the keeper starts that run, not this tool).
          Known: (1) "no unit in <p>" / "before writing a unit to <p>" where <p> is a completion marker or a results file
          (RESULT.json|results.jsonl) was written in its run dir during the run; (2) a publish refusal naming a
          lint-derivable field. Anything else: exit 3 `UNKNOWN-FAILURE-CLASS <reason>` and nothing changes.

Ownership (operator 2026-11-02): handoff_task must name an existing handoffs/active/<file>.md (`file.md:ROW` or
`file.md`); the row belongs to that HANDOFF and its PASS/FAIL/run-end events reach that handoff's session.
Smoke = THE dry run (operator 2026-11-02): the launcher runs HERE, in the owner's turn, on 4 cpus no quiet-host grant
holds (GPU rows: only while gpu-quiet is free, with VRAM residency checked; else refused "GPU busy, retry"), for
smoke_timeout_s (300). PASS (a first unit in result_path, clean stop) writes dryrun/<id>/PASS.json: ready at once. FAIL
writes the FAIL memo and prints launcher_out_tail; the allocator grants only PASSed rows."""
import argparse
import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rowflow as rf  # noqa: E402

_MARKER = re.compile(r"\.(complete|ended|done|FILED)$|/grants/|/(RUN_)?(COMPLETE|TERMINAL)[^/]*$", re.I)
RESULT_FILE = {"json": "RESULT.json", "jsonl": "results.jsonl"}
RESULT_NAMES = ("RESULT.json", "RESULT.jsonl", "results.jsonl", "results.json")
SPEC_KEYS = ("id", "owner", "lane", "regions", "result_path", "result_format", "decision_rule", "estimate_s", "handoff_task",
             "priority_rank", "scratch_root", "keep", "dryrun_timeout_s", "min_window_s", "lineage", "lineage_reset", "supersedes",
             "notes", "row", "snapshot", "admission_class", "dryrun_whole_host", "dryrun_native_result")
REPO = os.environ.get("ROWFLOW_REPO", "/workspace")
SMOKE_TIMEOUT_S = 300
DERIVABLE = ("lane", "scratch_root", "keep", "kind")
_UNIT_RE = re.compile(r"(?:no unit in|before writing a unit to) (\S+) \(")


def is_marker(p):
    return bool(_MARKER.search(str(p or "")))


# Operator 2026-11-01 23:55Z "DO BETTER" (third occurrence: inf70, kvu-vkq3 tokenize, sr6 `sha256sum -c FULL-MODEL.sha256` on one
# core inside a whole-host quiet grant): hashing model weights or single-core prep inside the grant is refused at publish.
PREP_RX = re.compile(r"(?:sha256sum|sha256|shasum|md5sum|b2sum|hashlib\.sha256)\b[^\n]*(?:\.gguf|FULL-MODEL|\bMODEL[^\s]*\.sha256|/models?/|weights?)"
                     r"|\b(?:tokeni[sz]e|tokenizer\.encode|pretokeni[sz]e)\b"
                     r"|\b(?:wget|curl|aria2c|rsync|huggingface-cli download|hf_hub_download|snapshot_download)\b"
                     r"|\bcp\b[^\n]*\.gguf", re.I)
# small source/packet checksum lists (SOURCE-SHA256SUMS, PACKET-SHA256SUMS, INPUT.sha256 over scripts) are cheap integrity
# checks and stay allowed; only WEIGHT hashing (gguf / FULL-MODEL / models dir) and single-core prep are refused.
PREP_MSG = "verify/prepare inputs once before publishing, not inside the grant"


def executed_texts(launcher):
    """The launcher's text plus every local script it executes (engine line tokens and $D/<file> references in its own dir)."""
    texts = {}
    try:
        texts[launcher] = open(launcher, errors="replace").read()
    except OSError:
        return texts
    d = os.path.dirname(launcher)
    cands = set()
    try:
        cands.update(rf.referenced_paths(rf.parse_launcher(launcher)))
    except Exception:
        pass
    for m in re.finditer(r"(?:\$D|\$\{D\}|" + re.escape(d) + r")/([A-Za-z0-9_.-]+\.(?:sh|py|bash))", texts[launcher]):
        cands.add(os.path.join(d, m.group(1)))
    for c in cands:
        if os.path.isfile(c) and c != launcher and os.path.getsize(c) < 2_000_000:
            try:
                texts[c] = open(c, errors="replace").read()
            except OSError:
                pass
    return texts


def prep_in_grant(launcher):
    """(file, offending line) when the launcher or a script it runs hashes weights or does single-core prep in the grant."""
    for f, txt in executed_texts(launcher).items():
        for ln in txt.splitlines():
            if ln.lstrip().startswith("#"):
                continue
            if PREP_RX.search(ln):
                return f, ln.strip()[:160]
    return None


def lint(spec):
    """Rewrite the known spec defects in place; returns the LINT notes. Everything else is rowflow.publish's job."""
    notes = []
    launcher = os.path.abspath(str(spec.get("launcher") or ""))
    if os.path.isfile(launcher):
        hit = prep_in_grant(launcher)
        rf.need(hit is None, f"{PREP_MSG}: {hit[0]} runs `{hit[1]}`" if hit else "")
        if not spec.get("lane"):
            try:
                cls = rf.parse_launcher(launcher)["class"]
                spec["lane"] = "gpu" if cls in ("gpu", "cpu+gpu") else "cpu"
                notes.append(f"lane={spec['lane']} (launcher --class {cls})")
            except rf.Refused:
                pass  # publish reports the launcher defect
        if not spec.get("scratch_root") and launcher.startswith(rf.TMP):
            spec["scratch_root"] = rf.TMP + launcher[len(rf.TMP):].split("/")[0]
            notes.append(f"scratch_root={spec['scratch_root']} (launcher's job dir)")
    rp = str(spec.get("result_path") or "")
    if is_marker(rp):
        fn = RESULT_FILE.get(str(spec.get("result_format") or ""))
        rf.need(fn, f"result_path {rp} is a completion marker, not a results file: declare result_format json|jsonl "
                    f"(-> RESULT.json|results.jsonl in the run dir) or point result_path at the file the filer reads")
        rundir = spec.get("scratch_root") if "/grants/" in rp else os.path.dirname(rp)
        rf.need(rundir, f"result_path {rp} is a grants/ marker and the spec has no scratch_root to place {fn} in")
        spec["result_path"] = rp = os.path.join(rundir, fn)
        notes.append(f"result_path={rp} (was a completion marker)")
    sr = str(spec.get("scratch_root") or "").rstrip("/")
    if not spec.get("keep") and sr and rp.startswith(sr + "/"):
        spec["keep"] = [os.path.relpath(rp, sr)]
        notes.append(f"keep={spec['keep']}")
    if not spec.get("kind"):
        spec["kind"] = "compute"
        notes.append("kind=compute")
    return notes


def check_handoff(spec, repo=None):
    """The row belongs to a handoff: handoff_task must name an existing handoffs/active/<file>.md."""
    ht = str(spec.get("handoff_task") or "").strip()
    f = os.path.basename(ht.split(":", 1)[0])
    rf.need(f.endswith(".md") and os.path.isfile(os.path.join(repo or REPO, "handoffs", "active", f)),
            f"handoff_task {ht!r} names no handoffs/active/<file>.md; write \"handoff_task\": \"<file>.md:<ROW-ID>\" (or "
            f"\"<file>.md\") for the handoff whose task this row serves - the row belongs to that handoff, and its "
            f"dry-run FAIL/PASS and run-end reach that handoff's session (FILLERS, session pids and engines are not owners)")


def smoke_regions(lane, regions, flags):
    """Where the smoke runs: GPU rows only while gpu-quiet is free (else refused); CPU rows on 4 cpus of a quarter no
    quiet-host grant holds, preferring one with no region-lock holder. Nothing is booked: a dry run uses no real resources."""
    rl = rf.rl_status()
    grants = rf.open_grants(flags)
    if lane == "gpu":
        rf.need(rl.get(rf.GPU, ("free",))[0] == "free" and not any(rf.GPU in g["holds"] for g in grants), "GPU busy, retry")
        return regions
    quiet = set().union(*[g["holds"] for g in grants if rf.GPU in g["holds"] and len(g["holds"] & set(rf.QUARTERS)) == 4] or [set()])
    qs = sorted((q for q in rf.QUARTERS if q not in quiet), key=lambda q: rl.get(q, ("free",))[0] != "free")
    rf.need(qs, "a quiet-host grant holds every quarter, retry")
    lo = int(qs[0][1]) * 24
    return f"{lo}-{lo + 3}"


def publish_smoked(spec, flags, source):
    """Publish, then THE dry run in the owner's turn (rowflow.dryrun_run writes PASS.json or the FAIL memo)."""
    regions = smoke_regions(spec.get("lane"), spec.get("regions") or "mi210_0,184-191", flags)
    row = rf.publish(spec, flags, source=source)
    rid = row["id"]
    v, msg = rf.dryrun_run(flags, rid, regions, one_quarter=True, smoke_s=int(spec.get("smoke_timeout_s") or SMOKE_TIMEOUT_S))
    if v == "PASS":
        print(f"SMOKE PASS {rid} on {regions}: {msg}")
        return row
    t = "\n".join(rf.tail(os.path.join(rf.dry_dir(flags, rid), "launcher.out"), 30))
    raise rf.Refused(f"smoke {v} for {rid} on {regions}: {msg}\nlauncher_out_tail:\n{t}\nFIX: fix the launcher/spec now, in "
                     f"this turn, then re-run publish_row.py on the same spec (the row is not granted until a smoke PASSes)")


def results_written_during(fail, rundir):
    """The newest RESULT.json|results.jsonl in rundir whose mtime falls inside the failed dry run, else None."""
    try:
        t0 = dt.datetime.strptime(fail["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp() - int(fail.get("elapsed_s") or 0) - 60
    except (KeyError, TypeError, ValueError):
        return None
    hits = [p for p in (os.path.join(rundir, n) for n in RESULT_NAMES) if os.path.isfile(p) and os.path.getmtime(p) >= t0]
    return max(hits, key=os.path.getmtime) if hits else None


def repair(rid, flags):
    """Returns (rc, message). rc 0 = republished; 3 = unknown failure class (nothing changed)."""
    row = rf.load_json(rf.ready_path(flags, rid))
    rf.need(row and row.get("schema") == rf.SCHEMA, f"no epyc.row.v3 row at ready/{rid}.json")
    fails = rf.fail_paths(flags, rid)
    rf.need(fails, f"no FAIL record under dryrun/{rid}/; nothing to repair")
    fail = rf.load_json(fails[-1]) or {}
    reason = str(fail.get("reason") or "")
    spec = {k: row[k] for k in SPEC_KEYS if row.get(k) is not None}
    spec.update(launcher=row["launcher"]["path"], ram_gib=row.get("gib"))
    # JEV-3 replace: the FAIL class is the typed judgment (worker_fast); the regex classifier answers only when typed is unavailable
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "churn"))
    import typed_classify as tc  # noqa: E402
    d = tc.decide_fail(fail)
    cls = d["label"]
    print(f"FAIL-CLASS {cls.value} source={d['source']}" + (f" (typed unavailable: {d['unavailable'][:200]})" if d["unavailable"] else ""), file=sys.stderr)
    m = _UNIT_RE.search(reason)
    rp = m.group(1) if m else None
    if cls == tc.FailClass.result_dir_path and rp:
        found = results_written_during(fail, os.path.dirname(rp.split("*")[0]))
        if not found:
            return 3, f"UNKNOWN-FAILURE-CLASS result_dir_path but nothing was written during the run: {reason}"
        spec["result_path"], spec["result_format"] = found, rf.guess_format(found)
    elif cls == tc.FailClass.marker_result_path and rp:
        if spec.get("result_format") == "text-lines":
            spec.pop("result_format")  # the extension guess for a marker, not a declaration: lint refuses or rewrites
    elif cls != tc.FailClass.derivable_field_missing:
        return 3, f"UNKNOWN-FAILURE-CLASS {reason}" if d["source"] != "typed" else f"UNKNOWN-FAILURE-CLASS (typed {cls.value}) {reason}"
    for note in lint(spec):
        print(f"LINT {note}")
    new = rf.publish(spec, flags, source=f"repair:{fails[-1]}")
    changed = [f"{k} {row.get(k)!r} -> {new.get(k)!r}" for k in ("result_path", "result_format", "lane", "regions", "scratch_root", "keep") if row.get(k) != new.get(k)]
    rf.need(changed, f"repair of {rid} would republish an identical row; the keeper would fail it again")
    return 0, f"REPAIRED {rid} -> {new['id']}: " + "; ".join(changed)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--migrate", action="store_true", help="spec is a legacy ready/<id>.json manifest")
    ap.add_argument("--repair", metavar="ROW_ID")
    ap.add_argument("--flags", default=rf.FLAGS)
    a = ap.parse_args(argv)
    try:
        if a.repair:
            rc, msg = repair(a.repair, a.flags)
            print(msg)
            return rc
        rf.need(a.spec, "spec.json or --repair <row-id> required")
        spec = rf.load_json(a.spec)
        rf.need(spec, f"{a.spec} is not a JSON object")
        if a.migrate:
            spec = rf.spec_from_legacy(spec, a.flags)
        check_handoff(spec)
        for note in lint(spec):
            print(f"LINT {note}")
        print(rf.published_line(publish_smoked(spec, a.flags, os.path.abspath(a.spec)), a.flags))
        return 0
    except rf.Refused as e:
        print(f"REFUSED: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
