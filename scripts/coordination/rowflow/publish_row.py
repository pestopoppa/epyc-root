#!/usr/bin/env python3
"""publish_row.py <spec.json> [--migrate] | publish_row.py --repair <row-id>   [--flags DIR] - the owner's ONE tool.

publish   LINT the spec, then rowflow.publish derives the rest. The lint rewrites the two defects that used to cost a dry
          run plus an agent turn (CAF-4): a result_path that is a completion marker (.complete/.ended/.done/.FILED,
          grants/, COMPLETE*/TERMINAL*) becomes the declared results file in the same run dir (result_format json ->
          RESULT.json, jsonl -> results.jsonl; no declared format -> refused in one line), and the derivable fields
          lane (launcher --class), scratch_root (the launcher's job dir) and kind=compute are filled when missing. keep is
          left as the owner wrote it: empty = inputs + result (the reaper never deletes a file older than the row's first
          job start and always keeps result_path; keep globs only add). Every rewrite is printed as one LINT line.
--repair  after a dry-run FAIL of a known class: rebuild the spec from ready/<id>.json, apply the fix, lint, republish
          under the SAME id (a spec change makes the keeper re-dry-run it; the keeper starts that run, not this tool).
          Known: (1) "no unit in <p>" / "before writing a unit to <p>" where <p> is a completion marker or a results file
          (RESULT.json|results.jsonl) was written in its run dir during the run; (2) a publish refusal naming a
          lint-derivable field. Anything else: exit 3 `UNKNOWN-FAILURE-CLASS <reason>` and nothing changes.

Ownership (operator 2026-11-02): handoff_task must name an existing handoffs/active/<file>.md (`file.md:ROW` or
`file.md`); the row belongs to that HANDOFF and its PASS/FAIL/run-end events reach that handoff's session.
Task lint (BRF-T6-1, D6 staged, operator 2026-11-02): handoff_task must also name the TASK (`file.md:<TASK-ID>` or
`file.md:<LINE>`); that open box is linted with `scripts/handoffs/task_lint.py publish`. RELAXED (operator 2026-11-03):
the row is REFUSED only when the box names no model/build identity (field c), states no stop rule (field s), or
handoff_task does not resolve to a real open task box (file-only, or not found). Every other finding (NEEDS-*, pending
operator choice, non-inference payload, roll-up, prose prerequisite, standing hold, metric/rule/region/estimate
fields) is a WARNING, printed and recorded in the row's `publish_warnings`; the smoke still gates every row. The lint
runs before the smoke, so a refused row costs no compute.
Smoke = THE dry run (operator 2026-11-05: a KEEPER-SCHEDULED filler): a CPU row's smoke is QUEUED
(dryrun/<id>/SMOKE-QUEUED.json) and this tool returns at once; the keeper's allocate places it first, on 4 genuinely
free cores, in the next free slot. Waiting is never a failure. `--smoke-now` runs it here, at once, on free cores of the
keeper's snapshot (queued if none). (GPU rows: on their own regions, VRAM residency checked, and only while the GPU is free - otherwise QUEUED as
dryrun/<id>/GPU-SMOKE-QUEUED.json and run by the allocator in the next GPU gap, or by `rowflow.py gpu-batch` from any
session; never refused). PASS (operator 2026-11-03) = the job's FIRST REAL PROGRESS within first_progress_s (300; the spec
may set it): spec.smoke_predicate exits 0, or a NEW non-placeholder record appears in result_path (rowflow.FirstProgress),
then a clean stop -> dryrun/<id>/PASS.json: ready at once. FAIL writes the FAIL memo and prints ONE line (cause + fix +
the log path); the allocator grants only PASSed rows."""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rowflow as rf  # noqa: E402

