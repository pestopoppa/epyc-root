"""Strict projection of the native CS-22.V0 four-arm parity receipt.

Relocation is explicit: CS22V0_RELOCATIONS names a JSON object mapping recorded
absolute file names to current byte-identical copies. Original names and hashes
remain in the native evidence. No new warrant or grading ladder is created.
"""
from __future__ import annotations
import hashlib
import types
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = "vidya.adapters.cs22v0_parity/v1"
AUTHORITY = "fixed_corpus_verifier_no_timing_no_quality"

ARMS = ("whisper", "gguf", "jit")
POINTS = ((.5, .3), (.5, .5), (.5, .75), (.5, 1.0), (.5, 1.2), (.6, 1.2))
ONNX = "4cbf549b8326f60f80f2536d9eefeb450a9abe83365a098031c89719f1be17d2"
MANIFEST = "f27786317203b724c859c9da5d85f56ab1cac07f25ef84dfeaab77bd3fafc46f"
CODE = {"cs47_stops.py": "af410f114749b5f78155c8e0de114769cbccf093a6e0e3fcae029921ce514ca4", "serving_segments.py": "ee638d7961a529023e9aae9414080c2196640e7b098345c86779eca68e85957e", "native_executor.py": "4a591dfefb1e580825283cb6692d15b2e26eb3c83a640cb035f260aeb0d9c9ef", "native_receipt.py": "46e3bb27eaa9bf7f25ea1d8b6f28c40e1f1b993e941e69ba9e73eee472417ba0"}

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()

def _json(path):
    return json.loads(Path(path).read_text())

def _resolve(name, digest, reloc):
    name = str(name)
    if not Path(name).is_absolute() or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid recorded path or digest")
    p = Path(reloc.get(name, name))
    if not p.is_absolute() or sha(p) != digest:
        raise ValueError("recorded file missing or changed: " + name)
    return p

def _module(path, name, digest):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("pinned comparator changed")
    module = types.ModuleType(name)
    exec(compile(data, str(path), "exec"), module.__dict__)
    return module

