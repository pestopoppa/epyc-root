#!/usr/bin/env python3
"""Tests for premise_screener.py — the P2-2 point classifier.

WHAT THESE PIN, AND WHY EACH ONE IS WORTH PINNING.

`premise_screener` exists because a screen of a row's FORM cannot know whether
the world has already satisfied it: 4 of 8 fact-checked rows on 2026-08-12, then
7 of 11, had premises that were already true. Its whole value is therefore in
the four properties below, and every one of them is a property of a FAILURE
path — which is exactly the class of behaviour that rots silently, because
nothing downstream notices a screener that quietly says yes.

  1. EVIDENCE IS MANDATORY. A verdict with no usable quote is downgraded to
     "unknown", never accepted. `EvidenceGateTests`, and `MutationCheckTests`
     proves that test is not vacuous by deleting the gate and watching it fail.
  2. THE CHEAP CHECK RUNS FIRST. A mechanically-provable closed row returns
     "stale" having made ZERO model calls. `MechanicalShortCircuitTests` counts
     the calls with a client that records every invocation.
  3. FAILURE IS "UNKNOWN", NEVER "STILL-NEEDED". Timeouts, exceptions, garbage,
     no server — all "unknown". `ClientFailureTests`. The specific thing being
     forbidden is a fail-open: "still-needed" on error would re-dispatch
     satisfied work, which is the failure this module was built to stop.
  4. THE ENUM IS CLOSED. No input produces a fourth verdict. `VerdictEnumTests`
     fuzzes the model's output field with the values a real model actually
     emits when it is off-script.

NO LIVE MODEL IS REQUIRED OR PERMITTED. Every test injects a stub client. A test
that could reach a real server would pass or fail on the weather.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import premise_screener as ps  # noqa: E402
import backlog_row_check as brc  # noqa: E402


# --------------------------------------------------------------- stub clients


class RecordingClient:
    """A stub model client. Records every call; returns a canned response.

    Injected via `screen_premise(..., client=...)`, which is the reason that
    keyword exists: the module must be testable without a server, and a test
    that needs the stack up is a test that does not run.
    """

    def __init__(self, response="", raises=None):
        self.response = response
        self.raises = raises
        self.calls: list[str] = []

    def __call__(self, prompt, *, timeout_s=90.0):
        self.calls.append(prompt)
        if self.raises is not None:
            raise self.raises
        return self.response

    @property
    def n_calls(self) -> int:
        return len(self.calls)


def reply(verdict, evidence, reason="because the probe says so, at length"):
    return json.dumps({"verdict": verdict, "evidence": evidence, "reason": reason})


#: A row whose text matches nothing in handoffs/active/, so the mechanical layer
#: abstains and the model path is exercised. No paths in it, so the artifact
#: probes stay empty and the test does no filesystem or git work.
UNRESOLVABLE_ROW = {
    "task_id": "test-row-001",
    "task_text": "Zzq unresolvable premise sentinel for the screener unit tests",
}


# --------------------------------------------------- 1. mandatory evidence

def _assert_evidenceless_downgrades(module, case: unittest.TestCase) -> None:
    """The assertion body of the evidence-gate test, factored out.

    It lives in a function taking the MODULE so `MutationCheckTests` can run the
    identical assertions against a mutant with the downgrade deleted. Without
    this factoring the mutation check would be testing a copy of the test rather
    than the test itself.
    """
    for bad in ("", "   ", "n/a", "none", "stale", "N/A", "see above", "?"):
        client = RecordingClient(reply("stale", bad))
        out = module.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        case.assertEqual(
            out["verdict"], "unknown",
            f"evidence {bad!r} is not a usable quote, so the verdict must be "
            f"downgraded to unknown — got {out['verdict']!r}",
        )
        case.assertEqual(out["evidence"], "")
        case.assertEqual(client.n_calls, 1, "the model should have been consulted once")

    # A non-string evidence field is the same defect wearing a different type.
    for bad in (None, 12, [], {"quote": "x"}):
        client = RecordingClient(json.dumps(
            {"verdict": "stale", "evidence": bad, "reason": "r"}))
        out = module.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        case.assertEqual(out["verdict"], "unknown", f"evidence {bad!r} must downgrade")


class EvidenceGateTests(unittest.TestCase):
    def test_evidenceless_verdict_downgrades_to_unknown(self):
        _assert_evidenceless_downgrades(ps, self)

    def test_downgrade_is_recorded_not_silent(self):
        """A refused verdict must be auditable — the caller has to be able to
        tell 'the model said unknown' from 'the model said stale and I refused
        it'. Those route differently."""
        client = RecordingClient(reply("stale", ""))
        out = ps.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        self.assertEqual(out["verdict"], "unknown")
        self.assertEqual(out["provenance"]["downgraded_from"], "stale")
        self.assertEqual(
            out["provenance"]["downgrade_cause"], "missing-or-unusable-evidence")
        self.assertIn("no usable evidence", out["reason"])

    def test_a_real_quote_is_accepted(self):
        """The positive control. A gate that refused everything would pass every
        test above while making the module useless."""
        quote = "worker_runner.py:1 — file does not exist on disk"
        client = RecordingClient(reply("still-needed", quote))
        out = ps.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        self.assertEqual(out["verdict"], "still-needed")
        self.assertEqual(out["evidence"], quote)
        self.assertEqual(client.n_calls, 1)

    def test_verdict_restated_as_evidence_is_not_evidence(self):
        client = RecordingClient(reply("stale", "still-needed"))
        out = ps.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        self.assertEqual(out["verdict"], "unknown")


