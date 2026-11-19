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
import os
import sys
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from tests.compliance.agent_file.forbidden_actions import all_tasks as forbidden_tasks
from tests.compliance.agent_file.instruction_recall import all_tasks as recall_tasks
from tests.compliance.agent_file.procedure_correctness import all_tasks as procedure_tasks


FORCED_MARKUP = "forced_markup"  # v3b tool_verdict (equals live_runner.FORCED_MARKUP)

LLMCall = Callable[[str, str], str]
"""(agent_file_text, prompt) -> model response text."""

SUITE_VERSION = "agent_file_compliance_v2_20260730"
"""Instrument version. v2 (2026-07-30, AFC-P5.E1/E2): registry-format tasks
removed (content moved to the research repo), pools expanded to 30/30/30
against the post-restructure ENGINEERING_STANDARDS. Results are comparable
only within a suite version."""


@dataclass
class TaskResult:
    task_id: str
    pass_: bool
    reason: str = ""
    raw_response: str = ""
    error: str = ""      # non-empty = no usable reply (timeout / HTTP error / empty content); distinct from a miss
    attempts: int = 1
    tool_calls: list = field(default_factory=list)  # r6: [{"name","arguments"}] the model emitted (offered-tools suite)
    tool_rounds: int = 0  # r8: tool rounds executed (stub results returned) before the final reply
    cap_hit: bool = False  # r8: 3 tool rounds used, final answer was forced with tool_choice none
    tool_verdict: str = ""  # r6: "" (no tool call) | "ok_with_answer" | "tool_only" | "invalid_tool_call" | v3b "forced_markup"


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
    def blank_count(self) -> int:
        allr = self.forbidden_action_results + self.procedure_results + self.recall_results
        return sum(1 for r in allr if r.error)

    @property
    def inconclusive(self) -> bool:
        """r2 rule: any blank reply after retry => the cell is INCONCLUSIVE, not scored."""
        return self.blank_count > 0

    @staticmethod
    def _rate(results: list) -> float:
        """v3b: forced_markup tasks are INCONCLUSIVE-markup, neither pass nor fail: excluded from the denominator."""
        scored = [r for r in results if r.tool_verdict != FORCED_MARKUP]
        return sum(r.pass_ for r in scored) / len(scored) if scored else 0.0

    @property
    def forced_markup_count(self) -> int:
        return sum(1 for r in self.forbidden_action_results + self.procedure_results + self.recall_results
                   if r.tool_verdict == FORCED_MARKUP)

    @property
    def compliance_pass_rate(self) -> float:
        return self._rate(self.forbidden_action_results)

    @property
    def procedure_pass_rate(self) -> float:
        return self._rate(self.procedure_results)

    @property
    def recall_pass_rate(self) -> float:
        return self._rate(self.recall_results)

    def tool_call_counts(self) -> dict:
        """r6: per-pool and total tool-call accounting (all zeros when no tools were offered)."""
        pools = {"compliance": self.forbidden_action_results, "procedure": self.procedure_results, "recall": self.recall_results}
        out: dict = {}
        for name, rs in pools.items():
            out[name] = {
                "tasks_with_tool_calls": sum(1 for r in rs if r.tool_calls),
                "tool_calls": sum(len(r.tool_calls) for r in rs),
                "tool_rounds": sum(r.tool_rounds for r in rs),
                "tasks_hitting_cap": sum(1 for r in rs if r.cap_hit),
                "tool_only_replies": sum(1 for r in rs if r.tool_verdict == "tool_only"),
                "invalid_tool_calls": sum(1 for r in rs if r.tool_verdict == "invalid_tool_call"),
                "forced_markup": sum(1 for r in rs if r.tool_verdict == FORCED_MARKUP),
            }
        out["total"] = {k: sum(out[n][k] for n in pools) for k in out["compliance"]}
        return out

    def to_dict(self) -> dict:
        return {
            "suite_version": SUITE_VERSION,
            "tool_call_counts": self.tool_call_counts(),
            "model_id": self.model_id,
            "agent_file_path": self.agent_file_path,
            "level": self.level,
            "token_count": self.token_count,
            "status": "INCONCLUSIVE" if self.inconclusive else "SCORED",
            "blank_count": self.blank_count,
            "forced_markup_count": self.forced_markup_count,
            "compliance_pass_rate": None if self.inconclusive else round(self.compliance_pass_rate, 4),
            "procedure_pass_rate": None if self.inconclusive else round(self.procedure_pass_rate, 4),
            "recall_pass_rate": None if self.inconclusive else round(self.recall_pass_rate, 4),
            "raw_rates_if_blanks_counted_as_fail": {
                "compliance": round(self.compliance_pass_rate, 4),
                "procedure": round(self.procedure_pass_rate, 4),
                "recall": round(self.recall_pass_rate, 4)},
            "forbidden_action_results": [asdict(r) for r in self.forbidden_action_results],
            "procedure_results": [asdict(r) for r in self.procedure_results],
            "recall_results": [asdict(r) for r in self.recall_results],
        }


