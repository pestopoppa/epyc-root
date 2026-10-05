"""Server-side eval-batch timeout extension (2026-07-21 EV-11c incident fix).

Completes the EV-11c fix: the client-side eval-honesty guards
(``test_eval_tower_rel1_honesty_guards.py``) stop a deadline-starved call from
tripping the breaker, but the *root cause* was that the interactive role SLA
(worker=60s) capped every llama call two ways:

  1. ``resolve_timeout`` (routing_decision.py) clamps the request budget DOWN to
     the role SLA via ``min`` — so a 300s eval request became a 60s one.
  2. ``LLMPrimitives._clamp_timeout_to_request_budget`` (primitives.py) then
     re-clamped the llama call's role-base timeout (60s) DOWN to the remaining
     deadline — so even an extended deadline could not lift the 60s cap.

2,048-token MATH-tail generations at 4-wide shared bandwidth need >60s, so the
call 504'd, tripped the circuit breaker, and the breaker served in-band
``[ERROR: ...]`` text as answers plus a silent role fallback.

These tests pin the two server changes AND the client payload that reaches them:

  * ``resolve_timeout`` EXTENDS beyond the role SLA for self-declared
    ``eval_batch`` traffic, and is byte-unchanged (DOWN-only clamp) otherwise.
  * ``_clamp_timeout_to_request_budget`` is IDENTITY-preserving for every
    interactive-shaped budget (``remaining <= role_base``) and only extends when
    ``remaining > role_base`` (the eval-batch-extended deadline).
  * ``call_orchestrator_forced`` sends ``timeout_s`` + ``workload_class`` so the
    raised eval budget actually reaches ``resolve_timeout``.

Run: .venv/bin/python -m pytest tests/unit/test_eval_batch_timeout_extension.py -q
INFERENCE-FREE.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.api.models import ChatRequest
from src.api.routes.chat_pipeline.routing_decision import resolve_timeout
from src.config import reset_config
from src.llm_primitives.primitives import LLMPrimitives
from src.roles import Role

# seeding_orchestrator + eval_tower live on sys.path under scripts/ (mirrors the
# import shim used by test_eval_tower_rel1_honesty_guards.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (REPO_ROOT / "scripts" / "benchmark", REPO_ROOT / "scripts" / "autopilot"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import eval_tower  # noqa: E402
import seeding_orchestrator  # noqa: E402

# Role SLA we pin for deterministic routing-timeout assertions. worker_general's
# interactive SLA is 60s; the env override lets us assert against a fixed base
# regardless of the live registry.
_PINNED_ROLE_SLA_S = 60
_WORKER_ROLE = str(Role.WORKER_GENERAL)


@pytest.fixture()
def pinned_worker_sla():
    """Pin the worker_general role SLA to 60s for resolve_timeout tests."""
    with patch.dict(os.environ, {"ORCHESTRATOR_TIMEOUTS_WORKER_GENERAL": str(_PINNED_ROLE_SLA_S)}):
        reset_config()
        try:
            yield _PINNED_ROLE_SLA_S
        finally:
            reset_config()


# ── resolve_timeout: eval_batch EXTENDS, everything else DOWN-only clamp ───────


class TestResolveTimeoutEvalBatchExtension:
    def test_request_shape_accepts_giant_eval_budget(self):
        request = ChatRequest(prompt="q", workload_class="eval_batch", timeout_s=3600)
        assert request.timeout_s == 3600

        with pytest.raises(ValidationError):
            ChatRequest(prompt="q", workload_class="eval_batch", timeout_s=3601)

    def test_eval_batch_extends_beyond_role_sla(self, pinned_worker_sla):
        """eval_batch + explicit timeout_s longer than the SLA -> the LONGER value."""
        request = ChatRequest(
            prompt="a hard MATH-tail question",
            workload_class="eval_batch",
            timeout_s=300,  # > 60s role SLA
        )
        assert resolve_timeout(request, [_WORKER_ROLE]) == 300
        assert 300 > pinned_worker_sla  # sanity: this is a genuine extension

    def test_eval_batch_shorter_timeout_still_honored(self, pinned_worker_sla):
        """eval_batch with a SHORTER declared budget takes that budget (max(1,·))."""
        request = ChatRequest(prompt="q", workload_class="eval_batch", timeout_s=25)
        assert resolve_timeout(request, [_WORKER_ROLE]) == 25

    def test_non_eval_traffic_clamps_down_unchanged(self, pinned_worker_sla):
        """Interactive traffic can only SHORTEN below the SLA, never extend."""
        request = ChatRequest(prompt="q", workload_class="interactive", timeout_s=3600)
        # min(60, 3600) == 60 — the DOWN-only clamp is preserved exactly.
        assert resolve_timeout(request, [_WORKER_ROLE]) == pinned_worker_sla

    def test_unset_workload_class_clamps_down_unchanged(self, pinned_worker_sla):
        """No workload_class == legacy path == DOWN-only clamp."""
        request = ChatRequest(prompt="q", timeout_s=300)
        assert resolve_timeout(request, [_WORKER_ROLE]) == pinned_worker_sla

    def test_timeout_s_absent_leaves_sla_unchanged(self, pinned_worker_sla):
        """No timeout_s -> role SLA, whether or not workload_class is eval_batch."""
        req_eval = ChatRequest(prompt="q", workload_class="eval_batch")
        req_plain = ChatRequest(prompt="q")
        assert resolve_timeout(req_eval, [_WORKER_ROLE]) == pinned_worker_sla
        assert resolve_timeout(req_plain, [_WORKER_ROLE]) == pinned_worker_sla

    def test_eval_batch_below_shorter_bound_floored_to_one(self, pinned_worker_sla):
        """Extension path still floors at 1 (max(1, int(timeout_s)))."""
        request = ChatRequest(prompt="q", workload_class="eval_batch", timeout_s=1)
        assert resolve_timeout(request, [_WORKER_ROLE]) == 1


# ── primitives clamp: identity for remaining<=base, extension for remaining>base ─


def _old_clamp_reference(timeout_s: float, remaining_s: float | None) -> int:
    """The clamp behavior BEFORE the EV-11c fix.

    Byte-for-byte reproduction of the historic body so identity can be proven
    against a fixed reference rather than a re-run of the (now-changed) method.
    """
    timeout_f = max(1.0, float(timeout_s))
    if remaining_s is None:
        return int(timeout_f)
    clamped_f = max(1.0, min(timeout_f, remaining_s))
    return int(clamped_f)


class TestClampTimeoutIdentityAndExtension:
    @pytest.mark.parametrize("remaining_s", [1.0, 5.0, 30.0, 59.0, 60.0])
    def test_identity_for_interactive_shaped_budgets(self, remaining_s):
        """remaining <= role_base: new clamp == pre-fix clamp, exactly.

        This is the IDENTITY PROOF. Interactive requests set their deadline to
        the role SLA (resolve_timeout) and it only decreases, so `remaining`
        never exceeds the 60s base -> the fix must be invisible to them.
        """
        base = 60
        primitives = LLMPrimitives(mock_mode=True)
        with primitives.request_context(deadline_s=None, task_id="identity"):
            with patch.object(primitives, "_remaining_deadline_s", return_value=remaining_s):
                new_val = primitives._clamp_timeout_to_request_budget(base)
                diag = primitives.get_budget_diagnostics()

        assert new_val == _old_clamp_reference(base, remaining_s)
        # Whenever the pre-fix path shrank the budget, the new path records the
        # SAME clamp diagnostics it always did (remaining < base cases here).
        if remaining_s < base:
            assert diag["budget_applied"] is True
            assert diag["timeout_clamp_events"] >= 1
        else:  # remaining == base: min() returned base, historic path no-op
            assert diag["budget_applied"] is False
            assert diag["timeout_clamp_events"] == 0

    def test_extends_when_remaining_exceeds_base(self):
        """remaining > role_base: use the full remaining budget (the EV-11c fix).

        This is the ONLY case that differs from the pre-fix behavior, and it
        only arises for an eval_batch request whose deadline was extended past
        the 60s worker SLA.
        """
        base = 60
        remaining_s = 300.0
        primitives = LLMPrimitives(mock_mode=True)
        with primitives.request_context(deadline_s=None, task_id="extend"):
            with patch.object(primitives, "_remaining_deadline_s", return_value=remaining_s):
                new_val = primitives._clamp_timeout_to_request_budget(base)
                diag = primitives.get_budget_diagnostics()

        assert new_val == 300  # full remaining budget, NOT capped to the 60s base
        assert new_val != _old_clamp_reference(base, remaining_s)  # pre-fix would be 60
        assert _old_clamp_reference(base, remaining_s) == base
        # Extension is not a clamp -> no shrink diagnostics recorded.
        assert diag["budget_applied"] is False
        assert diag["timeout_clamp_events"] == 0

    def test_no_deadline_returns_base_unchanged(self):
        """No request deadline -> role base passes through (both old and new)."""
        primitives = LLMPrimitives(mock_mode=True)
        with primitives.request_context(task_id="no-deadline"):
            val = primitives._clamp_timeout_to_request_budget(60)
        assert val == 60 == _old_clamp_reference(60, None)


# ── client payload: timeout_s + workload_class reach the server ────────────────


def _capture_payload(**call_kwargs) -> dict:
    """Fire call_orchestrator_forced through a MockTransport, return the JSON body."""
    captured: dict = {}

    def _handler(request):  # noqa: ANN001
        captured["payload"] = json.loads(request.content)
        return eval_tower.httpx.Response(200, json={"answer": "ok"})

    transport = eval_tower.httpx.MockTransport(_handler)
    with eval_tower.httpx.Client(transport=transport) as client:
        seeding_orchestrator.call_orchestrator_forced(client=client, **call_kwargs)
    return captured["payload"]


class TestClientPayloadCarriesEvalBudget:
    def test_payload_carries_timeout_s_and_workload_class(self, monkeypatch):
        monkeypatch.delenv("AUTOPILOT_EVAL_MIN_LLAMA_BUDGET_S", raising=False)
        payload = _capture_payload(
            prompt="a hard MATH-tail question",
            force_role="worker_math",
            timeout=300,  # the raised AUTOPILOT_EVAL_REQUEST_TIMEOUT_S
            workload_class="eval_batch",
        )
        assert payload["timeout_s"] == 300
        assert payload["workload_class"] == "eval_batch"
        assert payload["max_queue_wait_ms"] == 150_000
        # client_deadline_unix_s is derived from timeout -> a >60s remaining budget.
        assert payload["client_deadline_unix_s"] > 0

    def test_eval_queue_reserves_at_most_half_the_deadline(self, monkeypatch):
        monkeypatch.delenv("AUTOPILOT_EVAL_MIN_LLAMA_BUDGET_S", raising=False)
        payload = _capture_payload(
            prompt="q",
            force_role="frontdoor",
            timeout=600,
            workload_class="eval_batch",
        )
        assert payload["timeout_s"] == 600
        assert payload["max_queue_wait_ms"] == 300_000

    def test_non_eval_queue_cap_remains_legacy_90_seconds(self, monkeypatch):
        monkeypatch.delenv("AUTOPILOT_EVAL_MIN_LLAMA_BUDGET_S", raising=False)
        payload = _capture_payload(prompt="q", force_role="frontdoor", timeout=600)
        assert payload["max_queue_wait_ms"] == 90_000

    def test_legacy_payload_omits_workload_class_when_unset(self, monkeypatch):
        """Old-server-safe: no workload_class key when the caller doesn't set it."""
        monkeypatch.delenv("AUTOPILOT_EVAL_MIN_LLAMA_BUDGET_S", raising=False)
        payload = _capture_payload(prompt="q", force_role="frontdoor", timeout=120)
        assert "workload_class" not in payload
        assert payload["timeout_s"] == 120  # timeout_s always present


