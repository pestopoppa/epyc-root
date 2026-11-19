"""Replay the prospective official EXP01 writer and rowflow custody."""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import re
import shlex
import shutil
import statistics
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from claim_tuple import ClaimTuple, ProjectionError

from .exp01_proxy_capture import ARMS, INSTRUMENT, OFFICIAL_SOURCE_KIND, _digest, _matches, _require, _speed_matches

MARKER = "official-completion-binding.json"
ARCHIVE = "native-official.tar.gz"
SCHEMA = "epyc.rowflow.completed_exp01_official_filing.v1"
MODE = "official"
FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
PAIRS = tuple(zip(ARMS[::2], ARMS[1::2], strict=True))
LIBRARIES = ("build/ggml/src/libggml.so", "build/src/libllama.so")
STAT_KEYS = ("size", "dev", "ino", "mtime_ns", "ctime_ns")
RUN_MEMBERS = ("RUN.json", "TERMINAL.json", "results.jsonl", "SUMMARY.json", "linkage.log")
ALLOCATOR_MEMBERS = {
    "grant.original": "grant",
    "grant-ended.original": "ended",
    "allocator-complete.original": "complete",
}
GRANT_COPY_SOURCES = {"allocator-original", "RUN.grant.raw"}
ASSET_MEMBERS = {
    "original-fixed-items.jsonl": "items",
    "recovery-seal.json": "recovery_seal",
    "recovery-terminal.json": "recovery_terminal",
    "tooling-manifest.json": "tooling_manifest",
}
FIXED_MEMBERS = {*RUN_MEMBERS, *ALLOCATOR_MEMBERS, *ASSET_MEMBERS,
                 "ready-manifest.json", "RESULT.json", "SOURCE.json"}
SOURCE_MEMBERS = {
    "PINS.json", "bench.sh", "capture.py", "cli.sh", "identity.py", "job_r3.sh",
    "launch.sh", "launch_capture.py", "look.py", "models.env", "pilot_r3_job.sh",
    "prepare.py", "quality.py", "runner.py", "spec.json",
}
# These are the R2 producer implementations whose semantics this reader replays.
WRITER_DIGESTS = {
    "bench.sh": "88f201329a8c7d851bef3c9002c90a331c7c1adc37d8f1e26dc0336206a19f73",
    "capture.py": "143e24c690b769efbce807ca01a38358b4436ad101c4ff218964224fb14f6962",
    "cli.sh": "efad0561e9ddaf1aa9e35d4b8aa1c8d0adccf5c65562571fb47d3c174f03aa93",
    "identity.py": "38148f87f49914febe154c0f12fef53b4c891bc9a56f7ac9926dcaee410b75b0",
    "job_r3.sh": "dbba2fdc3116a6f08cd5d1e8d638f51100bc1b0e04a67689a659e3f969c8c3ef",
    "launch_capture.py": "9603223f69aadc76bac98265444119860e862eeabcd08fe35c95d61754ac67c1",
    "look.py": "7e06ae391f5fd3348a1ffdf5ea84c62e590daca30149ad41b8f8a36c52316c76",
    "pilot_r3_job.sh": "9e1084e5c31c577e491b35f1024c20cae83c14f1892677e56dc7df9dba32a79f",
    "quality.py": "30ee6916d19d069af718584d87cded9f186dd1e4f715ceee3b2335acab01666e",
    "runner.py": "c72cad093207f48676ff46375dd0da37636531839307989379350153145a8749",
}
ITEMS_DIGEST = "96dc98cf6b2cfdd65897f1deaf2b6f8481225d013851262cf08d6171f150fdbc"
INSTRUMENT_SHA = "c04881fc0f31dae5f8ec59c1d683889f0c9dfa11"
TOOL_DIGESTS = {
    "bench": "58194ccf81d06dd66051bc6bfcb6345556a23cd35bd0df9fcc56a04a5c02af55",
    "cli": "34ce38ab3077b64daeb87c3b3bee5327103859f27c7248bda04f046b63953fe8",
    "linkage_verifier": "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33",
}
LIMITATION = "Prospective CPU proxy pilot observation. Operational looks and the fixed quality slice are exploratory."
MAX_MEMBER_BYTES = 32 << 20
MAX_ARCHIVE_BYTES = 192 << 20
MAX_ARCHIVE_ENTRIES = 240


def _unique_fields(fields):
    result = dict(fields)
    _require(len(result) == len(fields), "duplicate fields in original record")
    return result


def _json(data):
    return json.loads(data, object_pairs_hook=_unique_fields)


def _canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _zero(value):
    return type(value) is int and value == 0


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _identity(record, path=None):
    name = Path(record["path"])
    _require(name.is_absolute() and str(name) == record["path"] and ".." not in name.parts
             and (path is None or name == path)
             and all(type(record[key]) is int and record[key] >= 0 for key in STAT_KEYS)
             and _sha(record["sha256"]), f"invalid original artifact identity: {name}")


