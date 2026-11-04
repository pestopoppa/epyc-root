import hashlib,json,os,pathlib,subprocess,sys,tempfile
D=pathlib.Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-build-row'); S=pathlib.Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-build-source')
PATCH='f9824d7605b50380f00d7a1795ce788a41a4a6f5caceb234bcfee610ca7cba34'
def digest(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def source():
 assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()=='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
 assert hashlib.sha256(subprocess.check_output(['git','-C',str(S),'diff','--binary','--abbrev=10','HEAD'])).hexdigest()==PATCH
 assert not subprocess.check_output(['git','-C',str(S),'ls-files','--others','--exclude-standard'])
def marker(p,s): assert s.encode() in subprocess.check_output(['strings',str(p)])
def validate(data):
 source(); run=pathlib.Path(data['run']).resolve(strict=True); assert run.parent==(D/'runs').resolve()
 assert data['mode'] in ('smoke','build')
 for p,h in data['files'].items():
  q=pathlib.Path(p).resolve(strict=True); assert q.is_relative_to(run) and digest(q)==h
 marker(run/('build/src/CMakeFiles/llama.dir/llama-memory-recurrent.cpp.o' if data['mode']=='smoke' else 'build/bin/libllama.so'),'CAFE4_TARGET_RS')
 if data['mode']=='build':
  marker(run/'candidate','llama_cafe4_target_configure'); marker(run/'build/bin/libllama.so','llama_cafe4_target_counts')
def write(mode,run,out):
 run=pathlib.Path(run).resolve(); files=[run/'configure.log',run/'build.log',run/'build/CMakeCache.txt']
 files += [run/'build/src/CMakeFiles/llama.dir/llama-memory-recurrent.cpp.o'] if mode=='smoke' else [run/'candidate',run/'build/bin/libllama.so']
 data={'schema':'epyc.cafe4.build.v1','mode':mode,'run':str(run),'source_commit':'ffc1bac82eeca6f9099e1ccd9ba49703c460a115','patch_sha256':PATCH,'candidate_sha256':digest(D/'candidate.cpp'),'files':{str(p.resolve(strict=True)):digest(p) for p in files},'scope':'experimental build only; synthetic draft, no inference or CAFE-4 verdict'}
 validate(data); out=pathlib.Path(out); out.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=out.parent,prefix='.result-')
 with os.fdopen(fd,'w') as f: json.dump(data,f,sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())
 os.replace(tmp,out)
if sys.argv[1]=='source': source()
elif sys.argv[1]=='write': write(*sys.argv[2:])
elif sys.argv[1]=='check':
 data=json.loads((D/'RESULT.json').read_text()); assert data['mode']=='build'; validate(data)