# ── window-runner budget default: honor AUTOPILOT_EVAL_REQUEST_TIMEOUT_S ────────


class TestWindowRunnerBudgetDefault:
    """EV-BASELINE-E7 root cause: the eval_batch window runner hardcoded
    ``--evaltower-timeout-s`` to 120.0 and ALWAYS passed it to ``EvalTower(...)``,
    silently overriding ``AUTOPILOT_EVAL_REQUEST_TIMEOUT_S`` — so every
    heavy-suite question was budgeted at 120s regardless of the env, and died at
    ~119-120s. The default is now deferred to the env-aware standard
    (``_default_eval_timeout``); an explicit flag still wins.
    """

    @staticmethod
    def _runner():
        import importlib

        return importlib.import_module("eval_batch_serving_evaltower_window")

    def test_default_honors_request_timeout_env(self, monkeypatch):
        monkeypatch.setenv("AUTOPILOT_EVAL_REQUEST_TIMEOUT_S", "420")
        runner = self._runner()
        args = runner.parse_args(["--api-url", "http://localhost:8000"])
        # The whole failure: this used to be 120.0 no matter the env.
        assert args.evaltower_timeout_s == 420.0

    def test_default_without_env_is_registry_derived_not_120(self, monkeypatch):
        monkeypatch.delenv("AUTOPILOT_EVAL_REQUEST_TIMEOUT_S", raising=False)
        runner = self._runner()
        args = runner.parse_args([])
        # Registry-derived eval default (frontdoor SLA + queue allowance), never
        # the old silent 120.0 cap.
        assert args.evaltower_timeout_s == float(eval_tower._default_eval_timeout())
        assert args.evaltower_timeout_s == 600.0

    def test_explicit_flag_still_wins(self, monkeypatch):
        monkeypatch.setenv("AUTOPILOT_EVAL_REQUEST_TIMEOUT_S", "420")
        runner = self._runner()
        args = runner.parse_args(["--evaltower-timeout-s", "90"])
        assert args.evaltower_timeout_s == 90.0


