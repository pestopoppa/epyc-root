"""Prospective source fixtures only; no server, model, hardware or live ledger."""
import hashlib
import json
from pathlib import Path
import unittest
from types import SimpleNamespace

from autokernel import census_capture as capture
from adapters import autokernel_census as adapter
from claim_tuple import ProjectionError
from test_autokernel_census_adapter import CensusCaptureTest


class CpuServerTest(unittest.TestCase):
    def fixture(self, *, tensor_width=5, actual_mask='48', grant_region='48-71', draft_counter=True):
        base = CensusCaptureTest('test_projection_and_grade')
        base.setUp()
        self.addCleanup(base.doCleanups)
        r,p = base.root,base.paths
        for name,body in [('libggml-cpu.so','cpu fixture'),('instrument_library','fixture instrument'),
                          ('requests',json.dumps([{'speculative.n_max':4}]))]:
            q=r/name; q.write_text(body); p[name]=str(q)
        Path(p['grant']).write_text(f'regions={grant_region} start=1970-01-01T00:00Z end=1970-01-01T00:02Z\n')
        Path(p['build_complete']).write_text(f"BUILD_COMPLETE source={'a'*40} kind=cpu end=1970-01-01T00:00:00Z no-model-runs=true\n")
        Path(p['elf_manifest']).write_text(''.join(f'{capture.file_sha256(Path(p[n]))}  {p[n]}\n'
                                                 for n in ('binary','libggml-cpu.so')))
        workload={'id':'cpu-server-fixture','model':p['model'],'expected_ops':['MUL_MAT'],
                  'request_files':{'verify':p['requests']}}
        Path(p['recipe']).write_text(json.dumps({'kernel_commit':'a'*40,'workloads':[workload]}))
        Path(p['binding']).write_text(json.dumps({'recipes_sha256':capture.file_sha256(Path(p['recipe']))}))
        shape={'phase':'verify','n_tokens':4,'n_seq':1}
        argv=['numactl','--interleave=2','--',p['binary'],'-m',p['model'],'-np','1']
        startup=f"CENSUS_MODEL model=0x1 path={p['model']}\nllama_context: n_seq_max = 1\nllama_context: n_ubatch = 512\n"
        phase='slot operator(): id 0 | task 1 | new prompt, task.n_tokens = 21\n'
        phase+='slot accept(): id 0 | task 1 | accepted 2/4 draft tokens\n'
        phase+='CENSUS_API_BEGIN id=1 ctx=0x2 tokens=5 scope=api_batch seq_ids=0,0,0,0,0,\n'
        phase+='CENSUS_GRAPH gid=1 id=1 ctx=0x2 model=0x1 nodes=1001 rc=0\n'
        phase+=''.join(f'CENSUS_NODE gid=1 id=1 ctx=0x2 model=0x1 node={i} op=MUL_MAT backend=CPU dst_type=0 ne=16,5,1,1 src0_type=0 src0_ne=32,16,1,1 src1_type=0 src1_ne=32,{tensor_width},1,1\n' for i in range(1001))
        phase+='CENSUS_API_END id=1 ctx=0x2 rc=0\n'
        log=r/'server.log'; log.write_text(startup+phase)
        cpu,shim=p['libggml-cpu.so'],p['instrument_library']
        samples=[{'utc_ns':t,'pid':123,'phase':'requests','task_affinity':{'1':actual_mask},
                  'loaded_ggml':[cpu],'loaded_instrument':[shim],
                  'slots':[{'id':0,'is_processing':True}],'own_vram_bytes':None,
                  'global_vram_bytes':None,'kfd_processes':None} for t in (2_000_000_000,3_000_000_000)]
        env={'PATH':'/fixture','FILLER_CPUS':'48-71','GGML_SCHED_DEBUG':'2','LD_PRELOAD':shim}
        inputs={k:v for k,v in p.items() if k!='libggml-hip.so' and k!='libggml-cpu.so'}
        journal=r/'server.capture.jsonl'
        capture.begin(journal,attempt_id='cpu',started_ns=1_000_000_000,argv=argv,env=env,shape=shape,
                      grant=Path(p['grant']).read_text(),deadline='30',kernel_commit='a'*40,inputs=inputs)
        capture.finish(journal,attempt_id='cpu',ended_ns=4_000_000_000,rc=0,error='',samples=samples,
            log=str(log),loaded_dsos={'cpu':cpu,'instrument':shim},spawned_ns=1_500_000_000,
            loaded_before={x:capture.file_identity(Path(x)) for x in (cpu,shim)})
        requests=json.loads(Path(p['requests']).read_text())
        timings={'predicted_n':8}
        if draft_counter: timings['draft_n']=4
        responses=[{'stop':True,'timings':timings}]
        graph=adapter.graph_evidence(startup+phase,phase,p['model'])
        evidence=adapter.shape_evidence(SimpleNamespace(**shape),startup,phase,requests,responses,samples)
        evidence['guards']['native_tensor_width_and_api_sequences']=adapter.tensor_shape_observed(SimpleNamespace(**shape),graph)
        evidence['guards']['native_instrument_mapping']=True
        evidence['observed']=all(evidence['guards'].values())
        request_log=r/'requests.native.json'
        request_log.write_text(json.dumps({'requests':requests,'responses':responses,'samples':samples,
                                           'phase_log_byte_offset':len(startup.encode())}))
        row={**graph,'shape':shape,'argv':argv,'rc':0,'state':'OBSERVED','instrument':'server',
             'device_seen':False,'phase_log_byte_offset':len(startup.encode()),
             'native_shape_evidence':evidence,'request_log':str(request_log),
             'request_log_sha256':capture.file_sha256(request_log)}
        identity={'workload_id':workload['id'],'backend':'cpu','claim_cpus':'48-71',
            'model':{'path':p['model'],'sha256':capture.file_sha256(Path(p['model']))},
            'kernel':{'commit':'a'*40,'binary_sha256':capture.file_sha256(Path(p['binary']))},
            'recipe':workload,'env':{'FILLER_CPUS':'48-71'}}
        record=r/'server.record.json'
        record.write_text(json.dumps({'schema':'epyc.autokernel.workload_census.v1','identity':identity,
            'graph':{'shape_envelope':[shape],'per_shape':[row]},'validity':{'state':'OBSERVED',
            'observed':True,'freshness_key':hashlib.sha256(capture.canonical(identity)).hexdigest()}}))
        sidecar=r/'server.belief.jsonl'
        capture.seal_record(sidecar,record=record,journals=[journal])
        return sidecar

    def test_cpu_server_projects_actual_tensor_evidence_and_narrow_pinning(self):
        rows=adapter.native_rows(self.fixture())
        claim=adapter.project(rows[0])
        self.assertEqual(claim.value,1)
        self.assertEqual(claim.applicability['backend'],'cpu')
        self.assertEqual(rows[0]['row']['matmul_src1_shapes'],[[32,5,1,1]])

    def test_resealed_wrong_tensor_width_or_missing_draft_counter_refuses(self):
        for kwargs in ({'tensor_width':6},{'draft_counter':False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ProjectionError):
                adapter.native_rows(self.fixture(**kwargs))

    def test_outside_or_empty_mask_and_wrong_cpu_grant_refuse(self):
        for kwargs in ({'actual_mask':'48,72'},{'actual_mask':''},{'grant_region':'24-47'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ProjectionError):
                adapter.native_rows(self.fixture(**kwargs))


if __name__=='__main__': unittest.main()
