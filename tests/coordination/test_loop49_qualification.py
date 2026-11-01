"""20 offline audit regressions. Retain every fixture; never unlink or rename.

These unit tests use tiny local fixtures and retained historical FILED bytes;
they do not run inference, require a compute grant, or produce a qualification
receipt or compute smoke. Set LOOP49_TEST_ARTIFACTS=<retained dir> so generated
test artifacts remain available for audit. Historical FILED bytes are copied
unchanged beside this test's receipt ledger.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/coordination'))
import qualify_launcher as q
import failed_run_rollup as filer
import filler_engine14 as engine

class AuditRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get('LOOP49_TEST_ARTIFACTS'):
            raise unittest.SkipTest('retained artifact root required')
        cls.art = Path(os.environ['LOOP49_TEST_ARTIFACTS']) / secrets.token_hex(8)
        cls.art.mkdir(parents=True, exist_ok=False)
        receipts = ROOT / 'tests/coordination/fixtures/loop49'
        cls.real_receipts = {}
        for entry in q.load(receipts / 'receipts.json'):
            filed = receipts / (entry['id'] + '.FILED')
            assert q.sha(filed) == entry['sha256']
            cls.real_receipts[entry['case']] = filed.read_bytes()

    def setUp(self):
        self.d = self.art / self.id().split('.')[-1]; self.d.mkdir()
        self.m = dict(id='real-row-id', requires_tools=['bash'], ports=[], shared_state=[], exclusive_class=None,
            window_s=600, min_window_s=60, items=2, tokens_per_item=1, n_ctx_required=32,
            est_output_GiB=0, gib=8, process_limit_GiB=6, claimed_cpus='any-cpu-quarter',
            regions='any-cpu-quarter', scratch_root=str(self.d))
        for key in ('launcher', 'job', 'qual_fixture', 'source_manifest', 'row'):
            path = self.d / key; path.write_text('# fixture\n'); self.m[key] = str(path)
        model_path = self.d / 'model'; model_path.write_text('model fixture bytes\n')
        Path(self.m['source_manifest']).write_text(f'{q.sha(model_path)}  {model_path.resolve()}\n')
        self.m['qualification_model'] = {
            'id': 'fixture-model', 'path': str(model_path), 'sha256': q.sha(model_path),
        }
        row_cells = [self.m['id'], 'refactor', self.m['launcher'], self.m['regions'], '60 s', '8 GiB',
            str(self.d/'STOP'), 'READY', 'cpu', '600 s', '60 s', 'n', 'n', 'manifest.json', 'fixture',
            'n/a (fixture)', 'cpu', 'requested_window_s=600; est_output_GiB=0; scratch_root=%s; claimed_cpus=any-cpu-quarter; process_limit_GiB=6' % self.d]
        Path(self.m['row']).write_text('| ' + ' | '.join(row_cells) + ' |\n')
        self.m['engine'] = str(q.HERE / 'filler_run14.sh')
        self.allow = self.d / 'allow.json'
        q.create(self.allow, {'kind':'epyc.engine-allowlist.v1','engines':[q.sha(self.m['engine'])]})
        self.policy = self.d / 'policy.json'
        q.create(self.policy, dict(interim_until_utc='2000-01-01T00:00Z', interim_floor_gib=150, normal_floor_gib=150))
        self.qual_root = self.d / 'qual' / ('a' * 32)
        self.results = self.qual_root / 'results'; self.results.mkdir(parents=True)
        self.result = self.results / 'result.json'; q.create(self.result, {'native': True})
        self.first_request_path = self.results / 'first-request.json'
        self.grants = self.qual_root / 'grants'; self.grants.mkdir()
        self.grant = self.grants / (self.m['id'] + '.grant')
        self.grant.write_text('synthetic qualification grant marker\n')
        self.rc75_ended = self.grants / (self.m['id'] + '.deadline.ended')
        self.rc75_ended.write_text(
            'rc=75 time=2026-11-01T00:00:00Z reason=fixture-deadline\n'
            'partial=true\nnative_complete=false\nphase=qualification\ngranted=true\n')
        self.launcher_ended = self.grants / (self.m['id'] + '.ended')
        self.launcher_ended.write_text(
            'rc=0 time=2026-11-01T00:00:00Z reason=qualification-complete\n'
            'partial=false\nnative_complete=false\nphase=qualification\ngranted=true\n')
        self.p = dict(admission={'rc':0,'affinity_ok':True},completion={'complete_cmd_present':True,'is_complete_rc':0},
            rc75={'exit_code':75,'partial_flag':True, 'ended_path':str(self.rc75_ended),
                  'ended_line_sha256':q.sha(self.rc75_ended)},
            launcher_terminal={'path':str(self.launcher_ended), 'sha256':q.sha(self.launcher_ended)},
            disk={'job_floor_gib':150,'policy_floor_gib':150},children_drained=True,
            first_request={'ok':True,'n_ctx':32,'prompt_tokens':1,'measured_tok_s':10},
            result_writer={'ok':True,'result_path':str(self.result.resolve()),'sha256':q.sha(self.result)},
            exec_namespace={'tools':{'bash':'/usr/bin/bash'}}, nonce=self.qual_root.name,
            qualification_root=str(self.qual_root))
        self.refresh_native_record()

    def static(self):
        with patch.object(q, 'checked_manifest', return_value='fixture'), patch.dict(os.environ, {'WS58_ROOT': str(ROOT)}):
            return q.static_check(self.m, self.allow)

    def refresh_native_record(self):
        f = self.p['first_request']
        f['native_record'] = {
            'record_kind': 'epyc.qual.native-first-request.v1',
            'provenance': 'native-runtime',
            'source_manifest_sha256': q.sha(self.m['source_manifest']),
            'model_id': self.m['qualification_model']['id'],
            'model_sha256': self.m['qualification_model']['sha256'],
            'result_path': str(self.result.resolve()),
            'result_sha256': q.sha(self.result),
        }
        self.first_request_path.write_text(json.dumps(f, sort_keys=True) + '\n')
        self.p['first_request_record'] = {
            'record_kind': f['native_record']['record_kind'],
            'path': str(self.first_request_path.resolve()),
            'sha256': q.sha(self.first_request_path),
        }

    def evidence(self):
        self.refresh_native_record()
        self.p['rc75']['ended_line_sha256'] = q.sha(self.rc75_ended)
        self.p['launcher_terminal']['sha256'] = q.sha(self.launcher_ended)
        return q.evidence_check(self.m, self.p, self.policy)

    def filed(self, case):
        """Return the retained historical filing bytes, never a reconstructed receipt."""
        return self.real_receipts[case]

    def launch(self, extra, env=None):
        args = ['bash',str(q.HERE/'filler_run14.sh'),'--id',self.m['id'],'--cmd','true','--stop',str(self.d/'STOP'),
                '--workdir',str(self.d),*extra]
        e = dict(os.environ,FILLER_GRANTS_DIR=str(self.d/'grants'),FILLER_FLAGS_DIR=str(self.d))
        if env: e.update(env)
        proc = subprocess.run(args,env=e,capture_output=True,text=True,timeout=5)
        (self.d/'launcher.stdout').write_text(proc.stdout); (self.d/'launcher.stderr').write_text(proc.stderr)
        return proc

    def test_T01_paw_host_region_lock_missing(self):
        self.assertIn(b'host region-lock absent', self.filed('T1'))
        self.p['exec_namespace']['tools']['region-lock'] = None
        self.m['requires_tools'].append('region-lock')
        with self.assertRaisesRegex(q.Refused,'tool-missing'): self.evidence()

    def test_T02_gpu_build_complete_cmd_missing(self):
        self.assertIn(b'outer completion predicate', self.filed('T2'))
        proc=self.launch([])
        self.assertEqual(proc.returncode,65)
        self.assertIn('complete-cmd-missing',(self.d/'grants/real-row-id.ended').read_text())
        self.assertFalse((self.d/'grants/real-row-id.grant').exists())

    def test_T03_akxall8_rg_missing(self):
        self.assertIn(b'host rg absent', self.filed('T3'))
        self.m['requires_tools']=['rg']
        with self.assertRaisesRegex(q.Refused,'tool-missing'): self.evidence()

    def test_T04_ufh12_relocatable_fixed_cpus(self):
        self.assertIn(b'granted72-95-vs-declared24-47', self.filed('T4'))
        self.m['claimed_cpus']='24-47'
        with self.assertRaisesRegex(q.Refused,'relocatable-with-fixed-cpus'): self.static()

    def test_T05_hsf5p_wrong_affinity(self):
        self.assertIn(b'affinity mismatch', self.filed('T5'))
        self.p['admission']['affinity_ok']=False
        with self.assertRaisesRegex(q.Refused,'affinity'): self.evidence()

    def test_T06_yarn_infeasible_window(self):
        self.assertIn(b'128k', self.filed('T6'))
        self.m.update(items=120,tokens_per_item=131072,window_s=28800)
        self.p['first_request'].update(prompt_tokens=131072,measured_tok_s=3.7)
        with self.assertRaisesRegex(q.Refused,'infeasible-window'): self.evidence()

    def test_T07_hil15_deadline_rc1(self):
        self.assertIn(b'FAILED-RUN', self.filed('T7'))
        self.p['rc75']['exit_code']=1
        with self.assertRaisesRegex(q.Refused,'rc75'): self.evidence()

    def test_T08_inf75_job_floor151(self):
        self.assertIn(b'151GiB', self.filed('T8'))
        self.p['disk']['job_floor_gib']=151
        with self.assertRaisesRegex(q.Refused,'disk-floor-mismatch'): self.evidence()

    def test_T09_hil15_disk_wait_never_granted(self):
        self.assertIn(b'disk-floor', self.filed('T9'))
        self.assertEqual(q.scheduling_state(self.m,[],149.23,self.policy),'READY-WAIT-DISK')
        self.assertFalse((self.d/'grants').exists())
        r=filer.classify(dict(root_cause_family='C',state='READY-WAIT-DISK',rc=0,granted=False,compute_burned=False))
        self.assertNotIn('qualified_science_run', r); self.assertNotIn('science_score', r)

    def test_T10_yarn_stale_real_id_path(self):
        self.assertIn(b'frozen-cohort-path-changed', self.filed('T10'))
        launch=self.d/'stale-launch.sh'; launch.write_text('test "$WS58_QUAL_NONCE" = predecessor-id || exit 70\n')
        rc=q.invoke(launch,self.d,dict(os.environ,WS58_QUAL_NONCE='real-row-id'),3,self.d/'stale.log')
        self.assertEqual(rc,70)

    def test_T11_dtap_port_overlap(self):
        self.assertIn(b'port-18991', self.filed('T11'))
        self.m['ports']=[18991]
        self.assertEqual(q.scheduling_state(self.m,[dict(ports=[18991],shared_state=[],exclusive_class=None)],1000,self.policy),'READY-SKIP port-overlap')

    def test_T12_lb49_ds41_exclusive(self):
        self.assertIn(b'live DS41 server', self.filed('T12'))
        self.m['exclusive_class']='ds41'
        self.assertEqual(q.scheduling_state(self.m,[dict(ports=[],shared_state=[],exclusive_class='ds41')],1000,self.policy),'READY-SKIP exclusive-class')

    def test_T13_inf50_gitnexus_shared_state(self):
        self.assertIn(b'GitNexus', self.filed('T13'))
        self.m['shared_state']=['~/.gitnexus']
        self.assertEqual(q.scheduling_state(self.m,[dict(ports=[],shared_state=['~/.gitnexus'],exclusive_class=None)],1000,self.policy),'READY-SKIP shared-state')

    def test_T14_inf12_smoke_only_expected_cpus(self):
        self.assertIn(b'expected_cpus: unbound variable', self.filed('T14'))
        launch=self.d/'smoke-branch.sh'; launch.write_text('set -u\nif [ "${G2_MODE:-}" = smoke ]; then expected_cpus=1; fi\necho "$expected_cpus"\n')
        self.assertNotEqual(q.invoke(launch,self.d,dict(os.environ,WS58_QUAL='1'),3,self.d/'branch.log'),0)

    def test_T15_hil15_real_argv_rejected(self):
        self.assertIn(b'host boot rejects forwarded --job', self.filed('T15'))
        launch=self.d/'argv.sh'; launch.write_text('set -- --job packet\n[ "$#" = 1 ] || exit 64\n')
        self.assertEqual(q.invoke(launch,self.d,dict(os.environ,WS58_QUAL='1'),3,self.d/'argv.log'),64)

    def test_T16_jetlong_ctx32768(self):
        self.assertIn(b'32768 slot', self.filed('T16'))
        self.m['n_ctx_required']=130000; self.p['first_request']['n_ctx']=32768
        with self.assertRaisesRegex(q.Refused,'n_ctx'): self.evidence()

    def test_T17_inf50_retains_results_and_nonce_outputs(self):
        self.assertIn(b'results directory', self.filed('T17'))
        real=self.d/'results'; real.mkdir(); (real/'retained.json').write_text('native')
        nonce=self.d/'qual'/'nonce'/'results'; nonce.mkdir(parents=True); q.create(nonce/'result.json',{'fixture':True})
        self.evidence()
        self.assertEqual((real/'retained.json').read_text(),'native')
        self.assertEqual(list(real.iterdir()),[real/'retained.json'])
        with self.assertRaises(FileExistsError): q.create(nonce/'result.json',{'overwrite':True})

    def test_T18_identity_validator_failed_native_retained(self):
        self.assertIn(b'nativePASS-preserved', self.filed('T18'))
        r=filer.classify(dict(root_cause_family='B',rc=1,native_complete=True,validator_rc=1,granted=True))
        self.assertEqual(r['outcome'],'VALIDATOR-FAILED'); self.assertTrue(r['retain_native_output'])
        proc=subprocess.run([sys.executable,str(q.HERE/'failed_run_rollup.py'),'--workdir',str(self.d),'--validate-only',sys.executable,'-c','raise RuntimeError("validator")'],capture_output=True)
        self.assertNotEqual(proc.returncode,0); self.assertTrue(self.result.is_file())

    def test_D2_science_quota_counts_qualified_diagnostic_verdict_and_failed_grant(self):
        diagnostic = filer.classify(dict(root_cause_family='I', phase='production', rc=0,
            diagnostic_result=True, qualified=True, granted=True, science_score=999, qualified_science_run=True, verdict='diagnostic verdict: source defect confirmed'))
        self.assertEqual(diagnostic['outcome'], 'DIAGNOSTIC-RESULT')
        self.assertNotIn('qualified_science_run', diagnostic)
        self.assertNotIn('science_score', diagnostic)
        failed = filer.classify(dict(root_cause_family='A', phase='production', rc=127,
            granted=True, qualified=False))
        self.assertNotIn('science_score', failed)
        partial_no_verdict = filer.classify(dict(root_cause_family='E', phase='production', rc=75,
            partial=True, granted=True, qualified=True, verdict=None))
        self.assertNotIn('qualified_science_run', partial_no_verdict)
        self.assertNotIn('science_score', partial_no_verdict)

    def sealed_receipt(self):
        p=copy.deepcopy(self.p)
        binding=q.hashes(self.m,self.policy)
        p.update(binding,kind='epyc.qual.pass.v1',id=self.m['id'],nonce='a'*32,
                 ran_at=datetime.now(timezone.utc).isoformat())
        p['receipt_sha256_excluding_self']=q.digest(p)
        store=self.d/'nonce-store'
        q.create(store/('a'*32+'.issued.json'),{'id':self.m['id'],'binding':binding})
        q.create(store/('a'*32+'.sealed.json'),{'id':self.m['id'],'receipt_sha256':p['receipt_sha256_excluding_self']})
        q.create(q.receipt_path(self.m),p)
        opts=argparse.Namespace(allowlist=self.allow,nonce_store=store,policy=self.policy,flags_dir=self.d,fingerprint_now=False)
        return p,opts

    def test_synthetic_retained_positive_quota_proof_chain(self):
        # Synthetic protocol fixture only: no benchmark or measurement claim.
        import science_quota as sq
        from datetime import timedelta
        self.m['owner'] = 'refactor'
        Path(self.m['source_manifest']).write_text('')
        self.refresh_native_record()
        Path(self.m['launcher']).write_text("printf '%s\\n' '{\"exec_namespace\": {\"tools\": {\"bash\": \"/usr/bin/bash\"}}}'\n")
        _, opts = self.sealed_receipt()
        manifests = self.d / 'manifests'; manifests.mkdir()
        q.create(manifests / 'manifest.json', self.m)
        terminals = self.d / 'production-grants'; terminals.mkdir()
        row_id = self.m['id']
        (terminals / (row_id + '.grant')).write_text('regions=q0 start=2026-11-01T00:00Z end=2026-11-01T01:00Z\n')
        engine.ended(terminals / (row_id + '.ended'), 0, 'complete', phase='production', owner='refactor')
        filings = self.d / 'filings'; filings.mkdir()
        now = datetime.now(timezone.utc)
        q.create(filings / (row_id + '.FILED'), dict(id=row_id, outcome='COMPLETE',
                 verdict='synthetic-protocol-fixture', filed_at=now.isoformat()))
        rows = sq.collect_records(filings, terminals, manifests, nonce_store=str(opts.nonce_store),
                                  allowlist=str(self.allow), policy=str(self.policy), flags_dir=str(self.d))
        self.assertEqual(len(rows), 1)
        validated = sq.validate(rows[0])
        self.assertTrue(validated['_qualification_valid'], validated['_qualification_reason'])
        self.assertEqual(sq.score(validated), 1)
        self.assertEqual(sq.summarize(rows, datetime.now(timezone.utc), timedelta(hours=24))['owners']['refactor']['science_score'], 1)

    def test_T19_filed_disk_refusal_cannot_be_recast_as_pass(self):
        filed = self.filed('T9')
        self.assertIn(b'disk-floor', filed)
        original, opts = self.sealed_receipt()
        self.assertEqual(q.verify(self.m, opts), original)
        receipt = q.receipt_path(self.m)
        # The original filing is a failed run, not a qualification receipt. It
        # cannot replace or mutate the canonical sealed pass artifact.
        before = receipt.read_bytes()
        self.assertNotIn(b'epyc.qual.pass.v1', filed)
        self.assertEqual(receipt.read_bytes(), before)
        edited = copy.deepcopy(original)
        edited['completion']['is_complete_rc'] = 9
        real_load = q.load
        def read(path):
            return edited if Path(path) == receipt else real_load(path)
        with patch.object(q, 'checked_manifest', return_value='fixture'), patch.object(q, 'load', side_effect=read):
            with self.assertRaisesRegex(q.Refused, 'receipt-integrity'):
                q.verify(self.m, opts)
        self.assertEqual(receipt.read_bytes(), before)

    def test_T20_real_filing_and_launcher_fingerprint_tamper_are_rejected(self):
        filed = self.filed('T18')
        self.assertIn(b'nativePASS-preserved', filed)
        original,opts=self.sealed_receipt()
        self.assertEqual(q.verify(self.m, opts), original)
        # Fingerprinting executes only a tiny fixture launcher; no workload or
        # model is launched. Verification then rejects namespace drift.
        fp = self.d / 'fingerprint.sh'
        record = json.dumps({'exec_namespace': self.p['exec_namespace']}, separators=(',', ':'))
        fp.write_text('printf \'%s\\n\' ' + repr(record) + '\n')
        self.assertEqual(q.fingerprint(fp, self.d), self.p['exec_namespace'])
        opts.fingerprint_now = True
        with patch.object(q, 'checked_manifest', return_value='fixture'):
            with patch.object(q, 'fingerprint', return_value=self.p['exec_namespace']):
                self.assertEqual(q.verify(self.m, opts), original)
            with patch.object(q, 'fingerprint', return_value={'cwd':'changed'}):
                with self.assertRaisesRegex(q.Refused, 'namespace-stale'):
                    q.verify(self.m, opts)

        # Dead-launcher recovery checks PID birth before writing. A live PID
        # with its actual birth is refused; a missing PID is filed once only.
        identity = self.grants / 'dead.launcher.json'; ended = self.grants / 'dead.ended'
        identity.write_text(json.dumps({'pid':os.getpid(),'birth':engine.birth(os.getpid()),
            'id':'dead','phase':'qualification','grants_dir':str(self.grants.resolve())}))
        with self.assertRaisesRegex(ValueError, 'launcher-still-alive'):
            filer.record_launcher_dead(identity, ended)
        identity.write_text(json.dumps({'pid':2147483647,'birth':'1','id':'dead',
            'phase':'qualification','grants_dir':str(self.grants.resolve())}))
        filed = self.filed('T15')
        self.assertIn(b'--job', filed)
        filer.record_launcher_dead(identity, ended)
        first = ended.read_bytes()
        self.assertIn(b'launcher-dead:', first)
        with self.assertRaises(FileExistsError): filer.record_launcher_dead(identity, ended)
        self.assertEqual(ended.read_bytes(), first)

        # Production recovery charges only the owner bound by the verified
        # manifest and receipt; an edited identity owner fails closed.
        production_id = 'dead-production'
        manifest_path = self.d / 'manifest.json'
        production_manifest = dict(self.m, id=production_id, owner='refactor')
        manifest_path.write_text(json.dumps(production_manifest))
        production_identity = self.grants / (production_id + '.launcher.json')
        production_ended = self.grants / (production_id + '.ended')
        identity_payload = {
            'pid':2147483647, 'birth':'1', 'id':production_id, 'phase':'production',
            'grants_dir':str(self.grants.resolve()), 'owner':'forged-owner',
            'manifest_path':str(manifest_path), 'nonce_store':str(self.d/'nonce-store'),
            'allowlist_path':str(self.allow), 'policy_path':str(self.policy),
            'flags_dir':str(self.d),
        }
        production_identity.write_text(json.dumps(identity_payload))
        identity_payload.pop('owner')
        production_identity.write_text(json.dumps(identity_payload))
        with self.assertRaisesRegex(ValueError, 'owner-proof-missing'):
            filer.record_launcher_dead(production_identity, production_ended)
        identity_payload['owner'] = 'forged-owner'
        production_identity.write_text(json.dumps(identity_payload))
        with self.assertRaisesRegex(ValueError, 'owner-binding-mismatch'):
            filer.record_launcher_dead(production_identity, production_ended)
        self.assertFalse(production_ended.exists())
        identity_payload['owner'] = 'refactor'
        production_identity.write_text(json.dumps(identity_payload))
        (self.grants / (production_id + '.grant')).write_text(
            'regions=q0 start=2026-11-01T00:00Z end=2026-11-01T01:00Z\n')
        with patch.object(q, 'verify', return_value={'id':production_id}), patch.dict(os.environ, {}, clear=True):
            filer.record_launcher_dead(production_identity, production_ended)
        production_terminal = production_ended.read_text()
        self.assertIn('phase=production\ngranted=true\n', production_terminal)
        self.assertIn('owner=refactor\n', production_terminal)

        # Confirm an actual launcher edit invalidates the issued file binding.
        Path(self.m['launcher']).write_text('changed launcher\n')
        opts.fingerprint_now = False
        with patch.object(q,'checked_manifest',return_value='fixture'):
            with self.assertRaisesRegex(q.Refused,'issued-binding-stale'): q.verify(self.m,opts)

if __name__ == '__main__': unittest.main()
