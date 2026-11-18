"""Project a complete prospective R23-1 EOF observation on the shared carrier."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

ADAPTER_ID = "vidya.adapters.r231_eof_capture/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "r231-eof-capture"
SCHEMA = "epyc.r231_eof.native_capture.v1"
ROW = "vidya-r231-eof-native-wire-20261118-r2"
BASE = "ffc1bac82eeca6f9099e1ccd9ba49703c460a115"
UPSTREAM = "b04642061d183dff8504127dfbee1c1a8352682c"
CLI_SHA = "a90f1a24f8734ff02f293b8ab5eec38ec69574511daabcafde6bc089996cf6fb"
PINSET_SHA = "f28e4e04fb44ff1fff6e0581fdd75a9c2107324deb65d671a84049527f22ce1b"
REQUIRED_MAPS = ("libllama-cli-impl.so", "libllama.so", "libggml.so", "libggml-base.so")
_LIMIT = 16 << 20


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value)


def _require(test, reason):
    if not test:
        raise ProjectionError(f"R23-1 EOF {reason}")


def _case_plan():
    return [dict(name="verify-ggml-linkage", input_hex="", pty=False, limit_s=10),
            dict(name="cli-model-selection-eof", input_hex="", pty=False, limit_s=10),
            dict(name="compile-harness", input_hex="", pty=False, limit_s=60)] + [
        dict(name=f"{mode}-{name}", input_hex=pty_in if is_pty else simple, pty=is_pty,
             limit_s=10, expected_hex=expected)
        for mode, is_pty in (("simple", False), ("advanced", True))
        for name, simple, pty_in, expected in (
            ("eof", "", "04", ""), ("blank", "0a", "0a", "0a"), ("slash", "2f0a", "2f0a", "0a"),
            ("text", "68656c6c6f0a", "68656c6c6f0a", "68656c6c6f0a"))
    ]


def _case_stream(record, step, previous):
    _require({key: record[key] for key in step} == step, "case inputs or ordering differ")
    _require(record["state"] == "exited" and record["cleanup"] is True
             and type(record["pid"]) is int and record["pid"] > 0
             and math.isfinite(record["ended_monotonic"])
             and previous <= record["started_monotonic"] <= record["ended_monotonic"]
             and record["ended_monotonic"] - record["started_monotonic"] <= step["limit_s"] + 2,
             "case process interval, disposition or cleanup differs")
    raw = base64.b64decode(record["raw_output_b64"], validate=True)
    _require(len(raw) <= 1 << 20 and record["raw_output_sha256"] == _digest(raw),
             "case original output digest differs")
    expected_rc = 1 if step["name"] == "cli-model-selection-eof" else 0
    _require(type(record["rc"]) is int and record["rc"] == expected_rc, "case exit status differs")
    return raw


def _console_matches(output, step):
    marker = b"RESULT more="
    expected = marker + b"0 hex=" + step["expected_hex"].encode()
    allowed = {expected}
    if step["name"] == "advanced-slash":
        allowed.add(b"/\x08/\x08 \x08" + expected)
    lines = output.rstrip(b"\r\n").splitlines()
    return len(lines) > 0 and output.count(marker) == 1 and lines[-1] in allowed


def _maps(record, executable, digest, libraries, pins, cpus):
    process = record["process"]
    _require(str(executable) == process["executable"] == record["argv"][0]
             and digest == record["declared_executable_sha256"] == process["executable_sha256"]
             and process["affinity"] == cpus and re.fullmatch(r"[0-9]+", process["proc_start_ticks"]),
             "live executable, process birth or affinity differs")
    mapped = process["runtime_maps"]
    _require(bool(mapped) and all(
        pins.get(item["path"]) == item["sha256"] and _sha(item["sha256"])
        and type(item["inode"]) is int and item["inode"] > 0
        for item in mapped), "mapped library custody differs")
    _require(all(any(Path(item["path"]).name.startswith(library) for item in mapped)
                 for library in libraries), "required live mapped library missing")


def _verify(envelope):
    _require(set(envelope) == {"payload", "sha256"}, "original native envelope missing")
    record = envelope["payload"]
    _require(envelope["sha256"] == _digest(json.dumps(record, sort_keys=True,
                                                      separators=(",", ":")).encode()),
             "native payload seal differs")
    _require(record["schema"] == SCHEMA and record["id"] == ROW
             and re.fullmatch(r"[a-f0-9]{32}", record["run_id"])
             and record["mode"] == "native" and record["status"] == "COMPLETE"
             and record["model_loaded"] is False and record["inference_executed"] is False
             and record["unstarted"] == [], "smoke, historical, incomplete or wrong-mode record")
    planned = _case_plan()
    _require(record["plan"] == planned and len(record["records"]) == len(planned),
             "complete fixed case plan differs")
    grant = record["grant"]
    cpus = grant["cpus"]
    sectors = []
    for span in grant["regions"].split(","):
        first, _, last = span.partition("-")
        start, end = int(first), int(last or first)
        _require(0 <= start <= end <= 4095, "grant region differs")
        sectors.extend(range(start, end + 1))
    raw_grant = grant["original"].encode()
    fields = dict(pair.split("=", 1) for pair in raw_grant.decode().split())
    starts = datetime.fromisoformat(fields["start"].replace("Z", "+00:00")).timestamp()
    ends = datetime.fromisoformat(fields["end"].replace("Z", "+00:00")).timestamp()
    _require(grant["row"] == fields["id"] == ROW and grant["regions"] == fields["regions"]
             and "dryrun" not in fields.get("kind", "") and "dryrun" not in fields.get("schema", "")
             and len(cpus) == 4 and cpus == sorted(set(sectors))
             and grant["sha256"] == _digest(raw_grant)
             and grant["deadline"] == ends - 90
             and starts <= record["started_at"] <= record["ended_at"] <= record["stop_at"]
             == min(grant["deadline"], record["started_at"] + 300),
             "grant, resources or terminal window differ")
    pins = record["pins"]
    _require(_digest(json.dumps(pins, sort_keys=True, separators=(",", ":")).encode())
             == PINSET_SHA, "prospectively filed input and custody pin set differs")
    bindir = Path(pins["binary_dir"])
    cli = bindir / "llama-cli"
    build = pins["original_closure"]
    compiler = pins["compiler"]
    sources = pins["sources"]
    _require(pins["parent"] == BASE and pins["upstream_merge"] == UPSTREAM and build[str(cli)] == CLI_SHA
             and sources["original-manifest.json"] == pins["original_manifest_sha256"]
             and compiler["current_sha256"] == pins["current_tools"][compiler["current_path"]]
             and all(_sha(digest) for group in (build, sources, pins["current_tools"])
                     for digest in group.values())
             and _sha(compiler["historical_sha256"]) and _sha(record["console_harness_sha256"]),
             "declared source, compiler or candidate closure differs")
    mock = record["mock"]
    _require(mock["host"] == "127.0.0.1" and 0 < mock["port"] <= 65535 and mock["cleanup"] is True
             and mock["runner_sha256"] == sources["capture.py"] and ["GET", "/v1/models"] in mock["requests"]
             and all(method == "GET" and path in ("/health", "/v1/models", "/props")
                     for method, path in mock["requests"]), "loopback mock requests, identity or cleanup differ")

    previous = 0
    for entry, step in zip(record["records"], planned, strict=True):
        raw = _case_stream(entry, step, previous)
        previous = entry["ended_monotonic"]
        name = step["name"]
        if name == "verify-ggml-linkage":
            _require(entry["argv"][0] == "/bin/bash"
                     and Path(entry["argv"][1]).name == "verify_ggml_linkage.sh"
                     and entry["argv"][2:] == [str(cli), str(bindir)]
                     and entry["declared_executable_sha256"] == pins["current_tools"]["/bin/bash"],
                     "linkage verifier invocation differs")
        elif name == "cli-model-selection-eof":
            _require(b"Select model by number" in raw and entry["argv"][1:] == [
                "--server-base", f"http://127.0.0.1:{mock['port']}", "--simple-io"], "CLI behavior differs")
            _maps(entry, cli, CLI_SHA, REQUIRED_MAPS, build, cpus)
        elif name == "compile-harness":
            console = Path(entry["argv"][-1])
            _require(entry["argv"][0] == compiler["current_path"]
                     and entry["declared_executable_sha256"] == compiler["current_sha256"]
                     and entry["argv"][1] == "-std=c++17" and Path(entry["argv"][2]).name == "harness.cpp"
                     and entry["argv"][3:-1] == ["-L" + str(bindir), "-Wl,-rpath," + str(bindir),
                                                 "-Wl,--no-as-needed", "-lllama-common", "-o"]
                     and console.name == "console-harness" and console.parent.name == record["run_id"],
                     "fresh compiler or harness invocation differs")
        else:
            _require(_console_matches(raw, step)
                     and entry["argv"][1:] == [name.partition("-")[0]],
                     "console output or invocation differs")
            _maps(entry, console, record["console_harness_sha256"], ("libllama-common.so",), build, cpus)
    _require(previous - record["records"][0]["started_monotonic"]
             <= record["ended_at"] - record["started_at"] + 0.25,
             "monotonic case span exceeds the captured wall-clock window")
    return record


def units(path):
    path = Path(path)
    return [path] if path.is_file() else sorted(path.glob("native/*/NATIVE.json"))


def native_rows(path):
    return ({"path": str(path)},)


@register(SOURCE_KIND)
def project(native):
    try:
        path = Path(native["path"])
        _require(path.is_file() and not path.is_symlink(), "original seal missing")
        with path.open("rb") as stream:
            original = stream.read(_LIMIT + 1)
        _require(len(original) <= _LIMIT, "original seal exceeds reader bound")
        record = _verify(json.loads(original))
    except (KeyError, TypeError, ValueError, IndexError, OSError) as error:
        raise ProjectionError(f"R23-1 EOF malformed native seal: {error}") from error
    case_count = len(record["records"]) - 2
    return ClaimTuple(
        measurement_id=f"r231-eof:{record['run_id']}", metric="r231_eof_verified_behavior_cases",
        value=case_count, date=datetime.fromtimestamp(record["ended_at"], timezone.utc).date().isoformat(),
        category="CANDIDATE", metric_direction="higher_better", unit="cases", protocol_id="", reps=1,
        reps_basis="one complete bounded original capture", attestation_path=str(path),
        attestation_locator=str(path), attestation_sha256=_digest(original),
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"consumer": "autokernel.planner"},
        claim="Pinned R23-1 Linux CLI and linked console verified nine model-free behavior cases, "
              "including loopback model-selection EOF and simple/PTY EOF, blank, slash and text. "
              "Scope is CLI/console behavior only.",
        observation={"outcome_native": "model-free CLI/console cases complete"},
        extra={"adapter": ADAPTER_ID, "base": BASE, "upstream_merge": UPSTREAM,
               "cli_sha256": CLI_SHA, "run_id": record["run_id"], "cpus": record["grant"]["cpus"]},
    )


def frames_for_path(path, *, as_of):
    return to_frames(project({"path": str(path)}), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)