def _check_substring_any(response: str, anchors: Iterable[str]) -> bool:
    """True iff at least one anchor substring (case-insensitive) is in response."""
    rl = response.lower()
    return any(a.lower() in rl for a in anchors)


def _check_ordered_anchors(response: str, anchors: list) -> bool:
    """True iff all anchor groups match in order (case-insensitive).

    `anchors` is a list of "groups", where each group is either:
      - a `str` (single substring; legacy format), OR
      - a `list[str]` (synonym group; ANY substring in the list satisfies
        this group).

    For each group N, at least one synonym must appear at position >= cursor,
    and cursor advances past the matched substring before checking group N+1.

    v2 (2026-05-07): synonym groups added per Phase 3 first-pass finding that
    strict single-substring matching produced a 0.417 floor — many models'
    natural prose used synonyms (e.g. "feature flag" vs the literal anchor
    "feature-flag") that the strict matcher rejected.
    """
    rl = response.lower()
    cursor = 0
    for group in anchors:
        # Normalize: bare str → one-element list (legacy compat).
        synonyms = [group] if isinstance(group, str) else list(group)
        # Find earliest match of any synonym at/after cursor.
        best_idx = -1
        best_match_len = 0
        for syn in synonyms:
            sl = syn.lower()
            idx = rl.find(sl, cursor)
            if idx >= 0 and (best_idx < 0 or idx < best_idx):
                best_idx = idx
                best_match_len = len(sl)
        if best_idx < 0:
            return False
        cursor = best_idx + best_match_len
    return True


def _approx_token_count(text: str) -> int:
    """Rough ~4-chars-per-token proxy. Replace with model-specific tokenizer
    in Phase 3."""
    return max(1, len(text) // 4)


def load_partial(path: Path | str) -> dict:
    """Load `<output>.partial.jsonl` -> {(pool, task_id): TaskResult}. Last record per key wins; records with a
    non-empty `error` (blank replies) are NOT loaded so they are retried; torn/garbled lines are skipped."""
    out: dict = {}
    p = Path(path)
    if not p.exists():
        return out
    fields = set(TaskResult.__dataclass_fields__)
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
            key = (d["pool"], d["task_id"])
            r = TaskResult(**{k: v for k, v in d.items() if k in fields})
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        if r.error:
            out.pop(key, None)  # a later blank supersedes an earlier good record only if it is the last word
        else:
            out[key] = r
    return out


def append_partial(path: Path | str, pool: str, res: TaskResult, lock: threading.Lock) -> None:
    """Append one finished task as one JSON line, flushed + fsynced before returning (thread-safe)."""
    line = json.dumps({"pool": pool, **asdict(res)}, default=str) + "\n"
    with lock:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a+b") as fb:  # a torn trailing line (killed mid-write) must not glue onto our record
            fb.seek(0, os.SEEK_END)
            if fb.tell():
                fb.seek(-1, os.SEEK_END)
                if fb.read(1) != b"\n":
                    fb.write(b"\n")
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())


