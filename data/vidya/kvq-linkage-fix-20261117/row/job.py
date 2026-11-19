#!/usr/bin/env python3
"""VB-KVQ-V10-INGEST job: run the P-GPU-1 KV-quant sweep under the rowflow engine's GPU lock.

The producer is research scripts/benchmark/kv_quant_27b_v10_sweep.py (pinned worktree at
99301fa14). Binary = the production kernel store (kernels/production/gpu); the producer resolves,
hashes and ldd-verifies it itself and refuses anything else. The producer acquires the MI210 device
flock on its own; under filler_run15 the engine already holds that lock on fd 9, so this wrapper
replaces `claim.hold` with a context that PROVES the engine's ancestor holds the device-lock inode
(/proc/<pid>/fdinfo, exclusive FLOCK) and yields the producer's own HeldCpuClaim receipt. Nothing is
acquired twice and nothing is merely observed.

Modes
  --check   verify the source closure and the previously captured model identity using metadata.
  smoke     (FILLER_DRYRUN=1) one real replicate (A_f16_kv / d2k / rep1) through the producer's own
            run_replicate, no sidecar; writes $FILLER_DRYRUN_DIR/native/SMOKE-DONE.json.
  official  the full 30-launch matrix via the producer's main(); output run-<ts>/ holds summary.json
            and belief_measurements.jsonl (schema epyc.vidya.kv_quant_27b_v10_capture.v1), the exact
            file `cli.py ingest kv-quant-27b-v10-measurement` reads.
"""
import contextlib
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from functools import partial
from pathlib import Path

D = Path(__file__).resolve().parent
RES = Path("/mnt/raid0/llm/tmp/vidya-belief-substrate/kvq-ready/research")
PINNED = "99301fa149af86a6f9743d2b0405c9234ba39586"
CLOSURE_SHA256 = "ae4e57a718d9e59c310c056248d452bdf7b7c9c5b07521a244cc0f5c906abc53"
PREPARED_MODEL_SHA256 = "2c66376c4e3748fdc888539817c5e95e9b8d59ffcbb59a025beb5de088fc111d"


def pinned_json(path, expected_sha256):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise RuntimeError(f"receipt digest changed: {path}")
    return json.loads(raw)


def verify_source():
    manifest = pinned_json(D / "source-closure.json", CLOSURE_SHA256)
    head = subprocess.check_output(["git", "-C", str(RES), "rev-parse", "HEAD"], text=True).strip()
    if head != PINNED or head != manifest["base_commit"]:
        raise RuntimeError("source commit differs")
    changed = subprocess.check_output(["git", "-C", str(RES), "diff", "--name-only", "HEAD"], text=True).splitlines()
    if changed != manifest["allowed_modified"]:
        raise RuntimeError("unexpected source diff")
    for rel, expected in manifest["files"].items():
        if hashlib.sha256((RES / rel).read_bytes()).hexdigest() != expected:
            raise RuntimeError("source closure changed: " + rel)


def check_prepared_model(path, *, hash_file, identity, prepared, stat_identity):
    """Provide the preparation digest only while the model still matches its file identity."""
    if not hash_file:
        raise RuntimeError("prepared model identity requires the producer's execution path")
    try:
        if str(path) != identity["path"] or str(path.resolve(strict=True)) != identity["resolved_path"]:
            raise ValueError("model path differs from preflight")
        info = path.lstat()
        expected_stat = {key: identity[key] for key in ("dev", "inode", "bytes", "mtime_ns")}
        if (not stat.S_ISREG(info.st_mode) or stat_identity(info) != expected_stat
                or info.st_ctime_ns != prepared["model_ctime_ns"]):
            raise ValueError("model type or stat metadata differs from preparation")
    except (OSError, ValueError) as exc:
        return {"path": str(path), "stable": False, "identity_error": str(exc)}
    return {**identity,
            "identity_basis": "preflight_sha256_with_execution_stat_checks",
            "preflight_sha256": prepared["preflight_sha256"],
            "ctime_ns": info.st_ctime_ns}


