#!/usr/bin/env python3
"""Build and compare a prospective, observation-only kernel quality parity pack.

The v1 source declares capture source provenance, deployed serving shapes, and
banked production captures. The candidate supplies the same capture source
and serving identities, with a capture for each pinned request. Each capture
holds the original UTF-8 HTTP response body (base64 encoded), its SHA-256, and
the request SHA-256. It ties DFlash measurements to a server-instance ID,
slot count, and effective request cap. The CLI makes no inference requests.
"""

import argparse
import base64
import binascii
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


SOURCE_SCHEMA = "epyc.kernel_quality_parity_source.v1"
PACK_SCHEMA = "epyc.kernel_quality_parity_pack.v1"
CANDIDATE_SCHEMA = "epyc.kernel_quality_parity_candidate.v1"
REPORT_SCHEMA = "epyc.kernel_quality_parity_report.v1"
MANDATORY_SHAPES = {
    "frontdoor-cpu-moe-mtp",
    "worker-general-cpu-moe-mtp",
    "architect-critic-cpu-mtp",
    "ingest-long-context-recurrent-no-spec",
    "architect-general-hip",
    "worker-vision-hip-mmproj",
    "dspark-dflash",
}
PROMPTS = {"short", "long"}
FORMATS = {"json", "prose", "code", "reasoning"}
FIXTURES = {"loader-reshape", "recurrent-state"}
FINISHES = {"stop", "length"}
SHAPE_PINS = {
    "model_sha256", "recipe_sha256", "prompt_template_sha256", "sampling_sha256",
    "scorer_sha256", "question_pool_sha256", "endpoint_semantics_sha256",
    "generation_path_sha256",
}
SOURCE_FIELDS = {"schema", "capture_source", "runtime", "shapes", "items"}
SHAPE_FIELDS = {"id", "profile", "endpoint", *SHAPE_PINS}
ITEM_FIELDS = {
    "id", "shape", "request_body", "prompt_shape", "output_format", "fixture",
    "expected_finish", "validator", "dflash_pair", "production",
}
CAPTURE_FIELDS = {"request_sha256", "response_b64", "response_sha256"}
DFLASH_FIELDS = {"server_instance", "parallel_slots", "effective_n_max"}
CAP_KEY = "speculative.n_max"
ENDPOINTS = {"/completion", "/v1/chat/completions"}


class Incomplete(ValueError):
    """A declared coverage or capture row is missing."""


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def _json_hash(value):
    return _sha256(canonical_json(value))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _parse(raw):
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    canonical_json(value)
    return value


def _fields(value, expected, what):
    if not isinstance(value, dict) or value.keys() != expected:
        raise ValueError(f"{what} requires fields: {', '.join(sorted(expected))}")


def _named_rows(rows, what):
    if not isinstance(rows, list):
        raise ValueError(f"{what} must be a JSON array")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            raise ValueError(f"{what} requires nonempty IDs")
        if row["id"] in result:
            raise ValueError(f"duplicate {what} ID: {row['id']}")
        result[row["id"]] = row
    return result


def _digest(value, what, length=64):
    if not isinstance(value, str) or re.fullmatch(f"[0-9a-f]{{{length}}}", value) is None:
        raise ValueError(f"{what} requires a lowercase {length}-digit hex digest")


def _capture_source(value):
    _fields(value, {"commit", "tree", "source_sha256"}, "capture_source")
    for field in ("commit", "tree"):
        _digest(value[field], f"capture_source.{field}", length=40)
    _digest(value["source_sha256"], "capture_source.source_sha256")


def _runtime(value, shapes):
    _fields(value, set(shapes), "runtime shape coverage")
    for shape_id, identity in value.items():
        _fields(identity, {"kernel_commit", "kernel_tree", "binary_sha256"}, f"{shape_id} runtime")
        for field in ("kernel_commit", "kernel_tree"):
            _digest(identity[field], f"{shape_id}.{field}", length=40)
        _digest(identity["binary_sha256"], f"{shape_id}.binary_sha256")


def _shapes(rows):
    shapes = _named_rows(rows, "shape")
    profiles = set()
    for shape_id, shape in shapes.items():
        fields = SHAPE_FIELDS
        if shape.get("profile") == "dspark-dflash":
            fields = fields | {"validated_cap"}
            cap = shape.get("validated_cap")
            if type(cap) is not int or cap <= 0:
                raise ValueError(f"{shape_id}: validated_cap must be a positive integer")
        _fields(shape, fields, shape_id)
        if shape["profile"] not in MANDATORY_SHAPES or shape["endpoint"] not in ENDPOINTS:
            raise ValueError(f"{shape_id}: unsupported profile or endpoint")
        for field in SHAPE_PINS:
            _digest(shape[field], f"{shape_id}.{field}")
        profiles.add(shape["profile"])
    if missing := MANDATORY_SHAPES - profiles:
        raise Incomplete(f"missing mandatory serving profiles: {', '.join(sorted(missing))}")
    return shapes


