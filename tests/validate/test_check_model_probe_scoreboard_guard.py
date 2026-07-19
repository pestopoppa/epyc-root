from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "validate"
    / "check_model_probe_scoreboard_guard.py"
)
_SPEC = importlib.util.spec_from_file_location("check_model_probe_scoreboard_guard", _SCRIPT)
assert _SPEC and _SPEC.loader
guard = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = guard
_SPEC.loader.exec_module(guard)


def _diff(path: str, added: str) -> str:
    return "\n".join(
        [
            f"diff --git a/{path} b/{path}",
            f"--- a/{path}",
            f"+++ b/{path}",
            "@@ -1,0 +1,1 @@",
            f"+{added}",
        ]
    )


def test_registry_probe_metric_requires_scoreboard() -> None:
    findings = guard.scan_diff(
        "epyc-inference-research",
        _diff("orchestration/model_registry.yaml", "Nemotron-Nano Q8 tg512 84 t/s summary.json"),
        scoreboard_is_changed=False,
    )

    assert len(findings) == 1
    assert findings[0].path == "orchestration/model_registry.yaml"


def test_scoreboard_companion_satisfies_guard() -> None:
    findings = guard.scan_diff(
        "epyc-inference-research",
        _diff("orchestration/model_registry.yaml", "Qwable IQ4_XS tg512 100 t/s summary.json"),
        scoreboard_is_changed=True,
    )

    assert findings == []


def test_stop_list_steering_text_is_allowed_without_scoreboard() -> None:
    findings = guard.scan_diff(
        "epyc-root",
        _diff(
            "handoffs/active/inference-acceleration-index.md",
            "Do not run Bonsai Q1_0 speed reruns; redirect to AXA-2.",
        ),
        scoreboard_is_changed=False,
    )

    assert findings == []


def test_handoff_stop_list_evidence_requires_scoreboard() -> None:
    findings = guard.scan_diff(
        "epyc-root",
        _diff(
            "handoffs/active/inference-acceleration-index.md",
            "Bonsai Q1_0 MI210 tg512 38 t/s data/bonsai/summary.json",
        ),
        scoreboard_is_changed=False,
    )

    assert len(findings) == 1
    assert "stop-listed" in findings[0].reason


def test_model_doc_steering_with_scoreboard_is_allowed() -> None:
    findings = guard.scan_diff(
        "epyc-inference-research",
        _diff(
            "docs/reference/models/model-smoke-queue-2026-07-16.md",
            "Park Bonsai Q1_0 after 38 t/s; append any reopened result to the scoreboard.",
        ),
        scoreboard_is_changed=False,
    )

    assert findings == []


def test_handoff_paused_with_scoreboard_is_allowed() -> None:
    findings = guard.scan_diff(
        "epyc-root",
        _diff(
            "handoffs/active/gemma-challenge-kernel-techniques-v7.md",
            "Qwen3-VL-8B A/Bs are paused after 3/4; append reopened probes to the scoreboard.",
        ),
        scoreboard_is_changed=False,
    )

    assert findings == []
