import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
PACKET=BASE/'packet'
sys.path.insert(0,str(PACKET))
sys.path.insert(0,str(BASE/'rowflow'))
for name,attrs in {
    'server_probe_full':{'request':lambda *a,**k:None,'own_sample':lambda *a,**k:None,'ServerProbe':type('ServerProbe',(),{})},
    'affinity_scope':{'within':lambda *a,**k:True},
    'grant_guard':{'check_r11_smoke_admission':lambda *a,**k:None,'_logical_cpu_primary':lambda x:x},
    'golden_lifecycle':{'await_port_ready':lambda *a,**k:None,'wait_owned_health':lambda *a,**k:None,'stop_owned':lambda *a,**k:None},
}.items():
    module=types.ModuleType(name)
    for key,value in attrs.items():setattr(module,key,value)
    sys.modules[name]=module
import work
import enrollment
import rowflow
import publish_row

ROW='inf75-w5s-current-census-r7-20261031'
SHAPE={'phase':'prefill','n_tokens':2048,'n_seq':1}

def digest(raw): return hashlib.sha256(raw).hexdigest()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def signed_event(payload,previous=''):
    event={**payload,'schema':'epyc.autokernel.census_capture_event.v1','previous_sha256':previous}
    event['content_sha256']=digest(canonical(event))
    return event

def write_capture(path, payloads):
    rows=[]; prev=''
    for payload in payloads:
        row=signed_event(payload,prev); rows.append(row); prev=row['content_sha256']
    path.write_bytes(b''.join(canonical(row)+b'\n' for row in rows))
    return rows

def ref(path): return {'path':str(path.resolve()),'sha256':digest(path.read_bytes())}