def _read(path, limit):
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
             f"missing, linked or oversized official filing member {path.name}")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    _require(len(data) <= limit, f"oversized official filing member {path.name}")
    return data


def _allowed_member(name):
    return (name in FIXED_MEMBERS or name in {f"source/{key}" for key in SOURCE_MEMBERS}
            or re.fullmatch(r"speed-(Q4KM|IQ4KT|IQ2XXS|IQ2KT)-[1-3]\.(json|err)", name)
            or re.fullmatch(r"launches/(speed-(Q4KM|IQ4KT|IQ2XXS|IQ2KT)-[1-3]"
                            r"|q-(Q4KM|IQ4KT)-[A-Za-z0-9_.-]{1,60})\.(json|stdout|stderr)", name))


class _TarMember(tarfile.TarInfo):
    def _proc_member(self, archive):
        # Refuse extended headers before tarfile can read an unbounded metadata payload.
        _require(self.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE),
                 "non-regular official archive member")
        return super()._proc_member(archive)


def _archive(path):
    _require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_ARCHIVE_BYTES,
             "missing, linked or oversized official native archive")
    files = {}
    seen = set()
    total = 0
    with tarfile.open(path, "r|gz", tarinfo=_TarMember) as archive:
        for member in archive:
            name = member.name
            _require(name not in seen and len(seen) < MAX_ARCHIVE_ENTRIES,
                     "duplicate or excessive official archive entries")
            seen.add(name)
            if member.isdir():
                _require(name in {"source", "launches"} and member.size == 0,
                         "unexpected official archive directory")
                continue
            total += member.size
            _require(_allowed_member(name) and 0 <= member.size <= MAX_MEMBER_BYTES
                     and total <= MAX_ARCHIVE_BYTES, f"invalid official archive member: {name}")
            with archive.extractfile(member) as stream:
                data = stream.read(member.size + 1)
            _require(len(data) == member.size, f"truncated official archive member: {name}")
            files[name] = data
    return files


def _fields(text):
    return _unique_fields([tuple(token.split("=", 1)) for token in text.split()])


def _epoch(text, fmt="%Y-%m-%dT%H:%M:%SZ"):
    dt = datetime.strptime(text, fmt)
    _require(dt.strftime(fmt) == text, "noncanonical allocator timestamp")
    return dt.replace(tzinfo=timezone.utc).timestamp()