def _request(body, endpoint):
    if not isinstance(body, dict):
        raise ValueError("request_body must be an object")
    seed = body.get("seed")
    if type(seed) is not int or not 0 <= seed < 2**32 - 1:
        raise ValueError("request_body requires a fixed seed")
    if body.get("stream", False) is not False or body.get("cache_prompt") is not False:
        raise ValueError("request_body requires stream: false and cache_prompt: false")
    temperature = body.get("temperature")
    if type(temperature) not in (int, float) or temperature != 0:
        raise ValueError("request_body requires temperature: 0")

    if endpoint == "/completion":
        prompt, limit = body.get("prompt"), body.get("n_predict")
        if "messages" in body or "max_tokens" in body or not isinstance(prompt, str) or not prompt:
            raise ValueError("native request requires prompt and n_predict")
    else:
        prompt, limit = body.get("messages"), body.get("max_tokens")
        if ("prompt" in body or "n_predict" in body or not isinstance(prompt, list) or not prompt
                or any(not isinstance(message, dict) or not isinstance(message.get("role"), str)
                       or not message["role"] or "content" not in message for message in prompt)):
            raise ValueError("chat request requires messages and max_tokens")
    if type(limit) is not int or limit <= 0:
        raise ValueError("request_body requires a positive output token limit")
    return _json_hash(prompt), limit


def _semantic_matches(validator, content):
    if not isinstance(validator, dict):
        raise ValueError("validator requires a versioned identity")
    _fields(validator, {"id", "expected"}, "validator")
    validator_id, expected = validator["id"], validator["expected"]
    if validator_id in ("exact-text.v1", "contains-text.v1"):
        if not isinstance(expected, str) or not expected.strip():
            raise ValueError(f"{validator_id} requires nonempty expected text")
        return content == expected if validator_id == "exact-text.v1" else expected in content
    if validator_id == "json-object-subset.v1":
        if not isinstance(expected, dict) or not expected:
            raise ValueError(f"{validator_id} requires a nonempty expected object")
        try:
            actual = _parse(content.encode("utf-8"))
        except ValueError:
            return False
        return isinstance(actual, dict) and all(
            key in actual and canonical_json(actual[key]) == canonical_json(value)
            for key, value in expected.items()
        )
    raise ValueError(f"unsupported semantic validator: {validator_id!r}")


def _tokens(*aliases):
    exposed = [tokens for tokens in aliases if tokens is not None]
    if not exposed:
        return None
    for tokens in exposed:
        if not isinstance(tokens, list) or any(type(token) is not int or token < 0 for token in tokens):
            raise ValueError("invalid output token IDs")
        if tokens != exposed[0]:
            raise ValueError("conflicting exposed output token IDs")
    return exposed[0] or None


def _completion_count(data, details, tokens, finish, limit):
    counts = []
    for envelope, key in ((data, "usage"), (data, "timings"), (details, "timings")):
        if key in envelope and not isinstance(envelope[key], dict):
            raise ValueError(f"invalid response {key} object")
        inner = envelope.get(key, {})
        count_field = "completion_tokens" if key == "usage" else "predicted_n"
        if count_field in inner:
            counts.append(inner[count_field])
    if "tokens_predicted" in details:
        counts.append(details["tokens_predicted"])
    if not counts:
        return None
    if any(type(count) is not int or count <= 0 or count != counts[0] for count in counts):
        raise ValueError("invalid or conflicting response completion counts")
    count = counts[0]
    if tokens is not None and count != len(tokens):
        raise ValueError("response completion count differs from exposed output token IDs")
    if count > limit or (finish == "length" and count != limit):
        raise ValueError("response completion count contradicts the pinned token limit")
    return count


