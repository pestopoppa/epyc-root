"""Bind callbacks to the new persistent owner, never the retired boundary."""
import json
from pathlib import Path

COVERAGE = Path(__file__).resolve().parent.parent
PERSISTENT = COVERAGE / "persistent-serving"
LIVE = PERSISTENT / "runs/final-01"
LOCKS = COVERAGE / "persistent-callback-locks"
SOURCE_SHA = "97d17990a584623dc3c346fbee2023757df291ec251adcc012c76447cd410710"
IDENTITIES = {"holder": (133800, 161837437), "controller": (133805, 161837443),
              "gpu": (147287, 161842751), "cpu": (147530, 161842764)}


def snapshot(legacy):
    ready = LIVE / "READY.json"
    files = [ready, LIVE / "GRANT.json", LIVE / "SERVING.json", PERSISTENT / "serve.py"]
    legacy.same_file(files[-1], SOURCE_SHA)
    data = legacy.read(ready)
    expected = {**data["native"], "holder": data["holder"], "controller": data["controller"]}
    for role, (pid, birth) in IDENTITIES.items():
        if (expected[role]["pid"], expected[role]["start_ticks"]) != (pid, birth):
            raise RuntimeError(f"persistent ready receipt changed {role} identity")
    if data["serving"] != legacy.read(files[2]) or data["grant"] != legacy.read(files[1]):
        raise RuntimeError("persistent READY, grant or provider receipts disagree")
    return {"holder": data["holder"], "controller": data["controller"], "native": data["native"],
            "providers": data["serving"], "grant": data["grant"],
            "receipts": {str(path): legacy.digest(path) for path in files}}


def prove(engine, legacy, mechanical, spec, backend):
    if (LIVE / "STOP").exists() or (LIVE / "CLEANUP.json").exists():
        raise RuntimeError("persistent owner closed")
    holder, controller = spec["holder"], spec["controller"]
    native = spec["native"][backend]
    for role, record in (("holder", holder), ("controller", controller), (backend, native)):
        pid, birth = IDENTITIES[role]
        if (record["pid"], record["start_ticks"]) != (pid, birth) or mechanical.proc_identity(pid) != record:
            raise RuntimeError(f"persistent {role} changed")
    if controller["ppid"] != holder["pid"] or native["ppid"] != controller["pid"]:
        raise RuntimeError("persistent owner hierarchy changed")
    if engine.region(True, owner_pid=holder["pid"]) != spec["grant"]:
        raise RuntimeError("persistent whole-host grant no longer matches")
    return spec["providers"][backend]


def verify_receipts(legacy, spec):
    if spec != snapshot(legacy):
        raise RuntimeError("persistent READY/source receipt changed")
