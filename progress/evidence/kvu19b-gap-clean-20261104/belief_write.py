"""Prospective native ClaimTuple carrier; no grading/projection or historical backfill."""
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
from claim_tuple import ClaimTuple

def write_child(run,row,assets,*,qualification,manifest_sha):
 if qualification:raise ValueError('qualification cannot emit full-comparison measurement')
 if row.get('rc')!=0 or not row.get('cleanup',{}).get('verified_dead') or not row.get('started_utc') or not row.get('completed_utc'):raise ValueError('unverified child cannot emit measurement')
 positive=[s for s in row.get('samples',[]) if s['own_vram_b']>0 and all(v for k,v in s['mapped_libraries'].items() if k.startswith('libggml'))]
 if len(positive)<2:raise ValueError('missing write-time live GPU warrant')
 for name in ('stdout','stderr'):
  if hashlib.sha256(Path(row[name]).read_bytes()).hexdigest()!=row.get('raw_sha256',{}).get(name):raise ValueError('raw native file digest mismatch: '+name)
 own=int(row['argv'][2]);steps=int(row['argv'][4])
 payload={'schema':'kvu19b-gap.child-warrant.v1','row':row,'assets':assets,'runtime_manifest_sha256':manifest_sha,'authored_at':datetime.now(timezone.utc).isoformat(),'scope':'synthetic p3batch model microbenchmark; not serving speed, causal attribution or parent closure'}
 native=Path(run)/f"child-{row['index']:02d}.json"
 with native.open('x') as f:json.dump(payload,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 digest=hashlib.sha256(native.read_bytes()).hexdigest()
 tup=ClaimTuple(measurement_id=f"{Path(run).name}:{row['index']}:ms_per_step",metric='p3batch_synchronized_step_ms',value=row['metrics']['ms_per_step'],date=row['completed_utc'],category='CANDIDATE' if row['kvu'] else 'BASELINE',claim=f"Synthetic p3batch synchronized step time for kv_unified={row['kvu']}, four batched sequences; same-binary scoped observation",metric_direction='lower_better',protocol_id='',reps=1,reps_basis='scored',unit='ms/step',attestation_path=str(native),attestation_sha256=digest,attestation_present=True,attestation_verified=True,source_class='measurement',applicability={'model_file':assets['model']['path'],'model_sha256':assets['model']['sha256'],'backend':'HIP','device':positive[0]['gpu_bdf'],'context_tokens':own,'kernel':assets['source_commit'],'run_id':Path(run).name,'np':4,'shape':f'own={own},draft=1,n_act=4,q8_0','scope_basis':'native','surface':'synthetic-p3batch','knobs':{'kv_unified':row['kvu'],'GGML_CUDA_FA_SEQ_ROWS':1}},extra={'host_cpu_affinity':list(range(184,192)),'native_context_threads':'unknown; cp.n_threads retains native default','measured_correlated_steps':steps,'sample_unit':'timed_process','source_family':'VB-FA-MASKSKIP','native_schema':payload['schema'],'capture_started_utc':row['started_utc'],'capture_completed_utc':row['completed_utc'],'interpretation':'descriptive observation; no ratified protocol or causal verdict'})
 record={'schema':'epyc.native_claim_tuple.v1','source_family':'VB-FA-MASKSKIP','authored_at':payload['authored_at'],'claim_tuple':asdict(tup)}
 side=Path(run)/'belief_measurements.jsonl'
 with side.open('a') as f:f.write(json.dumps(record,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
 return str(side)
