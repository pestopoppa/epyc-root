"""AP-53: the harness records every rejected prompt/code mutation and feeds it back.

Pins: each reject path in actions.py writes {target, mutation_type, unified diff,
per-suite deltas, rejecting gate, timestamp}; accepted mutations write nothing;
the ledger reaches the mutation prompt for the same target only; a ledger
failure never changes the trial; torn lines are skipped.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "autopilot"))

actions = importlib.import_module("actions")
ledger = importlib.import_module("rejected_mutation_ledger")
from safety_gate import SafetyVerdict  # noqa: E402


class _Journal:
    def __init__(self, journal_dir: Path):
        self.journal_dir = journal_dir

    def recent_failures(self, *, species, n):
        return []

    def insights_text(self, n):
        return "(no insights yet)"

    def all_entries(self):
        return []

    def recent(self, n):
        return []

    def next_trial_id(self):
        return 41


class _Forge:
    def __init__(self, *, safety_valid=True, syntax_valid=True, mutated="new line\n"):
        self.safety_valid = safety_valid
        self.syntax_valid = syntax_valid
        self.mutated = mutated
        self.contexts: list[str] = []
        self.reverted = 0

    def _mutation(self, kwargs):
        return SimpleNamespace(
            file=kwargs["target_file"],
            mutation_type=kwargs["mutation_type"],
            description="d",
            original_content="old line\n",
            mutated_content=self.mutated,
            safety_valid=self.safety_valid,
            safety_reason="touches forbidden path" if not self.safety_valid else "ok",
            syntax_valid=self.syntax_valid,
        )

    def propose_mutation(self, **kwargs):
        self.contexts.append(kwargs.get("failure_context", ""))
        return self._mutation(kwargs)

    def propose_code_mutation(self, **kwargs):
        self.contexts.append(kwargs.get("failure_context", ""))
        return self._mutation(kwargs)

    def apply_mutation(self, mutation):
        pass

    def apply_code_mutation(self, mutation):
        pass

    def revert_mutation(self, mutation):
        self.reverted += 1

    def revert_code_mutation(self, mutation):
        self.reverted += 1


class _Gate:
    def __init__(self, passed: bool):
        self.passed = passed
        self.baseline = SimpleNamespace(
            pin_tier=lambda tier, register=False: SimpleNamespace(
                per_suite_quality={"math": 1.5, "code": 1.0}
            )
        )

    def check(self, result):
        return SafetyVerdict(passed=self.passed, violations=[] if self.passed else ["Quality regression"])


class _Tower:
    def hybrid_eval(self):
        return actions.EvalResult(
            tier=1, quality=1.2, speed=10.0, cost=0.0, reliability=1.0,
            per_suite_quality={"math": 1.2, "code": 1.1, "new_suite": 0.3},
        )


class _Swarm:
    def mark_epoch(self, epoch):
        pass


def _ctx(tmp_path, forge, *, passed):
    return actions._ActionContext(
        seeder=None, swarm=_Swarm(), forge=forge, lab=None, tower=_Tower(),
        gate=_Gate(passed), archive=None, journal=_Journal(tmp_path),
        state={"trial_counter": 7}, strategy_store=None, evo=None,
    )


@pytest.fixture(autouse=True)
def _gates_off(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_SKILL_EFFICACY_GATE", raising=False)
    monkeypatch.delenv("AUTOPILOT_BSV2_ACCEPT_GATE", raising=False)


def test_safety_gate_reject_writes_full_record(tmp_path):
    forge = _Forge()
    actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix",
         "description": "tighten retries"},
        _ctx(tmp_path, forge, passed=False),
    )
    assert forge.reverted == 1
    rows = ledger.load_records(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["writer"] == "harness"
    assert row["target"] == "frontdoor.md"
    assert row["mutation_type"] == "targeted_fix"
    assert row["rejecting_gate"] == "safety_gate"
    assert row["gate_detail"] == "Quality regression"
    assert row["trial_id"] == 7
    assert "-old line" in row["unified_diff"] and "+new line" in row["unified_diff"]
    assert len(row["diff_sha256"]) == 64
    assert row["per_suite_deltas"] == {"code": 0.1, "math": -0.3}
    assert row["per_suite_deltas_basis"] == "candidate_minus_tier_baseline"
    assert row["timestamp"]


def test_accepted_mutation_writes_nothing(tmp_path):
    actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
        _ctx(tmp_path, _Forge(), passed=True),
    )
    assert ledger.load_records(tmp_path) == []


def test_pre_eval_rejects_are_recorded(tmp_path):
    actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
        _ctx(tmp_path, _Forge(safety_valid=False), passed=True),
    )
    actions._action_code_mutation(
        {"type": "code_mutation", "file": "src/x.py", "mutation": "targeted_fix"},
        _ctx(tmp_path, _Forge(syntax_valid=False), passed=True),
    )
    rows = ledger.load_records(tmp_path)
    assert [(r["target"], r["rejecting_gate"]) for r in rows] == [
        ("frontdoor.md", "transfer_safety"),
        ("src/x.py", "syntax_validation"),
    ]
    assert rows[0]["gate_detail"] == "touches forbidden path"
    assert rows[0]["per_suite_deltas_basis"] == "unavailable"


def test_code_and_gepa_safety_rejects_are_recorded(tmp_path):
    actions._action_code_mutation(
        {"type": "code_mutation", "file": "src/x.py", "mutation": "targeted_fix"},
        _ctx(tmp_path, _Forge(), passed=False),
    )
    actions._action_gepa_optimize(
        {"type": "gepa_optimize", "file": "frontdoor.md"},
        _ctx(tmp_path, _Forge(), passed=False),
    )
    rows = ledger.load_records(tmp_path)
    assert [(r["artifact_kind"], r["mutation_type"], r["rejecting_gate"]) for r in rows] == [
        ("code", "targeted_fix", "safety_gate"),
        ("prompt", "gepa", "safety_gate"),
    ]


def test_rejections_feed_the_next_mutation_prompt_for_same_target_only(tmp_path):
    ctx = _ctx(tmp_path, _Forge(), passed=False)
    action = {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"}
    actions._action_prompt_mutation(action, ctx)
    actions._action_prompt_mutation(action, ctx)

    context, _ = actions._build_mutation_context(action, ctx)
    assert context.startswith("## Previously Rejected Mutations of `frontdoor.md`")
    assert "rejected by `safety_gate`" in context
    assert "this exact diff was rejected 2x" in context
    assert "+new line" in context

    other, _ = actions._build_mutation_context(
        {"type": "prompt_mutation", "file": "worker.md", "mutation": "targeted_fix"}, ctx
    )
    assert "Previously Rejected" not in other


def test_ledger_failure_never_changes_the_trial(tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(ledger, "build_record", boom)
    forge = _Forge()
    result, species = actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
        _ctx(tmp_path, forge, passed=False),
    )
    assert species == "prompt_forge"
    assert result.quality == 1.2
    assert forge.reverted == 1


def test_journal_without_dir_is_a_no_op(tmp_path):
    ctx = _ctx(tmp_path, _Forge(), passed=False)
    ctx.journal.journal_dir = None
    actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"}, ctx
    )
    assert not ledger.ledger_path(tmp_path).exists()


def test_torn_line_is_skipped_and_long_diffs_are_truncated_with_full_hash(tmp_path):
    big = "x\n" * 10000
    rec = ledger.build_record(
        target="t.md", mutation_type="compress", artifact_kind="prompt",
        rejecting_gate="simplicity", original_content="", mutated_content=big,
    )
    assert rec["diff_truncated"] is True
    assert len(rec["unified_diff"]) == ledger.MAX_STORED_DIFF_CHARS
    assert ledger.append_record(tmp_path, rec)
    with open(ledger.ledger_path(tmp_path), "a") as f:
        f.write('{"target": "t.md", "torn')
    rows = ledger.load_records(tmp_path)
    assert len(rows) == 1
    rendered = ledger.render_for_prompt(tmp_path, "t.md")
    assert "(diff truncated)" in rendered


# ── planner-facing fold over the journal ──────────────────────────────────────


def _row(trial_id, action, **over):
    base = dict(
        trial_id=trial_id, config_snapshot=action, pareto_status="dominated",
        outcome_status="ok", failure_analysis="", deficiency_category="",
        bug_corrupted_by="", keep_revert_decision="", eval_details={},
    )
    base.update(over)
    return SimpleNamespace(**base)


FLAG = {"type": "structural_experiment", "flags": {"user_modeling": True}, "description": "a"}
FAIL = "VIOLATIONS:\n  - Quality floor violation: 0.360 < 1.0 (tier 1)\n"


def test_planner_fold_lists_hard_rejections_and_counts_repeats():
    rows = [
        _row(1, FLAG, failure_analysis=FAIL),
        _row(2, dict(FLAG, description="reworded"), failure_analysis=FAIL),
        _row(3, {"type": "structural_experiment", "flags": {"x": True}}, outcome_status="invalid",
             failure_analysis="flag dependency missing"),
    ]
    recs = ledger.rejected_configs_from_entries(rows)
    assert [(r["last_trial_id"], r["rejections"], r["last_reason"]) for r in recs] == [
        (2, 2, "safety_gate"), (3, 1, "invalid"),
    ]
    text = ledger.render_rejected_configs_for_planner(rows)
    assert "trial #2 x2 structural_experiment" in text
    assert "Quality floor violation: 0.360 < 1.0 (tier 1)" in text
    assert "VIOLATIONS" not in text


def test_planner_fold_ignores_soft_neutral_observational_and_replay_rows():
    rows = [
        _row(1, FLAG),  # merely dominated: not a hard rejection
        _row(2, FLAG, failure_analysis=FAIL, bug_corrupted_by="abc123"),
        _row(3, FLAG, failure_analysis=FAIL, deficiency_category="seq_accumulating"),
        _row(4, FLAG, failure_analysis=FAIL, eval_details={"multitier_validation": {"stage": "t2"}}),
        _row(5, {"type": "seed_batch"}, outcome_status="invalid"),
        _row(6, {"type": "numeric_trial", "params": {"a": 0.1}}, failure_analysis=FAIL),
    ]
    assert ledger.rejected_configs_from_entries(rows) == []
    assert ledger.render_rejected_configs_for_planner(rows) == ""


def test_later_frontier_acceptance_clears_the_rejection():
    rows = [
        _row(1, FLAG, failure_analysis=FAIL),
        _row(2, FLAG, pareto_status="frontier"),
    ]
    assert ledger.rejected_configs_from_entries(rows) == []


def test_sequential_refutation_is_a_hard_rejection():
    rows = [_row(1, FLAG, deficiency_category="seq_refuted")]
    assert ledger.rejected_configs_from_entries(rows)[0]["last_reason"] == "sequential_refuted"


def test_autopilot_planner_feedback_uses_folded_journal():
    autopilot = importlib.import_module("autopilot")

    class J:
        def entries_with_supersessions(self):
            return [_row(9, FLAG, failure_analysis=FAIL)]

    assert autopilot._build_rejected_config_feedback(J()).startswith(
        "\n\n## Previously Rejected Configs"
    )

    class Broken:
        def all_entries(self):
            raise RuntimeError("boom")

    assert autopilot._build_rejected_config_feedback(Broken()) == ""
