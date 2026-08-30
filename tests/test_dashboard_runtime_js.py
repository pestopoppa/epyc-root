"""RUNTIME check of the Kernel R&D page's JS — not a syntax check.

KRD-AUDIT-20260812-REFRESH (`mainC`, for `inference`). The operator asked for
"live :8100 rendering, including runtime JS rather than syntax alone". Every existing
guard on this page is structural: `test_dashboard_static_js.py` parses and pattern-
matches. Nothing EXECUTED the render path, so a payload-shaped runtime fault —
reading `.length` off a null section, a mis-keyed lookup — would ship green and only
appear as a blank panel in a browser.

That is the incident-8 shape one layer up: the page draws nothing, and nothing in the
test suite says why.

WHAT THIS DOES. Loads `dashboard/static/loop.html`, extracts its script blocks, and
EXECUTES them under node against the payload the hub actually serves
(`server.loop_payload()`), with minimal DOM stubs, asserting no render function
throws and that BOTH producers' content reaches rendered output.

RETARGETED 2026-08-30. This ran against `kernel.html` until the two AutoKernel
surfaces merged; that page was deleted and `/kernel` became a 301 to `/loop`. The
guard follows the surviving page rather than dying with the retired one — and it is
now more load-bearing, not less, because `/loop` renders TWO producers and a fault
in either renderer would blank a card that carries the program's largest figure.

THE PAYLOAD IS THE SERVER'S OWN, not a fixture. `loop_payload()` reads the live
`loop-status.json` and the live `operator_gate_bundle.json` through the same readers
the browser gets. A fixture here would let the page and the test agree with each
other while both disagreed with the producer — the defect that left this surface's
GPU panel dark while 41 tests passed over it.

DELIBERATELY NOT jsdom: it is not installed, and requiring it would make this test
skip forever — a guard that never runs is the runner-blindness face. The stubs are
enough because the render path builds HTML strings and assigns `innerHTML`.

KNOWN LIMIT, stated rather than hidden: stubs are not a browser. CSS, layout, event
wiring and anything touching real DOM geometry are out of scope. This proves the
render functions execute and emit the expected content, not that the page looks right.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "dashboard/static/loop.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available for runtime JS execution")


def _payload() -> dict:
    """The real `/api/loop` body, built by the server itself."""
    import sys
    sys.path.insert(0, str(REPO))
    from dashboard import server as S
    return S.loop_payload()


def _run(page_js: str, payload: dict, tmp_path: Path,
         names: list[str] | None = None) -> dict:
    (tmp_path / "page.js").write_text(page_js, encoding="utf-8")
    (tmp_path / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(["node", str(HARNESS), str(tmp_path / "page.js"),
                           str(tmp_path / "payload.json"), *(names or [])],
                          capture_output=True, text=True, timeout=60)
    assert proc.stdout.strip(), f"harness produced no output; stderr={proc.stderr[:400]}"
    return json.loads(proc.stdout)


def _page_js() -> str:
    html = PAGE.read_text(encoding="utf-8")
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    assert blocks, "no script blocks found in loop.html"
    return "\n".join(blocks)


def test_no_render_function_throws_on_a_real_payload(tmp_path: Path) -> None:
    result = _run(_page_js(), _payload(), tmp_path, ["render"])
    assert result["threw"] == [], f"render functions threw: {result['threw']}"
    assert result["ran"] == 1, f"{result['ran']} render functions executed"


def test_both_producers_reach_rendered_output(tmp_path: Path) -> None:
    """Executing without throwing is not the same as rendering something.

    Two producers, two assertions. Checking only the loop would pass over a
    champion card that never drew — which is the shape of every defect this
    surface has had: a panel dark behind a green page.
    """
    result = _run(_page_js(), _payload(), tmp_path, ["render"])
    by_id = result["by_id"]
    assert result["rendered_chars"] > 500, "render produced almost no output"

    # The loop's own half.
    assert by_id.get("tiles"), "the loop progress tiles rendered nothing"
    assert by_id.get("disp"), "the disposition list rendered nothing"
    assert by_id.get("ident"), "the identity block rendered nothing"

    # The second producer's half, moved here from the retired page.
    opgate = by_id.get("opgate") or ""
    assert opgate, "the operator-gated champion card rendered nothing at all"
    assert "operator-gated" in opgate.lower(), (
        "the champion card rendered without its authority label, which is the "
        "one thing that stops the figure being read as a promotion claim")
    # Whatever the bundle's state, the card must say WHICH state — never draw a
    # confident blank.
    assert any(word in opgate for word in
               ("%", "ABSENT", "STALE", "MALFORMED")), opgate[:400]
    assert result["text_by_id"].get("opgate-badgetxt"), (
        "the champion card's freshness badge is empty, so its number carries no "
        "date on the page")


def test_the_retired_surfaces_markup_is_not_reachable_from_this_page(
        tmp_path: Path) -> None:
    """`/kernel`'s renderers must not have been copied along with its one live card.

    The controller-deployment liveness card in particular: its STOPPED was correct,
    which is exactly why it may not sit on the live page.
    """
    js = _page_js()
    for token in ("cmd-aggregate", "which-loop", "renderWhichLoop",
                  "renderCommandBand", "renderProgression", "/api/kernel"):
        assert token not in js, (
            f"{token!r} came across from the retired page; the merge was supposed "
            "to move ONE card, not re-home the surface")


def test_the_harness_CATCHES_a_runtime_fault(tmp_path: Path) -> None:
    """Mutation, as a test: a harness that cannot fail proves nothing.

    Injects a thrower ahead of a render function and asserts it is reported. Without
    this, `threw == []` above is indistinguishable from a harness that never ran.
    """
    # APPENDED, not prepended. Function declarations HOIST, so a thrower placed
    # before the real declaration is silently overridden by it — the mutation
    # vanishes and the test reports a clean run. Found by this test failing when it
    # should have passed, which is the mutation check catching a fault in itself.
    broken = _page_js() + "\nfunction render(d){ throw new Error('injected'); }\n"
    result = _run(broken, _payload(), tmp_path, ["render"])
    assert result["threw"], "the harness did not notice an injected runtime fault"
    assert any("injected" in t for t in result["threw"])
