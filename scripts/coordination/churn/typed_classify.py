#!/usr/bin/env python3
"""JEV-3 (REPLACE, operator 2026-11-02): typed judgment is the churn classifier; the regex classifiers are the fallback.

Two decisions go through here:
  (a) publish_row.repair()'s dry-run FAIL class -> FailClass            (decide_fail)
  (b) handoff_sessions.work_state()'s continue|pause|done read of a BACKLOG-handoff-<slug>.md -> WorkState + StopReason
                                                                        (decide_work_state)

Typed path (NATIVE mode, local llama-server worker_fast :8102, no orchestrator API): epyc-orchestrator
``src.typed_decisions.run_typed_decisions_native`` with one CHOICE question per enum. Needs the orchestrator venv
(/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python3) when typed_decisions is not importable here.

Jev principle: asked-but-unavailable is its own state. classify_* returns ``source="unavailable"``, ``label=None`` (never
a guess) when typed_decisions cannot be imported, the server does not answer, or the answer is out of enum. decide_*
answers with the typed label when one was given (including ``unknown``) and falls back to the regex classifier ONLY
when the typed side was unavailable, recording ``source="regex-fallback"`` and the unavailable detail.

CLI (read-only):
  typed_classify.py replay [--flags DIR]    typed answered vs unavailable over dryrun/*/FAIL-*.json
  typed_classify.py fail <FAIL.json>        the decision for one record, as JSON
  typed_classify.py work-state <BACKLOG.md> [--open-boxes N]
"""
from __future__ import annotations

import argparse
import enum
import json
import os
import re
import subprocess
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_COORD = os.path.dirname(_HERE)
ORCH_ROOT = os.environ.get("TYPED_CLASSIFY_ORCH_ROOT", "/mnt/raid0/llm/epyc-orchestrator")
ROLE = os.environ.get("TYPED_CLASSIFY_ROLE", "worker_fast")   # registry role the one-token read is charged to
PORT = int(os.environ.get("TYPED_CLASSIFY_PORT", "8102"))     # worker_fast; not listening -> unavailable, zero cost
DEFAULT_FLAGS = os.environ.get("ROWFLOW_FLAGS", "/mnt/raid0/llm/tmp/compute-flags")
STATE_MAX_CHARS = 2400
TAIL_LINES = 12


class FailClass(str, enum.Enum):
    marker_result_path = "marker_result_path"          # result_path is a completion marker, not the results file
    derivable_field_missing = "derivable_field_missing"  # spec.<lane|scratch_root|keep|kind> missing
    job_rc = "job_rc"                                  # the job itself exited non-zero / was signalled before a unit
    stop_file = "stop_file"                            # unit written but the job ignored the stop file
    result_dir_path = "result_dir_path"                # results were written during the run, at another path
    unknown = "unknown"


class WorkState(str, enum.Enum):
    continue_ = "continue"
    pause = "pause"
    done = "done"


class StopReason(str, enum.Enum):
    waiting_on_own_rows = "waiting_on_own_rows"
    backlog_empty = "backlog_empty"
    no_open_boxes = "no_open_boxes"
    has_fix_tasks = "has_fix_tasks"
    has_small_tasks = "has_small_tasks"
    has_own_inference_tasks = "has_own_inference_tasks"


FAIL_DESCRIPTIONS = {
    FailClass.marker_result_path: "the declared result_path is a completion marker (*.complete/.ended/.done/FILED, /grants/, "
                                  "COMPLETE*/TERMINAL*), so no unit could ever appear there",
    FailClass.derivable_field_missing: "the spec lacks a derivable field (lane, scratch_root, keep, kind) and nothing else failed",
    FailClass.job_rc: "the job exited with a non-zero rc, was signalled, or has no ended record, before writing any unit",
    FailClass.stop_file: "a unit was written but the job kept running past the stop file (not resumable)",
    FailClass.result_dir_path: "the job wrote RESULT.json/results.jsonl during the run but at a path other than result_path",
    FailClass.unknown: "none of the above fits",
}
STOP_DESCRIPTIONS = {
    StopReason.waiting_on_own_rows: "rows of this handoff are queued/running; nothing else to do until they end",
    StopReason.backlog_empty: "the backlog has no rows and no tasks",
    StopReason.no_open_boxes: "the handoff has no open checkbox left",
    StopReason.has_fix_tasks: "blocked/needs-launcher/needs-qualification rows need fixing",
    StopReason.has_small_tasks: "non-inference tasks are listed",
    StopReason.has_own_inference_tasks: "own inference tasks still need publishing as rows",
}


