"""Regression coverage for the health-check interpreter contract."""

from pathlib import Path


HEALTH_CHECK = Path(__file__).resolve().parents[2] / "scripts/session/health_check.sh"


def test_semantic_integrity_uses_repository_python() -> None:
    source = HEALTH_CHECK.read_text()

    assert 'REPO_PYTHON="$ROOT/.venv/bin/python"' in source
    assert '[[ ! -x "$REPO_PYTHON" ]]' in source
    assert (
        'timeout 90s "$REPO_PYTHON" '
        'scripts/maintenance/check_episodic_integrity.py --semantic --require-semantic'
    ) in source
    assert (
        "timeout 90s python3 "
        "scripts/maintenance/check_episodic_integrity.py --semantic --require-semantic"
    ) not in source
