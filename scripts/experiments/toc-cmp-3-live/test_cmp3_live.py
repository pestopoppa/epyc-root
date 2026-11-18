"""Offline read-side checks for paired continuation and exact span custody."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def probe(monkeypatch):
    here = Path(__file__).parent
    shared = here.parent / "toc-cmp-4-live"
    monkeypatch.syspath_prepend(str(shared))
    for name, path in (("cmp4_runner", shared / "runner.py"), ("cmp3_live", here / "cmp3_live.py")):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
    return module


def dump(path, body):
    path.write_text(json.dumps(body), encoding="utf-8")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_wire(root, name, kind, prompt, *, complete=True, boundaries=None):
    request = root / f"{name}.request"
    response = root / f"{name}.response"
    dump(request, {"messages": [{"role": "user", "content": prompt}]})
    dump(response, {"choices": [{"message": {"content": "model-generated"}}]})
    return {
        "call_kind": kind, "graph_turn": 3, "history_boundaries": boundaries or [],
        "request_file": request.name, "request_sha256": sha(request.read_text()),
        "response_file": response.name, "response_sha256": sha(response.read_text()),
        "stream_requested": False, "response_complete": complete, "http_status": 200,
    }


def evidence(probe, root, *, arm=1, boundary=True, contract=True, complete=True):
    cases = json.loads((probe.HERE / "cases.json").read_text())
    case = cases[0]
    row = probe.schedule(cases)[arm]
    framed = "[Execution brief v1]\nFull brief\n[Pinned governance 2]\n€é\n[End contract]\n"
    (root / "EXPECTED-CONTRACT.txt").write_text(framed, encoding="utf-8")
    prompt = framed if contract else "control prompt\n"
    summary = row["arm"] == "summary_only"
    if not summary:
        log = root / "session.verbatim.md"
        span = case["marker"] + " café"
        log.write_text(f"fixture:\n{span}\n", encoding="utf-8")
        prompt += (f'[Verbatim manifest: omitted fixture]\nTurn 1 output chars={len(span)} '
                   f'sha256={sha(span)} peek({len(span)}, file_path="{log}", offset=9)\n')
    wire = [make_wire(root, "generation", "generation", prompt, complete=complete, boundaries=[3])]
    if summary:
        wire.insert(0, make_wire(root, "summary", "summary", case["marker"]))
    dump(root / "GRAPH.json", {"wire": wire, "correct": False, "grade_reason": None})
    events = [
        {"event": "boundary", "turn": 3, "summary_tokens": 30 if summary else 0},
        {"event": "turn", "turn": 3, "prompt_tokens": 1234, "completion_tokens": 8},
    ] if boundary else []
    events.append({
        "event": "final", "arm": row["arm"], "trial_index": 0, "context_budget_tokens": probe.BUDGET,
        "effective_context_budget_tokens": probe.BUDGET, "trigger_fraction": 0.5,
        "history_valid": True, "terminal_state": "finished",
    })
    (root / "trial.trajectory.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events))
    return row, case


def test_frozen_pairing_and_no_answer_in_task_or_governance(probe):
    cases = json.loads((probe.HERE / "cases.json").read_text())
    rows = probe.schedule(cases)
    assert len(rows) == 6
    assert [r["label"] for r in rows[:3]] == list(reversed([r["label"] for r in rows[3:]]))
    for case in cases:
        assert {r["sampling_seed"] for r in rows if r["task_id"] == case["id"]} == {case["seed"]}
        assert case["ticket"] not in probe.trial_case(case)["prompt"] + case["governance"]


@pytest.mark.parametrize(("arm", "contract"), [(0, False), (1, True), (2, True)])
def test_qualified_arms(probe, tmp_path, arm, contract):
    row, case = evidence(probe, tmp_path, arm=arm, contract=contract)
    result = probe.assess(tmp_path, row, case)
    assert result["status"] == "observed"
    assert result["contract_delivered"] is contract
    assert result["continuation_prompt_tokens"] == 1234
    assert result["correct"] is False


def test_early_finish_and_incomplete_response_are_unknown(probe, tmp_path):
    row, case = evidence(probe, tmp_path, boundary=False)
    assert probe.assess(tmp_path, row, case)["reason"] == "boundary_not_reached"
    row, case = evidence(probe, tmp_path, complete=False)
    result = probe.assess(tmp_path, row, case)
    assert result["status"] == "unknown"
    assert result["contract_delivered"] is None


def test_contract_in_state_without_wire_delivery_fails(probe, tmp_path):
    row, case = evidence(probe, tmp_path, contract=False)
    assert probe.assess(tmp_path, row, case)["reason"] == "contract_delivery_mismatch"


def test_manifest_uses_exact_log_span_digest(probe, tmp_path):
    row, case = evidence(probe, tmp_path, arm=2)
    (tmp_path / "session.verbatim.md").write_text(case["marker"] + " wrong")
    with pytest.raises(ValueError, match="omission manifest digest or span mismatch"):
        probe.assess(tmp_path, row, case)


def test_cmp4_default_server_argv_and_new_port(probe):
    server = probe.live.server_argv(4)
    assert server[server.index("--port") + 1] == str(probe.live.PORT)
    cmp3 = probe.live.server_argv(4, probe.PORT)
    assert cmp3[cmp3.index("--port") + 1] == str(probe.PORT)
    assert [token for token in server if token != str(probe.live.PORT)] == [
        token for token in cmp3 if token != str(probe.PORT)
    ]


def test_real_child_receives_case_and_sets_candidate_contract(probe, tmp_path):
    if not probe.SOURCE.is_dir() or not probe.live.PYTHON.is_file():
        pytest.skip("prepared candidate and orchestrator venv required")
    cases = json.loads((probe.HERE / "cases.json").read_text())
    row = probe.schedule(cases)[1]
    dump(tmp_path / "INPUT.json", {"row": row, "case": probe.trial_case(cases[0]),
        "source": str(probe.SOURCE), "endpoint": probe.ENDPOINT, "temperature": 0.3, "smoke": True})
    script = """