# ------------------------------------------------------------------ regex classifiers (the fallback)
def _publish_row():
    sys.path.insert(0, os.path.join(_COORD, "rowflow"))
    import publish_row  # noqa: E402
    return publish_row


def heuristic_fail(fail: dict) -> tuple[FailClass, str]:
    """Exactly repair()'s class detection (publish_row.py), without touching the row or republishing."""
    pr = _publish_row()
    reason = str(fail.get("reason") or "")
    m = pr._UNIT_RE.search(reason)
    if m:
        rp = m.group(1)
        found = pr.results_written_during(fail, os.path.dirname(rp.split("*")[0]))
        if found:
            return FailClass.result_dir_path, f"results written during the run at {found}"
        if pr.is_marker(rp):
            return FailClass.marker_result_path, f"{rp} is a completion marker"
        return FailClass.unknown, "UNKNOWN-FAILURE-CLASS (no unit, path is a real results file, nothing written during the run)"
    if re.search(r"spec\.(%s) missing" % "|".join(pr.DERIVABLE), reason):
        return FailClass.derivable_field_missing, "spec.<derivable> missing"
    return FailClass.unknown, "UNKNOWN-FAILURE-CLASS (reason has no unit path)"


def _hs_regexes():
    """handoff_sessions' own compiled regexes when importable, else byte-identical copies."""
    try:
        sys.path.insert(0, _COORD)
        import handoff_sessions as hs  # noqa: E402
        return hs.ADV_RX, hs.OWN_TASK_RX
    except Exception:
        return (re.compile(r"^- \[(blocked|needs-launcher|needs-qualification)\] ", re.M),
                re.compile(r"^- \S+ L\d+ \[(cpu|gpu)\] ", re.M))


_WAITING_RX = re.compile(r"^- \[(?:qualified-armed|running)\] \S+ rank=\S+ \*\*([^*]+)\*\*", re.M)


def heuristic_work_state(backlog_text: str, open_boxes: int) -> tuple[WorkState, StopReason, str]:
    """work_state()'s non-generalist branch (handoff_sessions.py), re-run on the given text."""
    adv_rx, own_rx = _hs_regexes()
    b = backlog_text or ""
    adv = adv_rx.findall(b)
    waiting = _WAITING_RX.findall(b)
    ni = b.split("## Non-inference", 1)[1] if "## Non-inference" in b else ""
    ni = ni.split("\n## ", 1)[0]
    ntasks = len([l for l in ni.splitlines() if l.startswith("- [")])
    own = len(own_rx.findall(b))
    if adv:
        return WorkState.continue_, StopReason.has_fix_tasks, f"{len(adv)} advanceable row(s) (blocked/needs-launcher/needs-qualification)"
    if own:
        return WorkState.continue_, StopReason.has_own_inference_tasks, f"{own} own inference task(s) to publish as rows"
    if ntasks:
        return WorkState.continue_, StopReason.has_small_tasks, f"{ntasks} non-inference task(s) in the backlog"
    if waiting:
        return WorkState.pause, StopReason.waiting_on_own_rows, "waiting on row(s) " + ", ".join(waiting[:6]) + " (queued/running)"
    if open_boxes:
        return WorkState.continue_, StopReason.backlog_empty, f"{open_boxes} open box(es) in the handoff, none waiting on a row"
    return WorkState.done, StopReason.no_open_boxes, "nothing open and no rows waiting"