def _response(raw, endpoint, cap, limit):
    data = _parse(raw)
    if not isinstance(data, dict) or "error" in data:
        raise ValueError("capture requires a successful response object")
    if endpoint == "/completion":
        details = data
        content = data.get("content")
        reasoning = data.get("reasoning_content")
        finish = {"limit": "length", "eos": "stop", "word": "stop"}.get(data.get("stop_type"))
        tokens = _tokens(data.get("tokens"))
    else:
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise ValueError("capture requires exactly one chat choice")
        choice = choices[0]
        message = choice.get("message")
        verbose = data.get("__verbose", {})
        if not isinstance(message, dict) or not isinstance(verbose, dict) or message.get("tool_calls"):
            raise ValueError("capture requires a text chat message")
        details = verbose
        content = message.get("content")
        reasoning = message.get("reasoning_content")
        finish = choice.get("finish_reason")
        tokens = _tokens(data.get("tokens"), choice.get("tokens"), verbose.get("tokens"))
    if not isinstance(content, str) or (reasoning is not None and not isinstance(reasoning, str)):
        raise ValueError("capture requires text content and optional text reasoning")
    if finish not in ("stop", "length"):
        raise ValueError("capture lacks a supported finish condition")
    if cap is not None:
        settings = details.get("generation_settings")
        echoed = settings.get(CAP_KEY) if isinstance(settings, dict) else None
        if type(echoed) is not int or echoed != cap:
            raise ValueError("DFlash response does not echo the pinned effective n_max")
    count = _completion_count(data, details, tokens, finish, limit)
    return content, reasoning, finish, tokens, count


def _capture(capture, request_sha256, endpoint, cap, limit):
    _fields(capture, CAPTURE_FIELDS | (DFLASH_FIELDS if cap is not None else set()), "capture")
    if capture["request_sha256"] != request_sha256:
        raise ValueError("capture request hash mismatch")
    try:
        raw = base64.b64decode(capture["response_b64"], validate=True)
    except (TypeError, ValueError, binascii.Error) as exc:
        raise ValueError("capture requires base64 response bytes") from exc
    if base64.b64encode(raw).decode("ascii") != capture["response_b64"]:
        raise ValueError("capture base64 is not canonical")
    if _sha256(raw) != capture["response_sha256"]:
        raise ValueError("response byte hash mismatch")
    if cap is not None:
        server, slots, effective = (capture[key] for key in ("server_instance", "parallel_slots", "effective_n_max"))
        if not isinstance(server, str) or not server.strip() or type(slots) is not int or slots != 1:
            raise ValueError("DFlash capture requires a server instance with -np 1")
        if type(effective) is not int or effective != cap:
            raise ValueError("DFlash effective n_max differs from the pinned request")
    return _response(raw, endpoint, cap, limit)


def _pair_check(pairs, phase):
    """Require both cap arms of each request on the same server instance."""
    servers = {}
    for pair_id, rows in pairs.items():
        by_cap = {cap: (shape, body, server) for cap, shape, body, server in rows}
        if len(rows) != 2 or len(by_cap) != 2 or 0 not in by_cap:
            raise Incomplete(f"{phase} DFlash pair {pair_id!r} requires exactly two cap arms")
        if by_cap[0] != next(value for cap, value in by_cap.items() if cap != 0):
            raise ValueError(f"{phase} DFlash pair {pair_id!r} differs in shape, cap-free body, or server instance")
        shape, _, server = by_cap[0]
        if servers.setdefault(shape, server) != server:
            raise ValueError(f"{phase} DFlash shape {shape!r} used more than one server instance")


def _coverage(items, shapes, pairs):
    counts = Counter(item["shape"] for item in items)
    if len(items) < 32:
        raise Incomplete("coverage requires at least 32 distinct requests")
    if deficient := sorted(shape for shape in shapes if counts[shape] < 4):
        raise Incomplete(f"coverage requires four requests per shape: {', '.join(deficient)}")
    for field, required in (
        ("prompt_shape", PROMPTS), ("output_format", FORMATS), ("fixture", FIXTURES),
        ("expected_finish", FINISHES),
    ):
        if missing := required - {item[field] for item in items}:
            raise Incomplete(f"coverage missing {field}: {', '.join(sorted(missing))}")
    if len(pairs) < 4:
        raise Incomplete("coverage requires at least four paired DFlash requests")
    _pair_check(pairs, "production")
    return {
        "shape_counts": dict(counts),
        "prompt_shapes": sorted(PROMPTS),
        "output_formats": sorted(FORMATS),
        "fixtures": sorted(FIXTURES),
        "finishes": sorted(FINISHES),
        "dflash_pairs": sorted(pairs),
    }


def _pair_row(item, capture, cap):
    return (
        cap, item["shape"], _json_hash({key: value for key, value in item["request_body"].items() if key != CAP_KEY}),
        capture["server_instance"],
    )


