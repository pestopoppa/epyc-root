#!/usr/bin/env python3
"""Tests for the streaming inference tap."""

import json
import threading
from pathlib import Path
from unittest.mock import MagicMock

import yaml

from src.inference_tap import (
    TapWriter,
    _NullWriter,
    annotate_current_tap,
    _read_sentinel,
    is_active,
    should_stream_role,
    stream_mode,
    tap_section,
)


class TestIsActive:
    """Tests for tap activation check."""

    def test_inactive_by_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv("INFERENCE_TAP_FILE", raising=False)
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(tmp_path / "nope"))
        import src.inference_tap as _mod
        _mod._sentinel_cache = ("", 0.0)
        assert is_active() is False

    def test_active_with_env_var(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_TAP_FILE", "/tmp/tap.log")
        assert is_active() is True

    def test_inactive_with_empty_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv("INFERENCE_TAP_FILE", "")
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(tmp_path / "nope"))
        import src.inference_tap as _mod
        _mod._sentinel_cache = ("", 0.0)
        assert is_active() is False


class TestStreamPolicy:
    """Tests for tap stream-mode policy."""

    def test_stream_mode_default_safe(self, monkeypatch):
        monkeypatch.delenv("INFERENCE_TAP_STREAM_MODE", raising=False)
        assert stream_mode() == "safe"

    def test_stream_mode_invalid_falls_back_to_safe(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_TAP_STREAM_MODE", "invalid")
        assert stream_mode() == "safe"

    def test_should_stream_role_safe_mode(self, monkeypatch):
        """Safe mode streams every role EXCEPT the ones whose live model is heavy.

        The heavy set is DERIVED from orchestration/derived/stack_priors.yaml —
        the same artifact `_safe_non_stream_roles_from_stack_priors` reads — and
        from the module's own default threshold, never from hard-coded role
        names. Which role carries the big model moves with the fleet (W1 moved
        the 122B off architect_general onto architect_critic and put a 27 GB
        Qwen3.6 on architect_general), but the RULE — mem_gb >= threshold means
        do not stream — is the contract and is what is pinned here.
        """
        import src.runtime.inference_tap as tap

        monkeypatch.setenv("INFERENCE_TAP_STREAM_MODE", "safe")
        monkeypatch.delenv("INFERENCE_TAP_SAFE_NON_STREAM_MIN_MEM_GB", raising=False)

        threshold = tap._DEFAULT_SAFE_NON_STREAM_MIN_MEM_GB
        artifact = yaml.safe_load(Path(tap.DEFAULT_STACK_PRIORS).read_text()) or {}
        mem_gb_by_role = {
            role: (record.get("model") or {}).get("mem_gb")
            for role, record in (artifact.get("roles") or {}).items()
            if isinstance(record, dict)
            and record.get("deployment_status") == "live_stack"
        }
        heavy = {
            role
            for role, mem_gb in mem_gb_by_role.items()
            if isinstance(mem_gb, (int, float)) and float(mem_gb) >= threshold
        }
        light = {
            role
            for role, mem_gb in mem_gb_by_role.items()
            if isinstance(mem_gb, (int, float)) and float(mem_gb) < threshold
        }

        # Teeth: the policy must be a real partition of the live fleet. An empty
        # `heavy` would mean safe mode streams EVERYTHING (the fail-open the
        # non-stream policy exists to prevent); an empty `light` would mean it
        # streams nothing.
        assert heavy, f"no live role at/above {threshold} GB in stack priors"
        assert light

        for role in sorted(heavy):
            assert should_stream_role(role) is False, role
        for role in sorted(light):
            assert should_stream_role(role) is True, role

        # A role with no live prior at all is not heavy → still streams.
        assert "worker_fast" not in mem_gb_by_role
        assert should_stream_role("worker_fast") is True

    def test_safe_non_stream_roles_derive_from_stack_priors(self, tmp_path, monkeypatch):
        import src.runtime.inference_tap as tap

        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            yaml.safe_dump(
                {
                    "roles": {
                        "architect_general": {
                            "deployment_status": "live_stack",
                            "model": {"mem_gb": 69.0},
                        },
                        "frontdoor": {
                            "deployment_status": "live_stack",
                            "model": {"mem_gb": 37.0},
                        },
                        "candidate_large": {
                            "deployment_status": "benchmark_or_candidate",
                            "model": {"mem_gb": 120.0},
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.delenv("INFERENCE_TAP_SAFE_NON_STREAM_MIN_MEM_GB", raising=False)

        assert tap._safe_non_stream_roles_from_stack_priors(priors) == frozenset(
            {"architect_general"}
        )

    def test_safe_non_stream_roles_fallback_when_priors_missing(self, tmp_path):
        import src.runtime.inference_tap as tap

        assert tap._safe_non_stream_roles_from_stack_priors(tmp_path / "missing.yaml") is None

    def test_degraded_safe_non_stream_roles_do_not_reconstruct_manifest_policy(self):
        import src.runtime.inference_tap as tap

        assert tap._degraded_safe_non_stream_roles_from_stack_manifest() is None

    def test_safe_non_stream_roles_without_stack_priors_fails_closed_for_tap(self, tmp_path):
        import src.runtime.inference_tap as tap

        assert tap.safe_non_stream_roles(tmp_path / "missing.yaml") == tap._all_known_roles()

    def test_should_stream_role_without_stack_priors_fails_closed(self, tmp_path, monkeypatch):
        import src.runtime.inference_tap as tap

        monkeypatch.setenv("INFERENCE_TAP_STREAM_MODE", "safe")
        monkeypatch.setattr(tap, "DEFAULT_STACK_PRIORS", tmp_path / "missing.yaml")

        assert tap.should_stream_role("frontdoor") is False
        assert tap.should_stream_role("unknown_role") is False

    def test_safe_non_stream_roles_recomputes_env_threshold(self, tmp_path, monkeypatch):
        import src.runtime.inference_tap as tap

        priors = tmp_path / "stack_priors.yaml"
        priors.write_text(
            yaml.safe_dump(
                {
                    "roles": {
                        "architect_general": {
                            "deployment_status": "live_stack",
                            "model": {"mem_gb": 69.0},
                        },
                        "frontdoor": {
                            "deployment_status": "live_stack",
                            "model": {"mem_gb": 37.0},
                        },
                    }
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setenv("INFERENCE_TAP_SAFE_NON_STREAM_MIN_MEM_GB", "80")
        assert tap.safe_non_stream_roles(priors) == frozenset()

        monkeypatch.setenv("INFERENCE_TAP_SAFE_NON_STREAM_MIN_MEM_GB", "64")
        assert tap.safe_non_stream_roles(priors) == frozenset({"architect_general"})

    def test_should_stream_role_safe_mode_uses_derived_policy(self, monkeypatch):
        import src.runtime.inference_tap as tap

        monkeypatch.setenv("INFERENCE_TAP_STREAM_MODE", "safe")
        monkeypatch.setattr(
            tap,
            "SAFE_NON_STREAM_ROLES",
            frozenset({"worker_general", "huge_role"}),
        )

        assert should_stream_role("huge_role") is False
        assert should_stream_role("worker_explore") is False
        assert should_stream_role("worker_fast") is False
        assert should_stream_role("architect_general") is True

    def test_should_stream_role_force_mode(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_TAP_STREAM_MODE", "force")
        assert should_stream_role("architect_general") is True

    def test_should_stream_role_off_mode(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_TAP_STREAM_MODE", "off")
        assert should_stream_role("frontdoor") is False


class TestTapWriter:
    """Tests for TapWriter output format."""

    def test_output_format(self, tmp_path):
        path = str(tmp_path / "tap.log")
        w = TapWriter(path)

        w.write_header("coder_escalation")
        w.write_prompt("Hello world")
        w.write_chunk("def foo():")
        w.write_chunk("\n    pass")
        w.write_timings(10, 100.0, 500.0, 20.0)

        with open(path) as f:
            content = f.read()

        assert "ROLE=coder_escalation" in content
        assert "PROMPT:" in content
        assert "Hello world" in content
        assert "RESPONSE:" in content
        assert "def foo():" in content
        assert "\n    pass" in content
        assert "TIMINGS: 10 tokens in 0.60s" in content
        assert "prompt=100ms" in content
        assert "gen=500ms" in content
        assert "20.0 t/s" in content
        # Verify structure markers
        assert "=" * 72 in content
        assert "-" * 72 in content

    def test_prompt_truncation(self, tmp_path):
        path = str(tmp_path / "tap.log")
        w = TapWriter(path)
        w.write_header("coder")
        long_prompt = "x" * 3000
        w.write_prompt(long_prompt, max_chars=2000)

        with open(path) as f:
            content = f.read()

        assert "1000 chars truncated" in content

        event_path = tmp_path / "tap.log.events.jsonl"
        events = [json.loads(line) for line in event_path.read_text().splitlines()]
        start = next(event for event in events if event["event"] == "start")
        assert start["prompt_len"] == 3000
        assert start["prompt_preview_len"] < start["prompt_len"]
        assert start["prompt_truncated"] is True

    def test_concurrent_writes(self, tmp_path):
        """4 threads writing simultaneously — no corruption."""
        path = str(tmp_path / "tap.log")
        errors = []

        def writer_fn(thread_id):
            try:
                w = TapWriter(path)
                for i in range(20):
                    w.write_chunk(f"[T{thread_id}:{i}]")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer_fn, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        with open(path) as f:
            content = f.read()

        # Each thread wrote 20 chunks
        for t in range(4):
            for i in range(20):
                assert f"[T{t}:{i}]" in content

    def test_write_response(self, tmp_path):
        path = str(tmp_path / "tap.log")
        w = TapWriter(path)
        w.write_header("frontdoor")
        w.write_prompt("hello")
        w.write_response("final answer")
        w.write_timings(3, 10.0, 20.0, 100.0)
        w.close()

        with open(path) as f:
            content = f.read()
        assert "final answer" in content


class TestNullWriter:
    """Verify _NullWriter is a silent no-op."""

    def test_all_methods_noop(self):
        w = _NullWriter()
        # Should not raise
        w.write_header("x")
        w.write_prompt("x")
        w.write_chunk("x")
        w.write_response("x")
        w.write_timings(0, 0.0, 0.0, 0.0)
        w.close()


class TestTapSection:
    """Tests for tap_section context manager."""

    def test_yields_null_writer_when_inactive(self, monkeypatch, tmp_path):
        monkeypatch.delenv("INFERENCE_TAP_FILE", raising=False)
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(tmp_path / "nope"))
        import src.inference_tap as _mod
        _mod._sentinel_cache = ("", 0.0)
        with tap_section("coder", "prompt") as w:
            assert isinstance(w, _NullWriter)

    def test_yields_tap_writer_when_active(self, tmp_path, monkeypatch):
        path = str(tmp_path / "tap.log")
        monkeypatch.setenv("INFERENCE_TAP_FILE", path)
        with tap_section("coder", "prompt text") as w:
            assert isinstance(w, TapWriter)
            w.write_chunk("hello")
            w.write_timings(5, 50.0, 200.0, 25.0)

        with open(path) as f:
            content = f.read()

        assert "ROLE=coder" in content
        assert "prompt text" in content
        assert "hello" in content
        assert "TIMINGS:" in content

    def test_structured_events_include_request_and_instance_metadata(self, tmp_path, monkeypatch):
        path = str(tmp_path / "tap.log")
        events_path = tmp_path / "events.jsonl"
        monkeypatch.setenv("INFERENCE_TAP_FILE", path)
        monkeypatch.setenv("INFERENCE_TAP_EVENTS_FILE", str(events_path))

        with tap_section(
            "frontdoor",
            "prompt text",
            metadata={
                "request_id": "req-1",
                "task_id": "task-1",
                "trial_id": 7,
                "batch_id": "batch-a",
            },
        ) as w:
            assert annotate_current_tap(
                instance_idx=2,
                instance_shape="q1",
                port=8082,
                topology_hash="topo1234",
            ) is True
            w.write_chunk("hel")
            w.write_chunk("lo")
            w.write_timings(5, 50.0, 200.0, 25.0)

        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        assert [event["event"] for event in events] == [
            "start",
            "metadata",
            "chunk",
            "chunk",
            "timings",
            "end",
        ]
        assert all(event["request_id"] == "req-1" for event in events)
        assert events[1]["instance_idx"] == 2
        assert events[1]["instance_shape"] == "q1"
        assert events[1]["port"] == 8082
        assert events[2]["text"] == "hel"


class TestCachingBackendIntegration:
    """Tests verifying _call_caching_backend uses correct path."""

    def test_uses_streaming_when_tap_active(self, monkeypatch):
        monkeypatch.setenv("INFERENCE_TAP_FILE", "/dev/null")

        mock_result = MagicMock()
        mock_result.tokens_generated = 10
        mock_result.prompt_eval_ms = 100.0
        mock_result.generation_ms = 500.0
        mock_result.predicted_per_second = 20.0
        mock_result.success = True
        mock_result.output = "hello"
        mock_result.http_overhead_ms = 0.0

        backend = MagicMock()
        backend.infer_stream_text = MagicMock(return_value=mock_result)
        backend.infer = MagicMock(return_value=mock_result)

        from src.prefix_cache import CachingBackend

        cb = CachingBackend(backend)
        role_config = MagicMock()
        request = MagicMock()
        request.prompt = "test prompt"

        cb.infer_stream_text(role_config, request, on_chunk=lambda c: None)

        backend.infer_stream_text.assert_called_once()
        backend.infer.assert_not_called()

    def test_uses_batch_when_tap_inactive(self, monkeypatch):
        monkeypatch.delenv("INFERENCE_TAP_FILE", raising=False)

        mock_result = MagicMock()
        mock_result.success = True

        backend = MagicMock()
        backend.infer = MagicMock(return_value=mock_result)

        from src.prefix_cache import CachingBackend

        cb = CachingBackend(backend)
        role_config = MagicMock()
        request = MagicMock()
        request.prompt = "test prompt"

        cb.infer(role_config, request)

        backend.infer.assert_called_once()


class TestInferStreamTextSSE:
    """Test SSE parsing in LlamaServerBackend.infer_stream_text()."""

    def test_parses_sse_chunks(self):
        """Mock httpx streaming to verify chunk extraction and InferenceResult."""
        from src.backends.llama_server import LlamaServerBackend, ServerConfig

        # Build SSE lines that iter_lines() would yield
        sse_lines = [
            'data: {"content": "Hello"}',
            'data: {"content": " world"}',
            'data: {"content": "!", "stop": true, "tokens_predicted": 3, '
            '"tokens_evaluated": 5, '
            '"timings": {"prompt_ms": 50.0, "predicted_ms": 100.0, '
            '"predicted_per_second": 30.0, "cache_n": 2}}',
        ]

        # Create a mock streaming response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.iter_lines = MagicMock(return_value=iter(sse_lines))
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_response)

        config = ServerConfig(base_url="http://localhost:8080")
        backend = LlamaServerBackend(config)
        backend.client = mock_client

        # Minimal role_config mock
        role_config = MagicMock()
        role_config.name = "coder"
        role_config.acceleration.temperature = 0.0

        request = MagicMock()
        request.prompt = "test"
        request.n_tokens = 100
        request.timeout = 60
        request.temperature = 0.0
        request.cache_prompt = None
        request.stop_sequences = None

        received_chunks = []
        result = backend.infer_stream_text(
            role_config, request, on_chunk=lambda c: received_chunks.append(c)
        )

        assert received_chunks == ["Hello", " world", "!"]
        assert result.output == "Hello world!"
        assert result.tokens_generated == 3
        assert result.success is True
        assert result.prompt_eval_ms == 50.0
        assert result.generation_ms == 100.0
        assert result.predicted_per_second == 30.0


class TestSentinelFallback:
    """Tests for sentinel file fallback in is_active() / _tap_path()."""

    def _reset_cache(self):
        """Force-expire the sentinel cache so reads are fresh."""
        import src.inference_tap as _mod
        _mod._sentinel_cache = ("", 0.0)

    def test_is_active_true_with_sentinel(self, tmp_path, monkeypatch):
        """is_active() returns True when sentinel file exists."""
        sentinel = tmp_path / "sentinel"
        sentinel.write_text("/tmp/tap.log")

        monkeypatch.delenv("INFERENCE_TAP_FILE", raising=False)
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(sentinel))
        self._reset_cache()

        assert is_active() is True

    def test_is_active_false_after_removal(self, tmp_path, monkeypatch):
        """is_active() returns False after sentinel is removed (cache expired)."""
        sentinel = tmp_path / "sentinel"
        sentinel.write_text("/tmp/tap.log")

        monkeypatch.delenv("INFERENCE_TAP_FILE", raising=False)
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(sentinel))
        self._reset_cache()

        assert is_active() is True

        # Remove sentinel and expire cache
        sentinel.unlink()
        self._reset_cache()

        assert is_active() is False

    def test_sentinel_cache_is_used(self, tmp_path, monkeypatch):
        """Reads within 5 seconds return cached value (no re-read)."""
        sentinel = tmp_path / "sentinel"
        sentinel.write_text("/tmp/tap.log")

        monkeypatch.delenv("INFERENCE_TAP_FILE", raising=False)
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(sentinel))
        self._reset_cache()

        # First read populates cache
        assert _read_sentinel() == "/tmp/tap.log"

        # Remove file — cached value should still be returned
        sentinel.unlink()
        assert _read_sentinel() == "/tmp/tap.log"  # cached!

        # After expiring cache, read returns empty
        self._reset_cache()
        assert _read_sentinel() == ""

    def test_env_var_takes_precedence(self, tmp_path, monkeypatch):
        """Env var is checked before sentinel."""
        sentinel = tmp_path / "sentinel"
        sentinel.write_text("/tmp/sentinel_tap.log")

        monkeypatch.setenv("INFERENCE_TAP_FILE", "/tmp/env_tap.log")
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(sentinel))
        self._reset_cache()

        assert is_active() is True
        # _tap_path should return env var, not sentinel
        from src.inference_tap import _tap_path
        assert _tap_path() == "/tmp/env_tap.log"

    def test_nonexistent_sentinel(self, tmp_path, monkeypatch):
        """Missing sentinel file returns empty string without error."""
        monkeypatch.delenv("INFERENCE_TAP_FILE", raising=False)
        monkeypatch.setattr("src.inference_tap._SENTINEL", str(tmp_path / "nope"))
        self._reset_cache()

        assert is_active() is False
        assert _read_sentinel() == ""


def test_grep_lines_reverse_finds_old_request_past_tail(tmp_path):
    """Reverse-grep must recover a request's lines even when buried under MBs of
    newer events (the fixed-tail window misses anything older than seconds on a
    multi-GB tap). Regression for the 2026-05-31 empty-completed-panel bug."""
    from src.api.routes.dashboard_tap import _grep_lines_reverse, _read_tail
    p = tmp_path / "tap.jsonl"
    target = '{"event":"start","request_id":"chat-OLD:1","task_id":"chat-OLD","text":"x"}'
    filler = "\n".join(f'{{"event":"chunk","request_id":"chat-NEW:{i}","text":"y"}}'
                        for i in range(50000))  # ~3 MB of newer noise
    p.write_text(target + "\n" + filler + "\n")
    # Fixed 64 KB tail cannot see the old request...
    assert "chat-OLD" not in _read_tail(p, max_bytes=64 * 1024)
    # ...but the reverse-grep recovers exactly its line.
    got = _grep_lines_reverse(p, "chat-OLD")
    assert "chat-OLD:1" in got
    assert got.count("\n") == 0  # only the matching line, not the 50k filler


def test_grep_lines_reverse_missing_needle_returns_empty(tmp_path):
    from src.api.routes.dashboard_tap import _grep_lines_reverse
    p = tmp_path / "tap.jsonl"
    p.write_text('{"event":"start","request_id":"a:1"}\n')
    assert _grep_lines_reverse(p, "nonexistent") == ""
    assert _grep_lines_reverse(tmp_path / "absent.jsonl", "x") == ""


def test_events_rotation_shifts_and_caps(tmp_path, monkeypatch):
    """Events JSONL rotates at the size cap: current → .1 → .2, oldest dropped."""
    import src.runtime.inference_tap as tap
    events = tmp_path / "inference_tap_events.jsonl"
    monkeypatch.setenv("INFERENCE_TAP_EVENTS_MAX_MB", "0")  # bytes-based via patch below
    # Use a tiny cap by patching the config helper directly (env is MB-granular).
    monkeypatch.setattr(tap, "_events_rotation_config", lambda: (200, 2))
    # Write enough events to exceed 200 bytes several times.
    for i in range(40):
        tap._write_structured_event(str(events), {"event": "chunk", "request_id": f"r{i}", "text": "x" * 20})
    # Current file exists and is under/around the cap; rotations produced siblings.
    assert events.exists()
    assert (events.with_name("inference_tap_events.jsonl.1")).exists()
    # keep=2 → .3 must never appear.
    assert not (events.with_name("inference_tap_events.jsonl.3")).exists()


def test_events_no_rotation_under_cap(tmp_path, monkeypatch):
    import src.runtime.inference_tap as tap
    events = tmp_path / "ev.jsonl"
    monkeypatch.setattr(tap, "_events_rotation_config", lambda: (10 * 1024 * 1024, 3))
    for i in range(5):
        tap._write_structured_event(str(events), {"event": "chunk", "request_id": f"r{i}"})
    assert events.exists()
    assert not (events.with_name("ev.jsonl.1")).exists()


def test_grep_falls_through_to_rotated_sibling(tmp_path):
    """A request that landed in .1 (just before rotation) is still recoverable."""
    from src.api.routes.dashboard_tap import _grep_lines_reverse
    cur = tmp_path / "ev.jsonl"
    cur.write_text('{"request_id":"NEW:1","text":"a"}\n')
    (tmp_path / "ev.jsonl.1").write_text('{"request_id":"OLD:1","text":"b"}\n')
    assert "OLD:1" in _grep_lines_reverse(cur, "OLD")
    assert "NEW:1" in _grep_lines_reverse(cur, "NEW")
