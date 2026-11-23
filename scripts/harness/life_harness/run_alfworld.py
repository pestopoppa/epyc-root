"""Bind the rigor round to the upstream Life-Harness ALFWorld runner (the only upstream-importing module).

Nothing in the upstream clone is edited. ``prepare`` calls upstream ``initialize`` and then amends
``protocol.json`` (and re-hashes it into ``frozen_sources.json``) BEFORE any paid step; ``RigorRun``
subclasses upstream ``Run`` and replaces ``round`` with ``rounds.run_round``.

Upstream defects this layer works around (read from the clone at 4844bbb, nothing was run):
* ``initialize`` raises ``frozen unique TRAIN/TEST schedule mismatch`` for ALFWorld (8 numeric
  index collisions between TRAIN ``train_valid`` and TEST ``new_std``, which are different splits
  with disjoint game files), so a stock ``--domain alfworld`` run cannot even prepare. ``_initialize``
  is a copy of the body with the check made split-aware.
* ``Run.round`` indexes ``protocol["meta_reference"]`` / ``["ahe_reference"]``, which
  ``initialize`` never writes: a stock ``--run`` would crash with KeyError at the end of round 1,
  after ~100 solver episodes and the optimizer spend, before saving state. ``prepare`` writes
  placeholder lists so the keys exist; ``RigorRun.round`` does not use them.
* ``Broker`` defaults to a 600 s upstream read timeout; a non-streaming improver completion from a
  local architect model can take longer, so ``install_long_broker`` raises it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from . import plan as planlib
from . import rounds as roundlib
from .rigor import Budget, RigorViolation, qualify

GLUE_FILES = ("__init__.py", "rigor.py", "plan.py", "rounds.py", "proxy.py", "conformance.py", "run_alfworld.py", "cli.py")


def add_upstream_paths(lh_root: Path) -> None:
    for p in (str(lh_root), str(lh_root / "integrations/ahe-native")):
        if p not in sys.path:
            sys.path.insert(0, p)


def _read(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def design(lh_root: Path, *, accept_seed: int = 20261123, accept_size: int = planlib.BATCH) -> dict[str, Any]:
    """Pure, read-only: the proposal/accept/test design derived from the frozen manifest."""
    manifest = _read(lh_root / "evolution/reproduction/reference/manifest.json")
    spec = manifest["domains"]["alfworld"]
    P = [[int(i) for i in b.get("task_ids", b.get("indices", []))] for b in spec["batches"]]
    test = [int(i) for i in spec.get("test_task_ids", spec.get("test_indices", []))]
    A = planlib.plan_accept_batches(int(spec["train_pool"]), P, accept_size=accept_size, seed=accept_seed)
    proof = planlib.validate_plan(proposal_batches=P, accept_batches=A, test_ids=test,
                                  train_split=spec["train_split"], test_split=spec["test_split"])
    games = planlib.check_games_disjoint_files(lh_root / "AgentBench/data/alfworld",
                                              spec["train_split"] + ".json", spec["test_split"] + ".json")
    if not games["ok"]:
        raise ValueError("R3: train and test game files overlap: " + json.dumps(games))
    return {"proposal_batches": P, "accept_batches": A, "test_ids": test, "train_split": spec["train_split"],
            "test_split": spec["test_split"], "train_pool": spec["train_pool"], "accept_seed": accept_seed,
            "proof": proof, "game_disjointness": games,
            "rollouts": planlib.rollout_plan(accept_n=accept_size, proposal_n=len(P[0]), test_n=len(test))}


def _initialize(lbr: Any, root: Path, domain: str, d: dict[str, Any]) -> tuple[dict, dict]:
    """Equivalent of upstream ``initialize`` with its TRAIN/TEST overlap check made split-aware.

    Upstream raises ``frozen unique TRAIN/TEST schedule mismatch`` for ALFWorld because it
    intersects raw integer indices of two different splits (``train_valid`` vs ``new_std``): 8 of
    the shipped TRAIN indices equal TEST indices numerically while naming different games (the
    two game-file sets are disjoint; checked in ``design``). It also freezes only this domain's
    data (upstream freezes all three domains and so demands ~5.8 GB of WebShop files). The body is
    otherwise a copy of ``life_agentbench_run.initialize`` at 4844bbb, so state, protocol and
    frozen-hash layout stay what the unmodified runner and its evaluator subprocess expect.
    """
    if root.exists():
        raise FileExistsError("new run required; no blind replay of paid sessions")
    original = lbr.read(lbr.HISTORICAL / "manifest.json")
    batches, tests = d["proposal_batches"], d["test_ids"]
    if (not tests or len(set(tests)) != len(tests)
            or any(len(b) != 50 or len(set(b)) != 50 for b in batches)):
        raise ValueError("frozen unique TRAIN/TEST schedule mismatch (split-aware check)")
    frozen = {str(lbr.ROOT / n): sha for n, sha in lbr.profile.source_hashes().items()}
    for n, sha in original["snapshot_hashes"].items():
        frozen[str(lbr.HISTORICAL / "task_snapshot" / n)] = sha
    # Upstream freezes EVERY domain's data, so ``verify`` demands the three WebShop raw files
    # (~5.8 GB download) even for an ALFWorld-only run. Keep only this domain's data.
    dropped = [n for n in original["data_hashes"] if not n.startswith(f"data/{domain}/")]
    for n, sha in original["data_hashes"].items():
        if n not in dropped:
            frozen[str(lbr.ROOT / "AgentBench" / n)] = sha
    d["frozen_data_dropped"] = dropped
    files = [Path(lbr.__file__), lbr.HISTORICAL / "manifest.json", lbr.ROOT / "evolution/tau_comparison/common.py"]
    files += list(lbr.COMPOSITION.glob("*.py"))
    files += [lbr.AHE_NATIVE / "ahe_native" / n for n in ("api_broker.py", "metered_broker.py", "token_accounting.py", "connection.py")]
    frozen.update({str(p.resolve()): lbr.digest(p) for p in files})
    protocol = {"name": root.name, "domain": domain, "rounds": 6, "batches": batches, "test_ids": tests,
        "initialization": "empty H2-H5; no imported historical strategies",
        "solver": original["agent"], "solver_total_context": 32768, "solver_workers": 50,
        "optimizer": {"model": "deepseek-v4-flash", "max_output": lbr.OUTPUT_LIMIT,
            "interaction_limit": None, "token_limit": lbr.profile.MAX_TOTAL_TOKENS, "max_repairs": 3},
        "global_mr_concurrency": 8,
        "selection": "strict improvement on same complete 50-task TRAIN batch",
        "test": "fixed TRAIN-selected incumbent; full TEST after six rounds and seal"}
    root.mkdir(parents=True)
    lbr.save(root / "protocol.json", protocol)
    frozen[str(root / "protocol.json")] = lbr.digest(root / "protocol.json")
    lbr.save(root / "frozen_sources.json", frozen)
    lbr.save(root / domain / "state.json", {"domain": domain, "round": 0, "rounds": [],
        "active_snapshot": [], "active_snapshot_sha256": lbr.hooks.object_digest([]),
        "accepted_bundle_ids": [], "operation_log": []})
    lbr.save(root / "status.json", {"phase": "prepared", "completed_rounds": 0})
    return protocol, frozen


def prepare(lh_root: Path, name: str, *, glue_dir: Path, accept_seed: int = 20261123,
            budget_unit: str = "rollouts", budget_limit: float | None = None, min_gain: int = 1,
            max_p: float | None = None, max_infra_retries: int = 2, solver_workers: int | None = None) -> dict[str, Any]:
    """Create the run directory via upstream ``initialize`` and amend its protocol with R1-R5."""
    add_upstream_paths(lh_root)
    from evolution import life_agentbench_run as lbr  # upstream
    d = design(lh_root, accept_seed=accept_seed)
    total = d["rollouts"]["total"]
    limit = budget_limit if budget_limit is not None else (round(total * 1.15) if budget_unit == "rollouts" else None)
    budget = Budget(budget_unit, limit)  # refuses any unit other than rollouts/tokens (R5)
    root = lbr.ROOT / "evolution/experiments" / name
    protocol, frozen = _initialize(lbr, root, "alfworld", d)
    protocol["batches"] = d["proposal_batches"] + d["accept_batches"]
    protocol["proposal_batch_count"] = len(d["proposal_batches"])
    protocol["accept_batches"] = d["accept_batches"]
    protocol["meta_reference"] = [{} for _ in d["proposal_batches"]]  # upstream round() reads these; see module docstring
    protocol["ahe_reference"] = [{} for _ in d["proposal_batches"]]
    if solver_workers is not None:
        protocol["solver_workers"] = int(solver_workers)
    protocol["selection"] = ("R1-R5 rigor gate (AP-BSV2-ACCEPT-RIGOR): accept on a DISJOINT 50-task batch, fresh parent "
                             "re-run, sealed TEST, per-round decision record, budget in " + budget_unit)
    protocol["rigor"] = {
        "rules": ["R1 disjoint accept tasks", "R2 fresh parent re-run", "R3 sealed test split",
                  "R4 per-round decision record", "R5 budget in rollouts or tokens"],
        "train_split": d["train_split"], "test_split": d["test_split"], "accept_seed": accept_seed,
        "min_gain": min_gain, "max_p": max_p, "max_infra_retries": max_infra_retries,
        "budget": budget.to_json(), "rollouts": d["rollouts"], "proof": d["proof"],
        "game_disjointness": d["game_disjointness"], "frozen_data_dropped": d.get("frozen_data_dropped", []),
        "headline_rule": "final incumbent after the last TRAIN round (accept-gated); never selected on TEST",
        "glue_sha256": planlib.digest_files([glue_dir / n for n in GLUE_FILES if (glue_dir / n).exists()])}
    lbr.save(root / "protocol.json", protocol)
    frozen[str(root / "protocol.json")] = lbr.digest(root / "protocol.json")
    lbr.save(root / "frozen_sources.json", frozen)
    lbr.save(root / "RIGOR_BUDGET.json", budget.to_json())
    return {"root": str(root), "rigor": protocol["rigor"]}


def install_long_broker(timeout_s: float) -> None:
    """Raise the metering broker's upstream read timeout (default 600 s) before ``Run.run`` imports it."""
    import ahe_native.metered_broker as mb
    base = mb.Broker

    class LongBroker(base):  # type: ignore[misc, valid-type]
        def __init__(self, *a, **kw):
            kw.setdefault("upstream_timeout", timeout_s)
            super().__init__(*a, **kw)

    mb.Broker = LongBroker


