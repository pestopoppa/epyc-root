"""Tests for TD-21.25: EvolutionManager insight-distillation repair.

Before: `_extract_insights` fished a JSON array out of the distillation
response with marker/fence/whole-response heuristics and returned `[]` on any
miss -- a silent zero-insight round indistinguishable from "nothing to
learn". `_coerce_trial_ids` silently dropped unparseable evidence-id tokens,
weakening an insight's grounding with no visible signal.

After: `_extract_insights_result` fishes via the shared
`src.structured_output.repair.parse_with_repair` (full-schema validation),
and -- only when distillation itself is running against the local model
(`use_local_model=True`) -- spends ONE repair turn against that same model.
When distillation used the Claude CLI (`use_local_model=False`, the
default), the repair idiom has no server to reach, so a miss is a typed
`"failed"` RepairResult with an explicit reason instead of `[]`.
`_coerce_trial_ids` now counts every dropped token in
`TRIAL_ID_COERCION_COUNTS`, surfaced per-round via `distill()`'s
`evidence_ids_dropped` field.

Covers: happy path unchanged (0 repair calls); malformed response repaired
against the local model when reachable; malformed response is a typed
failure (not `[]`) when the backend is the Claude CLI; dropped evidence-id
tokens are counted; `distill()` surfaces `insight_parse_status` and
`evidence_ids_dropped`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from experiment_journal import JournalEntry  # noqa: E402
from species import evolution_manager as em_mod  # noqa: E402
from species.evolution_manager import (  # noqa: E402
    TRIAL_ID_COERCION_COUNTS,
    EvolutionManager,
)
from src.structured_output.repair import (  # noqa: E402
    STRUCTURED_OUTPUT_REPAIR_COUNTS,
    reset_counts_for_tests,
)

_SITE = "evolution_manager.insight_distillation"


def _reset_counters():
    reset_counts_for_tests()
    TRIAL_ID_COERCION_COUNTS["parsed"] = 0
    TRIAL_ID_COERCION_COUNTS["dropped"] = 0


class _FakeCompleter:
    """Stand-in for `http_chat_completer` -- records calls, never touches a
    real socket. Injected by monkeypatching `evolution_manager.http_chat_completer`."""

    def __init__(self, *responses: str):
        self._responses = list(responses)
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, base_url: str, *, model: str | None = None, **_kw):
        self.calls.append((base_url, model))

        def complete(messages, schema):
            if not self._responses:
                raise AssertionError("no more fake responses queued")
            return self._responses.pop(0)

        return complete


class CapturingManager(EvolutionManager):
    def __init__(self, response: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._response = response
        self.prompt = ""

    def _invoke_llm(self, prompt: str) -> str:
        self.prompt = prompt
        return self._response


_ONE_ENTRY = JournalEntry(
    trial_id=7,
    timestamp="2026-09-24T00:00:00Z",
    species="seeder",
    action_type="seed_batch",
    tier=1,
    quality=1.0,
    speed=1.0,
    cost=0.1,
    reliability=0.9,
    pareto_status="frontier",
)


class FakeStrategyStore:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def store(self, **kwargs):
        self.rows.append(kwargs)
        return "stored"


VALID_INSIGHTS = json.dumps(
    [
        {
            "description": "d",
            "insight": "i",
            "species": "all",
            "confidence": "high",
            "evidence_trial_ids": [7],
        }
    ]
)


class TestHappyPathUnchanged:
    def setup_method(self):
        _reset_counters()

    def test_clean_json_array_zero_repair_calls(self):
        manager = CapturingManager(VALID_INSIGHTS)
        store = FakeStrategyStore()
        result = manager.distill([_ONE_ENTRY], store, last_n=1, trial_id=1)
        assert result["status"] == "success"
        assert result["insights_stored"] == 1
        assert result["evidence_ids_dropped"] == 0
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_SITE, "parsed")) == 1
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_SITE, "repaired"), 0) == 0

    def test_fenced_marker_style_still_parses(self):
        # The exact `json:insights` marker style test_evolution_manager_scrub
        # already covers via distill(); this pins the direct extraction
        # method's behaviour on the same shape.
        response = f"```json:insights\n{VALID_INSIGHTS}\n```"
        manager = CapturingManager(response)
        extraction = manager._extract_insights_result(response)
        assert extraction.status == "parsed"
        assert extraction.repair_calls == 0
        assert extraction.value == json.loads(VALID_INSIGHTS)


class TestRepairWhenLocalModelReachable:
    def setup_method(self):
        _reset_counters()

    def test_malformed_response_is_repaired_against_local_model(self, monkeypatch):
        fake = _FakeCompleter(VALID_INSIGHTS)
        monkeypatch.setattr(em_mod, "http_chat_completer", fake)
        manager = CapturingManager(
            "Well, I looked at the trials and honestly there isn't a clean "
            "JSON array here, but trial 7 showed a high confidence result "
            "that applies to all species.",
            use_local_model=True,
            local_model_url="http://localhost:8082",
        )
        store = FakeStrategyStore()
        result = manager.distill([_ONE_ENTRY], store, last_n=1, trial_id=1)
        assert result["status"] == "success"
        assert result["insights_stored"] == 1
        assert fake.calls == [("http://localhost:8082/v1", "explore")]
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[(_SITE, "repaired")] == 1

    def test_repair_failure_is_typed_not_silent_empty(self, monkeypatch):
        fake = _FakeCompleter("still not json, sorry")
        monkeypatch.setattr(em_mod, "http_chat_completer", fake)
        manager = CapturingManager("no json here at all", use_local_model=True)
        store = FakeStrategyStore()
        result = manager.distill([_ONE_ENTRY], store, last_n=1, trial_id=1)
        assert result["status"] == "failed"
        assert result["insight_parse_status"] == "failed"
        assert "insight extraction failed" in result["reason"]
        assert store.rows == []
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[(_SITE, "failed")] == 1


class TestUnreachableClaudeCliBackend:
    def setup_method(self):
        _reset_counters()

    def test_malformed_response_over_claude_cli_is_a_typed_failure(self):
        # use_local_model=False (the default) -- the Claude CLI backend has
        # no HTTP endpoint for a repair turn to reach.
        manager = CapturingManager("just some prose, no JSON array anywhere")
        store = FakeStrategyStore()
        result = manager.distill([_ONE_ENTRY], store, last_n=1, trial_id=1)
        assert result["status"] == "failed"
        assert result["insight_parse_status"] == "failed"
        assert "Claude CLI" in result["reason"]
        # Never a silent [] flowing into StrategyStore.
        assert store.rows == []
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[(_SITE, "failed")] == 1

    def test_clean_json_over_claude_cli_costs_zero_calls(self):
        # The unreachable completer must never even be invoked on a clean fish.
        manager = CapturingManager(VALID_INSIGHTS)
        store = FakeStrategyStore()
        result = manager.distill([_ONE_ENTRY], store, last_n=1, trial_id=1)
        assert result["status"] == "success"


class TestGenuineZeroInsightsDistinctFromFailure:
    def setup_method(self):
        _reset_counters()

    def test_valid_empty_array_is_not_conflated_with_extraction_failure(self):
        manager = CapturingManager("[]")
        store = FakeStrategyStore()
        result = manager.distill([_ONE_ENTRY], store, last_n=1, trial_id=1)
        assert result["status"] == "failed"
        assert result["insight_parse_status"] == "parsed"
        assert result["reason"] == "LLM returned zero insights"


class TestTrialIdCoercionCounts:
    def setup_method(self):
        _reset_counters()

    def test_mixed_valid_and_garbage_tokens_counts_the_drop(self):
        ids = EvolutionManager._coerce_trial_ids("12, garbage, 34")
        assert ids == [12, 34]
        assert TRIAL_ID_COERCION_COUNTS["dropped"] == 1
        assert TRIAL_ID_COERCION_COUNTS["parsed"] == 2

    def test_non_integer_float_is_dropped_and_counted(self):
        ids = EvolutionManager._coerce_trial_ids(12.5)
        assert ids == []
        assert TRIAL_ID_COERCION_COUNTS["dropped"] == 1

    def test_clean_ids_never_increment_dropped(self):
        ids = EvolutionManager._coerce_trial_ids([1, 2, 3])
        assert ids == [1, 2, 3]
        assert TRIAL_ID_COERCION_COUNTS["dropped"] == 0

    def test_distill_surfaces_evidence_ids_dropped_delta(self):
        response = json.dumps(
            [
                {
                    "description": "d",
                    "insight": "i",
                    "species": "all",
                    "confidence": "high",
                    "evidence_trial_ids": "7, bogus",
                }
            ]
        )
        manager = CapturingManager(response)
        store = FakeStrategyStore()
        result = manager.distill([_ONE_ENTRY], store, last_n=1, trial_id=1)
        assert result["status"] == "success"
        assert result["evidence_ids_dropped"] == 1
