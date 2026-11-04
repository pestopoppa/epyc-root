#!/usr/bin/env python3
"""Compile the pinned FA capture harness against the preserved base ggml build."""
import hashlib,json,os,pathlib,subprocess,tempfile,time
D=pathlib.Path('/mnt/raid0/llm/tmp/kvu/kvu19a2-capture-build-20261102')
B=pathlib.Path('/mnt/raid0/llm/tmp/kvu/kvu19a2-preserved-20261102/base/bin')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def main():
 mode=os.environ['FILLER_DRYRUN']
 if mode not in ('0','1') or os.environ.get('FILLER_ID')!='handoff-kvu-kvu19a2-capture-build-20261102':raise RuntimeError('incorrect row or mode')
 if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()+60>=int(os.environ['FILLER_DEADLINE']):raise RuntimeError('stopped or deadline')
 for p,digest in json.loads((D/'inputs.json').read_text()).items():
  if sha(p)!=digest:raise RuntimeError('input changed: '+p)
 out=pathlib.Path(tempfile.mkdtemp(prefix='smoke-' if mode=='1' else 'build-',dir=D)); exe=out/'fa_harness'
 cmd=['/usr/bin/g++','-std=c++17','-O2',str(D/'fa_harness.cpp'),'-I'+str(D/'headers'),'-L'+str(B),'-lggml','-lggml-base','-lggml-cpu','-o',str(exe)]
 with (out/'compile.log').open('xb') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
 if pathlib.Path(os.environ['FILLER_STOPFILE']).exists():raise RuntimeError('stopped')
 rec={'schema':'kvu19a2.capture-build.v1','mode':'qualification' if mode=='1' else 'full','status':'built','binary':str(exe),'binary_sha256':sha(exe),'source_sha256':sha(D/'fa_harness.cpp'),'input_catalog_sha256':sha(D/'inputs.json'),'argv':cmd,'scope':'compile only; no GPU measurement'}
 target=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if mode=='1' else D/'RESULT.json'
 with target.open('x') as f:json.dump(rec,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
if __name__=='__main__':main()
