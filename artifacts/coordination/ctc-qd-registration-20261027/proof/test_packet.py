import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest import mock

ROOT = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ctc-qd-activation-prep/root')
PACKET = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ctc-qd-activation-prep/packet')
sys.path.insert(0, str(PACKET))
import registration_gate as gate
spec = importlib.util.spec_from_file_location('sweepfixtures', ROOT / 'tests/coordination/test_registration_sweep.py')
fixture = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)

class Packet(fixture.RegistrationSweepTests):
    def regenerate(self):
        super().regenerate()
        self.attach_fake_native_proofs()

    def attach_fake_native_proofs(self):
        # Synthetic receipt for binding tests only; not a native-validation claim.
        for rid, meta in self.cat['rows'].items():
            proof = {'schema': 'epyc.registration_native_validation.v1', 'recipe': meta['recipe'],
                     'anchors': meta['session']['anchors'], 'server': meta.get('server'),
                     'validator_source': 'synthetic-fixture-only'}
            if meta.get('server'):
                custody = self.base / ('custody-' + rid + '.txt'); custody.write_text('synthetic owner custody')
                proof['server_custody'] = {'path': str(custody), 'sha256': gate.sha_bytes(custody.read_bytes())}
            meta['native_validation'] = self.ref('proof-' + rid + '.json', proof)

    def ds41(self):
        result = super().ds41()
        self.attach_fake_native_proofs()
        return result

    def setUp(self):
        super().setUp()
        self.a[0] = 'codex-ni-old'
        self.b[17] = 'requested_window_s=900; est_output_GiB=0; scratch_root=/mnt/raid0/llm/tmp; claimed_cpus=0-23'
        self.regenerate()
        self.base.joinpath('FILLERS.md').write_text(self.table([self.a]))
        self.base.joinpath('ws58-quarters-20261027.queue').write_text('')
        self.base.joinpath('ws58-quarters-20261027.queue.done').write_text('')
        self.run_script('initialize_legacy.py', str(self.base))
        self.candidate.write_text(self.table([self.b]))
        self.meta = self.base / 'meta.json'

    def run_script(self, name, *args, env=None, expected=0):
        proc = subprocess.run([sys.executable, str(PACKET / name), *args], env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        return proc

    def register_proc(self, expected=0):
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        env = dict(os.environ, CTCQD_FLAGS=str(self.base))
        return self.run_script('ws58_register_row.py', 'new', str(self.candidate), '123', '900', '4', '0-23', str(self.meta), env=env, expected=expected)

    def test_register_known_match_resolution_and_revalidation(self):
        (self.base / gate.CAT).write_text(json.dumps({'schema': gate.sweep.SCHEMA, 'rows': {'codex-ni-old': self.cat['rows']['codex-ni-old']}}))
        self.register_proc(expected=2)
        self.assertNotIn('new', gate.sweep.rows(self.base / 'FILLERS.md')[1])
        self.cat['rows']['new']['resolutions'] = {'codex-ni-old': {'action': 'separate', 'reason': 'independent load required'}}
        self.register_proc()
        self.assertEqual(gate.grant(self.base, 'new')['matches'][0]['resolution']['action'], 'separate')
        cat = json.loads((self.base / gate.CAT).read_text())
        cat['rows']['new']['resolutions']['codex-ni-old']['reason'] = 'altered'
        (self.base / gate.CAT).write_text(json.dumps(cat))
        with self.assertRaises(gate.sweep.Invalid): gate.grant(self.base, 'new')

    def test_unknown_and_missing_receipt_do_not_bypass(self):
        self.register_proc()
        r = gate.grant(self.base, 'new')
        self.assertFalse(r['exhaustive'])
        self.assertEqual(r['unknown_legacy'][0]['row'], 'codex-ni-old')
        receipts = json.loads((self.base / gate.RECEIPTS).read_text()); del receipts['rows']['new']
        (self.base / gate.RECEIPTS).write_text(json.dumps(receipts))
        with self.assertRaises(gate.sweep.Invalid): gate.grant(self.base, 'new')
        self.assertTrue(gate.grant(self.base, 'codex-ni-old')['legacy_unbound'])
        (self.base / 'FILLERS.md').write_text(self.table([self.a[:-1] + ['changed'], self.b]))
        with self.assertRaises(gate.sweep.Invalid): gate.grant(self.base, 'codex-ni-old')

    def test_pending_refuses_grant_and_register(self):
        (self.base / gate.PENDING).write_text('{}')
        with self.assertRaises(gate.sweep.Invalid): gate.grant(self.base, 'codex-ni-old')
        self.register_proc(expected=2)

    def test_registrar_waits_for_competing_lease(self):
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        fd = os.open(self.base / '.publication.lock', os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        env = dict(os.environ, CTCQD_FLAGS=str(self.base))
        proc = subprocess.Popen([sys.executable, str(PACKET / 'ws58_register_row.py'), 'new', str(self.candidate), '123', '900', '4', '0-23', str(self.meta)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(.2); self.assertIsNone(proc.poll())
            self.assertNotIn('new', gate.sweep.rows(self.base / 'FILLERS.md')[1])
        finally:
            os.close(fd)
        out, err = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 0, (out, err))

    def test_native_catalog_producer(self):
        meta = self.cat['rows']['new']
        proc = self.run_script('catalog_entry.py', '--candidate', str(self.candidate), '--id', 'new', '--recipe', meta['recipe']['path'], '--session', meta['session']['id'], '--anchor', meta['session']['anchors'][0]['path'], '--native-validation', meta['native_validation']['path'])
        self.assertEqual(json.loads(proc.stdout), meta)
        (self.base / 'recipe.json').write_text('{}')
        self.run_script('catalog_entry.py', '--candidate', str(self.candidate), '--id', 'new', '--recipe', meta['recipe']['path'], '--session', meta['session']['id'], '--anchor', meta['session']['anchors'][0]['path'], '--native-validation', meta['native_validation']['path'], expected=2)

    def test_interrupted_publication_blocks_grants(self):
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        original = gate.atomic
        def crash(path, data):
            if path.name == gate.RECEIPTS: raise OSError('injected crash')
            return original(path, data)
        with mock.patch.object(gate, 'atomic', side_effect=crash):
            with self.assertRaises(OSError): gate.register(self.base, self.candidate, self.meta, '123', '900', '4', '0-23')
        self.assertTrue((self.base / gate.PENDING).exists())
        with self.assertRaises(gate.sweep.Invalid): gate.grant(self.base, 'codex-ni-old')
        self.run_script('recover_registration.py', str(self.base))
        self.assertFalse((self.base / gate.PENDING).exists())
        self.assertTrue(gate.grant(self.base, 'new')['allowed'])

    def test_gpu_registration_queue_shape(self):
        self.b[17] = 'requested_window_s=900; est_output_GiB=0; scratch_root=/mnt/raid0/llm/tmp; claimed_cpus=184-191'
        self.b[16] = 'gpu'; self.regenerate(); self.candidate.write_text(self.table([self.b]))
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        (self.base / 'ws58-gpu.queue').write_text('')
        (self.base / 'ws58-gpu.queue.held').write_text('new\n')
        env = dict(os.environ, CTCQD_FLAGS=str(self.base))
        self.run_script('ws58_register_row.py', 'new', str(self.candidate), '123', '900', '4', 'mi210_0,184-191', str(self.meta), 'gpu', '600', '^ *gpu-quiet', env=env)
        self.assertEqual((self.base / 'ws58-gpu.queue').read_text(), 'new|123|900|600|4|^ *gpu-quiet|mi210_0,184-191\n')
        self.assertEqual((self.base / 'ws58-gpu.queue.held').read_text(), '')
        self.assertTrue(gate.grant(self.base, 'new')['allowed'])

    def test_recovery_refuses_unexpected_generation(self):
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        original = gate.atomic
        def crash(path, data):
            if path.name == gate.RECEIPTS: raise OSError('injected crash')
            return original(path, data)
        with mock.patch.object(gate, 'atomic', side_effect=crash):
            with self.assertRaises(OSError): gate.register(self.base, self.candidate, self.meta, '123', '900', '4', '0-23')
        (self.base / 'ws58-quarters-20261027.queue').write_text('unrelated-change\n')
        self.run_script('recover_registration.py', str(self.base), expected=2)
        self.assertTrue((self.base / gate.PENDING).exists())

    def test_ds41_shared_native_join(self):
        self.ds41()
        self.base.joinpath('FILLERS.md').write_text(self.table([self.a]))
        self.candidate.write_text(self.table([self.b]))
        old = self.cat['rows']['codex-ni-old']; meta = self.cat['rows']['new']
        anchors = [[meta['session']['anchors'][0]['path'], meta['session']['anchors'][0]['sha256'], gate.sweep.digest(self.plan['anchor_identity'])]]
        meta['resolutions'] = {'codex-ni-old': {'action': 'join', 'session': meta['session']['id'], 'shared_load_sha256': meta['session']['load_sha256'], 'anchor_refs': anchors}}
        (self.base / gate.CAT).write_text(json.dumps({'schema': gate.sweep.SCHEMA, 'rows': {'codex-ni-old': old}}))
        self.register_proc()
        result = gate.grant(self.base, 'new')
        self.assertIn('same-DS41-server', result['matches'][0]['kinds'])
        self.assertEqual(result['matches'][0]['resolution']['action'], 'join')

    def test_candidate_snapshot_cannot_change_after_read(self):
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        original = gate.sweep.rows; reads = []
        def change_after_read(path):
            result = original(path)
            if Path(path) == self.candidate:
                reads.append(1)
                altered = self.b[:]; altered[14] = 'different decision'
                self.candidate.write_text(self.table([altered]))
            return result
        with mock.patch.object(gate.sweep, 'rows', side_effect=change_after_read):
            gate.register(self.base, self.candidate, self.meta, '123', '900', '4', '0-23')
        self.assertEqual(len(reads), 1)
        self.assertEqual(original(self.base/'FILLERS.md')[1]['new'], self.b)

    def test_invalid_queue_arguments_do_not_publish(self):
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        for window, gib, regions in [('oops', '4', '0-23'), ('900', '5', '0-23'), ('901', '4', '0-23'), ('900', '4', '24-47'), ('900', '4', 'bad')]:
            with self.subTest(window=window, gib=gib, regions=regions):
                with self.assertRaises((gate.sweep.Invalid, gate.dryrun.Refused)):
                    gate.register(self.base, self.candidate, self.meta, '123', window, gib, regions)
                self.assertFalse((self.base/gate.PENDING).exists())
                self.assertNotIn('new', gate.sweep.rows(self.base/'FILLERS.md')[1])

    def test_abort_restores_before_images_and_invalidates_old_generation(self):
        self.meta.write_text(json.dumps(self.cat['rows']['new']))
        before_row = (self.base/'FILLERS.md').read_bytes()
        before_queue = (self.base/'ws58-quarters-20261027.queue').read_bytes()
        before_done = (self.base/'ws58-quarters-20261027.queue.done').read_bytes()
        old_generation = gate.sha_bytes((self.base/gate.REGISTRY).read_bytes())
        original = gate.atomic
        def crash(path, data):
            if path.name == gate.RECEIPTS: raise OSError('injected crash')
            return original(path, data)
        with mock.patch.object(gate, 'atomic', side_effect=crash):
            with self.assertRaises(OSError): gate.register(self.base, self.candidate, self.meta, '123', '900', '4', '0-23')
        (self.base/'recipe.json').unlink()
        self.run_script('recover_registration.py', str(self.base), '--abort')
        self.assertEqual((self.base/'FILLERS.md').read_bytes(), before_row)
        self.assertEqual((self.base/'ws58-quarters-20261027.queue').read_bytes(), before_queue)
        self.assertEqual((self.base/'ws58-quarters-20261027.queue.done').read_bytes(), before_done)
        self.assertFalse((self.base/gate.CAT).exists())
        self.assertFalse((self.base/gate.RECEIPTS).exists())
        self.assertNotEqual(gate.sha_bytes((self.base/gate.REGISTRY).read_bytes()), old_generation)
        self.assertFalse((self.base/gate.PENDING).exists())

    def test_missing_native_evidence_candidate_refused_peer_unknown(self):
        meta=self.cat['rows']['new'].copy(); del meta['native_validation']
        self.meta.write_text(json.dumps(meta))
        with self.assertRaises(KeyError): gate.register(self.base, self.candidate, self.meta, '123', '900', '4', '0-23')
        self.assertFalse((self.base/gate.PENDING).exists())
        old=self.cat['rows']['codex-ni-old'].copy(); del old['native_validation']
        (self.base/gate.CAT).write_text(json.dumps({'schema': gate.sweep.SCHEMA, 'rows': {'codex-ni-old': old}}))
        self.register_proc()
        result=gate.grant(self.base, 'new')
        self.assertEqual(result['unknown_legacy'][0]['row'], 'codex-ni-old')
        self.assertFalse(result['exhaustive'])

    def test_active_and_dangling_grant_refuse_registration(self):
        grants=self.base/'grants'; grants.mkdir()
        path=grants/'new.grant'
        for dangling in (False, True):
            if dangling: path.symlink_to(grants/'missing-target')
            else: path.write_text('regions=0-23 start=x end=y\n')
            self.register_proc(expected=2)
            self.assertTrue(os.path.lexists(path))
            self.assertFalse((self.base/gate.PENDING).exists())
            self.assertNotIn('new', gate.sweep.rows(self.base/'FILLERS.md')[1])
            path.unlink()

if __name__ == '__main__':
    names = ['test_register_known_match_resolution_and_revalidation', 'test_unknown_and_missing_receipt_do_not_bypass', 'test_pending_refuses_grant_and_register', 'test_registrar_waits_for_competing_lease', 'test_native_catalog_producer', 'test_interrupted_publication_blocks_grants', 'test_gpu_registration_queue_shape', 'test_recovery_refuses_unexpected_generation', 'test_ds41_shared_native_join', 'test_candidate_snapshot_cannot_change_after_read', 'test_invalid_queue_arguments_do_not_publish', 'test_abort_restores_before_images_and_invalidates_old_generation', 'test_missing_native_evidence_candidate_refused_peer_unknown', 'test_active_and_dangling_grant_refuse_registration']
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Packet(name) for name in names))
    sys.exit(not result.wasSuccessful())
