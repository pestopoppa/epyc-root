#!/usr/bin/env python3
"""Run before publication; renders current recipe and binds original model receipt."""
import contextlib,hashlib,io,json,os,shutil,subprocess,sys
from pathlib import Path
D=Path(__file__).resolve().parent
O=Path('/mnt/raid0/llm/epyc-orchestrator')
sys.path.insert(0,str(O))
from scripts.server import orchestrator_stack as s
sys.path.insert(0,str(D))
import producer

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(O),*args],text=True).strip()
registry=O/'orchestration/model_registry.yaml'; reg_hash=sha(registry)
role=s.RegistryLoader(registry_path=registry,validate_paths=False).get_role('architect_critic')
raw=s.build_server_command(role,8083,False,numa_instance=0,prepare_runtime_dirs=False)
with contextlib.redirect_stdout(io.StringIO()):
 env=s.build_launch_env('architect_critic',{'PATH':'/usr/bin:/bin'})
 binary,paths=s._stack_prior_runtime_overrides('architect_critic')
 s._apply_runtime_requirements_env(env,binary_override=binary,ld_paths=paths,preserve={**s.recipe_env_for('architect_critic'),**s._role_env_overrides('architect_critic')})
 prefix=s._numa_prefix('architect_critic',0);s.apply_pinned_launch_env(env,prefix)
if sha(registry)!=reg_hash:raise RuntimeError('registry changed while rendering')
if '--no-cache-idle-slots' not in raw:raise RuntimeError('required cache flag missing')
# Reuse an original full-model digest receipt only when all original identity fields match.
origin=Path('/mnt/raid0/llm/worktrees/mains/h-kvu/progress/evidence/kvu16a-load-result-20261102/model-receipt.json')
receipt=json.loads(origin.read_text())
if sha(origin)!='42d05e6400e73d4618a84ec739bee0d00d62f3d4509f01b7534e38efbc74b078':raise RuntimeError('anchored model receipt changed')
shutil.copyfile(origin,D/'model-receipt.json')
assets=[];identities={}
for flag in ('-m','-md','--chat-template-file'):
 p=Path(raw[raw.index(flag)+1]).resolve();stat=producer.stat_identity(p)
 if flag in ('-m','-md'):
  prior=next(x for x in receipt['models'] if x['path']==str(p))
  if prior['stat']!=stat:raise RuntimeError('model identity differs from full-digest receipt')
  digest=prior['sha256']
 else:digest=sha(p)
 identities[str(p)]=digest;assets.append({'path':str(p),'stat':stat,'sha256':digest})
binpath=Path(raw[0]).resolve();build=binpath.parent.parent
runtime={}
for line in (build/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split(maxsplit=1)
 if name.startswith('bin/lib') or name=='bin/llama-server':
  p=(build/name).resolve()
  if sha(p)!=digest:raise RuntimeError('production manifest mismatch')
  runtime[str(p)]=digest
identities[str(binpath)]=runtime[str(binpath)];assets.append({'path':str(binpath),'stat':producer.stat_identity(binpath),'sha256':runtime[str(binpath)]})
link=Path('/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh')
shutil.copyfile(link,D/'verify_ggml_linkage.sh')
q=subprocess.run(['bash',str(D/'verify_ggml_linkage.sh'),str(binpath),str(binpath.parent)],env=env,capture_output=True,text=True,timeout=30)
(D/'linkage-preflight.txt').write_text(q.stdout+q.stderr)
if q.returncode:raise RuntimeError('linkage preflight failed')
modules={str(Path(m.__file__).resolve()):sha(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and str(getattr(m,'__file__','')).startswith(str(O)) and str(m.__file__).endswith('.py')}
plan={'checkout':str(O),'head':git('rev-parse','HEAD'),'registry_sha256':reg_hash,'stack_priors_path':str(s.STACK_PRIORS_PATH),'stack_priors_sha256':sha(s.STACK_PRIORS_PATH),'rendered_argv':raw,'argv':raw,'prefix':prefix,'effective_env':producer.selected_env(env),'identities':identities,'diagnostic_deviation':'-lv 4 adds allocation logging; memory/serving flags unchanged','compiler_source_sha256':modules}
record={'schema':'kvu16a.preflight.v2','plan':plan,'assets':assets,'runtime':runtime,'model_verification':'anchored full-model receipt reused after exact dev/inode/size/mtime/ctime verification; no fresh weight read','model_receipt_source':str(origin),'model_receipt_sha256':sha(origin),'registry_worktree_status':git('status','--porcelain','--untracked-files=no'),'registry_diff_sha256':hashlib.sha256(git('diff','--','orchestration/model_registry.yaml').encode()).hexdigest(),'producer_base_commit':'b1d7e1f77'}
(D/'preflight.json').write_text(json.dumps(record,indent=2)+'\n')
(D/'rendered-recipe.json').write_text(json.dumps(plan,indent=2)+'\n')
print('Prepared current compiler recipe,',len(modules),'source identities,',len(runtime),'approved runtime files, anchored model identities and linkage')
