"""PREP: one native pytest case, distinct from 103 descriptive audit controls."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_real_guard_audit_controls_conform():
    assets = Path(os.environ["NI76_ASSETS"]).resolve(strict=True)
    scope = Path(os.environ["NI76_SCOPE"]).resolve(strict=True)
    originals = scope / "originals"
    assert not (originals / "complete.json").exists()
    assert not (originals / "cases.json").exists()
    command = ["/usr/bin/python3", "-I", str(assets / "hosted-controls.py")]
    result = subprocess.run(command, timeout=600, check=False)
    assert result.returncode == 0
    complete = json.loads((originals / "complete.json").read_text())
    cases = json.loads((originals / "cases.json").read_text())
    assert complete["passed"] is True
    assert type(complete["cases"]) is int and complete["cases"] == 103
    assert len(cases) == 103
    assert len({case["label"] for case in cases}) == 103
    assert {'cpu-global-shared-inode', 'cpu-global-build-alias'} <= {case['label'] for case in cases}
    for case in cases:
        assert type(case["exit_code"]) is int
        assert type(case["expected"]) is int
        assert case["exit_code"] == case["expected"]
        if case["denial_no_mutation_required"]:
            assert case["before"] == case["after"]
        assert (originals / (case["label"] + ".stdout")).is_file()
        assert (originals / (case["label"] + ".stderr")).is_file()
    assert complete["claim"] == "admission only; no continuous lifetime assurance"