def load_prepared_model(ks):
    prepared = pinned_json(D / "prepared-model.json", PREPARED_MODEL_SHA256)
    preflight = pinned_json(D / "preflight.json", prepared["preflight_sha256"])
    if (prepared["schema"] != "epyc.vidya.kvq_prepared_model.v1"
            or preflight["valid"] is not True or preflight["repeated_binary_identity"] is not True):
        raise RuntimeError("model preparation requires a passing preflight")
    identity = preflight["model"]
    valid, reason = ks.model_identity_valid(identity)
    if not valid or not re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]):
        raise RuntimeError(f"preflight model identity is invalid: {reason}")
    return partial(check_prepared_model, identity=identity, prepared=prepared,
                   stat_identity=ks.common.stat_identity)


def prove_engine_lock(claim):
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
def engine_hold(lock_path=None, *, device_id, gpu_quiet_path=None, claim):
    pid = prove_engine_lock(claim)
    receipt = claim.HeldCpuClaim({"device_id": device_id, "lock_path": str(lock_path or claim.DEVICE_LOCK),
                                  "pid": pid, "mode": "engine_held_flock"}, [lock_path or claim.DEVICE_LOCK],
                                 gpu_quiet_path=gpu_quiet_path)
    yield receipt
    if prove_engine_lock(claim) != pid:
        raise RuntimeError("engine GPU lock holder changed during the window")


def main():
    verify_source()
    sys.path.insert(0, str(RES / "scripts"))
    sys.path.insert(0, str(RES / "scripts/benchmark"))
    from kernel_rnd.autokernel.loop import claim
    claim.hold = partial(engine_hold, claim=claim, device_id=claim.DEVICE_ID)
    # Operator 2026-11-08: the frozen tree's tracked state must be clean (verify_llama_cpp.sh's rule); these three old untracked
    # items, and only these, are tolerated for this row. Any other untracked entry still fails the producer's check.
    import kv_quant_27b_v10_sweep as ks
    ks.SOURCE_UNTRACKED_ALLOWLIST = {**ks.SOURCE_UNTRACKED_ALLOWLIST, "coordination/": "previously operator-approved non-build coordination artifacts"}
    if "--guard" in sys.argv:
        clean, reason = ks.common.process_guard_clean(ks.common.process_snapshot(), ks.PORT_BASE)
        print(reason)
        return 0 if clean else 5
    ks.model_identity = load_prepared_model(ks)
    model = ks.model_identity(ks.DEFAULT_TARGET_MODEL, hash_file=True)
    valid, reason = ks.model_identity_valid(model)
    if not valid:
        print("PREPARED MODEL REFUSED", model.get("identity_error", reason))
        return 1
    if "--check" in sys.argv:
        print("PREPARED MODEL OK", model["sha256"])
        return 0
    if os.environ.get("FILLER_DRYRUN") == "1":
        native = Path(os.environ["FILLER_DRYRUN_DIR"]) / "native"
        out = native / "run-smoke"
        out.mkdir(parents=True, exist_ok=True)
        args = ks.parse_args(["--execute", "--output-dir", str(native)])
        binary = ks.resolved_binary()
        plan = ks.build_plan(args, binary, model, probe=True)
        plan["runs"] = plan["runs"][:1]
        summary = ks.execute(args, binary, out, plan)
        first = (summary.get("results") or summary.get("replicates") or [{}])[0]
        identity_valid = summary["post_execution_identity_valid"]
        status = first.get("status") if identity_valid else "post_execution_identity_refused"
        (native / "SMOKE-DONE.json").write_text(json.dumps(
            {"first_status": status, "replicate_status": first.get("status"),
             "post_execution_identity_valid": identity_valid,
             "post_execution_identity_reason": summary["post_execution_identity_reason"],
             "cell": first.get("cell"), "depth": first.get("depth"),
             "records": len(first.get("records") or []), "summary_status": summary.get("status"),
             "note": "smoke = one real replicate through run_replicate; no sidecar, no matrix claim"}, sort_keys=True))
        return 0 if status == "ok" else 1
    out_root = D / "out"
    out_root.mkdir(exist_ok=True)
    rc = ks.main(["--execute", "--output-dir", str(out_root)])  # in-process, so the allowlist above applies
    if rc == 0:
        (out_root / "COMPLETE").write_text("complete\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
