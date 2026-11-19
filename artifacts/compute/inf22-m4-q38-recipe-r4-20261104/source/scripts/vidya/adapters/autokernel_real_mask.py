"""Strict prospective captured-mask identity projection; existing verifier ladder only."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.autokernel_real_mask/v1"
SCHEMA = "epyc.autokernel.ds41_fa_verifier.v1"
AUTHORITY = "captured_mask_probe_identity_no_serving_performance_or_promotion"
PROPOSITION = ("For the sixteen captured DS41 raw-plus-compressed top-k F16 masks at "
               "KV widths 4096, 8192, 32768, 65536 and query rows 2, 3, 4, 5, "
               "each recorded anchor/candidate probe configuration has identical inputs, "
               "three internally stable output repetitions, and bit-identical output rows.")
# Reviewed source bytes, populated at source integration; never execute archived code.
PRODUCERS = {'probe-source.cpp': 'eca6a1acd105e41548265ee6afc3359360273b005877ba1a2d3321b77774f5cb', 'verifier-source.py': '17fae6d96855db42a2b13f0e9e81786abb1b9acbe6a472edd7dcaf4bf278dd06', 'reference-source.py': 'ad028c93bccd49e227c2aa78466c7170421cd4e84d632d9d6af38f78591d55bf', 'capture-source.py': 'f1f82191be9d0bbdc1f90aec7852111315d7d51d20340ac1b8f977c0937395c6'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate native JSON member")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def regular(path):
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
            and stat.S_IMODE(before.st_mode) == 0o600 and before.st_size <= 128 * 1024 * 1024,
            "native original must be an owned private bounded regular file")
    def identity(info):
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        require(identity(os.fstat(stream.fileno())) == identity(before), "native file changed on open")
        raw = stream.read(128 * 1024 * 1024 + 1)
        require(len(raw) <= 128 * 1024 * 1024 and identity(os.fstat(stream.fileno())) == identity(before)
                and identity(path.lstat()) == identity(before), "native file changed during read")
    return raw


def pin(archive, item):
    name = item["name"]
    require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."),
            "artifact name escapes native custody")
    raw = regular(archive / name)
    require(digest(raw) == item["sha256"] and ("bytes" not in item or len(raw) == item["bytes"]),
            "native artifact digest/size changed")
    return raw


def utc(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, "UTC required")
    return parsed


def probe(stdout, case, team, library):
    lines = stdout.splitlines()
    header = f"AK_CPU_FA_REFERENCE_V1 512 512 1 64 {case['kv']} {case['nb']} 1 captured cache {team} 3 20261004"
    require(bool(lines) and lines[0] == header, "probe header disagrees with native request")
    tables, lib, inputs = {"D": {}, "R": {}}, None, None
    for line in lines[1:]:
        fields = line.split(" ")
        if len(fields) == 2 and fields[0] == "L" and lib is None:
            lib = fields[1]
        elif len(fields) == 2 and fields[0] == "I" and inputs is None and re.fullmatch("[0-9a-f]{16}", fields[1]):
            inputs = fields[1]
        elif len(fields) == 3 and fields[0] in tables and re.fullmatch("[0-9]+", fields[1]) and re.fullmatch("[0-9a-f]{16}", fields[2]):
            index = int(fields[1])
            table = tables[fields[0]]
            bound = 3 if fields[0] == "D" else case["nb"] * 64
            require(index < bound and index not in table, "duplicate/out-of-range native probe repetition/row")
            table[index] = fields[2]
        else:
            raise ValueError("unknown native probe line")
    require(lib in library and inputs is not None and len(tables["D"]) == 3
            and len(tables["R"]) == case["nb"] * 64, "wrong arm library or missing original repetitions/rows")
    return inputs, [tables["D"][index] for index in range(3)], tables["R"]


def read_record(path):
    path = Path(path).absolute()
    archive = path.parent
    for parent in reversed((archive, *archive.parents)):
        info = parent.lstat()
        sticky_temp = parent in (Path("/tmp"), Path("/var/tmp")) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o1777
        require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.getuid())
                and (not stat.S_IMODE(info.st_mode) & 0o022 or sticky_temp), "native custody ancestor is symlink/nonowned/writable")
    info = archive.lstat()
    require(path.name == "record.json" and re.fullmatch("[0-9a-f]{32}", archive.name)
            and stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o700, "native opaque private custody required")
    raw = regular(path)
    record = decode(raw)
    body = dict(record)
    seal = body.pop("record_sha256")
    require(digest(canonical(body)) == seal and record["schema"] == SCHEMA, "native record seal/schema changed")
    request_raw = regular(archive / "request.json")
    require(digest(request_raw) == record["request_sha256"], "native request changed")
    request = decode(request_raw)
    require(request["schema"] == SCHEMA + ".request" and request["capture_id"] == record["capture_id"] == archive.name,
            "native request/run identity mismatch")
    mode = request["evidence_mode"]
    require(mode in ("native_ds41_capture", "synthetic_source_control") and mode == record["evidence_mode"], "native evidence mode changed")
    proposition = "Synthetic source-conformance fixture only: " + PROPOSITION if mode == "synthetic_source_control" else PROPOSITION
    for key, value in (("decided_proposition", proposition), ("authority", AUTHORITY),
                       ("metric", "captured_mask_anchor_bit_identity"), ("metric_direction", "higher_better"),
                       ("category", "CANDIDATE")):
        require(request[key] == record[key] == value, "native proposition/authority contract changed")
    require(request["reps"] == 3 and type(request["reps"]) is int, "native three-repeat contract missing")
    require(request["started_at"] == record["started_at"] and utc(record["ended_at"]) >= utc(record["started_at"]),
            "native verifier chronology changed")
    names = [item["name"] for item in record["pins"]]
    require(len(names) == len(set(names)), "duplicate native pin")
    files = {item["name"]: pin(archive, item) for item in record["pins"]}
    pins = {item["name"]: item for item in record["pins"]}
    require(all(pins.get(item["name"]) == item for item in request["pins"]), "original request readset changed")
    require(bool(PRODUCERS) and all(digest(files[name]) == sha for name, sha in PRODUCERS.items()),
            "unreviewed verifier/capture/probe source bytes")
    manifest = decode(files["capture-capture-manifest.json"])
    require(manifest == request["capture_manifest"] and manifest["verifier_schema"] == SCHEMA
            and manifest["decided_proposition"] == proposition and manifest["evidence_mode"] == mode
            and manifest["schema"] == "epyc.autokernel.ds41_fa_capture.v1"
            and manifest["architecture"] == "deepseek41"
            and manifest["capture_contract"] == "ds41_real_mask_n2_5_v1", "native capture manifest contract")
    require(digest(files["capture-recipe.json"]) == manifest["recipe_sha256"]
            and digest(files["capture-prompt.txt"]) == manifest["prompt_sha256"]
            and digest(canonical(manifest["launch_env"])) == manifest["launch_env_sha256"],
            "native original prompt/recipe/environment digest changed")
    for key, length in (("source_commit", 40), ("model_sha256", 64), ("binary_sha256", 64), ("libllama_sha256", 64)):
        require(re.fullmatch(f"[0-9a-f]{{{length}}}", manifest[key]), "capture source/model/build digest malformed")
    require(Path(manifest["model"]).is_absolute() and bool(manifest["run_id"]), "capture model/run absent")
    for group, prefix in (("capture_sources", "capture-model-source-"), ("build_images", "capture-build-image-")):
        require(bool(manifest[group]), "capture source/build closure missing")
        for index, (name, sha) in enumerate(manifest[group].items()):
            suffix = ".txt" if group == "capture_sources" else ".bin"
            item = pins[prefix + str(index) + suffix]
            original = str(Path(manifest["source_root"]) / name) if group == "capture_sources" else name
            require(item["sha256"] == sha and item["original_path"] == original, "capture source/build binding changed")
    cases = request["cases"]
    expected = [(kv, nb) for kv in (4096, 8192, 32768, 65536) for nb in (2, 3, 4, 5)]
    require([(item["kv"], item["nb"]) for item in cases] == expected, "exact sixteen consumed-mask cases required")
    for case in cases:
        kv, nb = case["kv"], case["nb"]
        name = f"ds41_realmask_kv{kv // 1024}k_nb{nb}"
        require(case == dict(name=name, hsk=512, hsv=512, n_kv_heads=1, gqa=64,
            kv=kv, nb=nb, sinks=True, mask="captured", layout="cache", backend_ops=False), "native case geometry changed")
        data, sidecar = files[name + ".mask.f16"], decode(files[name + ".mask.json"])
        require(len(data) == kv * nb * 2, "consumed mask byte count changed")
        expected_sidecar = {"schema": "epyc.autokernel.ds41_fa_mask.v1", "type": "f16", "byte_order": "little",
            "layout": "token_kv", "ne": [kv, nb, 1, 1], "hsk": 512, "hsv": 512,
            "n_q_heads": 64, "n_kv_heads": 1, "mask_kind": "raw_plus_compressed_top_k",
            "mask_hash_algorithm": "fnv1a64", "mask_bytes": len(data)}
        expected_sidecar.update({key: manifest[key] for key in
            ("source_commit", "model", "model_sha256", "run_id", "recipe_sha256", "prompt_sha256")})
        require(all(sidecar.get(key) == value for key, value in expected_sidecar.items()), "native sidecar/run/mask mismatch")
        require(all(type(sidecar[key]) is int for key in
                    ("hsk", "hsv", "n_q_heads", "n_kv_heads", "mask_bytes", "compressed_ratio"))
                and all(type(value) is int for value in sidecar["ne"]), "native mask integer fields must not be boolean")
        ne = sidecar["original_ne"]
        require(len(ne) == 4 and all(type(value) is int for value in ne) and ne[0] == kv and ne[2:] == [1, 1] and ne[1] >= nb
            and sidecar["original_nb"] == [2, kv * 2, kv * 2 * ne[1], kv * 2 * ne[1]]
            and sidecar["slice"] == dict(row_start=0, row_count=nb, head_index=0, stream_index=0)
            and type(sidecar["layer"]) is int and sidecar["layer"] >= 0
            and sidecar["compressed_ratio"] in (1, 2), "original native consumed-mask slice/geometry changed")
        require(utc(manifest["started_at"]) <= utc(sidecar["captured_at"]) <= utc(record["started_at"]), "original capture time outside native chronology")
        fnv = 0xcbf29ce484222325
        for byte in data:
            fnv = ((fnv ^ byte) * 0x100000001b3) & ((1 << 64) - 1)
        require(sidecar["mask_hash"] == f"{fnv:016x}", "original native mask FNV changed")
    configs, arms = request["configs"], request["arms"]
    team = arms["candidate"]["threads"]
    require(type(team) is int and team > 0 and arms["anchor"]["threads"] == team, "native arm teams disagree")
    setting = arms["candidate"]["env"].get("GGML_FA_SPLIT_KV")
    match = re.match(r"\s*([+-]?\d+)", setting) if setting is not None else None
    here = "1" if setting is None or (match and int(match.group(1)) != 0) else "0"
    expected_configs = [[f"recipe split_kv={here} t7", here, 7]]
    if team != 7:
        expected_configs += [[f"recipe split_kv={here} t{team}", here, team]]
    other = "0" if here == "1" else "1"
    expected_configs += [[f"split_kv={other} t{team}", other, team]]
    require(configs == expected_configs, "native requested configuration coverage changed")
    observations = []
    for index, item in enumerate(record["observations"]):
        require(item["name"] == f"observation-{index:04d}.json", "native observation order/membership changed")
        row = decode(pin(archive, item))
        launch = decode(regular(archive / f"launch-{index:04d}.json"))
        require(all(row[key] == value for key, value in launch.items()) and row["sequence"] == index,
                "native pre-execution launch differs from terminal")
        require(row["output_capture"] == "original_binary_bytes", "original native output bytes missing")
        for stream in ("stdout", "stderr"):
            output_pin = row["original_outputs"][stream]
            require(output_pin["name"] == f"{stream}-{index:04d}.bin"
                    and output_pin == pins[output_pin["name"]]
                    and files[output_pin["name"]].decode("utf-8", errors="replace") == row[stream],
                    "original native stdout/stderr changed")
        require(utc(record["started_at"]) <= utc(row["started_at"]) <= utc(row["ended_at"]) <= utc(record["ended_at"])
            and type(row["wait_seconds"]) in (int, float) and math.isfinite(row["wait_seconds"])
            and row["wait_seconds"] >= 0, "native process chronology/wait missing")
        observations.append(row)
    if record["value"] is None:
        require(record["verdict"] == "unavailable", "NULL verifier verdict mismatch")
        return record, digest(raw), request
    require(type(record["value"]) is bool and record["verdict"] == ("pass" if record["value"] else "wrong"), "forged native verdict/value")
    require(len(observations) >= 4, "original compile/probe observations missing")
    binaries = {}
    for index, role in enumerate(("anchor", "candidate")):
        row = observations[index]
        require(row["error"] is None and type(row["returncode"]) is int and row["returncode"] == 0,
                "native probe compile failed")
        argv = row["argv"]
        build = request["builds"][role]
        expected_libraries = {name: item["sha256"] for name, item in pins.items() if name.startswith(role + "-libggml")}
        require(row["library_sha256_before"] == row["library_sha256_after"] == expected_libraries,
                "original native compile library bytes changed")
        require(argv[:5] == ["c++", "-std=c++17", "-O2", "-I", request["source_root"] + "/ggml/include"]
            and argv[6:] == ["-L", build + "/bin", "-Wl,-rpath," + build + "/bin", "-lggml-cpu", "-lggml-base", "-lggml", "-ldl", "-o", argv[-1]]
            and argv[5] == pins["probe-source.cpp"]["original_path"]
            and pins[f"compiled-probe-{index}.bin"]["original_path"] == argv[-1], "native compile/readset binding changed")
        binaries[role] = argv[-1]
    native_verdict = True
    offset = 2
    for case in cases:
        for _label, split, config_team in configs:
            runs = {}
            for role in ("anchor", "candidate"):
                require(offset < len(observations), "original arm/config observations missing")
                row = observations[offset]
                offset += 1
                expected_env = dict(arms[role]["env"], GGML_FA_SPLIT_KV=split)
                mask_pin = pins[case["name"] + ".mask.f16"]
                expected_libraries = {name: item["sha256"] for name, item in pins.items() if name.startswith(role + "-libggml")}
                binary_pin = pins["compiled-probe-" + str(0 if role == "anchor" else 1) + ".bin"]
                argv = [*arms[role]["prefix"], binaries[role], "512", "512", "1", "64", str(case["kv"]),
                    str(case["nb"]), "1", "captured", "cache", str(config_team), "3", "20261004", "--mask-file", mask_pin["original_path"]]
                require(row["argv"] == argv and row["env"] == expected_env and row["timeout_seconds"] == 900
                    and row["mask_sha256_before"] == row["mask_sha256_after"] == mask_pin["sha256"]
                    and row["library_sha256_before"] == row["library_sha256_after"] == expected_libraries
                    and row["probe_binary_sha256_before"] == row["probe_binary_sha256_after"] == binary_pin["sha256"]
                    and row["error"] is None and type(row["returncode"]) is int and row["returncode"] == 0,
                    "native probe argv/environment/exit/mask binding changed")
                library = request["builds"][role] + "/bin/libggml-cpu.so"
                require(pins[role + "-libggml-cpu.so"]["original_path"] == library, "native arm build library pin mismatch")
                runs[role] = probe(row["stdout"], case, config_team,
                    (library, pins[role + "-libggml-cpu.so"]["resolved_path"]))
            anchor, candidate = runs["anchor"], runs["candidate"]
            require(anchor[0] == candidate[0] and len(set(anchor[1])) == 1, "anchor unstable or unequal native inputs")
            if candidate[1] != anchor[1] or candidate[2] != anchor[2]:
                native_verdict = False
                break
        if not native_verdict:
            break
    require(offset == len(observations) and native_verdict == record["value"], "forged verdict or incomplete/extra original observations")
    return record, digest(raw), request


def native_rows(path):
    try:
        record, sha, request = read_record(path)
        if record["value"] is None:
            return ()
        return ({"record": record, "request": request, "record_sha256": sha,
                 "record_path": str(Path(path).absolute())},)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ProjectionError(f"real-mask native verifier refused: {exc}") from exc


@register("autokernel-real-mask-identity", source_class="verifier",
          decided_proposition_field="decided_proposition")
def project_real_mask(native):
    rows = native_rows(native["record_path"])
    if len(rows) != 1 or rows[0] != native:
        raise ProjectionError("original real-mask verifier record changed since reopening")
    record, manifest = native["record"], native["request"]["capture_manifest"]
    return ClaimTuple(measurement_id="real-mask:" + record["record_sha256"],
        metric=record["metric"], value=record["value"], date=record["ended_at"],
        category=record["category"], metric_direction=record["metric_direction"],
        claim=record["decided_proposition"], decided_proposition=record["decided_proposition"],
        source_class="verifier", source_kind=ADAPTER_ID, binding_kind="identity",
        attestation_locator=native["record_path"], reps=3, reps_basis="scored",
        extra={"record_sha256": native["record_sha256"], "authority": AUTHORITY,
               "evidence_mode": record["evidence_mode"],
               "capture_manifest": manifest, "native_verdict": record["verdict"],
               "exclusions": ["serving identity", "throughput", "promotion", "historical reconstruction"]},
        applicability={"model_file": manifest["model"], "backend": "cpu", "run_id": manifest["run_id"]})


def verify_and_grade(path):
    """Optional owning-session write hook: reopen originals, project, shared grade only."""
    from claim_tuple import grade
    return tuple(grade(project_real_mask(row)) for row in native_rows(path))
