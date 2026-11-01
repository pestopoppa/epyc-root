"""INF-70 HARNESS-1 classifier rectification (2026-10-04): fake token ids are refused.

Every INF-70 chat client called ``classify(dict(tokens=list(range(npred)), ...))``. Synthetic,
all-distinct ids make ``uniq`` == 1, ``top`` == 1/n and ``run`` == 1, so three of the five
degeneracy rules could never fire and any spaced ASCII text read COHERENT. Pinned here:

* the fake-id pattern (and any consecutive-id run, and non-integer ids) raises
  ``SyntheticTokenIds``; non-empty content without ids raises ``MissingTokenIds``;
* the v1 rules are unchanged on real ids (a real stuck-token loop is SALAD, real prose is
  COHERENT), and ``n > V1_MAX_N`` is refused because the fixed ``uniq < 0.35`` is length-biased;
* the client never constructs placeholder ids: it takes ``__verbose.tokens``, else /tokenize,
  else records ``NO-TOKEN-IDS``.

No server, no inference: the client helpers are exercised with in-memory fixtures.
"""

from __future__ import annotations

import importlib
import random
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2] / "scripts" / "inf70" / "harness1"
sys.path.insert(0, str(HARNESS))
classify_mod = importlib.import_module("classify")
client = importlib.import_module("client")  # main() is guarded: importing runs nothing

PROSE = ("The cache hierarchy keeps recently used lines close to the core so that most loads "
         "are served in a few cycles instead of hundreds. ") * 2


def _real_ids(n: int, seed: int = 0) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(1000, 150000) for _ in range(n)]


@pytest.mark.parametrize("npred", [16, 24, 200])
def test_fake_range_ids_are_refused(npred):
    with pytest.raises(classify_mod.SyntheticTokenIds):
        classify_mod.classify(dict(tokens=list(range(npred)), stop_type="stop", content=PROSE))


def test_offset_consecutive_run_is_refused():
    with pytest.raises(classify_mod.SyntheticTokenIds):
        classify_mod.classify(dict(tokens=list(range(5000, 5100)), stop_type="stop", content=PROSE))


def test_non_integer_ids_are_refused():
    with pytest.raises(classify_mod.SyntheticTokenIds):
        classify_mod.classify(dict(tokens=[str(i) for i in _real_ids(40)], stop_type="stop", content=PROSE))


def test_missing_ids_with_content_is_refused():
    with pytest.raises(classify_mod.MissingTokenIds):
        classify_mod.classify(dict(stop_type="stop", content=PROSE))


def test_the_old_fake_id_call_made_word_soup_coherent():
    """Documents the defect: before the refusal, a 200-token stuck loop on spaced ASCII passed."""
    soup = "the the the the " * 50
    old = dict(tokens=list(range(200)), stop_type="stop", content=soup)
    with pytest.raises(classify_mod.SyntheticTokenIds):
        classify_mod.classify(old)
    real = dict(tokens=[279] * 200, stop_type="stop", content=soup)
    r = classify_mod.classify(real)
    assert r["cls"] == "SALAD" and r["top"] == 1.0 and r["run"] == 200


def test_real_prose_ids_unchanged_v1_verdict():
    r = classify_mod.classify(dict(tokens=_real_ids(48), stop_type="stop", content=PROSE))
    assert r["cls"] == "COHERENT"
    assert r["classifier"] == classify_mod.CLASSIFIER_ID


def test_short_outputs_unchanged():
    assert classify_mod.classify(dict(tokens=[33], stop_type="eos", content="E"))["cls"] == "EARLY-EOS"
    assert classify_mod.classify(dict(tokens=[33, 34, 35], stop_type="stop", content="E"))["cls"] == "SHORT"
    assert classify_mod.classify(dict(tokens=[], stop_type="stop", content=""))["cls"] == "EMPTY"


def test_long_generation_out_of_calibrated_range():
    n = classify_mod.V1_MAX_N + 1
    with pytest.raises(classify_mod.OutOfCalibratedRange):
        classify_mod.classify(dict(tokens=_real_ids(n), stop_type="stop", content=PROSE * 10))


def test_client_source_builds_no_placeholder_ids():
    """Structural: no `range(...)` call anywhere in the client's code (docstrings may name it)."""
    import ast
    tree = ast.parse((HARNESS / "client.py").read_text())
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "range"]
    assert calls == []


def test_client_prefers_response_ids():
    ids = _real_ids(30)
    got = client.token_ids({"__verbose": {"tokens": ids}}, PROSE, tokenize=lambda t: pytest.fail("no fallback"))
    assert got == (ids, "response")


def test_client_falls_back_to_tokenize():
    ids = _real_ids(30, seed=1)
    assert client.token_ids({}, PROSE, tokenize=lambda t: ids) == (ids, "retokenized")


def test_client_never_fabricates_ids():
    def boom(_):
        raise OSError("tokenize unreachable")
    ids, src = client.token_ids({}, PROSE, tokenize=boom)
    assert (ids, src) == (None, "absent")
    assert client.classify_row(PROSE, ids, "stop")["cls"] == "NO-TOKEN-IDS"


