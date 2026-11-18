"""Offline synthetic refusal controls; uses the local pinned AdaMAST git checkout."""
import base64
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import fm2_adamast as adapter
CHECKOUT = Path(os.environ.get('FM2_ADAMAST_CHECKOUT', '/mnt/raid0/llm/worktrees/rtg34-fm-20261110-scratch/adamast-upstream'))
REV = '3c83d81c85937f5e8911fd96daa2ca38c1ad2585'
def dump(path, obj): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(obj, sort_keys=True)+'\n')
def b64(obj): return base64.b64encode(json.dumps(obj).encode()).decode()

class FM2Test(unittest.TestCase):
    def setUp(self):
        if not CHECKOUT.exists(): self.skipTest('pinned AdaMAST checkout unavailable')
        scratch = Path('/mnt/raid0/llm/tmp/vidya-belief-substrate/fm2-current/tests')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.code = self.root/'code'; self.code.mkdir()
        archive = subprocess.check_output(['git','-C',str(CHECKOUT),'archive',REV,'adamast'])
        subprocess.run(['tar','-x','-C',str(self.code)],input=archive,check=True)
        subprocess.run(['git','apply',str(ROOT/'scripts/experiments/fm2-adamast/adamast_local.patch')],cwd=self.code,check=True)
        self.uid='synthetic-one'; self.unit=self.root/'out/units'/self.uid; self.unit.mkdir(parents=True)
        self.trace=self.root/'inputs/traces'/f'{self.uid}.jsonl'
        dump(self.trace, {'problem_id':self.uid,'task':'synthetic task','raw_trajectory':'synthetic trajectory','metadata':{'stratum':'claude|2026-10|main','source_sha256':'a'*64}})
        dump(self.code/'belief-selection.json', {'unit_ids':[self.uid]})
        # Generate both prompt and native diagnosis with the pinned judge, no model call.
        generator='''import json,sys\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom adamast.core.trace_formats import load_trace_bundle\nfrom adamast.judges.contract import SelectionTraceJudge\nclass P:\n model="local-fm2"\n def complete(self,prompt,*,response_format):\n  self.prompt=prompt\n  return '{"failure_modes":[],"none_apply":true}'\np=P(); j=SelectionTraceJudge(Path(sys.argv[1])/"adamast/core/mast.json",p,max_trace_chars=12000,max_retries=0); d=j.judge(load_trace_bundle(Path(sys.argv[2])).traces[0]).to_dict();print(json.dumps({"prompt":p.prompt,"diagnosis":d}))'''
        v=json.loads(subprocess.check_output([sys.executable,'-I','-c',generator,str(self.code),str(self.trace)]))
        req={'model':'local-fm2','messages':[{'role':'user','content':v['prompt']}], 'chat_template_kwargs':{'enable_thinking':False},'max_completion_tokens':1536}
        resp={'choices':[{'finish_reason':'stop','message':{'content':'{"failure_modes":[],"none_apply":true}'}}]}
        now=datetime.now(timezone.utc); self.start=now.isoformat(); self.end=(now+timedelta(minutes=10)).replace(second=0,microsecond=0)
        grant=f"regions=24-47 start={(now-timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ')} end={self.end.strftime('%Y-%m-%dT%H:%MZ')} holds=q1\n".encode()
        runtime={'grant_path':'/tmp/test.grant','grant_body_b64':base64.b64encode(grant).decode(),'grant_sha256':hashlib.sha256(grant).hexdigest(),'server_argv':['server'],'runtime_dsos':{'lib':'a'},'filler':{'FILLER_ID':'test','FILLER_END':str(int(self.end.timestamp()))}}
        files=sorted(p for d in ('code','inputs') for p in (self.root/d).rglob('*') if p.is_file() and '__pycache__' not in str(p))
        (self.root/'SOURCE.sha256').write_text(''.join(adapter.sha(p)+'  '+str(p.relative_to(self.root))+'\n' for p in files))
        runtime['packet_sha256']=adapter.sha(self.root/'SOURCE.sha256')
        begin={'schema':'epyc.fm2.belief-begin.v1','scope':'pilot','unit_id':self.uid,'started_at':self.start,'trace_sha256':adapter.sha(self.trace),'packet_sha256':runtime['packet_sha256'],'runtime':runtime}
        dump(self.unit/'belief-begin.json',begin)
        dump(self.unit/'request.json',{'method':'POST','url':'http://127.0.0.1:123/v1/chat/completions','sent_at':self.start,'body_b64':b64(req)})
        dump(self.unit/'response.json',{'status':200,'received_at':self.start,'body_b64':b64(resp)})
        dump(self.unit/'diagnosis.json',{'schema_version':2,'trace_count':1,'diagnoses':[v['diagnosis']]})
        self.row={'unit_id':self.uid,'scope':'pilot','status':'valid','ok':True,'runtime':runtime,'trace_sha256':adapter.sha(self.trace),'source_sha256':'a'*64,'stratum':'claude|2026-10|main','started_at':self.start,'finished_at':self.start,'max_trace_chars':12000,'max_output_tokens':1536,'artifacts':{}}
        self.seal()
    def seal(self):
        self.row['artifacts']={n:adapter.sha(self.unit/n) for n in ('request.json','response.json','diagnosis.json') if (self.unit/n).exists()}
        dump(self.unit/'receipt.json',self.row)
    def rows(self): return adapter.native_rows(self.unit/'receipt.json')
    def test_valid(self):
        self.assertEqual(len(self.rows()),1)
        cmd=[sys.executable, str(ROOT/'scripts/vidya/cli.py'), '--ledger', str(self.root/'cli-ledger.jsonl'),
             '--json', 'ingest', 'fm2-adamast', '--path', str(self.unit/'receipt.json'),
             '--as-of', datetime.now(timezone.utc).isoformat()]
        report=json.loads(subprocess.check_output(cmd))
        self.assertEqual((report['rows_projected'],report['frames_emitted'],report['refused']), (1,3,[]))
        if self.root.is_relative_to(Path('/mnt/raid0/llm/tmp')):
            subprocess.run([sys.executable, str(ROOT/'scripts/experiments/fm2-adamast/belief_canary.py'),
                            '--receipt', str(self.unit/'receipt.json'), '--scratch', str(self.root)],
                           check=True, capture_output=True, text=True)
    def test_resealed_diagnosis_mismatch(self):
        p=self.unit/'diagnosis.json'; d=json.loads(p.read_text()); d['diagnoses'][0]['failure_modes']=[{'code':'MAST-1','evidence':'fabricated','confidence':'high','severity':'major'}]; d['diagnoses'][0]['none_apply']=False; dump(p,d); self.seal()
        with self.assertRaises(adapter.ProjectionError): self.rows()
    def test_resealed_request_trace_mismatch(self):
        p=self.unit/'request.json'; r=json.loads(p.read_text()); b=json.loads(base64.b64decode(r['body_b64']));b['messages'][0]['content']+='wrong trace';r['body_b64']=b64(b);dump(p,r);self.seal()
        with self.assertRaises(adapter.ProjectionError): self.rows()
    def test_source_and_response_drift(self):
        self.trace.write_text('bad')
        with self.assertRaises(adapter.ProjectionError): self.rows()
        self.setUp(); (self.unit/'response.json').write_text('{}')
        with self.assertRaises(adapter.ProjectionError): self.rows()
    def test_missing_begin_and_failure_unknown(self):
        (self.unit/'belief-begin.json').unlink()
        with self.assertRaises(adapter.ProjectionError): self.rows()
        self.setUp(); self.row.update(ok=False,status='parse_or_schema_failure');self.seal();self.assertEqual(self.rows(),())
if __name__ == '__main__': unittest.main()
