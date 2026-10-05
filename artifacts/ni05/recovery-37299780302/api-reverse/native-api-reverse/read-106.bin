from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark import axa2_teleport_policy_trace as trace


def test_trace_accepts_resident_same_quant_cutover():
    args = trace.parse_args(
        [
            "--trace",
            "/tmp/trace.jsonl",
            "--output",
            "/tmp/out",
            "--policy-enabled",
            "--role-allowlist",
            "architect_general",
            "--cpu-quant",
            "q4_k_m",
            "--gpu-quant",
            "q4_k_m",
        ]
    )
    rows = [
        {
            "trace_id": "t1",
            "role": "architect_general",
            "generated_tokens": 200,
            "estimated_remaining_tokens": 160,
            "cpu_tps": 20.0,
            "gpu_tps": 44.0,
            "gpu_available": True,
            "gpu_resident": True,
        }
    ]

    decisions = trace.evaluate_rows(rows, args)

    assert decisions[0]["decision"]["should_cutover"] is True
    assert decisions[0]["decision"]["reason"] == "cutover"
    assert decisions[0]["costs"]["positive_after_load_only"] is True


def test_trace_rejects_cross_quant_by_default():
    args = trace.parse_args(
        [
            "--trace",
            "/tmp/trace.jsonl",
            "--output",
            "/tmp/out",
            "--policy-enabled",
            "--cpu-quant",
            "q4_k_m",
            "--gpu-quant",
            "iq2_m",
        ]
    )

    decisions = trace.evaluate_rows(
        [
            {
                "role": "architect_general",
                "generated_tokens": 200,
                "estimated_remaining_tokens": 500,
                "cpu_tps": 20.0,
                "gpu_tps": 44.0,
                "gpu_available": True,
                "gpu_resident": True,
            }
        ],
        args,
    )

    assert decisions[0]["decision"]["should_cutover"] is False
    assert decisions[0]["decision"]["reason"] == "quant_change_not_allowed"


def test_main_writes_dry_policy_artifacts(tmp_path: Path):
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        json.dumps(
            {
                "trace_id": "t2",
                "role": "architect_general",
                "generated_tokens": 200,
                "estimated_remaining_tokens": 500,
                "cpu_tps": 20.0,
                "gpu_tps": 44.0,
                "gpu_available": True,
                "gpu_resident": True,
                "cpu_quant": "q4_k_m",
                "gpu_quant": "q4_k_m",
            }
        )
        + "\n"
    )
    out = tmp_path / "out"

    rc = trace.main(
        [
            "--trace",
            str(trace_path),
            "--output",
            str(out),
            "--policy-enabled",
        ]
    )

    assert rc == 0
    summary = json.loads((out / "summary.json").read_text())
    assert summary["schema"] == trace.SCHEMA
    assert summary["status"] == "dry_policy_trace_only"
    assert summary["decision_reasons"] == ["cutover"]
    assert summary["cutover_reasons"] == ["cutover"]
    assert summary["no_inference"] is True
    assert (out / "policy_decisions.jsonl").exists()
    decision_lines = (out / "policy_decisions.jsonl").read_text().splitlines()
    assert len(decision_lines) == 1
    assert json.loads(decision_lines[0])["decision"]["should_cutover"] is True
