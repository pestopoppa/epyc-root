import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.coordination import compute_ready as cr


AS_OF = "2026-08-13T12:30:00Z"
SCRIPT = Path(__file__).parents[2] / "scripts/coordination/compute_ready.py"


def checkpoint(blocker, node, *, weight="weight-1", model="model-small", grades=None,
               vram=2, duration=10, load=2, devices=None, bandwidth="idle",
               expires="2026-08-13T16:00:00Z", must_run=False, priority="background-churn",
               gates=None):
    return {
        "schema_version": cr.CHECKPOINT_SCHEMA,
        "kind": "compute-blocker",
        "event_id": f"checkpoint-{blocker}",
        "author": "worker-a",
        "ts": "2026-08-13T12:00:00Z",
        "blocker_id": blocker,
        "task_id": f"task-{blocker}",
        "task_text": f"run {blocker}",
        "spec_ref": f"spec.md#{blocker}",
        "checkpoint_ref": f"receipt:{blocker}",
        "checkpoint_sha256": "a" * 64,
        "validated": True,
        "graph_node_id": node,
        "priority_class": priority,
        "must_run": must_run,
        "expires_at": expires,
        "evidence_refs": [f"evidence:{blocker}"],
        "operator_gates": [] if gates is None else gates,
        "requirements": {
            "compatible_window_grades": grades or sorted(cr.GRADES),
            "required_devices": devices or ["gpu0"],
            "cpu_bandwidth_class": bandwidth,
            "gpu_vram_bytes": vram,
            "duration_seconds": duration,
            "contention_class": "exclusive-contiguous",
            "pausable": False,
            "model": {
                "model_id": model,
                "weight_id": weight,
                "size_bytes": 20,
                "load_seconds": load,
            },
        },
    }


def event(cp, state, number, prior, **extra):
    row = {
        "schema_version": cr.INTAKE_SCHEMA,
        "kind": "intake-disposition",
        "event_id": f"{cp['blocker_id']}-{number}-{state}",
        "author": "inference",
        "ts": f"2026-08-13T12:{number:02d}:00Z",
        "blocker_id": cp["blocker_id"],
        "checkpoint_event_id": cp["event_id"],
        "prior_event_id": prior,
        "state": state,
        "reason_code": f"test-{state}",
    }
    row.update(extra)
    return row


def ready_events(cp, *, minute=1):
    admitted = event(cp, "admitted", minute, cp["event_id"],
                     evidence_refs=[f"admission:{cp['blocker_id']}"])
    ready = event(cp, "ready", minute + 1, admitted["event_id"])
    return [admitted, ready]


def window(*, grade="full-idle", resident=None, load_allowed=True, budget=100,
           vram=100, starts="2026-08-13T12:00:00Z",
           expires="2026-08-13T14:00:00Z", models=None):
    return {
        "schema_version": cr.WINDOW_SCHEMA,
        "kind": "compute-window",
        "event_id": "window-event-1",
        "window_id": "window-1",
        "author": "inference",
        "ts": "2026-08-13T11:59:00Z",
        "grade": grade,
        "eligible_devices": ["gpu0"],
        "eligible_model_ids": models or ["model-small"],
        "cpu_bandwidth_class": "idle",
        "gpu_vram_available_bytes": vram,
        "max_model_bytes": 100,
        "resident_model_id": "model-small" if resident else None,
        "resident_weight_id": resident,
        "load_allowed": load_allowed,
        "starts_at": starts,
        "expires_at": expires,
        "time_budget_seconds": budget,
        "safe_drain_at": "window expiry",
        "observation_refs": ["sample:1", "sample:2"],
        "vram_observation_refs": ["vram:1", "vram:2"],
    }


def graph():
    nodes = [
        {"id": "A", "state": "active", "open": 1},
        {"id": "B", "state": "active", "open": 1},
        {"id": "C", "state": "active", "open": 1},
        {"id": "D", "state": "active", "open": 3},
        {"id": "E", "state": "active", "open": 2},
        {"id": "F", "state": "active", "open": 1},
        {"id": "OTHER", "state": "active", "open": 1},
        {"id": "LOCKED", "state": "active", "open": 9},
    ]
    return {
        "schema": "index_graph.v1",
        "nodes": nodes,
        "edges": [
            {"from": "D", "to": "A", "kind": "dep"},
            {"from": "E", "to": "D", "kind": "dep"},
            {"from": "F", "to": "B", "kind": "dep"},
            {"from": "LOCKED", "to": "A", "kind": "dep"},
            {"from": "LOCKED", "to": "OTHER", "kind": "dep"},
        ],
    }


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8")


