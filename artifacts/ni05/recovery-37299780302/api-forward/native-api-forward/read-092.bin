from __future__ import annotations

import copy
import hashlib
import json

import pytest

from scripts.autopilot import planner_roster as roster


def test_default_roster_is_exactly_two_codex_and_zero_claude() -> None:
    payload, digest, path = roster.load_roster(roster.DEFAULT_ROSTER)
    assert [cell["provider"] for cell in payload["cells"]] == ["codex", "codex_critic"]
    assert [cell["model"] for cell in payload["cells"]] == ["gpt-5.6-sol", "gpt-5.6-terra"]
    assert payload["constraints"]["claude_planner_count"] == 0
    assert payload["activation_reason"] == "weekly_claude_budget_exhausted"
    assert payload["expires_when"] == "manual_unset_or_reset"
    unsigned = {key: value for key, value in payload.items() if key != "self_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode()
    assert payload["self_sha256"] == hashlib.sha256(canonical).hexdigest()
    assert len(digest) == 64
    assert path == roster.DEFAULT_ROSTER


def test_claude_cell_is_rejected_even_if_counts_claim_zero() -> None:
    payload = json.loads(roster.DEFAULT_ROSTER.read_text(encoding="utf-8"))
    payload["cells"][1]["provider"] = "claude"
    payload["self_sha256"] = roster._canonical_sha256(
        {key: value for key, value in payload.items() if key != "self_sha256"}
    )
    with pytest.raises(roster.PlannerRosterError, match="Claude is forbidden"):
        roster.validate_roster(payload)


@pytest.mark.parametrize("count", [1, 3])
def test_one_or_three_planners_are_rejected(count: int) -> None:
    payload = json.loads(roster.DEFAULT_ROSTER.read_text(encoding="utf-8"))
    payload["cells"] = (payload["cells"] * 2)[:count]
    payload["self_sha256"] = roster._canonical_sha256(
        {key: value for key, value in payload.items() if key != "self_sha256"}
    )
    with pytest.raises(roster.PlannerRosterError, match="exactly two planners"):
        roster.validate_roster(payload)


def test_content_tamper_is_rejected_by_internal_self_hash(tmp_path) -> None:
    payload = json.loads(roster.DEFAULT_ROSTER.read_text(encoding="utf-8"))
    payload["cells"][1]["effort"] = "medium"
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(roster.PlannerRosterError, match="internal self-hash"):
        roster.load_roster(path)


def test_active_environment_is_bound_to_roster_sha_and_exact_roles(tmp_path) -> None:
    path = tmp_path / "roster.json"
    path.write_bytes(roster.DEFAULT_ROSTER.read_bytes())
    env = roster.apply_roster({"AUTOPILOT_PLANNER_PRIMARY": "claude"}, path)
    roster.validate_active_environment(env)
    assert env["AUTOPILOT_PLANNER_PRIMARY"] == "codex"
    assert env["AUTOPILOT_PLANNER_CRITIC"] == "codex_critic"
    assert env["AUTOPILOT_PLANNER_CRITIC_FALLBACK"] == "none"
    assert env["AUTOPILOT_PLANNER_MODE"] == "draft_critique"
    assert env["AUTOPILOT_PLANNER_CRITIQUE_POLICY"] == "always"
    assert env["AUTOPILOT_CODEX_MODEL"] == "gpt-5.6-sol"
    assert env["AUTOPILOT_CODEX_CRITIC_MODEL"] == "gpt-5.6-terra"

    drifted = copy.deepcopy(env)
    drifted["AUTOPILOT_PLANNER_CRITIC"] = "claude"
    with pytest.raises(roster.PlannerRosterError, match="differs from sealed roster"):
        roster.validate_active_environment(drifted)


def test_runtime_provider_check_revalidates_file_seal(tmp_path) -> None:
    path = tmp_path / "roster.json"
    path.write_bytes(roster.DEFAULT_ROSTER.read_bytes())
    env = roster.apply_roster({}, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cells"][0]["model"] = "claude-opus-5"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(roster.PlannerRosterError, match="internal self-hash"):
        roster.provider_allowed("codex", env)


def test_roster_application_does_not_rewrite_historical_artifacts(tmp_path) -> None:
    historical = tmp_path / "historical-campaign-manifest.json"
    original = b'{"schema":"epyc.autopilot.historical.v1","planner":"claude"}\n'
    historical.write_bytes(original)
    roster.apply_roster({}, roster.DEFAULT_ROSTER)
    assert historical.read_bytes() == original
