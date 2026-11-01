#!/usr/bin/python3
"""Model-free, source-bound v14 command fixture; never a science result."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def write(path: Path, obj: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return hashlib.sha256(data).hexdigest()


def digest_block(seed: bytes) -> str:
    block = seed
    h = hashlib.sha256()
    for i in range(64):
        block = hashlib.sha256(block + i.to_bytes(4, "little")).digest()
        h.update(block)
    return h.hexdigest()


def proc_birth(pid: int) -> int:
    return int(Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()[19])


def child_main(event_path: Path, stop_path: Path) -> int:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    # A deterministic first compute becomes visible before the parent writes the
    # qualification event; then remain live so active STOP can prove cleanup.
    first = digest_block(b"SPEC-GRAM3-r2-qualification-fixture")
    write(event_path, {"first_compute_sha256": first, "pid": os.getpid(),
                       "birth_ticks": proc_birth(os.getpid()), "done": True})
    turn = 0
    while not stop_path.exists():
        digest_block(first.encode() + turn.to_bytes(8, "little"))
        turn += 1
        time.sleep(0.01)
    return 0


def stop_child(p: subprocess.Popen[bytes]) -> None:
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=3)
    if p.poll() is None or Path(f"/proc/{p.pid}").exists():
        raise RuntimeError(f"fixture child pid={p.pid} did not drain")


def main() -> int:
    phase = os.environ.get("FILLER_QUAL_PHASE", "")
    if phase not in ("normal", "cutoff"):
        raise RuntimeError(f"bad fixture phase {phase!r}")
    if Path(__file__).resolve() != Path(os.environ["FILLER_QUAL_FIXTURE"]).resolve():
        raise RuntimeError("fixture file differs from keeper-bound source")
    manifest = json.loads(Path(os.environ["WS58_MANIFEST_PATH"]).read_text())
    if type(manifest.get("production")) is not bool or manifest["production"] is not False:
        raise RuntimeError("model-free command fixture requires explicit production=false")
    nonce = os.environ["WS58_QUAL_NONCE"]
    row_id = os.environ["FILLER_ID"]
    work_unit = manifest["command"]["work_unit"]
    manifest_sha = manifest["request_manifest_sha256"]
    results = Path(os.environ["FILLER_RESULTS_DIR"])
    proof_path = Path(os.environ["WS58_QUAL_PROOF"])
    flags = Path(os.environ["FILLER_FLAGS_DIR"])
    stop_path = Path(os.environ["FILLER_STOPFILE"])
    child_event = results / f"child-first-{phase}.json"
    first_started = time.monotonic()
    child = subprocess.Popen([sys.executable, "-I", "-B", str(Path(__file__).resolve()),
                              "--child", str(child_event), str(stop_path)],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True)
    first_deadline = time.monotonic() + 20
    while not child_event.is_file() and time.monotonic() < first_deadline:
        if child.poll() is not None:
            raise RuntimeError("fixture compute child exited before first event")
        time.sleep(0.01)
    if not child_event.is_file():
        stop_child(child)
        raise RuntimeError("fixture first compute timed out")
    native = json.loads(child_event.read_text())
    wall = max(time.monotonic() - first_started, 1e-6)
    first = {
        "ok": True, "scope": "COMMAND_NATIVE",
        "manifest_sha256": manifest_sha,
        "work_unit": work_unit,
        "work_completed": 1,
        "wall_s": wall,
        "measured_work_units_per_s": 1 / wall,
    }

    if phase == "normal":
        stop_child(child)
        result = results / "QUAL-RESULT.json"
        result_sha = write(result, {"complete": True, "phase": phase,
                                    "first_request": first,
                                    "first_compute_sha256": json.loads(child_event.read_text())["first_compute_sha256"]})
        proof = {"id": row_id, "nonce": nonce, "phase": phase,
                 "observed_cpus": sorted(os.sched_getaffinity(0)),
                 "first_request": first,
                 "result_writer": {"ok": True, "result_path": str(result), "sha256": result_sha},
                 "disk": {"job_floor_gib": manifest["job_floor_gib"]},
                 "children_drained": child.poll() is not None}
        write(proof_path, proof)
        return 0

    if os.environ.get("WS58_QUAL_ACTIVE_STOP") == "1":
        event_path = Path(os.environ["WS58_QUAL_CUTOFF_EVENT"])
        qdir = flags / "qual" / nonce
        if event_path != qdir / "cutoff-event.json":
            stop_child(child)
            raise RuntimeError("active cutoff event path is not nonce-bound")
        event = {"id": row_id, "nonce": nonce, "phase": "cutoff",
                 "native_first_event": True, "native_pid": child.pid,
                 "native_birth_ticks": native["birth_ticks"], "first_request": first}
        write(event_path, event)
        active_deadline = time.monotonic() + 90
        while not stop_path.exists() and time.monotonic() < active_deadline:
            if child.poll() is not None:
                raise RuntimeError("native child exited before active STOP")
            time.sleep(0.01)
        stop_observed = stop_path.exists()
        if not stop_observed:
            stop_child(child)
            raise RuntimeError("canonical qualifier did not deliver active STOP")
    else:
        # Non-production qualification uses the canonical immediate-deadline
        # path. Still perform first compute and drain the child before rc=75.
        stop_observed = False
        deadline = float(os.environ.get("FILLER_DEADLINE", "0"))
        if time.time() < deadline:
            stop_child(child)
            raise RuntimeError("fixture cutoff expected deadline to be reached")

    stop_child(child)
    partial = results / "PARTIAL.json"
    write(partial, {"partial": True, "unknown_disposition": "UNKNOWN",
                    "stop_observed": stop_observed, "first_request": first})
    proof = {"id": row_id, "nonce": nonce, "phase": phase,
             "observed_cpus": sorted(os.sched_getaffinity(0)),
             "first_request": first, "partial": True,
             "stop_observed": stop_observed,
             "deadline_reached": not stop_observed,
             "unknown_disposition": "UNKNOWN",
             "children_drained": child.poll() is not None}
    write(proof_path, proof)
    return 75


if len(sys.argv) > 1 and sys.argv[1] == "--child":
    raise SystemExit(child_main(Path(sys.argv[2]), Path(sys.argv[3])))
raise SystemExit(main())
