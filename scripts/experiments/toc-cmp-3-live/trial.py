"""Configure the pinned CMP-3 contract on the shared real REPL trial."""
import json
import sys
from pathlib import Path

from graph_trial import main


def configure_state(state, config, attempt):
    from src.graph.compaction_artifacts import ExecutionBrief, PinnedGovernance, render_contract, set_contract

    case = config["case"]
    brief = ExecutionBrief(
        verbatim_task=case["prompt"],
        current_intent="Recover the exact ticket value from the source record.",
        plan="Read the source, emit the receipt, then return the ticket.",
        completion_requirements="Return only the recovered ticket value in FINAL.",
        artifacts="Synthetic ticket record in the existing REPL context.",
        pointers="The last line of context holds the original record.",
    )
    governance = PinnedGovernance(case["governance"])
    # The same expected byte sequence lets the control prove its absence.
    (attempt / "EXPECTED-CONTRACT.txt").write_bytes(render_contract(brief, governance).encode("utf-8"))
    if config["row"]["contract"]:
        set_contract(state, brief, governance)
    # The graph adds an immediate FINAL instruction with three turns remaining.
    # Leave the forced boundary turn outside that range.
    state.max_turns = 7


if __name__ == "__main__":
    config = json.loads((Path(sys.argv[1]) / "INPUT.json").read_text())
    main(feature_overrides={"context_compaction_contract": config["row"]["contract"]},
         configure_state=configure_state)