def _read(receipt_path, reloc):
    rp = Path(receipt_path).resolve()
    rec = _json(rp)
    if rec.get("schema") != "epyc.cs22_v0.verifier_receipt.v1":
        return ()
    if rec.get("protocol_id") != "" or rec.get("co_tenant") != "UNKNOWN/unobserved":
        raise ValueError("invalid receipt scope")
    pp = _resolve(rec["predeclaration_path"], rec["predeclaration_sha256"], reloc)
    resultpath = _resolve(rec["native_result_path"], rec["native_result_sha256"], reloc)
    pre, result = _json(pp), _json(resultpath)
    if pre.get("schema") != "epyc.cs22_v0.predeclaration.v1" or pre.get("protocol_id") != "" or pre.get("co_tenant") != "UNKNOWN/unobserved" or pre.get("posterior_tolerance", "missing") is not None:
        raise ValueError("invalid predeclaration scope")
    props = {a: f"On all 224 pinned CS45 clips, {a} matches the pinned ONNX reference for CS47 stop events and for segments derived by the recorded common serving-policy segmenter at all six threshold/silence settings." for a in ARMS}
    if pre.get("propositions") != props or pre.get("reference_sha256") != ONNX or pre.get("corpus_manifest_sha256") != MANIFEST:
        raise ValueError("unexpected predeclared proposition or corpus")
    stop_contract = "CS47 threshold 0.5 at silence 0.3,0.5,0.75,1.0,1.2 seconds and threshold 0.6 at silence 1.2 seconds; sustained onset 0.1 seconds"
    segment_contract = "common postprocessor implementing transcribe Silero offline policy: negative=max(threshold-0.15,0.01), min speech 250ms, silence as point, pad 30ms, max speech unlimited"
    if pre.get("stop_contract") != stop_contract or pre.get("segment_contract") != segment_contract or result.get("stop_contract") != "CS47 sustained onset 0.1s; full 512-sample frames" or result.get("segment_contract") != "common postprocessor implementing transcribe Silero offline defaults: min_speech_ms=250, pad_ms=30, neg=max(threshold-0.15,0.01), max_speech_ms=0":
        raise ValueError("comparator contract mismatch")
    config = _resolve(pre["source_config_path"], pre["source_config_sha256"], reloc)
    cfg = _json(config)
    manifest = _resolve(pre["source_manifest_path"], pre["source_manifest_sha256"], reloc)
    source_files = {}
    for line in manifest.read_text().splitlines():
        digest, original = line.split("  ", 1)
        if original in source_files:
            raise ValueError("duplicate source")
        source_files[original] = (digest, _resolve(original, digest, reloc))
    code = {}
    for name, digest in CODE.items():
        hits = [p for original, (h, p) in source_files.items() if Path(original).name == name and h == digest]
        if len(hits) != 1:
            raise ValueError("missing pinned producer code: " + name)
        code[name] = hits[0]
    stop = _module(code["cs47_stops.py"], "cs22v0_original_stops", CODE["cs47_stops.py"])
    seg = _module(code["serving_segments.py"], "cs22v0_original_segments", CODE["serving_segments.py"])
    if tuple(stop.POINTS) != POINTS:
        raise ValueError("stop settings changed")
    required = {"onnx", "whisper_model", "gguf_model", "jit_model", "whisper_binary", "gguf_binary", "adapter", "comparator", "corpus_manifest"}
    if set(cfg["files"]) != required or cfg["expected_clips"] != 224:
        raise ValueError("incomplete input warrant")
    for item in cfg["files"].values():
        _resolve(item["path"], item["sha256"], reloc)
    if cfg["files"]["onnx"]["sha256"] != ONNX or cfg["files"]["corpus_manifest"]["sha256"] != MANIFEST:
        raise ValueError("input pin mismatch")
    if pre["model_sha256"] != {a: cfg["files"][{"whisper":"whisper_model", "gguf":"gguf_model", "jit":"jit_model"}[a]]["sha256"] for a in ARMS}:
        raise ValueError("model pin mismatch")
    precheck = rp.parent / "precheck"
    actual = {str(p.relative_to(precheck)): sha(p) for p in sorted(precheck.rglob("*")) if p.is_file()}
    if actual != pre["precheck_sha256"] or actual.get("warrant.json") != pre["warrant_sha256"]:
        raise ValueError("precheck mismatch")
    proof = _json(precheck / "warrant.json")
    expected_files = [{"label": k, "path": v["path"], "sha256": v["sha256"]} for k, v in cfg["files"].items()]
    if proof.get("files") != expected_files or proof.get("repos") != cfg["repos"] or proof.get("clips") != 224 or proof.get("manifest_sha256") != MANIFEST:
        raise ValueError("warrant content mismatch")
    if {r["commit"] for r in cfg["repos"]} != {"db678a031cf4c524bcab2c45a0dc6a7813106e4a", "b307379226d93d9c5ed790d7cea0626613c0ef4b"}:
        raise ValueError("source revisions missing")
    for repo in cfg["repos"]:
        current = subprocess.check_output(["git", "-c", "safe.directory=" + repo["path"], "-C", repo["path"], "rev-parse", "HEAD"], text=True).strip()
        if current != repo["commit"]:
            raise ValueError("source revision changed")
    if hashlib.sha256(pre["grant_contents"].encode()).hexdigest() != pre["grant_sha256"] or not pre["affinity"] or set(pre["commands"]) != set(("reference",) + ARMS):
        raise ValueError("execution provenance mismatch")
    m = re.search(r"\bstart=(\d{4}-\d\d-\d\d)T", pre["grant_contents"])
    if not m:
        raise ValueError("grant date missing")
    date = m.group(1)
    rows = [_json_line for line in _resolve(cfg["files"]["corpus_manifest"]["path"], MANIFEST, reloc).read_text().splitlines() if line.strip() for _json_line in [json.loads(line)]]
    if len(rows) != 224 or len({x["clip_id"] for x in rows}) != 224:
        raise ValueError("corpus cardinality")
    rawdir = resultpath.parent / "raw"
    raw = {p.name: p for p in rawdir.iterdir() if p.is_file()}
    expected_names = {"{}.{}.{}".format(x["clip_id"], a, suffix) for x in rows for a in ("reference",) + ARMS for suffix in ("stdout", "stderr", "status.json")}
    if set(raw) != expected_names or set(rec["raw_sha256"]) != expected_names or any(sha(p) != rec["raw_sha256"][n] for n, p in raw.items()):
        raise ValueError("raw evidence missing or changed")
    if result.get("complete") is not True or result.get("errors") != [] or set(result.get("exclusions", {})) != set(ARMS) or result.get("expected_clips") != 224 or result.get("expected_comparisons") != 672 or len(result["comparisons"]) != 672:
        raise ValueError("incomplete result")
    comparisons = {(r["clip"], r["arm"]): r for r in result["comparisons"]}
    if len(comparisons) != 672:
        raise ValueError("duplicate comparisons")
    mismatch = {a: 0 for a in ARMS}
    stop_mismatch = {a: 0 for a in ARMS}
    segment_mismatch = {a: 0 for a in ARMS}
    maxima = {a: 0.0 for a in ARMS}
    clips_dir = Path(cfg["clips_dir"])
    for item in rows:
        clip = item["clip_id"]
        if Path(clip).name != clip:
            raise ValueError("invalid clip id")
        wav_name = str(clips_dir / (clip + ".wav"))
        wav = Path(reloc.get(wav_name, wav_name))
        with wave.open(str(wav), "rb") as w:
            if (w.getframerate(), w.getsampwidth(), w.getnchannels(), w.getnframes()) != (16000, 2, 2, item["pcm"]["n_samples"]):
                raise ValueError("PCM format mismatch")
            if hashlib.sha256(w.readframes(w.getnframes())).hexdigest() != item["pcm"]["pcm_sha256"]:
                raise ValueError("PCM digest mismatch")
        frames = item["pcm"]["n_samples"] // 512
        if frames == 0:
            raise ValueError("frame count")
        arrays = {}
        for a in ("reference",) + ARMS:
            prefix = f"{clip}.{a}"
            status = _json(raw[prefix + ".status.json"])
            err = raw[prefix + ".stderr"].read_text().lower()
            obj = _json(raw[prefix + ".stdout"])
            probs = obj["probs"]
            if type(status.get("rc")) is not int or status["rc"] != 0 or (a == "whisper" and ("failed to compute vad graph" in err or "vad time =" not in err)) or obj.get("clip") != clip or len(probs) != frames or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in probs):
                raise ValueError("invalid native status or posterior")
            arrays[a] = probs
        ref = arrays["reference"]
        for a in ARMS:
            row, p = comparisons[(clip, a)], arrays[a]
            delta = max(abs(x-y) for x, y in zip(ref, p))
            maxima[a] = max(maxima[a], delta)
            if row["frames"] != frames or row["max_abs_diff"] != delta or set(row["operating_points"]) != {f"{t}:{s}" for t, s in POINTS}:
                raise ValueError("posterior summary mismatch")
            for threshold, silence in POINTS:
                expected = {"cs47_stop_equal": stop.stop_fires(ref, threshold, silence) == stop.stop_fires(p, threshold, silence), "serving_segments_equal": seg.segments(ref, threshold, int(silence*1000), frames*512) == seg.segments(p, threshold, int(silence*1000), frames*512)}
                if set(row["operating_points"][f"{threshold}:{silence}"]) != set(expected) or any(type(v) is not bool for v in row["operating_points"][f"{threshold}:{silence}"].values()) or row["operating_points"][f"{threshold}:{silence}"] != expected:
                    raise ValueError("event summary mismatch")
                mismatch[a] += not all(expected.values())
                stop_mismatch[a] += not expected["cs47_stop_equal"]
                segment_mismatch[a] += not expected["serving_segments_equal"]
    for a in ARMS:
        if type(result["exclusions"][a].get("eligible")) is not bool or any(type(result["exclusions"][a].get(k)) is not int for k in ("stop_mismatches", "segment_mismatches")) or result["exclusions"][a] != {"eligible": mismatch[a] == 0, "status": "complete", "stop_mismatches": stop_mismatch[a], "segment_mismatches": segment_mismatch[a]}:
            raise ValueError("exclusion summary mismatch")
    recorded = rec["propositions"]
    if len(recorded) != 3 or {x["arm"] for x in recorded} != set(ARMS):
        raise ValueError("proposition set")
    for x in recorded:
        a = x["arm"]
        if x["decided_proposition"] != props[a] or type(x["result"]) is not bool or x["result"] != (mismatch[a] == 0):
            raise ValueError("proposition mismatch")
    return tuple({"receipt_path": str(rp), "receipt_sha256": sha(rp), "predeclaration_sha256": rec["predeclaration_sha256"], "arm": a, "proposition": props[a], "value": mismatch[a] == 0, "max_abs_diff": maxima[a], "date": date, "relocations": reloc} for a in ARMS)

