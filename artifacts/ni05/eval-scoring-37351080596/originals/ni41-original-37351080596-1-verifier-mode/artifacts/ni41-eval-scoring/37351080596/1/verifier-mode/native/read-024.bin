"""EV-CONF-2 confidence probe driver, run against a mocked OpenAI-compatible endpoint.

No model server is touched. ``httpx.MockTransport`` stands in for llama-server.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (
    REPO_ROOT,
    REPO_ROOT / "scripts" / "autopilot",
    REPO_ROOT / "scripts" / "benchmark",
    REPO_ROOT / "scripts" / "analysis",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import confidence_probe as cp  # noqa: E402
import confidence_source_compare as csc  # noqa: E402
import eval_tower  # noqa: E402

N_WRONG, N_RIGHT = 4, 4

# ── fixtures ──────────────────────────────────────────────────────────────


def _questions(n: int = 12) -> list[dict[str, Any]]:
    return [
        {
            "id": f"gsm8k_{i:05d}",
            "suite": "math",
            "prompt": f"What is {i} + {i}?\n\nSolve step by step. Put your final numeric answer inside <answer></answer> tags.",
            "expected": str(2 * i),
            "scoring_method": "exact_match",
            "scoring_config": {"extract_pattern": r"<answer>(.*?)</answer>"},
        }
        for i in range(n)
    ]


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Any]:
    qs = _questions()
    qpath = tmp_path / "questions.jsonl"
    qpath.write_text("".join(json.dumps(q) + "\n" for q in qs))
    prepared = cp._prepare([dict(q) for q in qs])
    sidecar = tmp_path / "e7c.jsonl"
    lines = [json.dumps({"row_type": "batch_start", "eval_batch_id": "e7c"})]
    for i, q in enumerate(prepared):
        res = {
            "question_id": q["id"],
            "qid": eval_tower._question_result_qid(q),
            "correct": i % 2 == 0,
            "confidence": 1.0,
            "tokens_generated": 100 + i,
        }
        lines.append(json.dumps({"row_type": "question_result", "ordinal": i, "result": res}))
    # an infra-error row that must never be drawn
    lines.append(json.dumps({"row_type": "question_result", "ordinal": 99,
                             "result": {"question_id": "gsm8k_09999", "qid": "x", "correct": False,
                                        "error": "read_timeout"}}))
    sidecar.write_text("\n".join(lines) + "\n")
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"result": {"dataset_sha256": eval_tower.dataset_content_sha256(prepared)}}))
    manifest = cp.build_manifest(sidecar=sidecar, summary=summary, n_wrong=N_WRONG, n_right=N_RIGHT, seed=42)
    return {"tmp": tmp_path, "qpath": qpath, "sidecar": sidecar, "summary": summary,
            "manifest": manifest, "questions": prepared, "out": tmp_path / "out"}


def _tok(text: str, lp: float, alts: bool) -> dict[str, Any]:
    top = [{"token": text, "logprob": lp}]
    if alts:
        top.append({"token": "zz", "logprob": lp - 3.0})
    return {"token": text, "logprob": lp, "bytes": list(text.encode()), "top_logprobs": top}


class FakeServer:
    """Minimal llama-server: /v1/models, /props, /slots, /v1/chat/completions."""

    def __init__(self, *, spec: bool = False, slots: bool = True, placeholders: bool | None = None,
                 wrong_on: set[str] | None = None, fail_first: int = 0) -> None:
        self.spec = spec
        self.slots = slots
        self.placeholders = spec if placeholders is None else placeholders
        self.wrong_on = wrong_on or set()
        self.fail_first = fail_first
        self.chat_payloads: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf"}]})
        if path == "/props":
            return httpx.Response(200, json={
                "model_path": "/models/gemma.gguf", "build_info": "b10125-ef81196d5", "total_slots": 1,
                # llama-server reports defaults here regardless of launch flags
                "default_generation_settings": {"n_ctx": 16384,
                                                "params": {"speculative.types": "none", "speculative.n_max": 16}},
            })
        if path == "/slots":
            if not self.slots:
                return httpx.Response(501, json={"error": "slots endpoint disabled"})
            return httpx.Response(200, json=[{"id": 0, "speculative": self.spec}])
        assert path == "/v1/chat/completions"
        body = json.loads(request.content)
        self.chat_payloads.append(body)
        if self.fail_first > 0:
            self.fail_first -= 1
            return httpx.Response(503, text="loading model")
        prompt = body["messages"][0]["content"]
        n = int(prompt.split("What is ")[1].split(" +")[0])
        val = 2 * n + (1 if f"gsm8k_{n:05d}" in self.wrong_on else 0)
        # the `</answer>` stop fires, so the stream ends inside the tag
        pieces = [("Adding gives $", -0.2), (f"{val}$", -0.4), ("\n\n<answer>", -0.01), (str(val), -0.05 - 0.1 * n)]
        rows = []
        for i, (t, lp) in enumerate(pieces):
            if self.placeholders and i in (1, 2):
                rows.append({"token": t, "logprob": 0.0, "bytes": list(t.encode()), "top_logprobs": []})
            else:
                rows.append(_tok(t, lp, alts=True))
        timings = {"prompt_n": 20, "predicted_n": len(rows), "predicted_per_second": 50.0}
        if self.spec:
            timings |= {"draft_n": 2, "draft_n_accepted": 2}
        return httpx.Response(200, json={
            "model": "gemma",
            "choices": [{"message": {"content": "".join(t for t, _ in pieces)}, "finish_reason": "stop",
                         "logprobs": {"content": rows}}],
            "usage": {"completion_tokens": len(rows)},
            "timings": timings,
        })


def _cfg(world: dict[str, Any], arm: str, **kw: Any) -> cp.ProbeConfig:
    return cp.ProbeConfig(arm=arm, endpoint="http://probe.test", out_dir=world["out"], **kw)


def _run(world: dict[str, Any], server: FakeServer, arm: str, **kw: Any) -> dict[str, Any]:
    manifest = cp.ensure_manifest(world["out"], world["manifest"])
    qs, digest = cp.resolve_questions(manifest, world["questions"], allow_dataset_drift=False)
    with httpx.Client(transport=httpx.MockTransport(server)) as client:
        return cp.run_probe(_cfg(world, arm, **kw), manifest, qs, digest, client=client, log=lambda m: None)


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ── sample ────────────────────────────────────────────────────────────────


def test_stratified_draw_is_seeded_balanced_and_excludes_error_rows(world: dict[str, Any]) -> None:
    m = world["manifest"]
    rows = m["rows"]
    assert [r["probe_ordinal"] for r in rows] == list(range(N_WRONG + N_RIGHT))
    assert sum(r["stratum"] == "e7c_wrong" for r in rows) == N_WRONG
    assert all((r["stratum"] == "e7c_right") == r["e7c_correct"] for r in rows)
    assert len({r["question_id"] for r in rows}) == len(rows)
    assert "gsm8k_09999" not in {r["question_id"] for r in rows}
    assert m["source_scored"] == 12 and m["source_accuracy"] == 0.5
    again = cp.build_manifest(sidecar=world["sidecar"], summary=world["summary"],
                              n_wrong=N_WRONG, n_right=N_RIGHT, seed=42)
    assert again["sample_sha256"] == m["sample_sha256"]
    other = cp.build_manifest(sidecar=world["sidecar"], summary=world["summary"],
                              n_wrong=N_WRONG, n_right=N_RIGHT, seed=7)
    assert other["sample_sha256"] != m["sample_sha256"]


def test_stratum_too_small_refuses(world: dict[str, Any]) -> None:
    with pytest.raises(cp.ProbeError, match="stratum too small"):
        cp.build_manifest(sidecar=world["sidecar"], summary=None, n_wrong=7, n_right=1, seed=42)


def test_manifest_mismatch_in_same_out_dir_refuses(world: dict[str, Any]) -> None:
    cp.ensure_manifest(world["out"], world["manifest"])
    other = cp.build_manifest(sidecar=world["sidecar"], summary=None, n_wrong=N_WRONG, n_right=N_RIGHT, seed=7)
    with pytest.raises(cp.ProbeError, match="different sample"):
        cp.ensure_manifest(world["out"], other)


def test_dataset_drift_refuses_unless_allowed(world: dict[str, Any]) -> None:
    drifted = [dict(q) for q in world["questions"]]
    drifted[0]["expected"] = "999"
    with pytest.raises(cp.ProbeError, match="dataset_sha256"):
        cp.resolve_questions(world["manifest"], drifted, allow_dataset_drift=False)
    qs, _ = cp.resolve_questions(world["manifest"], drifted, allow_dataset_drift=True)
    assert len(qs) == N_WRONG + N_RIGHT


def test_real_e7c_manifest_draws_100_100() -> None:
    if not cp.DEFAULT_E7C_SIDECAR.exists():
        pytest.skip("E7c sidecar not present")
    m = cp.build_manifest(sidecar=cp.DEFAULT_E7C_SIDECAR, summary=cp.DEFAULT_E7C_SUMMARY,
                          n_wrong=100, n_right=100, seed=42)
    assert m["source_scored"] == 1684 and m["source_accuracy"] == 0.7886
    assert m["e7c_dataset_sha256"].startswith("38e582cf")
    assert sum(r["stratum"] == "e7c_wrong" for r in m["rows"]) == 100
    assert len({r["qid"] for r in m["rows"]}) == 200


# ── request shape ─────────────────────────────────────────────────────────


def test_production_sampling_comes_from_registry_and_backend() -> None:
    from src.registry.registry_loader import RegistryLoader

    s = cp.production_sampling("worker_general")
    gd = RegistryLoader(validate_paths=False).get_role("worker_general").generation_defaults
    assert s["payload"]["temperature"] == gd.temperature
    assert s["payload"]["seed"] == 42
    assert {"top_k", "top_p", "repeat_penalty"} <= set(s["payload"])
    assert len(s["registry_sha256"]) == 64


def test_direct_stage_parity_helpers() -> None:
    assert "</answer>" in cp.direct_stage_stops() and "\n\n\n" in cp.direct_stage_stops()
    assert cp.restore_answer_close_tag("x <answer>5") == "x <answer>5</answer>"
    assert cp.restore_answer_close_tag("x <answer>5</answer>") == "x <answer>5</answer>"
    assert cp.restore_answer_close_tag("no tag") == "no tag"
    p = cp.build_payload(" q ", sampling={"temperature": 0.3}, top_logprobs=50, max_tokens=2048,
                         stop=["</answer>"], chat_template_kwargs=None)
    assert p["top_logprobs"] == 20 and p["logprobs"] is True and p["messages"][0]["content"] == "q"


def test_recipes_pin_champion_gpu_and_spec_state() -> None:
    a, b = cp.RUNNER_RECIPES["A-specoff"]["launch"], cp.RUNNER_RECIPES["B-mtp"]["launch"]
    for launch in (a, b):
        assert cp.CHAMPION_BIN in launch and "--device ROCm0 -ngl 99" in launch and "--slots" in launch
        assert "gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf" in launch
    assert "--spec-type" not in a and "-md " not in a
    assert "--spec-type draft-mtp" in b and "--spec-draft-n-max 2" in b
    assert cp.main(["--print-recipes"]) == 0


# ── run ───────────────────────────────────────────────────────────────────


def test_arm_a_writes_scored_sidecar_with_token_trace(world: dict[str, Any]) -> None:
    wrong = {world["manifest"]["rows"][0]["question_id"]}
    server = FakeServer(wrong_on=wrong)
    summary = _run(world, server, "A-specoff")
    assert summary["complete"] and summary["done"] == N_WRONG + N_RIGHT
    body = server.chat_payloads[0]
    assert body["top_logprobs"] == 20 and body["logprobs"] is True
    assert body["temperature"] == cp.production_sampling("worker_general")["payload"]["temperature"]
    assert "</answer>" in body["stop"] and body["max_tokens"] == 2048

    side = world["out"] / "question_results.A-specoff.jsonl"
    rows = _rows(side)
    assert rows[0]["row_type"] == "batch_start" and rows[-1]["row_type"] == "batch_complete"
    qr = [r for r in rows if r["row_type"] == "question_result"]
    assert len(qr) == N_WRONG + N_RIGHT
    for r in qr:
        assert r["answer"].endswith("</answer>")  # closing tag restored for the scorer
        assert r["result"]["scoring_method"] == "math_verify"
        assert r["result"]["confidence_source"] == "completion_probabilities_geomean"
        tl = r["token_logprobs"]
        assert tl["n_placeholder"] == 0 and tl["topk"] == 2
        assert tl["answer_span"]["source"] == "unterminated_answer_tag"
        assert r["probe"]["arm"] == "A-specoff" and r["probe"]["draft_n"] == 0
    by_q = {r["result"]["question_id"]: r["result"]["correct"] for r in qr}
    assert by_q.pop(next(iter(wrong))) is False  # real math_verify verdicts
    assert all(by_q.values())

    ident = json.loads((world["out"] / "serving_identity.A-specoff.json").read_text())["segments"][0]
    assert ident["serving"]["spec_declared"] is False
    assert ident["serving"]["props"]["build_info"] == "b10125-ef81196d5"
    assert ident["serving"]["props_speculative_unreliable"]["speculative.types"] == "none"
    assert ident["sample_sha256"] == world["manifest"]["sample_sha256"]

    # the offline comparison tool reads the probe sidecar unchanged
    loaded, stats = csc.load_rows([side])
    assert stats["scored_rows"] == N_WRONG + N_RIGHT
    rep = csc.compare(loaded, bootstrap=50, reweight_prevalence=cp.E7C_WORKER_GENERAL_PREVALENCE)
    assert rep["token_trace"]["rows_with_trace"] == N_WRONG + N_RIGHT
    assert rep["token_trace"]["rows_with_any_placeholder"] == 0
    assert rep["sources"]["answer_span_geomean"]["n"] == N_WRONG + N_RIGHT


def test_resume_skips_done_rows_and_retries_errors(world: dict[str, Any]) -> None:
    server = FakeServer(fail_first=1)
    s1 = _run(world, server, "A-specoff", limit=3)
    assert s1["done"] == 2 and not s1["complete"] and s1["segment"]["errors"] == 1
    assert len(server.chat_payloads) == 3
    s2 = _run(world, server, "A-specoff")
    assert s2["complete"] and s2["done"] == N_WRONG + N_RIGHT
    # 6 remaining rows including the errored one; the 2 done rows are not re-sent
    assert len(server.chat_payloads) == 3 + (N_WRONG + N_RIGHT - 2)
    side = world["out"] / "question_results.A-specoff.jsonl"
    loaded, _ = csc.load_rows([side])  # last write wins per ordinal
    assert len(loaded) == N_WRONG + N_RIGHT
    assert len(json.loads((world["out"] / "serving_identity.A-specoff.json").read_text())["segments"]) == 2


def test_resume_refuses_foreign_batch(world: dict[str, Any]) -> None:
    world["out"].mkdir(parents=True)
    (world["out"] / "question_results.A-specoff.jsonl").write_text(
        json.dumps({"row_type": "batch_start", "eval_batch_id": "someone-else"}) + "\n"
    )
    with pytest.raises(cp.ProbeError, match="belongs to batch"):
        _run(world, FakeServer(), "A-specoff")


def test_arm_a_fails_on_placeholder_tokens(world: dict[str, Any]) -> None:
    # /slots is disabled and timings carry no draft counters; only placeholders reveal spec.
    server = FakeServer(slots=False, placeholders=True)
    with pytest.raises(cp.SpecDecodingDetected, match="n_placeholder=2"):
        _run(world, server, "A-specoff")
    side = world["out"] / "question_results.A-specoff.jsonl"
    assert not [r for r in _rows(side) if r["row_type"] == "question_result"]
    rej = _rows(world["out"] / "rejected.A-specoff.jsonl")
    assert rej[0]["reason"] == "speculative_decoding_in_spec_off_arm"
    assert cp.SpecDecodingDetected.exit_code == 3


def test_arm_a_fails_preflight_when_slots_declare_spec(world: dict[str, Any]) -> None:
    server = FakeServer(spec=True)
    with pytest.raises(cp.SpecDecodingDetected, match="speculative=true"):
        _run(world, server, "A-specoff")
    assert server.chat_payloads == []


def test_arm_a_fails_on_draft_counters_without_placeholders(world: dict[str, Any]) -> None:
    server = FakeServer(spec=True, slots=False, placeholders=False)
    with pytest.raises(cp.SpecDecodingDetected, match="draft_n=2"):
        _run(world, server, "A-specoff")


def test_arm_b_records_placeholders(world: dict[str, Any]) -> None:
    summary = _run(world, FakeServer(spec=True), "B-mtp")
    assert summary["complete"]
    assert summary["segment"]["rows_with_placeholder"] == N_WRONG + N_RIGHT
    side = world["out"] / "question_results.B-mtp.jsonl"
    rep = csc.compare(csc.load_rows([side])[0], bootstrap=20)
    assert rep["token_trace"]["placeholder_fraction_median"] == 0.5


def test_arm_b_refuses_a_spec_off_server(world: dict[str, Any]) -> None:
    with pytest.raises(cp.ProbeError, match="not the MTP arm"):
        _run(world, FakeServer(spec=False), "B-mtp")
    with pytest.raises(cp.ProbeError, match="not engaged"):
        _run(world, FakeServer(spec=False, slots=False), "B-mtp")


def test_missing_logprobs_refuses(world: dict[str, Any]) -> None:
    class NoLogprobs(FakeServer):
        def __call__(self, request: httpx.Request) -> httpx.Response:
            resp = super().__call__(request)
            if request.url.path == "/v1/chat/completions" and resp.status_code == 200:
                data = resp.json()
                data["choices"][0].pop("logprobs")
                return httpx.Response(200, json=data)
            return resp

    with pytest.raises(cp.ProbeError, match="no logprobs"):
        _run(world, NoLogprobs(), "A-specoff")


def test_cli_end_to_end_with_questions_jsonl(world: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    server = FakeServer()
    real_client = httpx.Client
    monkeypatch.setattr(cp.httpx, "Client", lambda *a, **k: real_client(transport=httpx.MockTransport(server)))
    common = ["--out-dir", str(world["out"]), "--e7c-sidecar", str(world["sidecar"]),
              "--e7c-summary", str(world["summary"]), "--n-wrong", str(N_WRONG), "--n-right", str(N_RIGHT),
              "--questions-jsonl", str(world["qpath"])]
    assert cp.main(common + ["--manifest-only"]) == 0
    assert (world["out"] / "sample_manifest.json").exists()
    assert server.chat_payloads == []
    assert cp.main(common + ["--arm", "A-specoff", "--endpoint", "http://probe.test"]) == 0
    assert json.loads((world["out"] / "probe_summary.A-specoff.json").read_text())["complete"]
    bad = FakeServer(spec=True)
    monkeypatch.setattr(cp.httpx, "Client", lambda *a, **k: real_client(transport=httpx.MockTransport(bad)))
    assert cp.main(common + ["--arm", "A-specoff", "--endpoint", "http://probe.test"]) == 3
