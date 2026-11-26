"""Regression evidence for the calibration-only LOOP-62 recipe check."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "coordination"))
from taskflow import loop_contract  # noqa: E402


_ALIASES = repr({f"src.a{n}": f"src.package.a{n}" for n in range(16)})
_REFERENCE = f"""
_COMPAT_ALIASES = {_ALIASES}

def test_compat_alias_is_the_unrenamed_target_module(alias, target):
    module = importlib.import_module(alias)
    assert module is sys.modules[target]
    assert module.__name__ == target
    assert module.__spec__.name == target

def test_all_compat_aliases_concurrent_first_import_is_safe():
    script = "barrier = threading.Barrier(24)"
    for trial in range(20):
        run_trial(script)
"""

_CANDIDATE = f"""
_COMPAT_ALIASES = {_ALIASES}

def test_compat_alias_is_the_unrenamed_target_module(alias_name, target_name):
    importlib.import_module(target_name)
    resolved = importlib.import_module(alias_name)
    assert sys.modules[target_name] is resolved

@pytest.mark.xfail(reason={loop_contract._XFAIL_REASON!r}, strict=False)
def test_all_compat_aliases_concurrent_first_import_is_safe():
    "Keep the same stress recipe."
    script = 'barrier = threading.Barrier(24)'
    for trial in range( 20 ):
        run_trial(script)
"""


@pytest.mark.parametrize(
    ("old", "new", "diagnostic"),
    [
        ("", "", None),
        ("src.package.a0", "src.package.wrong", "pinned 16-entry alias map"),
        (" is resolved", " == resolved", "alias and target object identity"),
        ("range( 20 )", "range(19)", "pinned mixed test body"),
        ("run_trial(script)", "run_trial('unrelated {bad_key}'.format())", "pinned mixed test body"),
        ("strict=False", "strict=True", "xfail reason and strict=False"),
    ],
)
def test_loop62_calibration_contract(tmp_path, monkeypatch, old, new, diagnostic):
    path = tmp_path / "tests" / "unit" / "test_compat_alias_cold_import.py"
    path.parent.mkdir(parents=True)
    path.write_text(_CANDIDATE.replace(old, new))

    def pinned_source(argv, **kwargs):
        assert argv == ["git", "-C", str(tmp_path), "show", loop_contract._REFERENCE]
        return subprocess.CompletedProcess(argv, 0, _REFERENCE, "")

    monkeypatch.setattr(loop_contract.subprocess, "run", pinned_source)
    failure = loop_contract.validate(tmp_path)
    if diagnostic is None:
        assert failure is None
    else:
        assert diagnostic in failure
