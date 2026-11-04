#!/usr/bin/env python3
"""Freeze P3-3 model + C6 load-threads build identity before the first cell."""
import hashlib, json, os, re, subprocess, tempfile, time
from pathlib import Path
import controller, native_executor as n

PACKET=Path(__file__).resolve().parent
REGISTRY=Path('/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml')
BUILD_INPUTS=n.BUILD_ROOT/'BUILD-INPUTS.json'
BUILD_RECEIPT=n.BUILD_RECEIPT
C6_TREE='51b0a4fda906ffd3d029fd21bf41204675f08167'
C6_STORES={
 'cpu':Path('/mnt/raid0/llm/kernels/builds/cpu-20261030-729599d69-c6'),
 'gpu':Path('/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6')}
LINK=n.ROOT/'scripts/utils/verify_ggml_linkage.sh'
VERIFIERS=(LINK,n.WRAPPER,n.MONITOR,n.ROOT/'scripts/lib/canonical_recipe.py')

def sha(path,check=None):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):
   if check is not None and not check(): raise RuntimeError('grant ended during hashing')
   h.update(block)
 return h.hexdigest()

def checked(argv,env=None,check=None,timeout=180):
 with tempfile.TemporaryFile() as out:
  p=subprocess.Popen(argv,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
  start=time.monotonic()
  try:
   while p.poll() is None:
    if time.monotonic()-start>timeout or (check is not None and not check()): raise TimeoutError('precondition timeout, grant end, or STOP')
    time.sleep(.25)
  except BaseException:
   if p.poll() is None:
    os.killpg(p.pid,15)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,9);p.wait()
   raise
  out.seek(0);text=out.read().decode(errors='replace')
  if p.returncode:raise RuntimeError(f'precondition rc={p.returncode}: {text[-2000:]}')
  return text

def verify_build_receipt(check=None):
 raw=BUILD_RECEIPT.read_bytes(); receipt=json.loads(raw)
 if receipt.get('schema')!='pf1.loadthreads.build-receipt.v1':raise RuntimeError('C6 load-threads build receipt schema mismatch')
 if not (receipt.get('build_only') is True and receipt.get('model_run') is False and receipt.get('store_modified') is False):raise RuntimeError('build receipt does not prove build-only/store-unchanged scope')
 source=receipt.get('source') or {}
 if source.get('commit')!=n.HEAD or source.get('tree')!=C6_TREE or Path(source.get('worktree','')).resolve()!=n.SRC.resolve():raise RuntimeError('build source identity differs from approved C6 worktree')
 patch=Path(source.get('patch_path',''))
 if patch.resolve()!=(n.BUILD_ROOT/'patch.diff').resolve() or sha(patch,check)!=source.get('patch_sha256'):raise RuntimeError('build source patch hash mismatch')
 inputs_sha=sha(BUILD_INPUTS,check)
 if receipt.get('build_inputs_sha256')!=inputs_sha:raise RuntimeError('build inputs differ from receipt')
 changed=source.get('changed_files')
 if not isinstance(changed,list) or changed!=['tools/llama-bench/llama-bench.cpp']:raise RuntimeError('unexpected C6 source-change set')
 expected={
  'cpu':n.BUILD_ROOT/'build-cpu/bin/llama-bench',
  'gpu':n.BUILD_ROOT/'build-gpu/bin/llama-bench'}
 for role in ('cpu','gpu'):
  base=(receipt.get('base_c6') or {}).get(role) or {}; output=(receipt.get('output_builds') or {}).get(role) or {}; command=(receipt.get('commands') or {}).get(role) or {}
  if Path(base.get('store_root','')).resolve()!=C6_STORES[role].resolve() or base.get('source_commit')!=n.HEAD or base.get('source_tree')!=C6_TREE:raise RuntimeError(f'{role} base C6 identity mismatch')
  if not base.get('store_files_checksum_check') or 'fail' in str(base['store_files_checksum_check']).lower():raise RuntimeError(f'{role} base store checksum verification absent/failed')
  for field in ('build_identity','sha256sums'):
   if sha(base[field],check)!=base[field+'_sha256']:raise RuntimeError(f'{role} base {field} changed')
  for path,digest in base.get('library_and_binary_hashes',{}).items():
   if sha(path,check)!=digest:raise RuntimeError(f'{role} base C6 artifact changed: {path}')
  if Path(output.get('binary','')).resolve()!=expected[role].resolve():raise RuntimeError(f'{role} output binary path mismatch')
  if sha(output['binary'],check)!=output.get('binary_sha256'):raise RuntimeError(f'{role} output binary digest mismatch')
  if output.get('help_syntax_probe')!='--load-threads 1 --help' or output.get('help_accepts_option') is not True:raise RuntimeError(f'{role} compiled load-threads CLI witness absent')
  if not command.get('configure_argv') or not command.get('build_argv') or '--target' not in command['build_argv'] or 'llama-bench' not in command['build_argv']:raise RuntimeError(f'{role} exact build commands missing')
  for field in ('configure_log_sha256','build_log_sha256'):
   if not re.fullmatch(r'[0-9a-f]{64}',str(output.get(field,''))):raise RuntimeError(f'{role} {field} missing or malformed')
  if str(expected[role].parent.parent) not in ' '.join(command['build_argv']):raise RuntimeError(f'{role} build command points outside enrolled output')
  linked=output.get('linked_libraries') or {}
  if not linked:raise RuntimeError(f'{role} output library inventory absent')
  for soname,item in linked.items():
   path=Path(item['path'])
   if sha(path,check)!=item.get('sha256') or path.resolve()!=Path(item['resolved_path']).resolve():raise RuntimeError(f'{role} library binding mismatch: {soname}')
  tool_hashes=receipt.get('tool_binary_hashes') or {}
 tool_versions=receipt.get('tool_versions') or {}
 if not tool_hashes or not tool_versions:raise RuntimeError('build tool identity missing')
 for path,digest in tool_hashes.items():
  if sha(path,check)!=digest:raise RuntimeError(f'build tool binary changed: {path}')
 return receipt,hashlib.sha256(raw).hexdigest()

