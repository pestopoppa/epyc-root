"""Compare the original and exact-event oracles, writing only this assessment lane."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from oracle import DOC, LOG, LOG_SHA, PROBE, PROBE_SHA

HERE = Path(__file__).resolve().parent
COMPARE = HERE.parent / "main-comparison"
FROZEN = HERE.parent.parent / "ws58-a3b-frozen-revalidation-20261126"
MAIN = COMPARE / "runs/PFXC-A3/direct-1"
GPU = FROZEN / "quality-runs/cache-safe-01/units/gpu-PFXC-A3-on-coding"
ORIGINAL = COMPARE / "cases/PFXC-A3/oracle.py"
REVISED = HERE / "oracle.py"
ORIG_SHA = "c24d7895ec3157595cebcb24a4c7a930ee4792358a5598745142f93ddc059d1e"
VERSION = "pfxc.exact-events.v4"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def render(groups):
    header = "| " + " | ".join(["Order", "Log line", "Entry MiB"] * len(groups)) + " |\n"
    header += "| " + " | ".join(["---", "---", "---:"] * len(groups)) + " |\n"
    for y in range(max(map(len, groups))):
        cells = [field for group in groups
                 for field in (group[y] if y < len(group) else ("", "", ""))]
        header += "| " + " | ".join(map(str, cells)) + " |\n"
    return header


def grade(case, label, source, expected_old, expected_new, diagnostic=""):
    out = HERE / "controls" / case
    lane = out / "lane"
    target = lane / DOC
    target.parent.mkdir(parents=True)
    if source is not None:
        target.write_bytes(source)
    revision = {}
    for name, oracle, expected in (("original", ORIGINAL, expected_old), ("revised", REVISED, expected_new)):
        proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)],
                              capture_output=True, timeout=30)
        logs = {}
        for kind, data in (("stdout", proc.stdout), ("stderr", proc.stderr)):
            log = out / f"{name}.{kind}.log"
            log.write_bytes(data)
            logs[f"{kind}_sha256"] = sha(log)
        if expected is not None:
            assert proc.returncode == expected, (case, name, proc.returncode, proc.stderr.decode())
        if name == "revised" and diagnostic:
            assert diagnostic in proc.stderr.decode(), (case, proc.stderr.decode())
        revision[name] = {"oracle_sha256": sha(oracle), "rc": proc.returncode, **logs}
    result = {"id": case, "purpose": label, "candidate_sha256": sha(target) if target.exists() else None,
              "expected_new_diagnostic": diagnostic or None, "receipt": revision}
    write(out / "RESULT.json", result)
    print(f"{case}: original={revision['original']['rc']} revised={revision['revised']['rc']}", flush=True)
    return result


def main():
    assert sha(ORIGINAL) == ORIG_SHA
    main_candidate = MAIN / "lane" / DOC
    gpu_candidate = GPU / "independent/work" / DOC
    upstream = [
        main_candidate, gpu_candidate, GPU / "sandbox/work" / DOC,
        MAIN / "oracle-result.json", GPU / "RESULT.json", GPU / "ORACLE.stderr.log",
    ]
    originals = {str(path): sha(path) for path in upstream}
    assert sha(gpu_candidate) == sha(GPU / "sandbox/work" / DOC)
    assert load(MAIN / "oracle-result.json")["checked_candidate_files"][DOC]["sha256"] == sha(main_candidate)
    assert load(GPU / "RESULT.json")["oracle"]["stderr_sha256"] == sha(GPU / "ORACLE.stderr.log")
    assert load(MAIN / "oracle-result.json")["oracle_sha256"] == load(GPU / "RESULT.json")["oracle"]["oracle_sha256"] == ORIG_SHA
    text = main_candidate.read_text()
    sample = re.search(r"(?m)^\| Order \| Log line \| Entry MiB \|\n(?:^\|[^\n]*\|\n)+", text)
    assert sample, "accepted direct document table moved"
    rows = [[int(order), int(line), size] for order, line, size in re.findall(
        r"(?m)^\| (\d+) \| (\d+) \| (\d+\.\d+) \|$", sample[0])]
    assert len(rows) == 41
    original_size_section = text[text.index("## Entry sizes"):text.index("## Cache sizing")]
    assert sample[0] in original_size_section

    def doc(*groups):
        return (text[:sample.start()] + render(groups) + text[sample.end():]).encode()

    def clone():
        return [row.copy() for row in rows]

    middle = clone()
    middle[20], middle[21] = middle[21], middle[20]
    middle[20][0], middle[21][0] = 21, 22
    wrong_line = clone()
    wrong_line[20][1] = 9999
    wrong_size = clone()
    wrong_size[20][2] = "973.458"
    duplicate_number = clone()
    duplicate_number[20][0] = 20
    duplicate_instead = clone()
    duplicate_instead[20][1:] = duplicate_instead[19][1:]
    tail = [[42 + ix, line, size] for ix, (_, line, size) in enumerate(rows[17:20])]
    receipts = [
        grade("historical-main-direct", "Original accepted direct candidate, byte preserved", main_candidate.read_bytes(), 0, 0),
        grade("valid-side-by-side", "Same 41 events across two explicit ordinal groups", doc(rows[:21], rows[21:]), 1, 0),
        grade("historical-gpu-on", "Original GPU ON artifact has 44 events and repeats three lines",
              gpu_candidate.read_bytes(), 1, 1, "expected 41 source events exactly once, found 44; duplicate source lines: 1314, 1330, 1429"),
        grade("linear-duplicate-44", "Original regex wrongly accepts a 44-row subsequence",
              doc(rows + tail), 0, 1, "expected 41 source events exactly once, found 44; duplicate source lines: 1314, 1330, 1429"),
        grade("extra-event-42", "Original regex ignores one extra row with a distinct source line",
              doc(rows + [[42, 9999, "202.145"]]), 0, 1, "expected 41 source events exactly once, found 42"),
        grade("duplicate-instead-of-event", "41 rows alone cannot prove each event occurs once",
              doc(duplicate_instead), 1, 1, "found 41; duplicate source lines: 1429"),
        grade("missing-event", "One row removed", doc(rows[:20] + rows[21:]), 1, 1, "exactly once, found 40"),
        grade("wrong-order", "Adjacent authentic tuples assigned to the wrong event ordinals",
              doc(middle), 1, 1, "event 21: source line 1568, expected 1528"),
        grade("wrong-source-line", "Correct value at ordinal 21 with incorrect source-line attribution",
              doc(wrong_line), 0, 1, "event 21: source line 9999, expected 1528"),
        grade("wrong-size", "Correct ordinal and line with an incorrect measurement",
              doc(wrong_size), 1, 1, "event 21: size 973.458 MiB, expected 973.457 MiB"),
        grade("duplicate-ordinal", "Exact set of source lines and sizes with conflicting ordinal claims",
              doc(duplicate_number), 0, 1, "entry ordinals must cover 1–41 exactly once"),
        grade("no-output", "Original baseline has no candidate document", None, 1, 1, DOC),
        grade("missing-probe-pin", "Existing pinned-capture check still refuses a changed hash",
              text.replace(PROBE_SHA, "a" * 64).encode(), 1, 1, PROBE_SHA),
        grade("missing-eviction-log-pin", "Existing server trace hash still required",
              text.replace(LOG_SHA, "b" * 64).encode(), 1, 1, LOG_SHA),
        grade("missing-sizing-minimum", "Existing 11896 MiB sizing arithmetic still required",
              text.replace("11896", "11897").encode(), 1, 1, "11896"),
        grade("missing-np2-geometry", "Existing geometry expectation still required",
              text.replace("np2", "second slot").encode(), 1, 1, "np2"),
    ]
    assert all(sha(Path(path)) == expected for path, expected in originals.items())
    proof = {"case": "PFXC-A3", "acceptance_version": VERSION, "oracle_sha256": sha(REVISED),
             "original_oracle_sha256": ORIG_SHA, "original_results_preserved": True,
             "no_model_calls": True, "controls": receipts}
    write(HERE / "REPLAY.json", proof)
    main_result = load(HERE / "controls/historical-main-direct/RESULT.json")
    gpu_result = load(HERE / "controls/historical-gpu-on/RESULT.json")
    facts = {"version": VERSION, "case": "PFXC-A3", "oracle": REVISED.name, "oracle_sha256": sha(REVISED),
             "original_oracle_sha256": ORIG_SHA, "control_receipt": "REPLAY.json",
             "control_receipt_sha256": sha(HERE / "REPLAY.json"),
             "pinned_captures": {str(LOG): LOG_SHA, str(PROBE): PROBE_SHA},
             "original_inputs_before_after_sha256": originals,
             "saved_assessments": {"main_direct": main_result, "cache_safe_gpu_on": gpu_result},
             "observed_format_issue": "Original value-subsequence scan rejected a valid side-by-side table and accepted a linear 44-event table.",
             "correction": "Require exactly 41 pinned events with source-order values. Match explicit ordinals and source-line claims when supplied. Keep the existing trace pin, sizing and geometry checks.",
             "gpu_on_objective_failure": "Expected 41 events, found 44. Source lines 1314, 1330 and 1429 repeat. The 41-event nearest-rank p95 is rank 39.",
             "grading_scope": "Offline comparison of saved artifacts using an identical revised oracle for main and local arms."}
    write(HERE / "acceptance-migration.json", facts)
    print(f"{len(receipts)} model-free comparisons verified. Revised oracle SHA {sha(REVISED)}")


if __name__ == "__main__":
    main()