_MARKER = re.compile(r"\.(complete|ended|done|FILED)$|/grants/|/(RUN_)?(COMPLETE|TERMINAL)[^/]*$", re.I)
RESULT_FILE = {"json": "RESULT.json", "jsonl": "results.jsonl"}
RESULT_NAMES = ("RESULT.json", "RESULT.jsonl", "results.jsonl", "results.json")
SPEC_KEYS = ("id", "owner", "lane", "regions", "result_path", "result_format", "decision_rule", "estimate_s", "handoff_task",
             "priority_rank", "scratch_root", "keep", "dryrun_timeout_s", "min_window_s", "lineage", "lineage_reset", "supersedes",
             "notes", "row", "snapshot", "admission_class", "dryrun_native_result", "publish_warnings", "busy_fraction",
             "first_progress_s", "smoke_predicate", "unit_key", "fix_ref", "baseline_ref", "shape_override", "width_justification", "timing")
REPO = os.environ.get("ROWFLOW_REPO", "/mnt/raid0/llm/views/epyc-root-main")  # tracks origin/main; /workspace is a stale detached checkout
SMOKE_TIMEOUT_S = 300
MIN_ESTIMATE_S = 300  # ws58 2026-11-02: a shorter job runs in the owner's turn, not as a row
DERIVABLE = ("lane", "scratch_root", "kind")
_UNIT_RE = re.compile(r"(?:no unit in|before writing a unit to) (\S+) \(")


def is_marker(p):
    return bool(_MARKER.search(str(p or "")))


# Operator 2026-11-01 23:55Z "DO BETTER" (third occurrence: inf70, kvu-vkq3 tokenize, sr6 `sha256sum -c FULL-MODEL.sha256` on one
# core inside a whole-host quiet grant): hashing model weights or single-core prep inside the grant is flagged at publish.
# Operator 2026-11-03 (session review §5 item 8): a WARNING (printed + publish_warnings), never a refusal.
PREP_RX = re.compile(r"(?:sha256sum|sha256|shasum|md5sum|b2sum|hashlib\.sha256)\b[^\n]*(?:\.gguf|FULL-MODEL|\bMODEL[^\s]*\.sha256|/models?/|weights?)"
                     r"|\b(?:tokeni[sz]e|tokenizer\.encode|pretokeni[sz]e)\b"
                     r"|\b(?:wget|curl|aria2c|rsync|huggingface-cli download|hf_hub_download|snapshot_download)\b"
                     r"|\bcp\b[^\n]*\.gguf", re.I)
# small source/packet checksum lists (SOURCE-SHA256SUMS, PACKET-SHA256SUMS, INPUT.sha256 over scripts) are cheap integrity
# checks and are not flagged; only WEIGHT hashing (gguf / FULL-MODEL / models dir) and single-core prep are warned about.
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
        if hit:  # operator 2026-11-03 (session review §5 item 8): WARN, never refuse; recorded in the row's publish_warnings
            w = f"prep-in-grant: {hit[0]} runs `{hit[1]}`; {PREP_MSG} (it spends grant time; publish continues)"
            print(f"WARN {w}")
            pw = list(spec.get("publish_warnings") or [])
            if w not in pw:
                spec["publish_warnings"] = pw + [w]
        if spec.get("snapshot") is not True:  # operator 2026-11-03: snapshot is opt-in; say what is NOT frozen
            try:
                vol = [p for p in rf.referenced_paths(rf.parse_launcher(launcher)) if rf.volatile_root(p)]
            except Exception:  # noqa: BLE001 - publish reports a launcher defect itself
                vol = []
            if vol:
                w = (f"volatile-paths: the job runs {', '.join(vol[:3])} from a lane/worktree path that can change or vanish "
                     "before its grant; set \"snapshot\": true in the spec to freeze it (publish continues)")
                print(f"WARN {w}")
                pw = list(spec.get("publish_warnings") or [])
                if w not in pw:
                    spec["publish_warnings"] = pw + [w]
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
    # keep is not linted (operator 2026-11-03, session review 3.1): an empty keep = every input (older than the first job
    # start) + the result; the keeper's reaper protects both and keep globs only add to them.
    rf.check_busy_fraction(spec)   # before the smoke: a bad value costs no compute
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


