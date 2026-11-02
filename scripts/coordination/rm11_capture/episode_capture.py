"""Offline design prototype; not integrated, not an attestation or grading rule."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

SCHEMA = "epyc.rm11.episode_capture.prototype.v1"


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def capture_episode(*, run_id: str, episode_id: str, question_id: str,
                    request: dict[str, Any], response: dict[str, Any],
                    selected_index: int | None, parse_status: str,
                    candidate_pool_sha256: str, order: list[int],
                    native_distribution: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retain native response and explicit unknowns; never manufacture score probabilities.

    Distribution is a producer-supplied native capture, not an assertion of its provenance.
    Even structurally valid data cannot pass the SC43 gate in this offline prototype.
    """
    if not all(isinstance(x, str) and x.strip() for x in (run_id, episode_id, question_id, parse_status)):
        raise ValueError("run, episode, question and parse status are required")
    if not isinstance(request, dict) or not isinstance(response, dict):
        raise ValueError("request and response must be objects")
    if len(candidate_pool_sha256) != 64 or any(c not in "0123456789abcdef" for c in candidate_pool_sha256):
        raise ValueError("candidate_pool_sha256 must be a lowercase sha256")
    if not order or any(type(i) is not int or i < 0 for i in order) or len(set(order)) != len(order):
        raise ValueError("order must contain unique nonnegative source indices")
    if selected_index is not None and (type(selected_index) is not int or selected_index not in order):
        raise ValueError("selected index must be a source index in order, or null")
    if parse_status == "ok" and selected_index is None:
        raise ValueError("successful parse requires selected index")
    if parse_status != "ok" and selected_index is not None:
        raise ValueError("failed parse must not select an index")

    distribution: dict[str, Any] = {
        "status": "not_available", "probabilities": None, "score_tokens": None,
        "K": None, "retained_mass": None, "readout_method": None,
        "aggregation_timing": None, "native_provenance": "unverified",
    }
    issues = ["native score-token probability vector not captured"]
    if native_distribution is not None:
        if not isinstance(native_distribution, dict):
            raise ValueError("native_distribution must be an object or null")
        distribution.update(native_distribution)
        distribution["native_provenance"] = "unverified"
        issues = _distribution_issues(distribution)
        distribution["status"] = "structurally_complete" if not issues else "incomplete"
    # Native provenance, tokenizer/position, and the authority of this read-out are deliberately
    # unverified. Neither structurally complete inputs nor a flag supplied by a caller can pass.
    issues.append("native provenance and SC43 applicability not verified by this prototype")
    record = {
        "schema": SCHEMA,
        "locator": {"run_id": run_id, "episode_id": episode_id},
        "question_id": question_id,
        "candidate_pool_sha256": candidate_pool_sha256,
        "source_order": order,
        "request": request,
        "request_sha256": digest(request),
        "response": response,
        "response_sha256": digest(response),
        "selected_source_index": selected_index,
        "parse_status": parse_status,
        "distribution": distribution,
        "sc43_vector_compliant": False,
        "compliance_reasons": issues,
        "authority": "ungraded prototype; no decision authority",
    }
    record["record_sha256"] = digest(record)
    return record


def _distribution_issues(dist: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    values, tokens, k = dist.get("probabilities"), dist.get("score_tokens"), dist.get("K")
    if type(k) is not int or k < 1:
        issues.append("K must be a positive integer")
    if not isinstance(tokens, list) or not all(isinstance(x, str) and x for x in tokens) or len(set(tokens)) != len(tokens):
        issues.append("score_tokens must be distinct nonempty strings")
    if not isinstance(values, list) or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in values):
        issues.append("probabilities must be finite raw probabilities")
    else:
        if type(k) is not int or len(values) != k:
            issues.append("probability vector length must equal K")
        mass = dist.get("retained_mass")
        if type(mass) not in (int, float) or not math.isfinite(mass) or not 0 < mass <= 1 or not math.isclose(sum(values), mass, rel_tol=1e-9, abs_tol=1e-12):
            issues.append("retained_mass must equal the sum of raw probabilities in (0, 1]")
    if isinstance(tokens, list) and (type(k) is not int or len(tokens) != k):
        issues.append("score_tokens length must equal K")
    if not isinstance(dist.get("readout_method"), str) or not dist["readout_method"].strip():
        issues.append("readout_method is required")
    if dist.get("aggregation_timing") not in ("pre-order-aggregation", "post-order-aggregation"):
        issues.append("aggregation_timing must specify pre- or post-order-aggregation")
    return issues