def test_client_row_records_refusal_not_verdict():
    r = client.classify_row(PROSE, list(range(40)), "stop")
    assert r["cls"] == "REFUSED" and "SyntheticTokenIds" in r["note"]


def test_main_http_transport_records_response_fallback_eof_and_refusal(monkeypatch, tmp_path):
    """Exercise the request/row path with a fake transport and no model or listening server."""
    import io
    import json
    prompts = [{"id": str(i), "class": "test", "prompt": str(i)} for i in range(4)]
    (tmp_path / "prompts.json").write_text(json.dumps(prompts))
    monkeypatch.setattr(client, "HERE", str(tmp_path))
    monkeypatch.setattr(client, "OUT", str(tmp_path))
    ids = _real_ids(40)
    long_ids = _real_ids(257)
    requests = []
    chats = iter([
        {"choices": [{}]},  # warmup
        {"choices": [{"message": {"content": PROSE}, "finish_reason": "stop"}], "__verbose": {"tokens": ids, "stop_type": "eos"}},
        {"choices": [{"message": {"content": PROSE}, "finish_reason": "stop"}]},
        {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}], "__verbose": {"tokens": [], "stop_type": "eos"}},
        {"choices": [{"message": {"content": PROSE}, "finish_reason": "length"}], "__verbose": {"tokens": long_ids}},
    ])
    def urlopen(req, timeout):
        body = json.loads(req.data)
        requests.append((req.full_url, body))
        if req.full_url.endswith("/tokenize"):
            return io.BytesIO(json.dumps({"tokens": ids}).encode())
        return io.BytesIO(json.dumps(next(chats)).encode())
    monkeypatch.setattr(client.urllib.request, "urlopen", urlopen)
    client.main("fixture", "1")
    rows = [json.loads(line) for line in (tmp_path / "fixture.rows.jsonl").read_text().splitlines()]
    assert [row["token_source"] for row in rows] == ["response", "retokenized", "response", "response"]
    assert rows[0]["token_ids"] == ids and rows[0]["stop_type_native"] == "eos"
    assert rows[1]["token_ids"] == ids
    assert rows[2]["verdict"] == "EMPTY" and rows[2]["stop_type_native"] == "eos"
    assert rows[3]["verdict"] == "REFUSED" and rows[3]["token_ids"] == long_ids
    chat_bodies = [body for url, body in requests if url.endswith("/v1/chat/completions")]
    assert all(body["return_tokens"] and body["verbose"] for body in chat_bodies)
    assert sum(url.endswith("/tokenize") for url, _ in requests) == 1


def test_http_tokenize_eof_yields_no_token_ids(monkeypatch):
    def eof(_request, timeout):
        raise EOFError("truncated HTTP response")
    monkeypatch.setattr(client.urllib.request, "urlopen", eof)
    ids, source = client.token_ids({}, PROSE, lambda text: client.post("1", "/tokenize", {"content": text}))
    assert (ids, source) == (None, "absent")
    assert client.classify_row(PROSE, ids, "stop")["cls"] == "NO-TOKEN-IDS"


@pytest.mark.parametrize("bad", [[True], [1.5], ["42"], [-1], "", (1, 2)])
def test_classifier_refuses_invalid_short_ids(bad):
    with pytest.raises(classify_mod.SyntheticTokenIds):
        classify_mod.classify({"tokens": bad, "content": "", "stop_type": "stop"})


@pytest.mark.parametrize("bad", [[True], [1.5], ["42"], [-1], [1, False]])
def test_client_rejects_malformed_ids_without_coercion(bad):
    good = [42, 7]
    assert client.token_ids({"__verbose": {"tokens": bad}}, "text", lambda _: good) == (good, "retokenized")
    assert client.token_ids({"__verbose": {"tokens": bad}}, "text", lambda _: bad) == (None, "absent")


def test_empty_content_requires_actual_ids():
    assert client.token_ids({}, "", lambda _: None) == (None, "absent")
    assert client.token_ids({}, "", lambda _: []) == ([], "retokenized")
    assert client.token_ids({"__verbose": {"tokens": []}}, "", lambda _: None) == ([], "response")
    with pytest.raises(classify_mod.MissingTokenIds):
        classify_mod.classify({"content": "", "stop_type": "stop"})


def test_final_http_error_is_persisted(monkeypatch, tmp_path):
    import io
    import json
    (tmp_path / "prompts.json").write_text(json.dumps([{"id": "last", "class": "test", "prompt": "x"}]))
    monkeypatch.setattr(client, "HERE", str(tmp_path))
    monkeypatch.setattr(client, "OUT", str(tmp_path))
    calls = []
    def urlopen(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            return io.BytesIO(b"{}")
        raise EOFError("final response truncated")
    monkeypatch.setattr(client.urllib.request, "urlopen", urlopen)
    client.main("error", "1")
    rows = [json.loads(line) for line in (tmp_path / "error.rows.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["verdict"] == "HTTP-ERROR"
    assert "truncated" in rows[0]["note"]
