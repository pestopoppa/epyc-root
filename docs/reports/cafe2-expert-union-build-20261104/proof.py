import hashlib,json,os,pathlib,subprocess,sys,tempfile
D=pathlib.Path('/mnt/raid0/llm/tmp/df2/cafe2-expert-build'); S=pathlib.Path('/mnt/raid0/llm/tmp/df2/cafe2-expert-source')
PINS={'candidate.cpp': '4d3aa0eba8c908cfca0331079069ff540ca3937fd2fb79cee750aefd91b34cca', 'expert_union.hpp': '6bf5bb05f647346b635b1f0b7a34bde530c5db913220ddedb65cbd7681e28d6d', 'mtp_draft_bridge.hpp': '9688a97c3ad30e5aa008650d29a7b4d463109220b7dc48a136f9324aa2cf3919', 'prompt.json': 'e92cd6dd3ca848fdd90e1d975358663ce2c0f3e4ced754094f82ee89f05a036b'}
PATCH='86851c0e550ba543ef3ab1ccfa85c14aa18715ddff4836332c380b7d0740ad7a'
COMMIT='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def source():
 for n,h in PINS.items():assert digest(D/n)==h
 assert subprocess.check_output(['git','-C',str(S),'rev-parse','HEAD'],text=True).strip()==COMMIT
 assert hashlib.sha256(subprocess.check_output(['git','-C',str(S),'diff','--binary','--abbrev=10','HEAD'])).hexdigest()==PATCH
 assert not subprocess.check_output(['git','-C',str(S),'ls-files','--others','--exclude-standard'])
def validate(d):
 source();assert d['source_commit']==COMMIT and d['patch_sha256']==PATCH and d['input_sha256']==PINS
 r=pathlib.Path(d['run']).resolve(strict=True);assert r.parent==(D/'runs').resolve()
 for p,h in d['files'].items():
  q=pathlib.Path(p).resolve(strict=True);assert q.is_relative_to(r) and digest(q)==h
 p=r/('candidate.o' if d['mode']=='smoke' else 'build/bin/cafe2-verify-cost');st=subprocess.check_output(['strings',str(p)])
 for mark in [b'CAFE2_VERIFY_RAW',b'CAFE2_EFFECTIVE_THREADS',b'cafe2.expert.window.begin.v1']:assert mark in st
 if d['mode']=='build':
  l=(r/'linkage.log').read_text();assert 'not found' not in l and str(r/'build/bin') in l and 'llama-common' in l
 else:assert d['mode']=='smoke'
def write(mode,run,out):
 source();r=pathlib.Path(run);files=[r/'candidate.o'] if mode=='smoke' else [r/'build/bin/cafe2-verify-cost',r/'build/CMakeCache.txt',r/'configure.log',r/'build.log',r/'linkage.log',*list((r/'build/bin').glob('libllama*.so*')),*list((r/'build/bin').glob('libggml*.so*'))]
 assert files and all(x.exists() for x in files)
 d={'schema':'epyc.cafe2.expert.build.v1','mode':mode,'run':str(r.resolve()),'source_commit':COMMIT,'patch_sha256':PATCH,'input_sha256':PINS,'files':{str(x.resolve()):digest(x) for x in files},'scope':'build only; no native expert union or timing observation'};validate(d)
 p=pathlib.Path(out);p.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(dir=p.parent,prefix='.proof-')
 with os.fdopen(fd,'w') as f:json.dump(d,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
if sys.argv[1]=='predicate':
 try:
  t0=int(os.environ['FILLER_SMOKE_T0']);p=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']);assert p.stat().st_mtime>=t0
  d=json.loads(p.read_text());assert d['mode']=='smoke';obj=(pathlib.Path(d['run']).resolve(strict=True)/'candidate.o').resolve(strict=True);assert str(obj) in d['files'] and obj.stat().st_size>0 and obj.stat().st_mtime>=t0;validate(d)
 except (AssertionError,OSError,KeyError,TypeError,ValueError,subprocess.SubprocessError):raise SystemExit(1)
 raise SystemExit(0)
if sys.argv[1]=='source':source()
elif sys.argv[1]=='write':write(*sys.argv[2:])
elif sys.argv[1]=='check':
 d=json.loads((D/'RESULT.json').read_text());assert d['mode']=='build';validate(d)
