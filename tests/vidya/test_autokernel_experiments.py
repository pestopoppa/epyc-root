"""Belief redesign P1-C: AutoKernel `experiments.db` -> loop beliefs.

The fixture DB is built here with the REAL schema (`sqlite3 'file:...?mode=ro' .schema` on
ak-27b-gpu-verify-20261004/store/experiments.db, 2026-10-21) and one row per status the adapter
distinguishes. No real store is touched, no ledger but a tmp one is written.

The store manifest is `_ak_store_manifest.resolve(store)` (two strategies, one owner): the loop's
`loop-status.json` target first, else the uniform native `research_scope` of the store's rows.
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))

import cli  # noqa: E402
from adapters import autokernel_experiments as exp  # noqa: E402
from claim_tuple import ProjectionError, grade, to_frames  # noqa: E402
from ledger import Ledger  # noqa: E402

SCHEMA = """
CREATE TABLE experiments (
    attempt_id        TEXT PRIMARY KEY,
    recorded_at       TEXT NOT NULL,
    campaign_id       TEXT NOT NULL,
    deployment        TEXT,
    epoch_sha256      TEXT NOT NULL,
    hypothesis_id     TEXT,
    mechanism_id      TEXT,
    target_surface    TEXT,
    target_symbol     TEXT,
    statement         TEXT,
    falsifier         TEXT,
    status            TEXT NOT NULL,
    effect_fraction   REAL,
    exact_effect      REAL,
    target_effect     REAL,
    refusal_reason    TEXT,
    result_sha256     TEXT,
    spawn_parent      TEXT,
    branch_id         TEXT,
    width             INTEGER,
    depth             INTEGER,
    payload           TEXT NOT NULL
);
CREATE INDEX experiments_epoch ON experiments (epoch_sha256);
CREATE INDEX experiments_mechanism ON experiments (mechanism_id);
CREATE TABLE epoch_aliases (
    full_epoch        TEXT PRIMARY KEY,
    measurement_epoch TEXT NOT NULL,
    recorded_at       TEXT NOT NULL,
    record            TEXT NOT NULL
);
"""

EPOCH = hashlib.sha256(b"epoch").hexdigest()
BUILD = hashlib.sha256(b"build").hexdigest()[:40]
MODEL = "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
MODEL_SHA = hashlib.sha256(b"model").hexdigest()
CAPTURE = hashlib.sha256(b"capture").hexdigest()
RECEIPT = "sha256:" + hashlib.sha256(b"receipt").hexdigest()


def aid(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()


def native_scope(surface="serving:q27b-gpu-dflash2-np1"):
    return {"backend": "gpu", "measurement_surface": surface,
            "model": {"path": MODEL, "sha256": MODEL_SHA}, "quant": "Q8_0",
            "recipe": {"build_recipe": {}, "original_serving_arms": None}, "request_digest": None}


def comparison(effect=0.0205, floor=3.412, pairs=5, decisive=False, **extra):
    return {"surface": "aggregate_tok_s", "model": None, "effect": effect,
            "effect_pct": effect * 100, "estimator": "median-ratio", "pairs": pairs,
            "noise_floor_pct": floor, "decisive": decisive,
            "anchor_samples": [21.8, 21.9, 22.0, 21.9, 21.9],
            "candidate_samples": [22.3, 22.4, 22.3, 22.3, 22.2], "residency": {}, **extra}


def serving_comparison(effect=0.04):
    return {"metric": "aggregate_tok_s", "effect": effect, "effect_pct": effect * 100,
            "pairs": 3, "noise_floor_pct": 1.5, "decisive": True, "anchor_tok_s": 80.0,
            "candidate_tok_s": 83.2, "np": 1,
            "measurement_plan": {"instrument": "matched_process_v2"}}


# (name, status, columns, payload) -- one row per distinguished status, in rowid order.
def rows():
    base = {"campaign_id": "ak-loop", "epoch_sha256": EPOCH, "spawn_parent": BUILD,
            "target_surface": "ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp",
            "target_symbol": "ggml_iqk_try_mul_mat_id"}
    mech = {"mechanism_id": "akm-mmid-qact-block-partition",
            "statement": "S" * 400, "falsifier": "F" * 400}
    return [
        ("kept", "kept", {**base, **mech, "effect_fraction": 0.0205},
         {"comparison": comparison(belief_capture={"capture_id": CAPTURE}),
          "research_scope": native_scope(), "belief_receipt_id": RECEIPT,
          "candidate_diff_sha256": aid("diff"), "reason": "R" * 500}),
        ("keep_candidate", "keep_candidate", {**base, **mech, "effect_fraction": 0.031},
         {"comparison": comparison(effect=0.031, decisive=True),
          "research_scope": native_scope()}),
        ("measured_null", "measured_null",
         {**base, "mechanism_id": "akm-null", "effect_fraction": 0.001},
         {"comparison": comparison(effect=0.001), "reason": "inside the floor"}),
        ("regression", "regression",
         {**base, "mechanism_id": "akm-regress", "effect_fraction": -0.05},
         {"comparison": comparison(effect=-0.05, decisive=True),
          "research_scope": native_scope()}),
        ("serving_gate", "measured_serving_gate",
         {**base, "mechanism_id": "serving-gate-abc123", "effect_fraction": None},
         {"comparison": serving_comparison(), "serving": serving_comparison(),
          "research_scope": native_scope()}),
        ("divergence", "measured_divergence", {**base, "mechanism_id": "serving-divergence-abc"},
         {"hypothesis": "bench said +4%, serving said -1%: bundle held",
          "comparison": serving_comparison(effect=-0.01)}),
        ("gate_correctness", "gate_refused",
         {**base, "mechanism_id": "akm-q8-streamk", "refusal_reason": "MUL_MAT failed on ROCm0",
          "target_symbol": "launch_mul_mat_q"},
         {"refusal_gate": "correctness", "reason": "MUL_MAT failed on ROCm0",
          "belief_receipt_id": RECEIPT, "research_scope": native_scope(),
          "gates": [{"gate": "compile", "passed": True, "reason": None, "detail": None}]}),
        ("gate_op_scope", "gate_refused",
         {**base, "mechanism_id": "akm-scope", "refusal_reason": "route outside the admitted ops"},
         {"refusal_gate": "op_scope", "reason": "route outside the admitted ops"}),
        ("integrity", "integrity_refused",
         {**base, "mechanism_id": "akm-integrity", "refusal_reason": "critic mutated the tree"},
         {"integrity_screen": {"refusal_class": "critic_tree_mutation"},
          "reason": "critic mutated the tree"}),
        ("anchor_verified", "anchor_verified",
         {**base, "mechanism_id": "anchor-guard", "effect_fraction": 0.0004},
         {"anchor_guard": {"check": "anchor-guard", "passed": True, "pairs": 5,
                           "floor_pct": 3.412, "effect_pct": 0.04,
                           "comparison": comparison(effect=0.0004)}}),
        ("runtime_observed", "runtime_observed",
         {**base, "mechanism_id": "rt-arm", "effect_fraction": 0.012},
         {"comparison": serving_comparison(effect=0.012), "research_scope": native_scope()}),
        ("anchor_excursion", "anchor_guard_excursion", {**base, "mechanism_id": "anchor-guard"},
         {"anchor_guard": {"excursion": True}}),
        ("patch_rejected", "patch_rejected", {**base, "mechanism_id": "akm-pr"},
         {"reason": "critic: no"}),
        ("hypothesis_rejected", "hypothesis_rejected", {**base, "mechanism_id": "akm-hr"},
         {"reason": "critic: already measured"}),
        ("authoring_failed", "authoring_failed", {**base, "mechanism_id": "akm-af"},
         {"reason": "authoring_failed: no diff"}),
        ("planner_transient", "planner_transient", {**base}, {"reason": "transient"}),
        ("no_attempt_id", "kept", {**base, "mechanism_id": "akm-x", "effect_fraction": 0.02},
         {"comparison": comparison()}),
        ("bad_payload", "kept", {**base, "mechanism_id": "akm-bad"}, "this is not json"),
        ("aa_skipped", "anchor_verified", {**base, "mechanism_id": "anchor-guard"},
         {"anchor_guard": {"passed": True, "pairs": 0, "effect_pct": None, "detail": "skipped"}}),
        ("gate_via_gates_list", "gate_refused",
         {**base, "mechanism_id": "akm-gl", "refusal_reason": "MUL_MAT_ID failed on ROCm0"},
         {"gates": [{"gate": "compile", "passed": True},
                    {"gate": "reference_comparison", "passed": False,
                     "reason": "MUL_MAT_ID failed on ROCm0", "detail": "x"}]}),
    ]


FIXTURE = rows()
NAMES = [name for name, *_ in FIXTURE]


def rowid_of(name: str) -> int:
    return NAMES.index(name) + 1


def make_store(tmp_path, name="store", fixture=None, with_attempt_none=True):
    store = tmp_path / name
    store.mkdir()
    conn = sqlite3.connect(store / "experiments.db")
    conn.executescript(SCHEMA)
    for index, (label, status, columns, payload) in enumerate(fixture or FIXTURE):
        attempt = None if (label == "no_attempt_id" and with_attempt_none) else aid(label)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        conn.execute(
            "INSERT INTO experiments (attempt_id, recorded_at, campaign_id, epoch_sha256, status,"
            " mechanism_id, target_surface, target_symbol, statement, falsifier, effect_fraction,"
            " refusal_reason, spawn_parent, payload) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (attempt, f"2026-10-04T04:{index:02d}:38Z", columns["campaign_id"],
             columns["epoch_sha256"], status, columns.get("mechanism_id"),
             columns.get("target_surface"), columns.get("target_symbol"),
             columns.get("statement"), columns.get("falsifier"), columns.get("effect_fraction"),
             columns.get("refusal_reason"), columns.get("spawn_parent"), text))
    conn.commit()
    conn.close()
    return store


@pytest.fixture
def store(tmp_path):
    return make_store(tmp_path)


MANIFEST = {"store": "/fixture/store", "label": "Q38FN cpu", "strategy": "row_scope",
            "recipe": "q38fn-cpu-t48",
            "scope": {"model_file": "/mnt/raid0/llm/models/Q38FN-UD-IQ4_XS.gguf",
                      "quant": "UD-IQ4_XS", "backend": "cpu", "device": "epyc-9655",
                      "recipe": "q38fn-cpu-t48", "np": 1, "scope_basis": "store_manifest"}}
STATUS_MANIFEST = {"store": "/fixture/store", "strategy": "loop_status", "recipe": "r-selected",
                   "scope": {"model_file": "/mnt/raid0/llm/models/Q38FN-UD-IQ4_XS.gguf",
                             "backend": "cpu", "recipe": "r-selected",
                             "scope_basis": "store_manifest"}}


def projected(store, manifest=None):
    manifest = manifest or MANIFEST
    out = {}
    for row in exp.native_rows(store):
        out[NAMES[row["rowid"] - 1]] = exp.project(row, store_manifest=manifest)
    return out


# ------------------------------------------------------------------------------ read side


def test_native_rows_is_incremental_and_ordered(store):
    allrows = exp.native_rows(store)
    assert [r["rowid"] for r in allrows] == list(range(1, len(FIXTURE) + 1))
    assert [r["rowid"] for r in exp.native_rows(store, since_rowid=None)] == [r["rowid"] for r in allrows]
    tail = exp.native_rows(store, since_rowid=15)
    assert [r["rowid"] for r in tail] == list(range(16, len(FIXTURE) + 1))
    assert exp.native_rows(store, since_rowid=len(FIXTURE)) == []
    assert exp.native_rows(store, since_rowid=10**9) == []
    for bad in (-1, 1.5, "3", True):
        with pytest.raises(ProjectionError):
            exp.native_rows(store, since_rowid=bad)


def test_since_rowid_rows_equal_the_same_rows_of_a_full_read(store):
    full = {r["rowid"]: r for r in exp.native_rows(store)}
    for row in exp.native_rows(store, since_rowid=7):
        assert row == full[row["rowid"]]


def test_payload_is_read_only_for_projectable_statuses(store):
    by_name = {NAMES[r["rowid"] - 1]: r for r in exp.native_rows(store)}
    for name in ("planner_transient", "patch_rejected", "hypothesis_rejected", "authoring_failed",
                 "anchor_excursion"):
        assert by_name[name]["payload"] is None and by_name[name]["payload_sha256"] is None
    assert isinstance(by_name["kept"]["payload"], dict) and len(by_name["kept"]["payload_sha256"]) == 64
    assert by_name["bad_payload"]["payload"] is None and by_name["bad_payload"]["payload_error"]


def test_native_rows_never_writes_the_store(store):
    db = store / "experiments.db"
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    before_files = sorted(p.name for p in store.iterdir())
    exp.native_rows(store)
    exp.native_rows(store, since_rowid=3)
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert sorted(p.name for p in store.iterdir()) == before_files


def test_missing_db_is_an_error_not_an_empty_read(tmp_path):
    with pytest.raises(ProjectionError, match="no experiments.db"):
        exp.native_rows(tmp_path)


def test_store_missing_optional_columns_still_reads(tmp_path):
    store = tmp_path / "old"
    store.mkdir()
    conn = sqlite3.connect(store / "experiments.db")
    conn.execute("CREATE TABLE experiments (attempt_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,"
                 " status TEXT NOT NULL, payload TEXT NOT NULL)")
    conn.execute("INSERT INTO experiments VALUES ('a1', '2026-09-01T00:00:00Z', 'measured_null', ?)",
                 (json.dumps({"comparison": comparison(effect=0.0)}),))
    conn.commit()
    conn.close()
    (row,) = exp.native_rows(store)
    assert row["deployment"] is None and row["epoch_sha256"] is None and row["payload"]


# ------------------------------------------------------------------------------ status table


EXPECTED = {
    # name: (disposition, outcome, category, source_class)
    "kept": ("measurement", "improved", "CANDIDATE", "measurement"),
    "keep_candidate": ("measurement", "improved", "CANDIDATE", "measurement"),
    "measured_null": ("measurement", "null", "CANDIDATE", "measurement"),
    "regression": ("measurement", "regressed", "CANDIDATE", "measurement"),
    "serving_gate": ("measurement", "improved", "CANDIDATE", "measurement"),
    "divergence": ("verifier", "divergence", "CANDIDATE", "verifier"),
    "gate_correctness": ("verifier", "refused_correctness", "CANDIDATE", "verifier"),
    "integrity": ("verifier", "refused_correctness", "CANDIDATE", "verifier"),
    "anchor_verified": ("baseline", "anchor", "BASELINE", "measurement"),
    "runtime_observed": ("baseline", "anchor", "BASELINE", "measurement"),
    "gate_via_gates_list": ("verifier", "refused_correctness", "CANDIDATE", "verifier"),
}


def test_status_to_outcome_table(store):
    tuples = projected(store)
    by_row = {NAMES[r["rowid"] - 1]: r for r in exp.native_rows(store)}
    for name, (disposition, outcome, category, source_class) in EXPECTED.items():
        tup = tuples[name]
        assert tup is not None, name
        assert exp.classify(by_row[name])[0] == disposition, name
        assert exp.observation_of(tup)["outcome"] == outcome, name
        assert exp.observation_of(tup)["outcome_native"] == by_row[name]["status"], name
        assert (tup.category, tup.source_class) == (category, source_class), name
        assert tup.source_kind == "autokernel-experiment" and tup.protocol_id == "", name


def test_every_projection_is_an_observation_judged_located(store):
    """No protocol is ever filled in, so the ladder (not this adapter) says Judged/Located."""
    for name, tup in projected(store).items():
        if tup is not None:
            assert grade(tup)[:2] == ("Judged", "Located"), name


def test_measured_serving_gate_outcome_follows_the_sign_of_its_effect(tmp_path):
    def one(effect, decisive):
        comp = serving_comparison(effect=effect)
        comp["decisive"] = decisive
        fixture = [("g", "measured_serving_gate",
                    {"campaign_id": "c", "epoch_sha256": EPOCH, "mechanism_id": "serving-gate-x"},
                    {"comparison": comp})]
        s = make_store(tmp_path, name=f"s{effect}{decisive}", fixture=fixture)
        (row,) = exp.native_rows(s)
        return exp.observation_of(exp.project(row, store_manifest=MANIFEST))["outcome"]

    assert one(0.04, True) == "improved"
    assert one(-0.04, True) == "regressed"
    assert one(-0.001, False) == "null"


def test_measurement_fields(store):
    kept = projected(store)["kept"]
    obs = exp.observation_of(kept)
    assert kept.metric == "aggregate_tok_s" and kept.unit == "t/s"
    assert kept.metric_direction == "higher_better"
    assert kept.value == pytest.approx(22.3) and obs["anchor_value"] == pytest.approx(21.9)
    assert obs["effect_rel"] == pytest.approx(0.0205)
    assert obs["noise_floor_rel"] == pytest.approx(0.03412)
    assert obs["decisive"] is False and obs["n_pairs"] == 5 and kept.reps == 5
    assert kept.reps_basis.startswith("scored:")
    assert kept.date == "2026-10-04T04:00:38Z"
    assert len(obs["outcome_reason"]) <= 300
    assert obs["mechanism"]["id"] == "akm-mmid-qact-block-partition"
    assert len(obs["mechanism"]["statement"]) == 240 and len(obs["mechanism"]["falsifier"]) == 240
    assert "+2.05% vs anchor" in kept.claim and "floor 3.41%" in kept.claim
    assert "producer verdict KEPT" in kept.claim
    assert obs["serving_claim_id"] == f"legacy-serving-v2:{CAPTURE}"
    scope = exp.applicability_of(kept)
    assert scope["build_sha"] == BUILD and scope["epoch"] == EPOCH
    assert scope["surface"].endswith("iqk_dispatch.cpp") and scope["symbol"] == "ggml_iqk_try_mul_mat_id"
    assert scope["recipe"] == "q27b-gpu-dflash2-np1"


def test_matched_process_serving_rows_say_so(store):
    tup = projected(store)["serving_gate"]
    assert tup.reps_basis == "scored:matched process pairs"
    assert tup.value == pytest.approx(83.2) and exp.observation_of(tup)["anchor_value"] == 80.0
    assert exp.applicability_of(tup)["np"] == 1


def test_baseline_rows_carry_the_anchor_rate(store):
    tup = projected(store)["anchor_verified"]
    assert tup.category == "BASELINE" and tup.value == pytest.approx(21.9)
    assert exp.observation_of(tup)["outcome"] == "anchor"


# ------------------------------------------------------------------------------ verifier


def test_correctness_refusal_is_a_verifier_graded_judged(store):
    tup = projected(store)["gate_correctness"]
    assert tup.source_class == "verifier"
    assert tup.decided_proposition == "MUL_MAT failed on ROCm0"
    assert tup.binding_kind == ""
    assert tup.metric == "correctness:MUL_MAT" and tup.value == 0
    assert tup.category == "CANDIDATE" and tup.metric_direction == "higher_better"
    q, t, reasons = grade(tup)
    assert (q, t) == ("Judged", "Located")
    assert any("not bound to the claim" in r for r in reasons)
    assert exp.observation_of(tup)["outcome_reason"] == "MUL_MAT failed on ROCm0"
    assert exp.applicability_of(tup)["op"] == "MUL_MAT"


def test_gate_refusal_found_through_the_gates_list(store):
    tup = projected(store)["gate_via_gates_list"]
    assert tup.source_class == "verifier" and tup.metric == "correctness:MUL_MAT_ID"
    assert tup.decided_proposition == "MUL_MAT_ID failed on ROCm0"


def test_integrity_and_divergence_are_verifier_class(store):
    tuples = projected(store)
    assert tuples["integrity"].metric == "integrity:critic_tree_mutation"
    assert tuples["integrity"].decided_proposition == "critic mutated the tree"
    assert tuples["divergence"].metric == "serving_gate:diverged"
    assert tuples["divergence"].decided_proposition == "bench said +4%, serving said -1%: bundle held"
    for name in ("integrity", "divergence"):
        assert grade(tuples[name])[:2] == ("Judged", "Located")


@pytest.mark.parametrize("gate,projects", [("correctness", True), ("reference_comparison", True),
                                           ("compile", False), ("configure", False),
                                           ("op_scope", False), ("oracle_unavailable", False),
                                           ("cpu_fa_perf_screen", False)])
def test_only_correctness_gates_project(tmp_path, gate, projects):
    fixture = [("g", "gate_refused",
                {"campaign_id": "c", "epoch_sha256": EPOCH, "mechanism_id": "akm-g",
                 "refusal_reason": "MUL_MAT failed on ROCm0"},
                {"refusal_gate": gate, "reason": "MUL_MAT failed on ROCm0"})]
    s = make_store(tmp_path, fixture=fixture)
    (row,) = exp.native_rows(s)
    assert (exp.project(row, store_manifest=MANIFEST) is not None) is projects
    if not projects:
        assert exp.classify(row) == (None, "scope_gate")


# ------------------------------------------------------------------------------ None cases


def test_rows_that_are_not_loop_beliefs_project_to_none(store):
    tuples = projected(store)
    by_row = {NAMES[r["rowid"] - 1]: r for r in exp.native_rows(store)}
    expected_reason = {
        "gate_op_scope": "scope_gate", "anchor_excursion": "instrument_session_health",
        "patch_rejected": "critic_or_scope_rejection", "hypothesis_rejected": "critic_rejection",
        "authoring_failed": "authoring_failure", "planner_transient": "noise",
        "no_attempt_id": "no_attempt_id", "bad_payload": "payload_unreadable",
        "aa_skipped": "no_numbers"}
    for name, reason in expected_reason.items():
        assert tuples[name] is None, name
        assert exp.classify(by_row[name]) == (None, reason), name


def test_no_row_without_an_attempt_id(store):
    row = {**next(r for r in exp.native_rows(store) if r["rowid"] == rowid_of("kept"))}
    assert exp.project(row, store_manifest=MANIFEST) is not None
    for bad in (None, "", "   ", "has space", "tab\tid", 7):
        assert exp.project({**row, "attempt_id": bad}, store_manifest=MANIFEST) is None
        with pytest.raises(ProjectionError):
            exp.measurement_id({**row, "attempt_id": bad}, MANIFEST)


def test_an_unusable_store_identity_is_refused(store):
    row = exp.native_rows(store)[0]
    with pytest.raises(ProjectionError, match="store_digest"):
        exp.project(row, store_manifest={})


# ------------------------------------------------------------------------------ scope


def test_native_scope_wins_and_is_labelled_native(store):
    scope = exp.applicability_of(projected(store)["kept"])
    assert scope["scope_basis"] == "native"
    assert scope["model_file"] == MODEL and scope["model_sha256"] == MODEL_SHA
    assert scope["quant"] == "Q8_0" and scope["backend"] == "gpu"
    assert "device" not in scope  # the store manifest's device never mixes into a native scope


def test_refusal_row_with_native_scope_is_native(store):
    scope = exp.applicability_of(projected(store)["gate_correctness"])
    assert scope["scope_basis"] == "native" and scope["model_file"] == MODEL


def test_row_without_research_scope_takes_the_store_manifest(store):
    scope = exp.applicability_of(projected(store)["measured_null"])
    assert scope["scope_basis"] == "store_manifest"
    assert scope["model_file"] == MANIFEST["scope"]["model_file"] and scope["quant"] == "UD-IQ4_XS"
    assert scope["backend"] == "cpu" and scope["device"] == "epyc-9655"
    assert scope["recipe"] == "q38fn-cpu-t48" and scope["np"] == 1  # row_scope: the shared recipe
    assert "model_sha256" not in scope  # only when recorded


def test_a_loop_status_manifest_scopes_model_and_backend_but_not_the_recipe(store):
    scope = exp.applicability_of(projected(store, STATUS_MANIFEST)["measured_null"])
    assert scope["scope_basis"] == "store_manifest" and scope["backend"] == "cpu"
    assert scope["model_file"] == STATUS_MANIFEST["scope"]["model_file"]
    assert "recipe" not in scope  # the loop's selected recipe is not the row's own


def test_no_native_scope_and_no_manifest_scope_is_honestly_unscoped(store):
    bare = {"store": "/fixture/store", "strategy": "none", "scope": {}}
    scope = exp.applicability_of(projected(store, bare)["measured_null"])
    assert "scope_basis" not in scope and "model_file" not in scope
    assert scope["epoch"] == EPOCH  # identity keys are still stated


def test_store_manifest_row_strategy_uses_one_uniform_native_scope(store, tmp_path):
    manifest = exp.build_store_manifest(store)
    assert manifest["strategy"] == "row_scope" and manifest["store"] == str(store.resolve())
    scope = manifest["scope"]
    assert scope["model_file"] == MODEL and scope["quant"] == "Q8_0"
    assert scope["recipe"] == "q27b-gpu-dflash2-np1" and scope["scope_basis"] == "store_manifest"
    other = native_scope()
    other["model"] = {"path": "/mnt/raid0/llm/models/other.gguf"}
    mixed = make_store(tmp_path, name="mixed", fixture=[
        ("a", "kept", {"campaign_id": "c", "epoch_sha256": EPOCH},
         {"comparison": comparison(), "research_scope": native_scope()}),
        ("b", "kept", {"campaign_id": "c", "epoch_sha256": EPOCH},
         {"comparison": comparison(), "research_scope": other})])
    derived = exp.build_store_manifest(mixed)
    assert derived["strategy"] == "none" and derived["scope"] == {}
    overridden = exp.build_store_manifest(mixed, label="L", overrides={
        "model_file": "/x/y.gguf", "backend": "cpu"})
    assert overridden["scope"] == {"model_file": "/x/y.gguf", "backend": "cpu"}
    assert overridden["label"] == "L"


def test_store_manifest_loop_status_strategy_wins_over_rows(store):
    status = {"schema": "epyc.autokernel.loop_status.v1", "target": {
        "selected_id": "r-selected", "campaign_id": "camp",
        "original_target": {"execution": {"backend": "CPU", "model": {
            "path": "/models/status.gguf", "sha256": "ab" * 32}}}}}
    (store / "loop-status.json").write_text(json.dumps(status))
    manifest = exp.build_store_manifest(store)
    assert manifest["strategy"] == "loop_status" and manifest["recipe"] == "r-selected"
    assert manifest["scope"]["model_file"] == "/models/status.gguf"
    assert manifest["scope"]["backend"] == "cpu" and manifest["scope"]["model_sha256"] == "ab" * 32
    assert manifest["store"] == str(store.resolve())


def test_one_module_owns_both_manifest_strategies():
    from adapters import _ak_store_manifest as owner

    assert exp.store_scope is owner
    assert {"load", "load_from_rows", "resolve", "row_scope"} <= set(owner.__all__)


# ------------------------------------------------------------------------------ identity


def test_measurement_id_is_byte_stable(store, tmp_path):
    first, second = projected(store), projected(store)
    digest = hashlib.sha256(MANIFEST["store"].encode()).hexdigest()[:16]
    for name, tup in first.items():
        if tup is None:
            continue
        assert tup.measurement_id == f"ak-exp:v1:{digest}:{aid(name)}", name
        assert tup == second[name], name  # every field, every run
        assert tup.attestation_sha256 == second[name].attestation_sha256
        assert tup.attestation_locator == (
            f"autokernel-experiments:/fixture/store/experiments.db#attempt={aid(name)}")


def test_measurement_id_depends_on_store_and_attempt_only(store):
    row = next(r for r in exp.native_rows(store) if r["rowid"] == rowid_of("kept"))
    base = exp.project(row, store_manifest=MANIFEST).measurement_id
    moved = exp.project({**row, "rowid": 99999}, store_manifest=MANIFEST).measurement_id
    changed_text = exp.project({**row, "statement": "different"}, store_manifest=MANIFEST).measurement_id
    other_store = exp.project(row, store_manifest={**MANIFEST, "store": "/other"}).measurement_id
    explicit = exp.project(row, store_manifest={**MANIFEST, "store_digest": "ab" * 32}).measurement_id
    assert base == moved == changed_text
    assert other_store != base and explicit == f"ak-exp:v1:{'ab' * 8}:{aid('kept')}"


def test_same_ids_when_the_rows_are_reread_incrementally(store):
    full = {r["rowid"]: exp.project(r, store_manifest=MANIFEST) for r in exp.native_rows(store)}
    part = {r["rowid"]: exp.project(r, store_manifest=MANIFEST)
            for r in exp.native_rows(store, since_rowid=5)}
    assert part and all(full[k] == v for k, v in part.items())


def test_frames_are_byte_stable_across_runs(store):
    first = [f["frame_id"] for t in projected(store).values() if t is not None
             for f in to_frames(t, as_of="2026-10-21T12:00:00Z", adapter_id=exp.ADAPTER_ID)]
    second = [f["frame_id"] for t in projected(store).values() if t is not None
              for f in to_frames(t, as_of="2026-10-21T12:00:00Z", adapter_id=exp.ADAPTER_ID)]
    assert first and first == second and len(set(first)) == len(first)
    assert len(first) == 3 * len(EXPECTED)


# ------------------------------------------------------------------------------ join + retrofit


def test_serving_capture_joins_by_capture_id_not_belief_receipt_id(store):
    tuples = projected(store)
    assert tuples["kept"].extra["serving_claim_id"] == f"legacy-serving-v2:{CAPTURE}"
    assert exp.observation_of(tuples["kept"])["serving_claim_id"] == f"legacy-serving-v2:{CAPTURE}"
    assert "serving_claim_id" not in exp.observation_of(tuples["gate_correctness"])
    # belief_receipt_id is the planner-evidence receipt: provenance, never the join key
    assert tuples["kept"].extra["belief_receipt_id"] == RECEIPT
    assert tuples["gate_correctness"].extra["belief_receipt_id"] == RECEIPT
    assert tuples["gate_correctness"].extra["serving_claim_id"] is None
    assert tuples["measured_null"].extra["serving_claim_id"] is None
    # the experiment claim keeps its own statement/falsifier and numbers
    obs = exp.observation_of(tuples["kept"])
    assert obs["mechanism"]["statement"] and obs["effect_rel"] == pytest.approx(0.0205)
    assert exp.serving_claim_id({"comparison": {"belief_capture": {"capture_id": "short"}}}) is None


def test_retrofit_unless_the_row_has_a_belief_capture(store):
    for tup in projected(store).values():
        if tup is not None:
            assert exp.observation_of(tup)["retrofit"] is True
            assert "belief_capture_sha256" not in tup.extra
    # a capture that is not the producer's v1 seal is REFUSED, never read as prospective and
    # never silently demoted to retrofit
    row = next(r for r in exp.native_rows(store) if r["rowid"] == rowid_of("kept"))
    row["payload"] = {**row["payload"], "belief_capture": {"capture_sha256": aid("c")}}
    assert exp.classify(row) == (None, "belief_capture_schema")
    assert exp.project(row, store_manifest=MANIFEST) is None


#: frame ids of the retrofit fixture projected by the Phase-1 adapter (origin/main 3418c3adc,
#: before the Phase-2 capture verifier): the verifier must not move a single retrofit frame.
PHASE1_FRAMES = (33, "699f291e9ac5ebb6b1bb72ccf7ea43d93bab91d572067996b16d2e3dd57cfb91")


def test_retrofit_frame_ids_are_unchanged_by_the_capture_verifier(store):
    ids = [f["frame_id"] for t in projected(store).values() if t is not None
           for f in to_frames(t, as_of="2026-10-21T12:00:00Z", adapter_id=exp.ADAPTER_ID)]
    assert (len(ids), hashlib.sha256("\n".join(ids).encode()).hexdigest()) == PHASE1_FRAMES


# ------------------------------------------------------------------------------ Phase 2: prospective

#: Rows written by the RESEARCH writer (`loop/archive.record` -> `controller/experiment_capture.py`,
#: branch f8/ak-exp-belief-capture-20261024), read back from SQLite: the cross-repo contract test.
PROSPECTIVE = json.loads((Path(__file__).parent / "fixtures/autokernel_experiments/"
                          "prospective_rows.json").read_text())["rows"]
_ALL_COLUMNS = (*exp._COLUMNS, "payload")


def make_prospective_store(tmp_path, name="pstore", edit=None):
    store = tmp_path / name
    store.mkdir()
    conn = sqlite3.connect(store / "experiments.db")
    conn.executescript(SCHEMA)
    for row in PROSPECTIVE:
        row = dict(row)
        if edit:
            row = edit(row)
        conn.execute(f"INSERT INTO experiments ({','.join(_ALL_COLUMNS)}) VALUES "
                     f"({','.join('?' for _ in _ALL_COLUMNS)})", [row[c] for c in _ALL_COLUMNS])
    conn.commit()
    conn.close()
    return store


def test_producer_rows_verify_and_project_as_prospective(tmp_path):
    store = make_prospective_store(tmp_path)
    rows = exp.native_rows(store)
    assert [r["status"] for r in rows] == ["keep_candidate", "gate_refused", "anchor_verified",
                                           "measured_null"]
    for row in rows:
        assert exp.capture_refusal(row, row["payload"]) is None, row["status"]
        tup = exp.project(row, store_manifest=MANIFEST)
        assert tup is not None, row["status"]
        assert exp.observation_of(tup)["retrofit"] is False
        assert tup.extra["belief_capture_sha256"] == row["payload"]["belief_capture"]["content_sha256"]
        assert grade(tup)[:2] == ("Judged", "Located")  # no protocol: prospective is not graded up
        frames = to_frames(tup, as_of="2026-10-24T12:00:00Z", adapter_id=exp.ADAPTER_ID)
        assert all(f["provenance"].get("retrofit") is not True for f in frames)
    kept = exp.project(rows[0], store_manifest=MANIFEST)
    assert exp.applicability_of(kept)["model_sha256"] == hashlib.sha256(b"model").hexdigest()
    assert exp.observation_of(kept)["n_pairs"] == 5
    # the NaN effect column and the inf floor were sealed as null, as SQLite stores them
    assert rows[3]["effect_fraction"] is None
    report = exp.ingest([store], store_manifests={str(store): MANIFEST})
    assert (report["projected"], report["prospective"], report["retrofit"]) == (4, 4, 0)


def _refused(tmp_path, name, edit):
    store = make_prospective_store(tmp_path, name=name, edit=edit)
    return {r["status"]: exp.classify(r) for r in exp.native_rows(store)}


def _payload_edit(fn):
    def edit(row):
        payload = json.loads(row["payload"])
        fn(payload)
        return {**row, "payload": json.dumps(payload, sort_keys=True)}
    return edit


@pytest.mark.parametrize("name,edit,reason", [
    ("status", lambda r: {**r, "status": "kept"} if r["status"] == "keep_candidate" else r,
     "disagrees_with_row"),
    ("effect", lambda r: {**r, "effect_fraction": 0.5} if r["status"] == "keep_candidate" else r,
     "disagrees_with_row"),
    ("recorded", lambda r: {**r, "recorded_at": "2026-10-25T00:00:00Z"}, "disagrees_with_row"),
    ("pairs", _payload_edit(lambda p: p.get("comparison", {}).update(pairs=9)
                            if "comparison" in p else None), "disagrees_with_row"),
    ("model_sha", _payload_edit(lambda p: p["research_scope"]["model"].update(sha256="e" * 64)
                                if "research_scope" in p else None), "disagrees_with_row"),
    ("unprojected", _payload_edit(lambda p: p.update(reason="edited after the fact")),
     "disagrees_with_row"),
    ("subject", _payload_edit(lambda p: p["belief_capture"]["subject"]["row"].update(
        mechanism_id="akm-forged")), "hash_mismatch"),
    ("schema", _payload_edit(lambda p: p["belief_capture"].update(schema="v0")), "schema"),
    ("malformed", _payload_edit(lambda p: p["belief_capture"].update(content_sha256="x")),
     "malformed"),
])
def test_a_capture_that_does_not_seal_its_row_is_refused(tmp_path, name, edit, reason):
    verdicts = _refused(tmp_path, name, edit)
    touched = {status: v for status, v in verdicts.items() if v[0] is None}
    assert touched, name
    assert all(v == (None, f"belief_capture_{reason}") for v in touched.values()), (name, verdicts)


def test_refused_captures_are_counted_not_dropped(tmp_path):
    store = make_prospective_store(tmp_path, edit=lambda r: {**r, "recorded_at": "2026-10-25T00:00:00Z"})
    report = exp.ingest([store], store_manifests={str(store): MANIFEST})
    assert report["projected"] == 0 and report["rows_read"] == 4
    assert report["not_projected"] == {"belief_capture_disagrees_with_row": 4}


# ------------------------------------------------------------------------------ ingest / CLI


def test_dry_run_counts_and_touches_no_ledger(store, tmp_path):
    report = exp.ingest([store], store_manifests={str(store): MANIFEST})
    assert report["dry_run"] and report["rows_read"] == len(FIXTURE)
    assert report["projected"] == len(EXPECTED) and report["frames"] == 3 * len(EXPECTED)
    assert report["by_disposition"] == {"measurement": 5, "verifier": 4, "baseline": 2}
    assert report["by_outcome"]["refused_correctness"] == 3
    assert report["not_projected"]["no_attempt_id"] == 1 and report["not_projected"]["noise"] == 1
    assert report["by_scope_basis"].get("native", 0) >= 5
    assert report["by_scope_basis"].get("store_manifest", 0) >= 1
    assert report["retrofit"] == report["projected"]
    assert report["stores"][0]["max_rowid"] == len(FIXTURE)
    assert report["projection_errors"] == []
    assert not (tmp_path / "ledger.jsonl").exists()


def test_cli_defaults_to_dry_run_and_prints_counts(store, capsys, tmp_path):
    assert cli.main(["ingest", "autokernel-experiments", "--store", str(store)]) == 0
    out = capsys.readouterr().out
    assert "dry run" in out and "projected=" in out and "not projected:" in out


def test_cli_json_report_and_since_rowid(store, capsys):
    assert cli.main(["--json", "ingest", "autokernel-experiments", "--store", str(store),
                     "--since-rowid", "15"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["dry_run"] and report["rows_read"] == len(FIXTURE) - 15
    assert report["stores"][0]["max_rowid"] == len(FIXTURE)


def test_cli_requires_a_store_with_a_db(tmp_path, capsys):
    assert cli.main(["ingest", "autokernel-experiments"]) == 2
    assert cli.main(["ingest", "autokernel-experiments", "--store", str(tmp_path)]) == 2
    assert "experiments.db" in capsys.readouterr().err


def test_cli_writes_only_to_an_explicit_ledger(store, tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    monkeypatch.setenv("VIDYA_STATE_DIR", str(state))
    monkeypatch.setenv("VIDYA_LEDGER", str(tmp_path / "env-ledger.jsonl"))
    # no --ledger: the env/default resolution is NOT an explicit write target
    assert cli.main(["ingest", "autokernel-experiments", "--store", str(store),
                     "--as-of", "2026-10-21T12:00:00Z"]) == 0
    assert not state.exists() and not (tmp_path / "env-ledger.jsonl").exists()
    # explicit scratch ledger, subcommand-side flag
    target = tmp_path / "scratch" / "ledger.jsonl"
    target.parent.mkdir()
    assert cli.main(["ingest", "autokernel-experiments", "--store", str(store),
                     "--ledger", str(target), "--as-of", "2026-10-21T12:00:00Z"]) == 0
    led = Ledger(target)
    first = len(led.read_all())
    assert first > 0 and led.verify() == []
    # idempotent: a second run appends nothing
    assert cli.main(["ingest", "autokernel-experiments", "--store", str(store),
                     "--ledger", str(target), "--as-of", "2026-10-21T12:00:00Z"]) == 0
    assert len(Ledger(target).read_all()) == first
    capsys.readouterr()


def test_cli_write_needs_as_of(store, tmp_path, capsys):
    target = tmp_path / "l.jsonl"
    assert cli.main(["ingest", "autokernel-experiments", "--store", str(store),
                     "--ledger", str(target)]) == 2
    assert not target.exists() and "--as-of" in capsys.readouterr().err


def test_cli_refuses_the_canonical_ledger_without_the_ownership_flag(store, tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("VIDYA_STATE_DIR", str(state))
    canonical = state / "ledger.jsonl"
    argv = ["ingest", "autokernel-experiments", "--store", str(store), "--ledger", str(canonical),
            "--as-of", "2026-10-21T12:00:00Z"]
    assert cli.main(argv) == 2
    assert not canonical.exists() and "canonical ledger" in capsys.readouterr().err
    assert cli.main(["--ledger", str(canonical), *argv[:4], "--as-of", "2026-10-21T12:00:00Z"]) == 2
    assert not canonical.exists()
    # a symlink to it is the same file
    link = tmp_path / "alias.jsonl"
    link.symlink_to(canonical)
    assert cli.main([*argv[:4], "--ledger", str(link), "--as-of", "2026-10-21T12:00:00Z"]) == 2
    # the owning session may
    assert cli.main([*argv, "--i-own-the-canonical-ledger"]) == 0
    assert canonical.exists() and Ledger(canonical).verify() == []


def test_the_real_canonical_path_is_refused_even_when_the_env_moves_the_state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDYA_STATE_DIR", str(tmp_path))
    with pytest.raises(ProjectionError, match="canonical ledger"):
        exp.check_ledger_target("/mnt/raid0/llm/state/vidya/ledger.jsonl", i_own_canonical=False)
    assert exp.check_ledger_target(tmp_path / "copy.jsonl", i_own_canonical=False)


def test_dry_run_flag_beats_an_explicit_ledger(store, tmp_path):
    target = tmp_path / "l.jsonl"
    assert cli.main(["ingest", "autokernel-experiments", "--store", str(store), "--ledger",
                     str(target), "--as-of", "2026-10-21T12:00:00Z", "--dry-run"]) == 0
    assert not target.exists()


def test_frames_carry_the_observation_on_the_evidence_assertion(store):
    tup = projected(store)["kept"]
    evidence = [f for f in to_frames(tup, as_of="2026-10-21T12:00:00Z", adapter_id=exp.ADAPTER_ID)
                if f["frame_type"].endswith("evidence_supports_claim/v1")][0]
    assertion = evidence["assertion"]
    assert assertion["observation"]["outcome"] == "improved"
    assert assertion["observation"]["effect_rel"] == "0.0205"  # carrier encodes floats as strings
    assert assertion["metric"] == "aggregate_tok_s" and assertion["unit"] == "t/s"


def test_resolve_runs_at_most_once_per_store_across_floor_and_experiments(store, tmp_path, monkeypatch):
    """One memo-cached manifest per store serves the floor path and the experiments path."""
    import scoped_ingest as si
    from adapters import _ak_store_manifest as owner
    from adapters import autokernel_serving_floor as floor

    calls = []
    real = owner.resolve
    monkeypatch.setattr(owner, "resolve", lambda s: (calls.append(str(s)), real(s))[1])
    fake = store / "serving-floor.fixture.json"
    fake.write_text("{}")
    monkeypatch.setattr(floor, "floor_paths", lambda s: [fake] if Path(s) == store else [])

    def refuse(path):
        raise ProjectionError("fixture floor is not a real floor")

    monkeypatch.setattr(floor, "read_floor", refuse)
    memo = tmp_path / "memo.json"
    first = si.ingest_scoped_store(tmp_path / "l1.jsonl", store, as_of="2026-10-21T12:00:00Z",
                                   memo_path=memo)
    assert first["floors_listed"] == 1 and first["experiments_rows_read"] == len(FIXTURE)
    assert calls == [str(store)] and first["experiments_manifests_built"] == 1
    # a later planning step, same memo: the cached manifest answers both paths
    second = si.ingest_scoped_store(tmp_path / "l2.jsonl", store, as_of="2026-10-21T12:00:00Z",
                                    memo_path=memo)
    assert second["floors_listed"] == 1 and calls == [str(store)]
    assert second["experiments_manifests_built"] == 0