import asyncio
import runpy
import socket
import sys

class GraphInitialized(Exception):
    pass

def reject_network(*_args, **_kwargs):
    raise AssertionError("offline initialization attempted network I/O")

def inspect_graph(coroutine):
    try:
        from src.features import features
        from src.graph.compaction_artifacts import ExecutionBrief, PinnedGovernance, render_contract
        state = coroutine.cr_frame.f_locals["state"]
        assert features().context_compaction_contract
        assert state.max_turns - 3 > 3
        assert render_contract(
            ExecutionBrief(**state.compaction_execution_brief),
            PinnedGovernance(**state.compaction_pinned_governance),
        ).encode("utf-8") == open("EXPECTED-CONTRACT.txt", "rb").read()
    finally:
        coroutine.close()
    raise GraphInitialized

asyncio.run = inspect_graph
socket.socket.connect = reject_network
try:
    runpy.run_path(sys.argv.pop(1), run_name="__main__")
except GraphInitialized:
    pass
else:
    raise AssertionError("child did not initialize the real graph")
"""
    env = probe.live.graph_env(row, tmp_path, "offline")
    env["PYTHONPATH"] = os.pathsep.join((str(probe.HERE), str(probe.HERE.parent / "toc-cmp-4-live")))
    result = subprocess.run([str(probe.live.PYTHON), "-B", "-c", script, str(probe.HERE / "trial.py"), str(tmp_path)],
                            cwd=tmp_path, env=env, text=True, capture_output=True, timeout=25)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("allocated,threads,expected", [
    ({0, 1, 2, 3, 96, 97, 98, 99}, "4", [0, 1, 2, 3]),
    ({0, 1, 2, 3}, "4", [0, 1, 2, 3]),
    ({96, 97, 98, 99}, "4", [96, 97, 98, 99]),
    ({0, 1, 2, 96, 97, 98}, "4", None),
    ({0, 1, 2, 3}, "3", None),
])
def test_grant_affinity_binding(probe, monkeypatch, allocated, threads, expected):
    current = set(allocated)
    def bind(_pid, cpus):
        nonlocal current
        assert set(cpus) <= current
        current = set(cpus)
    monkeypatch.setenv("FILLER_THREADS", threads)
    monkeypatch.setattr(probe.live.os, "sched_getaffinity", lambda _: current)
    monkeypatch.setattr(probe.live.os, "sched_setaffinity", bind)
    if expected is None:
        with pytest.raises(ValueError):
            probe.live.bind_four_cores()
    else:
        assert probe.live.bind_four_cores() == expected
        assert current == set(expected)
