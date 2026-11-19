"""Current entry controls with tiny sealed files; no model/runtime invocation."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_execution_binding as bindings
from test_execution_admission import sha


class Prerequisites(unittest.TestCase):
    setUp = bindings.CurrentGuard.setUp
    prepare = bindings.CurrentGuard.prepare

    def inputs(self):
        replay = self.root / 'framing.json'
        replay.write_text(json.dumps({'framing_pass': True, 'raw_sha256': self.binding.FRAMING_RAW_SHA}))
        canonical = self.root / 'canonical-export'
        projection = {}
        for leaf in self.binding.PROJECTION:
            path = canonical / leaf
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# synthetic projection; never imported\n')
            projection[leaf] = sha(path)
            self.seal['sources'][str(path)] = sha(path)
        self.seal['sources'][str(replay)] = sha(replay)
        self.binding.FRAMING_SHA = sha(replay)
        self.binding.PROJECTION = projection
        self.config['enrollment'] = {'framing_result': str(replay), 'canonical_export': str(canonical)}
        self.driver.BASE = self.root / 'base'
        self.driver.BASE.mkdir()
        receipt = self.root / 'receipt.json'
        manifest = self.driver.BASE / 'ORIGINAL-MODELS.json'
        for path in (receipt, manifest):
            path.write_text('{}\n')
            self.seal['sources'][str(path)] = sha(path)
        self.config['preload_receipt'] = str(receipt)
        self.loader = Mock(return_value={'synthetic': True})
        self.driver.load_preload_models = self.loader
        return replay, canonical, receipt, manifest

    def bind(self):
        _, bind = self.prepare()
        bind(self.driver)

    def test_enrollment_explicit_locations_preserve_diagnostic_scope(self):
        _, canonical, _, _ = self.inputs(); self.bind()
        self.assertEqual(self.guard.tests_and_enrollment(), {
            'canonical_export': str(canonical), 'scope': 'diagnostic; no new enrollment receipt'})

    def test_enrollment_requires_original_expected_identities(self):
        replay, canonical, _, _ = self.inputs()
        self.binding.FRAMING_SHA = '0' * 64
        self.bind()
        with self.assertRaisesRegex(ValueError, 'prerequisite'): self.guard.tests_and_enrollment()
        self.binding.FRAMING_SHA = sha(replay)
        first = next(iter(self.binding.PROJECTION))
        self.binding.PROJECTION[first] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'prerequisite'): self.guard.tests_and_enrollment()

    def test_framing_semantics_retained_even_for_sealed_input(self):
        replay, _, _, _ = self.inputs()
        replay.write_text(json.dumps({'framing_pass': False, 'raw_sha256': self.binding.FRAMING_RAW_SHA}))
        self.seal['sources'][str(replay)] = self.binding.FRAMING_SHA = sha(replay)
        self.bind()
        with self.assertRaisesRegex(ValueError, 'framing not valid'): self.guard.tests_and_enrollment()

    def test_missing_configuration_refuses_without_legacy_fallback(self):
        self.bind()
        with self.assertRaisesRegex(ValueError, 'prerequisite'): self.guard.tests_and_enrollment()

    def test_preload_delegates_same_inputs_and_checks_after_return(self):
        _, _, receipt, manifest = self.inputs(); self.bind()
        self.assertEqual(self.driver.RETAINED_PRELOAD_RECEIPT, receipt)
        self.assertEqual(self.driver.load_preload_models(receipt, manifest), {'synthetic': True})
        self.loader.assert_called_once_with(receipt, manifest)
        self.loader.side_effect = lambda *a: Path(self.config['stop_file']).touch()
        with self.assertRaisesRegex(ValueError, 'STOP'):
            self.driver.load_preload_models(receipt, manifest)

    def test_preload_missing_seal_or_redirection_never_calls_verifier(self):
        _, _, receipt, manifest = self.inputs(); self.bind()
        for args in ((self.root / 'foreign', manifest), (receipt, self.root / 'foreign')):
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, 'redirected'):
                self.driver.load_preload_models(*args)
        del self.seal['sources'][str(manifest)]
        with self.assertRaisesRegex(ValueError, 'prerequisite'):
            self.driver.load_preload_models(receipt, manifest)
        self.loader.assert_not_called()

    def test_stop_provider_loss_and_drift_refuse_both_entries(self):
        replay, _, receipt, manifest = self.inputs(); self.bind()
        calls = (self.guard.tests_and_enrollment, lambda: self.driver.load_preload_models(receipt, manifest))
        for call in calls:
            with patch.object(self.captured[0], 'recheck', side_effect=ValueError('provider lost')):
                with self.assertRaisesRegex(ValueError, 'provider lost'): call()
        replay.write_text('drift')
        for call in calls:
            with self.assertRaisesRegex(ValueError, 'source drift'): call()
        self.loader.assert_not_called()

    def test_verifier_failure_propagates_and_receipt_drift_refuses(self):
        _, _, receipt, manifest = self.inputs(); self.bind()
        self.loader.side_effect = ValueError('retained stat/metadata refusal')
        with self.assertRaisesRegex(ValueError, 'retained stat/metadata'):
            self.driver.load_preload_models(receipt, manifest)
        receipt.write_text('drift')
        with self.assertRaisesRegex(ValueError, 'source drift'):
            self.driver.load_preload_models(receipt, manifest)
        self.assertEqual(self.loader.call_count, 1)


if __name__ == '__main__': unittest.main()