class TestPromptAwareEvalBudget:
    def test_ordinary_prompt_uses_base_budget(self):
        assert eval_tower._eval_question_timeout_s("short", 600) == 600

    def test_over_128k_chars_uses_giant_budget(self):
        assert eval_tower._eval_question_timeout_s("x" * 131_073, 600) == 1200

    def test_over_512k_chars_uses_extended_giant_budget(self):
        assert eval_tower._eval_question_timeout_s("x" * 524_289, 600) == 3600

    def test_explicit_larger_base_is_never_reduced(self):
        assert eval_tower._eval_question_timeout_s("short", 2400) == 2400

    def test_generation_dispatch_uses_prompt_aware_budget(self, monkeypatch):
        seen: dict[str, object] = {}

        def _fake_call(**kwargs):
            seen.update(kwargs)
            return {"answer": "ok", "tokens_generated": 1, "routed_to": "ingest_long_context"}

        monkeypatch.setattr(eval_tower, "call_orchestrator_forced", _fake_call)
        tower = eval_tower.EvalTower(timeout=600)
        question = {
            "id": "long-context",
            "suite": "longbench",
            "prompt": "x" * 131_073,
            "expected": "ok",
        }
        with eval_tower.httpx.Client(timeout=1) as client:
            outcome = tower._generate_question(question, client)

        assert outcome.error is None
        assert seen["timeout"] == 1200
        assert seen["workload_class"] == "eval_batch"