# ------------------------------------------ 2. mechanical short-circuit

class MechanicalShortCircuitTests(unittest.TestCase):
    """A closed checkbox is proof. Proof costs zero tokens.

    Built against a REAL temporary handoff file driven through
    `backlog_row_check.find_by_text`/`classify` — not a mocked mechanical layer.
    Mocking it would test that the mock returns what the mock was told to.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "fake-handoff.md").write_text(
            "# Fake handoff\n"
            "\n"
            "## Phase 0\n"
            "\n"
            "- [x] QQ-1 Relocate the widget cache to the raid array ✅ 2026-08-15\n"
            "- [ ] QQ-2 Teach the widget cache to expire entries older than a week\n",
            encoding="utf-8",
        )
        self._saved = brc.HANDOFFS
        brc.HANDOFFS = self.dir
        self.addCleanup(self._restore)

    def _restore(self):
        brc.HANDOFFS = self._saved
        self.tmp.cleanup()

    def test_closed_row_returns_stale_with_zero_model_calls(self):
        client = RecordingClient(reply("still-needed", "a perfectly good quote here"))
        out = ps.screen_premise(
            {"task_id": "qq-1",
             "task_text": "QQ-1 Relocate the widget cache to the raid array"},
            client=client,
        )
        self.assertEqual(out["verdict"], "stale")
        self.assertEqual(
            client.n_calls, 0,
            "a mechanically-provable closed row must not spend an LLM call")
        self.assertEqual(out["provenance"]["llm_calls"], 0)
        self.assertEqual(out["provenance"]["decided_by"], "mechanical")
        self.assertIn("Relocate the widget cache", out["evidence"])
        self.assertIsNone(out["provenance"]["model"])

    def test_open_row_does_reach_the_model(self):
        """The negative control for the short-circuit. If the mechanical layer
        graded open rows too, the test above would pass for the wrong reason."""
        client = RecordingClient(reply("still-needed", "the expiry code is absent"))
        out = ps.screen_premise(
            {"task_id": "qq-2",
             "task_text": "QQ-2 Teach the widget cache to expire entries "
                          "older than a week"},
            client=client,
        )
        self.assertEqual(client.n_calls, 1)
        self.assertEqual(out["verdict"], "still-needed")
        self.assertEqual(out["provenance"]["mechanical"]["state"], "open")

    def test_open_row_bundle_carries_the_mechanical_findings(self):
        """The model must be given the probe RESULTS, not just the row text —
        otherwise it can only reason about plausibility, which is what the
        example pack spends six examples warning against."""
        client = RecordingClient(reply("still-needed", "the expiry code is absent"))
        ps.screen_premise(
            {"task_text": "QQ-2 Teach the widget cache to expire entries "
                          "older than a week"},
            client=client,
        )
        prompt = client.calls[0]
        self.assertIn("QQ-2 Teach the widget cache", prompt)
        self.assertIn("fake-handoff.md", prompt)
        self.assertIn("WORKED EXAMPLES", prompt)


# --------------------------------------------- 3. failure is always unknown

class ClientFailureTests(unittest.TestCase):
    """Every way the model can let us down, and the one answer to all of them.

    The forbidden outcome is not "a crash" — it is "still-needed". A crash is
    loud; a fail-open verdict is silent and re-runs satisfied work.
    """

    def _assert_unknown(self, out, why):
        self.assertEqual(out["verdict"], "unknown", why)
        self.assertNotEqual(out["verdict"], "still-needed")
        self.assertIn("verdict", out)
        self.assertIn("evidence", out)
        self.assertIn("reason", out)

    def test_client_raises_timeout(self):
        client = RecordingClient(raises=TimeoutError("read timed out after 90s"))
        out = ps.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        self._assert_unknown(out, "a timeout is not a verdict")
        self.assertIn("TimeoutError", out["reason"])

    def test_client_raises_connection_error(self):
        client = RecordingClient(raises=ConnectionRefusedError("connection refused"))
        out = ps.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        self._assert_unknown(out, "an unreachable server is not a verdict")

    def test_client_raises_arbitrary_exception(self):
        class Boom(Exception):
            pass

        client = RecordingClient(raises=Boom("something nobody anticipated"))
        out = ps.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
        self._assert_unknown(out, "an unanticipated exception is not a verdict")

    def test_unparseable_output(self):
        for junk in ("", "I think it is probably fine, honestly.",
                     "{not json at all", "```json\n{oops\n```", "null", "[]"):
            out = ps.screen_premise(
                dict(UNRESOLVABLE_ROW), client=RecordingClient(junk))
            self._assert_unknown(out, f"{junk!r} is not a parseable verdict")

    def test_offline_mode_is_unknown_not_fine(self):
        out = ps.screen_premise(dict(UNRESOLVABLE_ROW), offline=True)
        self._assert_unknown(out, "offline means undetermined, not satisfied")
        self.assertEqual(out["provenance"]["llm_calls"], 0)

    def test_no_client_and_nothing_reachable(self):
        """With discovery pointed at a dead port, the module must return unknown
        rather than raise — `worker_runner.py` calls this in its preflight."""
        saved = ps._DEFAULT_ENDPOINTS
        ps._DEFAULT_ENDPOINTS = ("http://127.0.0.1:1/v1",)
        saved_orch = ps._ORCHESTRATOR_BASE
        ps._ORCHESTRATOR_BASE = "http://127.0.0.1:1"
        try:
            out = ps.screen_premise(dict(UNRESOLVABLE_ROW), discovery_timeout_s=0.25)
        finally:
            ps._DEFAULT_ENDPOINTS = saved
            ps._ORCHESTRATOR_BASE = saved_orch
        self._assert_unknown(out, "no reachable model means undetermined")
        self.assertIn("no model server answered", out["provenance"]["client"]["error"])

    def test_garbage_row_input(self):
        for bad in (None, [], "a string", 7):
            out = ps.screen_premise(bad)  # type: ignore[arg-type]
            self._assert_unknown(out, f"row={bad!r} cannot be screened")
        out = ps.screen_premise({})
        self._assert_unknown(out, "an empty row carries no identity")

    def test_never_raises_across_the_whole_failure_surface(self):
        """The runner's preflight has no except: around this call."""
        for client in (RecordingClient(raises=KeyError("k")),
                       RecordingClient(raises=ValueError("v")),
                       RecordingClient(raises=OSError("o")),
                       RecordingClient("garbage")):
            try:
                ps.screen_premise(dict(UNRESOLVABLE_ROW), client=client)
            except Exception as exc:  # pragma: no cover - the failure being pinned
                self.fail(f"screen_premise raised {type(exc).__name__}: {exc}")