# ------------------------------------------------------------------ typed path
_PRIMITIVES = None


def _load_typed():
    """(Question, QuestionKind, run_typed_decisions_native, primitives). Raises on any import/config problem."""
    global _PRIMITIVES
    if ORCH_ROOT not in sys.path:
        sys.path.insert(0, ORCH_ROOT)
    from src.typed_decisions import Question, QuestionKind, run_typed_decisions_native  # noqa: E402
    if _PRIMITIVES is None:
        from src.config import get_config  # noqa: E402
        from src.llm_primitives import LLMPrimitives  # noqa: E402
        cfg = get_config()
        prim = LLMPrimitives(mock_mode=False, server_urls=dict(cfg.server_urls.as_dict()), num_slots=cfg.server.num_slots)
        if ROLE not in (getattr(prim, "_backends", None) or {}):
            raise RuntimeError(f"no LLM backend for role {ROLE!r} in the configured server URLs")
        _PRIMITIVES = prim
    return Question, QuestionKind, run_typed_decisions_native, _PRIMITIVES


def _typed_in_process(catalogue: list[dict], state: str) -> dict:
    Question, QuestionKind, run_native, prim = _load_typed()
    qs = [Question(id=q["id"], kind=QuestionKind.CHOICE, text=q["text"], options=tuple(q["options"]),
                   option_descriptions=tuple(q.get("descriptions") or ())) for q in catalogue]
    res = run_native(prim, state=state, questions=qs, role=ROLE)
    out = {d.question_id: {"value": d.value, "probabilities": dict(d.probabilities or {}), "confidence": d.confidence,
                           "mode": getattr(d, "mode", None)} for d in res.decisions}
    missing = [q["id"] for q in catalogue if q["id"] not in out]
    if missing:
        fails = "; ".join(f"{getattr(f, 'reason', '?')}: {getattr(f, 'detail', '')}" for f in (res.failures or ()))
        raise RuntimeError(f"typed failure for {missing}: {fails or 'no decision returned'}")
    return out


def _typed_importable() -> bool:
    if ORCH_ROOT not in sys.path:
        sys.path.insert(0, ORCH_ROOT)
    try:
        import src.typed_decisions  # noqa: F401
        return True
    except Exception:
        return False


def _require_listening() -> None:
    """Zero-cost unavailability: no import, no subprocess, no model call unless worker_fast accepts a TCP connect."""
    import socket
    try:
        socket.create_connection(("127.0.0.1", PORT), timeout=0.3).close()
    except OSError as exc:
        raise ConnectionError(f"{ROLE} :{PORT} not listening ({exc})")


def _typed_answers(catalogue: list[dict], state: str) -> dict:
    """{qid: {"value", "probabilities", "confidence"}} from ONE native constrained read. Raises on failure.
    catalogue items: {"id", "text", "options": [str], "descriptions": [str]}. Tests patch this seam.
    rowflow.py needs python>=3.12 while typed_decisions lives in the 3.11 orchestrator venv, so when the package is not
    importable here the read runs in a ``TYPED_CLASSIFY_PYTHON`` subprocess (this same file, `_typed-worker`, JSON over pipes)."""
    _require_listening()
    if _typed_importable():
        return _typed_in_process(catalogue, state)
    py = os.environ.get("TYPED_CLASSIFY_PYTHON", os.path.join(ORCH_ROOT, ".venv", "bin", "python3"))
    if not os.path.isfile(py) or os.path.realpath(py) == os.path.realpath(sys.executable):
        raise ImportError(f"src.typed_decisions not importable from {sys.executable} and no separate interpreter at {py}")
    proc = subprocess.run([py, "-I", os.path.abspath(__file__), "_typed-worker"], input=json.dumps({"catalogue": catalogue, "state": state}),
                          capture_output=True, text=True, timeout=float(os.environ.get("TYPED_CLASSIFY_TIMEOUT_S", "180")),
                          env={**os.environ, "TYPED_CLASSIFY_ORCH_ROOT": ORCH_ROOT, "TYPED_CLASSIFY_ROLE": ROLE, "TYPED_CLASSIFY_PORT": str(PORT)})
    try:
        reply = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    except ValueError:
        reply = {}
    if not reply.get("ok"):
        raise RuntimeError(f"typed worker ({py}) rc={proc.returncode}: {reply.get('error') or proc.stderr.strip()[-400:] or 'no reply'}")
    return reply["answers"]


