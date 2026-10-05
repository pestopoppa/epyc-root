"""Project private original DTAP report integrity; counts are descriptive only."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.dtap_timeout_report/v1"
AUTHORITY = "original_report_integrity_no_performance_or_promotion"
PROPOSITION = ("The selected original DTAP executions' reported timeout-censoring "
               "components are consistent with their recorded native terminal results: true.")
PRODUCERS = {
    "runner.py": "295cb5c7bfb48660b25c7e7ace52d227c13d5425060df64c86fa77936dabae58",
    "endpoint.py": "68c49a884b1744ad295fa708271908232fbacc451b3b4f8f2954d631e87899ba",
    "trace.py": "18dde91c2a27852a7e5c2a5281b8a5ef747c262f0d909d44a28ed609f686dfb3",
    "outcomes.py": "f4552c01eefad64e8ff7f1c4952c2e9b89890a6105f83a1ae3f379c731cd8a00",
    "env_state.py": "d3f7627c0ea2c097fdd727036803527418a4301ab9bb0dffa2b00d3606136b0f",
    "judge_guard.py": "b911cc4f978778e1f8b10d5a1c938faaacc312438cda1bacf4633b712d065216",
}
REGISTRY_SHA = "a4a4dbe4d264a1fc1572d5eff68314ce169d2990cfded1c5cfa6af6b69b44431"
EXCLUSIONS = ["inference authority", "performance", "promotion", "field robustness rates",
              "dependency completeness", "exact credential-bearing argv", "old-run reconstruction"]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate native JSON member")
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def regular(path):
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != 0o600 or before.st_size > 64 * 1024 * 1024):
        raise ValueError("native custody requires owned private regular files")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        def identity(info):
            return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns
        if identity(opened) != identity(before):
            raise ValueError("native custody file identity changed")
        raw = handle.read(64 * 1024 * 1024 + 1)
        if (len(raw) > 64 * 1024 * 1024 or identity(os.fstat(handle.fileno())) != identity(before)
                or identity(path.lstat()) != identity(before)):
            raise ValueError("native original changed during bounded read")
        return raw


def name(pin):
    value = pin["name"]
    if not isinstance(value, str) or Path(value).name != value or value in ("", ".", ".."):
        raise ValueError("native artifact pin escapes archive")
    return value


def read_pin(archive, pin):
    raw = regular(archive / name(pin))
    if digest(raw) != pin["sha256"]:
        raise ValueError("native original artifact hash mismatch")
    return raw


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("native timestamp is not UTC")
    return parsed


def trace_result(raw):
    """Verify original trace data using this trusted reader, never captured code."""
    records = [decode(line) for line in raw.splitlines() if line.strip()]
    if len(records) < 2 or records[-1]["event"] != "trace_finalize":
        raise ValueError("native trace closure missing")
    previous, root = "0" * 64, hashlib.sha256(b"dtap-trace-v1").digest()
    for index, record in enumerate(records):
        payload_sha = digest(canonical(record["payload"]))
        if record["seq"] != index + 1 or record["prev"] != previous or record["payload_hash"] != payload_sha:
            raise ValueError("native original trace chain mismatch")
        if index < len(records) - 1:
            root = hashlib.sha256(root + payload_sha.encode()).digest()
        previous = payload_sha
    final = records[-1]["payload"]
    if final["root"] != root.hex() or final["trace_id"] != records[-1]["prev"]:
        raise ValueError("native original trace root mismatch")
    starts = [row["payload"] for row in records if row["event"] == "session_start"]
    ends = [row["payload"]["result"] for row in records if row["event"] == "run_result"]
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError("native trace requires exact original start/terminal membership")
    return starts[0], ends[0], final["trace_id"]


def components(results, primary):
    total = len(results)
    timeouts = sum(row["completion_state"] == "terminal_timeout" for row in results)
    judged = sum(row["completion_state"] == "judged" for row in results)
    successes = sum(row["status"] == "ok" and row[primary] is True for row in results)
    finished = total - timeouts
    return {"primary_metric": primary,
            "metric_direction": "lower_better" if primary == "attack_success" else "higher_better",
            "total": total, "terminal_timeouts": timeouts, "other_errors": total - timeouts - judged,
            "judged": judged, "finished_non_timeout": finished, "successes": successes,
            "overall_rate": successes / total if total else None,
            "finished_rate": successes / finished if finished else None,
            "judged_rate": successes / judged if judged else None,
            "timeout_share": timeouts / total if total else None}


def read_receipt(path):
    path = Path(path)
    archive = path.parent
    for parent in reversed((archive.absolute(), *archive.absolute().parents)):
        info = parent.lstat()
        trusted_temp = (parent in (Path("/tmp"), Path("/var/tmp")) and info.st_uid == 0
                        and stat.S_IMODE(info.st_mode) == 0o1777)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid not in (0, os.getuid())
                or (stat.S_IMODE(info.st_mode) & 0o022 and not trusted_temp)):
            raise ValueError("native ancestor is symlink/nonowned/writable by another principal")
    directory = archive.lstat()
    if (not stat.S_ISDIR(directory.st_mode) or directory.st_uid != os.getuid()
            or stat.S_IMODE(directory.st_mode) != 0o700 or path.name != "receipt.json"):
        raise ValueError("native archive must be owned private original custody")
    if len(archive.name) != 32 or uuid.UUID(hex=archive.name).hex != archive.name:
        raise ValueError("native original archive is not an opaque producer UUID")
    raw = regular(path)
    record = decode(raw)
    body = dict(record)
    seal = body.pop("receipt_sha256")
    if digest(canonical(body)) != seal or record["schema"] != "epyc.dtap.timeout_report.v1":
        raise ValueError("native receipt seal/schema mismatch")
    if name(record["request"]) != "original-request.json" or name(record["terminal"]) != "original-terminal.json":
        raise ValueError("native request/terminal names must be canonical before opening")
    request = decode(read_pin(archive, record["request"]))
    terminal = decode(read_pin(archive, record["terminal"]))
    if request["schema"] != "epyc.dtap.timeout_request.v1" or terminal["schema"] != "epyc.dtap.timeout_terminal.v1":
        raise ValueError("native request/terminal schema mismatch")
    if request["capture_id"] != archive.name:
        raise ValueError("native opaque directory differs from original capture identity")
    if canonical(terminal["request"]) != canonical(record["request"]):
        raise ValueError("original terminal does not bind original request")
    if record["source_sha"] != request["source_sha"] or record["authority"] != AUTHORITY:
        raise ValueError("native source/authority mismatch")
    source_sha = request["source_sha"]
    if (not isinstance(source_sha, str) or len(source_sha) != 40
            or any(char not in "0123456789abcdef" for char in source_sha)
            or request["exclusions"] != EXCLUSIONS):
        raise ValueError("native public metadata is not the declared safe source identity/exclusion schema")
    if request["applicability"].get("mode") not in ("synthetic", "live_endpoint"):
        raise ValueError("native applicability has no supported original mode")
    pins = [record["request"], record["terminal"]]
    pins += [row["artifact"] for row in request["readset"]]
    pins += [row["artifact"] for row in terminal["runs"] if "artifact" in row]
    names = [name(pin) for pin in pins]
    if len(set(names)) != len(names) or set(names) | {"receipt.json"} != {p.name for p in archive.iterdir()}:
        raise ValueError("native original membership is not exact-once")
    for pin in pins:
        read_pin(archive, pin)
    for filename, expected in PRODUCERS.items():
        sources = [source for source in request["readset"]
                   if source["source"].endswith("/scripts/autopilot/evals/dtap/harness/" + filename)]
        if len(sources) != 1 or sources[0]["artifact"]["sha256"] != expected:
            raise ValueError("native producer source pin is not reviewed")
    registries = [source for source in request["readset"]
                  if source["source"].endswith("/scripts/autopilot/evals/dtap/cases.json")]
    if len(registries) != 1 or registries[0]["artifact"]["sha256"] != REGISTRY_SHA:
        raise ValueError("native registry source pin is not reviewed")
    for selected in request["selected"]:
        suffix = "/scripts/autopilot/evals/dtap/judges/" + selected["case_id"] + "/judge.py"
        if sum(source["source"].endswith(suffix) for source in request["readset"]) != 1:
            raise ValueError("native selected judge source membership unavailable")
    began, ended = utc(request["created_utc"]), utc(terminal["ended_utc"])
    if ended < began:
        raise ValueError("native request/terminal UTC order differs")
    value = record["timeout_reporting_integrity"]
    if value is None:
        if not terminal["diagnostics"] or not record["diagnostic"] or record["decided_proposition"]:
            raise ValueError("native diagnostic record pretends to decide a proposition")
        return record, digest(raw), request, terminal
    if value is not True or terminal["diagnostics"] or record["diagnostic"] or record["decided_proposition"] != PROPOSITION:
        raise ValueError("native report integrity assertion disagrees with original terminal")
    if terminal["observed_source_sha"] != request["source_sha"]:
        raise ValueError("native observed source HEAD differs")
    original_modules = {row["module"]: row for row in request["loaded_modules"]}
    observed_modules = {row["module"]: row for row in terminal["observed_loaded_modules"]}
    readset = {row["source"]: row["artifact"]["sha256"] for row in request["readset"]}
    package = request["harness_package"]
    if not isinstance(package, str) or package.split(".")[-1] != "harness":
        raise ValueError("native imported harness package is unspecified")
    for module, row in observed_modules.items():
        if module != package and not module.startswith(package + "."):
            raise ValueError("native loaded module is outside its declared harness package")
        relative = module[len(package):].strip(".").replace(".", "/")
        suffix = "/harness/" + relative if relative else "/harness"
        if not any(row["source"].endswith(suffix + ending) for ending in (".py", "/__init__.py")):
            raise ValueError("native loaded module source origin differs from its declared identity")
    if (not original_modules or not observed_modules
            or len(original_modules) != len(request["loaded_modules"])
            or len(observed_modules) != len(terminal["observed_loaded_modules"])
            or any(observed_modules.get(module) != row for module, row in original_modules.items())
            or any(readset.get(row["source"]) != row["sha256"] for row in observed_modules.values())):
        raise ValueError("native loaded module source/origin membership differs")
    selected = [(row["case_id"], row["arm"], row["seed"]) for row in request["selected"]]
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("native selection is empty or duplicate")
    actual, groups, primary_metrics = [], {}, {}
    for row in terminal["runs"]:
        if row["diagnostic"]:
            raise ValueError("native trace original is diagnostic")
        start, result, trace_id = trace_result(read_pin(archive, row["artifact"]))
        identity = tuple(row[key] for key in ("case_id", "arm", "seed"))
        if (tuple(start[key] for key in ("case_id", "arm", "seed")) != identity
                or tuple(result[key] for key in ("case_id", "arm", "seed")) != identity
                or canonical(result) != canonical(row["original_result"]) or trace_id != row["trace_id"]
                or canonical(start["arm_config"]) != canonical(request["config"])):
            raise ValueError("native selected identity/config/original terminal differs")
        begin_run, end_run = utc(result["started_utc"]), utc(result["ended_utc"])
        elapsed = result["elapsed_s"]
        if (not began <= begin_run <= end_run <= ended or isinstance(elapsed, bool)
                or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < 0):
            raise ValueError("native execution elapsed/UTC metadata invalid")
        failure = result["failure"] or {}
        if (request["applicability"]["mode"] == "live_endpoint"
                and result["endpoint_kind"] != "native_transport"):
            raise ValueError("native live applicability has no native transport configuration")
        state = ("judged" if result["status"] == "ok" else "terminal_timeout"
                 if failure.get("type") == "endpoint" and
                 (failure.get("detail") or {}).get("terminal_native_timeout") is True else "other_error")
        if result["completion_state"] != state or result["status"] not in ("ok", "failed"):
            raise ValueError("native original typed terminal state disagrees")
        primary = "task_success" if start["threat"] == "benign" else "attack_success"
        secondary = "attack_success" if primary == "task_success" else "task_success"
        if state == "judged" and (failure or type(result[primary]) is not bool
                                   or (result[secondary] is not None and type(result[secondary]) is not bool)):
            raise ValueError("native judged outcomes unavailable")
        if state == "judged" and result["judge_origin"] not in {
                source["source"] for source in request["readset"]
                if source["source"].endswith("/scripts/autopilot/evals/dtap/judges/" + result["case_id"] + "/judge.py")}:
            raise ValueError("native loaded judge origin is not its original selected source")
        actual.append(identity)
        key = row["case_id"] + "::" + row["arm"]
        if key in primary_metrics and primary_metrics[key] != primary:
            raise ValueError("native primary metric changed within group")
        primary_metrics[key] = primary
        groups.setdefault(key, []).append(result)
    if actual != selected:
        raise ValueError("native original selected execution membership/order differs")
    recomputed = {key: components(results, primary_metrics[key]) for key, results in groups.items()}
    if canonical(recomputed) != canonical(terminal["components"]):
        raise ValueError("native original censoring denominators/components disagree")
    return record, digest(raw), request, terminal


def native_rows(path):
    try:
        record, sha, request, terminal = read_receipt(path)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ProjectionError("DTAP native report custody refused: " + type(exc).__name__) from exc
    if record["timeout_reporting_integrity"] is None:
        return ()
    return ({"record": record, "request": request, "terminal": terminal,
             "receipt_path": str(Path(path).resolve()), "receipt_sha256": sha},)


def public_locator(path):
    """No caller-controlled parent or filename belongs in a public report."""
    path = Path(path)
    value = path.parent.name if path.name == "receipt.json" else path.name
    try:
        if len(value) == 32 and uuid.UUID(hex=value).hex == value:
            return str(uuid.UUID(hex=value))
    except ValueError:
        pass
    return "private-input:" + digest(str(path).encode())


@register("dtap-timeout-report", source_class="verifier",
          decided_proposition_field="decided_proposition")
def project_dtap_timeout_report(native):
    rows = native_rows(native["receipt_path"])
    if len(rows) != 1 or canonical(rows[0]) != canonical(native):
        raise ProjectionError("native report changed since reopening")
    record, request, terminal = native["record"], native["request"], native["terminal"]
    return ClaimTuple(measurement_id="dtap-timeout:" + record["receipt_sha256"],
                      metric="timeout_reporting_integrity", value=True,
                      date=terminal["ended_utc"], category="CANDIDATE", metric_direction="higher_better",
                      protocol_id="", claim=record["decided_proposition"],
                      decided_proposition=record["decided_proposition"], source_class="verifier",
                      source_kind=ADAPTER_ID, binding_kind="identity",
                      attestation_locator=str(uuid.UUID(hex=request["capture_id"])),
                      extra={"receipt_sha256": native["receipt_sha256"], "source_sha": request["source_sha"],
                             "components": list(terminal["components"].values()),
                             "applicability_mode": request["applicability"]["mode"],
                             "applicability_sha256": digest(canonical(request["applicability"])),
                             "exclusions": request["exclusions"]})
