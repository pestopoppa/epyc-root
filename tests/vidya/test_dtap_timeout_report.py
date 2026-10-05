"""Actual prospective cross-repo producer custody; no endpoint or captured code execution."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from adapters import dtap_timeout_report as adapter
from claim_tuple import ProjectionError, grade, to_frames
import cli


@pytest.fixture
def producer():
    source = os.environ.get("NI37_APP_ROOT")
    if not source:
        pytest.skip("named NI37 source-contract checkout is required; dedicated CI asserts the binding")
    root = Path(source)
    harness = root / "scripts" / "autopilot" / "evals" / "dtap"
    assert harness.is_dir(), "explicit source-contract checkout is unavailable"
    sys.path.insert(0, str(harness))
    from harness import runner
    assert Path(runner.__file__).resolve().parent == harness.resolve() / "harness"
    return runner, harness


def captured(tmp_path, producer, *, diagnostic=False):
    runner, harness = producer
    from harness.endpoint import DryRunStub
    from harness.outcomes import EndpointFailure, ToolFailure
    case = "finance-benign-trade-execution-001"
    fixture_path = harness / "fixtures" / f"{case}.done.json"
    payload = json.loads(fixture_path.read_text())

    class Fault(DryRunStub):
        def complete(self, messages, seed=0):
            if seed == 3:
                raise EndpointFailure("synthetic native typed timeout", detail={"terminal_native_timeout": True,
                    "cap_scope": "endpoint_request", "request_timeout_s": 0.125})
            raise ToolFailure("synthetic ordinary tool error")

    def factory(case_id, arm, seed):
        if diagnostic:
            raise RuntimeError("original synthetic factory refusal")
        if seed in (3, 4):
            return Fault(payload, seed=seed)
        fixture = json.loads(json.dumps(payload))
        if seed == 2:
            fixture["script"] = []
            fixture["agent_responses"] = ["No transaction executed."]
        return DryRunStub(fixture, seed=seed)

    arguments = dict(results_dir=tmp_path / "runs", native_capture_root=tmp_path / "private",
                     capture_fixture_paths=[fixture_path],
                     capture_applicability={"mode": "synthetic", "scope":
                        "synthetic-secret-body private-fixture-name.txt; controlled fault/stub cases"})
    if diagnostic:
        with pytest.raises(RuntimeError, match="original synthetic factory refusal"):
            runner.run_matrix([case], ["done"], [0], factory, **arguments)
    else:
        runner.run_matrix([case], ["done"], list(range(5)), factory, **arguments)
    return next((tmp_path / "private").glob("*/receipt.json"))


def write(path, value):
    path.write_bytes(adapter.canonical(value))


def reseal_receipt(path, record):
    record.pop("receipt_sha256", None)
    record["receipt_sha256"] = adapter.digest(adapter.canonical(record))
    write(path, record)


def reseal_terminal(path, record, terminal):
    target = path.parent / "original-terminal.json"
    write(target, terminal)
    record["terminal"]["sha256"] = adapter.digest(target.read_bytes())
    reseal_receipt(path, record)


def test_actual_original_five_unit_components_use_shared_grade_and_preserve_false_outcomes(tmp_path, producer):
    path = captured(tmp_path, producer)
    native = adapter.native_rows(path)[0]
    tup = adapter.project_dtap_timeout_report(native)
    assert grade(tup)[:2] == ("Judged", "Located")
    assert tup.value is True and tup.metric == "timeout_reporting_integrity"
    assert tup.claim == native["record"]["decided_proposition"] == adapter.PROPOSITION
    components = tup.extra["components"][0]
    assert components["overall_rate"] == 2 / 5 and components["finished_rate"] == 2 / 4
    assert components["timeout_share"] == 1 / 5 and components["judged_rate"] == 2 / 3
    assert components["other_errors"] == 1 and components["terminal_timeouts"] == 1
    originals = native["terminal"]["runs"]
    assert originals[2]["original_result"]["task_success"] is False
    assert originals[3]["original_result"]["completion_state"] == "terminal_timeout"
    assert originals[4]["original_result"]["failure"]["type"] == "tool"
    assert all("task passed" not in json.dumps(frame) for frame in to_frames(tup, as_of=tup.date, adapter_id=adapter.ADAPTER_ID, authority=adapter.AUTHORITY))
    output = os.environ.get("NI37_PROJECTION_OUTPUT")
    if output:
        proof = {"schema": "epyc.dtap.synthetic_fixture_projection.v1",
                 "scope": "one original five-unit synthetic matrix verified during this fixture command",
                 "native_receipt_file_sha256": native["receipt_sha256"],
                 "native_artifact_sha256": sorted(adapter.digest(adapter.regular(item))
                                                   for item in path.parent.iterdir()),
                 "source_sha": native["request"]["source_sha"],
                 "timeout_reporting_integrity": tup.value,
                 "decided_proposition": tup.claim, "components": components,
                 "grade": list(grade(tup)), "frames_emitted": len(to_frames(tup, as_of=tup.date, adapter_id=adapter.ADAPTER_ID, authority=adapter.AUTHORITY)),
                 "applicability_mode": "synthetic",
                 "exclusions": ["private body/filename/argv export", "live applicability",
                                "performance", "promotion", "dependency completeness"]}
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(adapter.canonical(proof))


def test_original_diagnostic_has_no_row_and_is_never_backfilled(tmp_path, producer):
    path = captured(tmp_path, producer, diagnostic=True)
    before = path.read_bytes()
    record, digest, request, terminal = adapter.read_receipt(path)
    assert record["timeout_reporting_integrity"] is None and record["decided_proposition"] == ""
    assert adapter.native_rows(path) == () and path.read_bytes() == before


@pytest.mark.parametrize("mutation", ["components", "original_result", "trace", "source",
                                      "duplicate_member", "applicability", "module_origin", "public_metadata", "renamed_archive",
                                      "missing", "symlink", "fifo", "escaped_terminal"])
def test_original_custody_and_coherent_reseal_controls_refuse(tmp_path, producer, mutation):
    path = captured(tmp_path, producer)
    record, sha, request, terminal = adapter.read_receipt(path)
    if mutation == "components":
        next(iter(terminal["components"].values()))["finished_rate"] = 1.0
        reseal_terminal(path, record, terminal)
    elif mutation == "original_result":
        terminal["runs"][2]["original_result"]["task_success"] = True
        reseal_terminal(path, record, terminal)
    elif mutation in ("trace", "missing", "symlink", "fifo"):
        target = path.parent / terminal["runs"][0]["artifact"]["name"]
        if mutation == "trace":
            target.write_bytes(target.read_bytes() + b" ")
        else:
            target.unlink()
            if mutation == "symlink":
                target.symlink_to(path)
            elif mutation == "fifo":
                os.mkfifo(target)
    elif mutation in ("source", "duplicate_member", "applicability", "module_origin", "public_metadata"):
        if mutation == "source":
            source = next(row for row in request["readset"] if row["source"].endswith("/harness/runner.py"))
            target = path.parent / source["artifact"]["name"]
            target.write_bytes(target.read_bytes() + b"\n# unreviewed producer edit\n")
            source["artifact"]["sha256"] = adapter.digest(target.read_bytes())
        elif mutation == "duplicate_member":
            request["readset"].append(request["readset"][0])
        elif mutation == "applicability":
            request["applicability"]["mode"] = "live_endpoint"
        elif mutation == "module_origin":
            request["loaded_modules"][0]["source"] = "/foreign-checkout/harness/__init__.py"
        else:
            request["exclusions"].append("private-secret-body caller-controlled-private-parent-name")
        original = path.parent / "original-request.json"
        write(original, request)
        record["request"]["sha256"] = adapter.digest(original.read_bytes())
        terminal["request"] = record["request"]
        reseal_terminal(path, record, terminal)
    elif mutation == "renamed_archive":
        destination = path.parent.with_name(uuid.uuid4().hex)
        path.parent.rename(destination)
        path = destination / "receipt.json"
    else:
        record["terminal"]["name"] = "../outside-fifo"
        os.mkfifo(path.parent.parent / "outside-fifo")
        reseal_receipt(path, record)
    with pytest.raises(ProjectionError):
        adapter.native_rows(path)


def test_cli_and_frames_never_export_native_body_or_arbitrary_names(tmp_path, producer, capsys):
    path = captured(tmp_path / "caller-controlled-private-parent-name", producer)
    native = adapter.native_rows(path)[0]
    tup = adapter.project_dtap_timeout_report(native)
    frames = to_frames(tup, as_of=tup.date, adapter_id=adapter.ADAPTER_ID, authority=adapter.AUTHORITY)
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "dtap-timeout-report",
                   "--path", str(path), "--as-of", "2026-10-06T00:00:00Z", "--dry-run"])
    output = capsys.readouterr()
    combined = output.out + output.err + json.dumps(frames)
    assert rc == 0
    assert "synthetic-secret-body" not in combined and "private-fixture-name.txt" not in combined
    assert "caller-controlled-private-parent-name" not in combined
    assert frames[0]["assertion"]["locator"] == adapter.public_locator(path)
    assert "/" not in frames[0]["assertion"]["locator"]
    report = json.loads(output.out)
    assert report["frames_emitted"] == 3 and report["dry_run"] is True
    assert not ledger.exists() or ledger.stat().st_size == 0


def test_project_reopens_original_and_refuses_mutated_in_memory_counts(tmp_path, producer):
    native = adapter.native_rows(captured(tmp_path, producer))[0]
    next(iter(native["terminal"]["components"].values()))["terminal_timeouts"] = 0
    with pytest.raises(ProjectionError, match="changed since reopening"):
        adapter.project_dtap_timeout_report(native)


@pytest.mark.parametrize("case_id,arm,secondary", [
    ("finance-benign-trade-execution-001", "done", "attack_success"),
    ("crm-malicious-direct-general-ai-restrictions-001", "compromised", "task_success"),
])
def test_original_nullable_secondary_projects_without_inventing_a_verdict(tmp_path, producer, monkeypatch,
                                                                         case_id, arm, secondary):
    runner, harness = producer
    from harness.endpoint import DryRunStub
    actual_judge = runner.JudgeApplication.run

    def source_shaped_secondary(self, responses, trajectory):
        result = actual_judge(self, responses, trajectory)
        # Synthetic original shape follows benign bare None and direct attack
        # (None, metadata) contracts; existing production coercion is untouched.
        result[secondary] = None
        return result

    monkeypatch.setattr(runner.JudgeApplication, "run", source_shaped_secondary)
    fixture = harness / "fixtures" / f"{case_id}.{arm}.json"
    runner.run_matrix([case_id], [arm], [0], lambda *args: DryRunStub(json.loads(fixture.read_text())),
                      results_dir=tmp_path / "runs", native_capture_root=tmp_path / "private",
                      capture_fixture_paths=[fixture, Path(__file__)],
                      capture_applicability={"mode": "synthetic", "scope": "source-shaped nullable secondary control"})
    path = next((tmp_path / "private").glob("*/receipt.json"))
    native = adapter.native_rows(path)[0]
    original = native["terminal"]["runs"][0]["original_result"]
    tup = adapter.project_dtap_timeout_report(native)
    assert original[secondary] is None and grade(tup)[:2] == ("Judged", "Located")
    counts = tup.extra["components"][0]
    assert counts["total"] == counts["finished_non_timeout"] == counts["judged"] == 1
    assert counts["terminal_timeouts"] == counts["other_errors"] == 0
    assert counts["primary_metric"] == ("task_success" if secondary == "attack_success" else "attack_success")
    assert counts["metric_direction"] == ("higher_better" if secondary == "attack_success" else "lower_better")


@pytest.mark.parametrize("field,value", [("task_success", None), ("task_success", "unknown"), ("attack_success", "unknown")])
def test_independent_reader_refuses_coherently_resealed_malformed_original_outcomes(tmp_path, producer, field, value):
    from harness.trace import TraceRecorder
    path = captured(tmp_path, producer)
    record, sha, request, terminal = adapter.read_receipt(path)
    row = terminal["runs"][0]
    target = path.parent / row["artifact"]["name"]
    events = [adapter.decode(line) for line in adapter.regular(target).splitlines() if line.strip()]
    recorder = TraceRecorder(target)
    for event in events[:-1]:
        if event["event"] == "run_result":
            event["payload"]["result"][field] = value
            row["original_result"] = event["payload"]["result"]
        recorder.record(event["event"], event["payload"])
    row["trace_id"] = recorder.close()
    row["artifact"]["sha256"] = adapter.digest(adapter.regular(target))
    # All outer pins and the original trace chain now agree; rejection must
    # come from native outcome applicability, not an incidental stale hash.
    reseal_terminal(path, record, terminal)
    with pytest.raises(ProjectionError):
        adapter.native_rows(path)


@pytest.mark.parametrize("state", ["refused", "missing"])
def test_cli_non_success_locations_and_reasons_do_not_export_caller_names(tmp_path, producer, capsys, state):
    sentinel = "caller-controlled-private-parent-name"
    if state == "missing":
        path = tmp_path / sentinel / "private-original-name.json"
    else:
        path = captured(tmp_path / sentinel, producer)
        record, sha, request, terminal = adapter.read_receipt(path)
        next(iter(terminal["components"].values()))["finished_rate"] = 1.0
        reseal_terminal(path, record, terminal)
    rc = cli.main(["--ledger", str(tmp_path / "ledger.jsonl"), "--json", "ingest", "dtap-timeout-report",
                   "--path", str(path), "--as-of", "2026-10-06T00:00:00Z", "--dry-run"])
    output = capsys.readouterr()
    assert rc == 0
    assert sentinel not in output.out + output.err
    assert "private-original-name.json" not in output.out + output.err
    report = json.loads(output.out)
    assert report[state] and report["frames_emitted"] == 0
