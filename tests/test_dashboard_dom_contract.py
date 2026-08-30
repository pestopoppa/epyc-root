"""Every element the page's renderers look up must exist in the markup.

WHY (2026-08-28). Merging the aggregate and champion cards deleted
`id="cmd-aggregate-value"` while `renderCommandBand` still did
`$("#cmd-aggregate-value").textContent = ...`. That is a null dereference, so the
FIRST renderer to touch it threw and took the entire live render down with it: the
page showed "connecting…" in every card and the message

    live endpoint unavailable: can't access property "textContent", aggValue is null

`node --check` passed the whole time -- it validates syntax, not DOM lookups. Nothing
in the suite modelled the page's structure, so an id could be deleted out from under
its reader with no test noticing.

This closes that: extract every id the script looks up and assert the markup
defines it. Cheap, and it fails on exactly the mistake that was made.

RETARGETED 2026-08-30. The page this was written against, `kernel.html`, was
deleted when the two AutoKernel surfaces merged and `/kernel` became a redirect to
`/loop`. The DEFECT CLASS did not go anywhere -- `loop.html` grew a whole new
section the same day -- so the guard moved to the surviving page rather than being
retired with the old one.

TWO LOOKUP IDIOMS, and both are matched on purpose. `kernel.html` used a
`$ = s => document.querySelector(s)` helper and so was scanned for `$("#id")`;
`loop.html` calls `document.getElementById("id")` directly. A guard that knew only
the first spelling would have found ZERO lookups on this page and passed --
vacuously, over the exact structure it exists to check.
`test_the_scan_finds_the_lookups_it_claims_to_find` below is what stops that being
silent again.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

PAGE = Path(__file__).resolve().parents[1] / "dashboard/static/loop.html"

#: Ids created at runtime rather than declared in markup would belong here. Keep it
#: empty unless one genuinely exists -- an exemption list is how this class of test
#: quietly stops testing.
RUNTIME_CREATED: set[str] = set()

#: `document.getElementById("foo")` and the `$("#foo")` / `$("#foo", root)` helper
#: shape. Both, because the two pages this guard has covered used different ones and
#: a scan that matches only the absent idiom reports "no lookups" as "no problems".
_GET_BY_ID = re.compile(r'getElementById\(\s*"([A-Za-z0-9_-]+)"')
_DOLLAR = re.compile(r'\$\(\s*"#([A-Za-z0-9_-]+)"')


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _script(html: str) -> str:
    return "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S))


def _looked_up(script: str) -> set[str]:
    return set(_GET_BY_ID.findall(script)) | set(_DOLLAR.findall(script))


class DomContractTests(unittest.TestCase):

    def test_the_scan_finds_the_lookups_it_claims_to_find(self):
        """NON-VACUITY. An empty ``looked_up`` set makes the check below pass over
        anything at all, which is precisely how a retargeted guard dies quietly."""
        looked_up = _looked_up(_script(_page()))
        self.assertGreaterEqual(
            len(looked_up), 10,
            "the id scan found almost nothing on this page -- either the page "
            "changed its lookup idiom or the regexes no longer match it, and either "
            f"way the contract below is vacuous. found: {sorted(looked_up)}")
        # A specific id from the section added in the merge, so the scan is pinned
        # to real content rather than to a count it could reach with stale matches.
        self.assertIn("opgate", looked_up)

    def test_every_looked_up_id_exists_in_the_markup(self):
        html = _page()
        looked_up = _looked_up(_script(html))
        declared = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
        missing = sorted(looked_up - declared - RUNTIME_CREATED)
        self.assertEqual(
            missing, [],
            "these ids are read by the script but defined nowhere in the markup, so "
            "the first renderer to touch one throws and kills the whole render: "
            f"{missing}")

    def test_the_second_producers_card_is_declared_and_read(self):
        """The operator-gated champion evidence moved onto this page in the merge.

        Its host, its badge and the badge's text node are three separate elements
        and the renderer writes to all three; a card that renders its number into an
        element that does not exist is the null deref above, with the program's
        largest figure attached to it.
        """
        html = _page()
        script = _script(html)
        for element in ("opgate", "opgate-badge", "opgate-badgetxt"):
            self.assertIn(f'id="{element}"', html, element)
            self.assertIn(element, script, f"{element} is declared but never read")


if __name__ == "__main__":
    unittest.main()
