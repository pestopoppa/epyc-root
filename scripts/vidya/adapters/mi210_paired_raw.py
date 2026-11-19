"""Project prospective native requests as observations through the shared carrier.

No protocol was attested by these producers. A sealed raw run establishes custody,
not a protocol. This module supplies no grading ladder or causal/promotion claim.
"""
import hashlib
import re
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.vidya.producers import mi210_paired_capture as raw  # noqa: E402

SOURCE_KIND = "mi210-paired-raw"
ADAPTER_ID = "vidya.adapters.mi210_paired_raw/v1"
AUTHORITY = "measurement"
DIAGNOSTIC_SCOPE = "One native request from the captured launch; no protocol or paired effect."


def _model_scope(declaration):
    """Match the pinned single-file weights and declared Q38 GPU recipe."""
    model = declaration["model"]
    if declaration["source"] != "Q38P-3a" or not isinstance(model, list) or len(model) != 1:
        return {}
    identity = model[0]
    if not isinstance(identity, dict) or identity.get("error") is not None:
        return {}
    path, digest = identity.get("path"), identity.get("sha256")
    if not isinstance(path, str) or Path(path).suffix.lower() != ".gguf":
        return {}
    if re.search(r"-\d{5}-of-\d{5}\.gguf$", Path(path).name, re.IGNORECASE):
        return {}
    if not isinstance(digest, str) or not raw.carrier.SHA256.fullmatch(digest):
        return {}
    commands = declaration["recipe"].get("argv")
    if not isinstance(commands, dict):
        return {}
    expected_flags = {"-m": path, "-ngl": "all", "--device": "ROCm0"}
    aliases = {"--model", "--gpu-layers", "--n-gpu-layers", "-dev"}
    for _, arm in declaration["order"]:
        argv = commands.get(arm)
        if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
            return {}
        if any(arg.partition("=")[0] in aliases or
               ("=" in arg and arg.partition("=")[0] in expected_flags) for arg in argv):
            return {}
        for flag, value in expected_flags.items():
            if argv.count(flag) != 1:
                return {}
            index = argv.index(flag) + 1
            if index == len(argv) or argv[index] != value:
                return {}
    return {"model_sha256": digest, "backend": "gpu", "scope_basis": "native"}


def project(root):
    root = raw._root(root)
    run = raw.read(root)
    intent = run["intent"]
    declaration = intent["declaration"]
    if run["state"] != "complete" or declaration["mode"] != "measurement":
        raise ValueError("only complete measurement-scope raw runs project")
    source = declaration["source"]
    scope = _model_scope(declaration)
    categories = declaration["recipe"].get("arm_categories", {})
    tuples = []
    for attempt in run["attempts"]:
        native = attempt["native"]
        category = categories.get(native["arm"])
        if category not in raw.carrier.CATEGORIES:
            raise ValueError("native arm category missing")
        requests = native["requests"]
        if not isinstance(requests, list) or not requests:
            raise ValueError("native request timings missing")
        for index, request in enumerate(requests):
            timing = request.get("timings")
            if not isinstance(timing, dict):
                raise ValueError("full native timing record required")
            count, ms = timing.get("predicted_n"), timing.get("predicted_ms")
            if type(count) is not int or count <= 0 or not raw.carrier.finite(ms) or ms <= 0:
                raise ValueError("native timing denominator")
            if source == "NPD1-STEP3":
                metric, value, unit, direction = "native_request_tpot_ms", ms / count, "ms/token", "lower_better"
            else:
                metric, value, unit, direction = "native_request_decode_tps", timing.get("predicted_per_second"), "token/s", "higher_better"
                if not raw.carrier.finite(value) or value <= 0:
                    raise ValueError("native decode rate missing")
            path = root / f"attempt-{attempt['index']:02d}.json"
            rid = intent["run_id"]
            key = f"{rid}/{attempt['index']}/{index}/{metric}"
            row = {"schema": raw.SCHEMA, "producer": source, "run_id": rid,
                   "measurement_id": "mi210_" + hashlib.sha256(key.encode()).hexdigest()[:24],
                   "metric": metric, "value": value, "unit": unit,
                   "metric_direction": direction, "category": category,
                   "claim": f"{source} {native['pair']}/{native['arm']} request {index} native diagnostic {metric}",
                   "date": intent["date"], "emitted_at": intent["date"],
                   "protocol_id": "", "reps": 1, "reps_basis": "one-native-completed-request",
                   "results_path": str(path), "results_sha256": raw.carrier.file_sha256(path),
                   "extra": {"scope": "prospective diagnostic observation; no protocol attestation",
                             "declaration": declaration, "native": native,
                             "terminal_sha256": run["terminal"]["row_sha256"]}}
            row["row_sha256"] = raw.carrier.row_digest(row)
            projected = raw.carrier.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=str(path))
            tuples.append(replace(projected, applicability=scope,
                                  observation={"outcome_reason": DIAGNOSTIC_SCOPE}))
    return tuples


def emit(path, *, as_of, limit=None):
    """Read and validate the whole run once, then emit per-request shared frames."""
    from claim_tuple import ProjectionError, to_frames

    try:
        return [frame for row in project(path)[:limit]
                for frame in to_frames(row, as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY)]
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        raise ProjectionError(f"invalid MI210 raw capture: {exc}") from exc
