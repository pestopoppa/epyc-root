"""Actual terminal serial children -> retained target cards, with no hardware work."""
import importlib
import json
from pathlib import Path

from dashboard import loop_status
from tests.test_dashboard_runtime_js import _page_js, _run
from tests.test_dashboard_serial_loop import producer, sources  # noqa: F401


def test_terminal_original_cpu_gpu_results_remain_selectable(sources, tmp_path, monkeypatch):  # noqa: F811
    fixture = importlib.import_module("autokernel.loop.test_serial_run")
    sr = importlib.import_module("autokernel.loop.serial_run")
    work = tmp_path / "actual-terminal"
    work.mkdir()
    router, argv = fixture._inputs(work, monkeypatch, rounds=1)
    marker = '(out / "loop-continuation.json").write_text(json.dumps(row))'
    child_source = fixture.CHILD.replace(
        'SimpleNamespace(status="measured_null")',
        'SimpleNamespace(status="kept" if cpu else "measured_null")').replace(
        'anchor_commit="a" * 40,', 'anchor_commit=("b" if cpu else "a") * 40,').replace(marker, '''
from scripts.kernel_rnd.autokernel.loop import status
status.write(Path(sr.option(argv, "--store")), state="complete", epoch="fixture",
    campaign_id="ak-loop", anchor_commit=row["current_anchor"]["commit"],
    model=row["model"], surface="serving:fixture-"+target_id, pairs=5,
    noise_floor_pct=7.8, target=identity, champion_head=row["current_anchor"]["commit"],
    batch={"output_dir": str(out), "pid": __import__("os").getpid()},
    iterations_planned=row["iterations_requested"], outcomes=[{
        "status":"kept" if cpu else "measured_null", "mechanism_id":"synthetic-"+target_id,
        "reason":"fixture-only, no measured hardware gain"} for _ in range(count)])
''' + marker)
    assert child_source != fixture.CHILD
    (work / "child.py").write_text(child_source)
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(router))
    assert sr.main(argv) == 0
    # Never parse the large result/native captures to render a completed batch.
    original_reader = loop_status._serial_bytes
    def bounded(path, **kwargs):
        assert Path(path).name != "loop-run.json"
        return original_reader(path, **kwargs)
    monkeypatch.setattr(loop_status, "_serial_bytes", bounded)
    wire = loop_status.snapshot()[0]
    serial = wire["serial"]
    assert serial["state"] == "complete" and serial["active"] is None and serial["child"] is None
    completed = serial["completed"]
    assert completed["errors"] == []
    assert [row["target_id"] for row in completed["items"]] == ["cpu", "gpu"]
    assert all(row["detail"] and not row["error"] for row in completed["items"]), completed
    cpu = completed["items"][0]
    assert cpu["summary"]["outcome_counts"] == {"kept": 1}
    assert cpu["detail"]["derived"]["kept"] == 1
    assert cpu["detail"]["loop"]["anchor_commit"] == cpu["detail"]["loop"]["champion_head"] == "b" * 40
    canonical = loop_status.snapshot(sources[0])[0]
    assert wire["champion_vs_production"]["measured"] == canonical["champion_vs_production"]["measured"]
    assert wire["knowledge"]["attempts"] == canonical["knowledge"]["attempts"] > 0
    page = _page_js() + '''
function chooseCpu(d){render(d);document.getElementById("serial-retained-target").onchange({target:{value:"0"}});}
function chooseGpu(d){render(d);document.getElementById("serial-retained-target").onchange({target:{value:"1"}});}
'''
    for name, target in (("chooseCpu", "cpu"), ("chooseGpu", "gpu")):
        view = _run(page, wire, tmp_path, [name])
        assert view["threw"] == []
        assert "1 / 1" in view["by_id"]["tiles"]
        assert "synthetic-" + target in view["by_id"]["recent"]
        assert "Retained target result" in view["text_by_id"]["hdr-step"]
        assert "not current activity" in view["by_id"]["serial"]
        assert view["by_id"]["champ"] and view["by_id"]["know"]
        assert view["text_by_id"]["hdr-state"] == "complete"

    # A later unrelated report cannot stand in for the retained original batch.
    cpu_status = Path(completed["items"][0]["detail"]["evidence"])
    original = cpu_status.read_text()
    changed = json.loads(original)
    changed["batch"]["output_dir"] = "/other/run"
    cpu_status.write_text(json.dumps(changed))
    wrong = loop_status.snapshot()[0]["serial"]["completed"]["items"][0]
    assert wrong["detail"] is None and "not this retained terminal batch" in wrong["error"]
    cpu_status.unlink()
    absent_wire = loop_status.snapshot()[0]
    absent = absent_wire["serial"]["completed"]["items"][0]
    assert absent["summary"]["iterations_completed"] == 1
    assert absent["detail"] is None and "absent" in absent["error"]
    view = _run(page, absent_wire, tmp_path, ["chooseCpu"])
    assert view["threw"] == [] and "Retained detail unavailable" in view["by_id"]["serial"]
    assert "1 / 1" not in view["by_id"]["tiles"]
    assert view["by_id"]["champ"] and view["by_id"]["know"]
    cpu_status.write_text(original)

    state_path = router / "serial-state.json"
    state = json.loads(state_path.read_text())
    state["last_results"]["0"]["sha256"] = "0" * 64
    state_path.write_text(json.dumps(state))
    refused = loop_status.snapshot()[0]["serial"]["completed"]["items"][0]
    assert refused["detail"] is None and "bytes differ" in refused["error"]
    state["config_digest"] = "another-owner"
    state_path.write_text(json.dumps(state))
    refusal = loop_status.snapshot()[0]["serial"]["completed"]
    assert not refusal["items"] and "differs" in refusal["errors"][0]