# ---------------------------------------------------- 4. the enum is closed

class VerdictEnumTests(unittest.TestCase):
    OFF_SCRIPT = [
        "STALE", "Still-Needed", "still needed", "STILL_NEEDED", "UNKNOWN",
        "maybe", "probably-stale", "needs-review", "yes", "no", "true", "false",
        "still-needed (high confidence)", "", "   ", "verdict", "1", "null",
        "stale|still-needed", "I am not sure", "STALE.", "`stale`",
    ]

    def test_no_input_yields_a_fourth_verdict(self):
        good_quote = "queue.jsonl — test -L reports REGULAR_FILE, not a symlink"
        for raw in self.OFF_SCRIPT:
            out = ps.screen_premise(
                dict(UNRESOLVABLE_ROW),
                client=RecordingClient(reply(raw, good_quote)),
            )
            self.assertIn(
                out["verdict"], ps.VERDICTS,
                f"model verdict {raw!r} produced {out['verdict']!r}, which is "
                f"outside the closed ladder {ps.VERDICTS}",
            )

    def test_non_string_and_structural_junk_verdicts(self):
        for raw in (None, 3, ["stale"], {"v": "stale"}, True):
            out = ps.screen_premise(
                dict(UNRESOLVABLE_ROW),
                client=RecordingClient(json.dumps(
                    {"verdict": raw, "evidence": "a genuinely long quote here",
                     "reason": "r"})),
            )
            self.assertIn(out["verdict"], ps.VERDICTS)

    def test_case_and_punctuation_normalise_rather_than_escape(self):
        quote = "queue.jsonl — test -L reports REGULAR_FILE, not a symlink"
        cases = {"STALE": "stale", "`stale`": "stale", "STALE.": "stale",
                 "Still-Needed": "still-needed", "still needed": "still-needed",
                 "UNKNOWN": "unknown", "maybe": "unknown"}
        for raw, expected in cases.items():
            out = ps.screen_premise(
                dict(UNRESOLVABLE_ROW), client=RecordingClient(reply(raw, quote)))
            self.assertEqual(out["verdict"], expected, f"{raw!r} -> {expected!r}")

    def test_coerce_verdict_directly(self):
        """The single mint point. If a future edit adds a second place a verdict
        string is constructed, this test keeps passing and the enum silently
        opens — so `test_no_input_yields_a_fourth_verdict` above is the one that
        matters, and this one just pins the mapping."""
        self.assertEqual(ps._coerce_verdict("stale"), "stale")
        self.assertEqual(ps._coerce_verdict("STALE"), "stale")
        self.assertEqual(ps._coerce_verdict("whatever"), "unknown")
        self.assertEqual(ps._coerce_verdict(None), "unknown")