def _task_lint():
    """task_lint.py: TASK_LINT_DIR, else a copy installed beside this file (compute-flags/bin/rowflow), else the checkout
    this file lives in, else the repo's scripts/handoffs (ROWFLOW_REPO)."""
    here = os.path.dirname(os.path.abspath(__file__))
    # the checkout this file lives in wins over ROWFLOW_REPO, so a checkout's tests lint with that checkout's lint
    for d in (os.environ.get("TASK_LINT_DIR"), here, os.path.join(os.path.dirname(os.path.dirname(here)), "handoffs"),
              os.path.join(REPO, "scripts", "handoffs")):
        if d and os.path.isfile(os.path.join(d, "task_lint.py")):
            if d not in sys.path:
                sys.path.insert(0, d)
            import task_lint  # noqa: E402
            return task_lint
    raise rf.Refused("task_lint.py not found (set TASK_LINT_DIR or ROWFLOW_REPO); publish cannot lint the task box")


def task_box(spec, repo=None):
    """(file, line, box text, children) of the OPEN box handoff_task names: `<file>.md:<TASK-ID>` matches the bold ID at
    the start of a checkbox; `<file>.md:<N>` is a 1-based line number."""
    tl = _task_lint()
    ht = str(spec.get("handoff_task") or "").strip()
    f, _, task = ht.partition(":")
    path = os.path.join(repo or REPO, "handoffs", "active", os.path.basename(f))
    rf.need(task.strip(), f"handoff_task {ht!r} names no task: write \"<file>.md:<TASK-ID>\" so the publish gate can lint "
                          f"the box this row serves (BRF-T6-1)")
    task = task.strip()
    rf.need(os.path.isfile(path), f"handoff_task {ht!r}: {path} does not exist")
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    idx = None
    if task.isdigit():
        idx = int(task) - 1
        rf.need(0 <= idx < len(lines) and tl.L1.CHECKBOX.match(lines[idx]), f"handoff_task {ht!r}: line {task} is not a checkbox")
    else:
        rx = re.compile(r"^\s*[-*] \[.\]\s*\*\*" + re.escape(task) + r"(?![A-Za-z0-9.-])")
        idx = next((i for i, l in enumerate(lines) if rx.match(l)), None)
        rf.need(idx is not None, f"handoff_task {ht!r}: no checkbox **{task}** in {os.path.basename(f)}")
    state = tl.L1.CHECKBOX.match(lines[idx]).group(2)
    rf.need(state == " ", f"handoff_task {ht!r}: the box is [{state}], not open; a row serves an open task")
    txt, ch = tl.L1.block(lines, idx)
    return path, idx + 1, txt, ch


def check_task_lint(spec, repo=None):
    """BRF-T6-1, relaxed (operator 2026-11-03): refuse only (1) a box that does not resolve to a real open task (task_box),
    (2) a box with no model/build identity, (3) a box with no stop rule. Every other finding is a WARNING: printed, and
    recorded in the row's publish record as spec["publish_warnings"] (-> ready/<id>.json). Returns the warnings."""
    path, ln, txt, ch = task_box(spec, repo)
    refuse, warn = _task_lint().publish_findings(txt, ch)
    rf.need(not refuse, f"task_lint publish REFUSED {os.path.basename(path)}:{ln} ({spec.get('handoff_task')}):\n  - "
            + "\n  - ".join(refuse) + f"\nFIX: edit the box at {path}:{ln} as listed above, then re-run publish_row.py")
    warn = [f"{os.path.basename(path)}:{ln}: {w}" for w in warn]
    for w in warn:
        print(f"WARN task_lint {w}")
    if warn:
        spec["publish_warnings"] = warn
    else:
        spec.pop("publish_warnings", None)
    return warn


