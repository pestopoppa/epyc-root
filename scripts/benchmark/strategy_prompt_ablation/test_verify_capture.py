"""Model-free tests of capture custody; test payloads are fabricated fixtures."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import native_capture
import verify_capture


class CaptureVerification(unittest.TestCase):
    def test_schedule_and_tampering(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            digests = {a: hashlib.sha256(a.encode()).hexdigest() for a in native_capture.ARMS}
            plan = {'schema': 'epyc.strategy_prompt_ablation.plan.v1', 'run_authority': False,
                    'prompt_sha256': digests, 'schedule': [{'question_id': 'q1', 'order': list(native_capture.ARMS)}]}
            pp = root / 'plan.json'; pp.write_text(json.dumps(plan))
            plan_sha = hashlib.sha256(pp.read_bytes()).hexdigest()
            captures = root / 'captures'; captures.mkdir()
            for i, arm in enumerate(native_capture.ARMS):
                native_capture.write_observation(captures / f'{i:06d}', plan_sha256=plan_sha, question_id='q1',
                    arm=arm, prompt_sha256=digests[arm], source_identity='fixture', slot_reset_receipt='fixture', origin='live_claimed', status='complete',
                    turns=[dict(request=b'fixture request', response=b'fixture response', prompt_tokens=2, output_tokens=3, elapsed_s=.1, error=None)], correct=True)
            result = verify_capture.verify(pp, captures)
            self.assertEqual(result['status'], 'custody_only')
            self.assertIn('No actual execution order', result['limitations'])
            (captures / '000001' / 'turn-0001-response.bin').write_bytes(b'tampered')
            with self.assertRaises(ValueError): verify_capture.verify(pp, captures)

    def test_refuses_incomplete_and_synthetic(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); captures = root / 'captures'; captures.mkdir()
            plan = {'schema': 'epyc.strategy_prompt_ablation.plan.v1', 'run_authority': False,
                    'prompt_sha256': {a: hashlib.sha256(a.encode()).hexdigest() for a in native_capture.ARMS},
                    'schedule': [{'question_id': 'q', 'order': list(native_capture.ARMS)}]}
            pp = root / 'plan.json'; pp.write_text(json.dumps(plan))
            with self.assertRaises(ValueError): verify_capture.verify(pp, captures)
            for i, arm in enumerate(native_capture.ARMS):
                native_capture.write_observation(captures / f'{i:06d}', plan_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),
                    question_id='q', arm=arm, prompt_sha256=plan['prompt_sha256'][arm], source_identity='fixture', slot_reset_receipt='fixture',
                    origin='synthetic', status='complete', turns=[dict(request=b'r', response=b's', prompt_tokens=0, output_tokens=0, elapsed_s=0, error=None)], correct=False)
            with self.assertRaises(ValueError): verify_capture.verify(pp, captures)

    def test_refuses_malformed_fields_and_errors_but_allows_explicit_null_metrics(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); captures = root / 'captures'; captures.mkdir()
            digests = {a: hashlib.sha256(a.encode()).hexdigest() for a in native_capture.ARMS}
            plan = {'schema': 'epyc.strategy_prompt_ablation.plan.v1', 'run_authority': False,
                    'prompt_sha256': digests,
                    'schedule': [{'question_id': 'q', 'order': list(native_capture.ARMS)}]}
            pp = root / 'plan.json'; pp.write_text(json.dumps(plan))
            digest = hashlib.sha256(pp.read_bytes()).hexdigest()
            for i, arm in enumerate(native_capture.ARMS):
                native_capture.write_observation(captures / f'{i:06d}', plan_sha256=digest,
                    question_id='q', arm=arm, prompt_sha256=digests[arm], source_identity='fixture',
                    slot_reset_receipt='fixture', origin='live_claimed', status='complete',
                    turns=[dict(request=b'r', response=b's', prompt_tokens=None, output_tokens=None,
                                elapsed_s=None, error=None)], correct=None)
            self.assertEqual(verify_capture.verify(pp, captures)['status'], 'custody_only')
            record_path = captures / '000000' / 'record.json'
            original = json.loads(record_path.read_text())
            for mutation in ('missing_metric', 'bool_turn', 'task_error', 'turn_error', 'extra_field'):
                record = json.loads(json.dumps(original))
                if mutation == 'missing_metric': del record['turns'][0]['prompt_tokens']
                if mutation == 'bool_turn': record['turns'][0]['turn'] = True
                if mutation == 'task_error': record['error'] = 'failed'
                if mutation == 'turn_error': record['turns'][0]['error'] = 'failed'
                if mutation == 'extra_field': record['extra'] = True
                record_path.write_text(json.dumps(record))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    verify_capture.verify(pp, captures)
            record_path.write_text(json.dumps(original))
            for bad in ('a' * 64, 'not-a-digest'):
                changed = dict(plan); changed['prompt_sha256'] = {a: bad for a in native_capture.ARMS}
                pp.write_text(json.dumps(changed))
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    verify_capture.verify(pp, captures)


if __name__ == '__main__': unittest.main()