def native_rows(path):
    try:
        loc = os.environ.get("CS22V0_RELOCATIONS")
        reloc = _json(loc) if loc else {}
        if not isinstance(reloc, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k,v in reloc.items()):
            raise ValueError("invalid relocation map")
        return _read(path, reloc)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, subprocess.SubprocessError) as exc:
        raise ProjectionError(f"CS22V0 receipt refused: {exc}") from exc

@register("cs22v0-parity", source_class="verifier", decided_proposition_field="decided_proposition")
def project(native):
    try:
        rows = _read(native["receipt_path"], native["relocations"])
        if native not in rows:
            raise ValueError("native evidence changed on reopen")
        return ClaimTuple(measurement_id="cs22v0:" + native["receipt_sha256"] + ":" + native["arm"], metric="fixed_corpus_event_equality", value=native["value"], date=native["date"], category="CANDIDATE", metric_direction="higher_better", claim=native["proposition"], decided_proposition=native["proposition"], source_class="verifier", source_kind=ADAPTER_ID, binding_kind="identity", protocol_id="", reps=224, reps_basis="scored", attestation_locator=native["receipt_path"], extra={"predeclaration_sha256": native["predeclaration_sha256"], "receipt_sha256": native["receipt_sha256"], "arm": native["arm"], "posterior_max_abs_diff_descriptive": native["max_abs_diff"], "co_tenant": "UNKNOWN/unobserved", "date_basis": "grant start date", "scope": "fixed corpus and common postprocessor; no native segment API, timing, population quality or weight identity claim", "relocations": native["relocations"]})
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError, subprocess.SubprocessError) as exc:
        raise ProjectionError(f"CS22V0 projection refused: {exc}") from exc
