"""Tests for running-state attestation generation."""

from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.attest import generate_attestation as attest


def test_parse_process_args_for_llama_server() -> None:
    cmdline = [
        "/opt/llama.cpp/build/bin/llama-server",
        "-m",
        "/models/model.gguf",
        "-md",
        "/models/draft.gguf",
        "--host",
        "127.0.0.1",
        "--port",
        "8070",
        "-np",
        "1",
        "-c",
        "32768",
        "-t",
        "96",
        "-ub",
        "8192",
        "-ctk",
        "q8_0",
        "-ctv",
        "q8_0",
        "--flash-attn",
        "on",
        "--mlock",
    ]

    assert attest.classify_process(cmdline) == "llama_server"
    parsed = attest.parse_process_args(cmdline)

    assert parsed["port"] == 8070
    assert parsed["model_path"] == "/models/model.gguf"
    assert parsed["draft_model_path"] == "/models/draft.gguf"
    assert parsed["parallel_slots"] == "1"
    assert parsed["context_length"] == "32768"
    assert parsed["threads"] == "96"
    assert parsed["ubatch_size"] == "8192"
    assert parsed["kv_cache_type_k"] == "q8_0"
    assert parsed["kv_cache_type_v"] == "q8_0"
    assert parsed["flash_attention"] == "on"
    assert parsed["mlock"] is True


def test_classify_process_does_not_match_supervisor_flag_text() -> None:
    cmdline = [
        "/usr/local/bin/earlyoom",
        "--ignore",
        "^(llama-server|sd-server)$",
    ]

    assert attest.classify_process(cmdline) is None
    assert attest.parse_process_args(cmdline) == {"port": None}


def test_registry_port_map_includes_numa_ports(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """
server_mode:
  frontdoor:
    port: 8070
    model_path: /models/frontdoor.gguf
    numa_ports: [8080, 8180]
  worker_vision:
    port: 8086
    model:
      name: Qwen2.5-VL
      path: /models/vl.gguf
""",
        encoding="utf-8",
    )

    ports = attest.load_registry_ports(registry)

    assert ports[8070][0]["registry_section"] == "server_mode.frontdoor"
    assert ports[8070][0]["port_kind"] == "primary"
    assert ports[8080][0]["port_kind"] == "numa_replica"
    assert ports[8180][0]["role"] == "frontdoor"
    assert ports[8086][0]["model_name"] == "Qwen2.5-VL"


def test_registry_port_map_preserves_shared_port_aliases(tmp_path: Path) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        """
server_mode:
  frontdoor:
    port: 8070
    model_path: /models/frontdoor.gguf
  coder_escalation:
    port: 8070
    model_path: /models/frontdoor.gguf
""",
        encoding="utf-8",
    )

    ports = attest.load_registry_ports(registry)

    assert [entry["registry_section"] for entry in ports[8070]] == [
        "server_mode.frontdoor",
        "server_mode.coder_escalation",
    ]


def test_manifest_port_map_can_satisfy_live_port_attestation() -> None:
    registry_ports: dict[int, list[dict[str, object]]] = {}
    manifest_ports = {
        8185: [
            {
                "role": "ingest_long_context",
                "model_name": None,
                "model_path": None,
                "registry_section": "stack_manifest.ingest_long_context",
                "port_kind": "stack_manifest_hot",
            }
        ]
    }

    ports = attest.merge_port_maps(registry_ports, manifest_ports)
    summary = attest.summarize(
        [
            {
                "pid": 123,
                "kind": "llama_server",
                "port": 8185,
                "registry_matches": ports[8185],
                "dynamic_linking": {"issues": []},
            }
        ]
    )

    assert summary["issue_count"] == 0


def test_llama_resolution_detects_cross_tree_mismatch() -> None:
    status = attest.llama_resolution_status(
        "/mnt/raid0/llm/ik_llama.cpp/build/bin/llama-server",
        {
            "libllama.so": "/mnt/raid0/llm/llama.cpp/build/bin/libllama.so",
            "libggml.so": "/mnt/raid0/llm/ik_llama.cpp/build/ggml/src/libggml.so",
        },
    )

    assert status["expected_tree"] == "/mnt/raid0/llm/ik_llama.cpp"
    assert status["issues"] == ["libllama.so_tree_mismatch:/mnt/raid0/llm/llama.cpp"]


