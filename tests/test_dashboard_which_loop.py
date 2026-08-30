"""The Kernel-R&D page must not be readable as a statement about the loop.

WHY THIS SUITE EXISTS. On 2026-08-30 the operator read this on ``/kernel``:

    AutoKernel loop / STOPPED / deployment gpu-discovery-champion-v37 ·
    last lifecycle event 2026-08-28 14:12:42Z (48 h ago) — authoring/build are
    event-silent by design

...while the rebuilt AutoKernel loop was running, 46 iterations in. Every clause
of that sentence was TRUE of the thing it observed — the superseded discovery
controller. It was the *label* that was wrong: a card called "AutoKernel loop"
reporting a controller deployment, next to a second page also called AutoKernel
that observes the actual loop. Nothing on either page acknowledged the other, so
a correct reading of one producer was unreadable as anything but a claim about
the other.

TWO GUARDS, and they fail in opposite directions:

1. ``/kernel`` fetches ``/api/loop`` and states the loop's OWN reading. Four
   freshness states plus an unreachable case, each distinct — because a banner
   that renders nothing when it cannot read the loop puts the page back where it
   started, quietly implying this deployment is all there is.
2. The card's "authoring/build are event-silent by design" excuse is now
   conditional on the server's own ``kernel_live`` watchdog. It was
   unconditional, so it explained away the silence of a producer the hub had
   already declared ``stopped_reporting`` — a verdict the page held in its
   payload and never rendered.

NO NEW DATA PLANE. ``/kernel`` gains one read-only fetch of the other surface's
existing route. It does not import ``loop_status``, re-derive freshness, or
couple its envelope to the loop's — INF-66 P6 rewrites this surface, and one
contract's rewrite must not become another's outage.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

PAGE = REPO / "dashboard/static/kernel.html"
LOOP_PAGE = REPO / "dashboard/static/loop.html"
HARNESS = Path(__file__).resolve().parent / "js" / "render_harness.js"
REGISTRY = REPO / "dashboard/registry.json"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node not available for runtime JS execution")

#: The banner element and the liveness sub-line the operator actually read.
#: kernel.html looks elements up with ``$ = s => document.querySelector(s)``,
#: so the harness keys them by SELECTOR, not by bare id.
BANNER_ID = "which-loop"
BANNER_SEL = "#which-loop"
LIVENESS_SEL = "#cmd-liveness-sub"

#: The sentence that explained away a two-day silence.
EXCUSE = "event-silent by design"


def _strip_comments(text: str) -> str:
    """HTML and JS comments removed, so an assertion about the PAGE is not
    answered by a comment about the page. This is the "key too wide" failure in
    miniature: the rationale for a fix contains the string the fix removes."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


def _page_js() -> str:
    html = PAGE.read_text(encoding="utf-8")
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
    assert blocks, "no inline script blocks found in kernel.html"
    return "\n".join(blocks)


def _kernel_payload() -> dict:
    """The page's own ``/api/kernel`` payload, so the harness's standard render
    pass behaves normally while the driver below exercises the new functions."""
    from dashboard import server as S
    data = S.kernel_payload()
    data.setdefault("_activity", {})["current_state"] = S.autokernel_current_state()
    return data


def _drive(call: str, tmp_path: Path) -> dict:
    """Run kernel.html's JS, then execute one extra call, and report the DOM.

    APPENDED, never prepended: function declarations hoist, so a driver placed
    ahead of the real declarations would be overwritten by them and the test
    would silently exercise nothing.
    """
    driver = (f"\ntry{{ {call} }}catch(e){{ "
              f"document.getElementById('driver-threw').innerHTML='THREW: '+e.message; }}\n")
    (tmp_path / "page.js").write_text(_page_js() + driver, encoding="utf-8")
    (tmp_path / "payload.json").write_text(json.dumps(_kernel_payload()), encoding="utf-8")
    proc = subprocess.run(["node", str(HARNESS), str(tmp_path / "page.js"),
                           str(tmp_path / "payload.json")],
                          capture_output=True, text=True, timeout=60)
    assert proc.stdout.strip(), f"harness produced no output; stderr={proc.stderr[:600]}"
    out = json.loads(proc.stdout)
    assert not out.get("load_error"), out.get("load_error")
    return out


