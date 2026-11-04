import copy
import datetime as dt
import hashlib
import os
import json
from pathlib import Path
import tempfile
import unittest
from capture_writer import write_case, _stat
from test_capture_records import make_arm

class CaptureWriterTest(unittest.TestCase):
    def test_custody_and_fail_closed_controls(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);root=d/'grants';root.mkdir();now=dt.datetime.now(dt.timezone.utc)
            grant=root/'case1.grant';grant.write_text('regions=0-23 start='+ (now-dt.timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ')+' end='+ (now+dt.timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%MZ')+' holds=build\n')
            paths={}
            for name in ('receipt','compiler','compiler_meta','candidate','source_code','bridge','source_patch','prompt_manifest','runtime_manifest','lib','model'):
                p=d/name;p.write_bytes(name.encode());paths[name]=p
            entry=lambda name:{'path':str(paths[name]),'sha256':hashlib.sha256(name.encode()).hexdigest()}
            paths['compiler_meta'].write_text('CMAKE_CXX_COMPILER:FILEPATH='+str(paths['compiler'])+'\n')
            model=dict(entry('model'),stat=_stat(paths['model']),hash_mode='preflight-full-stat-bound')
            paths['prompt_manifest'].write_text(json.dumps({'model':{'path':model['path'],'sha256':model['sha256'],'stat':model['stat']},'prompts':[{}, {'ids':[10,11]}]}))
            actual=lambda name:{'path':str(paths[name]),'sha256':hashlib.sha256(paths[name].read_bytes()).hexdigest()}
            receipt={'source_commit':'ffc1bac82eeca6f9099e1ccd9ba49703c460a115','mode':'build','candidate_sha256':actual('source_code')['sha256'],'bridge_sha256':actual('bridge')['sha256'],'patch_sha256':actual('source_patch')['sha256'],'frozen_prompt_manifest_sha256':actual('prompt_manifest')['sha256'],'files':{'candidate':actual('candidate')['sha256'],'cache':actual('compiler_meta')['sha256']}}
            paths['receipt'].write_text(json.dumps(receipt))
            c={'row_id':'case1','phase':'official','device':'cpu','case_index':1,'sample_time':now.timestamp(),'pid':123,'pid_start_ticks':1,'affinity':[0,1], 'grant_path':str(grant),'model':model,'build':dict({k:actual(k) for k in ('receipt','compiler','compiler_meta','candidate','source_code','bridge','source_patch','prompt_manifest','runtime_manifest')},source_commit='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'),'argv':[str(paths['candidate']),str(paths['model']),'1'],'mapped_libraries':{str(paths['lib']):entry('lib')['sha256']},'model_mapped':True,'proc_maps_sha256':'a'*64,'child_rc':0,'child_reaped':True}
            def line(p):
                st=p.stat();return f'1000-2000 r--p 00000000 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {p.resolve()}\n'
            maps=d/'proc-maps';maps.write_text(''.join(line(paths[k]) for k in ('model','candidate','lib')))
            c['proc_maps_path']=str(maps);c['proc_maps_sha256']=hashlib.sha256(maps.read_bytes()).hexdigest()
            summary=('CAFE4_GEOMETRY_REFS prompt=1 off_batch_serial=0.001 off_ckpt_serial=0.001 off_batch_ckpt=0.001 observe_batch_serial=0.001 observe_ckpt_serial=0.001 observe_batch_ckpt=0.001\n'
                     'CAFE4_MTP_ROLLBACK width=3 accepted=1 selected=1 faulted=1 off_error=0 observe_error=0 fault_error=1 off_observe=0 fault_observe=1 tolerance=0.00101\n'
                     'RESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges\n')
            raw=(''.join(make_arm(i) for i in range(3))+summary).encode()
            got=write_case(d/'good',c,raw,root);self.assertEqual(got['capture_status'],'CAPTURED_UNGRADED');self.assertEqual(len(got['arms']),3)
            self.assertTrue((d/'good'/'fault.native.log').is_file());self.assertEqual(got['grant']['sha256'],hashlib.sha256(grant.read_bytes()).hexdigest())
            partial=write_case(d/'partial',c,raw.replace(b'faulted=1',b'faulted=',1),root);self.assertEqual(partial['capture_status'],'UNKNOWN');self.assertTrue((d/'partial'/'native.log').is_file())
            missing=copy.deepcopy(c);del missing['mapped_libraries'];self.assertEqual(write_case(d/'missing',missing,raw,root)['capture_status'],'UNKNOWN')
            failed=copy.deepcopy(c);failed['child_rc']=2;self.assertEqual(write_case(d/'failed',failed,raw,root)['capture_status'],'UNKNOWN')
            maps.write_text(maps.read_text()+'tampered\n');self.assertEqual(write_case(d/'maps-tamper',c,raw,root)['capture_status'],'UNKNOWN');maps.write_text(''.join(line(paths[k]) for k in ('model','candidate','lib')))
            paths['source_patch'].write_bytes(b'tampered');self.assertEqual(write_case(d/'tamper',c,raw,root)['capture_status'],'UNKNOWN')
            paths['source_patch'].write_bytes(b'source_patch');grant.write_text('regions=0-23 start=2026-01-01T00:00Z end=2027-01-01T00:00Z kind=rowflow-dryrun\n');self.assertEqual(write_case(d/'dryrun',c,raw,root)['capture_status'],'UNKNOWN')

if __name__=='__main__':unittest.main()
