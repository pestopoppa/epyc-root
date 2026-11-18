"""Strict prospective reader and exact AK27B planning-context canary."""
from argparse import ArgumentParser
from datetime import datetime
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from .observation import *  # noqa: F403
except ImportError:
    from observation import *  # noqa: F403
sys.path.insert(0, str(HERE / "reader/scripts/vidya") if (HERE / "reader/scripts/vidya").is_dir()
                else str(HERE.parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, grade, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_gfx_observation/v1"
SOURCE = "autokernel-gfx-observation-measurement"
FILES = {"gfx-counter.json", "ggml-linkage.log", "request.json", "response.json", "server.log",
         "source-manifest.json"} | {"source/" + name for name in SOURCE_FILES}


def validate_workload(root, record):
    require(set(record["files"]) == FILES, "missing or extra raw capture")
    for name, expected in record["files"].items():
        path = root / name
        require(not path.is_symlink() and path.is_file() and digest(path) == expected,
                f"raw artifact bytes changed: {name}")
    manifest = record["source_manifest"]
    require(manifest["locator"] == "source-manifest.json"
            and manifest["sha256"] == record["files"][manifest["locator"]],
            "missing native source manifest join")
    closure = json.loads((root / manifest["locator"]).read_bytes())
    require(digest(root / manifest["locator"]) == digest(HERE / "source-manifest.json")
            and closure["research_commit"] == RESEARCH and closure["reader_revision"] == READER_REVISION
            and closure["files"] == {name: record["files"]["source/" + name] for name in SOURCE_FILES}
            and closure["files"]["gpu_counter.py"] == COLLECTOR_SHA
            and closure["files"]["verify_ggml_linkage.sh"] == LINKAGE_SHA,
            "original producer closure changed or is incomplete")
    grant = record["grant"]
    raw = dict(field.split("=", 1) for field in grant["raw"].split())
    grant_path = Path(grant["path"])
    require(grant_path.name == ROW + ".grant" and grant_path.parent.name == "grants"
            and "mi210_0" in raw.get("regions", "").split(",")
            and "gpu-quiet" in raw.get("holds", "").split(","),
            "native grant lacks device and quiet token")
    if record["mode"] == "official":
        require(grant_path == Path("/mnt/raid0/llm/tmp/compute-flags/grants") / (ROW + ".grant")
                and raw.get("kind") != "rowflow-dryrun", "official claim used a dry-run grant")
    else:
        require(grant_path.parent.parent.name == ROW and raw.get("kind") == "rowflow-dryrun"
                and raw.get("id") == ROW, "smoke claim lacks original dry-run grant")
    start = datetime.fromisoformat(record["started_at"])
    end = datetime.fromisoformat(record["ended_at"]) if "ended_at" in record else datetime.fromisoformat(now())
    grant_open, grant_close = (datetime.fromisoformat(raw[k].replace("Z", "+00:00"))
                               for k in ("start", "end"))
    require(grant_open <= start <= end <= grant_close
            and type(grant["deadline_epoch"]) is int
            and grant_open.timestamp() < grant["deadline_epoch"] <= grant_close.timestamp(),
            "native UTC outside original grant")
    cpus = record["cpus"]
    require(len(cpus) == 4 and len(set(cpus)) == 4 and all(type(c) is int and 184 <= c <= 191 for c in cpus),
            "missing granted four-CPU job placement")
    granted = set()
    for part in raw.get("cpus", raw.get("regions", "")).split(","):
        if part == "mi210_0":
            continue
        require(bool(re.fullmatch(r"[0-9]+(?:-[0-9]+)?", part)), "invalid granted CPU identity")
        bounds = list(map(int, part.split("-")))
        lo, hi = bounds[0], bounds[-1]
        require(0 <= lo <= hi <= 191, "invalid granted CPU range")
        granted.update(range(lo, hi + 1))
    require(set(cpus) <= granted, "captured CPUs exceed original grant")
    lock = record["lock_begin"]
    require(lock == record["lock_end"] and lock["path"] == str(GPU_LOCK)
            and all(type(lock[k]) is int and lock[k] > 0 for k in ("pid", "birth", "device", "inode"))
            and re.fullmatch(r"\d+", lock["fd"])
            and re.match(r"^lock:\s+\d+: FLOCK\s+ADVISORY\s+WRITE\s", lock["raw"]),
            "missing or contradictory exclusive device lock evidence")
    before, after = record["server_before"], record["server_after"]
    for snapshot in (before, after):
        vram = snapshot["kfd_vram_bytes"]
        require(snapshot["exe"] == str(SERVER) and snapshot["argv"] == argv()
                and snapshot["hip_mapping"] == {str(HIP): HIP_SHA}
                and all(type(v) is int and v >= 0 for v in vram.values()) and sum(vram.values()) > 0
                and all(type(snapshot[k]) is int and snapshot[k] > 0 for k in ("pid", "birth", "at_ns"))
                and re.fullmatch(r"[1-9][0-9]*", snapshot["bound_loopback_inode"]),
                "server identity, custody or own-PID HIP/VRAM missing")
    require(all(before[k] == after[k] for k in ("pid", "birth", "bound_loopback_inode")),
            "server was replaced during the workload")
    trace = json.loads((root / "gfx-counter.json").read_bytes())
    start_ns, end_ns = record["request_started_ns"], record["request_ended_ns"]
    result = counter_window(trace, start_ns, end_ns)
    require(trace["claim_acquired_observed_ns"] <= before["at_ns"]
            <= result["observed_window"]["start"]["host_before_ns"] < start_ns
            < end_ns < result["observed_window"]["end"]["host_after_ns"]
            <= after["at_ns"] <= trace["claim_release_observed_ns"],
            "workload and observed counter windows do not join")
    require(record[METRIC] == result[METRIC] and record["observed_window"] == result["observed_window"]
            and record["belief_measurements"] == [
                native_measurement(record, record["files"]["gfx-counter.json"], result)],
            "authored measurement differs from raw counter reduction")
    request = json.loads((root / "request.json").read_bytes())
    response = json.loads((root / "response.json").read_bytes())
    require(request == REQUEST and response.get("stop") is True
            and isinstance(response.get("content"), str) and response["content"]
            and type(response.get("tokens_predicted")) is int
            and response["tokens_predicted"] == REQUEST["n_predict"],
            "missing completed fixed request response")
    cleanup = record["server_cleanup"]
    require(type(cleanup["returncode"]) is int and all(cleanup[key] is True for key in
                ("verified_gone", "verified_listener_released", "verified_kfd_gone")),
            "missing owned-child, KFD or listener cleanup")


def load(path, *, allow_smoke=False):
    path = Path(path)
    try:
        require(path.name == "observation.json" and not path.is_symlink(), "invalid native locator")
        body = path.read_bytes()
        report = json.loads(body)
        expected = report.pop("self_sha256")
        require(seal(report) == expected, "native envelope seal mismatch")
        require(report["schema"] == SCHEMA and report["row_id"] == ROW
                and report["status"] == "observed" and (report["mode"] == "official"
                or (allow_smoke and report["mode"] == "publisher-smoke"))
                and re.fullmatch(r"native-[0-9a-f]{32}", report["run_id"])
                and report["run_id"] == path.parent.name
                and report["research_commit"] == RESEARCH and report["build_commit"] == BUILD
                and report["target"] == TARGET and report["model_sha256"] == MODEL_SHA
                and report["drafter_sha256"] == DRAFTER_SHA and "failure" not in report
                and all(report[k] is None for k in ("full_claim_coverage", "per_process_attribution",
                                                    "binary_busy_time")),
                "unknown, pre-hook, smoke or contradictory native observation")
        validate_workload(path.parent, report)
        return report, hashlib.sha256(body).hexdigest()
    except (KeyError, ValueError, TypeError, OSError, AttributeError) as exc:
        raise ProjectionError(str(exc)) from exc


def native_rows(path):
    path = Path(path).absolute()
    _, sha256 = load(path)
    return [{"path": str(path), "sha256": sha256}]


def project(row):
    path = Path(row["path"])
    record, attestation = load(path)
    if row["sha256"] != attestation:
        raise ProjectionError("native bytes changed after discovery")
    declaration, = record["belief_measurements"]
    value = declaration[METRIC]
    fields = ("measurement_id", "metric", "value", "date", "category", "metric_direction", "unit",
              "reps", "reps_basis", "protocol_id", "applicability")
    return ClaimTuple(
        **{key: declaration[key] for key in fields},
        source_kind=SOURCE, attestation_path=str(path), attestation_sha256=attestation,
        attestation_present=True, attestation_verified=True,
        claim=f"AK27B fixed Q8_0 DFlash2 request: two valid counter boundaries report {value:g} "
              f"activity-weighted seconds. {LIMIT}",
        observation={"outcome_native": f"{value:g} GFX activity-weighted seconds over the boundary-read window",
                     "decisive": False},
        extra={METRIC: value, "observed_window": record["observed_window"], "limitations": LIMIT,
               "run_id": record["run_id"], "collector_commit": RESEARCH, "build_commit": BUILD,
               "model_sha256": MODEL_SHA, "drafter_sha256": DRAFTER_SHA,
               "full_claim_coverage": None, "per_process_attribution": None, "binary_busy_time": None})


def canary(path, out, *, ledger_path=None, index_path=None):
    import loop_beliefs
    from ledger import Ledger

    out.mkdir()
    tup = project(native_rows(path)[0])
    stamp = now()
    if ledger_path is None:
        ledger_path = out / "ledger.jsonl"
        ledger_path.touch()
        index_path = out / "intake-index.yaml"
        index_path.write_text("[]\n")
    ledger = Ledger(ledger_path)
    for frame in to_frames(tup, as_of=stamp, adapter_id=ADAPTER_ID):
        ledger.append(frame)
    cid = "clm_" + tup.measurement_id
    controls = {
        "exact_ak27b": TARGET,
        "cpu": dict(TARGET, backend="cpu"),
        "other_weights": dict(TARGET, model_file="unrelated.gguf", model_sha256="0" * 64),
        "same_name_other_digest": dict(TARGET, model_sha256="0" * 64),
    }
    result = {}
    for label, target in controls.items():
        answer = loop_beliefs.prepare("autokernel.planner", target, ledger=ledger_path,
                                      index_path=index_path, known_good=out / (label + ".known-good.json"),
                                      alarm_state=out / (label + ".alarm.json"), read_log=out / "reads.jsonl")
        (out / (label + ".json")).write_bytes(canonical(answer) + b"\n")
        actual = cid in answer.get("evidence", {}).get("claim_ids", [])
        require(answer["status"] == "ready" and actual == (label == "exact_ak27b"),
                f"planner context failed for {label}")
        result[label] = actual
    return {"eligible": 1, "refused": 0, "frames": 3, "claim_id": cid,
            "grade": list(grade(tup)[:2]), "visible": result}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--canary", type=Path)
    args = parser.parse_args()
    if args.canary:
        print(json.dumps(canary(args.source, args.canary), indent=2))
    else:
        tup = project(native_rows(args.source)[0])
        print(json.dumps({"tuple": tup.__dict__, "grade": grade(tup)}, indent=2))


if __name__ == "__main__":
    main()
