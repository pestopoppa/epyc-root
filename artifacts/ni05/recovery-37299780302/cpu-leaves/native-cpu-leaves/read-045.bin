"""AP-55: per-trial infra fingerprint + explicit NON_COMPARABLE marking.

Pins: every component is digested separately so a comparison names what moved;
volatile facts (PIDs, start times) never enter a digest; an unreadable side is
UNVERIFIED, never COMPARABLE; PID reuse from a stale stack state file is refused;
journal rows round-trip the fingerprint and legacy rows load without one.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from src.autopilot_core import infra_fingerprint as inf  # noqa: E402
from src.autopilot_core.infra_fingerprint import (  # noqa: E402
    COMPARABLE,
    NON_COMPARABLE,
    UNVERIFIED,
    collect_infra_fingerprint,
    compare_infra_fingerprints,
    group_by_infra_regime,
)


def _fake_roots(tmp_path: Path, *, thp: str = "[always] madvise never") -> tuple[Path, Path]:
    proc = tmp_path / "proc"
    sysr = tmp_path / "sys"
    (proc / "sys/kernel").mkdir(parents=True, exist_ok=True)
    (proc / "sys/kernel/numa_balancing").write_text("0\n")
    (proc / "cpuinfo").write_text("model name\t: Unit CPU\n")
    (proc / "stat").write_text(f"cpu 0 0\nbtime {int(time.time()) - 1000}\n")
    (sysr / "kernel/mm/transparent_hugepage").mkdir(parents=True, exist_ok=True)
    (sysr / "kernel/mm/transparent_hugepage/enabled").write_text(thp + "\n")
    (sysr / "kernel/mm/transparent_hugepage/defrag").write_text("madvise\n")
    return proc, sysr


def _orch_root(tmp_path: Path) -> Path:
    root = tmp_path / "orch"
    (root / "scripts/autopilot").mkdir(parents=True, exist_ok=True)
    (root / "orchestration").mkdir(parents=True, exist_ok=True)
    (root / "scripts/autopilot/eval_tower.py").write_text("EVAL = 1\n")
    (root / "orchestration/model_registry.yaml").write_text("roles: {}\n")
    return root


def _collect(tmp_path: Path, **over):
    proc, sysr = _fake_roots(tmp_path, thp=over.pop("thp", "[always] madvise never"))
    root = over.pop("root", None) or _orch_root(tmp_path)
    binary = tmp_path / "llama-server"
    if not binary.exists():
        binary.write_bytes(over.pop("binary_bytes", b"\x7fELF-v9"))
    model = tmp_path / "m.gguf"
    if not model.exists():
        model.write_bytes(b"GGUF" + b"\0" * 64)
    state = over.pop(
        "stack_state",
        {"frontdoor": {"role": "frontdoor", "pid": 99999999, "port": 8080,
                       "started_at": "2026-09-01T00:00:00", "model_path": str(model)}},
    )
    return collect_infra_fingerprint(
        orchestrator_root=root,
        stack_state=state,
        fallback_binary=binary,
        proc_root=proc,
        sys_root=sysr,
        **over,
    )


def test_fingerprint_has_every_component_digest_and_overall_digest(tmp_path):
    fp = _collect(tmp_path)
    assert set(fp["component_digests"]) == set(inf.COMPONENTS)
    assert len(fp["digest"]) == 64
    # orchestrator root is not a git repo -> recorded as unavailable, never guessed
    assert "orchestrator" in fp["unavailable"]
    assert fp["components"]["kernel"]["declared_binaries"]
    assert fp["components"]["host"]["thp_enabled"] == "[always] madvise never"


def test_identical_regime_is_stable_and_volatile_facts_do_not_enter_digest(tmp_path):
    a = _collect(tmp_path)
    b = _collect(
        tmp_path,
        stack_state={"frontdoor": {"role": "frontdoor", "pid": 88888888, "port": 8080,
                                   "started_at": "2026-09-02T00:00:00",
                                   "model_path": str(tmp_path / "m.gguf")}},
    )
    assert a["component_digests"]["models"] == b["component_digests"]["models"]
    assert a["component_digests"]["kernel"] == b["component_digests"]["kernel"]


def test_binary_change_is_non_comparable_and_named(tmp_path):
    a = _collect(tmp_path)
    (tmp_path / "llama-server").write_bytes(b"\x7fELF-v10")
    b = _collect(tmp_path)
    verdict = compare_infra_fingerprints(b, a, reference_label="baseline_tier_1")
    assert verdict["status"] == NON_COMPARABLE
    assert verdict["differing_components"] == ["kernel"]
    assert verdict["reference"] == "baseline_tier_1"


def test_host_config_change_is_non_comparable(tmp_path):
    a = _collect(tmp_path)
    b = _collect(tmp_path, thp="always [madvise] never")
    assert compare_infra_fingerprints(b, a)["differing_components"] == ["host"]


def test_requantised_model_changes_models_component(tmp_path):
    a = _collect(tmp_path)
    (tmp_path / "m.gguf").write_bytes(b"GGUF" + b"\1" * 64)
    b = _collect(tmp_path)
    assert "models" in compare_infra_fingerprints(b, a)["differing_components"]


def test_missing_fingerprint_is_unverified_never_comparable(tmp_path):
    a = _collect(tmp_path)
    assert compare_infra_fingerprints(a, None)["status"] == UNVERIFIED
    assert compare_infra_fingerprints({}, a)["status"] == UNVERIFIED
    assert compare_infra_fingerprints({"status": "capture_error"}, a)["status"] == UNVERIFIED


def test_unreadable_component_on_both_sides_is_unverified_not_comparable(tmp_path):
    a = _collect(tmp_path)
    b = _collect(tmp_path)
    # both lack a git orchestrator -> no difference found, but not proven equal
    verdict = compare_infra_fingerprints(b, a)
    assert verdict["status"] == UNVERIFIED
    assert "orchestrator" in verdict["unverified_components"]


def test_fully_readable_identical_regime_is_comparable():
    digests = {name: f"d-{name}" for name in inf.COMPONENTS}
    fp = {"digest": "x", "component_digests": digests, "kernel_evidence": "live"}
    assert compare_infra_fingerprints(fp, dict(fp))["status"] == COMPARABLE


def test_stale_pid_is_not_attributed_to_the_stack(tmp_path):
    proc, _ = _fake_roots(tmp_path)
    pid_dir = proc / "4242"
    pid_dir.mkdir()
    other = tmp_path / "unrelated-bin"
    other.write_bytes(b"other")
    os.symlink(other, pid_dir / "exe")
    (pid_dir / "maps").write_text("")
    # process started 10s after boot; the state row claims a start weeks later
    (pid_dir / "stat").write_text("4242 (x) S " + " ".join(["0"] * 18) + " 1000 0\n")
    row = {"pid": 4242, "started_at": datetime.now().isoformat()}
    assert inf._pid_matches_row(4242, row, proc) is False
    comp = inf._kernel_component({"r": row}, fallback_binary=None, proc_root=proc)
    assert comp.get("status") == "unavailable"


def test_live_process_libraries_enter_kernel_digest(tmp_path):
    proc, _ = _fake_roots(tmp_path)
    pid_dir = proc / "4243"
    pid_dir.mkdir()
    exe = tmp_path / "llama-server-live"
    exe.write_bytes(b"live")
    lib = tmp_path / "libggml-cpu.so"
    lib.write_bytes(b"ggml-a")
    os.symlink(exe, pid_dir / "exe")
    (pid_dir / "maps").write_text(
        f"7f00-7f01 r-xp 00000000 00:00 1   {lib}\n7f01-7f02 r-xp 0 00:00 2 /usr/lib/libc.so.6\n"
    )
    btime = int((proc / "stat").read_text().split("btime ")[1])
    ticks = os.sysconf("SC_CLK_TCK")
    started = time.time() - 60
    (pid_dir / "stat").write_text(
        "4243 (llama-server) S " + " ".join(["0"] * 18) + f" {int((started - btime) * ticks)} 0\n"
    )
    row = {"pid": 4243, "started_at": datetime.fromtimestamp(started).isoformat()}
    a = inf._kernel_component({"r": row}, fallback_binary=None, proc_root=proc)
    assert list(a["live_libraries"]) == [str(lib)]
    lib.write_bytes(b"ggml-b")
    inf._FILE_DIGEST_CACHE.clear()
    b = inf._kernel_component({"r": row}, fallback_binary=None, proc_root=proc)
    assert a["digest"] != b["digest"]


def test_group_by_regime_separates_batches():
    rows = [
        {"trial_id": 1, "infra_fingerprint": {"digest": "a"}},
        {"trial_id": 2, "infra_fingerprint": {"digest": "b"}},
        {"trial_id": 3},
    ]
    assert group_by_infra_regime(rows) == {"a": [1], "b": [2], "": [3]}


def _entry(trial_id: int, **over) -> JournalEntry:
    base = dict(trial_id=trial_id, timestamp="2026-09-16T00:00:00+00:00", species="s",
                action_type="numeric_trial", tier=1, quality=1.0, speed=1.0, cost=1.0,
                reliability=1.0, pareto_status="candidate")
    base.update(over)
    return JournalEntry(**base)


def test_journal_round_trips_fingerprint_and_measurement_carries_it(tmp_path):
    fp = {"digest": "f" * 64, "component_digests": {}}
    comp = {"status": NON_COMPARABLE, "differing_components": ["kernel"]}
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1, infra_fingerprint=fp, comparability=comp))
    reloaded = ExperimentJournal(journal_dir=tmp_path).all_entries()[0]
    assert reloaded.infra_fingerprint == fp
    assert reloaded.comparability == comp
    assert reloaded.measurement["infra_fingerprint"] == "f" * 64
    assert reloaded.measurement["comparability"] == NON_COMPARABLE


def test_legacy_row_without_fingerprint_loads_and_claims_nothing(tmp_path):
    legacy = _entry(1)
    row = {k: v for k, v in legacy.__dict__.items()
           if k not in {"infra_fingerprint", "comparability", "measurement"}}
    (tmp_path / "autopilot_journal.jsonl").write_text(json.dumps(row) + "\n")
    loaded = ExperimentJournal(journal_dir=tmp_path).all_entries()[0]
    assert loaded.infra_fingerprint == {}
    assert loaded.comparability == {}


def test_baseline_promotion_event_carries_fingerprint(tmp_path):
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1))
    event = journal.append_baseline_promotion_event(
        source_trial_id=1, tier=1, previous_quality=1.0, new_quality=1.1,
        reason="ok", proof={}, result_metrics={}, baseline_state={},
        infra_fingerprint={"digest": "abc"},
    )
    assert event["infra_fingerprint"] == {"digest": "abc"}
    assert ExperimentJournal(journal_dir=tmp_path).baseline_promotion_events() == [event]


# ── autopilot wiring ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def autopilot():
    import autopilot as module  # noqa: E402

    return module


def _fp(**digests):
    full = {name: f"d-{name}" for name in inf.COMPONENTS}
    full.update(digests)
    return {"digest": inf._digest(full), "component_digests": full, "kernel_evidence": "live"}


def test_trial_against_unfingerprinted_baseline_is_unverified(autopilot):
    verdict = autopilot._infra_comparability_for_trial({}, 1, _fp())
    assert verdict["status"] == UNVERIFIED


def test_promotion_records_reference_regime_then_drift_is_marked(autopilot):
    state: dict = {}
    promoted = SimpleNamespace(updated=True, tier=1)
    autopilot._record_baseline_infra_fingerprint(state, promoted, _fp())
    assert autopilot._infra_comparability_for_trial(state, 1, _fp())["status"] == COMPARABLE
    moved = autopilot._infra_comparability_for_trial(
        state, 1, _fp(kernel="d-kernel-v10"), baseline_revision=3
    )
    assert moved["status"] == NON_COMPARABLE
    assert moved["differing_components"] == ["kernel"]
    assert moved["reference"] == "baseline_tier_1_rev3"
    # other tiers keep no reference
    assert autopilot._infra_comparability_for_trial(state, 2, _fp())["status"] == UNVERIFIED


def test_rejected_promotion_does_not_move_reference(autopilot):
    state: dict = {}
    autopilot._record_baseline_infra_fingerprint(state, SimpleNamespace(updated=False, tier=1), _fp())
    autopilot._record_baseline_infra_fingerprint(state, None, _fp())
    assert autopilot.BASELINE_INFRA_FINGERPRINTS_STATE_KEY not in state


def test_mid_trial_regime_change_is_non_comparable_even_with_matching_baseline(autopilot):
    state: dict = {}
    autopilot._record_baseline_infra_fingerprint(state, SimpleNamespace(updated=True, tier=1), _fp())
    verdict = autopilot._infra_comparability_for_trial(
        state, 1, _fp(), dispatch_fingerprint=_fp(models="d-models-old")
    )
    assert verdict["status"] == NON_COMPARABLE
    assert verdict["mid_trial"]["differing_components"] == ["models"]


def test_baseline_fingerprint_field_is_daemon_owned():
    from state_ownership import DAEMON_OWNED_STATE_FIELDS, KNOWN_EXTERNAL_CONTROL_FIELDS

    assert "baseline_infra_fingerprints" in DAEMON_OWNED_STATE_FIELDS
    assert "baseline_infra_fingerprints" not in KNOWN_EXTERNAL_CONTROL_FIELDS
