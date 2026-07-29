"""Adversarial contract tests for the sealed E8 evidence validator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from collections import Counter
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "artifacts/operator/prepare_e8_quality_baseline_reseed_20260726.sh"
ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
RESEARCH = Path("/mnt/raid0/llm/epyc-inference-research")
RUNNER = ORCH / "scripts/benchmark/run_e8_quality_baseline_reseed.py"
RATIFIER = ROOT / "artifacts/operator/ratify_e8_quality_baseline_protocol_repair_20260727.sh"
RECEIPT_NAME = "ratify_e8_quality_baseline_protocol_repair_20260727.json"

_RUNNER_SPEC = importlib.util.spec_from_file_location("e8_root_test_runner", RUNNER)
assert _RUNNER_SPEC is not None and _RUNNER_SPEC.loader is not None
runner = importlib.util.module_from_spec(_RUNNER_SPEC)
sys.modules[_RUNNER_SPEC.name] = runner
_RUNNER_SPEC.loader.exec_module(runner)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _canonical(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _fast_judge_trace(answer: str, expected: str, config: dict) -> dict:
    expected_call = runner.expected_judge_request(
        answer,
        expected,
        config,
        default_api_url="http://127.0.0.1:8000",
    )
    return {
        "schema": "epyc.e8_quality_llm_judge_trace.v1",
        "correlation_sha256": runner.judge_correlation_sha256(
            answer, expected, config
        ),
        "scorer_answer": runner._normalized_scorer_answer(answer),
        "expected": expected,
        "scoring_config": config,
        "candidate": expected_call["candidate"],
        "judge_prompt": None,
        "judge_role": None,
        "mode": "substring_fast_path",
        "request": None,
        "response": None,
        "http_error": None,
        "parsed_verdict": True,
        "error": None,
        "started_at": "2026-07-26T00:00:00Z",
        "finished_at": "2026-07-26T00:00:00Z",
        "source_sha256": {
            "debug_scorer": _hash(runner.DEBUG_SCORER_SOURCE),
            "seeding_scoring": _hash(runner.SCORING_SOURCE),
        },
    }


def _runtime_binding(tmp_path: Path, ports: list[int]) -> dict:
    runtime_dir = (tmp_path / "runtime").resolve()
    runtime_dir.mkdir(parents=True)
    binary = runtime_dir / "llama-server"
    binary.write_bytes(b"frozen-v8-test-binary")
    binary.chmod(0o755)
    models = {}
    mmprojs = {}
    for port in ports:
        models[port] = runtime_dir / f"model-{port}.gguf"
        mmprojs[port] = runtime_dir / f"mmproj-{port}.gguf"
        models[port].write_bytes(f"model-{port}".encode())
        mmprojs[port].write_bytes(f"mmproj-{port}".encode())
    cmdlines = {
        str(port): [
            str(binary),
            "-m",
            str(models[port]),
            "--mmproj",
            str(mmprojs[port]),
            "--port",
            str(port),
            "--ctx-size",
            "4096",
        ]
        for port in ports
    }
    topology = [{"port": port, "roles": ["test_role"]} for port in ports]
    artifact_paths = [binary, *models.values(), *mmprojs.values()]
    runtime_artifacts = {}
    for path in artifact_paths:
        info = path.stat()
        runtime_artifacts[str(path)] = {
            "path": str(path),
            "st_dev": info.st_dev,
            "st_ino": info.st_ino,
            "st_size": info.st_size,
            "st_mtime_ns": info.st_mtime_ns,
            "sha256": _hash(path),
        }
    return {
        "runtime_facts_sha256": "1" * 64,
        "stack_priors_sha256": "2" * 64,
        "orchestrator_state_sha256": "3" * 64,
        "model_registry_sha256": "4" * 64,
        "lean_registry_sha256": "5" * 64,
        "stack_numa_mode": "both",
        "selected_ports": ports,
        "server_pids": {str(port): 100000 + port for port in ports},
        "server_binaries": {str(port): str(binary) for port in ports},
        "server_cmdlines": cmdlines,
        "server_cmdline_sha256": {
            port: _canonical(cmdline) for port, cmdline in cmdlines.items()
        },
        "server_model_flags": {
            str(port): {
                "model": [str(models[port])],
                "mmproj": [str(mmprojs[port])],
                "draft_model": [],
            }
            for port in ports
        },
        "server_state_model_paths": {
            str(port): str(models[port]) for port in ports
        },
        "runtime_artifacts": runtime_artifacts,
        "llama_server": str(binary),
        "llama_source_provenance": runner.frozen_llama_source_provenance(),
        "runtime_topology": topology,
        "llama_server_sha256": _hash(binary),
        "llama_server_version": "llama-server version 10107",
    }


def _write_test_pool_override(tmp_path: Path, *, repaired: bool) -> Path:
    """Pin the historical scorer state without mutating the live question pool."""
    root = tmp_path / "research-override"
    module_path = root / "scripts/benchmark/question_pool.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text(
        f'''from __future__ import annotations

import importlib.util
from pathlib import Path

SOURCE = Path({str(RESEARCH / "scripts/benchmark/question_pool.py")!r})
spec = importlib.util.spec_from_file_location("e8_live_question_pool", SOURCE)
assert spec is not None and spec.loader is not None
live_pool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live_pool)
POOL_FILE = live_pool.POOL_FILE
_AFFECTED = {{"real_suite_v1_0043", "needle_039"}}
_EXTRACT_PATTERN = r"(\\d+)" if {repaired!r} else r"\\d+"


def load_pool(*args, **kwargs):
    pool = live_pool.load_pool(*args, **kwargs)
    return {{
        suite: [
            {{**row, "scoring_config": {{**row["scoring_config"], "extract_pattern": _EXTRACT_PATTERN}}}}
            if row.get("id") in _AFFECTED else row
            for row in rows
        ]
        for suite, rows in pool.items()
    }}
'''
    )
    return root


def _fixed_vectors(
    tmp_path: Path, *, use_valid_test_pool: bool
) -> tuple[object, dict[int, dict], dict[int, dict], dict[int, list[dict]]]:
    previous = os.environ.get("EPYC_RESEARCH_ROOT")
    os.environ["EPYC_RESEARCH_ROOT"] = str(
        _write_test_pool_override(tmp_path, repaired=use_valid_test_pool)
    )
    try:
        vectors: dict[int, dict] = {}
        scoring_vectors: dict[int, dict] = {}
        questions_by_tier: dict[int, list[dict]] = {}
        tower = runner.EvalTower(url="http://127.0.0.1:8000", timeout=1)
        for tier, n in ((1, 50), (2, 500)):
            questions, core_id = runner.question_vector(
                tower,
                tier=tier,
                t1_core_id="core_v2",
                n=n,
                seed=runner.EVAL_SPEC_SEED,
            )
            vector = runner.public_vector(
                questions,
                tier=tier,
                core_id=core_id,
                seed=runner.EVAL_SPEC_SEED,
            )
            scoring_vector = runner.scoring_vector(
                questions,
                tier=tier,
                core_id=core_id,
                seed=runner.EVAL_SPEC_SEED,
            )
            vectors[tier] = vector
            scoring_vectors[tier] = scoring_vector
            questions_by_tier[tier] = questions
    finally:
        if previous is None:
            os.environ.pop("EPYC_RESEARCH_ROOT", None)
        else:
            os.environ["EPYC_RESEARCH_ROOT"] = previous
    return tower, vectors, scoring_vectors, questions_by_tier


def _evidence(tmp_path: Path, *, use_valid_test_pool: bool = True) -> Path:
    bundle_dir = (tmp_path / "evidence").resolve()
    receipt_path = (
        tmp_path / "artifacts/operator" / RECEIPT_NAME
    ).resolve()
    runner_hash = _hash(RUNNER)
    tower, vectors, scoring_vectors, questions_by_tier = _fixed_vectors(
        tmp_path, use_valid_test_pool=use_valid_test_pool
    )
    for tier in (1, 2):
        vector = vectors[tier]
        scoring_vector = scoring_vectors[tier]
        _write(bundle_dir / f"question_vector.T{tier}.json", vector)
        _write(bundle_dir / f"scoring_vector.T{tier}.json", scoring_vector)

    ports = list(range(8070, 8094))
    binding = _runtime_binding(tmp_path, ports)
    measurement_source_sha256 = {
        str(path): _hash(path)
        for path in runner.measurement_source_paths(
            runner.parse_args(["--protocol-proposal"])
        )
    }
    protocol = {
        "protocol_id": "e8_quality_full_pool_tier_baseline.v3",
        "seed": 42,
        "repetitions": 3,
        "generation_concurrency": 3,
        "scoring_concurrency": 3,
        "request_timeout_s": 300,
        "frontdoor_request_contract": {
            "force_role": "frontdoor",
            "force_mode": "direct",
            "allow_delegation": False,
            "request_priority": "background",
            "workload_class": "eval_batch",
            "max_queue_wait_ms": 90000,
            "verification": "all_routes_frontdoor",
        },
        "watcher_contract": {
            "active_load_scope": "per_tier_repetition",
            "allowed_probe_failure_reason": "read_timeout",
            "requires_http_200": True,
            "requires_models_loaded": 6,
            "requires_status": "degraded",
            "requires_exact_preflight_probe_urls": True,
            "preserves_binding_immutability_autopilot_checks": True,
        },
        "baseline_mode": "direct_core_only_v1",
        "route_policy": "frontdoor_only",
        "judge_defaults": {
            "orchestrator_api_url": "http://127.0.0.1:8000",
            "role": "worker_general",
        },
        "selected_ports": ports,
        "runtime_topology": binding["runtime_topology"],
        "runtime_facts_sha256": binding["runtime_facts_sha256"],
        "runtime_binding": binding,
        "llama_source_provenance": runner.frozen_llama_source_provenance(),
        "measurement_source_sha256": measurement_source_sha256,
        "expected_probe_groups": [
            "architect_general",
            "coder_escalation/frontdoor/worker_summarize",
            "ingest_long_context",
            "toolrunner/worker_general/worker_math",
            "vision_escalation",
            "worker_vision",
        ],
        "tiers": {
            str(tier): {
                "core_id": vector["core_id"],
                "n": vector["n"],
                "dataset_sha256": vector["dataset_sha256"],
                "scoring_vector_sha256": _canonical(scoring_vectors[tier]),
                "vector_sha256": _canonical(vector),
            }
            for tier, vector in vectors.items()
        },
    }
    receipt = {
        "schema": "epyc.operator_e8_quality_baseline_protocol.v2",
        "decision": "RATIFY-E8-QUALITY-BASELINE-PROTOCOL-REPAIR-20260727",
        "era": "E8",
        "ratified_at": "2026-07-26T00:00:00+00:00",
        "operator_attestation": "operator-test",
        "t2_decision": {
            "n": 500,
            "recommended_default": 500,
            "alternatives": [500],
        },
        "protocol": protocol,
        "t1_core_file_sha256": _hash(tower._core_path("core_v2")),
        "expected_probe_groups": protocol["expected_probe_groups"],
        "acceptance": {
            "all_three_repetitions_clean": True,
            "no_monitor_gap_seconds": 7,
            "api_groups_exact": True,
            "all_routes_frontdoor": True,
            "sealed_atomic_publish": True,
        },
        "sha256": {"runner": runner_hash},
        "repository_heads": {
            "epyc_root": subprocess.check_output(
                ["git", "-C", ROOT, "rev-parse", "HEAD"], text=True
            ).strip(),
            "epyc_orchestrator": subprocess.check_output(
                ["git", "-C", ORCH, "rev-parse", "HEAD"], text=True
            ).strip(),
            "epyc_inference_research": subprocess.check_output(
                ["git", "-C", RESEARCH, "rev-parse", "HEAD"], text=True
            ).strip(),
        },
        "supersedes": {
            "historical_receipt": {
                "path": str((ROOT / "artifacts/operator/ratify_e8_quality_baseline_protocol_20260726.json").resolve()),
                "sha256": "f79ac3664ae2d8eabe181c095afc55a94ee61a49dc19d85a830ed10b4501aded",
            },
            "aborted_run_classification": {
                "path": str((ROOT / "artifacts/operator/aborted-e8-quality-baseline-evidence-20260727T120846Z-monitor-and-request-timeouts/classification.json").resolve()),
                "sha256": "5660c3c38446498cdfd225a64d27da969fd62d262baf46bde2e11395212fdd44",
            },
        },
    }
    _write(receipt_path, receipt)

    sources = []
    bundle_paths: list[Path] = []
    quality_values_by_tier: dict[str, list[float]] = {}
    for tier, vector in vectors.items():
        observations = []
        responses = []
        scoring_vector = scoring_vectors[tier]
        rows = []
        judge_traces = []
        for question, scoring_question in zip(
            vector["questions"], scoring_vector["questions"]
        ):
            answer = (
                scoring_question["expected"]
                if question["scoring_method"] == "llm_judge"
                else ""
            )
            correct = bool(
                runner.score_answer_deterministic(
                    answer,
                    scoring_question["expected"],
                    question["scoring_method"],
                    scoring_question["scoring_config"],
                )
            )
            rows.append(
                {
                    "qid": question["qid"],
                    "suite": question["suite"],
                    "scoring_method": question["scoring_method"],
                    "answer": answer,
                    "correct": correct,
                    "error": None,
                    "partial": False,
                    "degraded": False,
                    "route_used": "frontdoor",
                    "scoring_config_sha256": question[
                        "scoring_config_sha256"
                    ],
                }
            )
            if question["scoring_method"] == "llm_judge" and answer:
                assert correct is True
                judge_traces.append(
                    _fast_judge_trace(
                        answer,
                        scoring_question["expected"],
                        scoring_question["scoring_config"],
                    )
                )
        vector_counts = Counter(row["suite"] for row in rows)
        value = 3.0 * sum(row["correct"] for row in rows) / len(rows)
        suite_quality = {
            suite: (
                3.0
                * sum(row["correct"] for row in rows if row["suite"] == suite)
                / count
            )
            for suite, count in vector_counts.items()
        }
        quality_values_by_tier[str(tier)] = [value] * 3
        for repetition in range(1, 4):
            raw_path = bundle_dir / f"raw.T{tier}.r{repetition}.json"
            raw = {
                "q": value,
                "ts": f"2026-07-26T00:00:0{repetition}Z",
                "core_id": vector["core_id"],
                "protocol_id": protocol["protocol_id"],
                "n": vector["n"],
                "era": "E8",
                "per_suite_quality": suite_quality,
                "per_suite_counts": dict(vector_counts),
            }
            _write(raw_path, raw)
            bundle_paths.append(raw_path)
            observations.append(
                {
                    key: raw[key]
                    for key in ("q", "ts", "core_id", "protocol_id", "n", "era")
                }
                | {"path": str(raw_path), "sha256": _hash(raw_path)}
            )

            response_path = bundle_dir / f"responses.T{tier}.r{repetition}.jsonl"
            response_path.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
            )
            sidecar_path = (
                bundle_dir
                / "eval_sidecars"
                / f"question_results.e8-t{tier}-r{repetition}.jsonl"
            )
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            sidecar_rows = [
                {
                    "row_type": "batch_start",
                    "requested_n": vector["n"],
                    "concurrency": 3,
                    "complete": False,
                },
                *[
                    {
                        "row_type": "question_result",
                        "requested_n": vector["n"],
                        "ordinal": index,
                        "answer": row["answer"],
                        "complete": False,
                        "result": {
                            "qid": row["qid"],
                            "suite": row["suite"],
                            "correct": row["correct"],
                            "route": row["route_used"],
                            "scoring_method": row["scoring_method"],
                        },
                    }
                    for index, row in enumerate(rows)
                ],
                {
                    "row_type": "batch_complete",
                    "requested_n": vector["n"],
                    "completed_n": vector["n"],
                    "complete": True,
                },
            ]
            sidecar_path.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in sidecar_rows)
            )
            judge_trace_path = (
                bundle_dir / f"judge_traces.T{tier}.r{repetition}.jsonl"
            )
            judge_question_rows = [
                (ordinal, question)
                for ordinal, question in enumerate(vector["questions"])
                if question["scoring_method"] == "llm_judge"
            ]
            assert len(judge_traces) == len(judge_question_rows)
            judge_trace_path.write_text(
                "".join(
                    json.dumps(
                        row
                        | {
                            "fixed_vector_row": {
                                "tier": tier,
                                "repetition": repetition,
                                "ordinal": ordinal,
                                "qid": question["qid"],
                            }
                        },
                        sort_keys=True,
                    )
                    + "\n"
                    for row, (ordinal, question) in zip(
                        judge_traces, judge_question_rows
                    )
                )
            )
            bundle_paths.extend((response_path, sidecar_path, judge_trace_path))
            responses.append(
                {
                    "path": str(response_path),
                    "sha256": _hash(response_path),
                    "sidecar_path": str(sidecar_path),
                    "sidecar_sha256": _hash(sidecar_path),
                    "judge_trace_path": str(judge_trace_path),
                    "judge_trace_sha256": _hash(judge_trace_path),
                }
            )

        summary_path = bundle_dir / f"summary.T{tier}.json"
        summary = {
            "tier": tier,
            "core_id": vector["core_id"],
            "n": vector["n"],
            "quality": value,
            "per_suite_quality": suite_quality,
            "per_suite_counts": dict(vector_counts),
            "era": "E8",
            "decision_grade": True,
            "observations": observations,
            "question_vector_path": str(bundle_dir / f"question_vector.T{tier}.json"),
            "question_vector_sha256": _hash(
                bundle_dir / f"question_vector.T{tier}.json"
            ),
            "scoring_vector_path": str(
                bundle_dir / f"scoring_vector.T{tier}.json"
            ),
            "scoring_vector_sha256": _hash(
                bundle_dir / f"scoring_vector.T{tier}.json"
            ),
            "response_artifacts": responses,
        }
        _write(summary_path, summary)
        bundle_paths.extend(
            (
                summary_path,
                bundle_dir / f"question_vector.T{tier}.json",
                bundle_dir / f"scoring_vector.T{tier}.json",
            )
        )
        sources.append(
            {
                "tier": tier,
                "path": str(summary_path),
                "sha256": _hash(summary_path),
                "protocol_id": protocol["protocol_id"],
                "core_id": vector["core_id"],
                "n": vector["n"],
                "timestamp": "2026-07-26T00:00:03Z",
                "era": "E8",
                "instrument": "dedicated_full_pool_tier_baseline",
                "quality": value,
                "question_vector_sha256": _canonical(vector),
                "scoring_vector_sha256": _canonical(scoring_vector),
            }
        )

    watch_path = bundle_dir / "runtime_watch.jsonl"
    watch_rows = [
        {
            "started_at": "2026-07-26T00:00:00Z",
            "finished_at": "2026-07-26T00:00:00Z",
            "ok": True,
            "runtime_artifacts": {
                path: {
                    key: value
                    for key, value in identity.items()
                    if key != "sha256"
                }
                for path, identity in binding["runtime_artifacts"].items()
            },
        },
        {
            "started_at": "2026-07-26T00:00:05Z",
            "finished_at": "2026-07-26T00:00:05Z",
            "ok": True,
            "runtime_artifacts": {
                path: {
                    key: value
                    for key, value in identity.items()
                    if key != "sha256"
                }
                for path, identity in binding["runtime_artifacts"].items()
            },
        },
    ]
    watch_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in watch_rows)
    )
    bundle_paths.append(watch_path)

    file_hashes = {
        **measurement_source_sha256,
        str(RUNNER.resolve()): runner_hash,
        str(receipt_path): _hash(receipt_path),
        str((tmp_path / "runtime-facts.json").resolve()): binding["runtime_facts_sha256"],
        str((tmp_path / "stack-priors.yaml").resolve()): binding["stack_priors_sha256"],
        str((tmp_path / "orchestrator-state.json").resolve()): binding[
            "orchestrator_state_sha256"
        ],
        str((tmp_path / "model-registry.yaml").resolve()): binding["model_registry_sha256"],
        str((tmp_path / "lean-registry.yaml").resolve()): binding["lean_registry_sha256"],
    }
    report_path = bundle_dir / "runner_report.json"
    report = {
        "decision_grade": True,
        "preconditions": {
            "numeric_rerun": {"completed": 16, "required": 16},
            "file_sha256": file_hashes,
            "runtime_binding": binding,
            "protocol_receipt": str(receipt_path),
            "protocol_receipt_sha256": _hash(receipt_path),
            "runner_path": str(RUNNER.resolve()),
            "runner_sha256": runner_hash,
        },
        "postconditions": {
            "numeric_rerun": {"completed": 16, "required": 16},
            "file_sha256": file_hashes,
            "runtime_binding": binding,
            "watcher_path": str(watch_path),
            "watcher_sha256": _hash(watch_path),
            "watcher_samples": watch_rows,
            "checks": {
                "continuous_clean_monitor": True,
                "numeric_rerun_unchanged": True,
                "all_clean_repetitions": True,
            },
        },
    }
    _write(report_path, report)
    bundle_paths.append(report_path)

    manifest_path = bundle_dir / "e8_quality_baseline_evidence.json"
    manifest = {
        "schema": "epyc.e8_quality_baseline_evidence.v2",
        "eval_quality_era": "E8",
        "source_records": sources,
        "replacement": {
            "baseline_state": {
                "eval_quality_era": "E8",
                "baselines_by_tier": {
                    str(source["tier"]): source["quality"] for source in sources
                },
                "per_suite_quality_by_tier": {
                    str(source["tier"]): json.loads(
                        Path(source["path"]).read_text()
                    )["per_suite_quality"]
                    for source in sources
                },
                "per_suite_counts_by_tier": {
                    str(tier): vectors[tier]["per_suite_counts"]
                    for tier in (1, 2)
                },
            },
            "quality_history_by_tier": quality_values_by_tier,
            "quality_history_provenance_by_tier": {
                str(tier): [
                    {
                        "q": q,
                        "ts": f"2026-07-26T00:00:0{repetition}Z",
                        "era": "E8",
                        "core_id": vectors[tier]["core_id"],
                    }
                    for repetition, q in enumerate(
                        quality_values_by_tier[str(tier)], 1
                    )
                ]
                for tier in (1, 2)
            },
        },
        "protocol_receipt": {
            "path": str(receipt_path),
            "sha256": _hash(receipt_path),
        },
        "runner": {"path": str(RUNNER.resolve()), "sha256": runner_hash},
        "run_seal_path": str(bundle_dir / "run_seal.json"),
    }
    _write(manifest_path, manifest)
    bundle_paths.append(manifest_path)
    seal = {
        "schema": "epyc.e8_quality_baseline_run_seal.v1",
        "status": "complete",
        "manifest_sha256": _hash(manifest_path),
        "runner_report_sha256": _hash(report_path),
        "protocol_receipt_sha256": _hash(receipt_path),
        "runner_sha256": runner_hash,
        "bundle_sha256": {
            str(path.resolve()): _hash(path) for path in dict.fromkeys(bundle_paths)
        },
        "completed_at": "2026-07-26T00:00:10Z",
    }
    _write(bundle_dir / "run_seal.json", seal)
    return manifest_path


def _reseal(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text())
    paths = [manifest_path, manifest_path.parent / "runner_report.json"]
    report = json.loads(paths[1].read_text())
    watch_path = Path(report["postconditions"]["watcher_path"])
    report["postconditions"]["watcher_sha256"] = _hash(watch_path)
    _write(paths[1], report)
    paths.append(watch_path)
    for source in manifest["source_records"]:
        summary_path = Path(source["path"])
        summary = json.loads(summary_path.read_text())
        for observation in summary["observations"]:
            observation["sha256"] = _hash(Path(observation["path"]))
            paths.append(Path(observation["path"]))
        for response in summary["response_artifacts"]:
            response["sha256"] = _hash(Path(response["path"]))
            response["sidecar_sha256"] = _hash(Path(response["sidecar_path"]))
            response["judge_trace_sha256"] = _hash(
                Path(response["judge_trace_path"])
            )
            paths.extend(
                (
                    Path(response["path"]),
                    Path(response["sidecar_path"]),
                    Path(response["judge_trace_path"]),
                )
            )
        _write(summary_path, summary)
        source["sha256"] = _hash(summary_path)
        paths.extend(
            (
                summary_path,
                Path(summary["question_vector_path"]),
                Path(summary["scoring_vector_path"]),
            )
        )
    receipt_path = Path(manifest["protocol_receipt"]["path"])
    manifest["protocol_receipt"]["sha256"] = _hash(receipt_path)
    _write(manifest_path, manifest)
    seal = {
        "schema": "epyc.e8_quality_baseline_run_seal.v1",
        "status": "complete",
        "manifest_sha256": _hash(manifest_path),
        "runner_report_sha256": _hash(paths[1]),
        "protocol_receipt_sha256": _hash(receipt_path),
        "runner_sha256": _hash(RUNNER),
        "bundle_sha256": {
            str(path.resolve()): _hash(path) for path in dict.fromkeys(paths)
        },
        "completed_at": "2026-07-26T00:00:10Z",
    }
    _write(manifest_path.parent / "run_seal.json", seal)


def _validate(path: Path) -> subprocess.CompletedProcess[str]:
    override = path.parent.parent / "research-override"
    return subprocess.run(
        ["bash", str(SCRIPT), "--validate-evidence", str(path)],
        env={
            **os.environ,
            "EPYC_ROOT": str(path.parent.parent),
            "EPYC_SOURCE_ROOT": str(ROOT),
            "EPYC_ORCH": str(ORCH),
            "EPYC_RESEARCH": str(RESEARCH),
            "EPYC_PYTHON": str(ORCH / ".venv/bin/python"),
            **(
                {"EPYC_RESEARCH_ROOT": str(override)}
                if override.is_dir()
                else {}
            ),
        },
        capture_output=True,
        text=True,
    )


def _assert_validator_rejects(path: Path, message: str) -> None:
    result = _validate(path)
    assert result.returncode != 0
    assert message in result.stderr


def test_plan_documents_operator_receipt_and_sealed_evidence() -> None:
    result = subprocess.run(["bash", str(SCRIPT), "--plan"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "human-ratified protocol receipt" in result.stdout


def test_validator_rejects_constructed_source_vector_scorer_defect(tmp_path: Path) -> None:
    result = _validate(_evidence(tmp_path, use_valid_test_pool=False))
    assert result.returncode != 0
    assert "source vector scorer config is invalid" in result.stderr


def test_validator_rejects_arbitrary_n_core_or_protocol(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["source_records"][1]["n"] = 50
    _write(manifest_path, manifest)
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "source record differs from ratified tier contract")


def test_validator_rejects_noncanonical_t2_decision(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    receipt_path = Path(manifest["protocol_receipt"]["path"])
    receipt = json.loads(receipt_path.read_text())
    receipt["t2_decision"] = {
        "n": 50,
        "recommended_default": 500,
        "alternatives": [500, 50],
    }
    _write(receipt_path, receipt)
    _reseal(manifest_path)
    _assert_validator_rejects(
        manifest_path, "protocol receipt T2 decision is malformed"
    )


def test_validator_rejects_kill_between_manifest_and_seal(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    (manifest_path.parent / "run_seal.json").unlink()
    _assert_validator_rejects(manifest_path, "completion seal is missing")


def test_validator_rejects_monitor_failure_and_stale_numeric_evidence(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    report_path = manifest_path.parent / "runner_report.json"
    report = json.loads(report_path.read_text())
    report["preconditions"]["numeric_rerun"]["completed"] = 15
    report["postconditions"]["checks"]["continuous_clean_monitor"] = False
    _write(report_path, report)
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "runner report contains a failed global check")


def test_validator_rejects_wrong_route_and_sidecar_escape(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    response_path = manifest_path.parent / "responses.T1.r1.jsonl"
    rows = [json.loads(line) for line in response_path.read_text().splitlines()]
    rows[0]["route_used"] = "worker_general"
    response_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "response ledger contains a non-clean result")


def test_validator_rejects_response_order_and_scoring_hash_tampering(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    response_path = manifest_path.parent / "responses.T1.r1.jsonl"
    rows = [json.loads(line) for line in response_path.read_text().splitlines()]
    rows[0], rows[1] = rows[1], rows[0]
    rows[2]["scoring_config_sha256"] = "f" * 64
    response_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "response ledger order or scoring identity differs")


def test_validator_rejects_duplicate_response_qids(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    response_path = manifest_path.parent / "responses.T1.r1.jsonl"
    rows = [json.loads(line) for line in response_path.read_text().splitlines()]
    rows[1]["qid"] = rows[0]["qid"]
    response_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "response ledger order or scoring identity differs")


def test_validator_rejects_fabricated_raw_quality_with_valid_hashes(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    raw_path = manifest_path.parent / "raw.T1.r1.json"
    raw = json.loads(raw_path.read_text())
    raw["q"] = 3.0
    raw["per_suite_quality"] = {"suite": 3.0}
    _write(raw_path, raw)
    summary_path = manifest_path.parent / "summary.T1.json"
    summary = json.loads(summary_path.read_text())
    summary["observations"][0]["q"] = 3.0
    _write(summary_path, summary)
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "raw observation quality is not reproducible")


def test_validator_rejects_resealed_response_correctness_forgery(
    tmp_path: Path,
) -> None:
    manifest_path = _evidence(tmp_path)
    scoring = json.loads(
        (manifest_path.parent / "scoring_vector.T1.json").read_text()
    )
    ordinal = next(
        index
        for index, question in enumerate(scoring["questions"])
        if question["scoring_method"] == "substring"
    )
    response_path = manifest_path.parent / "responses.T1.r1.jsonl"
    rows = [json.loads(line) for line in response_path.read_text().splitlines()]
    rows[ordinal]["answer"] = scoring["questions"][ordinal]["expected"]
    rows[ordinal]["correct"] = False
    response_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    sidecar_path = (
        manifest_path.parent
        / "eval_sidecars/question_results.e8-t1-r1.jsonl"
    )
    sidecar_rows = [
        json.loads(line) for line in sidecar_path.read_text().splitlines()
    ]
    result_row = next(
        row
        for row in sidecar_rows
        if row.get("row_type") == "question_result"
        and row.get("ordinal") == ordinal
    )
    result_row["answer"] = rows[ordinal]["answer"]
    result_row["result"]["correct"] = False
    sidecar_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in sidecar_rows)
    )
    _reseal(manifest_path)

    _assert_validator_rejects(manifest_path, "independent scoring")


def test_validator_rejects_resealed_sidecar_ledger_mismatch(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    sidecar_path = (
        manifest_path.parent
        / "eval_sidecars/question_results.e8-t1-r1.jsonl"
    )
    rows = [json.loads(line) for line in sidecar_path.read_text().splitlines()]
    question_row = next(
        row for row in rows if row.get("row_type") == "question_result"
    )
    question_row["answer"] = "forged sidecar answer"
    sidecar_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    _reseal(manifest_path)

    _assert_validator_rejects(manifest_path, "sidecar differs")


def test_validator_rejects_same_path_runtime_content_mutation(
    tmp_path: Path,
) -> None:
    manifest_path = _evidence(tmp_path)
    receipt = json.loads(
        Path(json.loads(manifest_path.read_text())["protocol_receipt"]["path"]).read_text()
    )
    artifacts = receipt["protocol"]["runtime_binding"]["runtime_artifacts"]
    path_text = next(
        path
        for path in artifacts
        if path != receipt["protocol"]["runtime_binding"]["llama_server"]
    )
    artifact = Path(path_text)
    identity = artifacts[path_text]
    artifact.write_bytes(b"x" * identity["st_size"])
    os.utime(
        artifact,
        ns=(identity["st_mtime_ns"], identity["st_mtime_ns"]),
    )

    _assert_validator_rejects(manifest_path, "runtime artifact changed")


def test_validator_rejects_resealed_repository_head_claim(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    receipt_path = Path(manifest["protocol_receipt"]["path"])
    receipt = json.loads(receipt_path.read_text())
    receipt["repository_heads"]["epyc_inference_research"] = "f" * 40
    _write(receipt_path, receipt)
    _reseal(manifest_path)

    _assert_validator_rejects(manifest_path, "repository heads differ")


def test_validator_rejects_external_sealed_artifact(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    external = (tmp_path / "external-sidecar.jsonl").resolve()
    source = manifest_path.parent / "eval_sidecars/question_results.e8-t1-r1.jsonl"
    shutil.copy2(source, external)
    summary_path = manifest_path.parent / "summary.T1.json"
    summary = json.loads(summary_path.read_text())
    summary["response_artifacts"][0]["sidecar_path"] = str(external)
    _write(summary_path, summary)
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "resolves outside the evidence bundle")


def test_validator_rejects_runtime_cmdline_binding_drift(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    report_path = manifest_path.parent / "runner_report.json"
    report = json.loads(report_path.read_text())
    report["postconditions"]["runtime_binding"]["server_cmdlines"]["8070"][-1] = "8192"
    _write(report_path, report)
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "runner report runtime binding differs")


def test_validator_rejects_receipt_runner_hash_mismatch(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    receipt_path = Path(manifest["protocol_receipt"]["path"])
    receipt = json.loads(receipt_path.read_text())
    receipt["sha256"]["runner"] = "0" * 64
    _write(receipt_path, receipt)
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "protocol receipt does not bind the canonical runner hash")


def test_validator_rejects_noncanonical_receipt_path(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    alternate = (tmp_path / "alternate-receipt.json").resolve()
    shutil.copy2(Path(manifest["protocol_receipt"]["path"]), alternate)
    manifest["protocol_receipt"] = {"path": str(alternate), "sha256": _hash(alternate)}
    _write(manifest_path, manifest)
    _reseal(manifest_path)
    _assert_validator_rejects(manifest_path, "protocol receipt is not at the canonical operator path")


def test_validator_rejects_repaired_request_timeout_drift(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    receipt_path = Path(json.loads(manifest_path.read_text())["protocol_receipt"]["path"])
    receipt = json.loads(receipt_path.read_text())
    receipt["protocol"]["request_timeout_s"] = 120
    _write(receipt_path, receipt)
    _reseal(manifest_path)

    _assert_validator_rejects(manifest_path, "protocol receipt execution contract differs")


def test_validator_rejects_repaired_watcher_contract_drift(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    receipt_path = Path(json.loads(manifest_path.read_text())["protocol_receipt"]["path"])
    receipt = json.loads(receipt_path.read_text())
    receipt["protocol"]["watcher_contract"]["requires_status"] = "ok"
    _write(receipt_path, receipt)
    _reseal(manifest_path)

    _assert_validator_rejects(manifest_path, "protocol receipt watcher contract differs")


def test_validator_rejects_missing_abort_predecessor_binding(tmp_path: Path) -> None:
    manifest_path = _evidence(tmp_path)
    receipt_path = Path(json.loads(manifest_path.read_text())["protocol_receipt"]["path"])
    receipt = json.loads(receipt_path.read_text())
    receipt["supersedes"]["aborted_run_classification"]["sha256"] = "0" * 64
    _write(receipt_path, receipt)
    _reseal(manifest_path)

    _assert_validator_rejects(manifest_path, "protocol receipt predecessor evidence differs")


def test_ratifier_publish_is_create_only_and_durable(tmp_path: Path) -> None:
    script = RATIFIER.read_text()
    marker = '"$PYTHON" - "$tmp" "$OUTPUT" <<\'PY\'\n'
    publish_code = script.split(marker, 1)[1].split("\nPY", 1)[0]
    assert "os.link(source, destination)" in publish_code
    assert publish_code.count("os.fsync(directory_fd)") == 2
    assert "os.fsync(handle.fileno())" in script
    assert "mv --no-clobber" not in script
    assert "sync -f" not in script

    source = tmp_path / "receipt.tmp"
    destination = tmp_path / "receipt.json"
    source.write_text("new")
    destination.write_text("existing")
    raced = subprocess.run(
        [str(ORCH / ".venv/bin/python"), "-", str(source), str(destination)],
        input=publish_code,
        text=True,
        capture_output=True,
    )
    assert raced.returncode != 0
    assert destination.read_text() == "existing"
    assert source.read_text() == "new"

    destination.unlink()
    published = subprocess.run(
        [str(ORCH / ".venv/bin/python"), "-", str(source), str(destination)],
        input=publish_code,
        text=True,
        capture_output=True,
    )
    assert published.returncode == 0, published.stderr
    assert destination.read_text() == "new"
    assert not source.exists()
