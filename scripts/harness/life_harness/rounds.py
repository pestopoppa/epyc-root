"""One rigor-enforced evolve round, written against injected ports so it runs with fakes.

Shipped round (upstream ``Run.round``): incumbent eval on batch B -> propose from B's traces
-> candidate eval on the SAME B -> accept on one extra success. This round instead:

1. incumbent eval on the proposal batch P_n (its traces feed the proposer, as shipped);
2. propose;
3. FRESH parent eval and candidate eval on a DISJOINT accept batch A_n (R1, R2);
4. infra_error rows only are retried, up to ``max_infra_retries`` (R4);
5. ``rigor.decide_accept`` makes the decision and a per-round record is always written (R4);
6. a hard-rule failure (R1/R2/R3/R5) raises ``RigorViolation`` after the record is written.

Ports (duck-typed, see ``FakePorts`` in the tests):
  budget                          rigor.Budget
  active_manifest(name)           -> manifest handle for the current incumbent
  evaluate(name, manifest, ids)   -> {"rows": [...], "dir": str, "fresh": bool, "tokens": int}
                                     rows: {"id","index","success","status","infra","tokens"}
  propose(number, evidence)       -> {"bundle_path", "optimizer_tokens", "usage", "meta": {...}}
  stage(number, bundle_path)      -> (bundle, staged_manifest)
  commit(bundle)                  -> active snapshot sha256 after commit
  snapshot_sha()                  -> current active snapshot sha256
  write_decision(record)          -> persists the R4 record
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from . import rigor
from .rigor import Budget, RigorViolation, decide_accept, qualify, row_status


def _q(split: str, ids: Sequence[int]) -> list[str]:
    return [qualify(split, i) for i in ids]


def retry_infra(ports: Any, name: str, manifest: Any, result: Mapping[str, Any], *,
                max_retries: int, budget: Budget) -> tuple[list[dict], list[dict]]:
    """R4: re-run only infra_error rows; every other status is final. Returns (rows, attempts)."""
    rows = {r["id"]: dict(r) for r in result["rows"]}
    attempts: list[dict] = []
    for k in range(1, max_retries + 1):
        bad = [r for r in rows.values() if rigor.retry_allowed(row_status(r))]
        if not bad:
            break
        idx = sorted(int(r["index"]) for r in bad)
        budget.check(rollouts=len(idx), what=f"{name} retry {k}")
        res = ports.evaluate(f"{name}_retry{k}", manifest, idx)
        budget.charge(len(idx), res.get("tokens", 0))
        for r in res["rows"]:
            rows[r["id"]] = {**r, "retries": k}
        attempts.append({"attempt": k, "ids": idx,
                         "still_infra": sum(1 for r in res["rows"] if row_status(r) == "infra_error")})
    return list(rows.values()), attempts


def run_round(ports: Any, cfg: Mapping[str, Any], number: int) -> dict[str, Any]:
    """Run round ``number`` (1-based). ``cfg`` keys: proposal_batches, accept_batches (int index
    lists), train_split, test_split, test_ids, min_gain, max_p, max_infra_retries."""
    train_split = cfg["train_split"]
    P, A = cfg["proposal_batches"][number - 1], cfg["accept_batches"][number - 1]
    seen = set()
    for n in range(number - 1):
        seen |= set(_q(train_split, cfg["proposal_batches"][n])) | set(_q(train_split, cfg["accept_batches"][n]))
    sealed = _q(cfg["test_split"], cfg["test_ids"])
    budget: Budget = ports.budget

    # Whole-round precheck: refuse to START a round that cannot finish inside the budget (R5).
    budget.check(rollouts=len(P) + 2 * len(A), what=f"round {number}")

    tag = f"{number:02d}"
    manifest = ports.active_manifest(f"incumbent_{tag}")
    parent_sha = ports.snapshot_sha()
    inc = ports.evaluate(f"incumbent_{tag}", manifest, P)
    budget.charge(len(P), inc.get("tokens", 0))

    prop = ports.propose(number, inc)
    optimizer_tokens = int(prop.get("optimizer_tokens", 0))
    if budget.unit == "tokens":
        budget.charge(tokens=optimizer_tokens)
    bundle, staged = ports.stage(number, prop["bundle_path"])

    budget.check(rollouts=2 * len(A), what=f"round {number} accept evals")
    par = ports.evaluate(f"accept_parent_{tag}", manifest, A)
    budget.charge(len(A), par.get("tokens", 0))
    cand = ports.evaluate(f"accept_candidate_{tag}", staged, A)
    budget.charge(len(A), cand.get("tokens", 0))

    max_retries = int(cfg.get("max_infra_retries", 2))
    par_rows, par_retries = retry_infra(ports, f"accept_parent_{tag}", manifest, par,
                                        max_retries=max_retries, budget=budget)
    cand_rows, cand_retries = retry_infra(ports, f"accept_candidate_{tag}", staged, cand,
                                          max_retries=max_retries, budget=budget)

    round_tokens = (inc.get("tokens", 0) + par.get("tokens", 0) + cand.get("tokens", 0) + optimizer_tokens)
    decision = decide_accept(
        round_no=number, proposal_ids=_q(train_split, P), seen_ids=sorted(seen),
        sealed_ids=sealed, parent_rows=par_rows, candidate_rows=cand_rows,
        parent_fresh=bool(par.get("fresh")) and bool(cand.get("fresh")) and bool(inc.get("fresh")),
        budget=budget, round_tokens=round_tokens, optimizer_tokens=optimizer_tokens,
        min_gain=int(cfg.get("min_gain", 1)), max_p=cfg.get("max_p"))
    decision.update(
        proposal_eval=inc.get("dir"), accept_parent_eval=par.get("dir"), accept_candidate_eval=cand.get("dir"),
        parent_snapshot_sha256=parent_sha, infra_retries={"parent": par_retries, "candidate": cand_retries},
        proposal_batch_n=len(P), accept_batch_n=len(A), proposer=prop.get("meta", {}),
        headline_rule="final incumbent after the last TRAIN round; never selected on TEST")
    ports.write_decision(decision)

    hard = [b for b in decision["blockers"] if b["rule"] in rigor.HARD_RULES]
    if hard:
        raise RigorViolation(hard[0]["rule"], hard[0]["detail"] + f" (round {number}; see decision record)")

    active_sha = ports.commit(bundle) if decision["accept"] else parent_sha
    return {"round": number, "accepted": decision["accept"], "outcome": decision["outcome"],
            "active_snapshot_sha256": active_sha, "bundle": bundle, "decision": decision}