# ── end-to-end: a tier-style eval request carries its 420s budget to the backend ─


class _RecordingBackend:
    """Captures the ``request.timeout`` that reaches the llama-server backend."""

    def __init__(self):
        self.seen_timeout = None

    class _Result:
        output = "ok"
        tokens_generated = 1
        prompt_eval_ms = 0.0
        generation_ms = 0.0
        http_overhead_ms = 0.0
        predicted_per_second = 1.0
        completion_probabilities: list = []
        first_token_ms = 0.0
        stream_chunks = 1
        completion_reason = "stop"
        success = True
        partial = False

    def infer(self, role_config, request):
        self.seen_timeout = request.timeout
        return self._Result()

    def infer_stream_text(self, role_config, request, on_chunk=None):
        self.seen_timeout = request.timeout
        return self._Result()


class TestTierBudgetReachesBackendEndToEnd:
    """Mocked chain proving the 420s tier budget survives every hop:

    client payload ``timeout_s`` -> ``resolve_timeout`` (eval_batch EXTENDS) ->
    the ``chat.py`` request deadline -> ``_clamp_timeout_to_request_budget`` ->
    ``InferenceRequest.timeout`` at the backend. Regression against the
    EV-BASELINE-E7 120s deaths (backend saw the 120s ``inference_default``
    because the budget was dropped before it).
    """

    def test_420_budget_reaches_backend_not_120(self, monkeypatch):
        monkeypatch.setenv("AUTOPILOT_EVAL_REQUEST_TIMEOUT_S", "420")
        monkeypatch.delenv("AUTOPILOT_EVAL_MIN_LLAMA_BUDGET_S", raising=False)

        budget = eval_tower._default_eval_timeout()
        assert budget == 420  # env-derived per-question budget

        # Hop 1 — client payload carries the budget + eval_batch class.
        payload = _capture_payload(
            prompt="a hard reasoning question",
            force_role="frontdoor",
            timeout=budget,
            workload_class="eval_batch",
        )
        assert payload["timeout_s"] == 420
        assert payload["workload_class"] == "eval_batch"

        # Hop 2 — server resolve_timeout EXTENDS to the declared eval budget.
        req = ChatRequest(
            prompt=payload["prompt"],
            timeout_s=payload["timeout_s"],
            workload_class=payload["workload_class"],
            client_deadline_unix_s=payload["client_deadline_unix_s"],
        )
        resolved = resolve_timeout(req, ["frontdoor"])
        assert resolved == 420

        # Hop 3 — the chat.py deadline is built from the resolved budget, and
        # Hop 4 — the backend request.timeout is clamped to that deadline
        # (NOT capped to the 60/180 role SLA and NOT the 120 default).
        import time as _time

        primitives = LLMPrimitives(
            mock_mode=False, server_urls={"frontdoor": ""}, registry=None
        )
        backend = _RecordingBackend()
        primitives._backends = {"frontdoor": backend}
        primitives.server_urls = {"frontdoor": ""}
        primitives.admission_controller = None
        primitives.health_tracker = None

        request_deadline_s = _time.perf_counter() + max(1.0, float(resolved))
        with primitives.request_context(
            deadline_s=request_deadline_s,
            task_id="e2e",
            workload_class="eval_batch",
        ):
            # n_probs path (backend.infer) AND streaming path both must carry it.
            primitives._call_caching_backend(
                backend, "hi", "frontdoor", n_tokens=64, n_probs=5
            )
        assert backend.seen_timeout is not None
        assert backend.seen_timeout >= 418  # ~420, never the 120 default
        assert backend.seen_timeout != 120

    def test_120s_arg_default_would_have_capped_backend_at_120(self):
        """Counterfactual: the OLD 120s budget clamps the backend to 120 for a
        frontdoor request (role SLA 180 > remaining 120), reproducing the death.
        """
        import time as _time

        req = ChatRequest(prompt="q", timeout_s=120, workload_class="eval_batch")
        assert resolve_timeout(req, ["frontdoor"]) == 120  # the declared 120s

        primitives = LLMPrimitives(
            mock_mode=False, server_urls={"frontdoor": ""}, registry=None
        )
        backend = _RecordingBackend()
        primitives._backends = {"frontdoor": backend}
        primitives.server_urls = {"frontdoor": ""}
        primitives.admission_controller = None
        primitives.health_tracker = None
        with primitives.request_context(
            deadline_s=_time.perf_counter() + 120.0,
            task_id="cf",
            workload_class="eval_batch",
        ):
            primitives._call_caching_backend(
                backend, "hi", "frontdoor", n_tokens=64, n_probs=5
            )
        # remaining (~120) < frontdoor role base (180) -> clamped down to ~120.
        assert backend.seen_timeout <= 120
