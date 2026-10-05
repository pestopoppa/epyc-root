"""RTG-47 data plane — terminal ``prompt_tokens`` per request (2026-09-17).

``slot_progress`` attaches only while a busy slot is visible and NEVER to a
``complete`` record, so a request that finished between two /slots samples
used to leave the card with nothing but a character-count estimate — and the
estimate was indistinguishable from a measurement. The tap writer now records
llama-server's own terminal count (``tokens_evaluated`` / ``usage.prompt_tokens``)
on the ``timings`` event together with ``prompt_tokens_source="server_terminal"``,
and the parser surfaces both as top-level fields. Provenance is explicit in
BOTH directions: an unmeasured record says ``chars_estimate`` with value None.

All fixtures are synthetic JSONL; no sockets, no processes, no inference.
"""

from __future__ import annotations

import json

from src.api.routes.dashboard import _attach_slot_progress
from src.api.routes.dashboard_tap import _parse_structured_tap_requests
from src.runtime.inference_tap import TapWriter, _NullWriter

_NOW = 1_000_000.0


def _jsonl(*events: dict) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


def _base(request_id: str, ts: float) -> dict:
    return {"request_id": request_id, "role": "frontdoor", "port": 8070, "ts_epoch": ts,
            "ts": "2026-09-17T10:00:00.000+00:00"}


# --------------------------------------------------------------------- writer

def test_writer_records_measured_terminal_prompt_tokens_with_provenance(tmp_path) -> None:
    events = tmp_path / "events.jsonl"
    w = TapWriter(str(tmp_path / "tap.log"), metadata={"request_id": "r-measured"})
    w._event_path = str(events)
    w.write_header("frontdoor")
    w.write_prompt("hello")
    w.write_timings(12, 900.0, 300.0, 40.0, prompt_tokens=32851)
    w.close()

    timings = [json.loads(line) for line in events.read_text().splitlines()
               if json.loads(line)["event"] == "timings"]
    assert len(timings) == 1
    assert timings[0]["prompt_tokens"] == 32851
    assert timings[0]["prompt_tokens_source"] == "server_terminal"
    # The plaintext tap carries the same number, labelled.
    assert "prompt_tokens=32851" in (tmp_path / "tap.log").read_text()


def test_writer_omits_prompt_tokens_when_server_reported_none_or_zero(tmp_path) -> None:
    """An early-stopped stream (tokens_evaluated stays 0) or a usage-less chat
    stream must NOT fabricate a measurement — the field is absent, not 0."""
    events = tmp_path / "events.jsonl"
    w = TapWriter(str(tmp_path / "tap.log"), metadata={"request_id": "r-unknown"})
    w._event_path = str(events)
    w.write_header("frontdoor")
    w.write_prompt("hello")
    w.write_timings(5, 10.0, 20.0, 100.0, prompt_tokens=0)
    w.write_timings(5, 10.0, 20.0, 100.0, prompt_tokens=None)
    w.write_timings(5, 10.0, 20.0, 100.0)  # legacy positional call still works
    w.close()

    timings = [json.loads(line) for line in events.read_text().splitlines()
               if json.loads(line)["event"] == "timings"]
    assert len(timings) == 3
    for ev in timings:
        assert "prompt_tokens" not in ev
        assert "prompt_tokens_source" not in ev


def test_null_writer_accepts_the_new_keyword() -> None:
    _NullWriter().write_timings(0, 0.0, 0.0, 0.0, prompt_tokens=7)


# --------------------------------------------------------------------- parser

def test_completed_without_mid_run_observation_carries_true_count_marked_measured() -> None:
    """The headline case: no /slots sample ever saw this request (the sampler
    only sees busy slots and never attaches to `complete`), yet the completed
    record carries the TRUE prompt-token count and says it is measured."""
    tail = _jsonl(
        {**_base("r1", _NOW - 30), "event": "start", "prompt": "x" * 400, "prompt_len": 131_404},
        {**_base("r1", _NOW - 1), "event": "timings", "tokens": 334, "prompt_ms": 41_000.0,
         "gen_ms": 8_000.0, "tps": 41.7, "total_s": 49.0,
         "prompt_tokens": 32_851, "prompt_tokens_source": "server_terminal"},
        {**_base("r1", _NOW - 1), "event": "end"},
    )
    reqs = _parse_structured_tap_requests(tail, now_epoch=_NOW)
    assert len(reqs) == 1
    rec = reqs[0]
    assert rec["status"] == "complete"
    assert rec["prompt_tokens"] == 32_851
    assert rec["prompt_tokens_source"] == "server_terminal"
    # The character estimate is still there, separately, under its own name.
    assert rec["prompt_len"] == 131_404

    # And the slot funnel leaves the completed record alone: a busy slot on the
    # same port belongs to whoever is running now, and the terminal count does
    # not need it.
    out = _attach_slot_progress(
        reqs,
        slots_by_port={8070: [{"id": 0, "is_processing": True, "n_prompt_tokens": 99,
                               "n_prompt_tokens_processed": 10}]},
        sampled_at=_NOW, now=_NOW)
    assert "slot_progress" not in out[0]
    assert out[0]["prompt_tokens"] == 32_851


def test_unmeasured_record_is_legibly_an_estimate() -> None:
    """A legacy `timings` event (no prompt_tokens) yields value None and source
    `chars_estimate` — never a silent number the page could mistake."""
    tail = _jsonl(
        {**_base("r2", _NOW - 30), "event": "start", "prompt": "abc", "prompt_len": 3},
        {**_base("r2", _NOW - 1), "event": "timings", "tokens": 5, "prompt_ms": 1.0,
         "gen_ms": 2.0, "tps": 3.0, "total_s": 0.003},
        {**_base("r2", _NOW - 1), "event": "end"},
    )
    rec = _parse_structured_tap_requests(tail, now_epoch=_NOW)[0]
    assert rec["prompt_tokens"] is None
    assert rec["prompt_tokens_source"] == "chars_estimate"


def test_zero_or_malformed_terminal_count_is_not_a_measurement() -> None:
    tail = _jsonl(
        {**_base("r3", _NOW - 30), "event": "start", "prompt": "abc", "prompt_len": 3},
        {**_base("r3", _NOW - 1), "event": "timings", "tokens": 5, "prompt_ms": 1.0,
         "gen_ms": 2.0, "tps": 3.0, "total_s": 0.003, "prompt_tokens": 0},
        {**_base("r4", _NOW - 30), "event": "start", "prompt": "abc", "prompt_len": 3},
        {**_base("r4", _NOW - 1), "event": "timings", "tokens": 5, "prompt_ms": 1.0,
         "gen_ms": 2.0, "tps": 3.0, "total_s": 0.003, "prompt_tokens": "lots"},
    )
    by_id = {r["request_id"]: r for r in _parse_structured_tap_requests(tail, now_epoch=_NOW)}
    for rid in ("r3", "r4"):
        assert by_id[rid]["prompt_tokens"] is None
        assert by_id[rid]["prompt_tokens_source"] == "chars_estimate"


def test_running_record_has_no_terminal_count_yet() -> None:
    tail = _jsonl(
        {**_base("r5", _NOW - 3), "event": "start", "prompt": "abc", "prompt_len": 3},
        {**_base("r5", _NOW - 1), "event": "chunk", "text": "h"},
    )
    rec = _parse_structured_tap_requests(tail, now_epoch=_NOW)[0]
    assert rec["status"] == "running"
    assert rec["prompt_tokens"] is None
    assert rec["prompt_tokens_source"] == "chars_estimate"
