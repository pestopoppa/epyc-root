"""TRIPWIRE: `KnowledgeDistiller` has zero non-test callers.

Fourth of the dead-machinery cluster (`sub_decision`, `binding_routing`,
`mutation_ledger`, this). Same class of defect: fully-built, fully-tested
machinery that nothing in production ever constructs.

RE-DERIVED 2026-08-12 (`mainD`) against the audit row in
`handoffs/active/autopilot-continuous-optimization.md` ("AP-29 gate before
wiring — narrowed"), which says `KnowledgeDistiller` "has zero non-test
callers (uninstantiated, not flag-off)". The row holds. Every non-test hit
for `KnowledgeDistiller` / `knowledge_distiller` in the tracked tree is one
of: a docstring/comment mention (`strategy_store.py:21`,
`context_budget.py:115`), a bare file-path string used for staleness
checking (`scripts/autopilot/phase_status.py:85` — `AUTOPILOT_RUNTIME_SOURCE_PATHS`,
which only stats the file's mtime, never imports it), or JSON review-queue
artifacts that quote the path as text. None constructs the class.

THE NAME TRAP THAT ALMOST HID THIS. `scripts/autopilot/actions.py` wires an
autopilot action literally named `distill_knowledge`, which calls
`ctx.evo.distill(...)` — but `ctx.evo` is `EvolutionManager`
(`scripts/autopilot/species/evolution_manager.py`), a **separate class**
implementing its own from-scratch LLM-driven consolidation. It does not
import, construct, or otherwise touch `orchestration/repl_memory/
knowledge_distiller.py`. The module's own docstring claims "Triggered every
N=25 trials by the autopilot main loop" — that claim describes
`EvolutionManager.distill`, not this module; nothing in `autopilot.py`
references `knowledge_distiller` or `KnowledgeDistiller` at all. A grep for
"distill" alone would have wrongly closed this row against the wrong class.

WHAT THIS IS. A tripwire on a known gap, not a behaviour test. It PASSES
while `KnowledgeDistiller` is unreached and FAILS the moment production code
constructs one, forcing whoever wires it to also confirm the AP-29
episodic-only control-arm precondition (same audit row) rather than landing
a silent no-op caller.
"""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_ROOTS = ("src", "scripts", "orchestration")

_FINISH_THE_CHAIN = (
    "\n\nConstructing KnowledgeDistiller is not the feature. Before closing the AP-29 "
    "audit row: (1) confirm this is paired with the episodic-only control arm "
    "(retain+delete, abstraction disabled) that the distiller must beat per the row's "
    "arXiv 2605.12978 caution; (2) confirm the caller actually invokes .distill() on a "
    "real cycle, not just __init__; (3) close the row in "
    "handoffs/active/autopilot-continuous-optimization.md and delete this file."
)


def _grep(pattern: str) -> list[str]:
    out = subprocess.run(["git", "grep", "-n", "-F", pattern, "--", *_ROOTS],
                         cwd=REPO, capture_output=True, text=True, check=False).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def test_knowledge_distiller_is_still_never_constructed() -> None:
    """CONTENT-ANCHORED via AST, not a literal-string grep.

    A `KnowledgeDistiller(...)` appearing inside a docstring, comment, or string
    literal is not a construction — same lesson `test_binding_router_tripwire.py`
    already paid for. This parses every tracked hit for the class name and keeps
    only real `ast.Call` nodes whose callee resolves to `KnowledgeDistiller`,
    excluding the test suite itself (which legitimately constructs it to test it).
    """
    real: list[str] = []
    for hit in _grep("KnowledgeDistiller("):
        path = hit.split(":", 1)[0]
        if path.startswith("tests/"):
            continue
        if path == "orchestration/repl_memory/knowledge_distiller.py":
            continue  # the class's own body (methods returning/typing itself, etc.)
        src = (REPO / path).read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:                                   # pragma: no cover
            real.append(hit + "  (unparseable — check by hand)")
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "KnowledgeDistiller"):
                real.append(f"{path}:{node.lineno}")
    assert real == [], (
        "A KnowledgeDistiller is now CONSTRUCTED in non-test code (not merely named "
        "in a docstring, comment, or path string):\n  " + "\n  ".join(real)
        + _FINISH_THE_CHAIN)


def test_knowledge_distiller_module_still_exists_to_be_wired() -> None:
    """Guards the other resolution: silent deletion is also undocumented if the
    audit row still describes the module as pending."""
    assert (REPO / "orchestration/repl_memory/knowledge_distiller.py").exists(), (
        "orchestration/repl_memory/knowledge_distiller.py was deleted. That may be "
        "the right call — AP-29 gate-before-wiring may have been resolved by "
        "abandoning the distiller — but it is a decision, and the audit row should "
        "say so rather than pointing at a file that no longer exists.")