def _banner(call: str, tmp_path: Path) -> str:
    out = _drive(call, tmp_path)
    assert "THREW" not in out["by_id"].get("driver-threw", ""), \
        out["by_id"].get("driver-threw")
    return out["by_id"].get(BANNER_SEL, "")


def loop_payload(*, state: str = "fresh", loop_state: str = "running",
                 age_s: float | None = None) -> dict:
    """A ``/api/loop`` wire payload, shaped exactly as ``loop_status.snapshot``
    emits it. Built here rather than imported so this suite tests the PAGE's
    handling of the wire shape, not the reader's agreement with itself."""
    # The age must AGREE with the state it claims. A "stale" fixture stamped 60s
    # old is internally inconsistent, and a page rendering "stale · 1 min ago"
    # would look like a page bug in a report that is really a fixture bug.
    if age_s is None:
        age_s = 9000.0 if state == "stale" else 60.0
    stamped = (datetime.now(timezone.utc)
               - timedelta(seconds=age_s)).isoformat().replace("+00:00", "Z")
    body = {
        "schema": "epyc.autokernel.loop_status.v1", "generated_at": stamped,
        "state": loop_state, "campaign_id": "ak-loop", "iterations_done": 46,
        "iterations_planned": 60, "measurements_reached": 26,
        "champion_head": "5ad3e36dfb3acc9eda3dd3d5e137dce69a629cdd",
        "anchor_commit": "8fd1b23acf2be83d2916518671a77493a8a3f045",
    }
    empty = state in ("absent", "malformed")
    return {
        "schema": "epyc.autokernel.loop_status.v1",
        "evidence": "/mnt/raid0/llm/autokernel/loop-memory/loop-status.json",
        "store_root": "/mnt/raid0/llm/autokernel/loop-memory",
        "artifact_present": state != "absent",
        "reader_error": ("loop status is not valid JSON: line 1"
                         if state == "malformed" else None),
        "freshness_state": state,
        "age_s": None if empty else age_s,
        "stale_after_s": 1800.0,
        "generated_at": None if empty else stamped,
        "detail": {"fresh": "current",
                   "stale": "last heard from the loop 90.0 min ago",
                   "absent": "never published",
                   "malformed": "unreadable"}[state],
        "absence_means": "the rebuilt AutoKernel loop has never published a status "
                         "in this store root.",
        "loop": None if empty else body,
        "derived": None if empty else {"kept": 1, "negatives": 86},
    }


# --------------------------------------------------------------------------- #
# 1. The banner: /kernel states the LOOP's reading, from the loop's own route
# --------------------------------------------------------------------------- #
class TestWhichLoopBanner:

    def test_a_running_loop_is_named_as_running_on_the_kernel_page(self, tmp_path):
        """The operator's exact complaint, inverted into an assertion."""
        html = _banner(f"renderWhichLoop({json.dumps(loop_payload())})", tmp_path)
        assert "RUNNING" in html
        assert "46" in html, "the loop's iteration count is not on the page"
        assert "/loop" in html, "no route to the surface that owns this reading"
        assert "controller" in html.lower(), \
            "the banner does not say what THIS page observes"

    def test_a_stopped_loop_is_named_as_stopped_and_not_as_absent(self, tmp_path):
        html = _banner(f"renderWhichLoop({json.dumps(loop_payload(state='stale'))})",
                       tmp_path)
        assert "STOPPED REPORTING" in html
        assert "never published" not in html, \
            "a stale loop rendered the absent copy — two states collapsed"

    def test_every_freshness_state_renders_a_DISTINCT_banner(self, tmp_path):
        """The load-bearing assertion. If any two collapse, this page can imply a
        dead loop is merely quiet, or a running loop is gone."""
        seen = {}
        for state in ("fresh", "stale", "absent", "malformed"):
            seen[state] = _banner(
                f"renderWhichLoop({json.dumps(loop_payload(state=state))})", tmp_path)
        seen["unreachable"] = _banner(
            "renderWhichLoopUnreachable('/api/loop responded 503')", tmp_path)
        assert len(set(seen.values())) == 5, \
            f"two banner states produced the same rendering: {sorted(seen)}"
        for state, html in seen.items():
            assert html.strip(), f"the {state} banner rendered NOTHING"

    def test_an_unreachable_loop_route_asserts_nothing_about_the_loop(self, tmp_path):
        """Rendering "no loop" over a hub-side fetch failure would be the original
        defect with the blame swapped."""
        html = _banner("renderWhichLoopUnreachable('network down')", tmp_path)
        assert "says nothing about whether the loop is running" in html
        assert "STOPPED" not in html
        assert "never published" not in html

    def test_an_unknown_freshness_state_is_unknown_not_fine(self, tmp_path):
        """A state this page has never heard of must not fall through to the
        running rendering — fail-open here is how a new producer state would
        silently read as healthy."""
        payload = loop_payload()
        payload["freshness_state"] = "quiescent"
        html = _banner(f"renderWhichLoop({json.dumps(payload)})", tmp_path)
        assert "unknown" in html.lower()
        assert "RUNNING" not in html

    def test_the_banner_markup_is_in_the_page_before_any_fetch(self, tmp_path):
        """Its first paint must already say it is reading, not be blank: a banner
        that only exists after a successful fetch is absent exactly when the
        fetch fails."""
        html = PAGE.read_text(encoding="utf-8")
        assert f'id="{BANNER_ID}"' in html
        head = html.split(f'id="{BANNER_ID}"')[0]
        assert "<main>" in head, "the banner is not inside <main>"
        assert 'id="observation"' not in head, \
            "the banner is not the first thing in <main>"

    def test_the_banner_is_refreshed_on_a_timer_not_only_at_load(self, tmp_path):
        """A once-only read would freeze the loop's state at page load and then
        be wrong for as long as the tab stays open."""
        src = _page_js()
        assert re.search(r"setInterval\(\s*loadWhichLoop", src), \
            "the which-loop banner is never re-read"


