"""Portable subprocess checks for the stack-change scratch and preflight wrappers."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".claude/skills/stack-change/scripts"
ORCH_SOURCES = (
    "orchestration/stack_topology.yaml",
    "orchestration/launch_manifest.yaml",
    "scripts/server/stack_numa.py",
    "src/registry/stack_priors.py",
    "scripts/server/stack_commands.py",
    "scripts/server/orchestrator_stack.py",
    "scripts/server/stack_manifest.py",
    "scripts/voice/check_speech_layout.py",
    "scripts/voice/speech_layouts.yaml",
    "scripts/voice/nprocs_shim.c",
    "scripts/voice/run_wav_harness.py",
    "scripts/voice/build_nprocs_shim.sh",
    "src/config/models.py",
    "src/roles.py",
    "stack_templates/default.yaml",
)
RESEARCH_SOURCE = "orchestration/model_registry.yaml"


class StackChangeSkillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="stack-change-skill-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.orch = self.work / "orch"
        self.research = self.work / "research"

    def run_script(self, name: str, *args: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPTS / name), *args],
            env={**os.environ, "ORCH": str(self.orch), "RESEARCH": str(self.research), **extra_env},
            capture_output=True,
            text=True,
            check=False,
        )

    def write_pipeline(self, code: str) -> None:
        script = self.orch / "scripts/registry/stack_change_pipeline.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(code)

    def test_scratch_copies_all_declared_sources_from_fixture_repos(self) -> None:
        originals = [(self.orch, name) for name in ORCH_SOURCES]
        originals.append((self.research, RESEARCH_SOURCE))
        for repo, name in originals:
            source = repo / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(f"fixture:{repo.name}:{name}\n".encode())

        package = self.work / "package"
        result = self.run_script("scratch.sh", str(package))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(ORCH_SOURCES), 15)
        for repo, name in originals:
            kind = "orchestrator" if repo == self.orch else "research"
            self.assertEqual((package / kind / name).read_bytes(), (repo / name).read_bytes())
        self.assertIn('"schema": "epyc.stack_change_scratch.v1"', (package / "PROVENANCE.json").read_text())

    def test_preflight_classifies_recognized_failure_and_routes_checkout(self) -> None:
        argv = self.work / "argv.txt"
        self.write_pipeline(
            "import os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['STACK_CHANGE_ARGV']).write_text('\\n'.join(sys.argv[1:]))\n"
            "print('error: declaration parity in fixture')\n"
            "sys.exit(1)\n"
        )
        report = self.work / "classified.txt"
        result = self.run_script("preflight.sh", str(report), PYTHON=sys.executable, STACK_CHANGE_ARGV=str(argv))
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertEqual(argv.read_text().splitlines(), ["check", "--repo-root", str(self.orch), "--numa-mode", "both"])
        self.assertIn("fixable-by-transform (1)", report.read_text())

    def test_preflight_refuses_traceback_only_and_retains_raw(self) -> None:
        self.write_pipeline("raise RuntimeError('fixture import failed')\n")
        report = self.work / "traceback.txt"
        result = self.run_script("preflight.sh", str(report), PYTHON=sys.executable)
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)
        self.assertIn("unclassified pipeline failure (exit 1)", report.read_text())
        self.assertIn("needs-operator (1)", report.read_text())
        self.assertIn("RuntimeError: fixture import failed", Path(str(report) + ".raw").read_text())

    def test_preflight_clean_exit_is_clean(self) -> None:
        self.write_pipeline("print('summary: ok')\n")
        report = self.work / "clean.txt"
        result = self.run_script("preflight.sh", str(report), PYTHON=sys.executable)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 violation(s)", report.read_text())
        self.assertFalse(Path(str(report) + ".raw").exists())

    def test_preflight_refuses_incomplete_checkout(self) -> None:
        report = self.work / "missing.txt"
        result = self.run_script("preflight.sh", str(report), PYTHON=sys.executable)
        self.assertEqual(result.returncode, 2)
        self.assertIn("complete orchestrator checkout missing", result.stderr)
        self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
