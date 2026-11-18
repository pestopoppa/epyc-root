"""Attach a one-shot synthetic observation to the pinned graph's real REPL."""
import hashlib
import json
import sys
from pathlib import Path

from graph_trial import main as run_graph

RECORD_CODE = "print(take_record())"
CHECKPOINT_CODE = "print(checkpoint())"
BOUNDARY_TURN = 3
MAX_TURNS = 7


def record_output(case):
    return f"Archive record {case['label']}\nreceipt={case['needle']}\n" + " q7" * 1750 + "\n"


def checkpoint_output(case):
    return f"Checkpoint recorded for {case['label']}\n" + " z8" * 1750 + "\n"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    attempt = Path(sys.argv[1])
    config = json.loads((attempt / "INPUT.json").read_text())
    fixture = json.load(sys.stdin)
    sys.path.insert(0, config["source"])

    from src.repl_environment import environment
    from src.repl_environment.task_root import (
        begin_request_scope,
        clear_request_scope,
        request_scope,
    )

    needle = fixture["needle"]
    pending = [record_output(fixture)]
    checkpoint_text = checkpoint_output(fixture)
    del fixture
    task_root = attempt / "repl"
    task_root.mkdir()
    sealed = Path(config["source"]).parent
    private_paths = (sealed / "packet/cases.json", sealed / "prepared/cases.json",
                     attempt / "INPUT.json", Path("/proc/self/fd/0"))
    observed = []
    state = None
    emitted = 0

    def take_record():
        nonlocal emitted
        if not pending:
            return "Archive read already consumed."
        emitted += 1
        return pending.pop().removesuffix("\n")

    def checkpoint():
        return checkpoint_text.removesuffix("\n")

    class FixtureREPL(environment.REPLEnvironment):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._globals.update(take_record=take_record, checkpoint=checkpoint)
            self._builtin_global_keys = frozenset(self._globals)
            observed.append({"kind": "scope", "scope": request_scope().snapshot(),
                             "denied": [str(path) for path in private_paths
                                        if not self._validate_file_path(str(path))[0]]})

        def _read_registered_artifact(self, path, n, offset):
            result = super()._read_registered_artifact(path, n, offset)
            observed.append({"kind": "registered_read", "turn": state.turns, "path": str(path),
                             "needle_returned": needle in result})
            return result

        def execute(self, code):
            if state.turns == BOUNDARY_TURN:
                tail = state.history_turns[state.history_tail_start:]
                observed.append({"kind": "tail", "boundaries": list(state.history_boundaries),
                                 "turns": [turn["turn"] for turn in tail],
                                 "has_needle": any(needle in repr(turn) for turn in tail),
                                 "scope": request_scope().snapshot()})
            result = super().execute(code)
            output = result.output or ""
            observed.append({
                "kind": "execute", "turn": state.turns, "code": code, "output_sha256": sha(output),
                "output_chars": len(output), "needle_occurrences": output.count(needle),
                "emitted": emitted, "record_available": bool(pending),
                "user_globals": sorted(self._globals.keys() - self._builtin_global_keys),
                "repl_context_has_needle": needle in str(self._globals["context"]),
                "state_context_has_needle": needle in state.context or needle in state.prompt,
                "repl_artifacts_have_needle": needle in repr(self.artifacts),
                "error": result.error, "is_final": result.is_final, "final_answer": result.final_answer,
            })
            return result

    def configure_state(graph_state, _config, _attempt):
        nonlocal state
        state = graph_state
        state.max_turns = MAX_TURNS

    environment.REPLEnvironment = FixtureREPL
    try:
        begin_request_scope(str(task_root), edit_mode="none")
        run_graph(configure_state=configure_state)
    finally:
        clear_request_scope()
        (attempt / "FIXTURE-AUDIT.json").write_text(json.dumps(observed, indent=2) + "\n")


if __name__ == "__main__":
    main()
