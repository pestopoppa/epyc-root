"""Offline transport/control tests; no model calls or historical receipt backfills."""
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_beam_reader as launcher
import long_context_adapters as adapters
from beam_scoring import BEAM_ABILITIES


@pytest.fixture
def dataset(tmp_path):
    path = tmp_path / "data" / "100K-00000-of-00001.parquet"
    path.parent.mkdir()
    questions = {a: [{"question": f"Friday sprint question for {a}?", "rubric": ["a fact"],
                      "answer": "fact"}] for a in BEAM_ABILITIES}
    pq.write_table(pa.Table.from_pylist([{
        "conversation_id": "1", "chat": [[
            {"role": "user", "content": "My sprint ends Friday."},
            {"role": "assistant", "content": "I will remember Friday."}]],
        "probing_questions": repr(questions),
    }]), path)
    return path


def run(dataset, output, arm="full", reader=None, **kwargs):
    launcher.prepare_arm(dataset=dataset, expected_sha256=launcher.digest(dataset),
                            output=output, arm=arm, model="reader-Q8",
                            **kwargs)
    return launcher.execute_arm(output, reader or (lambda **kw: {
        "response": "Friday", "finish_reason": "stop"}))


def test_all_arms_receipt_and_checker(dataset, tmp_path, monkeypatch):
    class TraceFixture:
        name = "offline-trace-fixture"

        def __init__(self, chunks, **kwargs):
            self.chunks = chunks

        def __call__(self, question, *, conversation_id, top_k):
            return self.chunks[conversation_id][:top_k]

    monkeypatch.setattr(adapters, "TracePairChunkRetriever", TraceFixture)
    arms = []
    for arm in ("full", "rag", "trace"):
        calls = []
        def reader(**request):
            # Prove that a receipt already exists before the first call.
            assert (tmp_path / arm / "beam_run_receipt.json").is_file()
            calls.append(request)
            return {"response": "Friday", "finish_reason": "stop"}
        receipt = run(dataset, tmp_path / arm, arm, reader)
        assert receipt["status"] == "complete"
        assert receipt["questions_completed"] == len(BEAM_ABILITIES)
        payload = json.loads((tmp_path / arm / "reader.json").read_text())
        for qid, row in payload["results"]["beam"].items():
            assert row["finish_reason"] == "stop"
            assert hashlib.sha256(row["prompt"].encode()).hexdigest() == receipt["prompt_sha256_by_question"][qid]
        for request in calls:
            assert request["model"] == receipt["reader"]["model"]
            assert request["params"]["max_tokens"] == receipt["reader"]["max_tokens"] == 2048
            assert request["params"]["enable_thinking"] is False
            assert "Assistant: I will remember Friday." in request["prompt"]
        arms.append({"arm": arm, "receipt": receipt, "summary": {
            "fold": "beam_macro", "headline": 0.6, "judge_model": "different-judge",
            "truncated_rows": 0}})
    assert len({a["receipt"]["reader"]["prompt_sha256"] for a in arms}) == 1
    # Read the exact historical checker by git object, without copying it into this packet.
    source = subprocess.check_output([
        "git", "-C", "/mnt/raid0/llm/epyc-inference-research", "show",
        "c9aac169b:scripts/benchmark/beam_prerun_checklist.py"], text=True)
    checker = {"__name__": "receipt_test_checker"}
    exec(compile(source, "beam_prerun_checklist.py@c9aac169b", "exec"), checker)
    report = checker["check_arms"](arms, expected_dataset_sha=launcher.digest(dataset), min_max_tokens=2048)
    assert report["cleared"], report
    arms[2]["receipt"]["ingest"]["retrieval_budget"] = 99
    assert checker["check_arms"](arms)["items"][5]["status"] == "FAIL"
    arms[0]["summary"]["truncated_rows"] = 1
    assert checker["check_arms"](arms)["items"][2]["status"] == "FAIL"


def test_wrong_digest_never_calls_reader(dataset, tmp_path):
    with pytest.raises(ValueError, match="digest mismatch"):
        launcher.prepare_arm(dataset=dataset, expected_sha256="0" * 64, output=tmp_path / "run",
                             arm="full", model="reader")
    assert not (tmp_path / "run").exists()