def _typed_worker() -> int:
    req = json.load(sys.stdin)
    try:
        print(json.dumps({"ok": True, "answers": _typed_in_process(req["catalogue"], req["state"])}, default=str))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"[:800]}))
    return 0


def _unavailable(exc: BaseException) -> dict:
    return {"label": None, "source": "unavailable", "detail": f"{type(exc).__name__}: {exc}"[:600]}


def _to_enum(enum_cls, value):
    try:
        return enum_cls(str(value))
    except ValueError:
        raise RuntimeError(f"typed value {value!r} is not in {enum_cls.__name__} {[e.value for e in enum_cls]}")


def _fail_state(fail: dict) -> str:
    tail = fail.get("launcher_out_tail") or []
    parts = [f"dry-run FAIL of row {fail.get('id')}", f"reason: {fail.get('reason')}", f"ended: {fail.get('ended')}",
             f"first_unit_at: {fail.get('first_unit_at')}", f"fix_task: {fail.get('fix_task')}",
             "launcher.out tail:", *[str(l) for l in tail[-TAIL_LINES:]]]
    return "\n".join(parts)[:STATE_MAX_CHARS]


def classify_fail(fail_record: dict) -> dict:
    """Typed FailClass for one dryrun FAIL record. {"label": FailClass|None, "source": "typed"|"unavailable", "detail"}."""
    cat = [{"id": "fail_class", "text": "Which failure class best describes this dry-run FAIL record?",
            "options": [e.value for e in FailClass], "descriptions": [FAIL_DESCRIPTIONS[e] for e in FailClass]}]
    try:
        ans = _typed_answers(cat, _fail_state(fail_record))["fail_class"]
        label = _to_enum(FailClass, ans["value"])
    except Exception as exc:  # noqa: BLE001 - unavailable is the contract, never a guess
        return _unavailable(exc)
    return {"label": label, "source": "typed", "detail": json.dumps({"probabilities": ans["probabilities"],
                                                                     "confidence": ans["confidence"]}, default=str)}


def classify_work_state(backlog_text: str, open_boxes: int) -> dict:
    """Typed continue|pause|done + StopReason. {"label": WorkState|None, "stop_reason": StopReason|None, "source", "detail"}."""
    state = f"open checkboxes in the handoff: {int(open_boxes)}\nBACKLOG file:\n{(backlog_text or '')[:STATE_MAX_CHARS]}"
    cat = [{"id": "work_state", "text": "Should the session continue working, pause until its rows end, or is it done?",
            "options": [e.value for e in WorkState],
            "descriptions": ["there is work it can advance now", "only queued/running rows remain", "nothing open at all"]},
           {"id": "stop_reason", "text": "Which single reason best describes the backlog's state?",
            "options": [e.value for e in StopReason], "descriptions": [STOP_DESCRIPTIONS[e] for e in StopReason]}]
    try:
        ans = _typed_answers(cat, state)
        label = _to_enum(WorkState, ans["work_state"]["value"])
        reason = _to_enum(StopReason, ans["stop_reason"]["value"])
    except Exception as exc:  # noqa: BLE001
        return dict(_unavailable(exc), stop_reason=None)
    return {"label": label, "stop_reason": reason, "source": "typed",
            "detail": json.dumps({k: {"probabilities": v["probabilities"], "confidence": v["confidence"]} for k, v in ans.items()},
                                 default=str)}


