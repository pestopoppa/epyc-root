#!/usr/bin/env python3
"""Launcher for the rigor-enforced Life-Harness ALFWorld run (AP-POSTREBOOT-LH-RIGOR).

Run with the controller interpreter and ``-I`` (the script inserts its own repo root):

  PY=<controller venv>/bin/python
  $PY -I scripts/harness/life_harness/cli.py plan        --lh-root LH --name NAME
  $PY -I scripts/harness/life_harness/cli.py prepare     --lh-root LH --name NAME [budget/gate flags]
  $PY -I scripts/harness/life_harness/cli.py proxy       --improver-upstream URL --improver-model M \\
                                                         --solver-upstream URL --solver-model M [--improver-port P]
  $PY -I scripts/harness/life_harness/cli.py conformance --lh-root LH --improver-port P [--request FILE]
  $PY -I scripts/harness/life_harness/cli.py verify      --lh-root LH --name NAME [--deep]
  $PY -I scripts/harness/life_harness/cli.py smoke       --lh-root LH --name NAME --solver-tokenizer DIR [--episodes 5]
  $PY -I scripts/harness/life_harness/cli.py run         --lh-root LH --name NAME --improver-port P ... [--launch]

``plan``, ``prepare`` (writes the run dir), ``verify``, ``proxy`` (serves until killed) and ``run``
WITHOUT ``--launch`` (prints the plan) make no model call. ``smoke`` calls the SOLVER only;
``conformance`` makes one short improver request; ``run --launch`` does everything.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.harness.life_harness import conformance, run_alfworld  # noqa: E402
from scripts.harness.life_harness.proxy import HEALTH_PATH, LoopbackProxy  # noqa: E402

GLUE_DIR = Path(__file__).resolve().parent
SOLVER_FROZEN_PORT = 8400  # evolution/reproduction/reference/manifest.json agent.url


def _health(port: int) -> dict:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}{HEALTH_PATH}", timeout=5) as r:
        return json.load(r)


def cmd_plan(a) -> int:
    lh = Path(a.lh_root)
    d = run_alfworld.design(lh, accept_seed=a.accept_seed)
    out = {"name": a.name, "model_calls": 0,
           "rounds": [{"round": n + 1,
                       "evals": [{"name": f"incumbent_{n + 1:02d}", "ids": "P_%d" % (n + 1), "n": len(d["proposal_batches"][n]),
                                  "role": "evidence for the proposer (as shipped)"},
                                 {"name": f"accept_parent_{n + 1:02d}", "ids": "A_%d" % (n + 1), "n": len(d["accept_batches"][n]),
                                  "role": "R2 fresh parent re-run on the accept batch"},
                                 {"name": f"accept_candidate_{n + 1:02d}", "ids": "A_%d" % (n + 1), "n": len(d["accept_batches"][n]),
                                  "role": "candidate on the accept batch"}],
                       "gate": "rigor.decide_accept: R1 R2 R3 R4 R5, min_gain=%d" % a.min_gain} for n in range(len(d["proposal_batches"]))],
           "final_test": {"name": "final_test", "n": len(d["test_ids"]), "split": d["test_split"],
                          "rule": "R3: sealed until training_seal.json; headline = final TRAIN-gated incumbent"},
           "rollouts": d["rollouts"], "proof": d["proof"], "game_disjointness": d["game_disjointness"],
           "budget": {"unit": a.budget_unit, "limit": a.budget_limit if a.budget_limit is not None else round(d["rollouts"]["total"] * 1.15)},
           "accept_batch_head": [b[:5] for b in d["accept_batches"]]}
    sys.path.insert(0, str(lh))
    try:  # stock plan, for comparison only: it runs three domains and knows nothing of R1-R5
        from evolution import reproduce as stock
        out["stock_reproduce_plan_commands"] = [s["command"][-6:] for s in stock.make_plan(a.name, "agentbench", "life")["steps"]]
    except Exception as exc:  # pragma: no cover
        out["stock_reproduce_plan_commands"] = "unavailable: " + type(exc).__name__
    print(json.dumps(out, indent=2))
    return 0


def cmd_prepare(a) -> int:
    res = run_alfworld.prepare(Path(a.lh_root), a.name, glue_dir=GLUE_DIR, accept_seed=a.accept_seed,
                               budget_unit=a.budget_unit, budget_limit=a.budget_limit, min_gain=a.min_gain,
                               max_p=a.max_p, max_infra_retries=a.max_infra_retries, solver_workers=a.solver_workers)
    print(json.dumps(res, indent=2))
    return 0


def cmd_verify(a) -> int:
    """No model calls: load the prepared run through RigorRun and re-check every frozen hash."""
    lh = Path(a.lh_root)
    run_alfworld.add_upstream_paths(lh)
    from evolution import life_agentbench_run as lbr
    run = run_alfworld.make_run_class(lbr)(lbr.ROOT / "evolution/experiments" / a.name)
    bad = [p for p, sha in run.frozen.items() if not Path(p).is_file() or lbr.digest(p) != sha]
    if bad:
        print(json.dumps({"frozen_ok": False, "offenders": len(bad), "missing": sum(not Path(p).is_file() for p in bad),
                          "sample": bad[:5]}, indent=2))
        return 5
    run.verify()
    deep = None
    if a.deep:  # build the incumbent manifest (no model) and let upstream's own evaluator config accept every batch
        manifest = run.compose.write_active_chain(run.work, run.state, "verify_probe")
        deep = {}
        for label, ids in (("P_1", run.protocol["batches"][0]), ("A_1", run.protocol["accept_batches"][0]),
                           ("A_6", run.protocol["accept_batches"][5])):
            cfg = lbr.evaluation_config(run.root, "train", "verify_probe", manifest, ids)
            deep[label] = {"n": len(cfg["ids"]), "concurrency": cfg["concurrency"]}
        try:
            lbr.evaluation_config(run.root, "test", "final_test", manifest, run.protocol["test_ids"])
            deep["test_before_seal"] = "ACCEPTED (unexpected)"
        except Exception as exc:
            deep["test_before_seal"] = "refused: " + type(exc).__name__
    print(json.dumps({"deep": deep, "name": a.name, "frozen_ok": True, "rounds_done": run.state["round"], "budget": run.budget.to_json(),
                      "accept_batches": len(run.protocol["accept_batches"]), "batches_total": len(run.protocol["batches"]),
                      "solver_workers": run.protocol["solver_workers"], "min_gain": run.rigor["min_gain"],
                      "headline_rule": run.rigor["headline_rule"]}, indent=2))
    return 0


def cmd_proxy(a) -> int:
    log = Path(a.log_dir)
    imp = LoopbackProxy(mode="improver", upstream_base=a.improver_upstream, model_alias=a.improver_model,
                        port=a.improver_port, log_path=log / "improver_proxy.jsonl")
    sol = LoopbackProxy(mode="solver", upstream_base=a.solver_upstream, model_alias=a.solver_model,
                        port=a.solver_port, log_path=log / "solver_proxy.jsonl")
    imp.start()
    sol.start()
    print(json.dumps({"improver": imp.url, "solver": sol.url, "pid": os.getpid()}), flush=True)
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(flag=True))
    while not stop["flag"]:
        signal.pause()
    imp.stop()
    sol.stop()
    return 0


def cmd_conformance(a) -> int:
    if a.request:
        request = json.loads(Path(a.request).read_text())
    else:
        run_alfworld.add_upstream_paths(Path(a.lh_root))
        from evolution.life_evolve import profile  # upstream tool list
        request = conformance.synthetic_request(profile.TOOLS)
    verdict = conformance.replay(request, f"http://127.0.0.1:{a.improver_port}")
    if a.out:
        conformance.write_verdict(verdict, Path(a.out))
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["ok"] else 3


def cmd_smoke(a) -> int:
    """N solver episodes through the real evaluator + solver proxy (model calls: solver only; no improver).

    Gives the measured rate (episodes/hour, tokens/episode, status split) that the run booking is
    derived from. Uses the first N ids of proposal batch P_1 (search-side ids; R1/R3 unaffected).
    """
    import time
    lh = Path(a.lh_root)
    sol = _health(a.solver_port)
    if sol.get("mode") != "solver" or a.solver_port != SOLVER_FROZEN_PORT:
        print("refusing: solver port does not answer as our solver proxy on the frozen port", file=sys.stderr)
        return 4
    os.environ["LIFE_SOLVER_TOKENIZER"] = a.solver_tokenizer
    run_alfworld.add_upstream_paths(lh)
    from evolution import life_agentbench_run as lbr
    run = run_alfworld.make_run_class(lbr)(lbr.ROOT / "evolution/experiments" / a.name)
    run.verify()
    ids = run.protocol["batches"][0][:a.episodes]
    manifest = run.compose.write_active_chain(run.work, run.state, f"{a.phase}_manifest")
    t0 = time.time()
    res = run._ports().evaluate(a.phase, manifest, ids)
    secs = time.time() - t0
    from scripts.harness.life_harness.rigor import status_split
    out = {"phase": a.phase, "episodes": len(ids), "wall_seconds": round(secs, 1),
           "episodes_per_hour": round(len(ids) / secs * 3600, 2) if secs else None,
           "solver_tokens": res["tokens"], "tokens_per_episode": round(res["tokens"] / len(ids), 1),
           "solver_workers": run.protocol["solver_workers"], "status_split": status_split(res["rows"]),
           "successes": sum(r["success"] for r in res["rows"]), "eval_dir": res["dir"]}
    lbr.save(run.root / f"{a.phase}_result.json", out)
    print(json.dumps(out, indent=2))
    return 0 if out["status_split"]["infra_error"] == 0 else 6


def cmd_run(a) -> int:
    lh = Path(a.lh_root)
    imp, sol = _health(a.improver_port), _health(a.solver_port)
    if imp.get("mode") != "improver" or sol.get("mode") != "solver":
        print("refusing: improver/solver ports do not answer as our proxies", file=sys.stderr)
        return 4
    if a.solver_port != SOLVER_FROZEN_PORT:
        print(f"refusing: the frozen manifest hardwires solver port {SOLVER_FROZEN_PORT}", file=sys.stderr)
        return 4
    env = {"MR_HOST": f"http://127.0.0.1:{a.improver_port}", "MR_API_KEY": "lh-local-loopback",
           "LIFE_FLASH_TOKENIZER": a.flash_tokenizer, "LIFE_SOLVER_TOKENIZER": a.solver_tokenizer}
    plan = {"name": a.name, "improver_proxy": imp, "solver_proxy": sol, "env_set": sorted(env), "launch": a.launch}
    if not a.launch:
        print(json.dumps({**plan, "note": "plan only; pass --launch to start model calls"}, indent=2))
        return 0
    os.environ.update(env)
    run_alfworld.add_upstream_paths(lh)
    run_alfworld.install_long_broker(a.upstream_timeout)
    from evolution import life_agentbench_run as lbr
    cls = run_alfworld.make_run_class(lbr)
    cls(lbr.ROOT / "evolution/experiments" / a.name).run()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, name=True):
        sp.add_argument("--lh-root", required=True, help="Life-Harness clone")
        if name:
            sp.add_argument("--name", required=True)

    def gate(sp):
        sp.add_argument("--accept-seed", type=int, default=20261123)
        sp.add_argument("--budget-unit", choices=planlib_units(), default="rollouts")
        sp.add_argument("--budget-limit", type=float, default=None, help="default: 1.15 x planned rollouts")
        sp.add_argument("--min-gain", type=int, default=1, help="accept needs candidate-parent successes >= this")
        sp.add_argument("--max-p", type=float, default=None, help="optional exact McNemar p ceiling for accepts")
        sp.add_argument("--max-infra-retries", type=int, default=2)

    sp = sub.add_parser("plan"); common(sp); gate(sp); sp.set_defaults(fn=cmd_plan)
    sp = sub.add_parser("prepare"); common(sp); gate(sp)
    sp.add_argument("--solver-workers", type=int, default=None, help="concurrent solver episodes (upstream default 50)")
    sp.set_defaults(fn=cmd_prepare)
    sp = sub.add_parser("verify"); common(sp)
    sp.add_argument("--deep", action="store_true", help="also build a manifest and check evaluator configs (no model)")
    sp.set_defaults(fn=cmd_verify)
    sp = sub.add_parser("proxy")
    sp.add_argument("--improver-upstream", required=True, help="architect llama-server base, e.g. http://127.0.0.1:PORT/v1")
    sp.add_argument("--improver-model", required=True)
    sp.add_argument("--improver-port", type=int, required=True)
    sp.add_argument("--solver-upstream", required=True, help="Qwen3.6-35B-A3B llama-server base, e.g. http://127.0.0.1:PORT/v1")
    sp.add_argument("--solver-model", required=True)
    sp.add_argument("--solver-port", type=int, default=SOLVER_FROZEN_PORT)
    sp.add_argument("--log-dir", required=True)
    sp.set_defaults(fn=cmd_proxy)
    sp = sub.add_parser("conformance"); common(sp, name=False)
    sp.add_argument("--improver-port", type=int, required=True)
    sp.add_argument("--request", default=None)
    sp.add_argument("--out", default=None)
    sp.set_defaults(fn=cmd_conformance)
    sp = sub.add_parser("smoke"); common(sp)
    sp.add_argument("--solver-port", type=int, default=SOLVER_FROZEN_PORT)
    sp.add_argument("--solver-tokenizer", required=True)
    sp.add_argument("--episodes", type=int, default=5)
    sp.add_argument("--phase", default="solver_smoke5")
    sp.set_defaults(fn=cmd_smoke)
    sp = sub.add_parser("run"); common(sp)
    sp.add_argument("--improver-port", type=int, required=True)
    sp.add_argument("--solver-port", type=int, default=SOLVER_FROZEN_PORT)
    sp.add_argument("--flash-tokenizer", required=True, help="dir with the 3 hash-pinned DeepSeek-V4-Flash tokenizer files")
    sp.add_argument("--solver-tokenizer", required=True, help="local HF tokenizer dir for the solver model; for Qwen3.6 use a count-only copy whose "
                    "chat_template tolerates JSON-string tool arguments (the frozen worker passes strings)")
    sp.add_argument("--upstream-timeout", type=float, default=7200.0, help="broker read timeout for one improver completion (s)")
    sp.add_argument("--launch", action="store_true")
    sp.set_defaults(fn=cmd_run)
    a = p.parse_args()
    return a.fn(a)


def planlib_units():
    from scripts.harness.life_harness.rigor import BUDGET_UNITS
    return list(BUDGET_UNITS)


if __name__ == "__main__":
    sys.exit(main())