# ------------------------------------------------------------- provenance

class ProvenanceTests(unittest.TestCase):
    def test_model_id_and_prompt_hash_are_recorded(self):
        client = RecordingClient(reply("still-needed", "a quotable line of evidence"))
        out = ps.screen_premise(
            dict(UNRESOLVABLE_ROW), client=client, model="worker_general")
        prov = out["provenance"]
        self.assertEqual(prov["model"], "worker_general")
        self.assertRegex(prov["prompt_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(prov["llm_calls"], 1)
        self.assertEqual(prov["screener_version"], ps.SCREENER_VERSION)
        self.assertIn("sha256", prov["pack"])

    def test_prompt_hash_is_stable_for_the_same_row(self):
        a = ps.screen_premise(dict(UNRESOLVABLE_ROW),
                              client=RecordingClient(reply("stale", "quotable line here")))
        b = ps.screen_premise(dict(UNRESOLVABLE_ROW),
                              client=RecordingClient(reply("stale", "quotable line here")))
        self.assertEqual(a["provenance"]["prompt_sha256"],
                         b["provenance"]["prompt_sha256"])

    def test_real_example_pack_is_the_one_loaded(self):
        text, meta = ps.load_example_pack()
        self.assertFalse(
            meta["builtin"],
            "coordination/evals/examples/premise_screener.md should be readable; "
            "the built-in fallback is for degraded hosts only")
        self.assertIn("still-needed", text)
        self.assertIn("stale", text)

    def test_missing_pack_falls_back_and_says_so(self):
        out_text, meta = ps.load_example_pack(Path("/nonexistent/pack.md"))
        self.assertTrue(meta["builtin"])
        self.assertIn("fallback_reason", meta)
        self.assertIn("UNKNOWN", out_text)


# --------------------------------------------------------- the mutation check

def _load_mutant(source_transform):
    """Import a copy of premise_screener.py with its source transformed."""
    src = Path(ps.__file__).read_text(encoding="utf-8")
    mutated = source_transform(src)
    assert mutated != src, "the mutation did not change the source"
    tmpdir = tempfile.mkdtemp()
    path = Path(tmpdir) / "premise_screener_mutant.py"
    path.write_text(mutated, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("premise_screener_mutant", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _remove_evidence_downgrade(src: str) -> str:
    """Delete the evidence gate: `_usable_evidence` accepts anything.

    This is the precise inverse of requirement 2 — the module still returns a
    verdict, still parses, still runs; the ONLY thing gone is the refusal to
    accept an unevidenced verdict. If `EvidenceGateTests` still passed against
    this, it would be testing nothing.
    """
    pattern = re.compile(
        r"def _usable_evidence\(raw: Any\) -> Optional\[str\]:.*?(?=\ndef _extract_json)",
        re.S,
    )
    replacement = (
        "def _usable_evidence(raw: Any) -> Optional[str]:\n"
        "    # MUTANT: the downgrade gate has been deleted.\n"
        "    return raw if isinstance(raw, str) else \"\"\n\n\n"
    )
    return pattern.sub(replacement, src, count=1)


class MutationCheckTests(unittest.TestCase):
    """Proves `EvidenceGateTests` is not vacuous.

    Standing project rule: a check can pass for at least eight reasons that have
    nothing to do with the code being right, and the way you find out which one
    you have is to break the thing on purpose and watch the check go red. So the
    mutation is not run by hand once and reported in prose — it runs here, in
    the suite, and it is COUNTED by the reporter.
    """

    def test_mutant_is_actually_different(self):
        mutant = _load_mutant(_remove_evidence_downgrade)
        self.assertEqual(mutant._usable_evidence("n/a"), "n/a",
                         "the mutant should accept a non-quote as evidence")
        self.assertIsNone(ps._usable_evidence("n/a"),
                          "the real module must still refuse it")

    def test_evidence_gate_test_fails_against_the_mutant(self):
        mutant = _load_mutant(_remove_evidence_downgrade)
        with self.assertRaises(AssertionError) as caught:
            _assert_evidenceless_downgrades(mutant, self)
        self.assertIn(
            "downgraded to unknown", str(caught.exception),
            "the mutant must fail on the downgrade assertion specifically, not "
            "incidentally on a crash — a mutation that fails for the wrong "
            "reason proves nothing about the test",
        )

    def test_mutant_accepts_the_unevidenced_verdict_end_to_end(self):
        """Name the damage: with the gate gone, an unevidenced 'stale' is
        returned as a verdict, which parks a live row and, in the runner, routes
        a fix task for work that still needs doing."""
        mutant = _load_mutant(_remove_evidence_downgrade)
        out = mutant.screen_premise(
            dict(UNRESOLVABLE_ROW), client=RecordingClient(reply("stale", "n/a")))
        self.assertEqual(out["verdict"], "stale")
        self.assertEqual(ps.screen_premise(
            dict(UNRESOLVABLE_ROW),
            client=RecordingClient(reply("stale", "n/a")))["verdict"], "unknown")


# ------------------------------------------------------------------- CLI

class CLITests(unittest.TestCase):
    def test_row_json_offline_prints_json_and_exits_3(self):
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = ps.main(["--row-json", json.dumps(UNRESOLVABLE_ROW), "--offline"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["verdict"], "unknown")
        self.assertEqual(code, 3, "unknown exits 3 so a shell caller can branch")
        self.assertIn("provenance", payload)

    def test_bad_row_json_is_rejected(self):
        with self.assertRaises(SystemExit):
            ps.main(["--row-json", "{not json"])
        with self.assertRaises(SystemExit):
            ps.main(["--row-json", "[1,2,3]"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
