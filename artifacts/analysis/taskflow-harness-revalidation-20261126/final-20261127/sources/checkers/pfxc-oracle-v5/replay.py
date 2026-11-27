"""Replay the PFXC citation-prefix correction against frozen candidate bytes."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from oracle import DOC

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / "pfxc-oracle-v4"
V4 = OLD / "oracle.py"
V5 = HERE / "oracle.py"
V4_SHA = "1e9fda8b9996a3884d53072bc339ecc36454502103a7eb7a366c4b9fdfaefc57"
V5_SHA = "0909b84252e9e717d10704bfd90f09bad631a869b8880ba6cc54a798c3929068"
OFF = "gpu-PFXC-A3-off-recommended-guidance-1"
ON = "gpu-PFXC-A3-on-coding-guidance-1"
VERSION = "pfxc.exact-events.v5"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def invoke(oracle, lane, destination, label, expected):
    proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)],
                          capture_output=True, timeout=30)
    assert proc.returncode == expected, (label, lane, proc.returncode, proc.stderr)
    (destination / f"{label}.stdout.log").write_bytes(proc.stdout)
    (destination / f"{label}.stderr.log").write_bytes(proc.stderr)
    return {"rc": proc.returncode, "checker_sha256": digest(oracle),
            "stdout_sha256": sha(proc.stdout), "stderr_sha256": sha(proc.stderr),
            "diagnostic": proc.stderr.decode().strip() or None}


def compare(name, lane, raw_rc, v4_rc, v5_rc, candidate_sha, witness=None, suite="prior-control"):
    destination = HERE / "results" / suite / name
    destination.mkdir(parents=True)
    candidate = lane / DOC
    if candidate_sha is None:
        assert not candidate.exists()
    else:
        assert digest(candidate) == candidate_sha
    v4 = invoke(V4, lane, destination, "v4", v4_rc)
    v5 = invoke(V5, lane, destination, "v5", v5_rc)
    if witness:
        assert witness in (v5["diagnostic"] or ""), (name, v5)
    if candidate_sha is not None:
        assert digest(candidate) == candidate_sha
    result = {"id": name, "candidate_sha256": candidate_sha, "raw_original_rc_preserved": raw_rc,
              "v4": v4, "v5": v5, "semantic_review": "unreviewed in this offline replay"}
    write(destination / "RESULT.json", result)
    return result


def main():
    assert digest(V4) == V4_SHA and digest(V5) == V5_SHA
    prior_source = OLD / "REPLAY.json"
    assessment_source = OLD / "assessment-03" / "REPORT.json"
    old_controls = json.loads(prior_source.read_bytes())
    assessment = json.loads(assessment_source.read_bytes())
    assert len(old_controls["controls"]) == 16
    witnesses = {path: digest(path) for path in (prior_source, assessment_source, V4)}
    retained = [
        compare(row["id"], OLD / "controls" / row["id"] / "lane",
                row["receipt"]["original"]["rc"], row["receipt"]["revised"]["rc"],
                row["receipt"]["revised"]["rc"], row["candidate_sha256"], row["expected_new_diagnostic"])
        for row in old_controls["controls"]
    ]
    saved = {
        row["id"]: compare(row["id"], OLD / "assessment-03" / row["id"] / "candidate",
                           row["original_automated_score"]["rc"], row["reassessment"]["rc"],
                           0 if row["id"] == OFF else row["reassessment"]["rc"],
                           row["candidate_sha256"], suite="saved-assessment")
        for row in assessment["graded"]
    }
    assert saved[ON]["v5"]["rc"] == saved[OFF]["v5"]["rc"] == 0
    actual = (OLD / "assessment-03" / OFF / "candidate" / DOC).read_text()
    assert actual.count("| 1 | :558 | 329.659 |") == 1
    additional = []
    mutants = {
        "prefixed-wrong-line": ("| 1 | :9999 | 329.659 |", "event 1: source line 9999, expected 558"),
        "double-colon": ("| 1 | ::558 | 329.659 |", "malformed entry table group"),
        "trailing-colon": ("| 1 | 558: | 329.659 |", "malformed entry table group"),
        "colon-range": ("| 1 | :558:559 | 329.659 |", "malformed entry table group"),
        "prefixed-ordinal": ("| :1 | :558 | 329.659 |", "malformed entry table group"),
    }
    for name, (replacement, witness) in mutants.items():
        path = HERE / "controls" / name / "lane" / DOC
        path.parent.mkdir(parents=True)
        path.write_text(actual.replace("| 1 | :558 | 329.659 |", replacement))
        additional.append(compare(name, path.parents[2], None, 1, 1, digest(path), witness, "colon-control"))
    assert all(digest(path) == before for path, before in witnesses.items())
    report = {"case": "PFXC-A3", "version": VERSION, "oracle_sha256": V5_SHA, "previous_oracle_sha256": V4_SHA,
              "preserved_v4_controls": retained, "additional_colon_negative_controls": additional,
              "saved_assessments": saved, "original_inputs_preserved": True,
              "input_report_sha256": {str(path): before for path, before in witnesses.items()},
              "model_calls": 0, "semantic_review_performed": False}
    write(HERE / "REPLAY.json", report)
    write(HERE / "acceptance-migration.json", {
        "case": "PFXC-A3", "version": VERSION, "oracle": "oracle.py", "oracle_sha256": V5_SHA,
        "previous_oracle_sha256": V4_SHA, "control_receipt": "REPLAY.json",
        "control_receipt_sha256": digest(HERE / "REPLAY.json"),
        "change": "Accept one optional leading colon only in the Markdown source-line cell. Ordinal, source-line identity, size, exact event count, trace pins, budget, and geometry checks retain v4 behavior.",
        "saved_score_summary": {row["id"]: {"candidate_sha256": row["candidate_sha256"],
           "raw_original_rc": row["raw_original_rc_preserved"], "v4_rc": row["v4"]["rc"], "v5_rc": row["v5"]["rc"]}
           for row in saved.values()},
        "semantic_review": "unreviewed in this offline replay",
    })
    print(f"{len(retained)} prior controls, {len(additional)} colon negatives, {len(saved)} saved scores verified")


if __name__ == "__main__":
    main()