PASS_TO_CHILD = ("LIFE_SOLVER_TOKENIZER", "LIFE_FLASH_TOKENIZER")


def patch_child_env(lbr: Any, names: tuple[str, ...] = PASS_TO_CHILD) -> None:
    """Re-add tokenizer-path variables that upstream ``child_env`` strips from the evaluator subprocess.

    ``tau_comparison.common.child_env`` drops every variable whose NAME contains KEY, TOKEN, SECRET,
    PASSWORD, CREDENTIAL or AUTH, which removes ``LIFE_SOLVER_TOKENIZER``. The evaluator then falls
    back to ``Qwen/Qwen3-4B`` with ``local_files_only=True`` and every episode becomes an
    infrastructure error. These two variables are filesystem paths, not secrets.
    """
    original = lbr.native_environment
    if getattr(original, "_lh_patched", False):
        return

    def patched():
        env = original()
        for n in names:
            if os.environ.get(n):
                env[n] = os.environ[n]
        return env

    patched._lh_patched = True
    lbr.native_environment = patched


def make_run_class(lbr: Any):
    """Return ``RigorRun`` bound to the imported upstream module ``lbr``."""
    patch_child_env(lbr)

    class RigorRun(lbr.Run):
        def __init__(self, root: Path):
            super().__init__(root)
            self.rigor = self.protocol["rigor"]
            budget_file = Path(root) / "RIGOR_BUDGET.json"
            self.budget = Budget.from_json(_read(budget_file)) if budget_file.exists() else Budget.from_json(self.rigor["budget"])

        # -- persistence -------------------------------------------------
        def _save_budget(self) -> None:
            lbr.save(self.root / "RIGOR_BUDGET.json", self.budget.to_json())

        # -- evaluations that bypass the round (smoke, final TEST) ------------
        def evaluate(self, split, name, manifest, ids):
            if split == "test" and not (self.root / "training_seal.json").exists():
                raise RigorViolation("R3", "TEST requested before the TRAIN seal exists")
            if self.rigor["train_split"] == self.rigor["test_split"]:
                raise RigorViolation("R3", "train and test share a split namespace")
            self.budget.check(rollouts=len(ids), what=f"{split}/{name}")
            summary, directory = lbr.Run.evaluate(self, split, name, manifest, ids)
            self.budget.charge(len(ids), summary.get("tokens", 0))
            self._save_budget()
            return summary, directory

        # -- ports for rounds.run_round ---------------------------------------
        def _ports(self):
            run = self
            train_split = self.rigor["train_split"]

            class Ports:
                budget = run.budget

                def active_manifest(self, name):
                    return run.compose.write_active_chain(run.work, run.state, name)

                def snapshot_sha(self):
                    return run.state["active_snapshot_sha256"]

                def evaluate(self, name, manifest, ids):
                    directory = run.work / "evals" / name
                    fresh = not directory.exists()
                    summary, d = lbr.Run.evaluate(run, "train", name, manifest, ids)
                    rows = []
                    for i in ids:
                        r = _read(Path(d) / f"episode_{i}.json")
                        rows.append({"id": qualify(train_split, i), "index": int(i), "success": int(r["success"]),
                                     "status": r.get("status"), "infra": bool(r.get("infrastructure_error")),
                                     "tokens": r.get("tokens", 0)})
                    return {"rows": rows, "dir": str(d), "fresh": fresh, "tokens": summary.get("tokens", 0), "summary": summary}

                def propose(self, number, evidence):
                    workspace = run.root / f"optimizer_inputs/round_{number:02d}"
                    output = run.work / f"proposals/round_{number:02d}"
                    lbr.profile.prepare(run.work, Path(evidence["dir"]), workspace, seed=number)
                    bundle_path = lbr.profile.propose(workspace, output, completion=run.completion(number),
                        checkpoint_dir=run.work / f"optimizer_sessions/round_{number:02d}")
                    validation, usage = _read(output / "validation.json"), run.usage(number)
                    if (not usage["inference_accounting_complete"] or not usage["total_tokens"]
                            or usage["total_tokens"] != validation["usage"].get("total_tokens", 0)):
                        raise RuntimeError("optimizer ledger/checkpoint mismatch")
                    return {"bundle_path": bundle_path, "optimizer_tokens": usage["total_tokens"], "usage": usage,
                            "meta": {"proposer_requests": validation["proposer_requests"],
                                     "repairs_granted": validation["repairs_granted"]}}

                def stage(self, number, bundle_path):
                    bundle, _, staged = run.compose.stage_bundle(run.work, number, bundle_path, run.state)
                    return bundle, staged

                def commit(self, bundle):
                    parent = run.state["active_snapshot_sha256"]
                    operations = [{k: v for k, v in op.items() if k != "artifact_path"} for op in bundle["operations"]]
                    active = run.compose.commit_bundle(run.work, bundle, run.state)
                    run.state["active_snapshot"], run.state["active_snapshot_sha256"] = active, lbr.hooks.object_digest(active)
                    run.state["accepted_bundle_ids"].append(bundle["bundle_id"])
                    run.state["operation_log"].append({"bundle_id": bundle["bundle_id"], "operations": operations,
                        "parent_snapshot_sha256": parent, "committed_snapshot_sha256": run.state["active_snapshot_sha256"]})
                    return run.state["active_snapshot_sha256"]

                def write_decision(self, record):
                    out = run.root / "decisions"
                    out.mkdir(exist_ok=True)
                    lbr.save(out / f"round_{record['round']:02d}.json", record)
                    with (run.root / "DECISIONS.jsonl").open("a") as f:
                        f.write(json.dumps(record, sort_keys=True) + "\n")
                    run._save_budget()

            return Ports()

        def round(self, number):
            cfg = {"proposal_batches": self.protocol["batches"][:self.protocol["proposal_batch_count"]],
                   "accept_batches": self.protocol["accept_batches"], "train_split": self.rigor["train_split"],
                   "test_split": self.rigor["test_split"], "test_ids": self.protocol["test_ids"],
                   "min_gain": self.rigor["min_gain"], "max_p": self.rigor["max_p"],
                   "max_infra_retries": self.rigor["max_infra_retries"]}
            result = roundlib.run_round(self._ports(), cfg, number)
            d, bundle = result["decision"], result["bundle"]
            operations = [{k: v for k, v in op.items() if k != "artifact_path"} for op in bundle["operations"]]
            row = {"round": number, "train_batch": number - 1, "accepted": result["accepted"], "outcome": result["outcome"],
                   "parent_accept_successes": d["parent_successes"], "candidate_accept_successes": d["candidate_successes"],
                   "accept_gain": d["gain"], "accept_n": d["accept_n"], "mcnemar_exact_p": d["mcnemar_exact_p"],
                   "tokens_per_accepted_gain": d["tokens_per_accepted_gain"], "budget_unit": d["budget_unit"],
                   "bundle_id": bundle["bundle_id"], "bundle_hypothesis": bundle["hypothesis"], "operations": operations,
                   "active_snapshot_sha256": result["active_snapshot_sha256"], "decision_record": f"decisions/round_{number:02d}.json",
                   "proposer_requests": d["proposer"].get("proposer_requests"), "repairs_granted": d["proposer"].get("repairs_granted")}
            self.state["rounds"].append(row)
            self.state["round"] = number
            lbr.save(self.work / "state.json", self.state)
            self.verify()
            lbr.save(self.root / "TRAINING_RESULTS.json", {"domain": self.domain, "rounds": self.state["rounds"]})
            self.progress("round_complete", **{k: row[k] for k in ("round", "accepted", "outcome")})

    return RigorRun