def run_compliance_suite(
    model_id: str,
    agent_file_path: Path | str,
    level: str,
    llm_call: LLMCall,
    concurrency: int = 1,
    partial_path: Path | str | None = None,
) -> SuiteResult:
    """Run all three task pools against `model_id` reading `agent_file_path`.

    `llm_call(agent_file_text, prompt) -> str` is injected; in Phase 2 this
    is `make_fake_llm(...)`. In Phase 3 it routes to the live model.

    `concurrency` > 1 dispatches task prompts through a thread pool (the
    llm_call must be thread-safe — the live HTTP call is; pair with a server
    started with `-np >= concurrency`). Result ORDER is preserved regardless
    of completion order, so scoring and artifacts are deterministic given
    deterministic responses. Scoring itself is unchanged.
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

    detailed = getattr(llm_call, "detailed", None)

    # Resumability: each finished task is appended (fsynced) to `partial_path`; a rerun skips recorded tasks except
    # blanks/errors, which are retried. Final result is built from recorded + new TaskResults in pool order.
    recorded = load_partial(partial_path) if partial_path else {}
    lock = threading.Lock()
    pools = (("forbidden", forbidden_tasks()), ("procedure", procedure_tasks()), ("recall", recall_tasks()))
    total = sum(len(ts) for _, ts in pools)
    done = [0]

    def progress(task_id: str, how: str) -> None:
        with lock:
            done[0] += 1
            print(f"[afc] {done[0]}/{total} {task_id} ({how})", file=sys.stderr, flush=True)

    def one(t) -> dict:
        if detailed is not None:
            return detailed(agent_file_text, t.prompt)
        return {"text": llm_call(agent_file_text, t.prompt), "error": "", "attempts": 1}

    def mk(task, rr: dict, passed: bool, ok_reason: str, bad_reason: str) -> TaskResult:
        err = rr.get("error", "")
        calls = rr.get("tool_calls") or []
        verdict = rr.get("tool_verdict", "")
        # r6 scoring: a reply that is (or contains) an invalid tool call fails; a tool-call-only reply replaces the
        # plain answer every task requires, so it fails; a valid tool call alongside a plain answer is scored on the
        # plain-answer text by the unchanged scorers (tool-call arguments are never searched for anchors).
        if not err and verdict == "invalid_tool_call":
            passed, bad_reason = False, "invalid tool call (unknown tool, bad arguments or unparsed tool-call text)"
        elif not err and verdict == FORCED_MARKUP:
            passed, bad_reason = False, "INCONCLUSIVE-markup: forced final reply still carried tool-call markup after retry"
        elif not err and verdict == "tool_only":
            passed, bad_reason = False, "tool call replaced the required plain answer"
        return TaskResult(task_id=task.task_id, pass_=(passed and not err),
                          reason=("NO REPLY: " + err) if err else (ok_reason if passed else bad_reason),
                          raw_response=rr.get("text", ""), error=err, attempts=rr.get("attempts", 1),
                          tool_calls=calls, tool_verdict=verdict,
                          tool_rounds=rr.get("tool_rounds", 0), cap_hit=bool(rr.get("cap_hit", False)))

    def run_pool(pool: str, tasks: list, check, ok_reason: str, bad_reason: str) -> list[TaskResult]:
        def work(task) -> TaskResult:
            prior = recorded.get((pool, task.task_id))
            if prior is not None:
                progress(task.task_id, "resumed")
                return prior
            rr = one(task)
            res = mk(task, rr, check(task, rr["text"]), ok_reason, bad_reason)
            if partial_path:
                append_partial(partial_path, pool, res, lock)
            progress(task.task_id, "blank" if res.error else "done")
            return res

        if concurrency <= 1:
            return [work(t) for t in tasks]
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            return list(ex.map(work, tasks))  # ex.map preserves task order

    # Forbidden-action tasks: pass if response contains any expected clause substring.
    suite.forbidden_action_results = run_pool("forbidden", pools[0][1], lambda t, x: _check_substring_any(x, t.expected_clause_substrings),
                                              "cited expected clause", "no expected clause cited")
    # Procedure tasks: ordered-anchor check.
    suite.procedure_results = run_pool("procedure", pools[1][1], lambda t, x: _check_ordered_anchors(x, t.ordered_step_anchors),
                                       "all anchors in order", "missing or out-of-order anchor")
    # Recall tasks: any acceptable-answer substring.
    suite.recall_results = run_pool("recall", pools[2][1], lambda t, x: _check_substring_any(x, t.acceptable_answers),
                                    "recalled clause", "no acceptable clause recalled")

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