# --------------------------------------------------------------------------- #
# 2. The excuse: conditional on the hub's own watchdog
# --------------------------------------------------------------------------- #
def live_payload(*, watchdog: str, event_ts: str = "2026-08-28T14:12:42Z") -> dict:
    return {
        "deployment": "gpu-discovery-champion-v37",
        "active": False,
        "autokernel_log": [{"ts": event_ts, "line": "x"}],
        "activity": {"status": "stopped"},
        "_freshness": {"watchdog": {"state": watchdog,
                                    "reason": "the producer behind it has stopped."}},
    }


class TestSilenceIsNotExcused:

    def test_a_stopped_producer_no_longer_has_its_silence_explained_away(self, tmp_path):
        out = _drive(f"renderCommandBand({json.dumps(live_payload(watchdog='stopped_reporting'))})",
                     tmp_path)
        sub = out["by_id"].get(LIVENESS_SEL, "")
        assert sub, "the liveness card rendered nothing"
        assert EXCUSE not in sub, \
            "a producer the hub calls stopped_reporting still has its silence excused"
        assert "stopped_reporting" in sub, \
            "the hub's own watchdog verdict is still not shown on the page"

    def test_a_LIVE_producer_keeps_the_excuse(self, tmp_path):
        """The mutation half. If the excuse were simply deleted, the test above
        would pass while the page lost a true and useful statement: authoring and
        a single-threaded build really do span tens of minutes of silence."""
        out = _drive(f"renderCommandBand({json.dumps(live_payload(watchdog='ok'))})",
                     tmp_path)
        sub = out["by_id"].get(LIVENESS_SEL, "")
        assert EXCUSE in sub, \
            "a healthy producer lost the by-design silence explanation"
        assert "stopped_reporting" not in sub

    def test_the_card_no_longer_calls_itself_the_AutoKernel_loop(self, tmp_path):
        """The label is the defect. `/loop` owns that name now.

        COMMENTS ARE STRIPPED FIRST. The block carries a source comment naming
        the old label, so a raw substring check would fail on the explanation of
        the fix rather than on the fix — a key too wide over its own rationale.
        """
        block = _strip_comments(
            PAGE.read_text(encoding="utf-8")
            .split('id="cmd-liveness"')[1].split("</section>")[0])
        assert "AutoKernel loop" not in block, \
            "the controller card still calls itself the AutoKernel loop"
        assert "/loop" in block, "the card does not point at the surface that is"


