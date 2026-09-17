"""RTG-47 data plane — provenance stays visible on the machine page (2026-09-17).

Two producer-side facts now reach ``dashboard/static/machine.html``:

* a completed tap request may carry ``prompt_tokens`` with
  ``prompt_tokens_source == "server_terminal"`` (llama-server's own terminal
  count, recorded by the tap writer) — the ONLY form the page may render as
  ``↑ N tok``; anything else stays a character count labelled ``c``;
* an ``expected-stack-server`` node may carry ``substrate`` with
  ``substrate_source == "manifest"`` (declared, no process exists) — the chip
  must say *declared* and the title must name the declaration, so a declared
  substrate never reads as an observed one.

The view plane owns the rendering, so the guard lives here (plane rule,
``dashboard/README.md``). Two layers:

* contract strings — pure Python, always runs;
* ``progressBits`` executed under ``node`` with fixtures, skipped only when
  node is missing (the parse guard in ``test_dashboard_static_js`` is the
  always-on backstop).

Run: ``python3 -m unittest tests.test_dashboard_machine_provenance``
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_PAGE = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "machine.html"


def _extract_function(src: str, name: str) -> str:
    """Return the full text of top-level ``function <name>(...) { ... }``."""
    m = re.search(rf"^function {re.escape(name)}\(", src, re.MULTILINE)
    if not m:
        raise AssertionError(f"function {name} not found in machine.html")
    i = src.index("{", m.start())
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start(): j + 1]
    raise AssertionError(f"unbalanced braces in {name}")


def _extract_line(src: str, prefix: str) -> str:
    for line in src.splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"no top-level line starting with {prefix!r}")


class MachinePageProvenanceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.src = _PAGE.read_text(encoding="utf-8")

    def test_measured_prompt_tokens_are_gated_on_server_terminal_source(self) -> None:
        # The page must read the count ONLY under its measured provenance tag.
        self.assertIn('String(r.prompt_tokens_source || "") === "server_terminal"', self.src)
        self.assertIn("MEASURED (server terminal count)", self.src)
        # …and must still say when the prompt figure is only an estimate.
        self.assertIn("CHARACTER estimate", self.src)
        # The chars fallback line is unchanged: unmeasured prompts render in "c".
        self.assertIn('bits.push("prompt " + fmtCount(pl) + "c")', self.src)

    def test_manifest_declared_substrate_is_marked_declared(self) -> None:
        self.assertIn('String(n.substrate_source || "") === "manifest"', self.src)
        self.assertIn("manifest-declared, not observed", self.src)
        self.assertIn("DECLARED by manifest", self.src)
        # The declared chip is distinct markup from the observed chip.
        self.assertIn('<span class="chip gpu">GPU</span>', self.src)
        self.assertIn('GPU <span class="dimtx">declared</span>', self.src)


@unittest.skipUnless(shutil.which("node"), "node not available")
class ProgressBitsUnderNode(unittest.TestCase):
    """Execute the page's own ``progressBits`` on fixtures."""

    @classmethod
    def setUpClass(cls) -> None:
        src = _PAGE.read_text(encoding="utf-8")
        cls.prelude = "\n".join([
            _extract_line(src, "const num ="),
            _extract_function(src, "fmtCount"),
            _extract_function(src, "fmtTok"),
            _extract_line(src, "const ARW_UP ="),
            _extract_function(src, "progressBits"),
        ])

    def _run(self, sp, gen, chunks, terminal) -> dict:
        script = (
            self.prelude
            + "\nconst out = progressBits("
            + ", ".join(json.dumps(v) for v in (sp, gen, chunks, terminal))
            + ");\nprocess.stdout.write(JSON.stringify(out));\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(script)
            path = fh.name
        try:
            res = subprocess.run(["node", path], capture_output=True, text=True, timeout=30, check=False)
        finally:
            Path(path).unlink(missing_ok=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_terminal_measured_count_renders_as_tokens_without_fraction(self) -> None:
        # What normTapReq hands progressBits for a completed request whose only
        # prompt figure is the server's terminal count: total set, no mid-run
        # sample, not ambiguous.
        sp = {"total": 32851, "done": None, "decoded": None,
              "processing": False, "ambiguous": False, "sampledAt": None}
        out = self._run(sp, 334, 334, True)
        self.assertEqual(len(out["up"]), 1)
        self.assertIn("32.9k tok", out["up"][0])
        self.assertNotRegex(out["up"][0], r"\d[\d.k]*/\d")  # terminal: no climbing fraction
        self.assertNotIn("~", out["up"][0])       # measured, not port-level
        self.assertNotIn("(port)", out["up"][0])
        self.assertIn("334 tok", out["down"][0])  # ↓ from final timings

    def test_no_measurement_and_no_sample_renders_no_token_arrow(self) -> None:
        # Nothing measured → no ↑ at all; the caller then falls back to "prompt Nc".
        out = self._run(None, 12, 12, True)
        self.assertEqual(out["up"], [])
        self.assertIn("12 tok", out["down"][0])

    def test_mid_run_sample_keeps_fraction_and_ambiguity(self) -> None:
        sp = {"total": 48726, "done": 48447, "decoded": 0,
              "processing": True, "ambiguous": True, "sampledAt": 1.0}
        out = self._run(sp, None, 0, False)
        self.assertIn("48.4k/48.7k tok", out["up"][0])
        self.assertIn("~", out["up"][0])
        self.assertIn("(port)", out["up"][0])


if __name__ == "__main__":
    unittest.main()