def test_execution_does_not_reload_dataset(dataset, tmp_path, monkeypatch):
    output = tmp_path / "run"
    launcher.prepare_arm(dataset=dataset, expected_sha256=launcher.digest(dataset),
                         output=output, arm="rag", model="reader")
    dataset.unlink()  # No hashing or input extraction occurs inside execution.
    monkeypatch.setattr(adapters.BEAMAdapter, "extract_all", lambda self: pytest.fail("reloaded input"))
    receipt = launcher.execute_arm(output, lambda **kw: {"response": "text", "finish_reason": "stop"})
    assert receipt["status"] == "complete"


def test_materialized_prompts_cannot_change(dataset, tmp_path):
    output = tmp_path / "run"
    launcher.prepare_arm(dataset=dataset, expected_sha256=launcher.digest(dataset),
                         output=output, arm="full", model="reader")
    (output / "prepared-questions.json").write_text("[]")
    with pytest.raises(ValueError, match="prepared questions changed"):
        launcher.execute_arm(output, lambda **kw: pytest.fail("changed prompts were used"))


def test_prompt_drift_refused():
    with pytest.raises(ValueError, match="layout changed"):
        launcher.matched_prompt({"prompt": "new unreviewed header",
                                 "scoring_config": {"probing_question": "q"}}, "full")


def test_ambiguous_dataset_refused(dataset, tmp_path):
    (dataset.parent / "100K-extra.parquet").write_bytes(dataset.read_bytes())
    with pytest.raises(ValueError, match="single 100K"):
        run(dataset, tmp_path / "run")


def test_both_roles_required(dataset, tmp_path):
    table = pq.read_table(dataset).to_pylist()
    table[0]["chat"] = [[{"role": "user", "content": "user only"}]]
    pq.write_table(pa.Table.from_pylist(table), dataset)
    with pytest.raises(ValueError, match="both user and assistant"):
        run(dataset, tmp_path / "run")


def test_failure_keeps_partial_answers(dataset, tmp_path):
    count = 0
    def interrupted(**kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("transport failed")
        return {"response": "partial", "finish_reason": "length"}
    output = tmp_path / "partial"
    with pytest.raises(RuntimeError, match="transport failed"):
        run(dataset, output, reader=interrupted)
    receipt = json.loads((output / "beam_run_receipt.json").read_text())
    assert receipt["status"] == "failed" and receipt["questions_completed"] == 1
    rows = json.loads((output / "reader.json").read_text())["results"]["beam"]
    assert next(iter(rows.values()))["finish_reason"] == "length"
    with pytest.raises(ValueError, match="fresh run directory"):
        run(dataset, output)


def test_missing_finish_reason_is_failure(dataset, tmp_path):
    with pytest.raises(ValueError, match="finish_reason"):
        run(dataset, tmp_path / "run", reader=lambda **kw: {"response": "text"})
    assert json.loads((tmp_path / "run" / "beam_run_receipt.json").read_text())["status"] == "failed"


def test_http_request_controls_and_identity(monkeypatch):
    requests = []
    def transport(req, timeout):
        if isinstance(req, str):
            assert req.endswith("/v1/models")
            return io.BytesIO(b'{"data": [{"id": "reader-Q8"}]}')
        requests.append(json.loads(req.data))
        assert req.full_url.endswith("/v1/chat/completions")
        return io.BytesIO(b'{"choices": [{"message": {"content": "answer"}, "finish_reason": "length"}]}')
    monkeypatch.setattr(launcher, "urlopen", transport)
    with pytest.raises(ValueError, match="server identity"):
        launcher.HTTPReader("http://fixture", "wrong-model")
    client = launcher.HTTPReader("http://fixture", "reader-Q8")
    answer = client(prompt="history", model="reader-Q8", params=adapters.BEAMAdapter.inference_params)
    assert answer == {"response": "answer", "finish_reason": "length"}
    assert requests[0]["messages"] == [{"role": "user", "content": "history"}]
    assert requests[0]["max_tokens"] == 2048
    assert requests[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert requests[0]["temperature"] == 0.0
