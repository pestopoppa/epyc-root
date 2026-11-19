#!/usr/bin/env python3
"""Build an observation-only schedule for paired resident CPU requests.

The input is an ordered JSON array of cohorts. Each contains scenario,
nominal_context, and one native completion or chat request_body. All measured
rows in a cohort reference the same canonical request body by SHA-256.
"""

import argparse
import hashlib
import json
from pathlib import Path


SCHEMA = "epyc.kernel_promotion_resident_plan.v1"
ARMS = ("production", "candidate")
QUARTETS = 5
WARMUP_TOKENS = 64
COHORT_FIELDS = ("scenario", "nominal_context", "request_body")


def _canonical_json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"expected finite JSON data: {exc}") from exc


def _sha256(value):
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _body_token_limit(body):
    if not isinstance(body, dict):
        raise ValueError("request_body must be a JSON object")
    if body.get("cache_prompt") is not False:
        raise ValueError("request_body requires cache_prompt: false")
    temperature = body.get("temperature")
    if type(temperature) not in (int, float) or temperature != 0:
        raise ValueError("request_body requires temperature: 0")
    seed = body.get("seed")
    if type(seed) is not int or not 0 <= seed < 2**32 - 1:
        raise ValueError("request_body requires a fixed seed from 0 to 4294967294")

    if "prompt" in body and "messages" not in body and "max_tokens" not in body:
        if not isinstance(body["prompt"], str) or not body["prompt"]:
            raise ValueError("completion prompt must be a nonempty string")
        token_limit = "n_predict"
    elif "messages" in body and "prompt" not in body and "n_predict" not in body:
        messages = body["messages"]
        if not isinstance(messages, list) or not messages or any(
            not isinstance(message, dict) or not isinstance(message.get("role"), str)
            or not message["role"] or "content" not in message
            for message in messages
        ):
            raise ValueError("chat messages must be a nonempty array of role/content objects")
        token_limit = "max_tokens"
    else:
        raise ValueError("request_body needs either prompt/n_predict or messages/max_tokens")

    limit = body.get(token_limit)
    if type(limit) is not int or limit <= 0:
        raise ValueError(f"{token_limit} must be a positive integer")
    return token_limit


def build_plan(cohorts):
    """Snapshot and validate cohorts, then derive the canonical ABBA plan."""
    if not isinstance(cohorts, list) or not cohorts:
        raise ValueError("cohorts must be a nonempty JSON array")

    planned_cohorts = []
    schedule = []
    seen = set()
    for cohort_index, cohort in enumerate(cohorts):
        if not isinstance(cohort, dict) or cohort.keys() != set(COHORT_FIELDS):
            raise ValueError("each cohort requires exactly scenario, nominal_context, and request_body")
        scenario = cohort["scenario"]
        if not isinstance(scenario, str) or not scenario.strip():
            raise ValueError("scenario must be a nonempty string")
        nominal_context = cohort["nominal_context"]
        if type(nominal_context) is not int or nominal_context <= 0:
            raise ValueError("nominal_context must be a positive integer")
        identity = (scenario, nominal_context)
        if identity in seen:
            raise ValueError(f"duplicate cohort: {identity}")
        seen.add(identity)

        body = cohort["request_body"]
        token_limit = _body_token_limit(body)
        body = json.loads(_canonical_json(body))
        request_sha256 = _sha256(body)
        first, second = ARMS if cohort_index % 2 == 0 else ARMS[::-1]
        requests = [
            {
                "scenario": scenario,
                "nominal_context": nominal_context,
                "pair_index": position // 2,
                "schedule_position": position,
                "arm": arm,
                "request_sha256": request_sha256,
            }
            for position, arm in enumerate((first, second, second, first) * QUARTETS)
        ]
        schedule.extend(requests)
        planned_cohorts.append({
            "scenario": scenario,
            "nominal_context": nominal_context,
            "request_body": body,
            "request_sha256": request_sha256,
            "reps_per_arm": 2 * QUARTETS,
            "warmups": [
                {
                    "arm": arm,
                    "excluded": True,
                    "request_overrides": {token_limit: WARMUP_TOKENS},
                }
                for arm in ARMS
            ],
            "requests": requests,
        })

    return {
        "schema": SCHEMA,
        "status": "observation_only",
        "lifecycle_mode": "paired_resident",
        "schedule_sha256": _sha256(schedule),
        "cohorts": planned_cohorts,
    }


def validate_plan(plan):
    """Raise ValueError unless this plan matches the regenerated canonical plan."""
    try:
        cohorts = [
            {key: cohort[key] for key in COHORT_FIELDS}
            for cohort in plan["cohorts"]
        ]
    except (KeyError, TypeError) as exc:
        raise ValueError("plan lacks cohort inputs") from exc
    if _canonical_json(plan) != _canonical_json(build_plan(cohorts)):
        raise ValueError("plan does not match the canonical resident schedule")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohorts", type=Path, required=True, help="ordered cohort input JSON")
    parser.add_argument("--out", type=Path, required=True, help="new observation-only plan JSON")
    args = parser.parse_args(argv)

    try:
        cohorts = json.loads(args.cohorts.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
        plan = build_plan(cohorts)
        payload = json.dumps(plan, indent=2, sort_keys=True, allow_nan=False)
        with args.out.open("x", encoding="utf-8") as output:
            output.write(payload + "\n")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