def smoke_regions(lane, regions, flags):
    """Where an immediate (--smoke-now) smoke runs: GPU rows on their own regions, CPU rows on 4 genuinely free cores of
    the keeper's snapshot (rowflow.host_snapshot: region-lock, open grants, live smokes). None = nothing free now."""
    if lane == "gpu":
        return regions
    _, free, _ = rf.host_snapshot(flags)
    return rf.pick_smoke_cpus(free)


def queue_cpu_smoke(flags, rid, spec, smoke_s, why=""):
    """Operator 2026-11-05: the smoke is a keeper-scheduled filler. Unpublish until PASS and queue it; the allocator
    places it in the next free slot. Queued is not a failure."""
    unpublish(flags, rid)
    rf.atomic_json(rf.smoke_queued_path(flags, rid), {"id": rid, "smoke_s": smoke_s, "cpus": rf.SMOKE_CPUS, "spec": spec,
                                                      "queued_at": rf.now_iso()})
    print(f"queued for smoke{why}; the keeper runs it in the next free slot; your row becomes ready on PASS "
          f"(status: {rf.dry_dir(flags, rid)}/launcher.out) — move to your next task ({rid})")


def run_queued_smoke(flags, rid, regions):
    """The keeper's detached runner for ONE placed CPU smoke (publish_row.py --run-smoke). PASS/FAIL dequeue; WAIT (lock
    contention, a held host) leaves it queued for the next tick."""
    q = rf.smoke_queued_path(flags, rid)
    qd = rf.load_json(q) or {}
    try:
        up = unpublished_path(flags, rid)
        if os.path.exists(up):
            os.replace(up, rf.ready_path(flags, rid))
        try:
            v, msg = run_smoke(flags, rid, regions, int(qd.get("smoke_s") or SMOKE_TIMEOUT_S))
            if v == "PASS":
                row = rf.load_json(rf.ready_path(flags, rid))
                rf.need(row is not None, f"queued smoke {rid} lost its ready manifest")
                rf.supersede(flags, row)
                file_if_complete(flags, rid, row)
        except Exception as e:  # noqa: BLE001
            # keeper-hotfix 2026-11-05: a harness exception is not the row's verdict - WAIT (requeued, bounded), never FAIL
            v, msg = "WAIT", f"harness exception {type(e).__name__}: {e}"
        if v == "WAIT":   # bounded retry: the SMOKE_MAX_WAITS-th WAIT becomes FAIL reason=never-started
            row = rf.load_json(rf.ready_path(flags, rid)) or rf.load_json(unpublished_path(flags, rid))
            v = rf.smoke_wait_or_fail(flags, rid, row, msg[:200], log=print)
        print(f"SMOKE {v} {rid} on {regions}: {msg} (log: {os.path.join(rf.dry_dir(flags, rid), 'launcher.out')})")
        if v != "WAIT" and os.path.exists(q):
            os.remove(q)
        return v
    finally:
        try:
            os.remove(rf.smoke_placed_path(flags, rid))
        except OSError:
            pass