def test_collect_feature_flags_detects_worker_drift(monkeypatch, tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    for pid, value in ((101, "1"), (102, "0")):
        pid_dir = proc_root / str(pid)
        pid_dir.mkdir(parents=True)
        (pid_dir / "environ").write_bytes(f"ORCHESTRATOR_FEATURE_MODEL_FALLBACK={value}\0".encode())
    responses = [
        {
            "pid": 101,
            "flags": {"model_fallback": True},
            "sources": {"model_fallback": "ORCHESTRATOR_FEATURE_MODEL_FALLBACK"},
        },
        {
            "pid": 102,
            "flags": {"model_fallback": False},
            "sources": {"model_fallback": "ORCHESTRATOR_FEATURE_MODEL_FALLBACK"},
        },
    ]

    monkeypatch.setattr(attest, "_fetch_json", lambda _url: responses.pop(0))
    monkeypatch.setattr(
        attest,
        "load_declared_feature_env",
        lambda: {
            "status": "ok",
            "env": {"ORCHESTRATOR_FEATURE_MODEL_FALLBACK": "1"},
            "flag_env_names": {
                "model_fallback": "ORCHESTRATOR_FEATURE_MODEL_FALLBACK",
            },
            "flags": {"model_fallback": True},
        },
    )

    report = attest.collect_feature_flags(polls=2, delay_s=0, proc_root=proc_root)

    assert report["status"] == "warn"
    assert report["heterogeneous"] == {
        "model_fallback": {"101": True, "102": False},
    }
    # intent_diffs compares a worker against ITS OWN launch inputs (environ +
    # runtime flag file), not against the declared block — see
    # `expected_by_worker` in _expected_flag_diffs and the runtime-file test
    # below. Worker 102 reports exactly what its own environ says, so the
    # mismatch with the declared block surfaces as env_diffs, which is the
    # channel that actually names the offending variable.
    assert report["intent_diffs"] == []
    assert report["env_diffs"] == [
        {
            "pid": "102",
            "env": "ORCHESTRATOR_FEATURE_MODEL_FALLBACK",
            "expected": "1",
            "actual": "0",
        }
    ]


def test_collect_feature_flags_detects_worker_contradicting_its_own_env(
    monkeypatch, tmp_path: Path
) -> None:
    """A worker whose reported flags disagree with its own environ is intent drift.

    This is what intent_diffs is for: the process is not running what its own
    launch inputs predict (stale code, a legacy ORCHESTRATOR_* spelling, or a
    runtime file it never re-read). Distinct from env_diffs, which catches a
    worker launched with the wrong env in the first place.
    """
    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "101"
    pid_dir.mkdir(parents=True)
    (pid_dir / "environ").write_bytes(b"ORCHESTRATOR_FEATURE_MODEL_FALLBACK=0\0")

    responses = [
        {
            "pid": 101,
            "flags": {"model_fallback": True},
            "sources": {"model_fallback": "runtime_file:/nowhere/runtime_flags.json"},
        }
    ]
    monkeypatch.setattr(attest, "_fetch_json", lambda _url: responses.pop(0))
    monkeypatch.setattr(
        attest,
        "load_declared_feature_env",
        lambda: {
            "status": "ok",
            "env": {"ORCHESTRATOR_FEATURE_MODEL_FALLBACK": "0"},
            "flag_env_names": {"model_fallback": "ORCHESTRATOR_FEATURE_MODEL_FALLBACK"},
            "flags": {"model_fallback": False},
        },
    )

    report = attest.collect_feature_flags(polls=1, delay_s=0, proc_root=proc_root)

    assert report["env_diffs"] == []
    assert {
        (diff["pid"], diff["flag"], diff["expected"], diff["actual"])
        for diff in report["intent_diffs"]
    } >= {("101", "model_fallback", False, True)}
    assert report["status"] == "warn"


def test_collect_feature_flags_uses_runtime_file_for_worker_intent(
    monkeypatch, tmp_path: Path
) -> None:
    runtime_flags = tmp_path / "runtime_flags.json"
    runtime_flags.write_text(
        json.dumps(
            {
                "version": 1,
                "flags": {
                    "react_mode": {
                        "value": False,
                        "set_by": "unit",
                        "ts": "2026-07-20T00:00:00+00:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "101"
    pid_dir.mkdir(parents=True)
    pid_dir.joinpath("environ").write_bytes(
        (
            "ORCHESTRATOR_REACT_MODE=1\0"
            "ORCHESTRATOR_FEATURE_REACT_MODE=1\0"
            f"ORCHESTRATOR_RUNTIME_FLAGS_PATH={runtime_flags}\0"
        ).encode()
    )
    responses = [
        {
            "pid": 101,
            "flags": {"react_mode": False},
            "sources": {"react_mode": f"runtime_file:{runtime_flags}"},
        }
    ]

    monkeypatch.setattr(attest, "_fetch_json", lambda _url: responses.pop(0))
    monkeypatch.setattr(
        attest,
        "load_declared_feature_env",
        lambda: {
            "status": "ok",
            "env": {"ORCHESTRATOR_FEATURE_REACT_MODE": "1"},
            "flag_env_names": {"react_mode": "ORCHESTRATOR_FEATURE_REACT_MODE"},
            "flags": {"react_mode": True},
        },
    )

    report = attest.collect_feature_flags(polls=1, delay_s=0, proc_root=proc_root)

    assert report["status"] == "ok"
    assert report["intent_diffs"] == []
    assert report["env_diffs"] == []


def test_build_serving_config_reports_numa_match() -> None:
    rows = attest.build_serving_config(
        [
            {
                "pid": 123,
                "kind": "llama_server",
                "port": 8070,
                "registry_matches": [{"registry_section": "server_mode.frontdoor"}],
                "args": {
                    "model_path": "/models/model.gguf",
                    "context_length": "32768",
                    "threads": "96",
                },
                "cpus_allowed_list": "0-3",
            }
        ],
        numa_ports={8070: {"role": "frontdoor", "cpu_list": "0-3", "threads": 96}},
    )

    assert rows[0]["numa_match"] is True
    assert rows[0]["numa_intent"]["role"] == "frontdoor"


def test_collect_eval_instrument_hashes_files_and_env(tmp_path: Path) -> None:
    sentinel = tmp_path / "tool_sentinels.yaml"
    sentinel.write_text("sentinels: []\n", encoding="utf-8")
    proc_root = tmp_path / "proc"
    for pid, env in (
        (200, b"AUTOPILOT_TOOL_SENTINELS=1\0"),
        (201, b""),
    ):
        pid_dir = proc_root / str(pid)
        pid_dir.mkdir(parents=True)
        (pid_dir / "environ").write_bytes(env)

    report = attest.collect_eval_instrument(
        [
            {"pid": 200, "kind": "autopilot"},
            {"pid": 201, "kind": "orchestrator_api"},
        ],
        proc_root=proc_root,
        sentinel_paths=(sentinel,),
    )

    assert report["status"] == "warn"
    assert report["files"][0]["exists"] is True
    assert report["files"][0]["sha256"]
    assert report["missing_tool_sentinel_env"] == [{"pid": 201, "kind": "orchestrator_api"}]


def test_parse_gitnexus_status_marks_stale() -> None:
    parsed = attest._parse_gitnexus_status(
        "Repository: /repo\nIndexed commit: abc123\nCurrent commit: def456\nStatus: stale"
    )

    assert parsed["indexed_commit"] == "abc123"
    assert parsed["current_commit"] == "def456"
    assert parsed["stale"] is True


def test_build_report_from_fake_proc(monkeypatch, tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    pid_dir = proc_root / "123"
    pid_dir.mkdir(parents=True)
    (proc_root / "stat").write_text("btime 1700000000\n", encoding="utf-8")
    start_fields = ["0"] * 20
    start_fields[19] = "100"
    (pid_dir / "stat").write_text(
        "123 (llama-server) S " + " ".join(start_fields),
        encoding="utf-8",
    )
    (pid_dir / "status").write_text(
        "Name:\tllama-server\nState:\tS (sleeping)\nCpus_allowed_list:\t0-3\n",
        encoding="utf-8",
    )
    binary = tmp_path / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    binary.write_text("not an elf", encoding="utf-8")
    (pid_dir / "exe").symlink_to(binary)
    (pid_dir / "cmdline").write_bytes(
        b"/tmp/llama.cpp/build/bin/llama-server\0-m\0/models/model.gguf\0--port\08070\0"
    )
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "server_mode:\n  frontdoor:\n    port: 8070\n    model_path: /models/model.gguf\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        attest,
        "run_dynamic_checks",
        lambda _exe: {"status": "ok", "issues": [], "readelf": {}, "ldd": {}},
    )
    monkeypatch.setattr(
        attest,
        "load_numa_ports",
        lambda: {8070: {"role": "frontdoor", "cpu_list": "0-3", "threads": 4}},
    )

    report = attest.build_report(
        registry=registry,
        proc_root=proc_root,
        dcp_j7_results_root=tmp_path / "missing_dcp_j7",
        trigger="unit_test",
        generated_at="2026-06-12T00:00:00Z",
    )

    assert report["schema_version"] == 4
    assert report["trigger"] == "unit_test"
    assert report["summary"]["process_count"] == 1
    process = report["sections"]["processes"][0]
    assert process["pid"] == 123
    assert process["kind"] == "llama_server"
    assert process["port"] == 8070
    assert process["registry_matches"][0]["registry_section"] == "server_mode.frontdoor"
    assert process["cpus_allowed_list"] == "0-3"
    assert process["start_time"] == "2023-11-14T22:13:20Z"
    assert report["sections"]["feature_flags"]["status"] == "disabled"
    assert report["sections"]["serving_config"][0]["numa_match"] is True
    assert report["sections"]["dcp_j7"]["status"] == "missing"
    assert report["summary"]["issue_count"] == 0


def test_collect_dcp_j7_status_picks_latest_run_and_renders(tmp_path: Path) -> None:
    results_root = tmp_path / "benchmarks" / "results" / "runs" / "dcp_j7"
    old_run = results_root / "20260618T000000Z"
    latest_run = results_root / "20260619T113143Z"
    for run_dir, status in ((old_run, "insufficient"), (latest_run, "hold")):
        run_dir.mkdir(parents=True)
        (run_dir / "summary.json").write_text(
            json.dumps(
                {
                    "decision": {
                        "schema_version": "dcp_j7_decision.v1",
                        "status": status,
                        "recommendation": "keep dcp_pre_assembly default-off",
                        "blockers": ["latency_not_improved", "quality_not_scored"],
                    },
                    "off": {
                        "n": 3,
                        "p50_elapsed_s": 20.219,
                        "errors": 0,
                        "quality_scored": 0,
                    },
                    "on": {
                        "n": 3,
                        "p50_elapsed_s": 32.628,
                        "errors": 0,
                        "quality_scored": 0,
                    },
                    "delta": {"p50_elapsed_pct": -0.6137},
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "meta.json").write_text(
            json.dumps(
                {
                    "mode": "real",
                    "created_at": "2026-06-19T11:31:43+00:00",
                    "host_quiet_confirmed": True,
                    "orch_head_before": "f96a6ab",
                    "orch_head_after": "f96a6ab",
                    "orch_checkout_unchanged": True,
                }
            ),
            encoding="utf-8",
        )
    os.utime(old_run / "summary.json", (1_000_000, 1_000_000))
    os.utime(latest_run / "summary.json", (2_000_000, 2_000_000))

    status = attest.collect_dcp_j7_status(results_root=results_root)

    assert status["latest_run"] == str(latest_run)
    assert status["decision"]["schema_version"] == "dcp_j7_decision.v1"
    assert status["status"] == "hold"
    assert status["blockers"] == ["latency_not_improved", "quality_not_scored"]
    assert status["mode"] == "real"
    assert status["delta"]["p50_elapsed_pct"] == -0.6137

    rendered = attest.render_markdown(
        {
            "generated_at": "2026-06-21T00:00:00Z",
            "trigger": "unit_test",
            "scope": "test",
            "summary": {"process_count": 0, "issue_count": 0, "by_kind": {}, "issues": []},
            "sections": {
                "processes": [],
                "feature_flags": {},
                "serving_config": [],
                "eval_instrument": {},
                "drift": {},
                "dcp_j7": status,
            },
            "pending_sections": [],
        }
    )

    assert "## DCP/J7 Status" in rendered
    assert "Status: `hold`" in rendered
    assert "Blockers: `latency_not_improved, quality_not_scored`" in rendered
