"""SC86: the HS-4 OpenCode-shell write-side hook and its strict reader.

Pinned here:

* the run-sidecar field names (the driver contract) and the per-row ``extra`` field names;
* the HS-14 column set, re-derived from recorded counts, and the absent column when nothing passed;
* refusals: no pin, no plugin or config hash, pre-hook (no run sidecar, started before the hook,
  backfilled after the fact), inconsistent counts;
* no codified protocol gives ``Judged/Located`` through the shared ladder, and a cited one reaches
  ``Witnessed/Attested``;
* locator = run, shared by every row; a tampered sidecar is inadmissible; a mutated records file
  grades DOWN;
* writer -> ``cli.py ingest opencode-shell`` -> tuple, end to end.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from adapters import opencode_shell_run as reader  # noqa: E402
from adapters import opencode_shell_run_capture as capture  # noqa: E402
from ledger import Ledger  # noqa: E402

PIN = "a1b2c3d4e5" * 4
CFG = "c" * 64
PLUGIN = "b" * 64
SUITE = "5" * 64
EMITTED = "2026-09-16T10:05:00Z"

RUN = {
    "schema": capture.RUN_SCHEMA,
    "run_id": "hs4-p04-20260917-a",
    "started_at": "2026-09-16T09:00:00Z",
    "finished_at": "2026-09-16T10:00:00Z",
    "arm_role": "BASELINE",
    "harness": {"name": "opencode", "pin": PIN},
    "plugin": {"name": "epyc-orchestrator", "sha256": PLUGIN},
    "config_sha256": CFG,
    "harness_card_version": "hs7-card-2026-09-17",
    "request_keys": {"x_memory": "off", "x_tool_mode": "client"},
    "serving": {"endpoint": "http://127.0.0.1:8000/v1", "model_role": "frontdoor",
                "build_info": "10125-0db32c06e", "enable_thinking": False},
    "task_suite": {"name": "hs14-scratch-10", "fingerprint": SUITE},
    "counts": {"tasks": 10, "trials_per_task": 3, "attempts": 30, "passed_attempts": 12,
               "input_tokens": 600000, "cached_prompt_tokens": 450000},
    "records_file": "attempts.jsonl",
}


def make_run(root: Path, run: dict | None = None, name: str = "run-a") -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "attempts.jsonl").write_text(json.dumps({"task": "t0", "trial": 0, "passed": True}) + "\n")
    (d / capture.RUN_SIDECAR_NAME).write_text(json.dumps(run or RUN))
    return d


def write_sidecar(run_dir: Path, **kw) -> Path:
    kw.setdefault("emitted_at", EMITTED)
    return capture.write_belief_measurements(run_dir, producer="hs4_shell_driver.py", **kw)


def _tuples(run_dir: Path):
    return [reader.project(n) for n in reader.native_rows(run_dir)]


def _rows(sidecar: Path) -> list[dict]:
    return [json.loads(x) for x in sidecar.read_text().splitlines() if x.strip()]


def _variant(**changes) -> dict:
    run = copy.deepcopy(RUN)
    for dotted, value in changes.items():
        *parents, leaf = dotted.split("__")
        target = run
        for key in parents:
            target = target[key]
        if value is _DROP:
            del target[leaf]
        else:
            target[leaf] = value
    return run


_DROP = object()


# --- schema pins -------------------------------------------------------------------------------

def test_run_sidecar_field_names_are_pinned():
    assert capture.RUN_SIDECAR_FIELDS == {
        "": ("schema", "run_id", "started_at", "finished_at", "arm_role", "harness", "plugin",
             "config_sha256", "harness_card_version", "request_keys", "serving", "task_suite",
             "counts", "records_file"),
        "harness": ("name", "pin"),
        "plugin": ("name", "sha256"),
        "request_keys": ("x_memory", "x_tool_mode"),
        "serving": ("endpoint", "model_role", "build_info", "enable_thinking"),
        "task_suite": ("name", "fingerprint"),
        "counts": ("tasks", "trials_per_task", "attempts", "passed_attempts", "input_tokens",
                   "cached_prompt_tokens"),
    }
    assert capture.RUN_SCHEMA == "epyc.hs4.opencode_shell_run.v1"
    assert capture.RUN_SIDECAR_NAME == "opencode_shell_run.json"
    assert capture.SIDECAR_NAME == "opencode_shell_run.beliefs.jsonl"
    assert set(RUN) == set(capture.RUN_SIDECAR_FIELDS[""])


def test_row_and_extra_field_names_are_pinned(tmp_path):
    rows = _rows(write_sidecar(make_run(tmp_path)))
    assert set(rows[0]) == {
        "schema", "run_id", "producer", "emitted_at", "date", "measurement_id", "metric",
        "value", "unit", "metric_direction", "category", "claim", "protocol_id", "reps",
        "reps_basis", "records_path", "records_sha256", "extra", "row_sha256"}
    assert capture.EXTRA_FIELDS == (
        "harness_name", "harness_pin", "plugin_name", "plugin_sha256", "config_sha256",
        "harness_card_version", "x_memory", "x_tool_mode", "serving", "task_suite", "counts",
        "hs14_columns", "columns_absent", "run_sidecar_sha256", "started_at", "finished_at")
    assert set(rows[0]["extra"]) == set(capture.EXTRA_FIELDS)
    assert list(capture.METRICS) == [
        "shell_pass_at_1", "shell_input_tokens_per_attempt", "shell_prefix_cache_hit_share",
        "shell_prefill_tokens_per_solved_task"]


# --- projection ----------------------------------------------------------------------------------

def test_hs14_columns_and_run_identity_ride_on_every_tuple(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    tuples = {t.metric: t for t in _tuples(run)}
    assert set(tuples) == set(capture.METRICS)
    assert tuples["shell_pass_at_1"].value == 0.4 and tuples["shell_pass_at_1"].reps == 30
    assert tuples["shell_input_tokens_per_attempt"].value == 20000.0
    assert tuples["shell_prefix_cache_hit_share"].value == 0.75
    prefill = tuples["shell_prefill_tokens_per_solved_task"]
    assert prefill.value == 12500.0 and prefill.reps == 12
    assert prefill.reps_basis == "scored:passed_attempts"
    assert prefill.metric_direction == "lower_better"
    for tup in tuples.values():
        e = tup.extra
        assert e["harness_pin"] == PIN and e["config_sha256"] == CFG
        assert e["plugin_sha256"] == PLUGIN and e["plugin_name"] == "epyc-orchestrator"
        assert e["harness_card_version"] == "hs7-card-2026-09-17"
        assert e["x_memory"] == "off" and e["x_tool_mode"] == "client"
        assert e["serving"]["enable_thinking"] is False
        assert e["columns_absent"] == []
        assert e["run_sidecar_sha256"] == capture.content_hash(RUN)
        assert tup.category == "BASELINE"
        assert tup.source_kind == reader.SOURCE_KIND


def test_locator_is_the_run_and_ids_are_unique(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    tuples = _tuples(run)
    assert len({t.attestation_locator for t in tuples}) == 1
    loc = tuples[0].attestation_locator
    assert loc.startswith(f"opencode-shell:{RUN['run_id']}:pin{PIN}:cfg{CFG}:")
    assert loc.endswith("attempts.jsonl")
    assert len({t.measurement_id for t in tuples}) == len(tuples)


def test_x_memory_arm_changes_identity(tmp_path):
    a = make_run(tmp_path, name="off")
    b = make_run(tmp_path, _variant(request_keys__x_memory="on", arm_role="CANDIDATE"), "on")
    write_sidecar(a)
    write_sidecar(b)
    ids_a = {t.measurement_id for t in _tuples(a)}
    ids_b = {t.measurement_id for t in _tuples(b)}
    assert not ids_a & ids_b
    assert {t.category for t in _tuples(b)} == {"CANDIDATE"}


def test_no_passed_attempt_omits_the_prefill_column_and_names_it(tmp_path):
    run = make_run(tmp_path, _variant(counts__passed_attempts=0))
    write_sidecar(run)
    tuples = _tuples(run)
    assert {t.metric for t in tuples} == set(capture.METRICS) - {capture.METRIC_PREFILL}
    assert tuples[0].extra["columns_absent"] == [capture.METRIC_PREFILL]
    assert tuples[0].extra["hs14_columns"][capture.METRIC_PREFILL] is None


def test_no_codified_protocol_grades_as_observation(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run)
    for tup in _tuples(run):
        assert tup.protocol_id == ""
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")
        assert any("no protocol citation" in r for r in reasons)


def test_a_cited_protocol_reaches_witnessed_attested(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run, protocol_id="measurement/protocols/opencode-shell-run.md")
    q, t, _ = ct.grade(_tuples(run)[0])
    assert (q, t) == ("Witnessed", "Attested")


# --- writer refusals -------------------------------------------------------------------------------

@pytest.mark.parametrize("changes, needle", [
    ({"harness__pin": _DROP}, "harness.pin"),
    ({"harness__pin": "main"}, "harness.pin"),
    ({"harness": _DROP}, "missing fields: harness"),
    ({"config_sha256": _DROP}, "config_sha256"),
    ({"config_sha256": ""}, "config_sha256"),
    ({"plugin__sha256": "x"}, "plugin.sha256"),
    ({"harness_card_version": ""}, "harness_card_version"),
    ({"request_keys__x_memory": "maybe"}, "x_memory"),
    ({"serving__enable_thinking": _DROP}, "enable_thinking"),
    ({"started_at": "2026-09-15T23:59:59Z"}, "before the SC86 hook"),
    ({"counts__attempts": 29}, "tasks x trials_per_task"),
    ({"counts__passed_attempts": 31}, "exceeds attempts"),
    ({"counts__cached_prompt_tokens": 600001}, "exceeds input_tokens"),
    ({"records_file": "../elsewhere.jsonl"}, "bare file name"),
    ({"schema": "something.else"}, "pre-hook"),
])
def test_writer_refuses_and_writes_nothing(tmp_path, changes, needle):
    run = make_run(tmp_path, _variant(**changes))
    with pytest.raises(capture.CaptureError, match=needle.replace(".", r"\.")):
        write_sidecar(run)
    assert not (run / capture.SIDECAR_NAME).exists()


def test_unknown_run_sidecar_field_is_refused(tmp_path):
    run = copy.deepcopy(RUN)
    run["pass_at_1"] = 0.9
    with pytest.raises(capture.CaptureError, match="schema is closed"):
        write_sidecar(make_run(tmp_path, run))


def test_run_dir_without_run_sidecar_is_pre_hook(tmp_path):
    run = make_run(tmp_path)
    (run / capture.RUN_SIDECAR_NAME).unlink()
    with pytest.raises(capture.CaptureError, match="pre-hook"):
        write_sidecar(run)


def test_backfill_after_the_fact_is_refused(tmp_path):
    run = make_run(tmp_path)
    with pytest.raises(capture.CaptureError, match="never backfills"):
        write_sidecar(run, emitted_at="2026-09-18T10:00:00Z")
    with pytest.raises(capture.CaptureError, match="precedes"):
        write_sidecar(run, emitted_at="2026-09-16T09:30:00Z")


def test_missing_records_file_is_refused(tmp_path):
    run = make_run(tmp_path)
    (run / "attempts.jsonl").unlink()
    with pytest.raises(capture.CaptureError, match="records missing"):
        write_sidecar(run)


# --- reader strictness -------------------------------------------------------------------------------

def test_pre_hook_run_dir_projects_nothing(tmp_path):
    run = make_run(tmp_path)
    assert reader.native_rows(run) == ()


def test_tampered_value_voids_the_whole_file(tmp_path):
    run = make_run(tmp_path)
    sidecar = write_sidecar(run)
    rows = _rows(sidecar)
    rows[0]["value"] = 0.9
    rows[0]["row_sha256"] = capture.row_digest(rows[0])  # re-sealed, still does not re-derive
    sidecar.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert reader.native_rows(run) == ()
    with pytest.raises(ct.ProjectionError, match="re-derive"):
        reader.project({"row": rows[0]})


def test_mixed_runs_in_one_sidecar_are_inadmissible(tmp_path):
    a = make_run(tmp_path, name="a")
    b = make_run(tmp_path, _variant(run_id="other"), "b")
    rows = _rows(write_sidecar(a)) + _rows(write_sidecar(b))[:1]
    mixed = tmp_path / capture.SIDECAR_NAME
    mixed.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert reader.native_rows(mixed) == ()


def test_mutated_records_file_grades_down(tmp_path):
    run = make_run(tmp_path)
    write_sidecar(run, protocol_id="measurement/protocols/opencode-shell-run.md")
    (run / "attempts.jsonl").write_text("changed\n")
    tup = _tuples(run)[0]
    assert tup.attestation_present is False and tup.attestation_verified is None
    q, _t, _ = ct.grade(tup)
    assert q == "Witnessed"
    assert ct.grade(tup)[1] != "Attested"


# --- end to end ----------------------------------------------------------------------------------

def test_writer_to_cli_ingest_to_tuple(tmp_path, capsys):
    root = tmp_path / "runs"
    run = make_run(root)
    make_run(root, name="pre-hook")  # run sidecar only: declined, never filled
    write_sidecar(run)
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "opencode-shell",
                   "--path", str(root), "--as-of", "2026-09-16T11:00:00Z"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] == []
    assert report["units_matched"] == 2 and report["units_projected"] == 1
    assert report["declined"] == [str(root / "pre-hook")]
    assert report["rows_projected"] == 4 and report["frames_emitted"] == 12
    supports = [r.frame for r in Ledger(ledger).read_all()
                if r.frame["frame_type"] == "epyc.vidya/frame/evidence_supports_claim/v1"]
    expected = {f"clm_{t.measurement_id}" for t in _tuples(run)}
    assert {f["assertion"]["claim_id"] for f in supports} == expected
    assert {(f["assertion"]["grade"]["Q"], f["assertion"]["grade"]["T"]) for f in supports} == {
        ("Judged", "Located")}
