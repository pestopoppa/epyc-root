"""Read an original filed EXP01 source-capture control without launching its producer.

The write-time reader checked the pinned source, model and item-set files. Here
the archived bytes re-derive the result within that recorded scope. A filed
control has four single-launch observations and no protocol or pilot verdict.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import tarfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.exp01_proxy_capture/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "exp01-proxy-capture-diagnostic"
ARCHIVE = "native-control.tar.gz"
ARMS = ("Q4KM", "IQ4KT", "IQ2XXS", "IQ2KT")
MODE = "capture-control"
INSTRUMENT = "/mnt/raid0/llm/ik_llama.cpp"
LIMITATION = ("Minimal source-capture diagnostic only; single original unit per arm. "
              "No pilot ratio/look, speed advantage, port/futility, formal gate, or combination with r3.")
MAX_BYTES = 4 << 20


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ProjectionError(reason)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _matches(data: bytes, identity: dict, path: Path) -> bool:
    return (str(path) == identity["path"] and len(data) == identity["size"]
            and _digest(data) == identity["sha256"])


def _read(path: Path) -> bytes:
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_BYTES,
             f"missing, linked or oversized filing member {path.name}")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    _require(len(data) <= MAX_BYTES, f"oversized filing member {path.name}")
    return data


def _archive(path: Path, origin: Path) -> dict[str, bytes]:
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_BYTES,
             "missing, linked or oversized native archive")
    files = {}
    total = 0
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            parts = Path(member.name).parts
            _require(parts and parts[0] == origin.name and ".." not in parts,
                     "native archive has a different root or escaped member")
            if member.isdir():
                continue
            name = "/".join(parts[1:])
            total += member.size
            _require(member.isfile() and name not in files and total <= MAX_BYTES and len(files) < 64,
                     "invalid, duplicate or oversized native archive member")
            stream = archive.extractfile(member)
            _require(stream is not None, "missing native archive member")
            files[name] = stream.read()
    return files


def _launch(files: dict[str, bytes], origin: Path, row: dict, run: dict,
            mask: set[int], previous_end: float) -> tuple[dict, bytes]:
    unit = row["unit"]
    capture = row["belief_capture"]
    allocation = run["allocation"]
    _require(row["rc"] == 0 and row["cpus"] == allocation["FILLER_CPUS"] and row["threads"] == 4,
             "failed or resource-mismatched unit")
    path = f"launches/{unit}"
    data = files[f"{path}.json"]
    _require(_matches(data, capture["launch"], origin / f"{path}.json"), "launch record changed")
    launch = json.loads(data)
    start, end = launch["started_monotonic_s"], launch["ended_monotonic_s"]
    _require(launch["schema"] == "epyc.exp01.launch.v1" and launch["unit"] == unit
             and launch["rc"] == 0 and launch["disposition"] == "complete"
             and type(launch["pid"]) is int and launch["pid"] > 0 and previous_end <= start <= end
             and run["started_at"] <= launch["started_at"] <= launch["ended_at"]
             <= min(float(allocation["FILLER_DEADLINE"]), run["started_at"] + 900),
             "failed, overlapping or out-of-window launch")
    pins = run["pins"]["artifacts"]
    libs = [pins["instrument-lib:build/ggml/src/libggml.so"],
            pins["instrument-lib:build/src/libllama.so"]]
    samples = launch["samples"]
    _require(all(sample["own_pid"] == launch["pid"] and set(sample["affinity"]) == mask
                 and start <= sample["monotonic_s"] <= end for sample in samples),
             "in-window affinity or process identity mismatch")
    _require(sum(all(lib["path"] in sample["mapped"] for lib in libs)
                 for sample in samples) >= 2
             and all(launch["mapped_artifacts"].get(lib["path"]) == lib for lib in libs),
             "missing persistent mapped instrument identities")
    for stream in ("stdout", "stderr"):
        _require(_matches(files[f"{path}.{stream}"], launch[stream], origin / f"{path}.{stream}"),
                 f"launch {stream} changed")
    return launch, files[f"{path}.stdout"]



def _speed_matches(cell: dict, value: float) -> bool:
    if len(cell["samples_ns"]) != 1 or len(cell["samples_ts"]) != 1:
        return False
    ns, sample_rate = cell["samples_ns"][0], cell["samples_ts"][0]
    if (type(ns) is not int or ns <= 0 or ns != cell["avg_ns"]
            or type(sample_rate) not in (int, float) or not math.isfinite(sample_rate) or sample_rate <= 0):
        return False
    rate = (cell["n_prompt"] + cell["n_gen"]) * 1e9 / ns
    # llama-bench writes avg_ts with six decimal places and samples_ts with six significant digits.
    return (type(value) in (int, float) and value > 0 and value == cell["avg_ts"]
            == float(f"{rate:.6f}") and sample_rate == float(f"{rate:.6g}"))


def _control_rows(filing: Path) -> tuple[ClaimTuple, ...]:
    # Completion binding identifies the single original completed control inside rowflow smoke.
    binding = json.loads(_read(filing / "completion-binding.json"))
    manifest = json.loads(_read(filing / "manifest.json"))
    pass_bytes = _read(filing / "smoke-PASS.json")
    result_bytes = _read(filing / "RESULT.json")
    # Rowflow hashes canonical JSON of the published row before resolving the glob.
    published = {key: value for key, value in manifest.items()
                 if key not in {"completed_result_sha256", "declared_result_path"}}
    published["result_path"] = manifest["declared_result_path"]
    published_bytes = json.dumps(published, sort_keys=True, separators=(",", ":")).encode()
    _require(binding["schema"] == "epyc.rowflow.completed_smoke_filing.v1"
             and binding["manifest_sha256"] == _digest(published_bytes)
             and binding["pass_sha256"] == _digest(pass_bytes)
             and binding["result_sha256"] == _digest(result_bytes), "filing completion binding differs")
    passed, result = json.loads(pass_bytes), json.loads(result_bytes)
    origin = Path(binding["result_path"]).parent
    _require(origin.is_absolute() and Path(binding["result_path"]).name == "RESULT.json"
             and binding["result_path"] == manifest["result_path"]
             and manifest["completed_result_sha256"] == binding["result_sha256"]
             and binding["id"] == manifest["id"] == passed["id"]
             and binding["engine_sha256"] == manifest["engine"]["sha256"] == passed["engine_sha256"]
             and binding["launcher_sha256"] == manifest["launcher"]["sha256"] == passed["launcher_sha256"]
             and passed["job_complete"] is True
             and passed["result_path"] in (manifest["declared_result_path"], binding["result_path"])
             and result["result_path"] == str(origin / "NATIVE.json"),
             "no matching completed source-control filing")
    files = _archive(filing / ARCHIVE, origin)
    for name in ("RUN.json", "RESULT.json", "NATIVE.json", "TERMINAL.json", "results.jsonl"):
        _require(files[name] == _read(filing / name), f"archive and filed {name} differ")
    run, terminal = (json.loads(files[name]) for name in ("RUN.json", "TERMINAL.json"))
    run_id = run["run_id"]
    allocation = run["allocation"]
    cpus = allocation["FILLER_CPUS"]
    _require(run["schema"] == "epyc.exp01.capture.v1" and run["mode"] == terminal["mode"] == MODE
             and re.fullmatch(r"[0-9a-f]{32}", run_id)
             and run_id == result["run_id"] == terminal["run_id"]
             and terminal["state"] == "complete-capture-control" and terminal["rc"] == 0
             and result["schema"] == "epyc.exp01.capture_control_result.v1"
             and result["purpose"] == "source-capture-projection-control-only"
             and result["measurement"] is False and result["state"] == "complete"
             and result["source_sha256"] == run["source_sha256"]
             and re.fullmatch(r"[0-9a-f]{64}", run["source_sha256"]),
             "wrong mode, mixed identity or incomplete control")
    _require(run["planned"] == dict(purpose="source-capture-diagnostic-only", speed_arms=list(ARMS),
                                    launches_per_arm=1, paired_items=1, pp=512, tg=128,
                                    item_selection="first original pinned item in file order",
                                    no_pilot_decision=True),
             "source-control plan differs")
    # This reader accepts the compact quarter mask written by completed source controls.
    _require(re.fullmatch(r"[0-9]{1,4}-[0-9]{1,4}", cpus)
             and allocation["FILLER_THREADS"] == "4"
             and allocation["FILLER_ID"] == binding["id"]
             and cpus == manifest["regions"] == passed["regions"], "grant allocation differs")
    first, last = (int(cpu) for cpu in cpus.split("-"))
    grant = run["grant"]
    grant_text = grant["raw"].encode()
    grant_fields = dict(field.split("=", 1) for field in grant["raw"].split())
    _require(last - first == 3 and _digest(grant_text) == grant["identity"]["sha256"]
             and len(grant_text) == grant["identity"]["size"]
             and grant_fields["id"] == binding["id"] and grant_fields["regions"] == cpus,
             "original grant identity differs")
    mask = set(range(first, last + 1))

    pins = run["pins"]
    commit = pins["trees"][INSTRUMENT]
    _require(re.fullmatch(r"[0-9a-f]{40}", commit) and set(pins["models"]) == set(ARMS),
             "missing original instrument or model pins")
    reader_path = str(origin.parent.parent / "reader.py")
    _require(re.fullmatch(r"[0-9a-f]{64}", binding["sources_sha256"][reader_path])
             and re.fullmatch(r"[0-9a-f]{64}", pins["artifacts"]["items"]["sha256"]),
             "missing original producer reader or item-set identity")
    raw = files["results.jsonl"]
    rows = [json.loads(line) for line in raw.splitlines()]
    item = json.loads(files["fixed-item.jsonl"])
    _require(re.fullmatch(r"[\w.-]+", item["id"]), "invalid fixed item identity")
    expected = [("speed", arm, f"speed-{arm}-1") for arm in ARMS]
    expected += [("quality", arm, f"q-{arm}-{item['id']}") for arm in ARMS[:2]]
    _require(len(rows) == len(expected) + 1, "extra or missing control units")
    for row in rows:
        cap = row["belief_capture"]
        _require(cap["schema"] == "epyc.exp01.unit_capture.v1" and cap["run_id"] == run_id
                 and cap["mode"] == MODE and cap["allocation"] == allocation,
                 "mixed native mode, run or allocation")
    validity = rows[0]
    instrument = validity["instrument"]
    _require(validity["unit"] == "validity" and "kind" not in validity and validity["ok"] is True
             and instrument["fixture"] is False and instrument["commit"] == commit
             and instrument["tracked_dirty"] is False and instrument["linkage_rc"] == 0
             and instrument["kt_kernel_strings"] > 0, "native instrument validity differs")

    speeds, paired = [], {}
    previous_end = 0.0
    for row, (kind, arm, unit) in zip(rows[1:], expected, strict=True):
        _require((row["kind"], row["arm"], row["unit"]) == (kind, arm, unit),
                 "extra, reordered or mixed control unit")
        model = pins["models"][arm]
        model_path = model["metadata"]["path"]
        native_arm = validity["arms"][arm]
        _require((native_arm["path"], native_arm["size"], native_arm["sha256_pinned"])
                 == (model_path, model["metadata"]["size"], model["sha256_pinned"])
                 and native_arm["mtime"] == model["metadata"]["mtime_ns"] // 10**9
                 and native_arm["arch_supported_by_instrument"] is True,
                 "native model pin differs")
        launch, stdout = _launch(files, origin, row, run, mask, previous_end)
        previous_end = launch["ended_monotonic_s"]
        exe = pins["artifacts"]["bench" if kind == "speed" else "cli"]
        args = [exe["path"], "-m", model_path]
        _require(launch["executable"] == exe, "original executable differs")
        if kind == "speed":
            _require(launch["argv"] == args + ["-p", "512", "-n", "128", "-r", "1", "-t", "4", "-o", "json"],
                     "speed invocation differs from plan")
            _require(stdout == files[f"{unit}.json"]
                     and _matches(stdout, row["belief_capture"]["raw"], origin / f"{unit}.json")
                     and row["gguf"] == model_path and row["launch"] == 1,
                     "native speed output join differs")
            native = sorted(json.loads(stdout), key=lambda cell: cell["n_gen"])
            _require(len(native) == 2 and row["pp_n"] == 512 and row["tg_n"] == 128
                     and [(cell["n_prompt"], cell["n_gen"]) for cell in native] == [(512, 0), (0, 128)]
                     and all(cell["model_filename"] == model_path and cell["n_threads"] == 4
                             and cell["build_commit"] == row["build_commit"]
                             for cell in native)
                     and re.fullmatch(r"[0-9a-f]{7,40}", row["build_commit"])
                     and commit.startswith(row["build_commit"])
                     and all(_speed_matches(cell, row[key])
                             for key, cell in zip(("pp", "tg"), native, strict=True)),
                     "native speed does not re-derive")
            speeds.append({key: row[key] for key in ("arm", "unit", "pp", "tg")})
        else:
            _require(launch["argv"] == args + ["-p", item["prompt"], "-n", "256", "--temp", "0",
                                               "--seed", "42", "-t", "4", "--no-display-prompt"]
                     and row["item"] == item["id"] and row["item_native"] == item
                     and row["item_hash"] == _digest((item["prompt"] + item["expect_regex"]).encode())[:16]
                     and row["output"] == stdout.decode()
                     and row["correct"] is bool(re.search(item["expect_regex"], row["output"])),
                     "fixed paired item or output does not re-derive")
            paired[arm] = row["correct"]

    packet = json.loads(files["NATIVE.json"])
    comparison = dict(schema="epyc.exp01.capture_diagnostic.v1", run_id=run_id, mode=MODE,
                      speed_units=speeds, paired_item=[dict(item=item["id"], control=paired["Q4KM"],
                                                          intervention=paired["IQ4KT"])],
                      limitations=LIMITATION)
    _require(packet["comparison"] == comparison and result["limitations"] == LIMITATION
             and result["fixed_paired_items"] == 1 and result["native_speed_units"] == len(speeds)
             and result["projected_observations"] == len(packet["belief_measurements"]) == len(speeds),
             "filed source-control comparison differs")
    output = []
    for speed, mapping in zip(speeds, packet["belief_measurements"], strict=True):
        model = pins["models"][speed["arm"]]
        applicability = dict(model_file=model["metadata"]["path"], model_sha256=model["sha256_pinned"],
                             backend="cpu", build_sha=commit, threads=4, run_id=run_id, scope_basis="native")
        _require(mapping == dict(
            measurement_id=f"exp01-capture:{run_id}:{speed['unit']}", metric="tg128_native_tokens_per_s",
            value=speed["tg"], date=datetime.fromtimestamp(run["started_at"], timezone.utc).date().isoformat(),
            category="CANDIDATE",
            claim=f"EXP01 source-capture diagnostic {speed['arm']} original single native tg128 unit; no performance comparison",
            metric_direction="higher_better", protocol_id="", reps=1, unit="tokens/s",
            reps_basis="scored:one independent original llama-bench launch",
            attestation_locator=str(origin / "results.jsonl"), attestation_sha256=_digest(raw),
            attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
            applicability=applicability,
            observation=dict(outcome_native="capture-diagnostic-only", outcome_reason=LIMITATION),
            extra=dict(mode=MODE, native_unit=speed, paired_item=comparison["paired_item"], limitations=LIMITATION),
        ), "write-time tuple differs from strict source-control rederivation")
        # Keep the control label visible in the planner's numeric evidence line.
        output.append(replace(ClaimTuple(**mapping), metric="capture_control_tg128_native_tokens_per_s",
                              attestation_locator=str(filing / "results.jsonl")))
    return tuple(output)


def units(path: Path) -> list[Path]:
    return [path.parent if path.is_file() else path]


def _read_control(path: Path) -> tuple[ClaimTuple, ...]:
    try:
        return _control_rows(path)
    except (OSError, EOFError, ValueError, KeyError, TypeError, AttributeError, OverflowError,
            tarfile.TarError, re.error) as exc:
        raise ProjectionError(f"invalid EXP01 filed source-control record: {exc}") from exc


def native_rows(path: Path) -> tuple[dict, ...]:
    return tuple({"filing": path, "measurement_id": row.measurement_id} for row in _read_control(path))


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    if not isinstance(native, dict) or set(native) != {"filing", "measurement_id"}:
        raise ProjectionError("EXP01 projection requires a filed source-control locator and identity")
    for row in _read_control(Path(native["filing"])):
        if row.measurement_id == native["measurement_id"]:
            return row
    raise ProjectionError("EXP01 measurement identity was absent from the filed control")
