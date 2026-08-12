"""Parse guard for the inline JavaScript in ``dashboard/static/*.html``.

WHY THIS EXISTS. On 2026-08-10 the backlog-graph renderer was added to
``handoffs.html`` with a top-level ``const el = ...``. That name was already
taken at line 375 by the page's HTML element helper. A duplicate top-level
``const`` is a **SyntaxError**, and a SyntaxError anywhere in a ``<script>``
block aborts the WHOLE block — so the entire dashboard would have gone dead:
no board, no flow, no timeline, no kanban. It fails silently as a blank page,
not as an error anyone sees.

Nothing in the 157-test dashboard suite parsed this file's JavaScript. Every
existing test exercises ``dashboard/server.py`` and ``dashboard/panels.py`` —
the Python that *serves* the page — so a page that parses to nothing still
passed everything. This closes that gap.

THREE CHECKS, and the split is deliberate:

* ``test_no_duplicate_top_level_declarations`` is pure Python and ALWAYS runs.
  It catches the exact class that bit, and it must not depend on a toolchain
  that may be absent — a guard that quietly skips is a guard nobody can tell is
  dead, which is the same failure mode the panel registry exists to prevent.
* ``test_scripts_parse`` shells out to ``node --check`` for full syntax coverage
  and skips when node is unavailable. It is the broader net, not the load-bearing
  one; the check above is what holds when it is missing.
* ``test_kernel_current_state_renderer_executes`` runs the Kernel-R&D evidence
  renderer against a minimal contract. Parsing cannot catch a free identifier
  that throws only when a production-kernel-set card is rendered.

Run: ``python3 -m unittest tests.test_dashboard_static_js``
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_STATIC = Path(__file__).resolve().parents[1] / "dashboard" / "static"

#: Inline blocks only. ``<script src=...>`` has no body to parse here.
_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)

#: A declaration at column 0 inside a script block is top-level, and two of the
#: same name in one scope is a SyntaxError. Indented declarations are inside some
#: function/block and are legitimately allowed to shadow.
_TOP_DECL = re.compile(r"^(?:const|let|class)\s+([A-Za-z_$][\w$]*)", re.M)

#: `function foo()` and `async function foo()` at column 0. Redeclaring a
#: *function* is legal JS (the later one wins), so this is reported separately as
#: a shadowing smell rather than a hard failure.
_TOP_FUNC = re.compile(r"^(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.M)


def _pages() -> list[Path]:
    return sorted(_STATIC.glob("*.html"))


def _scripts(path: Path) -> list[str]:
    return _SCRIPT.findall(path.read_text(encoding="utf-8", errors="replace"))


class StaticJsTest(unittest.TestCase):

    def test_there_are_pages_to_check(self):
        """A guard that silently has nothing to guard is not a guard.

        If the static directory is renamed or emptied, every other test in this
        file would pass vacuously. This is the tripwire for that.
        """
        pages = _pages()
        self.assertTrue(pages, f"no *.html under {_STATIC}")
        self.assertTrue(
            any(_scripts(p) for p in pages),
            "no inline <script> blocks found in any static page — either the "
            "pages stopped carrying JS or the extractor regex stopped matching")

    def test_no_duplicate_top_level_declarations(self):
        """The exact defect: two top-level `const`/`let`/`class` of one name.

        Checked per page across ALL of its inline blocks together, because
        separate <script> blocks in one document share the global scope — the
        duplicate does not have to be inside a single block to be fatal.
        """
        for page in _pages():
            blocks = _scripts(page)
            if not blocks:
                continue
            seen: dict[str, int] = {}
            for src in blocks:
                for name in _TOP_DECL.findall(src):
                    seen[name] = seen.get(name, 0) + 1
            dupes = sorted(n for n, c in seen.items() if c > 1)
            self.assertEqual(
                dupes, [],
                f"{page.name}: top-level const/let/class declared more than once: "
                f"{dupes}. This is a SyntaxError and it aborts the ENTIRE script "
                f"block, so the whole page goes blank — not just the feature that "
                f"introduced the name.")

    def test_top_level_functions_are_not_shadowed(self):
        """Redeclaring a top-level function is legal but silently changes behaviour.

        Not a SyntaxError, so `node --check` will not catch it: the last
        definition simply wins and the earlier one is unreachable. On a page where
        two features each define `loadGraph`, one of them stops working with no
        error anywhere.
        """
        for page in _pages():
            counts: dict[str, int] = {}
            for src in _scripts(page):
                for name in _TOP_FUNC.findall(src):
                    counts[name] = counts.get(name, 0) + 1
            dupes = sorted(n for n, c in counts.items() if c > 1)
            self.assertEqual(
                dupes, [],
                f"{page.name}: top-level function(s) defined more than once: "
                f"{dupes}. Legal JS, so nothing errors — the later definition "
                f"just wins and the earlier feature silently stops working.")

    @unittest.skipIf(shutil.which("node") is None, "node unavailable")
    def test_scripts_parse(self):
        """Full syntax check of each inline block via ``node --check``.

        Wrapped in a function expression so DOM references are only *parsed*,
        never executed — this asserts the page's JS is syntactically valid, not
        that it runs headless.
        """
        node = shutil.which("node")
        for page in _pages():
            for i, src in enumerate(_scripts(page)):
                with tempfile.NamedTemporaryFile(
                        "w", suffix=".js", delete=False, encoding="utf-8") as fh:
                    fh.write("(function(){\n" + src + "\n});\n")
                    tmp = Path(fh.name)
                try:
                    proc = subprocess.run(
                        [node, "--check", str(tmp)],
                        capture_output=True, text=True, timeout=60)
                finally:
                    tmp.unlink(missing_ok=True)
                self.assertEqual(
                    proc.returncode, 0,
                    f"{page.name} script block #{i} does not parse:\n{proc.stderr}")

    @unittest.skipIf(shutil.which("node") is None, "node unavailable")
    def test_kernel_current_state_renderer_executes(self):
        """Execute the evidence-snapshot renderer against its minimum wire shape.

        ``node --check`` cannot catch a free identifier inside a function.  The
        production-kernel-set renderer once read ``state.production_kernel_set``
        even though the function binds the payload as ``s``.  The page parsed, but
        the resulting ReferenceError prevented controls, activity, and contract
        sections from rendering.  This small DOM stub exercises that boundary.
        """
        page = _STATIC / "kernel.html"
        blocks = _scripts(page)
        self.assertEqual(len(blocks), 1, "kernel.html must carry one inline script")
        source = blocks[0].split("async function load()", 1)[0]
        payload = r'''{
          _activity: {current_state: {
            production_kernel: {available: false},
            production_kernel_set: {
              intact: false, expected_kernels: 3, expected_binaries: 4,
              trees_matching: 3, binaries_proven: 4, binaries_unverified: 0,
              members: [{title: "llama.cpp", branch: "production-v9", head: "abc",
                matches_attestation: true,
                ggml_generation: {observed: "0.16.0", expected: null}}],
              binaries: [], stable_links: [], linkage: [],
              stable_links_ok: 4, linkage_verified: 4,
              ggml_generations_proven: 2, alarms: [],
              ambient_library_path: {clean: true, note: "dashboard process only"}
            },
            decision_controls: {available: false},
            instrument_preflight: {available: false},
            gpu_prefetch_replay: {available: false},
            fixed_campaign: {available: false},
            available_source_diagnostic: {available: false},
            empirical_smoke: {available: false},
            receipt_coverage: {note: "CURATED VIEW", projected_schemas: ["one.v1"]}
          }}
        }'''
        harness = f'''\nconst __box = {{innerHTML: "", classList: {{remove() {{}}, add() {{}}}}, style: {{}}}};
globalThis.document = {{
  querySelector() {{ return __box; }},
  querySelectorAll() {{ return []; }},
  createElement() {{ return __box; }}
}};
{source}
renderCurrentState({payload});
const __stateHtml = __box.innerHTML;
if (!__stateHtml.includes("Production kernel SET")) {{
  throw new Error("current-state renderer did not reach the kernel-set card");
}}
for (const expected of ["ggml observed 0.16.0", "not attested",
                        "dashboard process only", "CURATED VIEW"]) {{
  if (!__stateHtml.includes(expected)) throw new Error("missing distinction: " + expected);
}}
renderSections({{
  _render: {{mode: "contract_v2"}},
  sections: {{blocking_conditions: {{status: "observed", as_of: "now", open: [{{
    kind: "PREFLIGHT_REFUSED", detail: "host uptime exceeds the ratified ceiling"
  }}]}}}}
}});
if (!__box.innerHTML.includes("host uptime exceeds the ratified ceiling")) {{
  throw new Error("blocking-condition detail was reduced to a generic label");
}}
'''
        proc = subprocess.run(
            [shutil.which("node"), "-e", harness], capture_output=True,
            text=True, timeout=60)
        self.assertEqual(
            proc.returncode, 0,
            "kernel current-state renderer failed at runtime:\n" + proc.stderr)


if __name__ == "__main__":
    unittest.main()
