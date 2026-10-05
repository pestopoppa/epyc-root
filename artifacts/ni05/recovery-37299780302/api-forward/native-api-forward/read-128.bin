"""TRIPWIRE: `binding_routing` is a feature flag that cannot do anything.

Sibling of `test_sub_decision_producer_tripwire.py`, same class: fully-built machinery
with no path that reaches it, and nothing in the suite that would notice.

RE-DERIVED 2026-08-12 (`mainC`) from the audit row, and the row UNDERSTATES it. The
row says `binding_router` is "a parameter nobody passes". It is worse — the feature is
dead at THREE independent layers, any one of which alone would be enough:

  1. NEVER CONSTRUCTED. `BindingRouter()` appears exactly once in the tree, at
     `src/routing_bindings.py:19`, and that line is inside a docstring *Usage* example.
     No production code ever builds one.
  2. NEVER ASSIGNED. `src/api/state.py` declares `binding_router: Any | None = None`
     and nothing anywhere assigns it.
  3. NEVER PASSED. `_classify_and_route` takes `binding_router` and guards its whole
     override block on `if binding_router is not None:`. Its ONE production caller —
     `src/api/routes/chat_routing.py:325` — calls
     `_classify_and_route(prompt, context, has_image=has_image)` and omits it. Every
     other caller in the tree is a test.

So flipping `features().binding_routing` (default False, `src/features.py:144`) changes
nothing: there is no router to construct, nowhere holding one, and no call site that
would pass it. The flag is a fourth layer of inertness on top of the other three.

ANCHOR ROT worth recording, because it is why re-deriving mattered: the row cites
`src/api/chat_routing.py:97/230`, but the file now lives at `src/api/routes/`, and the
function it names — `_classify_and_route_proactive` — **no longer exists at all**. Two
of the row's three anchors were stale; the finding underneath was not.

WHAT THIS IS. A tripwire on a known gap, not a behaviour test. It passes while the
feature is inert and FAILS the moment anyone wires any layer, so whoever does is forced
to wire the REST of the chain rather than landing one layer that silently does nothing —
which is precisely how this got to three dead layers in the first place.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_ROOTS = ("src", "scripts", "orchestration")

_FINISH_THE_CHAIN = (
    "\n\nWiring one layer is not the feature. Before closing the audit row, confirm ALL "
    "of: a BindingRouter is constructed outside a docstring; something assigns "
    "state.binding_router; a production call site passes binding_router= into "
    "_classify_and_route; and features().binding_routing actually changes observed "
    "routing. Then delete this file."
)


def _grep(pattern: str) -> list[str]:
    out = subprocess.run(["git", "grep", "-n", pattern, "--", *_ROOTS],
                         cwd=REPO, capture_output=True, text=True, check=False).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def test_binding_router_is_still_never_constructed() -> None:
    """Layer 1. The only `BindingRouter()` in the tree is a docstring example.

    CONTENT-ANCHORED, not line-anchored (`auditor` review, 2026-08-12). The first
    version excluded the literal string `src/routing_bindings.py:19:`, which
    false-FAILS the moment anyone adds a line above that docstring — never a false
    PASS, so it was safe, but a tripwire that cries wolf on a cosmetic edit is a
    tripwire someone eventually deletes. This parses instead: a construction inside a
    STRING (the module's Usage example) is not a construction.
    """
    import ast

    real = []
    for hit in _grep(r"BindingRouter("):
        path = hit.split(":", 1)[0]
        src = (REPO / path).read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError:                                   # pragma: no cover
            real.append(hit + "  (unparseable — check by hand)")
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "BindingRouter"):
                real.append(f"{path}:{node.lineno}")
    assert real == [], (
        "A BindingRouter is now CONSTRUCTED in code (not merely named in a "
        "docstring):\n  " + "\n  ".join(real) + _FINISH_THE_CHAIN)


def test_binding_router_is_still_never_assigned() -> None:
    """Layer 2. `state.binding_router` is declared and never written."""
    hits = [h for h in _grep(r"binding_router\s*=")
            if "binding_router: " not in h and "binding_router=None" not in h]
    assert hits == [], (
        "Something now assigns or passes binding_router:\n  " + "\n  ".join(hits)
        + _FINISH_THE_CHAIN)


def test_the_one_production_caller_still_omits_binding_router() -> None:
    """Layer 3, and the most specific: the single live call site drops the argument.

    Pinned by BEHAVIOUR rather than by line number, because this row's own anchors
    rotted — the file moved to `src/api/routes/` and the function the row names was
    deleted. Line numbers are a hint; the call is the identity.
    """
    raw = (REPO / "src/api/routes/chat_routing.py").read_text(encoding="utf-8")
    # Whitespace-normalised so a linter rewrapping the call does not false-FAIL.
    src = " ".join(raw.split())
    assert "_classify_and_route(prompt, context, has_image=has_image)" in src, (
        "The production call site changed shape. Re-read it: if it now passes "
        "binding_router, the feature may finally be live — verify the whole chain."
        + _FINISH_THE_CHAIN)
    assert "if binding_router is not None:" in src, (
        "The guard this tripwire watches is gone. Either the feature was wired or it "
        "was removed; both are resolutions and both need the audit row closed.")
