"""Accept-batch design and run arithmetic for the rigor-enforced Life-Harness run.

The shipped Life round evaluates the incumbent AND the candidate on the SAME 50-task TRAIN
batch whose traces fed the proposer, so its accept step cannot satisfy R1. We keep the six
shipped proposal batches (P_n) untouched and add six accept batches (A_n) drawn from the
unused remainder of the TRAIN pool, disjoint from every P and from each other.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Mapping, Sequence

from .rigor import qualify

ROUNDS = 6
BATCH = 50


def plan_accept_batches(train_pool: int, proposal_batches: Sequence[Sequence[int]], *,
                        accept_size: int = BATCH, rounds: int = ROUNDS, seed: int = 20261123) -> list[list[int]]:
    """Deterministic accept batches disjoint from all proposal batches and from each other."""
    used = {int(i) for b in proposal_batches for i in b}
    if len(used) != sum(len(b) for b in proposal_batches):
        raise ValueError("proposal batches overlap each other")
    remaining = [i for i in range(train_pool) if i not in used]
    if len(remaining) < accept_size * rounds:
        raise ValueError(f"train pool too small: {len(remaining)} unused < {accept_size * rounds} needed")
    rng = random.Random(seed)
    rng.shuffle(remaining)
    return [sorted(remaining[n * accept_size:(n + 1) * accept_size]) for n in range(rounds)]


def check_games_disjoint(train_games: Mapping[str, Sequence[str]], test_games: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """R3 at game-file level: TRAIN pool and sealed TEST share no game file."""
    tr = {f for v in train_games.values() for f in v}
    te = {f for v in test_games.values() for f in v}
    both = sorted(tr & te)
    return {"train_games": len(tr), "test_games": len(te), "overlap": len(both), "ok": not both, "sample": both[:5]}


def check_games_disjoint_files(data_dir: Path, train_file: str = "train_valid.json", test_file: str = "new_std.json") -> dict[str, Any]:
    return check_games_disjoint(json.loads((data_dir / train_file).read_text()),
                                json.loads((data_dir / test_file).read_text()))


def validate_plan(*, proposal_batches: Sequence[Sequence[int]], accept_batches: Sequence[Sequence[int]],
                  test_ids: Sequence[int], train_split: str, test_split: str) -> dict[str, Any]:
    """Structural proof of R1 (+ the id-side of R3) for the whole plan; raises on any overlap."""
    if train_split == test_split:
        raise ValueError("R3: train and test split names must differ")
    p = [{qualify(train_split, i) for i in b} for b in proposal_batches]
    a = [{qualify(train_split, i) for i in b} for b in accept_batches]
    t = {qualify(test_split, i) for i in test_ids}
    allp, alla = set().union(*p), set().union(*a)
    problems = []
    if allp & alla:
        problems.append(f"R1: {len(allp & alla)} ids shared between proposal and accept batches")
    if sum(map(len, a)) != len(alla):
        problems.append("R1: accept batches overlap each other")
    if sum(map(len, p)) != len(allp):
        problems.append("R1: proposal batches overlap each other")
    if t & (allp | alla):
        problems.append("R3: sealed test ids appear in a search-side batch")
    if problems:
        raise ValueError("; ".join(problems))
    return {"proposal_ids": len(allp), "accept_ids": len(alla), "test_ids": len(t),
            "r1_disjoint": True, "r3_test_disjoint": True}


def rollout_plan(*, rounds: int = ROUNDS, proposal_n: int = BATCH, accept_n: int = BATCH,
                 test_n: int = 109, smoke_n: int = 1) -> dict[str, Any]:
    """Solver-episode arithmetic: the extra accept pair is the price of R1 + R2."""
    per_round = proposal_n + 2 * accept_n
    return {"per_round": {"incumbent_on_proposal_batch": proposal_n,
                          "accept_parent_fresh": accept_n, "accept_candidate": accept_n, "total": per_round},
            "train": rounds * per_round, "test": test_n, "smoke": smoke_n,
            "total": rounds * per_round + test_n + smoke_n,
            "shipped_total": rounds * 2 * proposal_n + test_n + smoke_n,
            "note": "retries of infra_error rows (R4) are extra, bounded by the budget limit"}


def digest_files(paths: Sequence[Path]) -> dict[str, str]:
    return {str(p): hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
