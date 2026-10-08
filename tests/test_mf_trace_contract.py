"""Prospective off-host native whole-module controls; no application imports."""
import ast
import hashlib
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE_SHA256 = "f50ff4a8f565e06cabe57fbf74e7009fa1a12fab68d7416ac17b4e87633491e8"

def isolated(trace_path):
    SRC = Path(os.environ["MF_TRACE_SOURCE"])
    raw = SRC.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    source = raw.decode()
    tree = ast.parse(source, filename=str(SRC))
    needed = {
        "_CALL_STOP_RE", "_ANNOUNCED_ACTION_VERSION", "_ANNOUNCED_ACTION_ADVERBS",
        "_ANNOUNCED_ACTION_VERBS", "_ANNOUNCED_ACTION_COMMITMENT",
        "_ANNOUNCED_ACTION_POSITIVE", "_ANNOUNCED_ACTION_NEAR", "_ANNOUNCED_ACTION_MODAL",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_is_comment_only", "_announced_action_plain_line", "_classify_announced_action",
            "_trace_announced_action", "_bep_turn_trace",
        }:
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in needed
            for target in node.targets
        ):
            selected.append(node)
    ns = {"re": re, "Any": object, "_trace_path": str(trace_path)}
    # Replace only application config-path resolution in the extracted writer.
    # The JSONL record construction, gating, clipping and append remain original AST.
    writer = next(n for n in selected if isinstance(n, ast.FunctionDef) and n.name == "_bep_turn_trace")
    config_tries = [n for n in ast.walk(writer) if isinstance(n, ast.Try) and any(
        isinstance(k, ast.ImportFrom) and k.module == "src.config" for k in n.body)]
    assert len(config_tries) == 1
    class IsolateConfig(ast.NodeTransformer):
        def visit_Try(self, node):
            if node is config_tries[0]:
                return ast.copy_location(ast.Assign(targets=[ast.Name(id="path", ctx=ast.Store())], value=ast.Name(id="_trace_path", ctx=ast.Load())), node)
            return self.generic_visit(node)
    writer = IsolateConfig().visit(writer)
    ast.fix_missing_locations(writer)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SRC), "exec"), ns)
    return ns, tree, source, SRC


