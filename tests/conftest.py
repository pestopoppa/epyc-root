"""Suite-wide hermetic seams.

THE CURRENT-SERIAL-RUN POINTER (2026-09-16). ``dashboard.loop_status`` prefers
the host's ``current-serial-run.json`` over ``AUTOKERNEL_LOOP_STORE_ROOT``
(a1cb667f). On a host where a serial run is live, every test that injects a
fixture store through that env var — or that reads the hub's own payload —
silently read the live serial run instead, and went red the moment the
autokernel session started one. Point the pointer at a path that never exists
for every test. Tests that exercise the pointer set the variable themselves
(``monkeypatch.setenv`` / ``os.environ``), which overrides this default.
"""
from __future__ import annotations

import pytest

CURRENT_SERIAL_RUN_ENV = "AUTOKERNEL_CURRENT_SERIAL_RUN_POINTER"


@pytest.fixture(autouse=True)
def _no_host_current_serial_run_pointer(tmp_path_factory, monkeypatch):
    missing = tmp_path_factory.getbasetemp() / "no-current-serial-run.json"
    monkeypatch.setenv(CURRENT_SERIAL_RUN_ENV, str(missing))


@pytest.fixture(autouse=True)
def _dashboard_artifacts_are_test_owned(request, tmp_path, monkeypatch):
    """Never let a dashboard test inherit an unrelated campaign or gate bundle.

    Test-specific monkeypatches run after this fixture. Missing producer artifacts
    remain honestly absent; tests that need data must supply original fixtures.
    """
    if not (request.node.path.name.startswith("test_dashboard_")
            or request.node.path.name == "test_production_kernel_set.py"):
        return
    from pathlib import Path
    from dashboard import kernel_contract, kernel_identity, kernel_progression, server
    for module in (server, kernel_contract, kernel_identity, kernel_progression):
        for name, value in list(vars(module).items()):
            if (isinstance(value, Path) and str(value).startswith((
                    "/mnt/raid0/llm/autokernel", "/mnt/raid0/llm/llama.cpp",
                    "/mnt/raid0/llm/epyc-inference-research",
                    "/workspace/repos/epyc-inference-research"))):
                monkeypatch.setattr(module, name, tmp_path / "absent" / name)
    for key in ("AUTOKERNEL_LOOP_STORE_ROOT", "AUTOKERNEL_FROZEN_TREE", "AUTOKERNEL_CHAMPION_TREE"):
        monkeypatch.setenv(key, str(tmp_path / "absent" / key))
    for key in ("AUTOKERNEL_CAMPAIGN_STORE_ROOT", "AUTOKERNEL_CAMPAIGN_ID",
                "AUTOKERNEL_CAMPAIGN_CONFIG_GENERATION", "AUTOKERNEL_CAMPAIGN_CONFIG_DIGEST"):
        monkeypatch.delenv(key, raising=False)
    server._watchdog_state.clear()
    kernel_contract._watchdog_state.clear()
    for module in (kernel_identity, kernel_contract):
        for name in ("PRODUCTION_KERNEL_ATTESTATION", "SPEECH_KERNEL_ATTESTATION"):
            monkeypatch.setattr(module, name, tmp_path / "absent" / name)
    monkeypatch.setattr(kernel_identity, "PRODUCTION_LLAMA_BINARIES", {
        key: tmp_path / "absent" / key for key in ("cpu", "hip")})
    monkeypatch.setattr(kernel_identity, "PRODUCTION_STABLE_LINKS", {
        key: (str(tmp_path / "absent" / key), name)
        for key, (_, name) in kernel_identity.PRODUCTION_STABLE_LINKS.items()})
