"""TD-21: prove the tests/unit/ hermetic seam actually keeps the real
inference lock / contention gate out of unit tests.

`tests/unit/conftest.py::_hermetic_inference_lock_and_contention_gate` is an
autouse fixture that redirects `ORCHESTRATOR_PATHS_TMP_DIR` and forces
`ORCHESTRATOR_PER_REGION_LOCKS` off for every test in this directory. This
module is the seam's own regression test: it drives a REAL `LLMPrimitives`
with a MOCKED backend through the real (unmocked) `_real_call()` ->
contention-gate -> `inference_lock()` control flow and asserts the resolved
lock file never lands under the real, shared-host `/mnt/raid0/llm/tmp`.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

import src.runtime.inference_lock as rt_lock
from src.llm_primitives import LLMPrimitives
from src.model_server import InferenceResult

_REAL_PROD_LOCK_FILE = "/mnt/raid0/llm/tmp/heavy_model.lock"


def _mocked_result(role: str) -> InferenceResult:
    return InferenceResult(
        role=role,
        output="ok",
        tokens_generated=1,
        generation_speed=1.0,
        elapsed_time=0.001,
        success=True,
        prompt_eval_ms=0.1,
        generation_ms=0.1,
        http_overhead_ms=0.0,
    )


def test_real_call_with_mocked_backend_never_touches_the_production_lock_file(
    monkeypatch, tmp_path_factory
):
    """A real LLMPrimitives + mocked backend still reaches `inference_lock()`
    inside `_real_call`. Under the tests/unit/ hermetic fixture, the resolved
    lock path must be some path under pytest's own base temp directory --
    never the real, shared `/mnt/raid0/llm/tmp/heavy_model.lock` other
    sessions on this host may be holding.
    """
    captured_paths: list = []
    original_lock_path = rt_lock._lock_path

    def _spy(role: str):
        path = original_lock_path(role)
        captured_paths.append(path)
        return path

    monkeypatch.setattr(rt_lock, "_lock_path", _spy)

    prims = LLMPrimitives(mock_mode=False, server_urls={"role_a": "http://localhost:9101"})
    backend = Mock(spec=[])
    backend.infer = Mock(return_value=_mocked_result("role_a"))
    prims._backends["role_a"] = backend

    result = prims._real_call("prompt", "role_a", n_tokens=8)

    # pytest's own base temp dir for this session/worker, e.g.
    # /tmp/pytest-of-<user>/pytest-<n>/ -- the hermetic fixture's own
    # tmp_path_factory.mktemp(...) directory lives under this, as a SIBLING
    # of (not nested inside) this test's own `tmp_path`.
    pytest_base_tmp = tmp_path_factory.getbasetemp()

    assert result == "ok"
    assert captured_paths, "inference_lock's _lock_path was never called -- test no longer exercises the lock seam"
    for path in captured_paths:
        assert str(path).startswith(str(pytest_base_tmp)), (
            f"resolved lock path {path} escaped pytest's own base temp dir ({pytest_base_tmp}); "
            "the hermetic seam is not redirecting the lock's get_config()"
        )
        assert str(path) != _REAL_PROD_LOCK_FILE, (
            "resolved lock path IS the real shared-host production lock file"
        )


@pytest.mark.real_inference_lock_state
def test_opt_out_marker_restores_the_real_env_derived_lock_path(monkeypatch):
    """Tests marked `real_inference_lock_state` skip the hermetic override and
    see whatever `_lock_path()` resolves to from the ambient environment (its
    own documented default/override contract) -- proving the opt-out works.
    """
    monkeypatch.delenv("ORCHESTRATOR_PATHS_TMP_DIR", raising=False)
    from src.config import reset_config

    reset_config()
    try:
        path = rt_lock._lock_path("frontdoor")
        assert path.name == "heavy_model.lock"
        # Ambient default resolution (no test-fixture override in effect):
        # PathsConfig.tmp_dir falls back to {llm_root}/tmp.
        assert str(path).endswith("/tmp/heavy_model.lock")
    finally:
        reset_config()