# --------------------------------------------------------------------------- #
# 3. Both directions, and the nav
# --------------------------------------------------------------------------- #
class TestTheTwoSurfacesAcknowledgeEachOther:

    def test_the_loop_page_points_back_at_the_controller_page(self):
        html = LOOP_PAGE.read_text(encoding="utf-8")
        assert 'href="/kernel"' in html, \
            "the live surface does not say where the campaign evidence went"
        assert "gpu-discovery-champion-v37" in html

    def test_the_loop_page_does_not_take_a_data_dependency_on_kernel(self):
        """A cross-LINK, not a cross-fetch. `/loop` must keep working while the
        surface INF-66 P6 rewrites is broken."""
        # STRUCTURAL, not a substring sweep: the page's own comment explains that
        # it does NOT read /api/kernel, and a bare `"/api/kernel" not in html`
        # fails on that sentence. What must be absent is a FETCH of it.
        js = "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                                  LOOP_PAGE.read_text(encoding="utf-8"), re.S))
        assert "/api/kernel" not in _strip_comments(js), \
            "/loop now fetches the surface it exists to be independent of"

    def test_the_nav_says_which_of_the_two_is_live_without_clicking(self):
        rows = {e["id"]: e for e in
                json.loads(REGISTRY.read_text(encoding="utf-8"))["dashboards"]}
        live, ctrl = rows["autokernel-loop"], rows["kernel"]
        assert live.get("chip") == "live"
        assert ctrl.get("chip") and ctrl["chip"] != "live"
        assert live["title"] != ctrl["title"]
        assert "superseded" in ctrl["blurb"].lower()
        assert "/loop" in ctrl["blurb"], \
            "the controller row does not route a reader to the live surface"

    def test_the_live_surface_is_listed_before_the_superseded_one(self):
        ids = [e["id"] for e in
               json.loads(REGISTRY.read_text(encoding="utf-8"))["dashboards"]]
        assert ids.index("autokernel-loop") < ids.index("kernel")

    def test_the_chip_comes_from_the_registry_not_a_hardcoded_id(self, tmp_path):
        """The nav had one chip for one hardcoded id. A second meaning needed a
        second hardcode, or data.

        EXECUTED, not grepped. `"e.chip" in nav.js` would pass over a nav.js
        that only mentions the field in a comment — the exact "asserts a string
        appears in source rather than that the code runs" failure this repo
        keeps being bitten by. This runs nav.js against the hub's OWN inlined
        registry (via `nav_asset`, so a field the server strips on the way out
        is caught too) and reads the chips back off the anchors it built.
        """
        from dashboard import server as S
        driver = r"""
const chips = {};
function anchor() {
  return { className: '', href: '', title: '', textContent: '',
           setAttribute() {},
           appendChild(child) { chips[this.textContent] = child.textContent; } };
}
const host = { id: '', textContent: '', classList: { add() {} },
               appendChild() {} };
global.window = {};
global.document = {
  getElementById: (id) => (id === 'epyc-nav' ? host : null),
  createElement: (tag) => (tag === 'a' ? anchor()
                          : { id: '', className: '', textContent: '',
                              appendChild() {} }),
  createTextNode: (t) => ({ t }),
  createDocumentFragment: () => ({ appendChild() {} }),
  head: { appendChild() {} }, documentElement: { appendChild() {} },
  body: { insertBefore() {}, firstChild: null },
  readyState: 'complete', addEventListener() {},
};
global.location = { port: '8100', protocol: 'http:', hostname: 'h',
                    pathname: '/kernel' };
"""
        script = (driver + "\n" + S.nav_asset().decode("utf-8")
                  + "\nconsole.log(JSON.stringify(chips));\n")
        (tmp_path / "nav_drive.js").write_text(script, encoding="utf-8")
        proc = subprocess.run(["node", str(tmp_path / "nav_drive.js")],
                              capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr[-800:]
        chips = json.loads(proc.stdout.splitlines()[-1])
        assert chips.get("AutoKernel") == "live", \
            f"the live AutoKernel surface renders no 'live' chip: {chips}"
        assert chips.get("Kernel-R&D") == "controller", \
            f"the controller surface renders no distinguishing chip: {chips}"
        assert chips.get("Legacy (:8000)") == "legacy", \
            f"moving the legacy chip into the registry dropped it: {chips}"
        assert "Handoffs" not in chips, \
            "a chipless row grew a chip — the fallback is too broad"
