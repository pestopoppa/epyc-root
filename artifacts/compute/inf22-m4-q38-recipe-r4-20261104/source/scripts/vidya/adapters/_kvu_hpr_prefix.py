"""Validate the existing KVU request family's prospective HPR provenance; no grading or new metric.

Mirrors research c4c2a3638's native wire contract. Tests bind this copy to the actual producer.
Legacy requests are untouched. A complete capture remains an UNVERIFIED instrument observation.
"""
from __future__ import annotations

import hashlib
import json
import re

from claim_tuple import ProjectionError

SCHEMA = "epyc.kvu121.hpr_prefix_capture.v1"
CONTRACT = dict(
    version="epyc.kvu121.hpr_native_contract.v1", status="UNVERIFIED",
    template_sha256="1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551",
    message_delimiters=[{"role": "assistant", "delimiter": "<|im_start|>assistant"},
                        {"role": "user", "delimiter": "<|im_start|>user"}],
    stop=[], checkpoint_at="positive token count at final user start",
    admission="requires future owner-reviewed golden parity/control probe and new predeclaration",
)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def ids_sha(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


def _ids(value):
    return isinstance(value, list) and all(type(x) is int and x >= 0 for x in value)


def validate(row: dict, previous: dict | None = None) -> dict | None:
    """Return provenance only. HTTP success is never a simulator/native-contract correctness pass."""
    marker = row.get("raw_request_record_schema")
    capture = row.get("prefix_capture")
    if marker is None and capture is None:
        return None
    try:
        return _validate(row, capture, marker, previous)
    except (TypeError, ValueError, KeyError, AttributeError, UnicodeError) as exc:
        raise ProjectionError(f"HPR native-prefix provenance malformed: {exc}") from exc


def _validate(row, capture, marker, previous):
    if marker != SCHEMA or not isinstance(capture, dict) or capture.get("schema") != SCHEMA:
        raise ProjectionError("HPR native-prefix schema/marker mismatch")
    prompt, generated = capture.get("prompt_token_ids"), capture.get("generated_token_ids")
    if not _ids(prompt) or not _ids(generated):
        raise ProjectionError("HPR prompt/generated IDs are not integer arrays")
    problems = []
    raw_lines = capture.get("native_raw_lines_hex") or []
    events, streamed, finals, stopped = [], [], [], False
    try:
        for encoded in raw_lines:
            line = bytes.fromhex(encoded).decode("utf-8").strip()
            if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                continue
            event = json.loads(line[5:].strip())
            events.append(event)
            if not isinstance(event, dict) or not isinstance(event.get("tokens"), list):
                problems.append("invalid native event"); continue
            if event.get("stop") is True:
                finals.append(event); stopped = True
            elif event.get("stop") is False and not stopped:
                streamed.extend(event["tokens"])
            else:
                problems.append("invalid native event order")
    except (ValueError, UnicodeError, AttributeError, TypeError):
        problems.append("malformed native wire bytes")
    if not raw_lines or events != capture.get("native_events") or streamed != generated or finals != capture.get("final_events"):
        problems.append("native wire bytes do not re-derive IDs/events/finals")
    if len(finals) != 1:
        problems.append("native final count is not one")
    final = finals[0] if len(finals) == 1 else {}
    binding = capture.get("request_binding") or {}
    args = binding.get("request_args") or {}
    if binding.get("native_contract") != CONTRACT or binding.get("native_contract_sha256") != sha(CONTRACT):
        problems.append("missing/different UNVERIFIED native contract")
    try:
        body = binding["request_body_json"]
        if (hashlib.sha256(body.encode()).hexdigest() != binding.get("request_body_sha256")
                or json.loads(body) != dict(prompt=prompt, **args)
                or sha(args) != binding.get("request_args_sha256")
                or ids_sha(prompt) != binding.get("prompt_ids_sha256")
                or binding.get("endpoint") != "/completion"
                or binding.get("endpoint_sha256") != hashlib.sha256(b"/completion").hexdigest()):
            problems.append("request binding does not re-derive")
    except (KeyError, ValueError, AttributeError, TypeError):
        problems.append("request binding incomplete")
    retained = final.get("tokens_cached")
    if (row.get("status") != 200 or row.get("error") is not None or capture.get("native_anomalies")
            or final.get("tokens") != [] or final.get("stop_type") != "limit" or final.get("truncated") is not False
            or type(final.get("tokens_evaluated")) is not int or final.get("tokens_evaluated") != len(prompt)
            or type(final.get("tokens_predicted")) is not int or final.get("tokens_predicted") != len(generated)
            or type(row.get("predicted_n")) is not int or row.get("predicted_n") != len(generated)
            or args.get("ignore_eos") is not True or type(args.get("n_predict")) is not int
            or args.get("n_predict", 0) <= 0 or args.get("n_predict") != len(generated)
            or type(retained) is not int or not len(prompt) <= retained <= len(prompt) + len(generated)):
        problems.append("incomplete fixed-length native response")
    declared = capture.get("state")
    if declared not in ("complete", "incomplete") or (declared == "complete") != (not problems):
        raise ProjectionError("HPR native-prefix declared completeness does not re-derive")
    if capture.get("retained_slot_tokens") != retained:
        raise ProjectionError("HPR retained boundary disagrees with native final")
    if declared == "complete":
        if capture.get("problems") != [] or capture.get("retained_generated_tokens") != retained - len(prompt):
            raise ProjectionError("HPR complete retained suffix does not re-derive")
    elif not isinstance(capture.get("problems"), list) or not capture["problems"] or "retained_generated_tokens" in capture:
        raise ProjectionError("HPR incomplete capture must preserve refusal and assert no exact suffix")
    prior_verification = "not_asserted_incomplete_capture"
    if declared == "complete":
        prior = row.get("prior_prefix_state") or {}
        if (type(prior.get("prefix_token_count")) is not int or prior["prefix_token_count"] < 0
                or type(prior.get("retained_slot_tokens")) is not int or prior["retained_slot_tokens"] < 0
                or type(prior.get("lcp_prev")) is not int or not 0 <= prior["lcp_prev"] <= min(prior["prefix_token_count"], len(prompt))
                or not re.fullmatch(r"[0-9a-f]{64}", str(prior.get("prefix_ids_sha256") or ""))
                or prior.get("scope") != "checkpoint policy conditional on prior native retained boundary"
                or (row.get("sim_inputs") or {}).get("lcp_prev") != prior["lcp_prev"]):
            raise ProjectionError("HPR prior captured state provenance is incomplete")
        if previous is not None:
            old = previous["prefix_capture"]
            prefix = old["prompt_token_ids"] + old["generated_token_ids"][:old["retained_generated_tokens"]]
            lcp = 0
            for a, b in zip(prefix, prompt):
                if a != b:
                    break
                lcp += 1
            expected = dict(source_probe=previous["probe"], retained_slot_tokens=old["retained_slot_tokens"],
                            prefix_token_count=len(prefix), prefix_ids_sha256=ids_sha(prefix), lcp_prev=lcp,
                            scope="checkpoint policy conditional on prior native retained boundary")
            if prior != expected or (row.get("sim_inputs") or {}).get("lcp_prev") != lcp:
                raise ProjectionError("HPR prior captured state does not re-derive from previous request")
            prior_verification = "previous_native_record_rederived"
        else:
            # v1 records only hash/length of the launch seed, not its raw IDs. Preserve its
            # native attestation; do not invent IDs or call the first prior state independently verified.
            if prior.get("source_probe") != "launch_seed":
                raise ProjectionError("HPR first request lacks launch-seed provenance")
            prior_verification = "producer_attested_launch_seed_raw_ids_absent"
    return dict(schema=SCHEMA, state=declared, native_contract_status="UNVERIFIED",
                native_contract_sha256=binding.get("native_contract_sha256"),
                capture_sha256=sha(capture), prompt_ids_sha256=ids_sha(prompt), generated_ids_sha256=ids_sha(generated),
                prompt_tokens=len(prompt), generated_tokens=len(generated), retained_slot_tokens=capture.get("retained_slot_tokens"),
                request_binding=binding, refusal_problems=capture.get("problems"), prior_prefix_state=row.get("prior_prefix_state"),
                prior_prefix_verification=prior_verification,
                scope="native provenance only; request_ok is HTTP status; no simulator pass, parity approval or measurement admission")