def fixture_paths(tmp_path, checkpoints, intake, windows, graph_value=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = {name: tmp_path / f"{name}.jsonl" for name in ("checkpoints", "intake", "windows")}
    write_jsonl(paths["checkpoints"], checkpoints)
    write_jsonl(paths["intake"], intake)
    write_jsonl(paths["windows"], windows)
    paths["graph"] = tmp_path / ".index-graph.json"
    write_json(paths["graph"], graph_value or graph())
    paths["graph_hash"] = hashlib.sha256(paths["graph"].read_bytes()).hexdigest()
    return paths


def build(tmp_path, checkpoints, intake, win=None, graph_value=None):
    paths = fixture_paths(tmp_path, checkpoints, intake, [win or window()], graph_value)
    value = cr.build_projection(paths["checkpoints"], paths["intake"], paths["windows"],
                                paths["graph"], paths["graph_hash"], AS_OF)
    return value, paths


def reason_codes(projection, blocker):
    candidate = next(row for row in projection["candidates"] if row["blocker_id"] == blocker)
    return {row["code"] for row in candidate["incompatibility_reasons"]}


def test_small_model_grade_is_an_exact_label_not_an_order(tmp_path):
    cp = checkpoint("small", "C", grades=["small-model-only"])
    intake = ready_events(cp)
    compatible, _ = build(tmp_path / "compatible", [cp], intake,
                          window(grade="small-model-only"))
    assert [row["blocker_id"] for row in compatible["plan"]["selected"]] == ["small"]

    incompatible, _ = build(tmp_path / "incompatible", [cp], intake,
                            window(grade="full-idle"))
    assert reason_codes(incompatible, "small") == {"grade_mismatch"}


def test_load_then_keep_hot_selects_one_same_weight_group(tmp_path):
    a = checkpoint("a", "A", weight="weight-1", grades=["load-then-keep-hot"])
    b = checkpoint("b", "B", weight="weight-1", grades=["load-then-keep-hot"])
    c = checkpoint("c", "C", weight="weight-2", grades=["load-then-keep-hot"])
    intake = ready_events(a) + ready_events(b, minute=3) + ready_events(c, minute=5)
    projection, _ = build(tmp_path, [a, b, c], intake,
                          window(grade="load-then-keep-hot", resident=None))
    assert [row["blocker_id"] for row in projection["plan"]["selected"]] == ["a", "b"]
    assert projection["plan"]["weight_groups"] == ["weight-1"]
    assert reason_codes(projection, "c") == {"wrong_weight"}


def test_full_idle_can_plan_multiple_weight_groups(tmp_path):
    a = checkpoint("a", "A", weight="weight-1")
    b = checkpoint("b", "B", weight="weight-2")
    projection, _ = build(tmp_path, [a, b], ready_events(a) + ready_events(b, minute=3))
    assert [row["blocker_id"] for row in projection["plan"]["selected"]] == ["a", "b"]
    assert projection["plan"]["weight_groups"] == ["weight-1", "weight-2"]


def test_typed_resource_expiry_weight_gate_and_batch_reasons(tmp_path):
    expired = checkpoint("expired", "C", expires="2026-08-13T12:15:00Z")
    vram = checkpoint("vram", "C", vram=101)
    device = checkpoint("device", "C", devices=["gpu1"])
    bandwidth = checkpoint("bandwidth", "C", bandwidth="reduced")
    wrong = checkpoint("wrong", "C", weight="weight-2")
    gated = checkpoint("gated", "C", gates=["operator:approve"])
    rows = [expired, vram, device, bandwidth, wrong, gated]
    intake = []
    for offset, cp in enumerate(rows):
        intake += ready_events(cp, minute=1 + offset * 2)
    projection, _ = build(tmp_path, rows, intake,
                          window(resident="weight-1", load_allowed=False, vram=100))
    assert "candidate_expired" in reason_codes(projection, "expired")
    assert "insufficient_vram" in reason_codes(projection, "vram")
    assert "device_mismatch" in reason_codes(projection, "device")
    assert "bandwidth_mismatch" in reason_codes(projection, "bandwidth")
    assert "wrong_weight" in reason_codes(projection, "wrong")
    assert "operator_gate_unresolved" in reason_codes(projection, "gated")


@pytest.mark.parametrize(
    ("starts", "expires", "code"),
    [
        ("2026-08-13T13:00:00Z", "2026-08-13T14:00:00Z", "window_not_started"),
        ("2026-08-13T11:00:00Z", "2026-08-13T12:30:00Z", "window_expired"),
    ],
)
def test_window_time_bounds_fail_closed(tmp_path, starts, expires, code):
    cp = checkpoint("a", "C")
    projection, _ = build(tmp_path, [cp], ready_events(cp),
                          window(starts=starts, expires=expires))
    assert code in reason_codes(projection, "a")
    assert projection["plan"]["selected"] == []


def test_missing_admission_is_projected_but_missing_evidence_is_rejected(tmp_path):
    cp = checkpoint("a", "C")
    projection, _ = build(tmp_path / "not-admitted", [cp], [])
    assert reason_codes(projection, "a") == {"missing_admission"}

    bad_checkpoint = copy.deepcopy(cp)
    bad_checkpoint["evidence_refs"] = []
    with pytest.raises(cr.ContractError, match="non-empty list") as exc:
        build(tmp_path / "checkpoint-evidence", [bad_checkpoint], [])
    assert exc.value.code == "missing_evidence"

    admitted = event(cp, "admitted", 1, cp["event_id"], evidence_refs=[])
    with pytest.raises(cr.ContractError) as exc:
        build(tmp_path / "admission-evidence", [cp], [admitted])
    assert exc.value.code == "missing_evidence"


def test_lease_and_physical_claims_are_required_before_execution(tmp_path):
    cp = checkpoint("a", "C")
    admitted, ready = ready_events(cp)
    planned = event(cp, "planned", 3, ready["event_id"], window_id="window-1")
    grant = event(cp, "granted", 4, planned["event_id"])
    with pytest.raises(cr.ContractError) as exc:
        build(tmp_path / "missing-lease", [cp], [admitted, ready, planned, grant])
    assert exc.value.code == "missing_lease"

    grant.update(lease_id="lease-1", lease_path="leases/lease-1.json")
    running = event(cp, "running", 5, grant["event_id"], lease_id="lease-1",
                    lease_path="leases/lease-1.json", physical_claim_refs=[])
    with pytest.raises(cr.ContractError) as exc:
        build(tmp_path / "missing-claims", [cp], [admitted, ready, planned, grant, running])
    assert exc.value.code == "missing_evidence"


@pytest.mark.parametrize("surface", ["intake", "window"])
def test_only_inference_may_author_dispositions_and_windows(tmp_path, surface):
    cp = checkpoint("a", "C")
    intake = ready_events(cp)
    win = window()
    if surface == "intake":
        intake[0]["author"] = "coordinator"
    else:
        win["author"] = "coordinator"
    with pytest.raises(cr.ContractError) as exc:
        build(tmp_path, [cp], intake, win)
    assert exc.value.code == "unauthorized_author"


def test_event_chain_and_lifecycle_are_strict(tmp_path):
    cp = checkpoint("a", "C")
    direct_ready = event(cp, "ready", 1, cp["event_id"])
    with pytest.raises(cr.ContractError) as exc:
        build(tmp_path / "transition", [cp], [direct_ready])
    assert exc.value.code == "invalid_transition"

    admitted = event(cp, "admitted", 1, cp["event_id"], evidence_refs=["admit:1"])
    wrong_source = event(cp, "ready", 2, admitted["event_id"])
    wrong_source["checkpoint_event_id"] = "checkpoint-someone-else"
    with pytest.raises(cr.ContractError) as exc:
        build(tmp_path / "source", [cp], [admitted, wrong_source])
    assert exc.value.code == "checkpoint_mismatch"


def test_graph_hash_and_all_edges_must_resolve(tmp_path):
    cp = checkpoint("a", "A")
    paths = fixture_paths(tmp_path / "hash", [cp], ready_events(cp), [window()])
    with pytest.raises(cr.ContractError) as exc:
        cr.build_projection(paths["checkpoints"], paths["intake"], paths["windows"],
                            paths["graph"], "0" * 64, AS_OF)
    assert exc.value.code == "graph_hash_mismatch"

    broken = graph()
    broken["edges"].append({"from": "UNKNOWN", "to": "A", "kind": "dep"})
    with pytest.raises(cr.ContractError) as exc:
        build(tmp_path / "edge", [cp], ready_events(cp), graph_value=broken)
    assert exc.value.code == "unresolved_graph_edge"


def test_leverage_ranking_override_priority_fit_age_and_stable_tie(tmp_path):
    must = checkpoint("z-must", "C", must_run=True)
    high_leverage = checkpoint("a-leverage", "A")
    direct = checkpoint("b-direct", "B")
    prod = checkpoint("c-prod", "C", priority="production-live", duration=11)
    exact = checkpoint("d-exact", "C", priority="production-live", duration=12)
    tie_b = checkpoint("tie-b", "C")
    tie_a = checkpoint("tie-a", "C")
    rows = [must, high_leverage, direct, prod, exact, tie_b, tie_a]
    intake = []
    for cp in rows:
        intake += ready_events(cp)
    projection, _ = build(tmp_path, rows, intake, window(budget=500))
    order = [row["blocker_id"] for row in projection["plan"]["selected"]]
    assert order == ["z-must", "a-leverage", "b-direct", "d-exact", "c-prod",
                     "tie-a", "tie-b"]
    leverage = next(row for row in projection["candidates"]
                    if row["blocker_id"] == "a-leverage")["leverage"]
    assert leverage == {
        "graph_node_id": "A",
        "fire_ready_task_count": 5,
        "direct_handoffs_unlocked": ["D"],
        "transitive_open_dependants": ["E"],
    }
    assert projection["plan"]["selected"][1]["rank_evidence"]["graph_sha256"] == \
        projection["inputs"]["graph"]["sha256"]


def test_batch_budget_excludes_lower_ranked_work_with_typed_reason(tmp_path):
    a = checkpoint("a", "A", duration=10, load=0)
    b = checkpoint("b", "B", duration=10, load=0)
    projection, _ = build(tmp_path, [a, b], ready_events(a) + ready_events(b),
                          window(budget=10, resident="weight-1"))
    assert [row["blocker_id"] for row in projection["plan"]["selected"]] == ["a"]
    assert reason_codes(projection, "b") == {"batch_time_exhausted"}


def test_cli_build_check_replay_is_byte_stable_and_sources_are_immutable(tmp_path):
    cp = checkpoint("a", "A")
    paths = fixture_paths(tmp_path, [cp], ready_events(cp), [window()])
    source_before = {name: path.read_bytes() for name, path in paths.items() if isinstance(path, Path)}
    output_1 = tmp_path / "projection-1.json"
    output_2 = tmp_path / "projection-2.json"
    base = [
        sys.executable, str(SCRIPT), "build",
        "--checkpoints", str(paths["checkpoints"]),
        "--intake", str(paths["intake"]),
        "--windows", str(paths["windows"]),
        "--graph", str(paths["graph"]),
        "--graph-sha256", paths["graph_hash"],
        "--as-of", AS_OF,
    ]
    subprocess.run(base + ["--output", str(output_1)], check=True)
    subprocess.run(base + ["--output", str(output_2)], check=True)
    assert output_1.read_bytes() == output_2.read_bytes()

    check = base.copy()
    check[2] = "check"
    checked = subprocess.run(check + ["--projection", str(output_1)], check=True,
                             capture_output=True, text=True)
    assert checked.stdout.startswith("OK ")
    assert source_before == {name: path.read_bytes() for name, path in paths.items()
                             if isinstance(path, Path)}

    tampered = json.loads(output_1.read_text(encoding="utf-8"))
    tampered["plan"]["selected"] = []
    write_json(output_1, tampered)
    failed = subprocess.run(check + ["--projection", str(output_1)], capture_output=True, text=True)
    assert failed.returncode == 2
    assert "projection_hash_invalid" in failed.stderr


def test_projection_hash_is_content_addressed_not_path_dependent(tmp_path):
    cp = checkpoint("a", "A")
    first = fixture_paths(tmp_path / "one", [cp], ready_events(cp), [window()])
    second = fixture_paths(tmp_path / "two", [cp], ready_events(cp), [window()])
    projections = []
    for paths in (first, second):
        projections.append(cr.build_projection(
            paths["checkpoints"], paths["intake"], paths["windows"], paths["graph"],
            paths["graph_hash"], AS_OF))
    assert projections[0] == projections[1]
    assert projections[0]["projection_sha256"] == projections[1]["projection_sha256"]
