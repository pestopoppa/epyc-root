"""Prospective scripted-archive cohort for native graph continuation diagnostics.

No model calls, source-pool replacements, or measured outcomes enter this compiler.
The archive is task input, not a claim that the model executed its ten turns.
"""

import argparse
import hashlib
import json
from pathlib import Path

VERSION = "epyc.cf3c.binding-cohort.v1"
SEED = "cf3c-binding-20261119-v1"
ARMS = ("A0", "A1-k4", "A1-k8", "A1-k12", "A2", "A3")
KINDS = ("head", "deep", "paired", "revision")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def value_for(kind, index):
    return hashlib.sha256(f"{SEED}/{kind}/{index}".encode()).hexdigest()[:16]


def compile_cohort():
    cases, inventory, schedule = [], [], []
    for kind in KINDS:
        task_id = f"binding_{kind}_v1"
        archive = []
        for index in range(1, 11):
            key = (
                "release"
                if kind == "revision" and index in {3, 6}
                else f"receipt-{index}"
            )
            receipt = f"{key}={value_for(kind, index)}"
            padding = (
                "Archive audit: checksum verified; transport complete; no action requested. "
                * 6
            )
            output = (
                receipt + "\n" + padding if kind == "head" else padding + "\n" + receipt
            )
            archive.append({"code": f"read_receipt({index})", "output": output})
        if kind == "paired":
            query = (
                "Return receipt-4 and receipt-6, in that order, joined by one colon."
            )
            expected = f"{value_for(kind, 4)}:{value_for(kind, 6)}"
        elif kind == "revision":
            query = "Return the latest recorded value of release (later archive entries supersede earlier entries)."
            expected = value_for(kind, 6)
        else:
            query = "Return the recorded value of receipt-4."
            expected = value_for(kind, 4)
        cases.append(
            {
                "id": task_id,
                "suite": "cf3c_scripted_binding_continuation",
                "prompt": (
                    "Continue the audit from the supplied scripted archive. "
                    "The archive is an input fixture, not actions you executed. "
                    "You may recover exact text from the registered full log using peek(). "
                    + query
                    + " Return only the requested value, with no explanation."
                ),
                "initial_history": archive,
                "expected": expected,
                "scoring_method": "exact_match",
            }
        )
        inventory.append(
            {
                "id": task_id,
                "suite": cases[-1]["suite"],
                "scoring_method": "exact_match",
                "scheduled": True,
                "grade_cohort": True,
                "grade_reason": None,
            }
        )
        pair = f"{task_id}/r0"
        seed = int(digest([SEED, pair])[:8], 16) & 0x7FFFFFFF
        for arm in sorted(ARMS, key=lambda a: digest([SEED, pair, a])):
            schedule.append(
                {
                    "unit": f"{pair}/{arm}",
                    "ordinal": len(schedule),
                    "case": task_id,
                    "arm": arm,
                    "seed": seed,
                    "pair": pair,
                    "repeat": 0,
                }
            )
    payload = {
        "schema": VERSION,
        "seed": SEED,
        "cases": cases,
        "inventory": inventory,
        "schedule": schedule,
        "scripted_archive": True,
        "archive_construction_cost_included": False,
        "adoption_margin_resolved": False,
        "automatic_extension": False,
    }
    return {**payload, "cohort_sha256": digest(payload)}


def validate_archive(archive):
    if not isinstance(archive, list) or len(archive) != 10:
        raise ValueError("binding archive requires exactly ten scripted observations")
    for entry in archive:
        if not isinstance(entry, dict) or set(entry) != {"code", "output"}:
            raise ValueError(
                "archive may contain only code and output, never a grading oracle"
            )
        if any(not isinstance(value, str) or not value for value in entry.values()):
            raise ValueError("archive code and output must be nonempty text")
        if len(entry["code"]) > 256 or not 180 < len(entry["output"]) <= 1200:
            raise ValueError("archive exceeds the registered render geometry")


def install_archive(state, repl, archive):
    """Persist scripted inputs with the source writer and its real peek offsets."""
    from src.graph.context_arm_ab import record_turn
    from src.graph.session_summary import _init_session_log

    validate_archive(archive)
    if state.history_turns or state.history_log_path or state.history_log_chars:
        raise ValueError("binding archive cannot replace existing native task history")
    _init_session_log(state, repl=repl)
    path = Path(state.session_log_path).with_name("session.verbatim.md")
    if path.exists():
        raise ValueError("binding archive cannot overwrite an existing verbatim log")
    current_turn = state.turns
    try:
        for number, entry in enumerate(archive, start=-len(archive)):
            state.turns = number
            record_turn(
                state,
                role="frontdoor",
                code=entry["code"],
                output=entry["output"],
                error=None,
            )
    finally:
        state.turns = current_turn
    if len(state.history_turns) != len(archive) or not path.is_file():
        raise ValueError("source writer did not retain the complete binding archive")
    state.context += (
        "\n\nScripted archive full log: peek("
        f"{state.history_log_chars}, file_path={json.dumps(str(path))}, offset=0)"
    )
    return {
        "scripted": True,
        "observations": len(archive),
        "archive_sha256": digest(archive),
        "verbatim_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "construction_cost_included": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.output.open("x") as stream:
        stream.write(json.dumps(compile_cohort(), indent=2, sort_keys=True) + "\n")