def build_pack(source):
    """Validate and snapshot the prospective source and all production response bytes."""
    if not isinstance(source, dict) or source.get("schema") != SOURCE_SCHEMA:
        raise ValueError("unsupported parity source schema")
    _fields(source, SOURCE_FIELDS, "source")
    source = _parse(canonical_json(source))
    _capture_source(source["capture_source"])
    shapes = _shapes(source["shapes"])
    _runtime(source["runtime"], shapes)
    requests = set()
    pairs = {}
    items = []

    for item_id, item in sorted(_named_rows(source["items"], "item").items()):
        _fields(item, ITEM_FIELDS, item_id)
        shape = shapes.get(item["shape"])
        if shape is None:
            raise ValueError(f"{item_id}: unknown serving shape")
        if (item["prompt_shape"] not in PROMPTS or item["output_format"] not in FORMATS
                or item["fixture"] not in FIXTURES | {None} or item["expected_finish"] not in FINISHES):
            raise ValueError(f"{item_id}: unsupported coverage tag")
        body, endpoint = item["request_body"], shape["endpoint"]
        prompt_hash, limit = _request(body, endpoint)
        request_hash = _json_hash(body)
        request = (endpoint, request_hash)
        if request in requests:
            raise ValueError(f"{item_id}: duplicate canonical request")
        requests.add(request)
        cap, pair_id = body.get(CAP_KEY), item["dflash_pair"]
        if shape["profile"] == "dspark-dflash":
            if (type(cap) is not int or cap not in (0, shape["validated_cap"])
                    or not isinstance(pair_id, str) or not pair_id.strip()):
                raise ValueError(f"{item_id}: DFlash requires a pair and cap 0 or the validated positive cap")
        elif pair_id is not None or CAP_KEY in body:
            raise ValueError(f"{item_id}: unexpected DFlash metadata")

        capture = item["production"]
        content, reasoning, finish, tokens, count = _capture(capture, request_hash, endpoint, cap, limit)
        if finish != item["expected_finish"] or not _semantic_matches(item["validator"], content):
            raise ValueError(f"{item_id}: banked production failed finish or semantic validation")
        if item["output_format"] == "json" and item["validator"]["id"] != "json-object-subset.v1":
            raise ValueError(f"{item_id}: JSON coverage requires the JSON object validator")
        if cap is not None:
            pairs.setdefault(pair_id, []).append(_pair_row(item, capture, cap))
        items.append({
            **item,
            "request_sha256": request_hash,
            "prompt_sha256": prompt_hash,
            "seed": body["seed"],
            "token_limit": limit,
            "content_sha256": _sha256(content.encode("utf-8")),
            "reasoning_sha256": None if reasoning is None else _sha256(reasoning.encode("utf-8")),
            "output_token_ids": tokens,
            "completion_count": count,
        })

    return {
        "schema": PACK_SCHEMA,
        "observation_only": True,
        "tool_source_sha256": _sha256(Path(__file__).read_bytes()),
        "capture_source": source["capture_source"],
        "runtime": source["runtime"],
        "shapes": [shapes[key] for key in sorted(shapes)],
        "coverage_matrix": _coverage(items, shapes, pairs),
        "items": items,
    }


def _pack_source(pack):
    if not isinstance(pack, dict) or pack.get("schema") != PACK_SCHEMA:
        raise ValueError("unsupported parity pack schema")
    return {
        "schema": SOURCE_SCHEMA,
        "capture_source": pack["capture_source"],
        "runtime": pack["runtime"],
        "shapes": pack["shapes"],
        "items": [{key: item[key] for key in ITEM_FIELDS} for item in pack["items"]],
    }


def pack_bytes(pack):
    """The canonical bytes to publish and pin out of band by SHA-256."""
    return canonical_json(pack) + b"\n"


