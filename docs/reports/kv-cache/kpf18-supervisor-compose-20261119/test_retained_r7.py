"""Accepted retained metadata inputs and synthetic refusal controls; no replay."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_execution_prerequisites as prerequisites

ROOT = Path('/mnt/raid0/llm/tmp/codex-ni-kpf18-native-segfault-r7-20261030')
PATHS = {
    'framing_result': ROOT / 'cpu-replay/attempts/1793382000-1793385600/RESULT.json',
    'complete_marker': ROOT / 'cpu-replay/COMPLETE',
    'source_manifest': ROOT / 'cpu-replay/SOURCES.sha256',
    'root_source_manifest': ROOT / 'SOURCES.sha256',
}


class RetainedR7(unittest.TestCase):
    setUp = prerequisites.Prerequisites.setUp
    prepare = prerequisites.Prerequisites.prepare
    inputs = prerequisites.Prerequisites.inputs
    bind = prerequisites.Prerequisites.bind

    def configure(self):
        self.inputs()
        self.config['enrollment'].update(framing_mode='retained-r7-v1',
                                        **{k: str(p) for k, p in PATHS.items()})
        for key, path in PATHS.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.binding.R7_PINS[key])
            self.seal['sources'][str(path)] = self.binding.R7_PINS[key]

    def test_exact_accepted_r7_entry_and_postcheck(self):
        self.configure(); self.bind()
        result = self.guard.tests_and_enrollment()
        self.assertEqual(result['framing_mode'], 'retained-r7-v1')
        self.assertEqual(result['accepted_result_sha256'], self.binding.R7_PINS['framing_result'])
        self.assertEqual(result['scope'], 'diagnostic; no new enrollment receipt')
        with patch.object(self.captured[0], 'recheck', side_effect=ValueError('provider lost')):
            with self.assertRaisesRegex(ValueError, 'provider lost'):
                self.guard.tests_and_enrollment()
        Path(self.config['stop_file']).touch()
        with self.assertRaisesRegex(ValueError, 'STOP'): self.guard.tests_and_enrollment()

    def test_default_r14_never_accepts_r7_and_unknown_mode_refuses(self):
        self.configure(); del self.config['enrollment']['framing_mode']; self.bind()
        with self.assertRaisesRegex(ValueError, 'prerequisite'): self.guard.tests_and_enrollment()
        self.config['enrollment']['framing_mode'] = 'r7'
        with self.assertRaisesRegex(ValueError, 'unknown framing'): self.guard.tests_and_enrollment()

    def test_each_missing_or_wrong_seal_refuses_without_fallback(self):
        self.configure(); self.bind()
        for key, path in PATHS.items():
            with self.subTest(key=key):
                expected = self.seal['sources'].pop(str(path))
                with self.assertRaisesRegex(ValueError, 'prerequisite'): self.guard.tests_and_enrollment()
                self.seal['sources'][str(path)] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'source drift'): self.guard.tests_and_enrollment()
                self.seal['sources'][str(path)] = expected

    def test_projection_is_still_required_for_r7(self):
        self.configure(); self.bind()
        canonical = Path(self.config['enrollment']['canonical_export'])
        del self.seal['sources'][str(canonical / next(iter(self.binding.PROJECTION)))]
        with self.assertRaisesRegex(ValueError, 'prerequisite'): self.guard.tests_and_enrollment()

    def test_digest_checked_independently_of_seal_inventory(self):
        self.configure()
        original = Path.read_bytes
        def drift(path):
            return b'drift' if path == PATHS['framing_result'] else original(path)
        with patch.object(Path, 'read_bytes', drift):
            with self.assertRaisesRegex(ValueError, 'prerequisite drift'):
                self.binding.retained_r7(self.config['enrollment'], lambda name, expected: Path(name))

    def test_semantics_even_with_synthetic_resealed_records(self):
        self.configure()
        baseline = json.loads(PATHS['framing_result'].read_text())
        mutations = [
            ('partial', True), ('rc', 1), ('rc', False), ('cleanup_verified', False),
            ('id', 'other'), ('source_manifest_sha256', '0' * 64),
            ('bridge_result.framing_pass', False), ('bridge_result.grid_count', 1127),
            ('bridge_result.event_count', 7), ('bridge_result.stages', []),
            ('bridge_result.raw_sha256', '0' * 64), ('bridge_result.ledger_sha256', '0' * 64),
            ('bridge_result.layouts_sha256', '0' * 64),
            ('bridge_result.fork_bindings_sha256', '0' * 64),
            ('bridge_result.historical_r6_verdict', 'PASS'),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                result = copy.deepcopy(baseline)
                target = result
                parts = field.split('.')
                for part in parts[:-1]: target = target[part]
                target[parts[-1]] = value
                data = json.dumps(result).encode()
                pins = dict(self.binding.R7_PINS, framing_result=hashlib.sha256(data).hexdigest())
                marker = json.loads(PATHS['complete_marker'].read_text())
                marker['result_sha256'] = pins['framing_result']
                marker_data = json.dumps(marker).encode()
                pins['complete_marker'] = hashlib.sha256(marker_data).hexdigest()
                def sealed(name, expected):
                    path = Path(name)
                    content = (data if path == PATHS['framing_result'] else
                               marker_data if path == PATHS['complete_marker'] else path.read_bytes())
                    return Mock(read_bytes=lambda: content)
                with patch.object(self.binding, 'R7_PINS', pins):
                    with self.assertRaisesRegex(ValueError, 'framing not valid'):
                        self.binding.retained_r7(self.config['enrollment'], sealed)

    def test_completion_marker_cannot_bind_another_result(self):
        self.configure()
        baseline = json.loads(PATHS['complete_marker'].read_text())
        for key, value in (('id', 'other'), ('result_path', '/other/RESULT.json'),
                           ('result_sha256', '0' * 64), ('schema', 'unknown')):
            with self.subTest(key=key):
                marker = dict(baseline, **{key: value})
                data = json.dumps(marker).encode()
                pins = dict(self.binding.R7_PINS, complete_marker=hashlib.sha256(data).hexdigest())
                def sealed(name, expected):
                    content = data if Path(name) == PATHS['complete_marker'] else Path(name).read_bytes()
                    return Mock(read_bytes=lambda: content)
                with patch.object(self.binding, 'R7_PINS', pins):
                    with self.assertRaisesRegex(ValueError, 'framing not valid'):
                        self.binding.retained_r7(self.config['enrollment'], sealed)


if __name__ == '__main__': unittest.main()
