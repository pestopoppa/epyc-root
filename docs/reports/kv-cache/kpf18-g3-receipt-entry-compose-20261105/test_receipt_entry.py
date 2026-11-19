"""Real receipt/preload verifier composed with the source-pinned driver main."""
import hashlib
import json
import os
import unittest
from unittest.mock import patch
import preload_integration as preload
import verify_receipt as verifier
from test_driver_integration import DriverIntegration

class ReceiptEntry(DriverIntegration):
    def setUp(self):
        super().setUp()
        if 'QUAL_AFFINITY' in os.environ:
            self.assertEqual(sorted(os.sched_getaffinity(0)), json.loads(os.environ['QUAL_AFFINITY']))
        receipt, manifest = {}, {}
        for role in ('target', 'drafter'):
            path = self.root / (role + '.synthetic')
            path.write_bytes((role + '-small-fixture').encode())
            entry = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'tensor_count': 1, 'metadata': {'synthetic': True},
                     'stat_identity': verifier.stat_identity(str(path))}
            if role == 'drafter': entry['metadata'].update(verifier.DRAFT_SHAPE)
            receipt[role] = entry
            manifest[role] = {k: entry[k] for k in ('path', 'sha256')}
        self.receipt = self.root / 'receipt.json'
        self.receipt.write_text(json.dumps(receipt, sort_keys=True))
        (self.root / 'ORIGINAL-MODELS.json').write_text(json.dumps(manifest))
        # The fixture pin replaces the historical pin; verifier and preload logic remain real.
        self.pin = patch.object(preload, 'EXPECTED_RECEIPT_SHA256', hashlib.sha256(self.receipt.read_bytes()).hexdigest())
        self.pin.start(); self.addCleanup(self.pin.stop)
        self.env['RETAINED_PRELOAD_RECEIPT'] = self.receipt
        self.env['load_preload_models'] = preload.load_preload_models
        self.env['unchanged_models'] = self.check_models

    def check_models(self):
        self.events.append('model_identity')
        preload.unchanged_models(self.env['PRELOAD_MODELS'])

    def refuse(self, message):
        with self.assertRaisesRegex(verifier.VerificationError, message): self.invoke(['--window-id', 'fixture'])
        self.assertFalse(any(isinstance(x, tuple) and x[0] in ('install', 'gate') for x in self.events))
        self.assertFalse((self.root / 'PRELOAD-MODEL-IDENTITY.json').exists())

    def test_valid_receipt_reaches_witness_and_gate(self):
        self.assertEqual(self.invoke(['--window-id', 'fixture']), 19)
        self.assertEqual([x[0] for x in self.events if isinstance(x, tuple)], ['install', 'gate'])
        identity = json.loads((self.root / 'PRELOAD-MODEL-IDENTITY.json').read_text())
        self.assertEqual(set(identity), {'target', 'drafter'})
        self.assertEqual(self.env['PRELOAD_MODELS']['draft_cache_shape']['draft_swa_layers'], 5)

    def test_changed_receipt_refuses_before_witness(self):
        self.receipt.write_bytes(self.receipt.read_bytes() + b' ')
        self.refuse('receipt digest mismatch')

    def test_manifest_mismatch_refuses_before_witness(self):
        p = self.root / 'ORIGINAL-MODELS.json'; value = json.loads(p.read_text())
        value['target']['sha256'] = 'different'; p.write_text(json.dumps(value))
        self.refuse('target sha256 differs')

    def test_stat_drift_refuses_before_witness(self):
        (self.root / 'target.synthetic').write_bytes(b'changed-size')
        self.refuse('target stat tuple drift')
