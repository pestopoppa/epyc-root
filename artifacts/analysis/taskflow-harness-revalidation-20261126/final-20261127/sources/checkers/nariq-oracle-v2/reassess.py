"""Qualify NARIQ's filename placement correction and regrade saved text only."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CASE = ROOT.parent / "ws58-a3b-frozen-revalidation-20261126/quality-v4/packets/NARIQ-LIBTRELLIS-MAP-1"
MAIN = ROOT / "main-comparison/runs/NARIQ-LIBTRELLIS-MAP-1/direct-1"
CPU = ROOT / "coverage/legacy-boundary-v3/runs/boundary-01/units/cpu-NARIQ-LIBTRELLIS-MAP-1-off-recommended-numa-resume-1-boundary"
DOC = Path("docs/research/exl3-4-gfx90a-libtrellis-design.md")
V1_SHA = "7dfb632558142af85b2d2395a17781bf81f7aa16899f73a91b2bdb9b698ff795"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ref(path, expected=None):
    seen = digest(path)
    if expected is not None and seen != expected:
        raise RuntimeError(f"pinned input changed: {path}")
    return {"path": str(path), "sha256": seen}


def load(path):
    return json.loads(path.read_bytes())


def run(oracle, lane, rc, witness=None):
    result = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)], timeout=10,
                            capture_output=True)
    diagnostic = result.stderr.decode().splitlines()[-1:] or None
    assert result.returncode == rc, (oracle, lane, diagnostic)
    if witness:
        assert diagnostic and witness in diagnostic[-1], (oracle, diagnostic)
    return {"rc": result.returncode, "diagnostic": diagnostic,
            "oracle_sha256": digest(oracle), "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()}


def original_refs(run_dir, receipt, patch):
    return {
        "receipt": ref(receipt), "patch": ref(patch),
        "stdout": ref(run_dir / "oracle.stdout.log"), "stderr": ref(run_dir / "oracle.stderr.log"),
    }


def main():
    old, new = CASE / "oracle.py", HERE / "oracle.py"
    case = load(CASE / "case.json")
    assert case["oracle_sha256"] == V1_SHA
    source = old.read_text()
    expected = source.replace('("test_runtime.hip", "lane", "offset", "group")',
                              '("lane", "offset", "group")')
    marker = "for heading, terms in required.items():"
    expected = expected.replace(marker, 'assert "test_runtime.hip" in text.lower(), ("document", "test_runtime.hip")\n' + marker)
    if new.read_text() != expected or digest(old) != V1_SHA:
        raise RuntimeError("oracle correction changed more than filename placement")

    main_measurement = MAIN / "measurement.json"
    main = load(main_measurement)
    main_doc = MAIN / "lane" / DOC
    assert main["path_scope_pass"] and main["final_changes"] == [str(DOC)]
    assert main["oracle"]["rc"] == 0 and main["oracle"]["oracle_sha256"] == V1_SHA
    main_input = ref(main_doc, main["oracle"]["checked_candidate_files"][str(DOC)]["sha256"])
    main_refs = original_refs(MAIN, main_measurement, MAIN / "delta.patch")
    assert main_refs["patch"]["sha256"] == main["patch_sha256"]
    for stream in ("stdout", "stderr"):
        assert main_refs[stream]["sha256"] == main["oracle"][f"{stream}_sha256"]

    cpu_result = CPU / "RESULT.json"
    cpu = load(cpu_result)
    cpu_lane = CPU / "independent/work"
    cpu_doc = cpu_lane / DOC
    assert cpu["status"] == "oracle_fail" and cpu["terminal_at"] > 0
    assert cpu["oracle"]["rc"] == 1 and cpu["oracle"]["oracle_sha256"] == V1_SHA
    assert not cpu["outside_scope"] and not cpu["unsafe_paths"] and set(cpu["changed_files"]) == {str(DOC)}
    cpu_input = ref(cpu_doc, cpu["changed_files"][str(DOC)]["sha256"])
    cpu_res = {
        "receipt": ref(cpu_result),
        "patch": ref(CPU / "independent/candidate.patch", cpu["patch_sha256"]),
        "stdout": ref(CPU / "ORACLE.stdout.log", cpu["oracle"]["stdout_sha256"]),
        "stderr": ref(CPU / "ORACLE.stderr.log", cpu["oracle"]["stderr_sha256"]),
    }
    assert (CPU / "ORACLE.stderr.log").read_text().endswith(
        "AssertionError: ('Harness coverage', 'test_runtime.hip')\n")

    cpu_text = cpu_doc.read_text()
    sections = dict(re.findall(r"(?ms)^## ([^\n]+)\n(.*?)(?=^## |\Z)", cpu_text))
    assert "test_runtime.hip" not in sections["Harness coverage"].lower()
    assert "test_runtime.hip" in sections["Wave64 MFMA"].lower()
    rows = [
        {"id": "main-direct", "candidate": main_input, "original_retained": main_refs,
         "v1_replay": run(old, MAIN / "lane", 0), "v2": run(new, MAIN / "lane", 0)},
        {"id": cpu["id"], "candidate": cpu_input, "original_retained": cpu_res,
         "v1_replay": run(old, cpu_lane, 1, "('Harness coverage', 'test_runtime.hip')"),
         "v2": run(new, cpu_lane, 0), "classification": "structural pass pending semantic review"},
    ]

    controls = [
        ("wrong-harness-filename", cpu_text.replace("test_runtime.hip", "test_runtime.cpp"),
         "('document', 'test_runtime.hip')"),
        ("missing-harness-filename", cpu_text.replace("`test_runtime.hip`", "the local harness"),
         "('document', 'test_runtime.hip')"),
        ("empty-harness-coverage", cpu_text.replace("## Harness coverage\n" + sections["Harness coverage"],
                                                   "## Harness coverage\n"),
         "('Harness coverage', 'lane')"),
        ("wrong-harness-pin", cpu_text.replace("dd090a874c22be58e09b18fc1fc86da7b46b1d85", "0" * 40),
         "unbound local harness source"),
    ]
    with TemporaryDirectory(prefix="text-controls-", dir=HERE) as scratch:
        lane = Path(scratch)
        doc = lane / DOC
        doc.parent.mkdir(parents=True)
        for name, text, witness in controls:
            assert text != cpu_text
            doc.write_text(text)
            rows.append({"id": name, "control_document_sha256": digest(doc), "v2": run(new, lane, 1, witness)})
    for references in (main_refs, cpu_res, {"main": main_input, "cpu": cpu_input}):
        for source_ref in references.values():
            ref(Path(source_ref["path"]), source_ref["sha256"])

    record = {
        "case": "NARIQ-LIBTRELLIS-MAP-1", "schema": "taskflow.nariq-structural-acceptance.v2",
        "brief": ref(CASE / "prompt.md"), "case_spec": ref(CASE / "case.json"),
        "old_oracle": ref(old, V1_SHA), "new_oracle": ref(new), "assessments": rows,
        "change": "Recognize the existing case-insensitive test_runtime.hip filename anywhere in the document. Preserve lane, offset and grouping terms in Harness coverage, both revision pins, all sections, all other required terms and the LDS ceiling check.",
        "reason": "The pinned brief asks the note to use test_runtime.hip for the coverage analysis. It gives headings and source requirements and does not assign the filename reference to a specific heading.",
        "disposition": "CPU result is structurally eligible for semantic review under V2. The V1 placement diagnostic is not an objective model failure.",
        "original_grades_preserved": True, "semantic_review_done": False, "model_calls": 0,
    }
    with (HERE / "REASSESSMENT.json").open("x") as handle:
        handle.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({row["id"]: row["v2"]["rc"] for row in rows}))


if __name__ == "__main__":
    main()
