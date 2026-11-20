"""Offline regression against pinned native code plus the exact proposed diff.

No API, model, database, source checkout copy or third-party dependency is used.
Run with python3 -m unittest discover -s proposed/m12k-probe-write -v.
"""
import ast
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get('M12K_ORCHESTRATOR', '/mnt/raid0/llm/epyc-orchestrator'))


def patched_source(source):
    """Apply the shipped one-hunk diff exactly in memory; refuse source drift."""
    lines = (HERE / 'probe-write.patch').read_text().splitlines(True)
    hunk = lines[next(i for i, line in enumerate(lines) if line.startswith('@@')) + 1:]
    before = ''.join(line[1:] for line in hunk if line.startswith((' ', '-')))
    after = ''.join(line[1:] for line in hunk if line.startswith((' ', '+')))
    if source.count(before) != 1:
        raise ValueError('patch context drift')
    return source.replace(before, after, 1)


class ProbeWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pins = json.loads((HERE / 'source-pins.json').read_text())
        for path, pin in pins['files'].items():
            content = (REPO / path).read_bytes()
            if hashlib.sha256(content).hexdigest() != pin['sha256']:
                raise AssertionError('source drift: ' + path)
        cls.native = (REPO / 'src/api/routes/chat_review.py').read_text()
        cls.candidate = patched_source(cls.native)
        spec = importlib.util.spec_from_file_location(
            'm12k_native_prompt_layout', REPO / 'src/backends/prompt_layout.py')
        cls.layout = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.layout)

    def execute(self, source, ir_source=None, bound_source=None, decision='parse_failure',
                scorer_error=False, with_scorer=True):
        node = next(n for n in ast.parse(source).body
                    if isinstance(n, ast.FunctionDef) and n.name == '_store_plan_review_episode')
        # Resolve only this function's dependencies; run its actual body unchanged.
        namespace = dict(TASK_IR_OBJECTIVE_LEN=200, log=logging.getLogger('m12k'),
                         _resolve_reviewer_role=lambda: 'architect_general',
                         _compute_plan_review_phase=Mock(return_value='B'))
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'chat_review.py', 'exec'), namespace)
        scorer = Mock()
        if scorer_error:
            scorer.score_external_result.side_effect = RuntimeError('offline failure')
        logger = Mock()
        state = types.SimpleNamespace(progress_logger=logger,
                                      q_scorer=scorer if with_scorer else None,
                                      hybrid_router=object(), plan_review_phase='A',
                                      update_plan_review_stats=Mock(return_value={'total_reviews': 51}))
        ir = dict(objective='a frozen objective', task_type='coder', risk_band='low')
        if ir_source is not None:
            ir['request_source'] = ir_source
        review = types.SimpleNamespace(decision=decision, score=0.0 if decision == 'parse_failure' else 0.9,
                                       is_ok=decision == 'ok', feedback='fixture', patches=[])
        progress = types.ModuleType('orchestration.repl_memory.progress_logger')
        progress.ProgressEntry = types.SimpleNamespace
        progress.EventType = types.SimpleNamespace(PLAN_REVIEWED='plan_reviewed')
        modules = {'src.backends.prompt_layout': self.layout,
                   'orchestration.repl_memory.progress_logger': progress}
        with patch.dict(sys.modules, modules), self.layout.source_scope(bound_source):
            result = namespace['_store_plan_review_episode'](state, 'task-1', ir, review)
        self.assertIsNone(result)
        state.update_plan_review_stats.assert_called_once_with(approved=review.is_ok)
        namespace['_compute_plan_review_phase'].assert_called_once_with({'total_reviews': 51})
        self.assertEqual(state.plan_review_phase, 'B')
        logger.log.assert_called_once()
        entry = logger.log.call_args.args[0]
        self.assertEqual(entry.data['decision'], decision)
        self.assertEqual(entry.outcome, 'success' if review.is_ok else 'corrected')
        self.assertEqual(ir['objective'], 'a frozen objective')
        return scorer

    def test_native_bug_reproduced(self):
        self.execute(self.native, 'probe').score_external_result.assert_called_once()

    def test_diagnostics_never_score_for_any_review_verdict(self):
        for source in ('probe', 'smoke', 'health', ' PROBE '):
            for decision in ('parse_failure', 'ok', 'drop', 'revise'):
                for ir, bound in ((source, None), (None, source), (source, source),
                                  (source, 'interactive'), ('interactive', source)):
                    with self.subTest(source=source, decision=decision, ir=ir, bound=bound):
                        self.execute(self.candidate, ir, bound, decision).score_external_result.assert_not_called()

    def test_learning_sources_preserve_exact_scoring_payload(self):
        for source in (None, 'interactive', 'benchmark', 'autopilot', 'repl_experiment', 'unknown'):
            for decision in ('parse_failure', 'ok', 'drop', 'revise'):
                with self.subTest(source=source, decision=decision):
                    native = self.execute(self.native, source, source, decision)
                    fixed = self.execute(self.candidate, source, source, decision)
                    fixed.score_external_result.assert_called_once()
                    self.assertEqual(native.score_external_result.call_args,
                                     fixed.score_external_result.call_args)

    def test_environment_alone_does_not_suppress_learning(self):
        with patch.dict(os.environ, {'ORCHESTRATOR_REQUEST_SOURCE': 'probe'}):
            self.execute(self.candidate).score_external_result.assert_called_once()

    def test_scorer_failure_remains_non_blocking(self):
        self.execute(self.candidate, 'interactive', scorer_error=True).score_external_result.assert_called_once()

    def test_missing_scorer_remains_safe(self):
        self.execute(self.candidate, with_scorer=False).score_external_result.assert_not_called()


if __name__ == '__main__':
    unittest.main()
