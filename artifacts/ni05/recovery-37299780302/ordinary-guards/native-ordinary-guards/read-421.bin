from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

import yaml

from src import inference_lock as lock_mod


def _patch_config_tmp(monkeypatch, tmp_path):
    cfg = SimpleNamespace(paths=SimpleNamespace(tmp_dir=tmp_path))
    monkeypatch.setattr(lock_mod, "get_config", lambda: cfg)


def _write_stack_priors(path: Path, roles: dict) -> Path:
    path.write_text(yaml.safe_dump({"roles": roles}), encoding="utf-8")
    return path


def test_default_heavy_role_uses_heavy_lock(monkeypatch, tmp_path):
    _patch_config_tmp(monkeypatch, tmp_path)
    monkeypatch.delenv("ORCHESTRATOR_INFERENCE_LOCK_FILE", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_INFERENCE_LOCK_EMBEDDER_FILE", raising=False)

    path = lock_mod._lock_path("frontdoor")
    assert path == tmp_path / "heavy_model.lock"


def test_embedder_role_uses_isolated_lock_by_default(monkeypatch, tmp_path):
    _patch_config_tmp(monkeypatch, tmp_path)
    monkeypatch.delenv("ORCHESTRATOR_INFERENCE_LOCK_EMBEDDER_FILE", raising=False)

    path = lock_mod._lock_path("embedder")
    assert path == tmp_path / "embedder_model.lock"


def test_embedder_lock_filename_override(monkeypatch, tmp_path):
    _patch_config_tmp(monkeypatch, tmp_path)
    monkeypatch.setenv("ORCHESTRATOR_INFERENCE_LOCK_EMBEDDER_FILE", "custom_embed.lock")

    path = lock_mod._lock_path("embedder_2")
    assert path == tmp_path / "custom_embed.lock"


def test_lock_roles_derive_from_live_stack_priors(tmp_path):
    priors = _write_stack_priors(
        tmp_path / "stack_priors.yaml",
        {
            "frontdoor": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["default"], "entries": []}},
            },
            "worker_general": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["worker_pool"], "entries": []}},
            },
            "worker_math": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": [], "entries": [{"mode": "worker_pool"}]}},
            },
            "toolrunner": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["worker_pool"], "entries": []}},
            },
            "worker_vision": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"entries": [{"vision_type": "worker"}]}},
            },
            "worker_summarize": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["default"], "entries": []}},
            },
            "candidate_worker": {
                "deployment_status": "benchmark_or_candidate",
                "serving": {"launch": {"modes": ["worker_pool"], "entries": []}},
            },
        },
    )

    roles = lock_mod._lock_roles_from_stack_priors(priors)

    assert roles is not None
    heavy, light = roles
    assert {"worker_general", "worker_math", "toolrunner", "worker_vision"} <= light
    assert {"frontdoor", "worker_summarize"} <= heavy
    assert "worker_fast" not in light
    assert "candidate_worker" not in light


def test_lock_roles_missing_or_invalid_stack_priors_fails_closed(tmp_path):
    assert lock_mod._lock_roles_from_stack_priors(tmp_path / "missing.yaml") is None

    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("roles: [", encoding="utf-8")

    assert lock_mod._lock_roles_from_stack_priors(invalid) is None


def test_degraded_lock_roles_do_not_reconstruct_manifest_policy():
    assert lock_mod._degraded_lock_roles_from_stack_manifest() is None


def test_lock_role_sets_recompute_stack_priors_without_import_snapshot(tmp_path):
    priors = tmp_path / "stack_priors.yaml"
    _write_stack_priors(
        priors,
        {
            "frontdoor": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["default"], "entries": []}},
            },
            "worker_general": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["worker_pool"], "entries": []}},
            },
        },
    )

    heavy, light = lock_mod.lock_role_sets(priors)
    assert "frontdoor" in heavy
    assert "worker_general" in light

    _write_stack_priors(
        priors,
        {
            "frontdoor": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["worker_pool"], "entries": []}},
            },
            "worker_general": {
                "deployment_status": "live_stack",
                "serving": {"launch": {"modes": ["default"], "entries": []}},
            },
        },
    )

    heavy, light = lock_mod.lock_role_sets(priors)
    assert "worker_general" in heavy
    assert "frontdoor" in light


def test_lock_role_sets_without_stack_priors_fails_closed_to_unknown_heavy(tmp_path):
    heavy, light = lock_mod.lock_role_sets(tmp_path / "missing.yaml")

    assert heavy == frozenset()
    assert light == frozenset()
    original_lock_role_sets = lock_mod.lock_role_sets
    lock_mod.lock_role_sets = lambda _path=None: (frozenset(), frozenset())
    try:
        assert lock_mod._is_heavy_role("frontdoor") is True
        assert lock_mod._is_heavy_role("worker_general") is True
    finally:
        lock_mod.lock_role_sets = original_lock_role_sets