# ------------------------------------------------------------------ decisions (typed first; regex only when unavailable)
def decide_fail(fail_record: dict) -> dict:
    """{"label": FailClass, "source": "typed"|"regex-fallback", "detail", "unavailable": detail|None}."""
    t = classify_fail(fail_record)
    if t["source"] == "typed":
        return dict(t, unavailable=None)
    label, detail = heuristic_fail(fail_record)
    return {"label": label, "source": "regex-fallback", "detail": detail, "unavailable": t["detail"]}


def decide_work_state(backlog_text: str, open_boxes: int) -> dict:
    """{"label": WorkState, "stop_reason": StopReason, "source": "typed"|"regex-fallback", "detail", "unavailable"}."""
    t = classify_work_state(backlog_text, open_boxes)
    if t["source"] == "typed":
        return dict(t, unavailable=None)
    label, reason, detail = heuristic_work_state(backlog_text, open_boxes)
    return {"label": label, "stop_reason": reason, "source": "regex-fallback", "detail": detail, "unavailable": t["detail"]}


# ------------------------------------------------------------------ replay (regression check, read-only)
def _fail_files(flags_dir: str) -> list[str]:
    d = os.path.join(flags_dir, "dryrun")
    out = []
    for rid in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        rd = os.path.join(d, rid)
        if os.path.isdir(rd):
            out += sorted(os.path.join(rd, f) for f in os.listdir(rd) if f.startswith("FAIL-") and f.endswith(".json"))
    return out


def replay(flags_dir: str = DEFAULT_FLAGS) -> list[dict]:
    """[{row, file, label, source, detail, unavailable}] over dryrun/*/FAIL-*.json via decide_fail. Reads only."""
    rows = []
    for p in _fail_files(flags_dir):
        row = os.path.basename(os.path.dirname(p))
        try:
            with open(p) as f:
                rec = json.load(f)
        except (OSError, ValueError) as exc:
            rows.append({"row": row, "file": p, "label": None, "source": "unreadable", "detail": str(exc), "unavailable": None})
            continue
        d = decide_fail(rec)
        rows.append({"row": row, "file": p, "label": d["label"].value, "source": d["source"], "detail": d["detail"],
                     "unavailable": d["unavailable"]})
    return rows


def format_table(rows: list[dict]) -> str:
    answered = sum(1 for r in rows if r["source"] == "typed")
    unavail = sum(1 for r in rows if r["source"] == "regex-fallback")
    lines = [f"{'row':<44} {'label':<24} source"]
    lines += [f"{r['row'][:44]:<44} {str(r['label']):<24} {r['source']}" for r in rows]
    lines.append(f"records={len(rows)} typed_answered={answered} typed_unavailable={unavail}")
    first = next((r for r in rows if r["unavailable"]), None)
    if first:
        lines.append(f"typed unavailable because: {first['unavailable'][:300]}")
    return "\n".join(lines)


def _json_default(o):
    return o.value if isinstance(o, enum.Enum) else str(o)


def main(argv=None) -> int:
    if argv is None and sys.argv[1:] == ["_typed-worker"]:
        return _typed_worker()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("replay")
    r.add_argument("--flags", default=DEFAULT_FLAGS)
    r.add_argument("--json", action="store_true")
    f = sub.add_parser("fail")
    f.add_argument("path")
    w = sub.add_parser("work-state")
    w.add_argument("path")
    w.add_argument("--open-boxes", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd == "replay":
        rows = replay(a.flags)
        print(json.dumps(rows, indent=1, default=_json_default) if a.json else format_table(rows))
        return 0
    if a.cmd == "fail":
        with open(a.path) as fh:
            rec = json.load(fh)
        print(json.dumps(decide_fail(rec), indent=1, default=_json_default))
        return 0
    with open(a.path) as fh:
        txt = fh.read()
    print(json.dumps(decide_work_state(txt, a.open_boxes), indent=1, default=_json_default))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        traceback.print_exc()
        raise SystemExit(130)
