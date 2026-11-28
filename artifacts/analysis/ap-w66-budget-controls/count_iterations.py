#!/usr/bin/env python3
"""Audit C22's native prompt iteration log for one ON28/OFF56 collision."""

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean


LAUNCH = re.compile(r"launch_slot_: id\s+(\d+) \| task (\d+) \| processing task")
RELEASE = re.compile(r"release: id\s+(\d+) \| task (\d+) \| stop processing")
ITER = re.compile(
    r"prefill-budget: iter (\d+): decode_rows = (\d+) \(slots (\d+)\), "
    r"prompt = (\d+) \(slots (\d+)\), budget = (\d+), t_iter = ([\d.]+) ms, "
    r"kv_pos = (\d+), ms/tok = ([\d.]+)"
)


@dataclass
class Iteration:
    number: int
    decode_rows: int
    generating_slots: int
    prompt_rows: int
    prefilling_slots: int
    budget: int
    ms: float
    kv_positions: int
    ms_per_token_after: float

    @classmethod
    def parse(cls, match):
        number, decode, generators, prompt, prefills, budget, ms, kv, ms_per_token = match.groups()
        return cls(
            int(number), int(decode), int(generators), int(prompt), int(prefills),
            int(budget), float(ms), int(kv), float(ms_per_token),
        )


def collect(lines, first_task, peer_task):
    first = (1, first_task)
    peer = (2, peer_task)
    launched = set()
    released = set()
    before_peer = []
    during_peer = []
    prior_prompt_rows = 0
    for line in lines:
        launch = LAUNCH.search(line)
        if launch:
            task = tuple(map(int, launch.groups()))
            if task in (first, peer) and task not in launched:
                launched.add(task)
            elif first in launched:
                raise ValueError(f"unexpected task after ON28 launch: {task}")
        release = RELEASE.search(line)
        if release:
            task = tuple(map(int, release.groups()))
            if task in launched:
                released.add(task)
        match = ITER.search(line)
        if match:
            row = Iteration.parse(match)
            if first not in launched:
                prior_prompt_rows += row.prompt_rows
            elif peer not in launched:
                before_peer.append(row)
            else:
                during_peer.append(row)
        if released == {first, peer}:
            break
    if launched != released or launched != {first, peer}:
        raise ValueError("missing a launch or stop-processing marker for ON28/OFF56")
    return prior_prompt_rows, before_peer, during_peer


def summarize(prior_rows, before_peer, during_peer, arm, historical=False):
    if sum(row.prompt_rows for row in before_peer) != 38:
        raise ValueError("native log does not account for all 38 ON28 fresh prompt rows")
    if sum(row.prompt_rows for row in during_peer) != 107912:
        raise ValueError("native log does not account for all 107912 OFF56 fresh prompt rows")
    if any(row.decode_rows != 0 or row.budget != 0 for row in before_peer):
        raise ValueError("unexpected decode or budget during ON28 initial prefill")
    if not historical and (prior_rows or any(row.ms_per_token_after != 0 for row in before_peer)):
        raise ValueError("fresh-arm replay has prompt work or a seeded estimator before OFF56")
    numbers = [row.number for row in before_peer + during_peer]
    if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        raise ValueError("missing, duplicate or reordered native iterations")
    mixed = [row for row in during_peer if row.decode_rows > 0]
    if not mixed or during_peer[0] != mixed[0]:
        raise ValueError("OFF56 did not begin prefill while ON28 was decoding")
    for row in before_peer + during_peer:
        if row.prefilling_slots != 1 or row.generating_slots != int(row.decode_rows > 0):
            raise ValueError(f"unexpected native slot occupancy at iteration {row.number}")
        if row.prompt_rows + row.decode_rows > 2048:
            raise ValueError(f"native iteration {row.number} exceeds the recorded n_batch")
        if arm == "budget" and row.decode_rows > 0:
            if not 64 <= row.budget <= 256 or row.prompt_rows > row.budget:
                raise ValueError(f"budget bound violated at mixed iteration {row.number}")
        elif row.budget != 0:
            raise ValueError(f"unexpected nonzero budget at iteration {row.number}")
    if arm == "budget" and mixed[0].budget != 256:
        raise ValueError("first mixed budget differs from the fresh stock cap")
    if arm == "control" and max(row.prompt_rows for row in mixed) <= 256:
        raise ValueError("control never processed more than 256 mixed prompt rows")
    durations = sorted(row.ms for row in mixed)
    mixed_prompt_rows = sum(row.prompt_rows for row in mixed)
    return {
        "arm": arm,
        "historical": historical,
        "prior_process_prompt_rows": prior_rows,
        "seed_before_first_mixed": before_peer[-1].ms_per_token_after,
        "first_mixed": asdict(mixed[0]),
        "last_mixed": asdict(mixed[-1]),
        "worst_mixed": asdict(max(mixed, key=lambda row: row.ms)),
        "mixed_iterations": len(mixed),
        "mixed_prompt_rows": mixed_prompt_rows,
        "off56_nonmixed_prompt_rows": 107912 - mixed_prompt_rows,
        "mixed_prompt_budget_values": sorted({row.budget for row in mixed}),
        "mixed_iterations_above_900_ms": sum(row.ms > 900 for row in mixed),
        "mixed_ms": {
            "mean": mean(durations),
            "p50": durations[round(.50 * (len(durations) - 1))],
            "p99_prior_27b_method": durations[round(.99 * (len(durations) - 1))],
            "p99_nearest_rank": durations[math.ceil(.99 * len(durations)) - 1],
            "worst": durations[-1],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--on28-task", type=int, required=True)
    parser.add_argument("--off56-task", type=int, required=True)
    parser.add_argument("--arm", choices=("control", "budget"), required=True)
    parser.add_argument(
        "--historical", action="store_true",
        help="allow the seeded estimator and prior warmups from the archived control replay",
    )
    args = parser.parse_args()
    if args.historical and args.arm != "control":
        parser.error("--historical applies to the archived control only")
    try:
        with args.log.open(errors="replace") as lines:
            result = collect(lines, args.on28_task, args.off56_task)
        report = summarize(*result, args.arm, args.historical)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