class Inf75R7EvidenceTests(unittest.TestCase):
    def _fixture(self, root, bad=None):
        packet=root/'packet';packet.mkdir()
        flags=root/'flags';dry=flags/'dryrun'/ROW;attempt=dry/'native-attempts'/'attempt-unique';attempt.mkdir(parents=True)
        workroot=root/'work';native=workroot/'native-full';out=native/'out'/'2000';out.mkdir(parents=True)
        model='/test/model-00001.gguf'; binary='/test/llama-server'; requests=packet/'requests.json';requests.write_text('[{"prompt":"real request"}]\n')
        pins={'sources':{binary:'b'*64,str(requests):digest(requests.read_bytes())},'models':{model:{'sha256':'c'*64,'size':1}}}
        (packet/'source-pins.json').write_text(json.dumps(pins))
        recipe={'id':ROW,'kernel_commit':'kernel-commit','binary':binary,'model':model,'ordered_shards':[model],
                'request_files':{'prefill':str(requests)}}
        (packet/'recipes.json').write_text(json.dumps({'workloads':[recipe]}))
        nonce='a'*48; start_ns=1000
        (native/'entry-facts.json').write_text(json.dumps({'utc_ns':start_ns,'rowflow_run_nonce':nonce})+'\n')
        scope='recipe scope; rowflow dry-run first native prefill unit only; not a complete W5s census'
        record_identity={'workload_id':ROW+'-dryrun','rowflow_run_nonce':nonce,
            'kernel':{'commit':'kernel-commit','binary_sha256':'b'*64},
            'model':{'shards':[{'path':model,'sha256':'c'*64}]},'claim_cpus':'0-95',
            'recipe':{'id':ROW},'scope':scope}
        if bad=='identity': record_identity['workload_id']='other-workload'
        if bad=='source': record_identity['kernel']['binary_sha256']='f'*64
        shape=dict(SHAPE)
        if bad=='shape': shape['phase']='decode'
        validity_key=digest(json.dumps(record_identity,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode())
        record={'schema':'epyc.autokernel.workload_census.v1','identity':record_identity,'validity':{'state':'OBSERVED','freshness_key':validity_key},
                'graph':{'shape_envelope':[shape],'per_shape':[{'shape':shape,'state':'OBSERVED','nodes_total':100}]}}
        native_record=out/'native-record.json';native_raw=json.dumps(record,sort_keys=True).encode()+b'\n';native_record.write_bytes(native_raw)
        log=out/'prefill.log';log.write_text('native request and server response log\n')
        terminal_rc=1 if bad=='terminal' else 0
        grant=f'regions=0-95 start=2026-11-01T00:00Z end=2026-11-01T02:00Z holds=q0,q1,q2,q3 schema=epyc.rowflow.dryrun-grant.v1 id={ROW} kind=rowflow-dryrun admission_class=diagnostic\n'
        start_payload={'kind':'start','attempt_id':ROW+'-prefill','started_ns':1200,'shape':shape,'grant':grant,
            'inputs':{'requests':ref(requests)},'kernel_commit':'kernel-commit','deadline':'2026-11-01T01:59Z'}
        term_payload={'kind':'terminal','attempt_id':ROW+'-prefill','ended_ns':1500,'rc':terminal_rc,'error':'' if terminal_rc==0 else 'failed','log':ref(log)}
        journal=out/(ROW+'-prefill.capture.jsonl');events=write_capture(journal,[start_payload,term_payload])
        sidecar=out/'native-record.belief.jsonl'
        record_event={'kind':'record','record':ref(native_record),'attempts':{'attempt_0':ref(journal)}}
        write_capture(sidecar,[record_event])
        if bad=='request-digest': requests.write_text('[{"prompt":"changed after capture"}]\n')
        if bad=='journal-tamper': journal.write_text(journal.read_text().replace('1200','1300'))
        summary={'state':'OBSERVED','rowflow_dryrun':True,'dryrun_shape_count':1,'native_record':str(native_record),
            'native_run_id':'2000','rowflow_run_nonce':nonce,'entry_facts':str(native/'entry-facts.json'),'scope':scope,
            'native_record_sha256':digest(native_raw),'capture_sidecar':str(sidecar),'capture_sidecar_sha256':digest(sidecar.read_bytes())}
        summary_path=out/'SUMMARY.json';summary_path.write_text(json.dumps(summary)+'\n')
        if bad=='stale': (native/'entry-facts.json').write_text(json.dumps({'utc_ns':3000,'rowflow_run_nonce':nonce})+'\n')
        production=root/'LAST-RESULT.json';production.write_text('{"production":"unchanged"}\n')
        return packet,workroot,dry,attempt,native_record,production

    def _copy(self, root, bad=None):
        packet,workroot,dry,attempt,native_record,production=self._fixture(root,bad)
        with patch.object(work,'D',packet), patch.dict(os.environ,{'W3_WORK_ROOT':str(workroot),'FILLER_DRYRUN_DIR':str(dry)}):
            result=work.copy_native_dryrun_result(native_record.parent/'SUMMARY.json',attempt/'native-result.json')
        return result,attempt,production

    def test_candidate_row_contract_matches_current_estimate_window_and_launcher(self):
        p=PACKET; launcher=p/'launch.v15.sh'
        spec={'schema':'epyc.row.v3','id':ROW,'owner':'codex-ni','lane':'cpu','regions':'0-95',
            'estimate_s':5700,'min_window_s':5400,'window_s':7140,'gib':192,'scratch_root':str(p),'workdir':str(p),
            'stop_file':str(p/'STOP'),'result_path':str(p/'LAST-RESULT.json'),'result_format':'json',
            'dryrun_whole_host':True,'dryrun_native_result':True,'admission_class':'diagnostic',
            'launcher':{'path':str(launcher),'sha256':enrollment.sha(launcher)},
            'engine':{'path':str(enrollment.ROWFLOW_ENGINE),'sha256':enrollment.sha(enrollment.ROWFLOW_ENGINE)},
            'keep':['LAST-RESULT.json','BUILD-RECEIPT-PATH']}
        self.assertTrue(enrollment.validate_v3(spec))
        self.assertEqual(enrollment.expected_v3_window(5700,5400),7140)
        params=json.loads((BASE/'artifacts'/'row-contract-parameters.json').read_text())
        self.assertEqual((params['estimate_s'],params['min_window_s'],params['window_s']),(5700,5400,7140))
        self.assertEqual(params['launcher']['sha256'],spec['launcher']['sha256'])
        self.assertTrue(params['result_path'].endswith('/successor-r7/LAST-RESULT.json'))
        spec['estimate_s']=4500
        with self.assertRaises(ValueError):enrollment.validate_v3(spec)

    def test_repair_schema_preserves_optional_dryrun_native_result(self):
        self.assertIn('dryrun_native_result', publish_row.SPEC_KEYS)
        self.assertTrue(rowflow.publish.__name__ == 'publish')

    def test_unique_attempt_paths_do_not_share_production_result(self):
        with tempfile.TemporaryDirectory() as td:
            p1=rowflow.new_dryrun_native_result_path(td);p2=rowflow.new_dryrun_native_result_path(td)
            self.assertNotEqual(p1,p2)
            self.assertTrue(p1.endswith('/native-attempts/'+Path(p1).parent.name+'/native-result.json'))

    def test_native_record_and_request_capture_receipt_are_copied_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            result,attempt,production=self._copy(Path(td))
            self.assertEqual(Path(result['path']).read_bytes(),(production.parent/'work'/'native-full'/'out'/'2000'/'native-record.json').read_bytes())
            receipt=json.loads(Path(result['receipt_path']).read_text())
            self.assertEqual(receipt['request_capture_count'],1)
            self.assertEqual(receipt['request_evidence'][0]['native_log_sha256'],digest(b'native request and server response log\n'))
            self.assertEqual(production.read_text(),'{"production":"unchanged"}\n')

    def test_bad_native_identity_shape_request_hash_journal_or_freshness_fail_closed(self):
        for bad in ('identity','source','shape','request-digest','journal-tamper','terminal','stale'):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as td:
                packet,workroot,dry,attempt,native_record,production=self._fixture(Path(td),bad)
                with patch.object(work,'D',packet),patch.dict(os.environ,{'W3_WORK_ROOT':str(workroot),'FILLER_DRYRUN_DIR':str(dry)}):
                    with self.assertRaises(ValueError):work.copy_native_dryrun_result(native_record.parent/'SUMMARY.json',attempt/'native-result.json')
                self.assertFalse((attempt/'native-result.json').exists())
                self.assertEqual(production.read_text(),'{"production":"unchanged"}\n')

    def test_completion_predicate_binds_request_evidence_and_separates_production(self):
        checker=PACKET/'completion_check.py'
        launcher=(PACKET/'launch.v15.sh').read_text()
        self.assertIn('--complete-cmd "/usr/bin/python3 -B $D/completion_check.py"',launcher)

        def run_dryrun(mutation=None):
            td=tempfile.TemporaryDirectory();root=Path(td.name)
            packet,workroot,dry,attempt,native_record,production=self._fixture(root)
            dest=attempt/'native-result.json'
            with patch.object(work,'D',packet),patch.dict(os.environ,{'W3_WORK_ROOT':str(workroot),'FILLER_DRYRUN_DIR':str(dry)}):
                work.copy_native_dryrun_result(native_record.parent/'SUMMARY.json',dest)
            receipt_path=dest.with_name('native-result.receipt.json')
            receipt=json.loads(receipt_path.read_text())
            if mutation=='empty':receipt['request_evidence']=[];receipt['request_capture_count']=0
            elif mutation=='missing':receipt.pop('request_evidence')
            elif mutation=='bad-hash':receipt['request_evidence'][0]['journal_sha256']='0'*64
            receipt_path.write_text(json.dumps(receipt))
            if mutation=='request-content':Path(receipt['request_evidence'][0]['request_path']).write_text('tampered request')
            elif mutation=='journal-content':Path(receipt['request_evidence'][0]['journal_path']).write_text('tampered journal')
            elif mutation=='log-content':Path(receipt['request_evidence'][0]['native_log_path']).write_text('tampered log')
            elif mutation=='sidecar-content':Path(receipt['capture_sidecar_path']).write_text('tampered sidecar')
            local=packet/'completion_check.py'
            text=checker.read_text().replace("D = Path(__file__).resolve().parent",f"D = Path({str(packet)!r})")
            text=text.replace("NATIVE_ROOT = Path('/mnt/micron/codex-w5s-current-census-r7-20261031')",f"NATIVE_ROOT = Path({str(workroot)!r})")
            local.write_text(text)
            env=dict(os.environ,FILLER_DRYRUN='1',FILLER_DRYRUN_DIR=str(dry),FILLER_DRYRUN_RESULT_PATH=str(dest))
            proc=subprocess.run(['/usr/bin/python3',str(local)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            td.cleanup()
            return proc.returncode

        self.assertEqual(run_dryrun(),0)
        for mutation in ('empty','missing','bad-hash','request-content','journal-content','log-content','sidecar-content'):
            with self.subTest(mutation=mutation):self.assertNotEqual(run_dryrun(mutation),0)

        with tempfile.TemporaryDirectory() as td:
            root=Path(td);local=root/'completion_check.py'
            text=checker.read_text().replace("D = Path(__file__).resolve().parent",f"D = Path({str(root)!r})")
            text=text.replace("NATIVE_ROOT = Path('/mnt/micron/codex-w5s-current-census-r7-20261031')",f"NATIVE_ROOT = Path({str(root)!r})")
            local.write_text(text)
            (root/'LAST-RESULT.json').write_text(json.dumps({'rc':0,'first_request_ok':True,'result_writer_ok':True}))
            env=dict(os.environ,FILLER_DRYRUN='0')
            self.assertEqual(subprocess.run(['/usr/bin/python3',str(local)],env=env).returncode,0)

if __name__=='__main__':unittest.main()
