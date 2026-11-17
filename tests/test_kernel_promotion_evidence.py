"""Fixture coverage for live identity, exact parity, and fail-closed publishing."""

import importlib.util
import os
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/benchmark/kernel_promotion_evidence.py"
SPEC = importlib.util.spec_from_file_location("kernel_promotion_evidence", SOURCE)
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


def plan():
    return evidence.resident_plan.build_plan([{
        "scenario": "fixture", "nominal_context": 2048,
        "request_body": {"prompt": "p", "temperature": 0, "seed": 35, "cache_prompt": False, "n_predict": 3},
    }])


def map_line(path, *, identity=None):
    if identity is None:
        info = path.stat()
        identity = info.st_dev, info.st_ino
    dev, ino = identity
    return f"1234-5678 r-xp 00000000 {os.major(dev):x}:{os.minor(dev):x} {ino} {path}\n"


def test_live_image_binds_open_executable_and_mapped_inodes(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    exe = tmp_path / "llama-server"
    exe.write_bytes(b"executable")
    library = tmp_path / "libggml-cpu.so.0"
    library.write_bytes(b"library")
    (proc / "exe").symlink_to(exe)
    (proc / "maps").write_text(map_line(library))
    pin = {"binary_sha256": evidence.digest(exe), "libraries": {library.name: evidence.digest(library)}}
    witness = evidence.live_image(proc, exe, pin)
    evidence.verify_live_image(proc, witness)
    library.rename(tmp_path / "replacement-target")
    library.write_bytes(b"library")
    with pytest.raises(ValueError, match="mapped inode"):
        evidence.live_image(proc, exe, pin)
    with pytest.raises(ValueError, match="identity changed"):
        evidence.verify_live_image(proc, witness)


def test_deleted_hot_library_and_wrong_library_digest(tmp_path):
    proc = tmp_path / "proc"
    proc.mkdir()
    exe = tmp_path / "llama-server"
    exe.write_bytes(b"executable")
    library = tmp_path / "libggml.so"
    library.write_bytes(b"other")
    (proc / "exe").symlink_to(exe)
    (proc / "maps").write_text(map_line(library))
    pin = {"binary_sha256": evidence.digest(exe), "libraries": {library.name: "0" * 64}}
    with pytest.raises(ValueError, match="differs from pin"):
        evidence.live_image(proc, exe, pin)
    with pytest.raises(ValueError, match="stable path"):
        evidence.map_identities(map_line(library).rstrip() + " (deleted)")


def test_mmap_model_must_bind_prepared_inode(tmp_path):
    path = tmp_path / "model.gguf"
    path.write_bytes(b"GGUF")
    pins = {str(path): {"stat": evidence.stat_identity(path.stat()), "sha256": evidence.digest(path)}}
    evidence.verify_models(pins)
    assert evidence.model_mappings(map_line(path), {str(path)}, pins, no_mmap=False)
    with pytest.raises(ValueError, match="mmap witness"):
        evidence.model_mappings("", {str(path)}, pins, no_mmap=False)
    assert evidence.model_mappings("", {str(path)}, pins, no_mmap=True) == {}
    assert evidence.stat_identity(path.stat()) == pins[str(path)]["stat"]
    path.write_bytes(b"stale")
    with pytest.raises(ValueError, match="prepared model changed"):
        evidence.verify_models(pins)


def write_request(directory, cohort, row, *, content="A" * 300, tokens=(1, 2, 3), count=3, pid=10,
                  resident=False):
    directory.mkdir(exist_ok=True)
    body = cohort["request_body"] | row.get("request_overrides", {})
    evidence.write(directory / "request.json", body)
    response = {"usage": {"completion_tokens": count}}
    if "n_predict" in body:
        response["content"] = content
    else:
        response["choices"] = [{"message": {"content": content}}]
    if tokens is not None:
        response["tokens"] = list(tokens)
    evidence.write(directory / "response.json", response)
    affinity = {str(pid): [0]}
    idle = {"idle_peer_before": {"cpu_s": 0}, "idle_peer_after": {"cpu_s": 0},
            "idle_peer_cpu_s": 0} if resident else {}
    evidence.write(directory / "row.json", {
        **row, "request_file_sha256": evidence.digest(directory / "request.json"),
        "response_file_sha256": evidence.digest(directory / "response.json"),
        "summary": {"completion_tokens": count, "elapsed_s": 2.0},
        "active_affinity_before": affinity, "active_affinity_after": affinity, **idle,
    })
    evidence.write(directory / "request-affinity.json", {
        "query_elapsed_s": 1.9, "sample_offsets_s": [0.1], "first_sample_affinity": affinity,
        "failure": None,
    })
    return evidence.collect_request(directory, cohort, row, {"pid": pid, "allowed_cpus": [0]})


def test_compares_full_native_content_and_scheduled_fresh_cells(tmp_path):
    schedule = plan()
    cohort = schedule["cohorts"][0]
    rows = cohort["requests"]
    left = write_request(tmp_path / "left", cohort, rows[0], content="A" * 300 + "x")
    right = write_request(tmp_path / "right", cohort, rows[1], content="A" * 300 + "y")
    keys = [("fixture", 2048, row["pair_index"], row["schedule_position"]) for row in rows]
    resident = dict.fromkeys(keys, left)
    fresh = dict.fromkeys(keys, left) | {keys[2]: right}
    report = evidence.parity_pack(schedule, resident, fresh)
    assert report["verdict"] == "different"
    assert len(report["comparisons"]) == 40
    assert report["comparisons"][0] == {
        "comparison": "paired_resident", "left": keys[0], "right": keys[1],
        "body": "exact", "content": "exact", "token_ids": "exact",
    }
    assert report["comparisons"][11]["content"] == "different"
    assert report["comparisons"][22]["content"] == "different"


@pytest.mark.parametrize("tokens", [None, [1, 2], [1, 2, True], [1, 2, -3]])
def test_missing_or_malformed_token_ids_are_incomplete(tmp_path, tokens):
    cohort = plan()["cohorts"][0]
    observed = write_request(tmp_path / "row", cohort, cohort["requests"][0], tokens=tokens)
    assert evidence.compare(observed, observed) == {"body": "exact", "content": "exact", "token_ids": "incomplete"}


def test_short_response_and_changed_body_fail_closed(tmp_path):
    cohort = plan()["cohorts"][0]
    row = cohort["requests"][0]
    with pytest.raises(ValueError, match="short response"):
        write_request(tmp_path / "short", cohort, row, count=2)
    directory = tmp_path / "body"
    write_request(directory, cohort, row)
    path = directory / "request.json"
    path.write_text('{"prompt":"changed"}')
    with pytest.raises(ValueError, match="differ from the plan"):
        evidence.collect_request(directory, cohort, row, {"pid": 10, "allowed_cpus": [0]})


def test_seal_publishes_only_after_verification_and_detects_tampering(tmp_path, monkeypatch):
    staging, sealed = tmp_path / ".staged", tmp_path / "sealed"
    staging.mkdir()
    artifact = staging / "fixture.txt"
    artifact.write_text("capture")
    comparison = {"status": "observation_only", "comparisons": []}

    def refuse(_root):
        raise ValueError("missing proof")

    monkeypatch.setattr(evidence, "build_comparison", refuse)
    with pytest.raises(ValueError, match="missing proof"):
        evidence.seal(staging, sealed)
    assert staging.is_dir() and not sealed.exists()
    monkeypatch.setattr(evidence, "build_comparison", lambda root: comparison)
    assert evidence.seal(staging, sealed) == comparison
    assert not staging.exists()
    assert evidence.verify(sealed) == comparison
    (sealed / "fixture.txt").write_text("tampered")
    with pytest.raises(ValueError, match="evidence seal"):
        evidence.verify(sealed)


def fixture_server(directory, pins, arm, pid):
    pin = pins["arms"][arm]
    library = Path(pin["binary_path"]).parent / next(iter(pin["libraries"]))
    model = Path(next(iter(pins["models"])))
    (directory / f"{arm}-maps.txt").write_text(map_line(library, identity=(3, 48))
                                             + map_line(model, identity=(3, 49)))
    (directory / f"{arm}-numa-maps.txt").write_text("1234 interleave:0-3 N0=8 N1=8\n")
    (directory / f"{arm}-server.log").write_text("ready\n")
    evidence.write(directory / f"{arm}-argv.json",
                   ["numactl", "--interleave=all", pin["binary_path"], "-m", str(model), "--no-kv-unified"])
    evidence.write(directory / f"{arm}-env.json", {"LD_LIBRARY_PATH": str(library.parent),
                                                   "ROCR_VISIBLE_DEVICES": "-1", "HIP_VISIBLE_DEVICES": "-1"})
    return {"pid": pid, "pgid": pid, "birth": 1, "allowed_cpus": [0], "affinity": {str(pid): [0]},
            "image": {"binary": {"sha256": pin["binary_sha256"], "stat": [3, 47, 100, 1, 1]},
                      "libraries": {str(library): {"sha256": pin["libraries"][library.name],
                                                   "stat": [3, 48, 200, 1, 1]}}},
            "models": {str(model): [3, 49]}}


def fixture_capture(root, plan, pins, opened, *, fresh):
    root.mkdir()
    evidence.write(root / "claim.open.json", opened)
    evidence.write(root / "plan.json", plan)
    host = {"boot_id": "boot", "numa_online": "0-3", "numa_cpus": {"node0": "0-23"},
            "cpu_online": "0-191", "cpu_model": "EPYC fixture", "uptime_s": 1.0}
    evidence.write(root / "host.json", host)
    evidence.write(root / "host-after.json", host | {"uptime_s": 2.0})
    (root / "contention-matrix.yaml").write_text('topology_hash: "abcdef0123456789"\n')
    (root / "contention-matrix.txt").write_text("OK: contention matrix is fresh (topology_hash=abcdef01)\n")
    for arm in evidence.ARMS:
        (root / f"{arm}-linkage.txt").write_text("linkage OK\n")
    directories = []
    for index, cohort in enumerate(plan["cohorts"]):
        directory = root / f"cohort-{index:03}"
        directory.mkdir()
        info = {key: cohort[key] for key in ("scenario", "nominal_context")}
        directories.append(info)
        warmups = {row["arm"]: row for row in cohort["warmups"]}
        if fresh:
            info["requests"] = []
        else:
            info.update(servers={}, cleanup={})
            for arm_index, (arm, warmup) in enumerate(warmups.items()):
                pid = 3 + 2 * index + arm_index
                info["servers"][arm] = fixture_server(directory, pins, arm, pid)
                info["cleanup"][arm] = {"pid": pid, "dead": True, "port_closed": True}
                write_request(directory / f"warmup-{arm}", cohort, warmup, pid=pid, count=64, tokens=range(64))
        for row in cohort["requests"]:
            position, arm = row["schedule_position"], row["arm"]
            request_dir = directory / f"request-{position:03}"
            if fresh:
                request_dir.mkdir()
                pid = 100 + 100 * index + position
                server = fixture_server(request_dir, pins, arm, pid)
                info["requests"].append(row | {"server": server, "complete": True,
                                               "cleanup": {"pid": pid, "dead": True, "port_closed": True}})
                write_request(request_dir / "warmup", cohort, warmups[arm], pid=pid, count=64, tokens=range(64))
            else:
                pid = info["servers"][arm]["pid"]
            write_request(request_dir, cohort, row, pid=pid, resident=not fresh)

    mode = "fresh" if fresh else "resident"
    lifecycle = "fresh_server" if fresh else "paired_resident"
    evidence.write(root / "capture.json", {
        "schema": f"epyc.kernel_promotion_{mode}_capture.v1", "status": "observation_only",
        "lifecycle_mode": lifecycle, "schedule_sha256": plan["schedule_sha256"], "provenance": pins,
        "complete": True, "cleanup_proved": True, "cohorts": directories,
    })


def test_full_pair_and_fresh_capture_seals_and_recomputes(tmp_path):
    staging, sealed = tmp_path / ".stage", tmp_path / "sealed"
    staging.mkdir()
    original = plan()["cohorts"][0]
    native = {key: original[key] for key in evidence.resident_plan.COHORT_FIELDS}
    chat = {"scenario": "chat", "nominal_context": 2048, "request_body": {
        "messages": [{"role": "user", "content": "p"}],
        "temperature": 0, "seed": 35, "cache_prompt": False, "max_tokens": 3,
    }}
    schedule = evidence.resident_plan.build_plan([native, chat])
    evidence.write(staging / "input-plan.json", schedule)
    (staging / "SOURCE.sha256").write_text("pinned source\n")
    model = "/fixture/model.gguf"
    model_sha = "0" * 64
    (staging / "model.sha256").write_text(f"{model_sha}  {model}\n")
    arm = {"binary_path": "/fixture/llama-server", "binary_sha256": "a" * 64,
           "libraries": {"libggml.so.1": "1" * 64}}
    pins = {
        "plan_sha256": evidence.digest(staging / "input-plan.json"),
        "source_manifest_sha256": evidence.digest(staging / "SOURCE.sha256"), "kv_mode": "split",
        "models": {model: {"stat": [3, 49, 300, 1, 1], "sha256": model_sha}},
        "arms": dict.fromkeys(evidence.ARMS, arm),
    }
    evidence.write(staging / "pins.json", pins)
    (staging / "provider.grant").write_text("fixture grant")
    claim = {"schema": "region-lock-claim.v1", "claim_id": "fixture",
             "provider_pid": 10, "provider_pid_starttime": 1}
    opened = claim | {
        "phase": "open", "provider": "region-lock", "cpu_list": "0-95",
        "regions": evidence.REGIONS, "flock_proof": [{"region": region} for region in evidence.REGIONS],
        "grant_start": "2026-11-17T13:00:00+00:00", "opened_utc": "2026-11-17T13:01:00+00:00",
        "grant_end": "2026-11-17T15:00:00+00:00", "grant_sha256": evidence.digest(staging / "provider.grant"),
    }
    evidence.write(staging / "provider.open.json", opened)
    evidence.write(staging / "provider.close.json", claim | {
        "phase": "close", "closed_utc": "2026-11-17T14:00:00+00:00",
        "open_sha256": evidence.digest(staging / "provider.open.json"), "child_rc": 0,
    })
    fixture_capture(staging / "resident", schedule, pins, opened, fresh=False)
    fresh = staging / "resident/fresh-replay"
    fixture_capture(fresh, schedule, pins, opened, fresh=True)
    capture = staging / "resident/capture.json"
    complete_capture = capture.read_bytes()
    damaged = evidence.read(capture)
    del damaged["cohorts"][0]["servers"]["production"]["image"]["binary"]["stat"]
    capture.unlink()
    evidence.write(capture, damaged)
    with pytest.raises(ValueError, match="server image differs"):
        evidence.seal(staging, sealed)
    assert not sealed.exists()
    capture.write_bytes(complete_capture)
    record = fresh / "cohort-001/request-000/request-affinity.json"
    original = record.read_bytes()
    record.write_text("{}")
    with pytest.raises(KeyError):
        evidence.seal(staging, sealed)
    assert not sealed.exists()
    record.write_bytes(original)
    report = evidence.seal(staging, sealed)
    assert report["verdict"] == "exact"
    assert report["resident_complete"] and report["fresh_complete"]
    assert len(report["comparisons"]) == 80
    assert evidence.verify(sealed) == report
