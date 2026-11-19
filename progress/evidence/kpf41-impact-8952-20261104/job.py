#!/usr/bin/env python3
"""Candidate-bound, model-free GitNexus impact scan. Requires the granted CPU build role."""
import json
import os
from pathlib import Path
import subprocess
import sys

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
from source_integrity import TREE, verify

OUT = D / "out"
GUARD = D / "gitnexus-guard.py"
HEAD = "8952a0f693fb923918157eb25117641b74766230"
SYMBOLS = [
    ("ggml_cuda_get_best_fattn_kernel", "ggml/src/ggml-cuda/fattn.cu"),
    ("ggml_cuda_flash_attn_ext_vec", "ggml/src/ggml-cuda/fattn.cu"),
    ("ggml_cuda_flash_attn_ext_vec_case_impl", "ggml/src/ggml-cuda/fattn-vec.cuh"),
    ("flash_attn_ext_vec", "ggml/src/ggml-cuda/fattn-vec.cuh"),
]
ENV = dict(os.environ, GITNEXUS_REPO_NAME="kpf41-direct-vec-impact-8952a0f", GITNEXUS_VERBOSE="1",
           GITNEXUS_HOME=str(D / "gitnexus-home"),
           GITNEXUS_WORKER_POOL_SIZE="1", GITNEXUS_PARSE_CHUNK_CONCURRENCY="1",
           GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS="120000", GITNEXUS_WORKER_MAX_CUMULATIVE_TIMEOUT_MS="600000",
           GITNEXUS_WORKER_SUB_BATCH_MAX_BYTES="131072")


def run(args, name=None):
    p = subprocess.run(args, cwd=TREE, env=ENV, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=7200)
    if name:
        (OUT / f"{name}.stdout").write_text(p.stdout)
        (OUT / f"{name}.stderr").write_text(p.stderr)
    if p.returncode:
        raise RuntimeError(f"{args!r} rc={p.returncode}; inspect retained {name} logs")
    return p.stdout


def emit(value, path=None):
    target = path or (OUT / "results.jsonl")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a") as f:
        f.write(json.dumps(value, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def main():
    ident = verify()
    if "--check" in sys.argv:
        print("Pinned source HEAD/tree, clean state, tracked coverage and key source digests verified; no graph scan")
        return 0
    OUT.mkdir(exist_ok=True)
    refs = {}
    for symbol, source in SYMBOLS:
        refs[symbol] = run(["git", "grep", "-n", "-w", symbol, HEAD, "--", source]).splitlines()
        if not refs[symbol]:
            raise RuntimeError(f"source reference not found for {symbol}")
    reference_record = {"type": "source_reference_scan", "status": "partial", "head": HEAD,
                        "tree": ident["tree"], "unit": 1, "count": len(SYMBOLS) + 1,
                        "references": refs, "counts": {k: len(v) for k, v in refs.items()}}
    if os.environ.get("FILLER_SMOKE") == "1":
        dry_path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"])
        emit(reference_record, dry_path)
        return 0
    emit(reference_record)

    run(["/usr/bin/python3", "-I", str(GUARD), "--repo", "app"])
    run(["bash", str(TREE / "scripts/gitnexus-analyze.sh"), "--skip-agents-md", "--skip-skills",
         "--index-only", "--workers", "1", "--force", "--verbose", "--max-file-size", "512",
         "--name", "kpf41-direct-vec-impact-8952a0f", "--allow-duplicate-name"], "analyze")
    status = run(["gitnexus", "status"], "status")
    if str(TREE) not in status or HEAD[:8] not in status:
        raise RuntimeError("GitNexus status does not identify the exact candidate source")

    tracked = run(["git", "ls-files", "-z"]).split("\0")
    large = [{"path": p, "bytes": (TREE / p).stat().st_size}
             for p in tracked if p and (TREE / p).is_file() and (TREE / p).stat().st_size > 512 * 1024]
    (OUT / "coverage.json").write_text(json.dumps({
        "head": HEAD, "tree": ident["tree"], "tracked_files": ident["tracked_files"],
        "graph_status": status, "tracked_files_over_512KiB": large,
        "limit_bytes": 512 * 1024, "analyzer_logs": ["analyze.stdout", "analyze.stderr"],
        "scope": "retained native diagnostics are required; files skipped by size/parser are unknown-impact, not zero-impact"
    }, indent=2) + "\n")

    for index, (symbol, source) in enumerate(SYMBOLS, 1):
        verify()
        raw = run(["gitnexus", "impact", symbol, "--repo", str(TREE), "--direction", "upstream",
                   "--file", source], f"impact-{index}")
        data = json.loads(raw)
        valid = (isinstance(data, dict) and data.get("target") and not data.get("error") and
                 not data.get("partial") and not data.get("truncated") and
                 data.get("status") not in ("ambiguous", "not_found") and
                 data.get("risk") in ("LOW", "MEDIUM", "HIGH", "CRITICAL"))
        if not valid:
            raise RuntimeError(f"impact unresolved/partial for {symbol}; no risk clearance")
        emit({"type": "native_impact", "head": HEAD, "tree": ident["tree"],
              "unit": index + 1, "count": len(SYMBOLS) + 1,
              "symbol": symbol, "source": source, "impact": data})
        if data["risk"] in ("HIGH", "CRITICAL"):
            (OUT / "OWNER_WARNING").write_text(
                f"STOP: {symbol} upstream impact {data['risk']}; owner review required before source edits.\n")
            emit({"type": "risk_stop", "head": HEAD, "symbol": symbol,
                  "risk": data["risk"], "partial": True})
            return 3
    verify()
    emit({"type": "scan_complete", "head": HEAD, "tree": ident["tree"],
          "unit": len(SYMBOLS) + 1, "count": len(SYMBOLS) + 1,
          "impact_count": len(SYMBOLS), "partial": False,
          "coverage": "out/coverage.json; inspect skipped-file logs before scope claims"})
    (OUT / "COMPLETE").write_text("All four native upstream impact scans and source coverage retained.\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        OUT.mkdir(exist_ok=True)
        (OUT / "INCONCLUSIVE").write_text(f"STOP: {type(exc).__name__}: {exc}\n")
        print(f"impact scan inconclusive: {exc}", file=sys.stderr)
        raise SystemExit(1)
