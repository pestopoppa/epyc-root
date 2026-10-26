"""Original subprocess execution and hostile carrier cases; no live inference."""
from pathlib import Path
import json
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from scripts.ci import native_conformance as nc
from adapters import ci_conformance as adapter
from claim_tuple import ProjectionError, grade


@pytest.fixture
def capture(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    source = repo / "fixture.py"
    source.write_text("# reviewed selected fixture\n")
    subprocess.run(["git", "-C", str(repo), "add", "fixture.py"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    sequence = 0

    def run(*, status="passed", exit_code=0, xml=None, generated_output_paths=None, generated_code=""):
        nonlocal sequence
        sequence += 1
        junit = repo / f"out-{sequence}.xml"
        output = tmp_path / f"capture-{sequence}"
        if xml is None:
            child = "" if status == "passed" else f"<{status}/>"
            xml = (f'<testsuites><testsuite tests="1" failures="{int(status == "failure")}" '
                   f'errors="{int(status == "error")}" skipped="{int(status == "skipped")}">'
                   f'<testcase classname="selected.fixture" name="case_one" time="0.1">'
                   f'{child}</testcase></testsuite></testsuites>')
        generated_clause = f"{generated_code}; " if generated_code else ""
        script = ("from pathlib import Path; import sys; print('original fixture output'); "
                  f"{generated_clause}"
                  f"Path({str(junit)!r}).write_text({xml!r}); sys.exit({exit_code})")
        record = nc.capture_fixture_execution(argv=[sys.executable, "-c", script], cwd=repo,
            junit=junit, output=output, repositories={"tested": repo},
            read_paths=[source, Path(nc.__file__)], selections=["selected.fixture::case_one"],
            generated_output_paths=generated_output_paths)
        return output, record

    return run


def test_original_execution_projects_only_bounded_boolean(capture):
    output, record = capture()
    rows = adapter.native_rows(output / "receipt.json")
    claim = adapter.project_ci_conformance(rows[0])
    assert claim.value is True
    assert claim.metric == "fixture_execution_conformant"
    assert claim.reps is None and claim.protocol_id == ""
    assert claim.attestation_path == claim.attestation_sha256 == ""
    assert grade(claim)[:2] == ("Judged", "Located")
    assert claim.claim == claim.decided_proposition == record["decided_proposition"]
    assert record["summary"]["counts"] == dict(passed=1, failure=0, error=0, skipped=0, collected=1, executed=1)
    assert record["exclusions"] == nc.EXCLUSIONS
    assert nc.regular_bytes(output / "command.log") == b"original fixture output\n"
    assert "generated_output_paths" not in record
    request = json.loads((output / record["request"]["name"]).read_bytes())
    assert "generated_output_paths" not in request and "generated_outputs" not in record


def test_generated_outputs_are_captured_in_declared_order(capture):
    declared = ["reports/first.json", "reports/second.json"]
    code = ("Path('reports').mkdir(); Path('reports/first.json').write_bytes(b'first\\x00bytes'); "
            "Path('reports/second.json').write_bytes(b'second-bytes')")
    output, record = capture(generated_output_paths=declared, generated_code=code)
    assert record["fixture_execution_conformant"] is True
    assert [item["path"] for item in record["generated_outputs"]] == declared
    assert [nc.regular_bytes(output / item["artifact"]["name"]) for item in record["generated_outputs"]] == [
        b"first\x00bytes", b"second-bytes"]
    native = adapter.native_rows(output / "receipt.json")[0]
    claim = adapter.project_ci_conformance(native)
    assert native["record"]["generated_output_paths"] == declared
    assert claim.value is True and claim.source_class == "verifier"
    assert claim.claim == claim.decided_proposition == record["decided_proposition"]
    assert grade(claim)[:2] == ("Judged", "Located")
    assert "generated_outputs" not in claim.extra


def test_generated_output_tamper_refused(capture):
    output, record = capture(generated_output_paths=["result.bin"],
                             generated_code="Path('result.bin').write_bytes(b'original')")
    pin = record["generated_outputs"][0]["artifact"]
    (output / pin["name"]).write_bytes(b"tampered")
    with pytest.raises(ProjectionError, match="generated output artifact digest mismatch"):
        adapter.native_rows(output / "receipt.json")


def test_failed_execution_with_generated_output_projects_original_false_finding(capture):
    output, record = capture(status="failure", exit_code=1,
        generated_output_paths=["result.bin"],
        generated_code="Path('result.bin').write_bytes(b'failure-artifact')")
    native = adapter.native_rows(output / "receipt.json")[0]
    claim = adapter.project_ci_conformance(native)
    assert record["fixture_execution_conformant"] is False and claim.value is False
    assert claim.decided_proposition == record["decided_proposition"]
    assert "command exited zero: false" in claim.decided_proposition
    assert grade(claim)[0] == "Judged"
    assert "generated_outputs" not in claim.extra


def test_resealed_request_mutation_cannot_relabel_generated_outputs(capture):
    output, record = capture(generated_output_paths=["first.bin", "second.bin"],
        generated_code="Path('first.bin').write_bytes(b'1'); Path('second.bin').write_bytes(b'2')")
    request_path = output / record["request"]["name"]
    request = json.loads(request_path.read_bytes())
    request["generated_output_paths"] = ["second.bin", "first.bin"]
    record["generated_output_paths"] = ["second.bin", "first.bin"]
    request_bytes = nc.canonical(request)
    request_path.write_bytes(request_bytes)
    record["request"]["sha256"] = nc.digest(request_bytes)
    record.pop("receipt_sha256")
    record["receipt_sha256"] = nc.digest(nc.canonical(record))
    (output / "receipt.json").write_bytes(nc.canonical(record))
    with pytest.raises(ProjectionError, match="generated output attachments differ from declaration order"):
        adapter.native_rows(output / "receipt.json")


@pytest.mark.parametrize("paths", [["repeat.bin", "repeat.bin"], ["../escape.bin"], [""], ["."]])
def test_invalid_generated_output_paths_refused_before_launch(capture, monkeypatch, paths):
    def unexpected_launch(*args, **kwargs):
        raise AssertionError("invalid output declaration launched a subprocess")
    monkeypatch.setattr(nc.subprocess, "Popen", unexpected_launch)
    with pytest.raises(ValueError, match="generated output"):
        capture(generated_output_paths=paths)


def test_preexisting_generated_output_refused_before_launch(capture, monkeypatch, tmp_path):
    existing = tmp_path / "repo" / "already.bin"
    existing.write_bytes(b"prior-run")
    def unexpected_launch(*args, **kwargs):
        raise AssertionError("pre-existing output launched a subprocess")
    monkeypatch.setattr(nc.subprocess, "Popen", unexpected_launch)
    with pytest.raises(ValueError, match="already exists"):
        capture(generated_output_paths=["already.bin"])


def test_generated_output_readset_collision_refused_before_launch(capture, monkeypatch):
    def unexpected_launch(*args, **kwargs):
        raise AssertionError("readset collision launched a subprocess")
    monkeypatch.setattr(nc.subprocess, "Popen", unexpected_launch)
    with pytest.raises(ValueError, match="collides with JUnit or declared readset"):
        capture(generated_output_paths=["fixture.py"])


def test_generated_output_parent_symlink_escape_refused_before_launch(capture, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    (repo / "escape").symlink_to(tmp_path, target_is_directory=True)
    def unexpected_launch(*args, **kwargs):
        raise AssertionError("escaping parent launched a subprocess")
    monkeypatch.setattr(nc.subprocess, "Popen", unexpected_launch)
    with pytest.raises(ValueError, match="parent escapes"):
        capture(generated_output_paths=["escape/output.bin"])


def test_missing_generated_output_is_diagnostic_without_tuple(capture):
    output, record = capture(generated_output_paths=["missing.bin"])
    assert record["fixture_execution_conformant"] is None
    assert "No such file" in record["diagnostic"]
    assert record["generated_outputs"] == []
    assert adapter.native_rows(output / "receipt.json") == ()


def test_generated_output_fifo_is_diagnostic_without_tuple(capture):
    output, record = capture(generated_output_paths=["result.fifo"],
        generated_code="import os; os.mkfifo('result.fifo')")
    assert record["fixture_execution_conformant"] is None
    assert "regular file" in record["diagnostic"]
    assert adapter.native_rows(output / "receipt.json") == ()


def test_generated_output_leaf_symlink_is_diagnostic_without_tuple(capture):
    output, record = capture(generated_output_paths=["result.link"],
        generated_code="Path('outside.bin').write_bytes(b'data'); Path('result.link').symlink_to('outside.bin')")
    assert record["fixture_execution_conformant"] is None
    assert record["generated_outputs"] == []
    assert adapter.native_rows(output / "receipt.json") == ()


def test_partial_generated_outputs_are_retained_only_as_diagnostic(capture):
    output, record = capture(generated_output_paths=["first.bin", "missing.bin"],
        generated_code="Path('first.bin').write_bytes(b'first')")
    assert record["fixture_execution_conformant"] is None
    assert [item["path"] for item in record["generated_outputs"]] == ["first.bin"]
    assert nc.regular_bytes(output / record["generated_outputs"][0]["artifact"]["name"]) == b"first"
    assert adapter.native_rows(output / "receipt.json") == ()


def test_resealed_attachment_hole_is_refused(capture):
    output, record = capture(generated_output_paths=["first.bin", "second.bin", "third.bin"],
        generated_code=("Path('first.bin').write_bytes(b'1'); Path('second.bin').write_bytes(b'2'); "
                       "Path('third.bin').write_bytes(b'3')"))
    record["generated_outputs"] = [record["generated_outputs"][0], record["generated_outputs"][2]]
    record.pop("receipt_sha256")
    record["receipt_sha256"] = nc.digest(nc.canonical(record))
    (output / "receipt.json").write_bytes(nc.canonical(record))
    with pytest.raises(ProjectionError, match="generated output attachments differ from declaration order"):
        adapter.native_rows(output / "receipt.json")


def test_failed_execution_remains_false_finding(capture):
    output, record = capture(status="failure", exit_code=1)
    assert record["fixture_execution_conformant"] is False
    claim = adapter.project_ci_conformance(adapter.native_rows(output / "receipt.json")[0])
    assert claim.value is False and grade(claim)[0] == "Judged"


def test_original_receipt_ingests_through_cli_to_real_ledger(capture, tmp_path, capsys):
    import cli
    from ledger import Ledger
    output, record = capture()
    ledger = tmp_path / "ledger.jsonl"
    assert cli.main(["--ledger", str(ledger), "--json", "ingest", "ci-fixture-conformance",
                     "--path", str(output / "receipt.json"), "--as-of", record["ended_utc"]]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 1 and report["frames_emitted"] == 3
    frames = [row.frame for row in Ledger(ledger).read_all()]
    support = next(frame for frame in frames if frame["frame_type"].endswith("evidence_supports_claim/v1"))
    assert support["assertion"]["grade"] == {"Q": "Judged", "T": "Located"}
    claim = next(frame for frame in frames if frame["frame_type"].endswith("claim_proposed/v1"))
    assert claim["assertion"]["display_text"] == record["decided_proposition"]


def test_pass_with_skipped_case_describes_executed_cases_only(capture):
    xml = ('<testsuite tests="2" failures="0" errors="0" skipped="1">'
           '<testcase classname="f" name="executed"/>'
           '<testcase classname="f" name="excluded"><skipped/></testcase></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is True
    assert record["summary"]["counts"]["executed"] == 1
    assert record["summary"]["counts"]["skipped"] == 1
    assert "Skipped cases" in adapter.native_rows(output / "receipt.json")[0]["record"]["decided_proposition"]


def test_environment_capture_is_allowlisted(capture, monkeypatch):
    monkeypatch.setenv("SECRET_FIXTURE_SENTINEL", "must-not-be-persisted")
    monkeypatch.setenv("GITHUB_RUN_ID", "original-run")
    output, record = capture()
    assert record["runner"]["run_id"] == "original-run"
    assert set(record["runner"]) == {"run_id", "job", "attempt", "os", "python"}
    assert b"must-not-be-persisted" not in (output / "receipt.json").read_bytes()


@pytest.mark.parametrize("options", [
    {"status": "skipped"}, {"status": "failure"}, {"exit_code": 2},
    {"xml": "<not-junit/>"}, {"xml": "broken"},
    {"xml": '<testsuite tests="0" failures="0" errors="0" skipped="0"/>'},
    {"xml": '<testsuite tests="2" failures="0" errors="0" skipped="0"><testcase classname="f" name="x"/></testsuite>'},
    {"xml": '<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="f" name="x" time="nan"/></testsuite>'},
])
def test_invalid_or_unexecuted_cases_emit_no_tuple(capture, options):
    output, record = capture(**options)
    assert record["fixture_execution_conformant"] is None
    assert record["diagnostic"]
    assert record["decided_proposition"] == ""
    assert adapter.native_rows(output / "receipt.json") == ()


@pytest.mark.parametrize("leaf", ["execution-request.json", "command.log", "original-junit.xml", "read-000.bin"])
def test_original_sidecar_tamper_refused(capture, leaf):
    output, _ = capture()
    (output / leaf).write_bytes(b"tampered")
    with pytest.raises(ProjectionError, match="digest mismatch"):
        adapter.native_rows(output / "receipt.json")


def test_resealed_fabricated_proposition_is_refused(capture):
    output, record = capture()
    record["decided_proposition"] = "all repository behavior is correct"
    record.pop("receipt_sha256")
    record["receipt_sha256"] = nc.digest(nc.canonical(record))
    (output / "receipt.json").write_bytes(nc.canonical(record))
    with pytest.raises(ProjectionError, match="proposition contradicts"):
        adapter.native_rows(output / "receipt.json")


def test_native_mutation_after_reopen_refused(capture):
    output, _ = capture()
    native = adapter.native_rows(output / "receipt.json")[0]
    native["record"]["fixture_execution_conformant"] = False
    with pytest.raises(ProjectionError, match="changed since reopening"):
        adapter.project_ci_conformance(native)


def test_receipt_symlink_refused(capture):
    output, _ = capture()
    link = output / "linked.json"
    link.symlink_to(output / "receipt.json")
    with pytest.raises(ProjectionError):
        adapter.native_rows(link)


def test_sidecar_fifo_refused_without_blocking(capture):
    import os
    output, _ = capture()
    log = output / "command.log"
    log.unlink()
    os.mkfifo(log)
    with pytest.raises(ProjectionError, match="regular file"):
        adapter.native_rows(output / "receipt.json")


def test_runs_have_unique_native_identity(capture):
    first, _ = capture()
    second, _ = capture()
    left = adapter.project_ci_conformance(adapter.native_rows(first / "receipt.json")[0])
    right = adapter.project_ci_conformance(adapter.native_rows(second / "receipt.json")[0])
    assert left.measurement_id != right.measurement_id


def test_plain_historical_validation_is_refused_not_reconstructed(tmp_path):
    old = tmp_path / "historical.json"
    old.write_text(json.dumps({"run_id": "37273697465", "status": "passed"}))
    with pytest.raises(ProjectionError, match="not a prospective"):
        adapter.native_rows(old)


def test_existing_outputs_cannot_be_recaptured(capture):
    output, record = capture()
    with pytest.raises(ValueError, match="already exists"):
        nc.capture_fixture_execution(argv=record["argv"], cwd=record["cwd"],
            junit=Path(record["cwd"]) / "out-1.xml", output=output,
            repositories={"tested": record["cwd"]},
            read_paths=[Path(record["cwd"]) / "fixture.py"], selections=record["selections"])


def test_missing_junit_is_diagnostic(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    source = repo / "fixture"
    source.write_text("selected")
    subprocess.run(["git", "-C", str(repo), "add", "fixture"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
    record = nc.capture_fixture_execution(argv=[sys.executable, "-c", "pass"], cwd=repo,
        junit="missing.xml", output=tmp_path / "capture", repositories={"tested": repo},
        read_paths=[source], selections=["fixture"])
    assert record["fixture_execution_conformant"] is None
    assert adapter.native_rows(tmp_path / "capture" / "receipt.json") == ()


def test_collection_skip_is_separate_from_named_case_warrant(capture):
    xml = ('<testsuite tests="2" failures="0" errors="0" skipped="1">'
           '<testcase classname="f" name="executed"/>'
           '<testcase classname="" name="tests.optional">'
           '<skipped message="collection skipped">optional dependency</skipped>'
           '</testcase></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is True
    assert record["summary"]["cases"] == [dict(classname="f", name="executed", status="passed")]
    assert record["summary"]["collection_skips"] == [dict(name="tests.optional", status="skipped")]
    assert record["summary"]["counts"]["collected"] == 1
    assert "Collection-level skips are excluded" in record["decided_proposition"]
    assert adapter.native_rows(output / "receipt.json")


@pytest.mark.parametrize("node", [
    '<testcase classname="" name="tests.optional"/>',
    '<testcase classname="" name=" "><skipped message="collection skipped"/></testcase>',
    '<testcase classname="" name="tests.optional::test_x"><skipped message="collection skipped"/></testcase>',
    '<testcase classname="" name="tests.optional"><failure/></testcase>',
    '<testcase classname="f" name="x"><failure/><failure/></testcase>',
    '<testcase classname="f" name="x"><skipped/><error/></testcase>',
    '<testcase classname="f" name="x"><system-out><failure/></system-out></testcase>',
    '<testcase classname="f" name="x"/><failure/>',
])
def test_ambiguous_or_unnamed_nodes_stay_diagnostic(capture, node):
    xml = '<testsuite tests="1" failures="0" errors="0" skipped="0">' + node + '</testsuite>'
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert adapter.native_rows(output / "receipt.json") == ()


@pytest.mark.parametrize("properties", [
    '<property name="epyc.junit.excluded_passed_subtest_reports" value="6"/>',
    '<property name="epyc.junit.accounting_policy" value="unknown"/>',
    '<property name="epyc.junit.accounting_policy" value="pytest-9.0.3-passed-subtest-reports-v1"/>'
    '<property name="epyc.junit.excluded_passed_subtest_reports" value="-1"/>',
    '<property name="epyc.junit.accounting_policy" value="pytest-9.0.3-passed-subtest-reports-v1"/>'
    '<property name="epyc.junit.excluded_passed_subtest_reports" value="1.0"/>',
])
def test_malformed_subtest_metadata_refused(capture, properties):
    xml = ('<testsuite tests="1" failures="0" errors="0" skipped="0"><properties>'
           + properties + '</properties><testcase classname="f" name="x"/></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert adapter.native_rows(output / "receipt.json") == ()


def test_metadata_never_excuses_missing_testcase(capture):
    xml = ('<testsuite tests="7" failures="0" errors="0" skipped="0"><properties>'
           '<property name="epyc.junit.accounting_policy" value="pytest-9.0.3-passed-subtest-reports-v1"/>'
           '<property name="epyc.junit.excluded_passed_subtest_reports" value="6"/>'
           '</properties><testcase classname="f" name="x"/></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert record["diagnostic"] == "inconsistent JUnit suite counts"
    assert adapter.native_rows(output / "receipt.json") == ()


def test_collection_only_skip_emits_no_named_execution_tuple(capture):
    xml = ('<testsuite tests="1" failures="0" errors="0" skipped="1">'
           '<testcase classname="" name="tests.optional">'
           '<skipped message="collection skipped"/></testcase></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert adapter.native_rows(output / "receipt.json") == ()


@pytest.mark.parametrize("attribute,value", [("tests", 3), ("skipped", 0), ("failures", 1), ("errors", 1)])
def test_collection_exclusion_preserves_all_suite_count_checks(capture, attribute, value):
    counts = dict(tests=2, skipped=1, failures=0, errors=0)
    counts[attribute] = value
    attrs = " ".join(f'{key}="{count}"' for key, count in counts.items())
    xml = (f'<testsuite {attrs}><testcase classname="f" name="executed"/>'
           '<testcase classname="" name="tests.optional">'
           '<skipped message="collection skipped"/></testcase></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert record["diagnostic"] == "inconsistent JUnit suite counts"
    assert adapter.native_rows(output / "receipt.json") == ()


@pytest.mark.parametrize("classname", ["tests.foo", "tests.foo.TestClass"])
def test_collection_skip_cannot_also_have_executed_module_cases(capture, classname):
    xml = ('<testsuite tests="2" failures="0" errors="0" skipped="1">'
           f'<testcase classname="{classname}" name="executed"/>'
           '<testcase classname="" name="tests.foo">'
           '<skipped message="collection skipped"/></testcase></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert record["diagnostic"] == "collection skip conflicts with named JUnit case"
    assert adapter.native_rows(output / "receipt.json") == ()


def test_duplicate_collection_skip_modules_refused(capture):
    node = ('<testcase classname="" name="tests.foo">'
            '<skipped message="collection skipped"/></testcase>')
    xml = ('<testsuite tests="3" failures="0" errors="0" skipped="2">'
           '<testcase classname="other" name="executed"/>' + node + node + '</testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert record["diagnostic"] == "duplicate JUnit case identity"
    assert adapter.native_rows(output / "receipt.json") == ()


def test_duplicate_reserved_subtest_properties_refused(capture):
    policy = '<property name="epyc.junit.accounting_policy" value="pytest-9.0.3-passed-subtest-reports-v1"/>'
    count = '<property name="epyc.junit.excluded_passed_subtest_reports" value="1"/>'
    xml = ('<testsuite tests="1" failures="0" errors="0" skipped="0"><properties>'
           + policy + count + count + '</properties>'
           '<testcase classname="f" name="x"/></testsuite>')
    output, record = capture(xml=xml)
    assert record["fixture_execution_conformant"] is None
    assert record["diagnostic"] == "invalid JUnit subtest accounting metadata"
    assert adapter.native_rows(output / "receipt.json") == ()