def compare_pack(pack, expected_sha256, candidate):
    """Compare prospective captures. Only the observation status selects the next investigation."""
    _digest(expected_sha256, "expected pack SHA-256")
    if _sha256(pack_bytes(pack)) != expected_sha256:
        raise ValueError("pack SHA-256 does not match the prospective pin")
    try:
        rebuilt = build_pack(_pack_source(pack))
    except (KeyError, TypeError) as exc:
        raise ValueError("invalid pack structure") from exc
    if pack_bytes(rebuilt) != pack_bytes(pack):
        raise ValueError("pack differs from its canonical build or tool source")

    if not isinstance(candidate, dict) or candidate.get("schema") != CANDIDATE_SCHEMA:
        raise ValueError("unsupported parity candidate schema")
    _fields(candidate, SOURCE_FIELDS | {"pack_sha256"}, "candidate")
    if candidate["pack_sha256"] != expected_sha256:
        raise ValueError("candidate pack SHA-256 does not match the prospective pin")
    _capture_source(candidate["capture_source"])
    candidate_shapes = _named_rows(candidate["shapes"], "candidate shape")
    _runtime(candidate["runtime"], candidate_shapes)
    candidate_items = _named_rows(candidate["items"], "candidate item")
    items = {item["id"]: item for item in pack["items"]}
    shapes = {shape["id"]: shape for shape in pack["shapes"]}
    report = {
        "schema": REPORT_SCHEMA,
        "observation_only": True,
        "quality_transfer_authorized": False,
        "promotion_authorized": False,
        "pack_sha256": expected_sha256,
        "production_runtime": pack["runtime"],
        "candidate_runtime": candidate["runtime"],
    }

    if (canonical_json(candidate_shapes) != canonical_json(shapes)
            or candidate["capture_source"] != pack["capture_source"]):
        return {**report, "status": "identity_drift", "next_action": "full_quality_regeneration"}
    if unknown := candidate_items.keys() - items.keys():
        raise ValueError(f"unexpected candidate items: {', '.join(sorted(unknown))}")
    if missing := items.keys() - candidate_items.keys():
        return {**report, "status": "incomplete", "next_action": "repeat_affected_role_window",
                "missing_items": sorted(missing)}

    pairs = {}
    failures = {}
    token_gaps = []
    count_gaps = []
    banked_gap = False
    for item_id, item in items.items():
        row = candidate_items[item_id]
        _fields(row, {"id", "capture"}, item_id)
        capture = row["capture"]
        shape = shapes[item["shape"]]
        cap = item["request_body"].get(CAP_KEY)
        limit = item["token_limit"]
        content, reasoning, finish, tokens, count = _capture(
            capture, item["request_sha256"], shape["endpoint"], cap, limit,
        )
        if cap is not None:
            pairs.setdefault(item["dflash_pair"], []).append(_pair_row(item, capture, cap))
        reasons = []
        if finish != item["expected_finish"]:
            reasons.append("finish_mismatch")
        if not _semantic_matches(item["validator"], content):
            reasons.append("semantic_validation_failed")
        banked = _response(base64.b64decode(item["production"]["response_b64"]), shape["endpoint"], cap, limit)
        if (content, reasoning) != banked[:2]:
            reasons.append("content_mismatch")
        if tokens is None or item["output_token_ids"] is None:
            token_gaps.append(item_id)
        elif tokens != item["output_token_ids"]:
            reasons.append("token_ids_mismatch")
        if count is None or item["completion_count"] is None:
            count_gaps.append(item_id)
        if item["output_token_ids"] is None or item["completion_count"] is None:
            banked_gap = True
        if reasons:
            failures[item_id] = reasons

    _pair_check(pairs, "candidate")
    if failures:
        return {**report, "status": "fail", "next_action": "full_quality_diagnostic",
                "failures": failures, "missing_token_ids": token_gaps,
                "missing_completion_counts": count_gaps}
    if token_gaps or count_gaps:
        next_action = "full_quality_regeneration" if banked_gap else "repeat_affected_role_window"
        return {**report, "status": "incomplete", "next_action": next_action,
                "missing_token_ids": token_gaps, "missing_completion_counts": count_gaps}
    return {**report, "status": "pass", "next_action": "record_observation", "matched_items": len(items)}


def _publish(output, payload):
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            os.link(temporary, output)
        finally:
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--source", required=True, type=Path)
    build.add_argument("--output", required=True, type=Path)
    compare = commands.add_parser("compare")
    compare.add_argument("--pack", required=True, type=Path)
    compare.add_argument("--pack-sha256", required=True)
    compare.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            payload = pack_bytes(build_pack(_parse(args.source.read_bytes())))
            _publish(args.output, payload)
            print(_sha256(payload))
            return 0
        payload = args.pack.read_bytes()
        if _sha256(payload) != args.pack_sha256:
            raise ValueError("pack file SHA-256 does not match the prospective pin")
        report = compare_pack(_parse(payload), args.pack_sha256, _parse(args.candidate.read_bytes()))
        print(canonical_json(report).decode("utf-8"))
        return {"pass": 0, "fail": 1, "incomplete": 2, "identity_drift": 2}[report["status"]]
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
