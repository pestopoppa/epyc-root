from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.autopilot.recode_multitier_execution_instrument import (
    SOURCE_INSTRUMENT,
    TARGET_INSTRUMENT,
    recode_payload,
)


def _source() -> dict:
    profile = {
        "execution_instrument_id": SOURCE_INSTRUMENT,
        "scoring_schedule_id": "judge-v1",
    }
    profile_json = json.dumps(profile, sort_keys=True, separators=(",", ":"))
    return {
        "status": "candidate_unratified",
        "tier": 2,
        "eval_result": {
            "n_questions": 2,
            "quality": 1.5,
            "reliability": 1.0,
            "question_results": [{"qid": "a"}, {"qid": "b"}],
            "details": {
                "errors": 0,
                "scoring_errors": 0,
                "eval_backend_drain_failure_count": 0,
                "eval_contaminated_by_abandoned_requests": False,
                "eval_execution_instrument_id": SOURCE_INSTRUMENT,
                "eval_execution_profile": profile,
                "eval_execution_profile_sha256": hashlib.sha256(
                    profile_json.encode()
                ).hexdigest(),
            },
        },
    }


def test_recode_changes_only_allowlisted_instrument_metadata() -> None:
    source = _source()
    before = copy.deepcopy(source)

    out = recode_payload(
        source,
        source_path=Path("/evidence/t2.json"),
        source_sha256="abc",
        recode_git_head="deadbeef",
    )

    assert source == before
    assert out["eval_result"]["question_results"] == before["eval_result"][
        "question_results"
    ]
    assert out["eval_result"]["quality"] == before["eval_result"]["quality"]
    assert out["eval_result"]["details"]["eval_execution_instrument_id"] == (
        TARGET_INSTRUMENT
    )
    assert out["eval_result"]["details"]["eval_execution_profile"][
        "execution_instrument_id"
    ] == TARGET_INSTRUMENT
    assert out["execution_instrument_recode"]["answers_changed"] is False


def test_recode_refuses_nonclean_source() -> None:
    source = _source()
    source["eval_result"]["details"]["errors"] = 1

    with pytest.raises(ValueError, match="source evidence is not clean"):
        recode_payload(
            source,
            source_path=Path("/evidence/t2.json"),
            source_sha256="abc",
            recode_git_head="deadbeef",
        )
