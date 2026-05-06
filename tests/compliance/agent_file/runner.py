"""Per-model agent-file compression-tolerance runner.

Phase 2 scaffolding: takes (model_id, agent_file_path, level, llm_call) and
returns (token_count, compliance_pass_rate, recall_pass_rate, procedure_pass_rate).

Phase 3 (inference-gated, out of scope here): wire `llm_call` to the actual
model server / Q-scorer pipeline. This module accepts a CALLABLE so unit
tests can use a deterministic fake (`make_fake_llm()`).

Usage:
    from tests.compliance.agent_file.runner import run_compliance_suite, make_fake_llm

    result = run_compliance_suite(
        model_id="opus-4.7",
        agent_file_path="agents/shared/ENGINEERING_STANDARDS.md",
        level="mild",
        llm_call=make_fake_llm("perfect"),
    )
    # → {model_id, agent_file_path, level, token_count,
    #    compliance_pass_rate, recall_pass_rate, procedure_pass_rate, ...}

CLI: `python -m tests.compliance.agent_file.runner --dry-run` runs the
deterministic-fake path against the original agent file at level=none.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from tests.compliance.agent_file.forbidden_actions import all_tasks as forbidden_tasks
from tests.compliance.agent_file.instruction_recall import all_tasks as recall_tasks
from tests.compliance.agent_file.procedure_correctness import all_tasks as procedure_tasks


LLMCall = Callable[[str, str], str]
"""(agent_file_text, prompt) -> model response text."""


@dataclass
class TaskResult:
    task_id: str
    pass_: bool
    reason: str = ""


@dataclass
class SuiteResult:
    model_id: str
    agent_file_path: str
    level: str
    token_count: int  # rough char-based proxy unless a tokenizer is supplied
    forbidden_action_results: list[TaskResult] = field(default_factory=list)
    procedure_results: list[TaskResult] = field(default_factory=list)
    recall_results: list[TaskResult] = field(default_factory=list)

    @property
    def compliance_pass_rate(self) -> float:
        if not self.forbidden_action_results:
            return 0.0
        return sum(r.pass_ for r in self.forbidden_action_results) / len(self.forbidden_action_results)

    @property
    def procedure_pass_rate(self) -> float:
        if not self.procedure_results:
            return 0.0
        return sum(r.pass_ for r in self.procedure_results) / len(self.procedure_results)

    @property
    def recall_pass_rate(self) -> float:
        if not self.recall_results:
            return 0.0
        return sum(r.pass_ for r in self.recall_results) / len(self.recall_results)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "agent_file_path": self.agent_file_path,
            "level": self.level,
            "token_count": self.token_count,
            "compliance_pass_rate": round(self.compliance_pass_rate, 4),
            "procedure_pass_rate": round(self.procedure_pass_rate, 4),
            "recall_pass_rate": round(self.recall_pass_rate, 4),
            "forbidden_action_results": [asdict(r) for r in self.forbidden_action_results],
            "procedure_results": [asdict(r) for r in self.procedure_results],
            "recall_results": [asdict(r) for r in self.recall_results],
        }


def _check_substring_any(response: str, anchors: Iterable[str]) -> bool:
    """True iff at least one anchor substring (case-insensitive) is in response."""
    rl = response.lower()
    return any(a.lower() in rl for a in anchors)


def _check_ordered_anchors(response: str, anchors: list[str]) -> bool:
    """True iff all anchors appear in the response in order (case-insensitive).

    Each anchor must appear AFTER the previous one's match position.
    """
    rl = response.lower()
    cursor = 0
    for a in anchors:
        idx = rl.find(a.lower(), cursor)
        if idx < 0:
            return False
        cursor = idx + len(a)
    return True


def _approx_token_count(text: str) -> int:
    """Rough ~4-chars-per-token proxy. Replace with model-specific tokenizer
    in Phase 3."""
    return max(1, len(text) // 4)


def run_compliance_suite(
    model_id: str,
    agent_file_path: Path | str,
    level: str,
    llm_call: LLMCall,
) -> SuiteResult:
    """Run all three task pools against `model_id` reading `agent_file_path`.

    `llm_call(agent_file_text, prompt) -> str` is injected; in Phase 2 this
    is `make_fake_llm(...)`. In Phase 3 it routes to the live model.
    """
    path = Path(agent_file_path)
    if not path.exists():
        raise FileNotFoundError(f"agent file not found: {agent_file_path}")

    agent_file_text = path.read_text(encoding="utf-8")
    suite = SuiteResult(
        model_id=model_id,
        agent_file_path=str(path),
        level=level,
        token_count=_approx_token_count(agent_file_text),
    )

    # Forbidden-action tasks: pass if response contains any expected clause substring.
    for task in forbidden_tasks():
        response = llm_call(agent_file_text, task.prompt)
        passed = _check_substring_any(response, task.expected_clause_substrings)
        suite.forbidden_action_results.append(
            TaskResult(
                task_id=task.task_id,
                pass_=passed,
                reason="cited expected clause" if passed else "no expected clause cited",
            )
        )

    # Procedure tasks: ordered-anchor check.
    for task in procedure_tasks():
        response = llm_call(agent_file_text, task.prompt)
        passed = _check_ordered_anchors(response, task.ordered_step_anchors)
        suite.procedure_results.append(
            TaskResult(
                task_id=task.task_id,
                pass_=passed,
                reason="all anchors in order" if passed else "missing or out-of-order anchor",
            )
        )

    # Recall tasks: any acceptable-answer substring.
    for task in recall_tasks():
        response = llm_call(agent_file_text, task.prompt)
        passed = _check_substring_any(response, task.acceptable_answers)
        suite.recall_results.append(
            TaskResult(
                task_id=task.task_id,
                pass_=passed,
                reason="recalled clause" if passed else "no acceptable clause recalled",
            )
        )

    return suite


# ─── deterministic fake LLM (Phase 2 scaffolding only) ────────────────────────

def make_fake_llm(mode: str = "perfect") -> LLMCall:
    """Build a deterministic fake LLM call for testing the runner.

    Modes:
    - "perfect": echoes the full agent file text — every recall/procedure/
      forbidden-action check passes (the agent file contains all the anchors
      we look for).
    - "blind": returns a fixed irrelevant string — every check fails.
    - "partial": echoes only the prompt — recall fails, but the prompt itself
      may contain some anchors so passes are mixed.
    """
    if mode == "perfect":

        def call(agent_file_text: str, prompt: str) -> str:
            return agent_file_text

        return call
    if mode == "blind":

        def call(agent_file_text: str, prompt: str) -> str:
            return "I don't know."

        return call
    if mode == "partial":

        def call(agent_file_text: str, prompt: str) -> str:
            return f"[restating the prompt] {prompt}"

        return call
    raise ValueError(f"unknown mode: {mode}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agent-file-compliance", description=__doc__)
    p.add_argument("--model", default="fake-perfect", help="model id (recorded only)")
    p.add_argument(
        "--agent-file",
        default="agents/shared/ENGINEERING_STANDARDS.md",
        help="path to agent file under test",
    )
    p.add_argument("--level", default="none", choices=["none", "mild", "medium", "aggressive"])
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="run with deterministic fake LLM (no inference)",
    )
    p.add_argument(
        "--fake-mode",
        default="perfect",
        choices=["perfect", "blind", "partial"],
        help="fake LLM mode for --dry-run",
    )
    p.add_argument("--json", action="store_true", help="emit full result as JSON")
    args = p.parse_args(argv)

    if not args.dry_run:
        print(
            "ERROR: live inference path is Phase 3 (inference-gated). "
            "Use --dry-run with --fake-mode for Phase 2 scaffolding tests.",
            file=sys.stderr,
        )
        return 2

    result = run_compliance_suite(
        model_id=args.model,
        agent_file_path=args.agent_file,
        level=args.level,
        llm_call=make_fake_llm(args.fake_mode),
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        d = result.to_dict()
        print(f"model: {d['model_id']}")
        print(f"agent_file: {d['agent_file_path']}")
        print(f"level: {d['level']}")
        print(f"token_count (~chars/4): {d['token_count']}")
        print(f"compliance_pass_rate: {d['compliance_pass_rate']}")
        print(f"procedure_pass_rate: {d['procedure_pass_rate']}")
        print(f"recall_pass_rate: {d['recall_pass_rate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
