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

This closes that: extract every `$("#id")` the script performs and assert the markup
defines it. Cheap, and it fails on exactly the mistake that was made.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest

KERNEL = Path("dashboard/static/kernel.html")

#: Ids created at runtime rather than declared in markup would belong here. Keep it
#: empty unless one genuinely exists -- an exemption list is how this class of test
#: quietly stops testing.
RUNTIME_CREATED: set[str] = set()


def _page() -> str:
    return KERNEL.read_text()


def _script(html: str) -> str:
    return "\n".join(re.findall(r"<script>(.*?)</script>", html, re.S))


class DomContractTests(unittest.TestCase):

    def test_every_looked_up_id_exists_in_the_markup(self):
        html = _page()
        script = _script(html)
        declared = set(re.findall(r'id="([A-Za-z0-9_-]+)"', html))
        # `$("#foo")` and `$("#foo", root)` — the page's own selector helper.
        looked_up = set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"', script))
        missing = sorted(looked_up - declared - RUNTIME_CREATED)
        self.assertEqual(
            missing, [],
            "these ids are read by the script but defined nowhere in the markup, so "
            "the first renderer to touch one throws and kills the whole render: "
            f"{missing}")

    def test_the_merged_champion_card_still_has_both_of_its_lines(self):
        """The specific regression: one card, champion value + receipt line."""
        html = _page()
        self.assertEqual(html.count('id="cmd-aggregate"'), 1)
        self.assertEqual(html.count('id="cmd-champion"'), 0,
                         "the duplicate champion card must stay gone")
        for needed in ("cmd-champion-value", "cmd-champion-sub", "cmd-aggregate-sub"):
            self.assertIn(f'id="{needed}"', html, needed)

    def test_no_renderer_writes_to_a_deleted_aggregate_value(self):
        script = _script(_page())
        self.assertNotIn('cmd-aggregate-value', script,
                         "cmd-aggregate-value was removed with the card merge; any "
                         "remaining reader is the null deref that broke the page")


if __name__ == "__main__":
    unittest.main()
