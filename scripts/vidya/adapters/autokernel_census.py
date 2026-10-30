"""Prospective workload-census journal projection; no retrospective warrant."""
from __future__ import annotations
import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from types import SimpleNamespace

from scripts.vidya.adapters._census_native_graph import (
    graph_evidence, shape_evidence, tensor_shape_observed,
)

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames

SOURCE_KIND = "autokernel-census"
ADAPTER_ID = "vidya.adapters.autokernel_census/v1"
AUTHORITY = "measurement"
SCHEMA = "epyc.autokernel.census_capture_event.v1"
NODE = re.compile(r"^node #\s*\d+\s*\(\s*([A-Z_0-9]+)\s*\):.*?\[\s*([A-Za-z0-9]+)\s*\]", re.M)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _cpus(text: str) -> set[int]:
    result = set()
    for token in text.split(','):
        if re.fullmatch(r'q[0-3]', token):
            start = int(token[1]) * 24
            result.update(range(start,start+24))
            result.update(range(start+96,start+120))
        elif re.fullmatch(r'\d+(?:-\d+)?', token):
            lo, _, hi = token.partition('-')
            low, high = int(lo), int(hi or lo)
            if low > high or high > 191:
                raise ValueError('invalid CPU range')
            result.update(range(low,high+1))
        else:
            raise ValueError('unknown CPU region')
    if not result:
        raise ValueError('empty CPU region')
    return result


def _server_graph(row, start, end, identity):
    raw = _read(end['log'])
    offset = row['phase_log_byte_offset']
    if type(offset) is not int or not 0 <= offset < len(raw):
        raise ValueError('invalid native request-phase log boundary')
    full = ANSI.sub('',raw.decode(errors='replace'))
    phase = ANSI.sub('',raw[offset:].decode(errors='replace'))
    startup = ANSI.sub('',raw[:offset].decode(errors='replace'))
    capture = json.loads(_read({'path':row['request_log'],'sha256':row['request_log_sha256']}))
    if Path(row['request_log']).parent != Path(end['log']['path']).parent:
        raise ValueError('request evidence outside original run')
    requests = json.loads(_read(start['inputs']['requests']))
    if capture['requests'] != requests or capture['samples'] != end['samples'] or capture['phase_log_byte_offset'] != offset:
        raise ValueError('native server request evidence differs')
    shape = SimpleNamespace(**row['shape'])
    graph = graph_evidence(full,phase,identity['model']['path'])
    evidence = shape_evidence(shape,startup,phase,requests,capture['responses'],end['samples'])
    evidence['guards']['native_tensor_width_and_api_sequences'] = tensor_shape_observed(shape,graph)
    evidence['guards']['native_instrument_mapping'] = any(s.get('loaded_instrument') for s in end['samples'])
    evidence['observed'] = all(evidence['guards'].values())
    if _canon(evidence) != _canon(row['native_shape_evidence']) or not evidence['observed']:
        raise ValueError('native server shape evidence missing or changed')
    for key in ('nodes_total','op_backend','op_type','graphs','matmul_src1_shapes','scope'):
        if _canon(graph[key]) != _canon(row[key]):
            raise ValueError('actual native compute graph differs from census')
    return graph


def _affinity_ok(sample, expected):
    tasks = sample.get('task_affinity',{})
    return bool(tasks) and all(re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*',mask)
                              and _cpus(mask) <= _cpus(expected) for mask in tasks.values())


def _canon(x: Any) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _read(ref: dict, *, retain: bool = True) -> bytes:
    try:
        path = Path(ref["path"])
        digest = hashlib.sha256()
        chunks = []
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1 << 20), b""):
                digest.update(chunk)
                if retain:
                    chunks.append(chunk)
                    if sum(map(len, chunks)) > 64 << 20:
                        raise ValueError("input exceeds bound")
        if digest.hexdigest() != ref["sha256"]:
            raise ValueError("digest mismatch")
        return b"".join(chunks)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ProjectionError(f"capture reference invalid: {exc}") from exc


