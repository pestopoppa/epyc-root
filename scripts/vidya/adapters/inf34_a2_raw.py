"""Prospective raw A2 observations; unchanged shared ClaimTuple grader only."""
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple,ProjectionError,register
from adapters import inf34_a2_capture as capture
from adapters._llama_bench_protocol import assess
ADAPTER_ID='vidya.adapters.inf34_a2_raw/v1'
AUTHORITY='measurement'
TRUSTED_CAPTURE_SHA256='c9dc0feb6923ebec347504f59b91aec5a43846e30458dbe6cc604ded5c08b0f4'
TRUSTED_SOURCE_SHA256='11fa583bb0160cc2babce6fd035014322cbbe22ac861fe5811812d1c2aec5ec7'
TRUSTED_GPU_ALIASES_SHA256='611c0571aadd1d7ee56a1bab0280e79a5f72063ddc34d01a6765de75f2e34b3f'
MODEL='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'
MODEL_SHAS=('5ce89370720f8bf90890f439361282104c1aa1482d4013bb9a50923e758e71a4','577a38a2392b40ca2193cea502e1d92f60b8cd370675d308e0ec21885d9daaa7','d4634e6d84f0ebb0940be15c90d3790bf6464e3dea3a1cddc567dc0e83ad8833')
def native_rows(path):
 path=Path(path);root=path.parent if path.is_file() else path
 try:
  row=capture.read(root);intent=row['intent']
  if intent['mode']!='official' or row['state']!='complete':return ()
  capture.require_complete(root,'official')
  if (intent['producer_sha256'],intent['source_manifest_sha256'],capture.digest(intent['view_aliases']))!=(TRUSTED_CAPTURE_SHA256,TRUSTED_SOURCE_SHA256,TRUSTED_GPU_ALIASES_SHA256):raise ValueError('unreviewed producer/source/view epoch')
  if intent['geometry']!={'n_prompt':16384,'reps':1,'threads':8,'ngl':99,'ubatch':512,'n_gen':0}:raise ValueError('original A2 geometry changed')
  if intent['frontend_sha256']!='9b8109dd02ff71fd03d6f63a810165284ebf13fc840bb1903b7387c259d347a5':raise ValueError('v10 frontend identity')
  if len(intent['models'])!=3 or tuple(x['declared_sha256'] for x in intent['models'])!=MODEL_SHAS or intent['models'][0]['path']!=MODEL:raise ValueError('canonical model identity')
  argv=intent['argv']
  expected=['-m',MODEL,'-p','16384','-n','0','-r','1','-ub','512','-t','8','-ngl','99','-ot',capture.OVERRIDE,'-o','json']
  if Path(argv[0]).name!='llama-bench' or argv[1:]!=expected:raise ValueError('exact original A2 argv')
  if intent['metric_direction']!='higher_better' or intent['window'].get('regions')!='mi210_0,0-95' or not intent['window'].get('grant_sha256'):raise ValueError('direction or actual window')
  if intent['actual_cpu_affinity']!=list(range(184,192)):raise ValueError('original A2 native affinity changed')
  expected_app={'model_file':MODEL,'quant':'UD-IQ4_XS','backend':'gpu','device':'ROCm0','context_tokens':16384,'surface':'single_raw_A2','scope_basis':'native','threads':8}
  if intent['applicability']!=expected_app:raise ValueError('applicability contradicts original A2 recipe')
  native=row['native_rows'][0]
  row['protocol_identity']=assess(row=native,argv=argv,build_commit=native['build_commit'],strict_unknown=True)
  return (row,)
 except ProjectionError:raise
 except (ValueError,KeyError,TypeError,OSError) as exc:raise ProjectionError('raw A2 capture: '+str(exc)) from exc
@register('inf34-a2-raw-prefill')
def project(row):
 intent=row['intent'];native=row['native_rows'][0]
 return ClaimTuple(measurement_id='inf34-a2:'+row['run_id']+':'+row['intent_sha256'],metric='prompt_throughput',value=native['samples_ts'][0],date=datetime.fromisoformat(intent['created_at']).date().isoformat(),category='CANDIDATE',claim='Single original16384-prompt A2 native benchmark observation; no crossover, grid, serving or quality claim',metric_direction='higher_better',protocol_id='',reps=1,reps_basis='one inner sample of one benchmark invocation; no independent replicate',unit='tokens/s',attestation_locator=row['public_locator'],source_kind='inf34-a2-raw-prefill',extra={'raw_capture_sha256':row['content_sha256'],'models':intent['models'],'frontend_sha256':intent['frontend_sha256'],'source_manifest_sha256':intent['source_manifest_sha256'],'window':intent['window'],'cleanup_verified':True,'native_protocol_identity':row['protocol_identity'],'verification_limit':'declared full model hashes; sidecar/size/edge verification only; no protocol attestation or diagnostic seal'},applicability=dict(intent['applicability'],kernel={'build_commit':native['build_commit'],'build_number':native['build_number']}))