class TraceControls(unittest.TestCase):
    def test_frozen_lexical_and_ordering_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            ns, tree, source, SRC = isolated(Path(d) / "trace.jsonl")
        classify = ns["_classify_announced_action"]
        trace_action = ns["_trace_announced_action"]
        # Exact positive forms: one anchored plain-prose clause, optional list bullet,
        # a concrete action verb, a nonempty object, and at most three approved adverbs.
        for text in (
            "I will inspect the config file.",
            "I'll carefully inspect the config file.",
            "I am going to check the result.",
            "I'm going to read the note.",
            "Let me open the file.",
            "Now I will run tests.",
            "Next I'll first then briefly check the manifest.",
            "- I will carefully first next inspect the module.",
            "2. Let me verify the expected output.",
        ):
            assert classify(text, complete=True) == (True, "explicit_anchored_commitment"), text

        # Clear complete negatives; quoted, inline-code, and fenced candidates never become positive.
        for text in (
            "The answer is 42.",
            "I looked at the file already.",
            '"I will inspect the config file."',
            "'I will inspect the config file.'",
            "`I will inspect the config file.`",
            "```python\nI will inspect the config file.\n```",
            "~~~text\nI'll run the test suite.\n~~~",
            "# I will inspect the code comment.",
        ):
            assert classify(text, complete=True) == (False, "no_candidate"), text

        # Ambiguous variants are unknown, never promoted to positive or false.
        for text in (
            "I will not inspect the file.",
            "I won't inspect the file.",
            "I might inspect the file.",
            "I could edit the file.",
            "I should run tests.",
            "If needed, I will inspect the file.",
            "I will probably inspect the file.",
            "I will inspect.",
            "I will eventually then inspect the file.",
            "I will inspect the file if it exists.",
            "I will inspect the file. I might edit it.",
            "For later: I will inspect the file.",
            "I will inspect `the file`.",
            "I will inspect the file?",
        ):
            value, status = classify(text, complete=True)
            assert value is None and status == "ambiguous_candidate", (text, value, status)

        assert classify("I will inspect the file.", complete=False) == (None, "incomplete_or_truncated")
        assert classify("I will inspect the file." + "x" * 4001, complete=True) == (None, "incomplete_or_truncated")
        assert classify("I will inspect the file.\n```python\n", complete=True) == (None, "unmatched_fence")
        assert classify("I will inspect `the file", complete=True) == (None, "unmatched_inline_code")
        assert classify('I will inspect "the file', complete=True) == (None, "unmatched_quote")
        assert classify("I will inspect the file.", complete=True, version="future.lex-v9") == (None, "unsupported_version")

        # Trace-carrier semantics: classify primary retained text only; no causal claim.
        assert trace_action("I will inspect the file.", complete=True, eligible=True,
                            retry_attempted=False, retry_failed=False) == (
            True, "explicit_anchored_commitment", "primary"
        )
        assert trace_action("I will inspect the file.", complete=True, eligible=True,
                            retry_attempted=True, retry_failed=False) == (
            None, "retry_output_not_retained", "retry"
        )
        assert trace_action("[ERROR: unavailable]", complete=True, eligible=False,
                            retry_attempted=False, retry_failed=False) == (
            None, "not_generated_output", "unknown"
        )
        assert trace_action("I will inspect the file.", complete=True, eligible=True,
                            retry_attempted=True, retry_failed=True) == (
            True, "explicit_anchored_commitment", "primary"
        )

        # Existing cheap synthetic controls retained without project imports.
        assert ns["_is_comment_only"]("") is True
        assert ns["_is_comment_only"]("\n # note\n\t") is True
        assert ns["_is_comment_only"]("# comment\nprint(1)") is False
        assert ns["_CALL_STOP_RE"].search('CALL("run_python_code")')
        assert not ns["_CALL_STOP_RE"].search('The word CALL is only discussed')

        trace_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_bep_turn_trace")
        trace_strings = {n.value for n in ast.walk(trace_fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        for required in {
            "native_completion_reason_primary", "native_completion_reason_retry",
            "completion_tokens_status", "requested_output_cap", "effective_output_cap_status",
            "raw_output_chars", "raw_output_truncated", "processed_output_chars",
            "post_extract_executable_code", "dsl_call_substring_signal", "nudge_branch_status",
            "announced_action_predicate_version", "announced_action_status",
            "announced_action_source",
        }:
            assert required in trace_strings, required
        assert "recognized_dsl_call" not in trace_strings
        assert ns["_ANNOUNCED_ACTION_VERSION"] == "announced_action.lex-v1"
        classifier_fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_classify_announced_action")
        classifier_strings = {n.value for n in ast.walk(classifier_fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert {"unsupported_version", "incomplete_or_truncated", "ambiguous_candidate", "no_candidate", "unmatched_fence"} <= classifier_strings
        assert any(isinstance(n, ast.Constant) and n.value == 4000 for n in ast.walk(trace_fn))
        assert "_reasoning_retry_output" not in source

        # Trace is emitted after prose rescue and before execution; early nudge outcomes retain trace calls.
        helper_text = source
        assert helper_text.count("_emit_bep_trace(False, \"comment_only\")") == 1
        assert helper_text.count("_emit_bep_trace(True, \"comment_ratio\")") == 1
        assert "action_source_output=_processed_raw" in helper_text
        assert "action_source_eligible=False" in helper_text
        assert "action_source_eligible=action_source_eligible" in helper_text
        trace_lines = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_emit_bep_trace"]
        repl_line = next(n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_tap_write_repl_exec")
        assert max(trace_lines) < repl_line
        assert "effective_output_cap" in trace_strings
        assert "not_exposed_by_call_metadata" in trace_strings

    def test_default_off_and_exact_enable(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "trace.jsonl"
            ns, _, _, _ = isolated(path)
            for value in (None, "", "0", "true"):
                with patch.dict(os.environ, {}, clear=True):
                    if value is not None:
                        os.environ["ORCHESTRATOR_BEP_TURN_TRACE"] = value
                    ns["_bep_turn_trace"](1, "frontdoor", "test")
                self.assertFalse(path.exists())

    def test_native_primary_retry_fields_and_unknown_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "trace.jsonl"
            ns, _, _, _ = isolated(path)
            with patch.dict(os.environ, {"ORCHESTRATOR_BEP_TURN_TRACE": "1"}):
                for primary, retry, attempted, failed in (
                    ({"completion_reason":"length", "transport":"model_server"}, {"completion_reason":"stop", "transport":"mock"}, True, False),
                    ({"completion_reason":"alien", "transport":"alien"}, None, False, False),
                    (["malformed"], "malformed", True, True),
                ):
                    ns["_bep_turn_trace"](1, "frontdoor", "I will inspect the file.",
                        primary_meta=primary, retry_meta=retry, retry_attempted=attempted,
                        retry_failed=failed, action_source_output="I will inspect the file.",
                        requested_output_cap=-1)
            rows=[json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(rows),3)
            self.assertEqual(rows[0]["native_completion_reason_primary"],"length")
            self.assertEqual(rows[0]["native_completion_reason_retry"],"stop")
            self.assertEqual(rows[0]["native_inference_transport"],"model_server")
            self.assertEqual(rows[0]["native_inference_transport_retry"],"mock")
            self.assertTrue(rows[0]["retry_attempted"])
            self.assertFalse(rows[0]["retry_failed"])
            self.assertEqual(rows[0]["announced_action_status"],"retry_output_not_retained")
            self.assertEqual(rows[1]["native_completion_reason_primary"],"unknown")
            self.assertEqual(rows[1]["native_completion_reason_retry"],"not_attempted")
            self.assertEqual(rows[1]["native_inference_transport"],"unknown")
            self.assertEqual(rows[1]["native_inference_transport_retry"],"not_attempted")
            self.assertEqual(rows[2]["native_completion_reason_primary"],"missing")
            self.assertEqual(rows[2]["native_completion_reason_retry"],"missing")
            self.assertTrue(rows[2]["retry_failed"])
            self.assertEqual(rows[2]["native_inference_transport_retry"],"unknown")
            for row in rows:
                self.assertIsNone(row["runtime_producer_revision"])
                self.assertEqual(row["runtime_producer_revision_status"],"unknown_not_captured")
                self.assertIsNone(row["completion_tokens"])
                self.assertIsNone(row["effective_output_cap"])
                self.assertEqual(row["completion_tokens_status"],"unsupported_unattested_backend_basis")
                self.assertEqual(row["effective_output_cap_status"],"not_exposed_by_call_metadata")
                self.assertEqual(row["requested_output_cap"],-1)

    def test_clipping_malformed_scalars_and_early_branch_unavailability(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "trace.jsonl"
            ns, _, _, _ = isolated(path)
            with patch.dict(os.environ, {"ORCHESTRATOR_BEP_TURN_TRACE":"1"}):
                ns["_bep_turn_trace"](2,"frontdoor","x"*4001,code="x"*2001,
                    requested_output_cap=True, processed_output_chars=True,
                    processed_output_truncated="false", post_extract_executable_code="false",
                    action_source_eligible=False, nudge_branch="batch_edit")
            row=json.loads(path.read_text())
            self.assertEqual(len(row["raw_output"]),4000)
            self.assertEqual(len(row["extracted_code"]),2000)
            self.assertTrue(row["raw_output_truncated"])
            for key in ("requested_output_cap","processed_output_chars", "processed_output_truncated","post_extract_executable_code"):
                self.assertIsNone(row[key])
            self.assertFalse(row["post_extract_known"])
            self.assertEqual(row["announced_action_status"],"not_generated_output")
            self.assertEqual(row["nudge_branch_status"],"unknown_post_execution")
