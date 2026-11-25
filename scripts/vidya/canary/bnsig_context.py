"""AK-BNSIG-P4 planning-context canary: a census bottleneck signature reaches the AutoKernel planner.

No inference, no GPU, no server. Stops at context assembly (agent-loop-design.md "Wired" is a canary
result). Passes only if, against a signed census:

1. the census signatures ingest into a SCRATCH ledger through `cli.py ingest ak-bottleneck-signature`
   (one Judged/Located observation per fired class, nothing refused or dropped);
2. run.py's own context hook (`bnsig_planner.context_entry`) yields the `bottleneck_signatures` view for
   a GPU target and nothing for a CPU target;
3. the prompt the planner is given (`actors.render_context`) shows the seeded hotspot with its primary
   class and its ruled-out set, and the CPU prompt does not;
4. a planted proposal declaring a RULED-OUT limiter (`sig:<class>`), parsed by the real
   `AgentPlanner._proposal_from_raw`, comes back as a Hypothesis (never refused) carrying
   `signature_assessment.verdict == "signature_conflict"`, with the WARN logged; a proposal declaring the
   primary class comes back `consistent`.

    python3 scripts/vidya/canary/bnsig_context.py --research <epyc-inference-research checkout> \
        --census <signed mi210_bandwidth_census.json> --scratch /mnt/raid0/llm/tmp/<dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import subprocess
import sys
import tempfile
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIDYA = ROOT / "scripts/vidya"
SCRATCH_ROOT = Path("/mnt/raid0/llm/tmp")
SOURCE = "ak-bottleneck-signature"
GPU_CTX = {"gpu_serving_profile": {"status": "observed", "windows": {}}, "kernel_hotspots": []}
CPU_TARGET = {"target": {"recipe": {"backend": "cpu"}}}


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ingest(census: Path, ledger: Path) -> dict:
    done = subprocess.run(
        [sys.executable, "-B", str(VIDYA / "cli.py"), "--ledger", str(ledger), "--json", "ingest", SOURCE,
         "--path", str(census), "--as-of", datetime.now(timezone.utc).isoformat()],
        cwd=ROOT, check=True, capture_output=True, text=True, timeout=120)
    report = json.loads(done.stdout)
    require(report["rows_projected"] > 0 and not (report.get("refused") or report.get("missing")),
            f"signature ingest projected nothing or refused: {report}")
    return report


def expected(census: Path) -> list[dict]:
    """The signed records the planner must show: (kernel, primary, ruled_out without fired classes)."""
    doc = json.loads(census.read_text())
    out = []
    for key, rec in (doc.get("records") or {}).items():
        sig = rec.get("signature") or {}
        if sig.get("class"):
            fired = set(sig.get("classes") or []) | set(sig.get("marginal") or [])
            out.append({"record": key, "kernel": rec.get("kernel_class"), "primary": sig["class"],
                        "ruled_out": [c for c in sig.get("ruled_out") or [] if c not in fired]})
    require(out, "census carries no signature: nothing to canary")
    require(any(e["ruled_out"] for e in out), "no signed record rules anything out: the WARN leg cannot run")
    return out


def replay(research: Path, census: Path) -> dict:
    sys.path[:0] = [str(research / "scripts/kernel_rnd")]
    from autokernel import bnsig_planner
    from autokernel.loop import actors

    consumer = research / "scripts/kernel_rnd/autokernel"
    require(Path(actors.__file__).resolve() == consumer / "loop/actors.py"
            and Path(bnsig_planner.__file__).resolve() == consumer / "bnsig_planner.py",
            "AutoKernel consumer came from a different checkout")
    args = Namespace(signature_prune="advisory", signature_census=census)
    gpu_entry, cpu_entry = bnsig_planner.context_entry(args, cpu=False), bnsig_planner.context_entry(args, cpu=True)
    require(cpu_entry == {} and gpu_entry.get(bnsig_planner.CONTEXT_KEY, {}).get("status") == "observed",
            f"run.py context hook: gpu {gpu_entry} cpu {cpu_entry}")
    gpu_prompt = actors.render_context({**GPU_CTX, **gpu_entry})
    cpu_prompt = actors.render_context({**GPU_CTX, **CPU_TARGET, **gpu_entry})

    planner = actors.AgentPlanner.__new__(actors.AgentPlanner)   # parse path only: no backend, no workspace
    planner.backend, planner.workspace = "claude", None
    view = gpu_entry[bnsig_planner.CONTEXT_KEY]
    hit = next(h for h in view["hotspots"] if h["ruled_out"])

    def propose(limiter: str):
        body = {"mechanism_id": f"bnsig-canary-{limiter}", "statement": f"sig:{limiter} canary proposal",
                "falsifier": "canary", "target_surface": "canary.cu", "target_symbol": hit["kernel"]}
        hyp, _ = planner._proposal_from_raw(json.dumps(body), {**GPU_CTX, **gpu_entry})
        return hyp

    log = logging.getLogger("autokernel.bnsig")
    records: list[logging.LogRecord] = []
    handler = logging.Handler()
    handler.emit = records.append
    log.addHandler(handler)
    try:
        conflict = propose(hit["ruled_out"][0])
        consistent = propose(hit["primary"])
    finally:
        log.removeHandler(handler)
    return {"gpu_prompt": gpu_prompt, "cpu_prompt": cpu_prompt, "view": view, "hit": hit,
            "conflict": conflict, "consistent": consistent,
            "warns": [r.getMessage() for r in records if r.levelno >= logging.WARNING],
            "sources": {str(p): sha(p) for p in (consumer / "loop/actors.py", consumer / "bnsig_planner.py",
                                                 consumer / "loop/actor_render.py")},
            "Hypothesis": actors.Hypothesis}


def check(got: dict, exp: list[dict]) -> None:
    for e in exp:
        require(f"| `{e['kernel']}` | {e['primary']} |" in got["gpu_prompt"],
                f"planner prompt does not show {e['kernel']} as {e['primary']}")
        if e["ruled_out"]:
            require(", ".join(e["ruled_out"]) in got["gpu_prompt"], f"ruled-out set of {e['kernel']} not shown")
    require("Bottleneck signatures" not in got["cpu_prompt"], "CPU prompt carries GPU bottleneck signatures")
    c, k = got["conflict"], got["consistent"]
    require(isinstance(c, got["Hypothesis"]) and isinstance(k, got["Hypothesis"]),
            "a signature proposal was refused or abstained (the gate must never refuse)")
    require((c.signature_assessment or {}).get("verdict") == "signature_conflict"
            and c.signature_assessment["conflict"] == [got["hit"]["ruled_out"][0]],
            f"ruled-out proposal not flagged: {c.signature_assessment}")
    require((k.signature_assessment or {}).get("verdict") == "consistent",
            f"primary-class proposal flagged: {k.signature_assessment}")
    require(len(got["warns"]) == 1 and "signature_conflict" in got["warns"][0],
            f"expected exactly one WARN, got {got['warns']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--research", type=Path, required=True, help="epyc-inference-research checkout")
    parser.add_argument("--census", type=Path, required=True, help="census JSON carrying records[k].signature")
    parser.add_argument("--scratch", type=Path, required=True, help="parent dir for a private canary run")
    args = parser.parse_args(argv)
    scratch = args.scratch.resolve()
    if SCRATCH_ROOT not in scratch.parents:
        parser.error(f"--scratch must be a subdirectory of {SCRATCH_ROOT}")
    census = args.census.resolve()
    before = sha(census)
    exp = expected(census)
    scratch.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="bnsig-context-", dir=scratch))
    ledger = out / "ledger.jsonl"
    report = ingest(census, ledger)
    got = replay(args.research.resolve(), census)
    check(got, exp)
    require(sha(census) == before, "census changed during replay")
    excerpt = out / "planner-context.txt"
    excerpt.write_text(got["gpu_prompt"] + "\n")
    receipt = {
        "schema": "epyc.vidya.bnsig_planning_canary.v1", "status": "passed", "census": str(census),
        "census_sha256": before, "ingest": {k: report.get(k) for k in ("rows_projected", "frames_emitted")},
        "ledger_sha256": sha(ledger),
        "entry_point": "bnsig_planner.context_entry -> actors.render_context; AgentPlanner._proposal_from_raw",
        "stop_boundary": "context assembly and reply parsing only; no backend call",
        "hotspots_shown": exp, "conflict": got["conflict"].signature_assessment,
        "consistent": got["consistent"].signature_assessment, "warns": got["warns"],
        "sources_sha256": {**got["sources"], str(VIDYA / "adapters/autokernel_bottleneck_signature.py"):
                           sha(VIDYA / "adapters/autokernel_bottleneck_signature.py")},
        "rendered_excerpt": excerpt.name, "rendered_excerpt_sha256": sha(excerpt),
        "scope": "Model-free. Scratch ledger, no inference, no GPU, no promotion.",
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