def _file_map(binding, manifest, report, run):
    rid = binding["id"]
    _require(isinstance(rid, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", rid),
             "invalid official allocator row ID")
    packet, origin = Path(manifest["scratch_root"]), Path(report["attempt"])
    _require(packet.is_absolute() and ".." not in packet.parts
             and origin.parent == packet / "official"
             and str(origin) == report["attempt"] and re.fullmatch(r"attempt-[a-z0-9_]+", origin.name)
             and manifest["result_path"] == str(origin.parent / "RESULT.json")
             and manifest["stop_file"] == str(packet / "STOP")
             and manifest["launcher"]["path"] == str(packet / "launch.sh")
             and manifest["published_from"] == str(packet / "spec.json")
             and manifest["schema"] == "epyc.row.v3" and manifest["id"] == report["unit_id"] == rid
             and manifest["lineage"] == "vidya-exp01-prospective-official-source"
             and manifest["lane"] == "cpu" and manifest["regions"] == "any-cpu-quarter"
             and manifest["shape"] == "quarter" and manifest["resumable"] is False
             and manifest["result_format"] == "json" and manifest["unit_key"] == "native_units"
             and _sha(manifest["engine"]["sha256"])
             and report["mode"] == binding["mode"] == MODE,
             "official ready manifest or RESULT custody differs")
    locations = {name: origin / name for name in RUN_MEMBERS}
    locations.update({name: FLAGS / "grants" / f"{rid}.{suffix}"
                      for name, suffix in ALLOCATOR_MEMBERS.items()})
    locations.update({name: Path(run["pins"]["artifacts"][key]["path"])
                      for name, key in ASSET_MEMBERS.items()})
    locations.update({"ready-manifest.json": FLAGS / "ready" / f"{rid}.json",
                      "RESULT.json": origin.parent / "RESULT.json", "SOURCE.json": packet / "SOURCE.json"})
    return origin, locations


def _allocation(files, manifest, run, terminal, binding, origin):
    rid = binding["id"]
    alloc = run["allocation"]
    cpus = alloc["FILLER_CPUS"]
    _require(re.fullmatch(r"[0-9]{1,4}-[0-9]{1,4}", cpus) and alloc["FILLER_THREADS"] == "24",
             "official allocation must be a 24-thread CPU quarter")
    first, last = map(int, cpus.split("-"))
    _require(0 <= first <= last <= 4095 and last - first == 23 and cpus == f"{first}-{last}"
             and set(alloc) == {"FILLER_ID", "FILLER_CPUS", "FILLER_THREADS", "FILLER_DEADLINE"}
             and alloc["FILLER_ID"] == rid, "official allocation identity differs")
    mask = list(range(first, last + 1))
    grant = run["grant"]
    grant_bytes = files["grant.original"]
    grant_path = FLAGS / "grants" / f"{rid}.grant"
    _identity(grant["identity"], grant_path)
    fields = _fields(grant_bytes.decode())
    _require(grant_bytes == grant["raw"].encode() and _matches(grant_bytes, grant["identity"], grant_path)
             and fields.get("id", rid) == rid and fields["regions"] == cpus,
             "original allocator grant differs from RUN")
    start, end = (_epoch(fields[key], "%Y-%m-%dT%H:%MZ") for key in ("start", "end"))
    ended = _fields(files["grant-ended.original"].decode())
    complete_parts = files["allocator-complete.original"].decode().split()
    _require(complete_parts and complete_parts[0] == "complete"
             and ended["rc"] == "0" and ended["reason"] == "complete"
             and ended["job_id"] == rid and ended["regions"] == cpus and ended["step"] == "job-run"
             and ended["owner"] == manifest["owner"] and int(ended["estimated_wall_s"]) == manifest["estimate_s"],
             "allocator did not report original official completion")
    complete = _fields(" ".join(complete_parts[1:]))
    _require(set(complete) == {"time", "id"} and complete["id"] == rid,
             "allocator completion marker identifies a different row")
    engine_start, engine_end, complete_at = (_epoch(value) for value in
                                              (ended["started"], ended["time"], complete["time"]))
    plan = run["planned"]
    planned_end = plan["launch_deadline"]
    deadline = int(alloc["FILLER_DEADLINE"])
    started_at, ended_at = run["started_at"], terminal["ended_at"]
    _require(all(_finite(value) for value in (started_at, ended_at, planned_end))
             and _epoch(manifest["published_at"]) <= engine_start
             and start <= engine_start <= started_at <= ended_at <= planned_end <= deadline == end - 90
             and ended_at < engine_end + 1 and engine_start <= engine_end <= complete_at <= end
             and plan["stop_file"] == str(origin / "STOP")
             and type(plan["cap_s"]) is int and 0 < plan["cap_s"] <= 5400
             and planned_end <= started_at + plan["cap_s"],
             "official timing, STOP path or authorized grant window differs")
    return mask, engine_start


def _metadata(pin):
    return {"path": pin["path"], **{key: pin[f"st_{key}"] for key in STAT_KEYS}}


def _assets(files, manifest, run, validity):
    source_bytes = files["SOURCE.json"]
    inventory = _json(source_bytes)
    packet = Path(manifest["scratch_root"])
    _require(_digest(source_bytes) == run["source_sha256"] and set(inventory) == SOURCE_MEMBERS
             and all(inventory[name] == _digest(files[f"source/{name}"]) for name in inventory)
             and all(inventory[name] == digest for name, digest in WRITER_DIGESTS.items())
             and inventory["look.py"] == run["planned"]["look_source"]
             and inventory["launch.sh"] == manifest["launcher"]["sha256"],
             "unsupported or changed original official source inventory")
    pins = run["pins"]
    a = pins["artifacts"]
    _require(_json(files["source/PINS.json"]) == pins and pins["trees"] == {INSTRUMENT: INSTRUMENT_SHA}
             and set(pins["models"]) == set(ARMS), "original producer instrument or model pins differ")
    for record in a.values():
        _identity(record)
    for name, pin_key in ASSET_MEMBERS.items():
        record = a[pin_key]
        _require(_matches(files[name], record, Path(record["path"])), f"original {pin_key} bytes differ")
    for name, pin_key in (("models.env", "modelset"), ("job_r3.sh", "producer")):
        _require(_matches(files[f"source/{name}"], a[pin_key], packet / name),
                 f"original {pin_key} bytes differ")

    seal = _json(files["recovery-seal.json"])
    recovery = _json(files["recovery-terminal.json"])
    recovery_pin = seal["custody"]["TERMINAL.json"]
    _require(seal["schema"] == "epyc.exp01.input_recovery_seal.v1" and seal["state"] == "complete-sealed"
             and set(seal["outputs"]) == {*ARMS, "imatrix.dat"}
             and recovery["schema"] == "epyc.exp01.input_recovery_receipt.v1"
             and recovery["mode"] == MODE and recovery["state"] == "complete-unsealed" and _zero(recovery["rc"])
             and seal["continuation"]["run_id"] == recovery["run_id"]
             and seal["continuation"]["row_id"] == recovery["row_id"]
             and _finite(recovery["ended_at"]) and recovery["ended_at"] <= run["started_at"]
             and _matches(files["recovery-terminal.json"],
                          {**_metadata(recovery_pin), "sha256": recovery_pin["sha256"]},
                          Path(recovery_pin["path"])), "recovery seal and original terminal differ")
    tool = _json(files["tooling-manifest.json"])
    for name, key in [("ITEMS", "items"), *((Path(rel).name, f"instrument-lib:{rel}") for rel in LIBRARIES)]:
        _require(a[key] == {**_metadata(tool[name]), "sha256": tool[name]["sha256"]},
                 f"recovery tooling pin differs: {name}")
    _require(all(a[name]["sha256"] == digest for name, digest in TOOL_DIGESTS.items()),
             "approved reference CLI, bench or linkage verifier digest differs")
    for name in ("bench", "cli"):
        _identity(a[name], Path(INSTRUMENT) / f"build/bin/llama-{name}")
    libs = {a[f"instrument-lib:{rel}"]["path"]: a[f"instrument-lib:{rel}"] for rel in LIBRARIES}
    _require(set(libs) == {str(Path(INSTRUMENT) / rel) for rel in LIBRARIES}
             and {name for name in a if name.startswith("instrument-lib:")}
             == {f"instrument-lib:{rel}" for rel in LIBRARIES}, "instrument library pin set differs")

    instrument = validity["instrument"]
    _require(validity.get("unit") == "validity" and "kind" not in validity and validity["ok"] is True
             and validity["why"] == [] and set(validity["arms"]) == set(ARMS)
             and instrument["tree"] == INSTRUMENT and instrument["commit"] == INSTRUMENT_SHA
             and instrument["fixture"] is False and instrument["tracked_dirty"] is False
             and _zero(instrument["linkage_rc"]) and type(instrument["kt_kernel_strings"]) is int
             and instrument["kt_kernel_strings"] > 0, "official instrument validity differs")
    linkage = files["linkage.log"].decode()
    _require(f"binary : {a['bench']['path']}" in linkage.splitlines()
             and f"expect : libraries under {INSTRUMENT}/build" in linkage.splitlines()
             and not re.search(r"^  BAD ", linkage, re.MULTILINE)
             and all(re.search(rf"^  OK +{re.escape(Path(path).name)} +-> +{re.escape(path)}$",
                               linkage, re.MULTILINE) for path in libs)
             and "ACCEPTED: monolithic ik libggml; all inspected libs inside " + INSTRUMENT + "/build"
             in linkage.splitlines() and re.search(r"^ +libggml-base.so seen +: 0\b", linkage, re.MULTILINE),
             "original static instrument linkage log differs")

    _require(a["items"]["sha256"] == ITEMS_DIGEST, "original pinned 24-item workload differs")
    expected_modelset = {"REQUIRE": " ".join(ARMS), "ITEMS": a["items"]["path"], "ITEMS_SHA": ITEMS_DIGEST}
    for arm in ARMS:
        model, sealed = pins["models"][arm], seal["outputs"][arm]
        meta, native = model["metadata"], validity["arms"][arm]
        original = recovery["outputs"][arm]
        _identity({**meta, "sha256": model["sha256_pinned"]})
        _require(meta == _metadata(sealed) == _metadata(original)
                 and meta["size"] > 0 and model["sha256_pinned"] == sealed["sha256"]
                 and original.get("sha256", sealed["sha256"]) == sealed["sha256"]
                 and native["path"] == meta["path"] and native["exists"] is True
                 and native["size"] == meta["size"] and native["mtime"] == meta["mtime_ns"] // 10**9
                 and native["sha256_pinned"] == sealed["sha256"]
                 and native["arch_supported_by_instrument"] is True and native["arch"] == "qwen35moe"
                 and "read_error" not in native, f"sealed or native model pin differs: {arm}")
        if arm in ("IQ4KT", "IQ2KT"):
            _require(native["types"].get(arm.replace("KT", "_KT"), 0) > 0,
                     f"native KT tensor mechanism absent: {arm}")
        expected_modelset.update({arm: meta["path"], f"{arm}_SHA": model["sha256_pinned"]})
    _require(len({pins["models"][arm]["metadata"]["path"] for arm in ARMS}) == len(ARMS),
             "duplicate official model paths")
    modelset = _unique_fields([tuple(token.split("=", 1))
                               for token in shlex.split(files["source/models.env"].decode())])
    _require(modelset == expected_modelset, "original modelset assignments differ from RUN")
    return libs


def _launch(files, origin, row, run, mask, libs, previous_end, previous_write):
    unit = row["unit"]
    allocation, carrier = run["allocation"], row["belief_capture"]
    _require(_zero(row["rc"]) and row["cpus"] == allocation["FILLER_CPUS"]
             and type(row["threads"]) is int and row["threads"] == len(mask),
             "official unit resources or return code differ")
    base = f"launches/{unit}"
    data = files[f"{base}.json"]
    _identity(carrier["launch"], origin / f"{base}.json")
    _require(_matches(data, carrier["launch"], origin / f"{base}.json"),
             "original official launch record changed")
    launch = _json(data)
    start, end = launch["started_monotonic_s"], launch["ended_monotonic_s"]
    started, ended = launch["started_at"], launch["ended_at"]
    written = carrier["written_at"]
    duration = row["duration_s"]
    _require(launch["schema"] == "epyc.exp01.launch.v1" and launch["unit"] == unit
             and _zero(launch["rc"]) and _zero(launch["native_rc"]) and launch["disposition"] == "complete"
             and "failure" not in launch and type(launch["pid"]) is int and launch["pid"] > 0
             and all(_finite(number) for number in (start, end, started, ended, duration))
             and 0 < start < end and previous_end <= start and previous_write <= started < ended <= written
             and 0 <= duration and ended - started <= duration + 0.00501
             and duration <= written - previous_write + 0.00501,
             "failed, overlapping or out-of-window official launch")
    previous_sample = None
    witnesses = 0
    for sample in launch["samples"]:
        sampled = sample["monotonic_s"]
        _require(_finite(sampled) and start <= sampled <= end
                 and (previous_sample is None or previous_sample < sampled)
                 and type(sample["own_pid"]) is int and sample["own_pid"] == launch["pid"]
                 and sample["affinity"] == mask
                 and all(type(cpu) is int for cpu in sample["affinity"]),
                 "official in-window sample, affinity or process identity differs")
        previous_sample = sampled
        witnesses += libs.keys() <= set(sample["mapped"])
    _require(witnesses >= 2 and launch["mapped_artifacts"] == libs,
             "missing persistent official mapped library identities")
    for stream in ("stdout", "stderr"):
        name = f"{base}.{stream}"
        _identity(launch[stream], origin / name)
        _require(_matches(files[name], launch[stream], origin / name), f"official launch {stream} changed")
    return launch


def _speed(files, origin, row, launch, model, tool, ordinal, threads):
    unit = row["unit"]
    argv = [tool["path"], "-m", model["path"], "-p", "512", "-n", "128",
            "-r", "1", "-t", str(threads), "-o", "json"]
    _require(launch["executable"] == tool and launch["argv"] == argv
             and row["gguf"] == model["path"] and type(row["launch"]) is int and row["launch"] == ordinal,
             "official speed executable, invocation or ordinal differs")
    stdout = files[f"launches/{unit}.stdout"]
    raw = row["belief_capture"]["raw"]
    _identity(raw, origin / f"{unit}.json")
    _require(stdout == files[f"{unit}.json"] and _matches(stdout, raw, origin / f"{unit}.json")
             and files[f"{unit}.err"] == files[f"launches/{unit}.stderr"],
             "original official bench streams differ")
    cells = _json(stdout)
    commit, model_type = row["build_commit"], row["type_k"]
    _require(re.fullmatch(r"[0-9a-f]{7,40}", commit) and INSTRUMENT_SHA.startswith(commit)
             and "parse_error" not in row
             and isinstance(model_type, str) and model_type
             and [(cell["n_prompt"], cell["n_gen"]) for cell in cells] == [(512, 0), (0, 128)]
             and (row["pp_n"], row["tg_n"]) == (512, 128)
             and all(cell["model_filename"] == model["path"] and type(cell["model_size"]) is int
                     and 0 < cell["model_size"] == cells[0]["model_size"] <= model["size"]
                     and cell["model_type"] == model_type and cell["n_threads"] == threads
                     and cell["build_commit"] == commit and cell["n_gpu_layers"] == 999
                     and all(cell[key] is False for key in ("cuda", "vulkan", "kompute", "metal", "sycl", "gpu_blas"))
                     and cell["gpu_info"] == "" and cell["rpc"] == "0"
                     and _speed_matches(cell, row[metric])
                     for metric, cell in zip(("pp", "tg"), cells, strict=True))
             and sum(cell["avg_ns"] for cell in cells) / 1e9
             <= launch["ended_monotonic_s"] - launch["started_monotonic_s"],
             "official native speed does not re-derive")


def _quality(files, row, launch, model, tool, item, threads):
    argv = [tool["path"], "-m", model["path"], "-p", item["prompt"], "-n", "256",
            "--temp", "0", "--seed", "42", "-t", str(threads), "--no-display-prompt"]
    _require(launch["executable"] == tool and launch["argv"] == argv,
             "official quality executable or invocation differs")
    stdout = files[f"launches/{row['unit']}.stdout"].decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    item_hash = _digest((item["prompt"] + item["expect_regex"]).encode())[:16]
    _require(row["item"] == item["id"] and row["item_native"] == item and row["item_hash"] == item_hash
             and row["output"] == stdout and row["correct"] is bool(re.search(item["expect_regex"], stdout)),
             "official pinned paired item or quality outcome does not re-derive")


def _look(first, second, speeds):
    # Keep the R2 producer's exact rounding and test unrounded band edges.
    xa, xb = ([row["tg"] for row in speeds[arm]] for arm in (first, second))
    ma, mb, sa, sb = statistics.mean(xa), statistics.mean(xb), statistics.stdev(xa), statistics.stdev(xb)
    ratio = mb / ma
    half = 2 * ((sa ** 2 / len(xa) + sb ** 2 / len(xb)) ** 0.5) / ma
    lo, hi = ratio - half, ratio + half
    stop = "answer" if lo > 1.00 else "futility" if hi < 0.95 else "continue"
    return dict(pair=f"{second}/{first}", n=[len(xa), len(xb)],
                ratio=round(ratio, 4), band=[round(lo, 4), round(hi, 4)], sd=[round(sa, 3), round(sb, 3)],
                mean=[round(ma, 3), round(mb, 3)], rule=">=0.95 tg128 ratio (STEP3/T3; decided only by the full paired set)",
                stop=stop, label="operational pilot look (exploratory/decision-support), never a gate result")


def _summary(summary, run, terminal, engine_start, validity, speeds, paired, last_write):
    wall = summary["wall_s"]
    launch_count = run["planned"]["launches_per_arm"]
    _require(type(wall) is int and int(last_write) - int(run["started_at"]) <= wall
             <= int(terminal["ended_at"]) - engine_start and 0 <= wall <= run["planned"]["cap_s"],
             "official summary wall time differs from the original window")
    tgs = {arm: [row["tg"] for row in speeds[arm]] for arm in ARMS}
    looks = {f"{first}:{second}": _look(first, second, speeds) for first, second in PAIRS}
    primary = looks["Q4KM:IQ4KT"]
    mechanism = any("KT" in row["type_k"].upper() for arm in ARMS[1::2] for row in speeds[arm])
    expected = dict(
        wall_s=wall, validity_ok=True, why=validity["why"], fixture=False,
        duration_per_launch_s={arm: [row["duration_s"] for row in speeds[arm]] for arm in ARMS},
        variance_sd_tg={arm: round(statistics.stdev(tgs[arm]), 3) for arm in ARMS},
        aa_spread_control_Q4KM=tgs["Q4KM"],
        capture_completeness={arm: [len(speeds[arm]), launch_count] for arm in ARMS},
        quality_items_scored=2 * len(paired), mechanism_selected=mechanism, looks=looks,
        consumer_coverage={
            "STEP2/T2 (report)": "partial: speed slice" if primary["ratio"] else "none",
            "STEP3/T3 (>=0.95 AND paired flips)": (
                "futility-indicated (operational, gate open)" if primary["stop"] == "futility"
                else "not answerable by pilot (needs full paired set + quality pass)"),
        },
        decision_hint="owner review: EXPAND with n from observed sd" if mechanism else "REVISE",
    )
    _require(_canonical(summary) == _canonical(expected), "original official summary does not re-derive")


def _verify_rows(files, origin, run, terminal, rows, mask, libs, engine_start):
    pins, plan = run["pins"], run["planned"]
    items = [_json(line) for line in files["original-fixed-items.jsonl"].splitlines()]
    ids = [item["id"] for item in items]
    launches = plan["launches_per_arm"]
    _require(type(launches) is int and launches in (2, 3) and plan["speed_arms"] == list(ARMS)
             and (plan["pp"], plan["tg"]) == (512, 128) and plan["planned_looks"] == list(range(2, launches + 1))
             and ids == plan["paired_item_ids"] and len(ids) == len(set(ids)) == 24
             and all(re.fullmatch(r"[A-Za-z0-9_.-]{1,60}", item_id) for item_id in ids),
             "original official speed plan or pinned item ordering differs")
    previous_write = run["started_at"]
    for row in rows:
        carrier = row["belief_capture"]
        time = carrier["written_at"]
        _require(carrier["schema"] == "epyc.exp01.unit_capture.v1" and carrier["run_id"] == run["run_id"]
                 and carrier["mode"] == MODE and carrier["allocation"] == run["allocation"]
                 and _finite(time) and previous_write < time <= terminal["ended_at"],
                 "mixed official unit identity or nonchronological raw writes")
        previous_write = time

    remaining = iter(rows[1:])
    previous_end, previous_write = 0.0, rows[0]["belief_capture"]["written_at"]
    used = FIXED_MEMBERS | {f"source/{name}" for name in SOURCE_MEMBERS}

    def take(kind, unit, arm=None):
        nonlocal previous_end, previous_write
        row = next(remaining, {})
        _require(row.get("kind") == kind and row.get("unit") == unit and row.get("arm") == arm,
                 f"incomplete, extra or reordered official units at {unit}")
        launch = None
        if arm is not None:
            launch = _launch(files, origin, row, run, mask, libs, previous_end, previous_write)
            previous_end = launch["ended_monotonic_s"]
            used.update(f"launches/{unit}.{ext}" for ext in ("json", "stdout", "stderr"))
        previous_write = row["belief_capture"]["written_at"]
        return row, launch

    speeds, looks, stopped = {arm: [] for arm in ARMS}, [], set()
    for ordinal in range(1, launches + 1):
        for first, second in PAIRS:
            if first in stopped:
                continue
            for arm in (first, second):
                unit = f"speed-{arm}-{ordinal}"
                row, launch = take("speed", unit, arm)
                _speed(files, origin, row, launch, pins["models"][arm]["metadata"],
                       pins["artifacts"]["bench"], ordinal, len(mask))
                speeds[arm].append(row)
                used.update({f"{unit}.json", f"{unit}.err"})
            if ordinal in plan["planned_looks"]:
                unit = f"look-{first}-{second}"
                row, _ = take("look", unit)
                expected = dict(_look(first, second, speeds), unit=unit, kind="look")
                _require(_canonical({key: value for key, value in row.items() if key != "belief_capture"})
                         == _canonical(expected), f"official operational look does not re-derive: {unit}")
                looks.append(expected)
                if expected["stop"] in ("answer", "futility"):
                    stopped.add(first)

    paired = []
    for item in items:
        pair = {"item": item["id"]}
        for arm in ARMS[:2]:
            row, launch = take("quality", f"q-{arm}-{item['id']}", arm)
            _quality(files, row, launch, pins["models"][arm]["metadata"], pins["artifacts"]["cli"], item, len(mask))
            pair[arm] = row["correct"]
        paired.append(pair)
    _require(next(remaining, None) is None and set(files) == used, "extra official units or archive members")
    _summary(_json(files["SUMMARY.json"]), run, terminal, engine_start, rows[0], speeds, paired, previous_write)
    return speeds, looks, paired


def official_rows(filing):
    binding = _json(_read(filing / MARKER, 64 << 10))
    _require(binding["schema"] == SCHEMA and set(binding) == {"schema", "id", "run_id", "mode",
                                                                  "manifest_sha256", "artifacts", "grant_copy_source"}
             and binding["grant_copy_source"] in GRANT_COPY_SOURCES,
             "unsupported official completion binding")
    files = _archive(filing / ARCHIVE)
    _require(FIXED_MEMBERS <= set(files), "missing original official archive members")
    manifest, report, run, terminal = (_json(files[key]) for key in
                                       ("ready-manifest.json", "RESULT.json", "RUN.json", "TERMINAL.json"))
    origin, locations = _file_map(binding, manifest, report, run)
    _require(binding["manifest_sha256"] == _digest(_canonical(manifest))
             and set(binding["artifacts"]) == set(locations), "official canonical ready manifest binding differs")
    for name, original in locations.items():
        pin = binding["artifacts"][name]
        _require(type(pin["size"]) is int and _matches(files[name], pin, original),
                 f"official completion binding differs: {name}")
    raw = files["results.jsonl"]
    _require(raw == _read(filing / "results.jsonl", MAX_MEMBER_BYTES),
             "official archive and filed result bytes differ")
    for name, pin in (("TERMINAL.json", report["terminal"]), ("results.jsonl", terminal["raw"]),
                      ("SUMMARY.json", terminal["summary"])):
        _identity(pin, locations[name])
        _require(_matches(files[name], pin, locations[name]), f"original {name} terminal custody differs")
    rows = [_json(line) for line in raw.splitlines()]
    run_id = run["run_id"]
    _require(run["schema"] == "epyc.exp01.capture.v1" and run["mode"] == terminal["mode"] == MODE
             and re.fullmatch(r"[0-9a-f]{32}", run_id) and run_id == terminal["run_id"] == binding["run_id"]
             and set(terminal) == {"run_id", "mode", "rc", "ended_at", "state",
                                   "stop_file_observed", "deadline_reached", "raw", "summary"}
             and terminal["state"] == report["state"] == "complete-unprojected"
             and _zero(terminal["rc"]) and terminal["stop_file_observed"] is False
             and terminal["deadline_reached"] is False and raw.endswith(b"\n")
             and 59 <= len(rows) <= 65 and type(report["native_units"]) is int and len(rows) == report["native_units"],
             "mixed identity, wrong mode or incomplete official run")
    mask, engine_start = _allocation(files, manifest, run, terminal, binding, origin)
    libs = _assets(files, manifest, run, rows[0])
    speeds, looks, paired = _verify_rows(files, origin, run, terminal, rows, mask, libs, engine_start)

    models = run["pins"]["models"]
    paired_context = {
        "model_identities": {arm: {"model_file": models[arm]["metadata"]["path"],
                                   "model_sha256": models[arm]["sha256_pinned"]} for arm in ARMS[:2]},
        "items": paired,
        "flips": {"correct_to_incorrect": sum(p["Q4KM"] and not p["IQ4KT"] for p in paired),
                  "incorrect_to_correct": sum(not p["Q4KM"] and p["IQ4KT"] for p in paired)},
    }
    observed_date = datetime.fromtimestamp(run["started_at"], timezone.utc).date().isoformat()
    digest = _digest(raw)
    for arm, arm_rows in speeds.items():
        model = models[arm]
        for metric, workload in (("pp", "pp512"), ("tg", "tg128")):
            vector = [row[metric] for row in arm_rows]
            yield ClaimTuple(
                measurement_id=f"exp01-official:{run_id}:{arm}:{workload}",
                metric=f"official_proxy_{workload}_native_tokens_per_s", value=statistics.mean(vector),
                date=observed_date, category="CANDIDATE", metric_direction="higher_better",
                claim=f"EXP01 official prospective CPU proxy pilot {arm} {workload} native throughput",
                reps=len(vector), unit="tokens/s", reps_basis="scored:independent original llama-bench launches",
                attestation_locator=str(filing / "results.jsonl"), attestation_sha256=digest,
                attestation_present=True, attestation_verified=True, source_kind=OFFICIAL_SOURCE_KIND,
                applicability=dict(model_file=model["metadata"]["path"], model_sha256=model["sha256_pinned"],
                                   backend="cpu", build_sha=INSTRUMENT_SHA, threads=len(mask),
                                   run_id=run_id, scope_basis="native"),
                observation=dict(outcome_native="prospective-proxy-pilot", outcome_reason=LIMITATION),
                extra=dict(mode=MODE, original_result=str(origin / "results.jsonl"), native_rates=vector,
                           operational_looks=looks, paired_quality=paired_context, limitations=LIMITATION),
            )


def _binding(files, manifest, report, run, grant_copy_source="allocator-original"):
    binding = dict(schema=SCHEMA, id=manifest["id"], run_id=run["run_id"], mode=MODE,
                   manifest_sha256=_digest(_canonical(manifest)), grant_copy_source=grant_copy_source)
    _, locations = _file_map(binding, manifest, report, run)
    binding["artifacts"] = {name: dict(path=str(path), size=len(files[name]), sha256=_digest(files[name]))
                            for name, path in locations.items()}
    return binding


def _write_bundle(path, files, binding):
    _require(len(files) <= MAX_ARCHIVE_ENTRIES and sum(map(len, files.values())) <= MAX_ARCHIVE_BYTES
             and all(_allowed_member(name) and len(data) <= MAX_MEMBER_BYTES for name, data in files.items()),
             "invalid official archive members")
    with (path / ARCHIVE).open("xb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gzip_out:
        with tarfile.open(fileobj=gzip_out, mode="w|", format=tarfile.USTAR_FORMAT) as archive:
            for name, data in sorted(files.items()):
                member = tarfile.TarInfo(name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
    (path / "results.jsonl").write_bytes(files["results.jsonl"])
    (path / MARKER).write_bytes(_canonical(binding) + b"\n")


def pack(ready: Path, grant: Path | None, ended: Path, complete: Path, output: Path) -> None:
    """File original R2 writer bytes and separately preserved allocator receipts."""
    files = {name: _read(path, 64 << 10) for name, path in (
        ("ready-manifest.json", ready),
        ("grant-ended.original", ended), ("allocator-complete.original", complete),
    )}
    manifest = _json(files["ready-manifest.json"])
    files["RESULT.json"] = _read(Path(manifest["result_path"]), 64 << 10)
    report = _json(files["RESULT.json"])
    origin = Path(report["attempt"])
    files["RUN.json"] = _read(origin / "RUN.json", 64 << 10)
    run = _json(files["RUN.json"])
    files["grant.original"] = _read(grant, 64 << 10) if grant else run["grant"]["raw"].encode()
    seed = dict(id=manifest["id"], mode=MODE)
    _, locations = _file_map(seed, manifest, report, run)
    total = sum(map(len, files.values()))

    def preserve(name, original):
        nonlocal total
        files[name] = _read(original, min(MAX_MEMBER_BYTES, MAX_ARCHIVE_BYTES - total))
        total += len(files[name])

    for name, path in locations.items():
        if name not in files:
            preserve(name, path)
    source = locations["SOURCE.json"].parent
    for name in SOURCE_MEMBERS:
        preserve(f"source/{name}", source / name)
    lines = files["results.jsonl"].splitlines()
    _require(59 <= len(lines) <= 65, "official capture has an incomplete or oversized schedule")
    for row in map(_json, lines):
        kind, unit = row.get("kind"), row["unit"]
        if kind not in ("speed", "quality"):
            continue
        members = [f"launches/{unit}.{ext}" for ext in ("json", "stdout", "stderr")]
        if kind == "speed":
            members.extend([f"{unit}.json", f"{unit}.err"])
        for name in members:
            _require(_allowed_member(name) and name not in files, f"invalid or duplicate launch member {name}")
            preserve(name, origin / name)

    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".exp01-official-") as temp:
        staged = Path(temp)
        grant_source = "allocator-original" if grant else "RUN.grant.raw"
        _write_bundle(staged, files, _binding(files, manifest, report, run, grant_source))
        tuple(official_rows(staged))
        output.mkdir()
        try:
            for name in (ARCHIVE, "results.jsonl", MARKER):
                (staged / name).rename(output / name)
        except OSError:
            shutil.rmtree(output)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=pack.__doc__)
    for name in ("ready", "ended", "complete", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--grant", type=Path, help="original allocator bytes if preserved outside RUN")
    args = parser.parse_args()
    try:
        pack(**vars(args))
    except (OSError, EOFError, ValueError, KeyError, TypeError, AttributeError, IndexError, OverflowError,
            tarfile.TarError, re.error) as exc:
        parser.exit(1, f"REFUSED: {exc}\n")
