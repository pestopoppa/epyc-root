#!/usr/bin/env python3
"""Verify pinned detached source, then run a separately granted native impact query."""
import json
import os
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
TREE = D / "source"
HEAD = "3796423904552652f4b3614d5a6b1497e84266e2"
FILE = "docs/reports/kv-cache/kpf50-child-evidence-20261104/child_evidence.py"
LOGS = D / "out" / "logs"
ENV = dict(os.environ, GITNEXUS_REPO_NAME="h-heterogeneous-slot-fabric-residency-impact6",
           GITNEXUS_VERBOSE="1", GITNEXUS_WORKER_POOL_SIZE="1",
           GITNEXUS_PARSE_CHUNK_CONCURRENCY="1")


def run(args, label, timeout=3600):
    """Run in the detached source tree and retain both streams plus exit status."""
    LOGS.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(args, cwd=TREE, env=ENV, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout, check=False)
    (LOGS / f"{label}.stdout.log").write_text(p.stdout)
    (LOGS / f"{label}.stderr.log").write_text(p.stderr)
    (LOGS / f"{label}.exit").write_text(f"{p.returncode}\n")
    if p.returncode:
        raise RuntimeError(f"{label} failed ({p.returncode}); see {LOGS}")
    return p.stdout


def check():
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=TREE,
                          text=True, capture_output=True, check=True).stdout.strip()
    assert Path(root).resolve() == TREE.resolve(), "source path is not its own checkout"
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=TREE, text=True,
                          capture_output=True, check=True).stdout.strip()
    assert head == HEAD, f"source HEAD drift: {head}"
    branch = subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=TREE,
                            text=True, capture_output=True)
    assert branch.returncode == 1, "source checkout must remain detached"
    dirty = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                           cwd=TREE, text=True, capture_output=True, check=True).stdout
    assert not dirty, f"source checkout is dirty: {dirty.strip()}"
    assert (TREE / FILE).is_file(), "target source missing"
    refs = subprocess.run(["git", "grep", "-n", "-w", "main", HEAD, "--", FILE],
                          cwd=TREE, text=True, capture_output=True, check=False)
    assert refs.returncode == 0 and refs.stdout.strip(), "no committed main source reference"
    return refs.stdout.splitlines()


refs = check()
if "--check" in sys.argv:
    print(f"Pinned detached source and target reference verified at {HEAD}; no graph work")
    raise SystemExit(0)

(D / "out").mkdir(exist_ok=True)
if os.environ.get("FILLER_SMOKE") == "1":
    # The smoke is a source-only check. It must never index or query GitNexus.
    p = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"])
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps({"type": "source_reference_scan", "status": "partial",
                            "head": HEAD, "symbol": "main", "source": FILE,
                            "unit_key": "committed_main_reference_lines",
                            "committed_main_reference_lines": len(refs),
                            "unit": "reference_lines", "count": len(refs),
                            "progress_s": 300, "references": refs}) + "\n")
        f.flush()
        os.fsync(f.fileno())
    raise SystemExit(75)

# Full grant only: the detached pinned checkout owns both its GitNexus index and query.
tracked = subprocess.run(["git", "ls-files", "-z"], cwd=TREE, capture_output=True, check=True).stdout
large = []
for raw_path in tracked.split(b"\0"):
    if not raw_path:
        continue
    path = raw_path.decode()
    full = TREE / path
    if full.is_file() and full.stat().st_size > 512 * 1024:
        large.append({"path": path, "size_bytes": full.stat().st_size})
(D / "out" / "tracked-files-over-512KiB.json").write_text(
    json.dumps({"threshold_bytes": 512 * 1024, "files": large}, indent=2) + "\n")
run(["/bin/bash", str(TREE / "scripts/gitnexus-analyze.sh"), "--skip-agents-md",
     "--skip-skills", "--workers", "1", "--force"], "analyze")
status = run(["gitnexus", "status"], "status")
assert str(TREE) in status and HEAD[:7] in status, "graph does not bind pinned source"
raw = run(["gitnexus", "impact", "main", "--repo", str(TREE), "--direction",
           "upstream", "--file", FILE], "impact")
try:
    data = json.loads(raw)
except json.JSONDecodeError as exc:
    raise RuntimeError(f"native impact output was not JSON; raw output retained in {LOGS}") from exc
assert (isinstance(data, dict) and not data.get("error") and not data.get("partial")
        and not data.get("truncated") and data.get("status") not in ("ambiguous", "not_found")
        and data.get("risk") in ("LOW", "MEDIUM", "HIGH", "CRITICAL")), \
    "impact unresolved/partial; native output retained in logs"
target = data.get("target")
assert isinstance(target, dict) and target.get("name") == "main" \
       and target.get("filePath") == FILE, "native impact target mismatch; raw output retained in logs"
with (D / "out" / "results.jsonl").open("a") as f:
    f.write(json.dumps({"type": "native_impact", "head": HEAD, "symbol": "main",
                        "source": FILE, "impact": data}, sort_keys=True) + "\n")
    f.flush()
    os.fsync(f.fileno())
if data["risk"] in ("HIGH", "CRITICAL"):
    (D / "out" / "OWNER_WARNING").write_text(
        f"STOP: main upstream impact {data['risk']}; owner review required before source edits.\n")
    raise SystemExit(3)
(D / "out" / "COMPLETE").write_text("Exact-source native upstream impact retained.\n")
