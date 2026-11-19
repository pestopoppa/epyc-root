#!/usr/bin/env python3
"""Bind a completed corrected build to this draft; never run a GPU program."""
import hashlib,json,os,pathlib,subprocess,sys
D=pathlib.Path(__file__).resolve().parent
B=pathlib.Path('/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/c6-b4-build-20261105')
BASE='729599d69871181d67af715a4c2f9162d5153a2e'
def sha(p):
 with pathlib.Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def image(directory):
 directory=pathlib.Path(directory).resolve()
 files={str(p.relative_to(directory)):sha(p) for p in directory.rglob('*') if p.is_file() and not p.is_symlink()}
 links={str(p.relative_to(directory)):os.readlink(p) for p in directory.rglob('*') if p.is_symlink()}
 for n in links:
  if not (directory/n).resolve().is_relative_to(directory) or not (directory/n).resolve().is_file(): raise ValueError('bad alias '+n)
 return files,links
def bind():
 if (D/'BOUND.json').exists(): raise ValueError('already bound; use a new packet')
 subprocess.run(['sha256sum','--strict','--quiet','-c','SEAL.sha256'],cwd=B,check=True)
 subprocess.run(['sha256sum','--strict','--quiet','-c','BUILD-INPUTS.sha256'],cwd=B,check=True)
 env=os.environ.copy(); env.pop('FILLER_DRYRUN',None)
 subprocess.run(['/usr/bin/python3','-B',str(B/'complete.py')],env=env,check=True)
 r=json.loads((B/'BUILD-RESULT.json').read_text())
 if r['schema']!='c6.b4.corrected.build.v1' or r['status']!='COMPLETE_BUILD_ONLY' or r['dryrun'] is not False or r['source_base']!=BASE or r['gpu_execution'] is not False or r['full_gak_pass'] is not None: raise ValueError('invalid build verdict')
 if r['source_manifest_sha256']!=sha(B/'BUILD-INPUTS.sha256') or r['source_patch_sha256']!=sha(B/'b4-quantized-min.patch') or r['base_candidate_patch_sha256']!=sha(B/'C6-TO-MMQ-COMPLETE.patch') or r['config_identity_sha256']!=sha(B/'BUILD-IDENTITY.json'): raise ValueError('build provenance drift')
 run=pathlib.Path(r['run']).resolve()
 if not run.is_relative_to((B/'builds').resolve()): raise ValueError('bad build location')
 folder=run/'cmake-build/bin'; files,links=image(folder)
 if files!=r['files'] or links!=r['symlinks'] or files['test-backend-ops']!=r['binary_sha256']: raise ValueError('corrected image drift')
 hips=[n for n in files if n.startswith('libggml-hip.so.')]
 if len(hips)!=1 or files[hips[0]]!=r['candidate_hip_sha256']: raise ValueError('corrected HIP drift')
 prior_build=D/'BASELINE-BUILD-RESULT.json'
 if sha(prior_build)!='bf50d945460498e2901930634fc76feed9acac389982b0354e80f58291ca43cb': raise ValueError('baseline receipt drift')
 old=json.loads((D/'PINS.json').read_text())['candidate'];
 prior=json.loads(prior_build.read_text())
 if old['binary_sha256']!=prior['binary_sha256'] or old['hip_library_sha256']!=prior['candidate_hip_sha256']: raise ValueError('baseline provenance mismatch')
 olddir=pathlib.Path(old['library_dir']).resolve()
 ofiles,olinks=image(olddir)
 if ofiles!=old['files'] or olinks!=old['symlinks'] or sha(old['binary'])!=old['binary_sha256']: raise ValueError('baseline image drift')
 ref=pathlib.Path('/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/c6-n5/prior-candidate')
 captures={p.name:sha(p) for p in ref.iterdir() if p.is_file() and not p.is_symlink()}
 required={'candidate_weight.bin','candidate_activation.bin','candidate_output.bin','sibling_weight.bin','sibling_activation.bin','sibling_output.bin','stderr.log','stdout.log'}
 if set(captures)!=required: raise ValueError('n5 prior capture set drift')
 expected={'candidate_weight.bin':'93f5950bb7d91cd6937de55639cb367708dbed8ad443863621d519d0e9993972','candidate_activation.bin':'8a80cdbadf0f25242b13be067ac2fd673e9d0f99d785c8f37640c48f6c28cd15'}
 if any(captures[n]!=h for n,h in expected.items()): raise ValueError('n5 retained input mismatch')
 corrected={'binary':str(folder/'test-backend-ops'),'library_dir':str(folder),'binary_sha256':r['binary_sha256'],'hip_library_sha256':r['candidate_hip_sha256'],'ggml_libraries_sha256':{n:h for n,h in files.items() if n.startswith('libggml')},'files':files,'symlinks':links}
 out={'schema':'epyc.c6.corrected-pair-binding.v1','build_receipt':str(B/'BUILD-RESULT.json'),'build_receipt_sha256':sha(B/'BUILD-RESULT.json'),'corrected':corrected,'baseline':old,'prior_n4_sha256':sha(D/'PRIOR-CANDIDATE-RESULT.json'),'n5_capture_path':str(ref),'n5_capture_sha256':captures,'build_source_manifest_sha256':r['source_manifest_sha256'],'build_patch_sha256':r['source_patch_sha256']}
 temp=D/'BOUND.json.tmp'
 with temp.open('x') as f: json.dump(out,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 try: os.link(temp,D/'BOUND.json')
 finally: temp.unlink()
if __name__=='__main__':
 try:bind()
 except Exception as e: print('BIND_REFUSED:',repr(e),file=sys.stderr);sys.exit(2)
