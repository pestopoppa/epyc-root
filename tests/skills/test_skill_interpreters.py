"""OBS-12: a skill's documented command must name an interpreter that has its imports.

kb-search once told every session to run bare ``python3``, which lacks numpy; the
project-wiki and research-intake scripts need PyYAML, which the system ``python3``
only has when ``~/.local`` survives a devcontainer rebuild (OBS-11 shows it may not).
These guards tie the two together so a new instance fails here, not in a session.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
VENV = "/workspace/repos/epyc-orchestrator/.venv/bin/python"

# Scripts that must refuse at startup, before doing any work, when PyYAML is missing.
CLI_GUARDED = [
    "project-wiki/scripts/lint_wiki.py",
    "project-wiki/scripts/query_wiki.py",
    "research-intake/scripts/seed_index.py",
    "research-intake/scripts/validate_intake.py",
    "research-intake/scripts/backfill_dispositions.py",
    "research-intake/scripts/resolve_intake_id.py",
]
# Scripts with an optional yaml import that must still refuse rather than ignore wiki.yaml.
CONFIG_GUARDED = [
    "project-wiki/scripts/compile_sources.py",
    "project-wiki/scripts/wiki_writer_review.py",
]


def _third_party_imports(path: Path, _seen: set[Path] | None = None) -> set[str]:
    """Every non-stdlib import, lazy ones included, following sibling modules.

    Repo packages (``scripts``, ``src``) are reported as-is: a script that needs them
    is not stdlib-only, so its documented command must name the venv.
    """
    seen = _seen if _seen is not None else set()
    seen.add(path)
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    out: set[str] = set()
    for m in mods:
        if m in sys.stdlib_module_names or m == "__future__":
            continue
        sibling = path.parent / f"{m}.py"
        if sibling.is_file():
            if sibling not in seen:
                out |= _third_party_imports(sibling, seen)
            continue
        out.add(m)
    return out


def _skill_scripts() -> list[Path]:
    return sorted(p for p in SKILLS.rglob("*.py") if not p.name.startswith("test_"))


def test_guard_lists_cover_every_third_party_importer():
    importers = {
        str(p.relative_to(SKILLS)) for p in _skill_scripts() if _third_party_imports(p)
    }
    assert importers == set(CLI_GUARDED) | set(CONFIG_GUARDED)


@pytest.mark.parametrize("rel", CLI_GUARDED + CONFIG_GUARDED)
def test_third_party_importer_names_the_venv(rel):
    text = (SKILLS / rel).read_text(encoding="utf-8")
    assert VENV in text
    assert "pip install pyyaml" not in text


_BARE_CALL = re.compile(r"(?<![\w/.])python3?\s+(?:-\S+\s+)*(\S+\.py)\b")


def test_documented_bare_python_calls_target_stdlib_only_scripts():
    offenders = []
    for doc in sorted(SKILLS.rglob("*.md")):
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for match in _BARE_CALL.finditer(line):
                target = Path(match.group(1).strip("`'\""))
                candidates = [ROOT / target, doc.parent / target]
                script = next((c for c in candidates if c.is_file()), None)
                if script is None:
                    continue
                extra = _third_party_imports(script)
                if extra:
                    offenders.append(f"{doc.relative_to(ROOT)}:{lineno} {target} needs {sorted(extra)}")
    assert offenders == []


def _yamlless_python() -> str | None:
    """The system interpreter with user site-packages disabled, if it truly lacks yaml."""
    exe = shutil.which("python3", path="/usr/bin:/bin")
    if exe is None:
        return None
    probe = subprocess.run([exe, "-s", "-c", "import yaml"], capture_output=True)
    return exe if probe.returncode != 0 else None


@pytest.mark.parametrize("rel", CLI_GUARDED)
def test_cli_refuses_cleanly_without_yaml(rel):
    exe = _yamlless_python()
    if exe is None:
        pytest.skip("no yaml-less system interpreter available")
    proc = subprocess.run(
        [exe, "-s", str(SKILLS / rel), "--help"],
        capture_output=True, text=True, cwd=ROOT, timeout=60,
    )
    assert proc.returncode == 1
    assert VENV in proc.stderr
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize("rel", CONFIG_GUARDED)
def test_config_loader_refuses_instead_of_ignoring_wiki_yaml(rel):
    exe = _yamlless_python()
    if exe is None:
        pytest.skip("no yaml-less system interpreter available")
    loader = "load_config" if rel.endswith("compile_sources.py") else "load_writer_config"
    code = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('m', {str(SKILLS / rel)!r})\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "sys.modules['m'] = m\n"
        "try:\n"
        "    spec.loader.exec_module(m)\n"
        f"    m.{loader}()\n"
        "except RuntimeError as exc:\n"
        "    print(exc); sys.exit(7)\n"
    )
    proc = subprocess.run(
        [exe, "-s", "-c", code], capture_output=True, text=True, cwd=ROOT, timeout=60,
        env={"PYTHONPATH": str((SKILLS / rel).parent)},
    )
    assert proc.returncode == 7, proc.stderr
    assert VENV in proc.stdout
