"""Regression guard for audit B6 / DRIFT-1: the safety_gate module-identity fix.

Two historical hazards are locked down here:

  (i)  ``src/safety_gate.py`` was renamed to ``src/diversity_gate.py`` so it no
       longer collides, by bare name, with ``scripts/autopilot/safety_gate.py``
       (the module the autopilot actually imports as ``safety_gate``).

  (ii) ``scripts/autopilot/species/structural_lab.py`` used to run
       ``sys.path.insert(0, str(ORCH_ROOT / "src"))``, putting ``src/`` AHEAD of
       ``scripts/autopilot`` on ``sys.path``. Combined with (i), a bare
       ``import safety_gate`` anywhere in the process could bind the wrong module.
       The fix inserts the repo ROOT and imports src modules via the ``src.``
       package prefix, so ``import safety_gate`` keeps resolving the autopilot
       module.
"""

from __future__ import annotations

from importlib.machinery import PathFinder
from pathlib import Path

ORCH_ROOT = Path(__file__).resolve().parents[2]


def test_src_safety_gate_renamed_to_diversity_gate() -> None:
    # (i) The colliding module name must be gone; the diversity gate lives on
    # under its new, unambiguous name.
    assert not (ORCH_ROOT / "src" / "safety_gate.py").exists()
    assert (ORCH_ROOT / "src" / "diversity_gate.py").exists()


def test_bare_import_safety_gate_resolves_autopilot_module() -> None:
    # (ii) Simulate the sys.path structural_lab now produces: repo ROOT ahead of
    # scripts/autopilot. Even with <root>/src on the search path (belt & braces),
    # a bare `import safety_gate` must resolve scripts/autopilot/safety_gate.py.
    # PathFinder.find_spec searches only the given path and does not execute the
    # module (keeps this robust while another agent edits safety_gate.py).
    search_path = [
        str(ORCH_ROOT),
        str(ORCH_ROOT / "src"),
        str(ORCH_ROOT / "scripts" / "autopilot"),
    ]
    spec = PathFinder.find_spec("safety_gate", search_path)
    assert spec is not None and spec.origin is not None
    assert Path(spec.origin) == ORCH_ROOT / "scripts" / "autopilot" / "safety_gate.py"


def test_structural_lab_never_inserts_src_ahead_of_path() -> None:
    # (ii) Static guard on the specific regression: structural_lab must not put
    # <root>/src at sys.path position 0 again.
    src_txt = (
        ORCH_ROOT / "scripts" / "autopilot" / "species" / "structural_lab.py"
    ).read_text(encoding="utf-8")
    assert 'sys.path.insert(0, str(ORCH_ROOT / "src"))' not in src_txt
