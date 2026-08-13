"""RUNTIME check of the Kernel-R&D page's JS — not a syntax check.

KRD-AUDIT-20260812-REFRESH (`mainC`, for `inference`). The operator asked for
"live :8100 rendering, including runtime JS rather than syntax alone". Every existing
guard on this page is structural: `test_dashboard_static_js.py` parses and pattern-
matches. Nothing EXECUTED the render path, so a payload-shaped runtime fault —
reading `.length` off a null section, a mis-keyed lookup — would ship green and only
appear as a blank panel in a browser.

That is the incident-8 shape one layer up: the page draws nothing, and nothing in the
test suite says why.

WHAT THIS DOES. Loads `dashboard/static/kernel.html`, extracts its script blocks, and
EXECUTES them under node against a real payload with minimal DOM stubs, asserting no
render function throws and that kernel-set content actually reaches rendered output.

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
PAGE = REPO / "dashboard/static/kernel.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available for runtime JS execution")


def _payload() -> dict:
    """A payload with the kernel set populated, built from the server itself."""
    import sys
    sys.path.insert(0, str(REPO / "dashboard"))
    import server as S
    data = S.kernel_payload()
    data.setdefault("_activity", {})["current_state"] = S.autokernel_current_state()
    return data


def _run(page_js: str, payload: dict, tmp_path: Path) -> dict:
    (tmp_path / "page.js").write_text(page_js, encoding="utf-8")
    (tmp_path / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(["node", str(HARNESS), str(tmp_path / "page.js"),
                           str(tmp_path / "payload.json")],
                          capture_output=True, text=True, timeout=60)
    assert proc.stdout.strip(), f"harness produced no output; stderr={proc.stderr[:400]}"
    return json.loads(proc.stdout)


def _page_js() -> str:
    html = PAGE.read_text(encoding="utf-8")
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
    assert blocks, "no script blocks found in kernel.html"
    return "\n".join(blocks)


def test_no_render_function_throws_on_a_real_payload(tmp_path: Path) -> None:
    result = _run(_page_js(), _payload(), tmp_path)
    assert result["threw"] == [], f"render functions threw: {result['threw']}"
    assert result["ran"] >= 3, f"only {result['ran']} render functions executed"


def test_the_kernel_set_actually_reaches_rendered_output(tmp_path: Path) -> None:
    """Executing without throwing is not the same as rendering something."""
    result = _run(_page_js(), _payload(), tmp_path)
    html = result["html"]
    assert result["rendered_chars"] > 500, "render produced almost no output"
    assert ("SET INTACT" in html) or ("SET NOT PROVEN" in html), (
        "the production kernel SET verdict does not appear in rendered output")
    for token in ("stable link", "linkage"):
        assert token in html, f"{token!r} missing from rendered output"
    for token in ("AutoKernel implementation readiness", "SC33 reward-integrity", "C3-C5",
                  "bounded gfx90a prior-art catalogue expansion",
                  "Last completed empirical checkpoint"):
        assert token in html, f"{token!r} missing from rendered output"
    for token in ("Funnel", "+28.9%", "+26.6%", "strict_keep",
                  "Unexplored / ready hypotheses", "promotion claim: <span class=\"ok\">false"):
        assert token in html, f"progression headline token {token!r} missing"


def test_the_harness_CATCHES_a_runtime_fault(tmp_path: Path) -> None:
    """Mutation, as a test: a harness that cannot fail proves nothing.

    Injects a thrower ahead of a render function and asserts it is reported. Without
    this, `threw == []` above is indistinguishable from a harness that never ran.
    """
    # APPENDED, not prepended. Function declarations HOIST, so a thrower placed
    # before the real declaration is silently overridden by it — the mutation
    # vanishes and the test reports a clean run. Found by this test failing when it
    # should have passed, which is the mutation check catching a fault in itself.
    broken = _page_js() + "\nfunction renderCurrentState(d){ throw new Error('injected'); }\n"
    result = _run(broken, _payload(), tmp_path)
    assert result["threw"], "the harness did not notice an injected runtime fault"
    assert any("injected" in t for t in result["threw"])
