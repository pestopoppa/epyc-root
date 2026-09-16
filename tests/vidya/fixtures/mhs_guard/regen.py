"""Generate the VB-MHS-OPS fixture with the REAL producer code (gate-frontier branch).

Run: python3 tests/vidya/fixtures/mhs_guard/regen.py <gate-frontier-worktree> tests/vidya/fixtures/mhs_guard/orchestration
Writes <out-dir>/autopilot_journal.jsonl and <out-dir>/autopilot_rejected_mutations.jsonl.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(src / "scripts" / "autopilot"))
sys.path.insert(0, str(src))

import types
for _m in ("httpx",):
    sys.modules.setdefault(_m, types.ModuleType(_m))  # import-time dep only; unused here
import rejected_mutation_ledger as rml  # noqa: E402
from eval_leakage_monitor import EvalLeakageMonitor  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from species import prompt_forge as pf  # noqa: E402

work = Path(tempfile.mkdtemp())
journal = ExperimentJournal(work, segment_snapshots=False)
CLOCK = {"ts": ""}


class TimedJournal:
    """Pins the ledger-event timestamp; the real append_ledger_event does the write."""

    def append_ledger_event(self, event):
        event = dict(event)
        event["timestamp"] = CLOCK["ts"]
        return journal.append_ledger_event(event)


class StubForge:
    EVAL_ID_VOCAB_SOURCES_ENV = pf.EVAL_ID_VOCAB_SOURCES_ENV if hasattr(
        pf, "EVAL_ID_VOCAB_SOURCES_ENV") else "AUTOPILOT_EVAL_ID_VOCAB_SOURCES"

    def __init__(self):
        self.available = False

    def set_eval_leakage_observer(self, fn):
        pass

    def describe_eval_id_sources(self):
        return [{"path": "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/debug/"
                         "question_pool.jsonl", "required": True, "exists": self.available,
                 "readable": self.available}]

    def load_eval_id_vocabulary(self):
        if self.available:
            return vocab_on
        return pf.EvalIdVocabulary(error="eval_id_source_missing:question_pool.jsonl")


class Alarm:
    def raise_alarm(self, message, evidence):
        return True

    def clear_alarm(self, message):
        return True


forge = StubForge()
mon = EvalLeakageMonitor(journal=TimedJournal(), state={}, alarm=Alarm(),
                         prompt_forge_module=forge, threshold=3, reassert_s=900.0,
                         clock=lambda: 0.0)

vocab_off = pf.EvalIdVocabulary(error="eval_id_source_missing:question_pool.jsonl")
vocab_on = pf.EvalIdVocabulary.from_rows([{"id": "mmlu_pro_q00017", "suite": "mmlu_pro"}])
assert vocab_on.available, vocab_on
LEAK = pf.eval_leakage_reason("Remember the answer to mmlu_pro_q00017 is B.", vocab_on)
assert LEAK and LEAK.startswith("eval_instance_leakage:"), LEAK
REASON = {
    "leak": LEAK,
    "vocab": pf.eval_leakage_reason("x", vocab_off),
    "risk": pf.mutation_risk_gate_reason("unknown"),
    "integrity": "prompt_integrity:missing required section '## Output'",
}
assert REASON["vocab"].startswith("eval_leakage_vocabulary_unavailable:"), REASON
assert REASON["risk"] and REASON["risk"].startswith("effect_risk_gate:"), REASON


def trial(tid, ts, action_type, status, species="prompt_forge"):
    journal.record(JournalEntry(
        trial_id=tid, timestamp=ts, species=species, action_type=action_type, tier=0,
        quality=0.0, speed=0.0, cost=0.0, reliability=0.0,
        pareto_status="skipped" if status != "ok" else "dominated",
        config_snapshot={"type": action_type, "file": "roles/coder_primary.md",
                         "mutation": "targeted_fix"},
        reasoning="{}", memory_count=0, outcome_status=status))


def reject(tid, ts, gate, detail="", kind="prompt"):
    rml.append_record(work, rml.build_record(
        target="roles/coder_primary.md", mutation_type="targeted_fix", artifact_kind=kind,
        rejecting_gate=gate, original_content="a\n", mutated_content="b\n",
        gate_detail=detail, trial_id=tid, timestamp=ts))


D = "2026-09-17T"
# pre-hook (hook = 2026-09-17T10:00:00+00:00): a guard-shaped reject that must NOT count
trial(100, D + "09:00:00+00:00", "prompt_mutation", "skipped")
reject(100, D + "09:00:00+00:00", "transfer_safety", REASON["leak"])
# startup preflight fails right after the hook
CLOCK["ts"] = D + "10:00:05+00:00"
mon.preflight()
trial(101, D + "10:01:00+00:00", "prompt_mutation", "skipped")
reject(101, D + "10:01:00+00:00", "transfer_safety", REASON["leak"])
trial(102, D + "10:02:00+00:00", "prompt_mutation", "ok")
trial(103, D + "10:03:00+00:00", "code_mutation", "skipped")
reject(103, D + "10:03:00+00:00", "transfer_safety", REASON["risk"], kind="code")
for n in range(3):  # three unavailable verdicts open the circuit; only trial 104 is journaled
    CLOCK["ts"] = D + "10:05:00+00:00"
    mon.observe(False, "eval_id_source_missing:question_pool.jsonl")
trial(104, D + "10:05:00+00:00", "prompt_mutation", "skipped")
reject(104, D + "10:05:00+00:00", "transfer_safety", REASON["vocab"])
trial(105, D + "10:10:00+00:00", "prompt_mutation", "ok")
reject(105, D + "10:10:00+00:00", "safety_gate", "quality regression")
trial(106, D + "10:11:00+00:00", "prompt_mutation", "skipped")  # file not found: no ledger
trial(107, D + "10:12:00+00:00", "numeric_trial", "ok", species="numeric_swarm")
trial(108, D + "10:13:00+00:00", "code_mutation", "skipped")
reject(108, D + "10:13:00+00:00", "syntax_validation", kind="code")
trial(109, D + "10:20:00+00:00", "prompt_mutation", "skipped")
reject(109, D + "10:20:00+00:00", "transfer_safety", REASON["integrity"])
forge.available = True
CLOCK["ts"] = D + "10:35:00+00:00"
mon.observe(True)
# next day: closes the 09-17 window; its own window stays open; an unclosed alarm
trial(110, "2026-09-18T01:00:00+00:00", "prompt_mutation", "ok")
forge.available = False
mon.consecutive = 0
for n in range(3):
    CLOCK["ts"] = "2026-09-18T02:00:00+00:00"
    mon.observe(False, "eval_id_source_unreadable:truncated")

out.mkdir(parents=True, exist_ok=True)
for name in ("autopilot_journal.jsonl", "autopilot_rejected_mutations.jsonl"):
    shutil.copy(work / name, out / name)
print(sorted(p.name for p in work.iterdir()))
