"""AP-BSV2-ACCEPT-RIGOR rules R1-R5 for the Life-Harness accept step.

Pure and dependency-free. Rules (canonical text: handoffs/active/autopilot-program.md,
box AP-BSV2-ACCEPT-RIGOR "RESULT"):

* R1 disjoint accept tasks: the accept batch shares no qualified id with any batch the
  proposer saw traces from, nor with any earlier accept batch. Fail closed when the
  proposal-side id set is unknown.
* R2 fresh parent re-run: the parent arm is evaluated in this round, on the accept batch,
  in the same window as the candidate; a cached parent outcome is never a baseline.
* R3 sealed test split: test ids never appear in any search-side eval; the headline
  checkpoint is chosen by a training-side rule, never best-on-test.
* R4 per-round decision record: status split (completed / solver_limit / infra_error /
  candidate_error; retry for infra_error only) and tokens per accepted gain (None, not
  zero, when nothing is accepted).
* R5 budget unit: rollouts or tokens, never iterations / trials / wall-clock; the unit is
  stored in the R4 record.

Ids are SPLIT-QUALIFIED strings (``train_valid:17``, ``new_std:17``) because the native
benchmark indexes each split separately: index 17 of TRAIN and index 17 of TEST are
different games, and a bare integer comparison would be wrong in both directions.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

STATUSES = ("completed", "solver_limit", "infra_error", "candidate_error")
BUDGET_UNITS = ("rollouts", "tokens")
# AgentBench SampleStatus values (AgentBench/src/typings/status.py) plus the two
# synthetic statuses the Life runtime emits.
_COMPLETED = {"completed"}
_SOLVER_LIMIT = {"agent context limit", "task limit reached", "context_limit"}
# Rules whose violation is a harness/setup defect: stop the run, never silently reject.
HARD_RULES = ("R1", "R2", "R3", "R5")


class RigorViolation(RuntimeError):
    """A hard rule (R1/R2/R3/R5) failed; the run must stop and name the rule."""

    def __init__(self, rule: str, detail: str):
        self.rule = rule
        self.detail = detail
        super().__init__(f"{rule}: {detail}")


def qualify(split_name: str, index: Any) -> str:
    return f"{split_name}:{index}"


def row_status(row: Mapping[str, Any]) -> str:
    """Map one native episode row to the four-way R4 split."""
    if row.get("infrastructure_error") or row.get("infra"):
        return "infra_error"
    raw = str(row.get("status") or "").strip().lower()
    if raw in _COMPLETED:
        return "completed"
    if raw in _SOLVER_LIMIT:
        return "solver_limit"
    return "candidate_error"


def status_split(rows: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    split = {s: 0 for s in STATUSES}
    for r in rows:
        split[row_status(r)] += 1
    return split


def retry_allowed(status: str) -> bool:
    """R4: only infra errors may be retried."""
    return status == "infra_error"


def tokens_per_accepted_gain(tokens: int | float, gain: int | float, accepted: bool) -> float | None:
    """Tokens per additional success. Undefined (None), never zero, unless accepted with gain > 0."""
    if not accepted or gain <= 0:
        return None
    return float(tokens) / float(gain)


def mcnemar_exact_p(parent_wins: int, candidate_wins: int) -> float:
    """Two-sided exact McNemar on discordant pairs (candidate-only vs parent-only successes)."""
    n = parent_wins + candidate_wins
    if n == 0:
        return 1.0
    k = min(parent_wins, candidate_wins)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


class Budget:
    """R5: a budget in rollouts or tokens only."""

    def __init__(self, unit: str, limit: float | None, spent: float = 0.0):
        if unit not in BUDGET_UNITS:
            raise ValueError(f"R5 budget unit must be one of {BUDGET_UNITS}, got {unit!r}")
        if limit is not None and limit <= 0:
            raise ValueError("R5 budget limit must be positive")
        self.unit, self.limit, self.spent = unit, limit, float(spent)

    def cost(self, rollouts: int = 0, tokens: int | float = 0) -> float:
        return float(rollouts) if self.unit == "rollouts" else float(tokens)

    def would_exceed(self, rollouts: int = 0, tokens: int | float = 0) -> bool:
        return self.limit is not None and self.spent + self.cost(rollouts, tokens) > self.limit

    def check(self, rollouts: int = 0, tokens: int | float = 0, what: str = "") -> None:
        if self.would_exceed(rollouts, tokens):
            raise RigorViolation("R5", f"{what or 'step'} would exceed {self.unit} budget "
                                 f"({self.spent:g} + {self.cost(rollouts, tokens):g} > {self.limit:g})")

    def charge(self, rollouts: int = 0, tokens: int | float = 0) -> None:
        self.spent += self.cost(rollouts, tokens)

    def to_json(self) -> dict[str, Any]:
        return {"unit": self.unit, "limit": self.limit, "spent": self.spent}

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> "Budget":
        return cls(value["unit"], value.get("limit"), value.get("spent", 0.0))


def _by_id(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(r["id"]): r for r in rows}


def select_headline_checkpoint(checkpoints: Sequence[Mapping[str, Any]], key: str = "train_gain") -> Mapping[str, Any] | None:
    """R3: pick the headline checkpoint by a training-side key; test-side keys are refused."""
    low = key.lower()
    if "test" in low or "sealed" in low or "heldout" in low:
        raise ValueError(f"R3: headline key {key!r} is test-side; pick by a training-side rule")
    scored = [c for c in checkpoints if c.get(key) is not None]
    return max(scored, key=lambda c: c[key]) if scored else None


def decide_accept(
    *,
    round_no: int,
    proposal_ids: Iterable[str] | None,
    seen_ids: Iterable[str] | None,
    sealed_ids: Iterable[str],
    parent_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    parent_fresh: bool,
    budget: Budget,
    round_tokens: int | float,
    optimizer_tokens: int | float,
    min_gain: int = 1,
    max_p: float | None = None,
) -> dict[str, Any]:
    """Apply R1-R5 to one round and return its decision record (does not mutate anything).

    ``parent_rows`` / ``candidate_rows`` are the ACCEPT-batch rows (id, success, status,
    infra, tokens) AFTER infra-only retries. ``seen_ids`` is every id any earlier search
    step used (earlier proposal batches and earlier accept batches).
    """
    blockers: list[dict[str, str]] = []
    p, c = _by_id(parent_rows), _by_id(candidate_rows)
    accept_ids = sorted(set(p) | set(c))

    # R1
    if proposal_ids is None:
        r1 = {"ok": False, "reason": "proposal id set unknown (fail closed)"}
        blockers.append({"rule": "R1", "detail": r1["reason"]})
    else:
        seen = {str(x) for x in (seen_ids or [])} | {str(x) for x in proposal_ids}
        overlap = sorted(set(accept_ids) & seen)
        r1 = {"ok": not overlap, "overlap_n": len(overlap), "overlap": overlap[:20]}
        if overlap:
            blockers.append({"rule": "R1", "detail": f"{len(overlap)} accept ids already seen by the search"})
    if set(p) != set(c):
        blockers.append({"rule": "R2", "detail": "parent and candidate evaluated on different task sets"})

    # R2
    r2 = {"ok": bool(parent_fresh) and set(p) == set(c)}
    if not parent_fresh:
        blockers.append({"rule": "R2", "detail": "parent arm is not a fresh same-round re-run"})

    # R3
    sealed = {str(x) for x in sealed_ids}
    leak = sorted(sealed & set(accept_ids))
    r3 = {"ok": not leak, "sealed_in_accept_eval": leak[:20]}
    if leak:
        blockers.append({"rule": "R3", "detail": f"{len(leak)} sealed test ids appear in the accept eval"})

    # R4: infra rows make the round non-decisive; everything else is scored.
    split = {"parent": status_split(parent_rows), "candidate": status_split(candidate_rows)}
    infra = split["parent"]["infra_error"] + split["candidate"]["infra_error"]
    undecided = infra > 0

    # R5
    r5 = {"ok": True, "unit": budget.unit, "limit": budget.limit, "spent": budget.spent}
    if budget.limit is not None and budget.spent > budget.limit:
        r5["ok"] = False
        blockers.append({"rule": "R5", "detail": f"{budget.unit} budget exceeded ({budget.spent:g} > {budget.limit:g})"})

    ids = sorted(set(p) & set(c))
    ps = sum(int(p[i]["success"]) for i in ids)
    cs = sum(int(c[i]["success"]) for i in ids)
    cand_only = sum(1 for i in ids if c[i]["success"] and not p[i]["success"])
    par_only = sum(1 for i in ids if p[i]["success"] and not c[i]["success"])
    gain = cs - ps
    pval = mcnemar_exact_p(par_only, cand_only)

    hard = [b for b in blockers if b["rule"] in HARD_RULES]
    if hard:
        outcome, accept = "blocked_" + hard[0]["rule"], False
    elif undecided:
        outcome, accept = "undecided_infra_error", False
    elif gain < min_gain:
        outcome, accept = "rejected_no_gain", False
    elif max_p is not None and pval > max_p:
        outcome, accept = "rejected_not_significant", False
    else:
        outcome, accept = "accepted", True

    return {
        "round": round_no,
        "outcome": outcome,
        "accept": accept,
        "rules": {"R1": r1, "R2": r2, "R3": r3, "R4": {"ok": not undecided, "status_split": split}, "R5": r5},
        "blockers": blockers,
        "accept_n": len(ids),
        "parent_successes": ps,
        "candidate_successes": cs,
        "gain": gain,
        "candidate_only_wins": cand_only,
        "parent_only_wins": par_only,
        "mcnemar_exact_p": pval,
        "min_gain": min_gain,
        "max_p": max_p,
        "optimizer_tokens": optimizer_tokens,
        "round_tokens_total": round_tokens,
        "tokens_per_accepted_gain": tokens_per_accepted_gain(round_tokens, gain, accept),
        "tokens_per_accepted_gain_basis": "round_tokens_total / (candidate_successes - parent_successes)",
        "budget": budget.to_json(),
        "budget_unit": budget.unit,
    }