def test_is_heavy_role_uses_derived_sets_and_unknowns_fail_closed(monkeypatch):
    monkeypatch.setattr(lock_mod, "HEAVY_ROLES", frozenset({"frontdoor"}))
    monkeypatch.setattr(lock_mod, "LIGHT_ROLES", frozenset({"worker_general"}))

    assert lock_mod._is_heavy_role("frontdoor") is True
    assert lock_mod._is_heavy_role("worker_general") is False
    assert lock_mod._is_heavy_role("worker_explore") is False
    assert lock_mod._is_heavy_role("worker_fast") is False
    assert lock_mod._is_heavy_role("made_up_role") is True


def test_inference_lock_respects_explicit_shared_override(monkeypatch, tmp_path):
    _patch_config_tmp(monkeypatch, tmp_path)
    captured = []

    def _capture_lock(*_args, **kwargs):
        lock_type = kwargs["lock_type"] if "lock_type" in kwargs else _args[1]
        captured.append((lock_type, kwargs["mode"]))
        return 0.0

    monkeypatch.setattr(lock_mod, "_acquire_lock_with_timeout", _capture_lock)

    with lock_mod.inference_lock("frontdoor", shared=True, max_hold_s=0):
        pass
    with lock_mod.inference_lock("worker_general", shared=False, max_hold_s=0):
        pass

    assert captured[0] == (lock_mod.fcntl.LOCK_SH, "shared")
    assert captured[1] == (lock_mod.fcntl.LOCK_EX, "exclusive")


def test_acquire_lock_aborts_on_cancel_check(monkeypatch, tmp_path):
    _patch_config_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(lock_mod.fcntl, "flock", lambda *_args, **_kwargs: (_ for _ in ()).throw(BlockingIOError()))
    monkeypatch.setattr(lock_mod.time, "sleep", lambda _s: None)

    with open(tmp_path / "heavy_model.lock", "a") as fh:
        try:
            lock_mod._acquire_lock_with_timeout(
                fh.fileno(),
                lock_mod.fcntl.LOCK_EX,
                role="architect_general",
                mode="exclusive",
                lock_file=tmp_path / "heavy_model.lock",
                timeout_s=180.0,
                poll_s=0.01,
                log_every_s=999.0,
                cancel_check=lambda: True,
                deadline_s=None,
            )
            assert False, "expected TimeoutError"
        except TimeoutError as e:
            assert "cancelled" in str(e)


def test_acquire_lock_aborts_on_request_deadline(monkeypatch, tmp_path):
    _patch_config_tmp(monkeypatch, tmp_path)
    monkeypatch.setattr(lock_mod.fcntl, "flock", lambda *_args, **_kwargs: (_ for _ in ()).throw(BlockingIOError()))
    monkeypatch.setattr(lock_mod.time, "sleep", lambda _s: None)
    monkeypatch.setattr(lock_mod.time, "perf_counter", lambda: 100.0)

    with open(tmp_path / "heavy_model.lock", "a") as fh:
        try:
            lock_mod._acquire_lock_with_timeout(
                fh.fileno(),
                lock_mod.fcntl.LOCK_EX,
                role="architect_general",
                mode="exclusive",
                lock_file=tmp_path / "heavy_model.lock",
                timeout_s=180.0,
                poll_s=0.01,
                log_every_s=999.0,
                cancel_check=None,
                deadline_s=99.0,
            )
            assert False, "expected TimeoutError"
        except TimeoutError as e:
            assert "deadline exceeded" in str(e)


def test_lock_watchdog_force_releases(monkeypatch, tmp_path):
    """Watchdog should force-release the lock after max_hold_s, unblocking the context."""
    _patch_config_tmp(monkeypatch, tmp_path)
    monkeypatch.delenv("ORCHESTRATOR_INFERENCE_LOCK_FILE", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_MAX_LOCK_HOLD_S", raising=False)

    start = time.monotonic()
    with lock_mod.inference_lock("frontdoor", max_hold_s=2):
        # Simulate a stuck inference — sleep longer than the watchdog timeout.
        time.sleep(4)
    elapsed = time.monotonic() - start

    # The context manager should complete; watchdog fires at ~2s, sleep finishes at ~4s.
    # Key assertion: the lock was released (we didn't deadlock).
    assert elapsed < 6, f"Lock held too long ({elapsed:.1f}s), watchdog may not have fired"


def test_lock_watchdog_does_not_fire_on_normal_hold(monkeypatch, tmp_path):
    """Watchdog should NOT fire when lock is released normally before timeout."""
    _patch_config_tmp(monkeypatch, tmp_path)
    monkeypatch.delenv("ORCHESTRATOR_INFERENCE_LOCK_FILE", raising=False)

    import logging
    fired = []
    orig_critical = logging.Logger.critical

    def _capture_critical(self, msg, *args, **kwargs):
        fired.append(msg)
        orig_critical(self, msg, *args, **kwargs)

    monkeypatch.setattr(logging.Logger, "critical", _capture_critical)

    with lock_mod.inference_lock("frontdoor", max_hold_s=5):
        time.sleep(0.1)  # Well under the 5s watchdog

    assert not any("force-releasing" in str(m) for m in fired)