def retire_old_verdicts(flags, rid):
    """ws58 2026-11-02: a publish is a FRESH smoke. An old FAIL memo (or PASS) must never stand in for this smoke's result
    (codex-ni-s18: a 00:07Z FAIL was re-reported at 10:4xZ), so earlier verdicts move to dryrun/<id>/superseded/<ts>/."""
    dd = rf.dry_dir(flags, rid)
    old = rf.fail_paths(flags, rid) + ([rf.pass_path(flags, rid)] if os.path.exists(rf.pass_path(flags, rid)) else [])
    if not old:
        return
    dst = os.path.join(dd, "superseded", dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    os.makedirs(dst, exist_ok=True)
    for p in old:
        os.replace(p, os.path.join(dst, os.path.basename(p)))


def unpublished_path(flags, rid): return os.path.join(rf.dry_dir(flags, rid), "unpublished.json")


def unpublish(flags, rid):
    """ws58 2026-11-02: ready/<id>.json exists only for a smoke PASS. A refused/failed smoke moves the manifest to
    dryrun/<id>/unpublished.json (kept for --repair), so nothing outside the owner's turn sees an unsmoked row."""
    rp = rf.ready_path(flags, rid)
    if os.path.exists(rp):
        os.makedirs(rf.dry_dir(flags, rid), exist_ok=True)
        os.replace(rp, unpublished_path(flags, rid))


def queued_path(flags, rid): return os.path.join(rf.dry_dir(flags, rid), "GPU-SMOKE-QUEUED.json")


def gpu_busy(flags):
    """Operator 2026-11-02: a GPU smoke never loads a model onto the MI210 while a GPU job runs (OOM, timing skew).
    Busy = a live grant holds gpu-quiet, a region-lock holder exists on gpu-quiet, or a queued-smoke batch is running."""
    if rf.rl_status().get(rf.GPU, ("free",))[0] != "free":
        return True
    return rf.gpu_batch_running(flags) or any(rf.GPU in g["holds"] for g in rf.open_grants(flags))


def run_smoke(flags, rid, regions, smoke_s):
    """THE dry run: (verdict, msg); the manifest survives only a PASS."""
    v, msg = "FAIL", "smoke did not run"
    try:
        v, msg = rf.dryrun_run(flags, rid, regions, one_quarter=True, smoke_s=smoke_s)
    finally:
        if v != "PASS":
            unpublish(flags, rid)
    return v, msg


def run_gpu_queue(flags):
    """The allocator's detached batch: every queued GPU smoke, one after another, as publish_row would run it."""
    n = 0
    for q in sorted(glob.glob(os.path.join(flags, "dryrun", "*", "GPU-SMOKE-QUEUED.json"))):
        qd = rf.load_json(q) or {}
        rid = os.path.basename(os.path.dirname(q))
        up = unpublished_path(flags, rid)
        if os.path.exists(up):
            os.replace(up, rf.ready_path(flags, rid))
        try:
            v, msg = run_smoke(flags, rid, qd.get("regions") or "mi210_0,184-191", int(qd.get("smoke_s") or SMOKE_TIMEOUT_S))
            if v == "PASS":
                row = rf.load_json(rf.ready_path(flags, rid))
                rf.need(row is not None, f"queued smoke {rid} lost its ready manifest")
                rf.supersede(flags, row)
                file_if_complete(flags, rid, row)
        except Exception as e:  # noqa: BLE001 - one smoke never stops the batch
            v, msg = "FAIL", f"{type(e).__name__}: {e}"
        print(f"GPU-SMOKE {v} {rid}: {msg}")
        os.remove(q)
        n += 1
    return n


def completed_result(row, passed):
    """Resolve the declared result once; a glob never becomes a destination directory."""
    declared = row.get("declared_result_path", row.get("result_path"))
    scratch = os.path.realpath(row.get("scratch_root") or "")
    rf.need(row.get("scratch_root") and isinstance(declared, str) and os.path.isabs(declared),
            "completed-smoke result needs an absolute declaration and scratch_root")
    matches = glob.glob(declared, recursive=True) if glob.has_magic(declared) else [declared]
    rf.need(len(matches) == 1, "completed-smoke result must match exactly one file")
    source = os.path.realpath(matches[0])
    rf.need(os.path.isfile(source) and os.path.commonpath([scratch, source]) == scratch
            and source != scratch, "completed-smoke result is missing or outside scratch_root")
    recorded = passed.get("result_path")
    rf.need(recorded == declared or (isinstance(recorded, str) and not glob.has_magic(recorded)
            and os.path.realpath(recorded) == source), "PASS result differs from the declared result")
    if passed.get("result_sha256") is not None:
        rf.need(rf.sha256(source) == passed["result_sha256"], "PASS result content hash changed")
    return source


def completed_bindings(flags, rid, row, passed, source):
    """Bind filing to the unchanged PASS, published code and current validated result bytes."""
    rf.need(row.get("schema") == rf.SCHEMA and row.get("id") == rid and passed.get("id") == rid,
            "completed smoke row/PASS identity mismatch")
    rf.need(passed.get("result_format") == row.get("result_format"), "PASS result format mismatch")
    for key in ("launcher", "engine"):
        item = row.get(key) or {}
        rf.need(item.get("path") and item.get("sha256") and os.path.isfile(item["path"]),
                f"completed smoke {key} identity missing")
        rf.need(rf.sha256(item["path"]) == item["sha256"] == passed.get(key + "_sha256"),
                f"completed smoke {key} content hash changed")
    parsed = rf.parse_launcher(row["launcher"]["path"])
    rf.need(os.path.realpath(parsed["engine"]) == os.path.realpath(row["engine"]["path"]),
            "completed smoke launcher engine differs")
    sources = {os.path.realpath(path): rf.sha256(path) for path in rf.referenced_paths(parsed)
               if os.path.isfile(path)}
    return {"schema": "epyc.rowflow.completed_smoke_filing.v1", "id": rid,
            "manifest_sha256": hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "pass_sha256": rf.sha256(rf.pass_path(flags, rid)), "result_path": source,
            "result_sha256": rf.sha256(source), "sources_sha256": sources,
            "launcher_sha256": row["launcher"]["sha256"], "engine_sha256": row["engine"]["sha256"]}


def file_if_complete(flags, rid, row):
    """ws58 2026-11-02: a smoke that COMPLETED the whole job is the run. Its result already sits where the row writes it
    (a declared glob resolves to one literal file); grants/<id>.ended + .complete are written as a granted run leaves them, so
    the row is done (status: grants/<id>.complete) and is never granted."""
    p = rf.load_json(rf.pass_path(flags, rid)) or {}
    if p.get("job_complete") is not True:
        return False
    # Operator 2026-11-02: never file a row complete because its SMOKE passed. Re-checked here (a PASS.json may predate
    # the check): the launcher must have no FILLER_SMOKE/FILLER_DRYRUN branch and the full-job predicate must hold.
    # Preserve the exact published manifest before removing it from READY. The
    # filer needs its rule and result path even when the entire job ran in the
    # owner smoke. Do not reconstruct those fields after the run.
    try:
        ready = rf.ready_path(flags, rid)
        rf.need(not os.path.exists(ready) or rf.load_json(ready) == row,
                "ready manifest differs from completed smoke")
        src = completed_result(row, p)
        bindings = completed_bindings(flags, rid, row, p, src)
        dd = rf.dry_dir(flags, rid)
        receipt_path = os.path.join(dd, "completed-smoke-filing.json")
        previous = rf.load_json(receipt_path)
        rf.need(not os.path.exists(receipt_path) or previous == bindings,
                "completed smoke filing content hash changed")
        ok, why = rf.smoke_completion_check(row)
        if not ok:
            print(f"smoke passed but the row is NOT complete ({rid}): {why}; it stays a row")
            return False
        rf.need(bindings == completed_bindings(flags, rid, row, p, src),
                "completed smoke content changed during full-completion check")
        rf.atomic_json(os.path.join(dd, "published-manifest.json"), row)
        archived = dict(row, result_path=src, declared_result_path=row["result_path"],
                        completed_result_sha256=bindings["result_sha256"])
        rf.atomic_json(os.path.join(dd, "completed-manifest.json"), archived)
        rf.atomic_json(receipt_path, bindings)
        g = os.path.join(flags, "grants")
        os.makedirs(g, exist_ok=True)
        dd = rf.dry_dir(flags, rid)
        for term in ("ended", "complete"):
            terminal_src = os.path.join(dd, term)
            dest = os.path.join(g, f"{rid}.{term}")
            if os.path.exists(terminal_src):
                with open(terminal_src) as f:
                    txt = f.read()
            elif os.path.exists(dest):
                # A retry must retain the terminal bytes already filed, including their time.
                with open(dest) as f:
                    txt = f.read()
            else:
                txt = (f"rc=0 reason=complete-in-smoke time={rf.now_iso()}\n" if term == "ended"
                       else f"complete time={rf.now_iso()} id={rid} via=smoke\n")
            if os.path.exists(dest):
                with open(dest) as f:
                    rf.need(f.read() == txt, "existing completed-smoke terminal differs")
                continue
            tmp = dest + ".tmp"
            with open(tmp, "w") as f:
                f.write(txt)
            os.replace(tmp, dest)
        ready = rf.ready_path(flags, rid)
        if os.path.exists(ready):
            rf.need(rf.load_json(ready) == row, "ready manifest changed during completed filing")
            os.remove(ready)
    except Exception:
        # Any failure after completed work must not leave it grantable again.
        # Preserve READY in the existing non-ready repair location, then raise.
        unpublish(flags, rid)
        raise
    print(f"job completed inside the smoke: no compute row needed; file the result now ({rid}: {src})")
    return True


def resume_complete(flags, rid):
    """Retry only terminal filing from a prior PASS; never publish, smoke or qualify again."""
    rf.need(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", rid), "invalid completed row id")
    dd = rf.dry_dir(flags, rid)
    candidates = [rf.load_json(os.path.join(dd, name)) for name in
                  ("unpublished.json", "published-manifest.json")]
    rows = [row for row in candidates if row is not None]
    if not rows:
        archived = rf.load_json(os.path.join(dd, "completed-manifest.json"))
        if archived is not None:
            row = dict(archived)
            if row.get("completed_result_sha256"):
                rf.need(os.path.isfile(row.get("result_path", ""))
                        and rf.sha256(row["result_path"]) == row["completed_result_sha256"],
                        "archived completed result content hash changed")
            if "declared_result_path" in row:
                row["result_path"] = row.pop("declared_result_path")
                row.pop("completed_result_sha256", None)
            rows = [row]
    rf.need(rows and all(row == rows[0] for row in rows), "prior completed/unpublished manifest missing or ambiguous")
    passed = rf.load_json(rf.pass_path(flags, rid))
    rf.need(passed and passed.get("job_complete") is True, "prior completed PASS missing")
    rf.need(file_if_complete(flags, rid, rows[0]), "prior smoke no longer satisfies full completion")
    return 0


def publish_smoked(spec, flags, source, queue_cpu=False):
    """Publish, then THE dry run (rowflow.dryrun_run writes PASS.json or the FAIL memo). queue_cpu=True (the CLI default,
    operator 2026-11-05): a CPU row's smoke is QUEUED for the keeper (returns None). A GPU row whose GPU is busy is QUEUED
    for the next GPU gap. An immediate CPU smoke with no free cores in the keeper's snapshot is queued too."""
    row = rf.publish(spec, flags, source=source)
    rid = row["id"]
    retire_old_verdicts(flags, rid)
    smoke_s = int(row.get("first_progress_s") or spec.get("first_progress_s") or spec.get("smoke_timeout_s") or SMOKE_TIMEOUT_S)
    if spec.get("lane") == "gpu" and gpu_busy(flags):
        unpublish(flags, rid)
        rf.atomic_json(queued_path(flags, rid), {"id": rid, "regions": spec.get("regions") or "mi210_0,184-191", "smoke_s": smoke_s, "spec": spec,
                                                 "queued_at": rf.now_iso()})
        print(f"GPU busy: smoke queued; it runs in the next GPU gap; your row becomes ready on PASS — move to your next task ({rid})")
        return None
    if spec.get("lane") != "gpu" and queue_cpu:
        queue_cpu_smoke(flags, rid, spec, smoke_s)
        return None
    regions = smoke_regions(spec.get("lane"), spec.get("regions") or "mi210_0,184-191", flags)
    if not regions:
        queue_cpu_smoke(flags, rid, spec, smoke_s, " (no free cores right now)")
        return None
    v, msg = run_smoke(flags, rid, regions, smoke_s)
    if v == "PASS":
        print(f"SMOKE PASS {rid} on {regions}: {msg}")
        rf.supersede(flags, row)   # refinement 5: a PASSed successor withdraws its predecessors
        if file_if_complete(flags, rid, row):
            return None
        return row
    if v == "WAIT" and spec.get("lane") != "gpu":   # waiting for a lock / a held host is never a failure: the keeper retries
        queue_cpu_smoke(flags, rid, spec, smoke_s, f" (WAIT: {msg[:160]})")
        return None
    # operator 2026-11-03 design goal: cause + fix in ONE line; the long log stays on disk behind a path
    raise rf.Refused(f"smoke {v} for {rid} on {regions}: {msg} (log: {os.path.join(rf.dry_dir(flags, rid), 'launcher.out')}; "
                     f"the row is not granted until a smoke PASSes)")


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
    row = rf.load_json(rf.ready_path(flags, rid)) or rf.load_json(unpublished_path(flags, rid))
    rf.need(row and row.get("schema") == rf.SCHEMA, f"no epyc.row.v3 row at ready/{rid}.json or dryrun/{rid}/unpublished.json")
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
    # no task re-lint here: --repair republishes a row that passed check_task_lint at publish and changes only
    # lint-derivable fields (result_path/result_format/lane/scratch_root/keep), never handoff_task
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
    ap.add_argument("--resume-complete", metavar="ROW_ID", help="retry terminal filing from an unchanged prior completed PASS; no smoke rerun")
    ap.add_argument("--flags", default=rf.FLAGS)
    ap.add_argument("--run-gpu-queue", action="store_true", help="(allocator, detached) run every queued GPU smoke")
    ap.add_argument("--smoke-now", action="store_true", help="run the CPU smoke now on free cores of the keeper's snapshot "
                    "instead of queueing it for the keeper (still queued when nothing is free)")
    ap.add_argument("--run-smoke", metavar="ROW_ID", help="(allocator, detached) run ONE keeper-placed CPU smoke")
    ap.add_argument("--regions", help="with --run-smoke: the cpus the keeper assigned")
    a = ap.parse_args(argv)
    if a.run_smoke:
        rf.need(a.regions, "--run-smoke needs --regions")
        v = run_queued_smoke(a.flags, a.run_smoke, a.regions)
        return 0 if v in ("PASS", "WAIT") else 1
    if a.run_gpu_queue:
        try:
            print(f"GPU-SMOKE-BATCH ran {run_gpu_queue(a.flags)}")
        finally:
            rf.release_gpu_batch(a.flags)
        return 0
    try:
        rf.need(sum(bool(x) for x in (a.spec, a.repair, a.resume_complete)) <= 1,
                "choose spec, --repair or --resume-complete")
        if a.resume_complete:
            return resume_complete(a.flags, a.resume_complete)
        if a.repair:
            rc, msg = repair(a.repair, a.flags)
            print(msg)
            return rc
        rf.need(a.spec, "spec.json or --repair <row-id> required")
        spec = rf.load_json(a.spec)
        rf.need(spec, f"{a.spec} is not a JSON object")
        if a.migrate:
            spec = rf.spec_from_legacy(spec, a.flags)
        rf.need(spec.get("estimate_s") is None or int(spec["estimate_s"]) >= MIN_ESTIMATE_S, "under 5 min: run it in your turn, not as a row")
        check_handoff(spec)
        check_task_lint(spec)
        for note in lint(spec):
            print(f"LINT {note}")
        row = publish_smoked(spec, a.flags, os.path.abspath(a.spec), queue_cpu=not a.smoke_now)
        if row:
            print(rf.published_line(row, a.flags))
        return 0
    except rf.Refused as e:
        print(f"REFUSED: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
