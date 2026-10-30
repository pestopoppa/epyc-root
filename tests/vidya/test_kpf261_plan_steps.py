"""Portable refusal and CLI coverage; full native canary uses the pinned producer capture."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
import cli
from adapters.kpf261_plan_steps import project, validate_plan_binding
from claim_tuple import ProjectionError


def test_synthetic_capture_is_refused_by_cli(tmp_path, capsys):
    (tmp_path / "protocol.json").write_text(json.dumps({
        "schema": "kpf261.real-planner.protocol.v1", "synthetic": True,
    }))
    (tmp_path / "capture-complete.json").write_text(json.dumps({"synthetic": True}))
    rc = cli.main(["--ledger", str(tmp_path / "ledger.jsonl"), "--json", "ingest",
                   "kpf261-plan-steps", "--path", str(tmp_path),
                   "--as-of", "2026-10-30T15:00:00Z"])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert report["frames_emitted"] == 0
    assert "synthetic" in report["refused"][0]["reason"]


def test_malformed_capture_is_a_refusal(tmp_path):
    (tmp_path / "protocol.json").write_text("{")
    with pytest.raises(ProjectionError, match="invalid planner capture"):
        project(tmp_path)


def test_task_and_initial_prompt_bind_to_corpus():
    row = {"original_action": "original", "objective": "goal", "context": {"prior": "x"}}
    context = json.dumps({"objective": "goal", "prior_context": {"prior": "x"}},
                         ensure_ascii=False, sort_keys=True)
    task = {"objective": "original", "context": context}
    build = lambda objective, ctx: objective + ctx
    initial = {"prompt": build("original", context)}
    validate_plan_binding(task, row, initial, build)
    with pytest.raises(ProjectionError, match="task differs"):
        validate_plan_binding({**task, "objective": "substituted"}, row, initial, build)
    with pytest.raises(ProjectionError, match="initial prompt differs"):
        validate_plan_binding(task, row, {"prompt": "substituted"}, build)


def test_v2_checkpoint_rederives_position_and_journal(tmp_path):
    import hashlib
    from adapters.kpf261_plan_steps import validate_v2_checkpoints

    corpus = [{"source_window": 1, "step": "a"}, {"source_window": 1, "step": "b"}]
    records = [{"task_id": "win1-b", "data": {"steps": [{"action": "x"}]}}]
    raw = (json.dumps(records[0]) + "\n").encode()
    complete = {"plans_attempted": 1, "next_corpus_position": 2, "corpus_exhausted": True, "count_target_met": False}
    checkpoint = {"plans_attempted": 1, "next_corpus_position": 2,
                  "journal_actions": 1, "journal_sha256": hashlib.sha256(raw).hexdigest()}
    path = tmp_path / "smoke-checkpoint.json"
    path.write_text(json.dumps(checkpoint))
    validate_v2_checkpoints(tmp_path, complete, records, corpus, raw, True)
    checkpoint["journal_actions"] = 2
    path.write_text(json.dumps(checkpoint))
    with pytest.raises(ProjectionError, match="checkpoint journal"):
        validate_v2_checkpoints(tmp_path, complete, records, corpus, raw, True)
    with pytest.raises(ProjectionError, match="counter"):
        validate_v2_checkpoints(tmp_path, {**complete, "next_corpus_position": 1}, records, corpus, raw, True)


def test_v2_primary_rejects_resealed_wire_substitution(tmp_path):
    import base64
    import hashlib
    from adapters.kpf261_plan_steps import validate_v2_primary

    schema = {"items": {"properties": {"id": {}, "action": {}}}}
    prompt = "original prompt"
    result = json.dumps([{"id": "s1", "action": "work"}])
    initial = {"args": [], "prompt": prompt, "kwargs": {"role": "architect_critic",
               "n_tokens": 256, "json_schema": schema, "skip_suffix": True}}
    (tmp_path / "call-000-request.json").write_text(json.dumps(initial))
    (tmp_path / "call-000-response.json").write_text(json.dumps({"result": result}))
    def wire(name, body, **extra):
        raw = body.encode()
        (tmp_path / name).write_text(json.dumps({"body_base64": base64.b64encode(raw).decode(),
            "body_sha256": hashlib.sha256(raw).hexdigest(), **extra}))
    wire("wire-000-request.json", json.dumps({"prompt": prompt, "n_predict": 256,
         "json_schema": schema}), url="http://localhost/completion")
    wire("wire-000-response.json", json.dumps({"content": result}), status=200)
    parse = lambda text: json.loads(text)
    steps = json.loads(result)
    validate_v2_primary(tmp_path, initial, steps, parse, schema)
    wire("wire-000-request.json", json.dumps({"prompt": prompt + " forged", "n_predict": 256,
         "json_schema": schema}), url="http://localhost/completion")
    with pytest.raises(ProjectionError, match="wire primary request"):
        validate_v2_primary(tmp_path, initial, steps, parse, schema)


def test_v2_repair_calls_are_replayed_and_extra_rpc_refused(tmp_path, monkeypatch):
    import base64
    import hashlib
    from adapters import kpf261_plan_steps as adapter

    schema = {"items": {"properties": {"id": {}, "action": {}}}}
    primary = {"args": [], "prompt": "task", "kwargs": {"role": "architect_critic",
               "n_tokens": 256, "json_schema": schema, "skip_suffix": True}}
    repair = {"args": [], "prompt": "native repair prompt", "kwargs": {
              "role": "architect_critic", "json_schema": schema, "skip_suffix": True}}
    steps = [{"id": "S1", "action": "work"}]
    responses = ["malformed S1 work", json.dumps(steps)]
    for i, request in enumerate((primary, repair)):
        (tmp_path / f"call-{i:03d}-request.json").write_text(json.dumps(request))
        (tmp_path / f"call-{i:03d}-response.json").write_text(json.dumps({"result": responses[i]}))
        for kind, payload in (("request", {"prompt": request["prompt"], "n_predict": 256,
                                           "json_schema": schema}),
                              ("response", {"content": responses[i]})):
            raw = json.dumps(payload).encode()
            envelope = {"body_base64": base64.b64encode(raw).decode(),
                        "body_sha256": hashlib.sha256(raw).hexdigest()}
            envelope.update({"url": "http://localhost/completion"} if kind == "request" else {"status": 200})
            (tmp_path / f"wire-{i:03d}-{kind}.json").write_text(json.dumps(envelope))
    seen = []
    def replay(root, manifest, raw, calls):
        seen.append((raw, calls))
        return steps
    monkeypatch.setattr(adapter, "replay_native_plan", replay)
    adapter.validate_v2_primary(tmp_path, primary, steps, lambda raw: [], schema, tmp_path, {})
    assert seen == [(responses[0], [(repair, responses[1])])]
    for kind in ("request", "response"):
        (tmp_path / f"wire-999-{kind}.json").write_text((tmp_path / f"wire-001-{kind}.json").read_text())
    with pytest.raises(ProjectionError, match="unmatched completion"):
        adapter.validate_v2_primary(tmp_path, primary, steps, lambda raw: [], schema, tmp_path, {})


def test_native_count_is_one_capture_observation(tmp_path, monkeypatch):
    import hashlib
    from adapters import kpf261_plan_steps as adapter
    from claim_tuple import grade, to_frames

    (tmp_path / "journal").mkdir()
    steps = [{"step_id": "S1"}, {"step_id": "S2"}]
    row = {"schema": "epyc.plan_steps_parsed.v1", "task_id": "t1", "timestamp": "2026-10-30T18:42:01Z",
           "data": {"plan_id": "t1", "n_steps": 2, "step_ids": ["S1", "S2"], "steps": steps}}
    raw = (json.dumps(row) + "\n").encode()
    (tmp_path / "journal" / "plan_steps_parsed.jsonl").write_bytes(raw)
    (tmp_path / "protocol.json").write_text(json.dumps({"schema": "kpf261.real-planner.protocol.v2",
        "synthetic": True, "corpus_sha256": "fixture", "fixture_model_file": "fixture.gguf"}))
    (tmp_path / "capture-complete.json").write_text(json.dumps({"synthetic": True,
        "journal_sha256": hashlib.sha256(raw).hexdigest(), "journal_actions": 2, "count_target_met": False}))
    (tmp_path / "corpus.jsonl").write_text("{}\n")
    monkeypatch.setattr(adapter, "validate_native", lambda *args: None)
    monkeypatch.setattr(adapter, "validate_v2_checkpoints", lambda *args: None)
    tup = adapter.project(tmp_path, allow_synthetic=True)
    assert tup.value == 2 and tup.unit == "actions" and tup.reps == 1
    assert tup.extra["journal_actions"] == 2 and tup.protocol_id == ""
    assert tup.observation["outcome_native"] == "count_target_not_met"
    assert tup.observation["mechanism"]["id"].startswith("kpf261-plan-actions/5778d55d01ea/")
    assert grade(tup)[:2] == ("Judged", "Located")
    frame = to_frames(tup, as_of="2026-10-30T19:00:00Z", adapter_id=adapter.ADAPTER_ID)[-1]
    assert frame["assertion"]["value"] == 2 and frame["assertion"]["unit"] == "actions"
    assert frame["assertion"]["reps"] == 1
