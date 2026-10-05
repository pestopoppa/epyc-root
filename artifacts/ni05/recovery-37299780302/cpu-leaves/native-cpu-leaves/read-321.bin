from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "benchmark" / "eval_batch_serving_probe.py"

spec = importlib.util.spec_from_file_location("eval_batch_serving_probe", MODULE_PATH)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
sys.modules["eval_batch_serving_probe"] = probe
spec.loader.exec_module(probe)


def _ok(url: str, body: object | None = None) -> probe.HttpResult:
    return probe.HttpResult(
        url=url,
        status=200,
        ok=True,
        elapsed_s=0.01,
        json_body={} if body is None else body,
    )


def test_activation_commands_use_stack_managed_feature_env() -> None:
    commands = "\n".join(probe.activation_commands("http://localhost:18070"))

    assert "start --only eval_batch_frontdoor" in commands
    assert "ORCHESTRATOR_FEATURE_EVAL_BATCH_SERVING=1" in commands
    assert "ORCHESTRATOR_EVAL_BATCH_FRONTDOOR_URL=http://localhost:18070" in commands
    assert "--smoke --confirm-clean-window --require-enabled" in commands


def test_resolve_tap_events_path_from_inference_tap_file(monkeypatch) -> None:
    monkeypatch.delenv("INFERENCE_TAP_EVENTS_FILE", raising=False)
    monkeypatch.setenv("INFERENCE_TAP_FILE", "/tmp/inference_tap.log")
    monkeypatch.setattr(probe, "TAP_SENTINEL", Path("/does/not/exist"))

    assert probe.resolve_tap_events_path() == Path("/tmp/inference_tap_events.jsonl")


def test_summarize_tap_events_detects_expected_port() -> None:
    summary = probe.summarize_tap_events(
        [
            {
                "event": "start",
                "batch_id": "b1",
                "request_id": "r1",
                "role": "frontdoor",
                "port": 18070,
            },
            {
                "event": "timings",
                "batch_id": "b1",
                "request_id": "r1",
                "role": "frontdoor",
                "port": 18070,
                "tps": 40.0,
            },
            {
                "event": "timings",
                "batch_id": "b1",
                "request_id": "r1",
                "role": "frontdoor",
                "port": 18070,
                "tps": 44.0,
            },
        ],
        expected_port=18070,
    )

    assert summary["hit_expected_port"] is True
    assert summary["ports"] == [18070]
    assert summary["roles"] == ["frontdoor"]
    assert summary["median_tps"] == 42.0


def test_smoke_requires_confirm_clean_window(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(probe, "_active_autopilot", lambda: False)
    monkeypatch.setattr(
        probe,
        "_request_json",
        lambda method, url, **kwargs: _ok(url, {"flags": {"eval_batch_serving": True}}),
    )
    monkeypatch.setattr(
        probe,
        "_collect_config_attest",
        lambda *args, **kwargs: [
            {"pid": 1, "flags": {"eval_batch_serving": True}, "sources": {}}
        ],
    )

    rc = probe.main(["--smoke", "--output-dir", str(tmp_path), "--summary-only"])

    assert rc == 2
    assert (tmp_path / "summary.json").exists()
    payload = (tmp_path / "summary.json").read_text(encoding="utf-8")
    assert "--smoke requires --confirm-clean-window" in payload
    assert capsys.readouterr().out == ""


def test_active_autopilot_blocks_smoke(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(probe, "_active_autopilot", lambda: True)
    monkeypatch.setattr(probe, "_request_json", lambda method, url, **kwargs: _ok(url, {}))
    monkeypatch.setattr(
        probe,
        "_collect_config_attest",
        lambda *args, **kwargs: [
            {"pid": 1, "flags": {"eval_batch_serving": True}, "sources": {}}
        ],
    )

    rc = probe.main(
        [
            "--smoke",
            "--confirm-clean-window",
            "--output-dir",
            str(tmp_path),
            "--summary-only",
        ]
    )

    report = (tmp_path / "summary.json").read_text(encoding="utf-8")
    assert rc == 75
    assert "AutoPilot appears active" in report


def test_smoke_posts_chat_and_matches_tap(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, dict | None]] = []

    def fake_request(method, url, *, payload=None, timeout_s=5.0):
        calls.append((method, url, payload))
        if url.endswith("/chat"):
            return _ok(url, {"answer": "3", "routed_to": "frontdoor"})
        return _ok(url, {})

    monkeypatch.setattr(probe, "_active_autopilot", lambda: False)
    monkeypatch.setattr(probe, "_request_json", fake_request)
    monkeypatch.setattr(
        probe,
        "_collect_config_attest",
        lambda *args, **kwargs: [
            {"pid": 1, "flags": {"eval_batch_serving": True}, "sources": {}}
        ],
    )
    monkeypatch.setattr(probe, "resolve_tap_events_path", lambda _explicit=None: tmp_path / "tap.jsonl")
    monkeypatch.setattr(
        probe,
        "load_recent_tap_events",
        lambda _path, *, batch_id, max_bytes=0: [
            {
                "event": "timings",
                "batch_id": batch_id,
                "request_id": "req",
                "role": "frontdoor",
                "port": 18070,
                "tps": 41.0,
            }
        ],
    )

    rc = probe.main(
        [
            "--smoke",
            "--confirm-clean-window",
            "--require-enabled",
            "--batch-id",
            "batch-test",
            "--request-id",
            "req",
            "--output-dir",
            str(tmp_path),
            "--summary-only",
            "--tap-grace-s",
            "0",
        ]
    )

    report = (tmp_path / "summary.json").read_text(encoding="utf-8")
    assert rc == 0
    assert any(url.endswith("/chat") for _method, url, _payload in calls)
    chat_payload = next(payload for _method, url, payload in calls if url.endswith("/chat"))
    assert chat_payload["workload_class"] == "eval_batch"
    assert chat_payload["request_priority"] == "background"
    assert chat_payload["batch_id"] == "batch-test"
    assert '"hit_expected_port": true' in report
    assert '"decision_grade": true' in report
