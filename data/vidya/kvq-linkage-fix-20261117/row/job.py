#!/usr/bin/env python3
"""VB-KVQ-V10-INGEST job: run the P-GPU-1 KV-quant sweep under the rowflow engine's GPU lock.

The producer is research scripts/benchmark/kv_quant_27b_v10_sweep.py (pinned clone ./research at
99301fa14). Binary = the production kernel store (kernels/production/gpu); the producer resolves,
hashes and ldd-verifies it itself and refuses anything else. The producer acquires the MI210 device
flock on its own; under filler_run15 the engine already holds that lock on fd 9, so this wrapper
replaces `claim.hold` with a context that PROVES the engine's ancestor holds the device-lock inode
(/proc/<pid>/fdinfo, exclusive FLOCK) and yields the producer's own HeldCpuClaim receipt. Nothing is
acquired twice and nothing is merely observed.

Modes
  --check   model-free preflight (store resolves, pins hash, research clone is the pinned commit).
  smoke     (FILLER_DRYRUN=1) one real replicate (A_f16_kv / d2k / rep1) through the producer's own
            run_replicate, no sidecar; writes $FILLER_DRYRUN_DIR/native/SMOKE-DONE.json.
  official  the full 30-launch matrix via the producer's main(); output run-<ts>/ holds summary.json
            and belief_measurements.jsonl (schema epyc.vidya.kv_quant_27b_v10_capture.v1), the exact
            file `cli.py ingest kv-quant-27b-v10-measurement` reads.
"""
import contextlib, json, os, runpy, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
RES = Path('/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate/tmp/vidya-kvq-v10-sweep-20261117/research')
SCRIPT = RES / "scripts/benchmark/kv_quant_27b_v10_sweep.py"
PINNED = "99301fa149af86a6f9743d2b0405c9234ba39586"
sys.path.insert(0, str(RES / "scripts"))
sys.path.insert(0, str(RES / "scripts/benchmark"))
def verify_source():
    import hashlib, subprocess
    manifest = json.loads((D / "source-closure.json").read_text())
    if subprocess.check_output(["git", "-C", str(RES), "rev-parse", "HEAD"], text=True).strip() != manifest["base_commit"]:
        raise RuntimeError("source commit differs")
    changed = subprocess.check_output(["git", "-C", str(RES), "diff", "--name-only", "HEAD"], text=True).splitlines()
    if changed != manifest["allowed_modified"]:
        raise RuntimeError("unexpected source diff")
    for rel, expected in manifest["files"].items():
        if hashlib.sha256((RES / rel).read_bytes()).hexdigest() != expected:
            raise RuntimeError("source closure changed: " + rel)
verify_source()
from kernel_rnd.autokernel.loop import claim  # noqa: E402


def head():
    import subprocess
    return subprocess.check_output(["git", "-C", str(RES), "rev-parse", "HEAD"], text=True).strip()


def prove_engine_lock():
    """An ancestor process holds the exclusive device flock on fd 9 (the engine's `exec 9>$GPU_LOCK`)."""
    expected = claim.DEVICE_LOCK.stat()
    for pid in claim._ancestor_pids(os.getpid()):
        try:
            actual = Path(f"/proc/{pid}/fd/9").stat()
            info = Path(f"/proc/{pid}/fdinfo/9").read_text()
        except OSError:
            continue
        if (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino) and any(
                l.startswith("lock:") and "FLOCK" in l and "WRITE" in l for l in info.splitlines()):
            return pid
    raise RuntimeError("no ancestor holds the MI210 device flock on fd 9; refusing to run unclaimed")


@contextlib.contextmanager
def engine_hold(lock_path=None, *, device_id=claim.DEVICE_ID, gpu_quiet_path=None):
    pid = prove_engine_lock()
    receipt = claim.HeldCpuClaim({"device_id": device_id, "lock_path": str(lock_path or claim.DEVICE_LOCK),
                                  "pid": pid, "mode": "engine_held_flock"}, [lock_path or claim.DEVICE_LOCK],
                                 gpu_quiet_path=gpu_quiet_path)
    yield receipt
    if prove_engine_lock() != pid:
        raise RuntimeError("engine GPU lock holder changed during the window")


def main():
    if head() != PINNED:
        raise SystemExit("research clone is not at the pinned commit")
    claim.hold = engine_hold
    # Operator 2026-11-08: the frozen tree's tracked state must be clean (verify_llama_cpp.sh's rule); these three old untracked
    # items, and only these, are tolerated for this row. Any other untracked entry still fails the producer's check.
    import kv_quant_27b_v10_sweep as ks
    ks.SOURCE_UNTRACKED_ALLOWLIST = {**ks.SOURCE_UNTRACKED_ALLOWLIST, "coordination/": "previously operator-approved non-build coordination artifacts"}
    if "--guard" in sys.argv:
        clean, reason = ks.common.process_guard_clean(ks.common.process_snapshot(), ks.PORT_BASE)
        print(reason)
        return 0 if clean else 5
    if "--check" in sys.argv:
        binary = ks.resolved_binary()
        source = ks.source_identity()
        first = ks.binary_identity(binary, probe=True)
        model = ks.model_identity(ks.DEFAULT_TARGET_MODEL, hash_file=True)
        valid, reason = ks.fixed_identities_valid(source, first, model)
        second = ks.binary_identity(binary, probe=True)
        repeat, repeat_reason = ks.identity_witness_matches({"binary": first}, {"binary": second})
        (D / "preflight.json").write_text(json.dumps(dict(valid=valid, reason=reason, repeated_binary_identity=repeat, repeated_reason=repeat_reason, source=source, binary=first, model=model),sort_keys=True))
        print("PREFLIGHT", valid, reason, "REPEATED-WITNESS", repeat, repeat_reason)
        return 0 if valid and repeat else 1
    if os.environ.get("FILLER_DRYRUN") == "1":
        native = Path(os.environ["FILLER_DRYRUN_DIR"]) / "native"
        out = native / "run-smoke"
        out.mkdir(parents=True, exist_ok=True)
        args = ks.parse_args(["--execute", "--output-dir", str(native)])
        binary = ks.resolved_binary()
        model = ks.model_identity(args.target_model, hash_file=True)
        plan = ks.build_plan(args, binary, model, probe=True)
        plan["runs"] = plan["runs"][:1]
        summary = ks.execute(args, binary, out, plan)
        first = (summary.get("results") or summary.get("replicates") or [{}])[0]
        (native / "SMOKE-DONE.json").write_text(json.dumps(
            {"first_status": first.get("status"), "cell": first.get("cell"), "depth": first.get("depth"),
             "records": len(first.get("records") or []), "summary_status": summary.get("status"),
             "note": "smoke = one real replicate through run_replicate; no sidecar, no matrix claim"}, sort_keys=True))
        return 0 if first.get("status") == "ok" else 1
    out_root = D / "out"
    out_root.mkdir(exist_ok=True)
    rc = ks.main(["--execute", "--output-dir", str(out_root)])  # in-process, so the allowlist above applies
    if rc == 0:
        (out_root / "COMPLETE").write_text("complete\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
