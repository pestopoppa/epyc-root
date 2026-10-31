"""Synthetic integration using unmodified, pinned APP producer AST bodies.

Materialize the four pinned files listed below from APP_COMMIT into --source-root.
Only the native producer slice executes; imports, transport, models and scoring
are not loaded. The journal envelope is an explicitly synthetic source-shaped
wrapper around the exact result emitted by the actual native sidecar writer.
This test is compatibility evidence, never a genuine evaluation cohort.
"""

import __future__
import argparse
import ast
import dataclasses
import hashlib
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import threading
import time
import types
from typing import Any
import unittest

APP_COMMIT = "0c4833bc3b0a38275e0b41433f9be68d6cf9b11f"
PINS = {
    "eval_tower.py": "289b2bc2a7a0f2380df8efdbfa45c3266e8ca0dde5db7eb0c441674b43d652d6",
    "measurement_guards.py": "b101d4c108c24ca9c24d0b443f32c11200236c61af1dc82c41a956d8929bd470",
    "behavior_signature.py": "5666e929ef58785751ce094b0b38575f06361dc42dbd246e697d5b35cd8336ef",
    "instrument_eras.yaml": "e329abef42d9f57980f21311e93b22d250bedc9c961b03aa3dd6f537e777a962",
}
SELECT = {
    "measurement_guards.py": {"DISPOSITION_SCORED"},
    "behavior_signature.py": {"normalize_answer_text", "normalized_answer_hash"},
    "eval_tower.py": {
        "_EVAL_QUESTION_JSONL_SCHEMA_VERSION",
        "EVAL_FENCE_ABSENT",
        "MAX_RECORDED_TOUCHED_PATHS",
        "_MAX_RECORDED_PATH_CHARS",
        "_HOST_COVARIATE_COMPACT_KEYS",
        "QUALITY_DENOMINATOR_POLICY",
        "_stable_question_qid",
        "_safe_artifact_name",
        "_compact_host_covariates",
        "_compact_question_result",
        "_EvalQuestionJsonlWriter",
        "EvalReconnectCost",
        "QuestionResult",
    },
}

_OPT_IN_SOURCE = os.environ.get("NIB83_NATIVE_SOURCE_ROOT")
SOURCE_ROOT = Path(_OPT_IN_SOURCE) if _OPT_IN_SOURCE else None
READER = Path(
    os.environ.get(
        "NIB83_NATIVE_READER", str(Path(__file__).with_name("postE17_histogram.py"))
    )
)


def load_native(source_root):
    module = types.ModuleType("_nib83_pinned_native")
    module.__dict__.update(
        {
            "dataclass": dataclasses.dataclass,
            "field": dataclasses.field,
            "hashlib": hashlib,
            "json": json,
            "math": math,
            "os": os,
            "Path": Path,
            "re": re,
            "threading": threading,
            "time": time,
            "Any": Any,
        }
    )
    sys.modules[module.__name__] = module
    custody = {
        "app_commit": APP_COMMIT,
        "synthetic_only": True,
        "native_runtime": "stdlib-only AST slice",
        "sources": [],
    }
    for name in (
        "measurement_guards.py",
        "behavior_signature.py",
        "eval_tower.py",
        "instrument_eras.yaml",
    ):
        expected = PINS[name]
        raw = (source_root / name).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise ValueError("pinned APP source mismatch: " + name)
        source = {"path": name, "sha256": actual, "nodes": []}
        if name in SELECT:
            selected = []
            found = set()
            text = raw.decode("utf-8")
            for node in ast.parse(text).body:
                identities = (
                    {node.name}
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                    else set()
                )
                if isinstance(node, ast.Assign):
                    identities = {
                        target.id
                        for target in node.targets
                        if isinstance(target, ast.Name)
                    }
                wanted = identities & SELECT[name]
                if wanted:
                    selected.append(
                        node
                    )  # Execute the original node, with no body rewrite.
                    found.update(wanted)
                    segment = ast.get_source_segment(text, node)
                    source["nodes"].append(
                        {
                            "names": sorted(wanted),
                            "line": node.lineno,
                            "source_sha256": hashlib.sha256(
                                segment.encode()
                            ).hexdigest(),
                            "ast_sha256": hashlib.sha256(
                                ast.dump(node, include_attributes=False).encode()
                            ).hexdigest(),
                        }
                    )
            if found != SELECT[name]:
                raise ValueError("missing or duplicated native slice nodes: " + name)
            code = compile(
                ast.Module(body=selected, type_ignores=[]),
                str(source_root / name),
                "exec",
                flags=__future__.annotations.compiler_flag,
            )
            exec(code, module.__dict__)
        custody["sources"].append(source)
    return module, custody


class NativeWriterCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE_ROOT is None:
            raise unittest.SkipTest(
                "opt-in pinned APP sources are unconfigured; run this file with "
                "--source-root/--custody-output or set NIB83_NATIVE_SOURCE_ROOT"
            )
        cls.native, cls.custody = load_native(SOURCE_ROOT)
        spec = importlib.util.spec_from_file_location("_nib83_reader", READER)
        cls.reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.reader)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def emitted(self, **values):
        result = self.native.QuestionResult(
            question_id="synthetic",
            suite="unit",
            prompt="",
            expected="",
            tokens_generated=3,
            **values,
        )
        writer = self.native._EvalQuestionJsonlWriter(
            root=self.root,
            root_source="synthetic_native_integration",
            eval_batch_id="synthetic-batch",
            trial_id=1,
            label="synthetic",
            requested_n=1,
            concurrency=1,
        )
        self.addCleanup(writer.close)
        writer.append_start()
        writer.append_result(
            ordinal=0,
            result=result,
            generated_at_s=1790199428.0,
            scored_at_s=1790199430.0,
        )
        writer.append_complete(completed_n=1, elapsed_s=2.0)
        writer.close()
        return [json.loads(line) for line in writer.path.read_text().splitlines()][
            -2
        ], writer.path

    def project(self, rows):
        source = self.root / "input.jsonl"
        source.write_text("".join(json.dumps(row) + "\n" for row in rows))
        if "mode" not in inspect.signature(self.reader.project).parameters:
            return self.reader.project(
                [source]
            )  # Retain meaningful original-behavior RED.
        return self.reader.project(
            [source], mode="native", registry_path=SOURCE_ROOT / "instrument_eras.yaml"
        )

    def journal(self, row, **details):
        return {
            "timestamp": "2026-10-22T00:00:00Z",
            "eval_details": {
                "question_results": [row["result"]],
                "details": {
                    "quality_denominator_policy": self.native.QUALITY_DENOMINATOR_POLICY,
                    "eval_quality_era": "E17-eval-task-failed-scores-zero-quality",
                    "eval_quality_era_status": "active",
                    **details,
                },
            },
        }

    def test_actual_bool_error_and_native_full_era(self):
        row, _ = self.emitted(
            error="synthetic agent error\nline", disposition="task_failed"
        )
        self.assertIs(row["result"]["error"], True)
        # No era label isolates Boolean-error compatibility from era-ID parsing.
        result = self.project([self.journal(row, eval_quality_era=None)])
        self.assertEqual(result["error_histogram"], {"synthetic agent error line": 1})
        self.assertEqual(result["class_counts"], {"task_failed": 1})
        self.assertEqual(result["registry"]["sha256"], PINS["instrument_eras.yaml"])
        full_era = self.project([self.journal(row)])
        self.assertEqual(full_era["error_histogram"], result["error_histogram"])

    def test_clean_wrong_answer_is_scored_but_incomplete_row_is_unknown(self):
        row, _ = self.emitted(answer="synthetic wrong answer", correct=False)
        self.assertNotIn("disposition", row["result"])
        self.assertNotIn("error", row["result"])
        clean = self.journal(row, eval_quality_era=None)
        broken = self.journal({"result": {}})
        result = self.project([clean, broken])
        self.assertEqual(result["class_counts"], {"scored": 1})
        self.assertEqual(result["unknown_or_unbound_question_rows"], 1)
        self.assertEqual(result["refusals"]["unsupported_native_compact_shape"], 1)

    def test_later_registered_era_requires_actual_native_policy(self):
        row, _ = self.emitted(error="synthetic error", disposition="task_failed")
        good = self.journal(row, eval_quality_era="E20-eval-corpus-ev19-quality")
        missing = self.journal(
            row,
            eval_quality_era="E20-eval-corpus-ev19-quality",
            quality_denominator_policy=None,
        )
        unknown = self.journal(row, eval_quality_era="E999-invented")
        malformed = self.journal(row, eval_quality_era=[])
        unresolved = self.journal(row, eval_quality_era_status="unresolved")
        result = self.project([good, missing, unknown, malformed, unresolved])
        self.assertEqual(result["residual_count"], 1)
        self.assertEqual(result["unknown_or_unbound_question_rows"], 4)
        self.assertEqual(result["refusals"]["quality_policy_missing_or_unknown"], 1)
        self.assertEqual(result["refusals"]["unregistered_eval_quality_era"], 2)
        self.assertEqual(result["refusals"]["eval_quality_era_status_unresolved"], 1)

    def test_native_generation_time_does_not_choose_quality_policy(self):
        row, _ = self.emitted(error="synthetic error", disposition="task_failed")
        result = self.project([row])
        self.assertEqual(result["residual_count"], 0)
        self.assertEqual(result["native_shape_counts"], {"task_failed": 1})
        self.assertEqual(result["refusals"]["sidecar_quality_policy_unbound"], 1)
        # A generation before E17, scored after E17, is not a policy conflict.
        before = 1790199428.0  # 2026-09-23T21:37:08Z; native generation fact only.
        after = 1790199430.0
        row["ended_at_s"] = before
        row["scored_at_s"] = after
        admitted = self.project([row, self.journal(row)])
        self.assertEqual(admitted["residual_count"], 1)
        self.assertEqual(
            admitted["timing"]["generation_ended_at_s"]["min"],
            "2026-09-23T21:37:08+00:00",
        )
        self.assertEqual(
            admitted["timing"]["scored_at_s"]["min"], "2026-09-23T21:37:10+00:00"
        )
        self.assertEqual(admitted["unknown_or_unbound_question_rows"], 1)
        self.assertIsNone(admitted["full_attempt_denominator"])

    def test_native_failure_classes_and_error_status_remain_distinct(self):
        rows = []
        for category in ("task_failed", "infra_failed", "scoring_failed"):
            # Independent writer path keeps append-only results source-generated.
            row, _ = self.emitted(
                error="synthetic quoted connection timeout", disposition=category
            )
            rows.append(self.journal(row))
        damaged = json.loads(json.dumps(rows[0]))
        damaged["eval_details"]["question_results"][0].pop("error")
        rows.append(damaged)
        result = self.project(rows)
        self.assertEqual(
            result["class_counts"],
            {"task_failed": 1, "infra_failed": 1, "scoring_failed": 1},
        )
        self.assertEqual(result["residual_count"], 1)  # Text never changes the class.
        self.assertEqual(result["refusals"]["missing_or_nonboolean_error_status"], 1)
        no_text = json.loads(json.dumps(rows[0]))
        no_text["eval_details"]["question_results"][0].pop("error_detail")
        missing_text = self.project([no_text])
        self.assertEqual(missing_text["class_counts"], {"task_failed": 1})
        self.assertEqual(missing_text["error_histogram"], {})
        self.assertEqual(missing_text["missingness"]["residual_error_text_unknown"], 1)

    def test_truncated_error_is_native_detail_and_public_output_has_only_hash(self):
        row, _ = self.emitted(error="x" * 210, disposition="task_failed")
        result = self.project([self.journal(row)])
        self.assertEqual(result["error_histogram"], {"x" * 200: 1})
        self.assertEqual(result["residual_text_at_native_cap_count"], 1)
        public = self.reader.public_summary(result)
        self.assertNotIn("error_histogram", public)
        self.assertNotIn("x" * 200, json.dumps(public))
        private = self.root / "private.json"
        self.reader._write_new_private(private, result)
        self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o600)
        with self.assertRaises(FileExistsError):
            self.reader._write_new_private(private, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--reader", type=Path, default=Path(__file__).with_name("postE17_histogram.py")
    )
    parser.add_argument("--custody-output", type=Path, required=True)
    args = parser.parse_args()
    SOURCE_ROOT, READER = args.source_root, args.reader
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeWriterCompatibility)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if hasattr(NativeWriterCompatibility, "custody"):
        args.custody_output.write_text(
            json.dumps(NativeWriterCompatibility.custody, indent=2) + "\n"
        )
    raise SystemExit(0 if result.wasSuccessful() else 1)