def served_identity():
 import yaml
 raw=REGISTRY.read_bytes(); data=yaml.safe_load(raw)
 role=data['roles']['architect_general']['model']; server=data['server_mode']['architect_general']['model']
 if role['path']!=str(n.MODEL) or server!=str(n.MODEL):raise RuntimeError('served model identity changed')
 known=[x['sha256'] for x in json.loads((PACKET/'IDENTITY.json').read_bytes())['model']['shards']]
 registry_hashes=[role['sha256'],role['shard_sha256'][n.MODEL.name.replace('00001-of','00002-of')],role['shard_sha256'][n.MODEL.name.replace('00001-of','00003-of')]]
 if registry_hashes!=known:raise RuntimeError('model shard identity differs from current served registry / frozen row identity')
 return {'path':str(REGISTRY),'sha256':hashlib.sha256(raw).hexdigest(),'role':'architect_general','model':server,'shard_sha256':registry_hashes}

def create(output,check=None):
 if os.environ.get('FILLER_PREFLIGHT')=='1' or not os.environ.get('FILLER_ID') or time.time()>=int(os.environ['FILLER_DEADLINE']):raise RuntimeError('manifest requires live admitted owner window')
 receipt,receipt_sha=verify_build_receipt(check)
 if subprocess.run(['git','-C',str(n.SRC),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()!=n.HEAD:raise RuntimeError('C6 build worktree HEAD mismatch')
 status=subprocess.run(['git','-C',str(n.SRC),'status','--porcelain','--untracked-files=all'],capture_output=True,text=True)
 if status.returncode or status.stdout.strip()!=' M tools/llama-bench/llama-bench.cpp':raise RuntimeError('C6 build worktree contains unexpected changes')
 for path in VERIFIERS:sha(path,check)
 shards=[]
 for item in json.loads((PACKET/'IDENTITY.json').read_bytes())['model']['shards']:
  path=Path(item['path']);value=sha(path,check)
  if value!=item['sha256']:raise RuntimeError(f'model shard digest changed: {path}')
  shards.append({'path':str(path),'sha256':value,'size':path.stat().st_size})
 bins={};linkage={};binary_paths={}
 for role in ('cpu','gpu'):
  build=receipt['output_builds'][role];binary=Path(build['binary']);linked={}
  for soname,item in build['linked_libraries'].items():linked[item['path']]=item['sha256']
  bins[role]={'path':str(binary),'sha256':build['binary_sha256'],'libraries':linked}
  env=dict(os.environ,LD_LIBRARY_PATH=str(binary.parent)+':/usr/lib/llvm-20/lib')
  linkage[role]=checked([str(LINK),str(binary),str(binary.parent)],env,check)
  help_out=checked([str(binary),'--load-threads','1','--help'],env,check,timeout=30)
  if '--load-threads' not in help_out:raise RuntimeError(f'{role} output binary lost --load-threads')
  binary_paths[role]=str(binary)
 knob=b'GGML_OP_OFFLOAD_MIN_BATCH'
 compiled=[path for path in bins['gpu']['libraries'] if knob in Path(path).read_bytes()]
 if not compiled:raise RuntimeError('C6 GPU output lacks compiled offload-control knob')
 version_files={str(path):sha(path,check) for path in VERIFIERS}
 w={'model_shards':shards,'cpu_binary_sha256':bins['cpu']['sha256'],'gpu_binary_sha256':bins['gpu']['sha256'],
    'source_head':n.HEAD,'build_line_policy':'each result must emit a build line with source commit prefix 729599d; build number is preserved verbatim per cell',
    'build_receipt_path':str(BUILD_RECEIPT),'build_receipt_sha256':receipt_sha,'build_inputs_sha256':receipt['build_inputs_sha256'],
    'build_patch_sha256':receipt['source']['patch_sha256'],'build_outputs':binary_paths,'binary_inventory':bins,'linkage':linkage,
    'argv_policy':'bench_canonical.sh, exact model/L/arm/ub plus -mmp 0 --load-threads 96',
    'env_policy':'canonical_recipe.py with store-specific output LD_LIBRARY_PATH; A1-disabled threshold recorded',
    'protocol':'PF1 P3-3 diagnostic; protocol_id empty until complete protocol conditions are proven',
    'declared_at':time.time(),'offload_knob_witness':compiled,'verifier_sources':version_files,
    'monitor_sha256':version_files[str(n.MONITOR)],'wrapper_sha256':version_files[str(n.WRAPPER)],
    'recipe_sha256':version_files[str(n.ROOT/'scripts/lib/canonical_recipe.py')],'served_identity':served_identity()}
 w['manifest_sha256']=controller.digest(w);controller.write(output,w)
 return w
