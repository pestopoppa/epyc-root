"""Validate the committed designed T1 core file (benchmarks/prompts/core_v2.jsonl).

The loader ``EvalTower._load_designed_core`` and the fail-closed
``designed_core_activation_guard`` are exercised against the REAL, versioned core
artifact (not a synthetic fixture). Offline: the core embeds full question rows,
so no question-pool load and no network/inference occur.

This is the "loads the real file" acceptance for the core_v2 build. It also
asserts the operator gate is still closed: the live instrument-era registry does
NOT yet authorize core_v2, so activation must fail closed until the operator
appends the human-owned quality/core era row.

2026-07-23 amendment: the `vl` suite was INCLUDED (previously whole-suite excluded
on the stale 0/376 record) after a 20-question vl truth slice scored 20/20 correct,
0 errors through the real eval path. vl enters as a 1-item coverage-single; the
bigcodebench decision-value double was demoted k=2->k=1 to hold total=50. See the
metadata `amendment` block and handoffs/active/core-v2-design-note-2026-07-23.md.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import eval_tower  # noqa: E402
from eval_tower import EvalTower, dataset_content_sha256  # noqa: E402
from src.autopilot_core.instrument_era_guard import (  # noqa: E402
    designed_core_activation_guard,
)

CORE_ID = "core_v2"
CORE_PATH = REPO_ROOT / "benchmarks" / "prompts" / "core_v2.jsonl"
_NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)

# Suites that MUST NOT appear in the designed core (excluded by design/task).
# NOTE: `vl` was INCLUDED by the 2026-07-23 amendment (truth slice 20/20, 0 errors); it is
# no longer forbidden. The 2 individually-dead vl items stay item-excluded (see below).
_FORBIDDEN_SUITES = {"tulving_episodic", "aa_lcr", "document_extraction", "gaia"}
# Item-level known-dead qids that must be absent (incl. the 2 individually-dead vl items,
# retained item-excluded even though the vl suite is now included).
_KNOWN_DEAD_QIDS = {
    "usaco_silver_1326", "usaco_silver_759",
    "ifeval_2292", "ifeval_3691",
    "bcb_BigCodeBench/228", "bcb_BigCodeBench/51",
    "chart_test_0452", "chart_test_1401",
}
# 2026-07-23 vl-inclusion amendment fixtures.
_EXPECTED_VL_QID = "vl_chart_test_0758"      # vl a-priori pool-tier median (k=1), tier 2
_DISPLACED_QID = "bcb_BigCodeBench/1028"     # bigcodebench demoted k=2->k=1 to hold total=50
_AMENDED_SHA = "88d7a59ca342f03c09cc5f9ba0c0cb08075de61d576c6225707822d0edb639ca"


def _load(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_T1_CORE_ID", CORE_ID)
    monkeypatch.delenv("AUTOPILOT_T1_CORE_PATH", raising=False)  # exercise the default path
    return EvalTower()._load_designed_core(CORE_ID)


def test_core_v2_file_exists_at_default_path():
    assert CORE_PATH.exists(), f"missing designed core artifact: {CORE_PATH}"


def test_loader_accepts_real_core_file(monkeypatch):
    questions, metadata, path = _load(monkeypatch)
    assert Path(path) == CORE_PATH
    assert metadata["core_id"] == CORE_ID
    assert metadata["policy_version"] == "core_v2_designed_e7_v1"
    assert metadata["selected_count"] == len(questions)
    assert len(questions) == 50
    # every loaded question is scoreable under the live eval-tower gate
    assert all(eval_tower._is_scoreable_question(q) for q in questions)


def test_core_dataset_sha_is_reproducible(monkeypatch):
    questions, metadata, _ = _load(monkeypatch)
    assert dataset_content_sha256(questions) == metadata["dataset_content_sha256"]
    assert len(metadata["dataset_content_sha256"]) == 64
    # pinned to the vl-inclusion amendment (regression guard on composition/order)
    assert metadata["dataset_content_sha256"] == _AMENDED_SHA


def test_core_stratification_and_exclusions(monkeypatch):
    questions, metadata, _ = _load(monkeypatch)
    suites = {q["suite"] for q in questions}
    assert len(suites) == 37  # 36 text suites + vl (2026-07-23 amendment)
    assert suites.isdisjoint(_FORBIDDEN_SUITES)
    assert "vl" in suites  # vl is now a first-class scoreable suite
    ids = {str(q.get("id", "")) for q in questions}
    assert ids.isdisjoint(_KNOWN_DEAD_QIDS)
    # dominant pool suites are capped (decision-value, not pool size)
    from collections import Counter
    per_suite = Counter(q["suite"] for q in questions)
    assert max(per_suite.values()) <= 2
    for dominant in ("general", "mmlu_pro", "thinking", "hotpotqa"):
        assert per_suite[dominant] <= 2
    # metadata records the exclusion rationale; vl is NO LONGER excluded
    excl = metadata["exclusions"]
    assert "vl" not in excl
    assert "tulving_episodic" in excl
    assert set(excl["zero_source_suites"]["suites"]) == {"aa_lcr", "document_extraction", "gaia"}


def test_core_difficulty_spread_uses_apriori_tier(monkeypatch):
    questions, _, _ = _load(monkeypatch)
    tiers = [int(q["tier"]) for q in questions if q.get("tier") is not None]
    assert len(tiers) == 50
    # spread across all three a-priori difficulty tiers (not saturated on one)
    assert set(tiers) == {1, 2, 3}
    assert min(tiers) == 1 and max(tiers) == 3
    # pinned hard-lean histogram after the vl-inclusion amendment
    # (displaced a tier-1 bigcodebench item, added a tier-2 vl item)
    from collections import Counter
    assert Counter(tiers) == {3: 21, 2: 18, 1: 11}


def test_core_includes_vl_and_bigcodebench_demotion(monkeypatch):
    """2026-07-23 amendment: vl included (truth slice 20/20); bigcodebench demoted to hold 50."""
    questions, metadata, _ = _load(monkeypatch)
    from collections import Counter
    per_suite = Counter(q["suite"] for q in questions)
    ids = {str(q.get("id", "")) for q in questions}

    # vl is a first-class 1-item coverage-single suite (the sole multimodal signal)
    assert per_suite["vl"] == 1
    assert _EXPECTED_VL_QID in ids
    vl_q = next(q for q in questions if q["suite"] == "vl")
    assert int(vl_q["tier"]) == 2
    vl_cs = vl_q["core_selection"]
    assert vl_cs["slot_kind"] == "coverage-single"
    assert vl_cs["suite_slot_k"] == 1

    # bigcodebench demoted k=2 -> k=1; its hardest (tier-1) item is displaced, median kept
    assert per_suite["bigcodebench"] == 1
    assert "bcb_BigCodeBench/0" in ids
    assert _DISPLACED_QID not in ids
    bcb_q = next(q for q in questions if q["suite"] == "bigcodebench")
    assert bcb_q["core_selection"]["suite_slot_k"] == 1

    # the amendment is recorded and machine-checkable
    amend = metadata["amendment"]
    assert amend["new_dataset_content_sha256"] == metadata["dataset_content_sha256"]
    assert "vl" in amend["change"].lower()

    # the 2 individually-dead vl items remain item-excluded even though the suite is included
    dead = metadata["exclusions"]["known_dead_instrument_items"]
    vl_dead = next(item for item in dead["items"] if item["suite"] == "vl")
    assert set(vl_dead["qids"]) == {"chart_test_0452", "chart_test_1401"}

    # slot-list bookkeeping tracks the demotion/inclusion
    policy = metadata["selection_policy"]
    assert "bigcodebench" not in policy["double_slot_suites"]
    assert "bigcodebench" in policy["single_slot_suites"]
    assert "vl" in policy["single_slot_suites"]


def test_activation_guard_matches_the_live_operator_registry(monkeypatch):
    """The guard's verdict on the LIVE registry must equal what that file declares.

    This test used to assert a flat "not authorized yet". That premise expired:
    the operator applied the ``E4-quality-core-v2`` row to
    ``orchestration/instrument_eras.yaml`` in f60646e9 (2026-07-23), so the guard
    correctly returns ``authorized`` and the old literal was asserting the absence
    of a row that exists. The durable claim — the guard reads the real
    operator-owned registry rather than a fixture, and agrees with it — is derived
    from the file here instead of being restated, so the next operator edit moves
    the expectation with it rather than turning this red.

    The fail-closed branch keeps its own coverage below, driven by a registry that
    genuinely lacks an authorizing row.
    """
    import yaml

    from src.autopilot_core.instrument_era_guard import (
        AUTOPILOT_QUALITY_SCOPE,
        instrument_eras_path,
    )

    monkeypatch.delenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", raising=False)
    live_path = instrument_eras_path()
    declared = [
        era
        for era in yaml.safe_load(live_path.read_text())["eras"]
        if str(era.get("scope", "")) == AUTOPILOT_QUALITY_SCOPE
        and str(era.get("core_id", "")) == CORE_ID
    ]

    verdict = designed_core_activation_guard(CORE_ID, now=_NOW)

    assert verdict["path"] == str(live_path)
    assert verdict["ok"] is bool(declared), (
        f"guard says ok={verdict['ok']} but {live_path} declares "
        f"{len(declared)} authorizing {CORE_ID} row(s)"
    )
    if declared:
        assert verdict["status"] == "authorized"
        assert verdict["era"]["core_id"] == CORE_ID
        assert verdict["era"]["id"] in {str(era["id"]) for era in declared}
    else:
        assert verdict["status"] == "missing_core_era"
        assert "human-owned E4/core row" in verdict["reason"]


def test_activation_guard_fails_closed_without_an_operator_core_row(tmp_path, monkeypatch):
    """A live-shaped registry with no authorizing core row must fail closed.

    Built by taking the REAL registry and dropping only the rows that name this
    core, so the negative case is the live file minus its authorization — not a
    hand-written stub that could drift away from the real schema.
    """
    import yaml

    from src.autopilot_core.instrument_era_guard import (
        AUTOPILOT_QUALITY_SCOPE,
        instrument_eras_path,
    )

    monkeypatch.delenv("AUTOPILOT_INSTRUMENT_ERAS_PATH", raising=False)
    data = yaml.safe_load(instrument_eras_path().read_text())
    kept = [
        era
        for era in data["eras"]
        if not (
            str(era.get("scope", "")) == AUTOPILOT_QUALITY_SCOPE
            and str(era.get("core_id", "")) == CORE_ID
        )
    ]
    assert len(kept) < len(data["eras"]), "live registry has no core row to remove"
    stripped = tmp_path / "instrument_eras.yaml"
    stripped.write_text(yaml.safe_dump({**data, "eras": kept}, sort_keys=False))

    verdict = designed_core_activation_guard(CORE_ID, path=stripped, now=_NOW)

    assert verdict["ok"] is False
    assert verdict["status"] == "missing_core_era"
    assert "human-owned E4/core row" in verdict["reason"]


def test_activation_guard_authorizes_with_operator_era_row(tmp_path, monkeypatch):
    """The ready-to-paste operator era row authorizes activation."""
    eras = tmp_path / "instrument_eras.yaml"
    eras.write_text(
        "eras:\n"
        "  - id: E8-quality-core-v2\n"
        '    from: "2026-07-23T00:00:00Z"\n'
        "    scope: autopilot_quality\n"
        f'    core_id: "{CORE_ID}"\n'
        '    policy_version: "core_v2_designed_e7_v1"\n'
    )
    verdict = designed_core_activation_guard(CORE_ID, path=eras, now=_NOW)
    assert verdict["ok"] is True
    assert verdict["status"] == "authorized"
    assert verdict["era"]["core_id"] == CORE_ID