def _events(raw: bytes) -> list[dict]:
    previous = ""
    out = []
    try:
        for line in raw.splitlines():
            event = json.loads(line)
            body = dict(event)
            digest = body.pop("content_sha256")
            if (body.get("schema") != SCHEMA or body.get("previous_sha256") != previous or
                    hashlib.sha256(_canon(body)).hexdigest() != digest):
                raise ValueError("event chain or digest mismatch")
            previous = digest
            out.append(event)
    except (ValueError, KeyError, TypeError) as exc:
        raise ProjectionError(f"invalid capture journal: {exc}") from exc
    return out


def native_rows(path: str | Path) -> tuple[dict, ...]:
    try:
        path = Path(path).resolve(strict=True)
        raw = path.read_bytes()
    except (OSError, TypeError) as exc:
        raise ProjectionError(f"census sidecar unavailable: {exc}") from exc
    events = _events(raw)
    if len(events) != 1 or events[0].get("kind") != "record":
        raise ProjectionError("record sidecar required")
    envelope = events[0]
    try:
        record = json.loads(_read(envelope["record"]))
        if record["schema"] != "epyc.autokernel.workload_census.v1":
            raise ValueError("wrong census schema")
        identity = record["identity"]
        backend = identity.get('backend','gpu')
        if backend not in ('cpu','gpu'):
            raise ValueError('unknown census backend')
        identity_hash = hashlib.sha256(_canon(identity)).hexdigest()
        if identity_hash != record["validity"]["freshness_key"]:
            raise ValueError("stale identity")
        shapes = record["graph"]["shape_envelope"]
        rows = record["graph"]["per_shape"]
        if record["validity"].get("state") != "OBSERVED" or record["validity"].get("observed") is not True:
            raise ValueError("census validity is not observed")
        attempts = [envelope["attempts"][f"attempt_{i}"] for i in range(len(envelope["attempts"]))]
        if not shapes or len(shapes) != len(rows) or len(rows) != len(attempts):
            raise ValueError("partial census")
        result = []
        verified_files = set()
        def verify_once(file):
            key = (file['path'], file['sha256'])
            if key not in verified_files:
                _read(file, retain=False)
                verified_files.add(key)
        for shape, row, ref in zip(shapes, rows, attempts):
            pair = _events(_read(ref))
            if len(pair) != 2 or [x["kind"] for x in pair] != ["start", "terminal"]:
                raise ValueError("incomplete attempt")
            start, end = pair
            if start["attempt_id"] != end["attempt_id"] or start["shape"] != shape or row["shape"] != shape or row["argv"] != start["argv"]:
                raise ValueError("attempt does not bind census shape and argv")
            if end["rc"] != 0 or end["error"] or row["rc"] != 0 or row["state"] != "OBSERVED":
                raise ValueError("attempt refused or failed")
            if not start["grant"] or hashlib.sha256(start["grant"].encode()).hexdigest() != start["grant_sha256"] or not start["env"] or not start["deadline"] or not start["kernel_commit"]:
                raise ValueError("missing prelaunch warrant")
            if start["env"].get("GGML_SCHED_DEBUG") != "2":
                raise ValueError("scheduler debug environment absent")
            if any(start["env"].get(key) != value for key, value in identity["env"].items()):
                raise ValueError("native identity environment differs from launch")
            grant_match = re.fullmatch(r"regions=(\S+) start=(\d{4}-\d\d-\d\dT\d\d:\d\dZ) end=(\d{4}-\d\d-\d\dT\d\d:\d\dZ)\s*", start["grant"])
            if not grant_match:
                raise ValueError("grant is not an original minute-precision writer record")
            tokens = grant_match[1].split(',')
            gpu = 'mi210_0' in tokens
            if gpu != (backend == 'gpu'):
                raise ValueError('grant backend differs from native identity')
            declared = _cpus(','.join(x for x in tokens if x != 'mi210_0'))
            actual = start['env'].get('FILLER_CPUS','')
            if not _cpus(actual) <= declared or actual != identity.get('claim_cpus',actual):
                raise ValueError('native CPU footprint differs from original grant')
            window_start = datetime.datetime.strptime(grant_match[2], "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc).timestamp()
            window_end = datetime.datetime.strptime(grant_match[3], "%Y-%m-%dT%H:%MZ").replace(tzinfo=datetime.timezone.utc).timestamp()
            if (
                    start["started_ns"] < int(window_start) * 1_000_000_000 or
                    int(start["deadline"]) != int(window_end) - 90):
                raise ValueError("grant window or CPU claim mismatch")
            inputs = start["inputs"]
            if not {"binary", "model", "recipe", "binding", "producer", "driver", "grant",
                    "capture_module", "residency", "workload_contract", "build_receipt_binding", "build_complete",
                    "build_log", "elf_manifest", "build_job", "build_sources"} <= set(inputs):
                raise ValueError("missing source identity")
            evidence_dir = Path(ref["path"]).parent / "evidence"
            def verify_retained(file):
                if (not Path(file["origin_path"]).is_absolute() or
                        Path(file["path"]).parent != evidence_dir or
                        Path(file["path"]).name != file["sha256"]):
                    raise ValueError("retained evidence locator invalid")
                verify_once(file)
            large = start.get('large_refs',[])
            if (len(large) != len(set(large)) or any(not re.fullmatch(
                    r'(?:model_shard_[1-9][0-9]*|drafter(?:_shard_[1-9][0-9]*)?)',key)
                    or key not in inputs for key in large)):
                raise ValueError('invalid native large artifact references')
            for key, file in inputs.items():
                if key not in {"binary", "model", *large}:
                    verify_retained(file)
                else:
                    verify_once(file)
            if _read(inputs["grant"]).decode() != start["grant"]:
                raise ValueError("grant literal differs from grant file")
            binding = json.loads(_read(inputs["binding"]))
            recipe_bundle = json.loads(_read(inputs["recipe"]))
            if binding.get("recipes_sha256") != inputs["recipe"]["sha256"]:
                raise ValueError("owner binding differs from recipe bundle")
            build_dir = Path(_read(inputs["build_receipt_binding"]).decode().strip())
            if not build_dir.is_absolute() or any(Path(inputs[key]["origin_path"]).parent != build_dir for key in
                    ("build_complete", "build_log", "elf_manifest", "build_job", "build_sources")):
                raise ValueError("build receipt directory differs from owner binding")
            matching = [item for item in recipe_bundle["workloads"]
                        if item.get("id") == identity["workload_id"]]
            if len(matching) != 1 or matching[0] != identity["recipe"] or recipe_bundle["kernel_commit"] != start["kernel_commit"]:
                raise ValueError("census differs from owner-bound recipe")
            complete = _read(inputs["build_complete"]).decode().strip()
            build_match = re.fullmatch(r"BUILD_COMPLETE source=" + re.escape(start["kernel_commit"]) +
                                r" kind=" + ('hip' if backend == 'gpu' else 'cpu') +
                                r" end=(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) no-model-runs=true", complete)
            if not build_match:
                raise ValueError("native build completion does not bind commit")
            build_time = datetime.datetime.strptime(build_match[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
            if int(build_time) * 1_000_000_000 > start["started_ns"]:
                raise ValueError("build completed after attempt start")
            if not _read(inputs["build_log"]).decode(errors="replace").startswith(
                    "source=" + start["kernel_commit"] + " "):
                raise ValueError("native build log does not bind commit")
            for manifest_key in ("build_sources", "source_manifest"):
                if manifest_key not in inputs:
                    continue
                source_lines = _read(inputs[manifest_key]).decode().splitlines()
                sources = start["manifest_sources"][manifest_key]
                listed = {}
                for line in source_lines:
                    match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
                    if not match or not Path(match[2]).is_absolute() or match[2] in listed:
                        raise ValueError("malformed source manifest")
                    listed[match[2]] = match[1]
                if not listed or set(listed) != set(sources):
                    raise ValueError("source manifest capture incomplete")
                for original, digest in listed.items():
                    captured = sources[original]
                    if captured["origin_path"] != original or captured["sha256"] != digest:
                        raise ValueError("source capture differs from native manifest")
                    verify_retained(captured)
            elf_manifest = {}
            for line in _read(inputs["elf_manifest"]).decode().splitlines():
                match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
                if not match or match[2] in elf_manifest:
                    raise ValueError("malformed ELF manifest")
                elf_manifest[match[2]] = match[1]
            if elf_manifest.get(inputs["binary"]["path"]) != inputs["binary"]["sha256"]:
                raise ValueError("binary absent or changed from build ELF manifest")
            server = row.get('instrument') == 'server'
            if (start['argv'].count(inputs['binary']['path']) != 1 if server
                    else start["argv"][0] != inputs["binary"]["path"]):
                raise ValueError("binary differs")
            if (start["argv"].count("-m") != 1 or
                    start["argv"][start["argv"].index("-m") + 1] != inputs["model"]["path"]):
                raise ValueError("model absent from argv")
            argv = start["argv"]
            if not server and (argv.count("-p") != 1 or argv.count("-n") != 1):
                raise ValueError("ambiguous workload argv")
            phase, tokens, seq = shape["phase"], shape["n_tokens"], shape["n_seq"]
            if phase not in ("prefill", "decode", "verify") or type(tokens) is not int or tokens < 0 or type(seq) is not int or seq < 1:
                raise ValueError("invalid native shape")
            if not server and (argv[argv.index("-p") + 1] != str(tokens if phase == "prefill" else 0) or argv[argv.index("-n") + 1] != str(0 if phase == "prefill" else tokens)):
                raise ValueError("argv workload differs from native shape")
            if not server:
                raise ValueError("scheduler capture lacks native API and tensor-width proof")
            if (server and (argv.count('-np') != 1 or argv[argv.index('-np')+1] != str(seq))) or (not server and ((seq == 1 and "-np" in argv) or (seq > 1 and (argv.count("-np") != 1 or argv[argv.index("-np") + 1] != str(seq))))):
                raise ValueError("argv parallelism differs from native shape")
            if (identity["kernel"]["commit"] != start["kernel_commit"] or
                identity["kernel"]["binary_sha256"] != inputs["binary"]["sha256"] or
                identity["model"]["sha256"] != inputs["model"]["sha256"] or
                identity["model"]["path"] != inputs["model"]["path"]):
                raise ValueError("identity differs from prelaunch inputs")
            if end["ended_ns"] > int(start["deadline"]) * 1_000_000_000:
                raise ValueError("attempt exceeded grant deadline")
            dsos = end["loaded_dsos"]
            for file in dsos.values():
                verify_once(file)
                if not file.get("mapped_identity") or file.get("mapped_identity") != file.get("hashed_identity"):
                    raise ValueError("loaded DSO identity changed before hash")
                instrument = inputs.get('instrument_library')
                if instrument and file['path'] == instrument.get('origin_path'):
                    if file['sha256'] != instrument['sha256'] or start['env'].get('LD_PRELOAD') != file['path']:
                        raise ValueError('loaded instrument differs from captured input')
                elif elf_manifest.get(file["path"]) != file["sha256"]:
                    raise ValueError("loaded DSO differs from build ELF manifest")
            samples = end["samples"]
            if (type(end["spawned_ns"]) is not int or not start["started_ns"] <= end["spawned_ns"] <= end["ended_ns"] or
                len(samples) < 2 or
                any(not end["spawned_ns"] <= s["utc_ns"] <= end["ended_ns"] for s in samples)):
                raise ValueError("missing during-run samples")
            library = 'libggml-hip.so' if backend == 'gpu' else 'libggml-cpu.so'
            if not dsos or not any(library in x['path'] for x in dsos.values()):
                raise ValueError('required loaded backend identity absent')
            positive = [s for s in samples if s.get('task_affinity')
                        and any('/'+library in p for p in s.get('loaded_ggml',[]))
                        and (not server or s.get('phase') == 'requests')
                        and (backend == 'cpu' or ((s.get('own_vram_bytes') or 0) > (1 << 30)
                            and (s.get('global_vram_bytes') or 0) > (1 << 30)
                            and (s.get('kfd_processes') or 0) > 0))]
            if len(positive) < 2:
                raise ValueError("residency unproven")
            if not positive[0].get('pid') or len({s.get('pid') for s in samples}) != 1:
                raise ValueError("samples do not belong to one process")
            if not start["env"].get("FILLER_CPUS") or any(
                not _affinity_ok(s,start['env']['FILLER_CPUS']) for s in positive):
                raise ValueError("process affinity differs from claim")
            if any(not _affinity_ok(s,start['env']['FILLER_CPUS']) for s in samples):
                raise ValueError("task escaped claim affinity")
            actual_paths = {x["path"] for x in dsos.values()}
            if not all(set(s["loaded_ggml"]+s.get('loaded_instrument',[])) <= actual_paths for s in positive):
                raise ValueError("loaded DSO not sealed")
            log = _read(end["log"]).decode("utf-8", errors="replace")
            plain = ANSI.sub("", log)
            counts: dict[str, dict[str, int]] = {}
            if server:
                if start['inputs']['requests']['origin_path'] != identity['recipe']['request_files'][phase]:
                    raise ValueError('native frozen request source differs from bound recipe')
                graph = _server_graph(row,start,end,identity)
                counts = graph['op_backend']
            else:
                for op, device_backend in NODE.findall(plain):
                    counts.setdefault(op, {})[device_backend] = counts.setdefault(op, {}).get(device_backend, 0) + 1
            total = sum(sum(v.values()) for v in counts.values())
            if total <= 1000 or total != row["nodes_total"] or counts != row["op_backend"]:
                raise ValueError("scheduler log differs from census")
            device_seen = (any((s.get('own_vram_bytes') or 0) > (1 << 30) for s in samples)
                           if server else bool(re.search(r"(?:Device\s+\d+:|using device)\s+.*(?:MI\d+|gfx\d+)", plain, re.I)))
            if (backend == 'gpu' and not device_seen) or row["device_seen"] is not device_seen:
                raise ValueError("required GPU device marker missing or differs")
            if not set(identity["recipe"]["expected_ops"]) <= set(counts):
                raise ValueError("required scheduler ops missing")
            result.append({"sidecar": str(path), "sidecar_sha256": hashlib.sha256(raw).hexdigest(),
                "record_sha256": envelope["record"]["sha256"], "shape": shape, "row": row,
                "identity": identity, "start": start, "end": end})
        return tuple(result)
    except (KeyError, IndexError, TypeError, ValueError, UnicodeError) as exc:
        raise ProjectionError(f"census warrant refused: {exc}") from exc


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or native not in native_rows(native.get("sidecar", "")):
        raise ProjectionError("row differs from native capture")
    return _project_checked(native)


def _project_checked(native: dict) -> ClaimTuple:
    shape, row, start, end = native["shape"], native["row"], native["start"], native["end"]
    timestamp = datetime.datetime.fromtimestamp(end["ended_ns"] / 1e9, datetime.timezone.utc).isoformat()
    return ClaimTuple(measurement_id=f"census:{native['record_sha256']}:{start['attempt_id']}",
        metric="census_shape_observed", value=1, date=timestamp, category="CANDIDATE",
        claim=f"Observed {row['nodes_total']} scheduler nodes for {native['identity']['workload_id']} {shape}",
        metric_direction="higher_better", protocol_id="", unit="boolean", source_kind=SOURCE_KIND,
        attestation_path=native["sidecar"], attestation_sha256=native["sidecar_sha256"],
        attestation_locator=f"{native['sidecar']}#{start['attempt_id']}",
        attestation_present=True, attestation_verified=True,
        applicability={"shape": str(shape), "build_sha": start["kernel_commit"],
                       "model_file": native["identity"]["model"]["path"],
                       "model_sha256": native["identity"]["model"]["sha256"], "backend": native['identity'].get('backend','gpu')},
        extra={"record_sha256": native["record_sha256"], "nodes_total": row["nodes_total"],
               "op_backend": row["op_backend"]})


def frames_for_record(path: str | Path, *, as_of: str) -> list[dict]:
    return [frame for row in native_rows(path) for frame in
            to_frames(_project_checked(row), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)]
