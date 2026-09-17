"""Regenerate the VB-AP53-RATE and SC83 fixtures with the REAL orchestrator writers.

The fixtures here are producer output, not hand-written imitations. Regenerate them
after a writer schema change:

    EPYC_ORCHESTRATOR_ROOT=<orchestrator checkout> \\
        <orchestrator venv>/bin/python tests/vidya/fixtures/vb_writers/generate.py

Writers used: ``scripts/autopilot/reproposal_rate.py`` (VB-AP53-RATE) and
``src/proactive_delegation/false_accept_record.py`` (SC83). The generator touches no
live journal: the journal directory recorded in the rows is a fixed locator, and
source identities are passed in rather than read from disk.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ORCH = Path(os.environ.get("EPYC_ORCHESTRATOR_ROOT", "/mnt/raid0/llm/epyc-orchestrator"))
sys.path[:0] = [str(ORCH), str(ORCH / "scripts" / "autopilot")]

import reproposal_rate as rr  # noqa: E402
from src.proactive_delegation import false_accept_record as far  # noqa: E402
from src.proactive_delegation import review_envelope as rev  # noqa: E402

JOURNAL_DIR = Path("/mnt/raid0/llm/epyc-orchestrator/orchestration")
FA_OUT = Path("/mnt/raid0/llm/epyc-orchestrator/data/reviewer_eval/false_accept_runs.jsonl")
SOURCES = {"journal_dir": str(JOURNAL_DIR),
           "journal_shards": [{"path": str(JOURNAL_DIR / "autopilot_journal.jsonl"),
                               "bytes": 1000, "prefix_sha256": "c" * 64}],
           "rejected_mutation_ledger": {"path": str(JOURNAL_DIR / "autopilot_rejected_mutations.jsonl"),
                               "bytes": 400, "prefix_sha256": "d" * 64}}
FLAG = {"type": "structural_experiment", "flags": {"user_modeling": True}}
FAIL = "VIOLATIONS:\n  - Quality floor violation\n"


def _row(tid, action, **over):
    base = dict(trial_id=tid, config_snapshot=dict(action), failure_analysis="",
                deficiency_category="", outcome_status="ok", pareto_status="dominated",
                bug_corrupted_by="", keep_revert_decision="", eval_details={})
    base.update(over)
    return SimpleNamespace(**base)


def _stable(line: dict) -> dict:
    """Pin timestamps so regeneration is byte-stable; re-derive every self-hash."""
    line = json.loads(json.dumps(line))
    stamp = "2026-09-16T12:00:00+00:00"
    line["written_at"] = stamp
    line["counts"]["window_closed_at"] = stamp
    for row in line["belief_measurements"]:
        row["date"] = stamp
        row["extra"]["row_sha256"] = rr.row_digest(row)
    line.pop("line_sha256", None)
    line["line_sha256"] = rr._sha(rr._canon(line))
    return line


def ap53() -> None:
    history = [_row(0, FLAG, failure_analysis=FAIL)] + [
        _row(t, FLAG if t % 2 == 0 else {"type": "seed_batch"}) for t in range(1, 12)]
    ledger = [{"trial_id": 5, "diff_sha256": "a", "rejecting_gate": "safety"},
              {"trial_id": 6, "diff_sha256": "a", "rejecting_gate": "safety"}]
    fold = rr.fold_windows(history, window=4)
    dsha = rr.definition_sha256()
    kw = dict(fold=fold, ledger_records=ledger, sources=SOURCES, definition_sha=dsha)
    armed = {"schema": rr.SCHEMA, "record": "armed", "writer": rr.WRITER_ID,
             "armed_at": "2026-09-16T11:00:00+00:00", "armed_from_trial": 4,
             "window_size": 4, "last_trial_at_arming": 0, "reason": "fixture"}
    prospective = [armed] + [_stable(rr.window_line(history, JOURNAL_DIR, start=s, window=4,
                                                    armed_from=4, **kw)) for s in (4, 8)]
    retro = [_stable(rr.window_line(history, JOURNAL_DIR, start=0, window=4, armed_from=4,
                                    retrospective=True, **kw))]
    (HERE / rr.RATE_FILENAME).write_text("".join(rr._canon(x) + "\n" for x in prospective))
    (HERE / rr.RETROSPECTIVE_FILENAME).write_text("".join(rr._canon(x) + "\n" for x in retro))


def _ann(aid, status, **over):
    ann = {"schema_version": "1.0.0", "annotation_id": aid, "corpus_id": "secreview-gold-v1",
           "subject": {"ref": "repo@abc123", "content_hash": "sha256:" + "a" * 64,
                       "file": "src/app.py", "line_start": 10, "line_end": 12},
           "finding": {"title": "SQL built by string concatenation", "category": "OWASP-A03",
                       "cwes": ["CWE-89"]},
           "status": status, "origin": "human",
           "annotated_by": [{"annotator": "operator", "kind": "human"}],
           "gold": {"executable_oracle": None,
                    "reasoning_label": {"verdict": status, "rationale": "by hand"}},
           "needs_arbitration": False}
    if status == "invalid":
        ann["invalid_reason"] = "constant input; no attacker-controlled data reaches the sink"
    else:
        ann["criticality"] = "must"
    ann.update(over)
    return ann


def _binding(aid, **over):
    from dataclasses import replace
    b = rev.ReviewBinding(
        source_hash=rev.content_hash(f"s-{aid}"), source_version="v1",
        candidate_hash=rev.content_hash(f"c-{aid}"), candidate_version="v1",
        reviewer_model="Qwen3.6-27B", reviewer_quant="Q4_K_M",
        prompt_bundle_hash=rev.content_hash("bundle"), pipeline_version="p1",
        review_schema_version="1.0.0")
    return replace(b, **over)


def _verdict(aid, endorse, b=None):
    b = b or _binding(aid)
    body = rev.sign_review(b, {"verdict": "endorse" if endorse else "reject"})
    env = rev.build_envelope(envelope_id=f"rev-{aid}", binding=b, signed_body=body,
                             validation_status="valid", created_at="2026-09-16T10:00:00+00:00")
    return {"annotation_id": aid, "envelope": env, "signed_body": body}


def write_fa_inputs(tmp: Path, verdicts) -> dict:
    corpus = [_ann("v0", "valid"), _ann("d0", "invalid"), _ann("d1", "invalid"),
              _ann("d2", "invalid"), _ann("d-arb", "invalid", needs_arbitration=True)]
    ids = [a["annotation_id"] for a in corpus]
    paths = {"corpus_path": tmp / "corpus.jsonl", "verdicts_path": tmp / "verdicts.jsonl",
             "bindings_path": tmp / "bindings.json"}
    paths["corpus_path"].write_text("".join(json.dumps(a) + "\n" for a in corpus))
    paths["verdicts_path"].write_text("".join(json.dumps(v) + "\n" for v in verdicts))
    paths["bindings_path"].write_text(json.dumps({i: _binding(i).as_schema() for i in ids}))
    return paths


def sc83() -> None:
    stale = _binding("d2", source_version="v0", source_hash=rev.content_hash("old"))
    lines = []
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a"
        b = Path(td) / "b"
        a.mkdir()
        b.mkdir()
        pa = write_fa_inputs(a, [_verdict("d0", True), _verdict("d1", False),
                                 _verdict("d2", True, stale)])
        lines.append(far.build_run_line(run_id="fixture-r1", out=FA_OUT,
                                        scored_at="2026-09-16T12:00:00+00:00", **pa))
        pb = write_fa_inputs(b, [_verdict("d2", True, stale)])
        lines.append(far.build_run_line(run_id="fixture-r2", out=FA_OUT,
                                        scored_at="2026-09-16T12:05:00+00:00", **pb))
        c = Path(td) / "c"
        c.mkdir()
        arb_stale = _binding("d-arb", source_version="v0", source_hash=rev.content_hash("old"))
        pc = write_fa_inputs(c, [_verdict("d0", True), _verdict("d1", False),
                                 _verdict("d-arb", True, arb_stale)])
        lines.append(far.build_run_line(run_id="fixture-r3", out=FA_OUT,
                                        scored_at="2026-09-16T12:10:00+00:00", **pc))
    (HERE / "false_accept_runs.jsonl").write_text(
        "".join(far._canon(x) + "\n" for x in lines))


if __name__ == "__main__":
    ap53()
    sc83()
    print("regenerated", sorted(p.name for p in HERE.glob("*.jsonl")))
