from pathlib import Path
import hashlib,json,shutil,os
D=Path('/mnt/raid0/llm/tmp/df2/cafe2-expert-build');S=Path('/mnt/raid0/llm/tmp/df2/cafe2-expert-source');old=Path('/mnt/raid0/llm/tmp/df2/cafe2-build-r2');src=Path('/mnt/raid0/llm/tmp/df2/cafe2-expert-union');rid='cafe2-v10-expert-union-build-20261104'
for n in ['expert_union.hpp','SOURCE-PROOF.md','INTEGRATION.md']:(D/n).write_bytes((src/n).read_bytes())
for n in ['mtp_draft_bridge.hpp','supervise.py']:(D/n).write_bytes((old/n).read_bytes())
ids=json.loads((D/'prompt.json').read_text())['ids'];s=(src/'candidate.cpp').read_text();oldblock='''                    const char *text = "Explain a jet engine briefly.";
                    int n = -llama_tokenize(vocab, text, std::strlen(text), nullptr, 0, true, true);
                    if (n > 0 && n < 120) {
                        llama_tokens prompt(n);
                        if (llama_tokenize(vocab, text, std::strlen(text), prompt.data(), n, true, true) == n) {''';newblock='''                    // Tokenized before admission with the pinned v10 vocabulary.
                    llama_tokens prompt{'''+','.join(map(str,ids))+'''};
                    const int n = (int) prompt.size();
                    bool frozen_tokens_ok = vocab != nullptr;
                    for (llama_token tok : prompt) frozen_tokens_ok = frozen_tokens_ok && tok >= 0 && tok < llama_vocab_n_tokens(vocab);
                    if (n > 0 && n < 120) {
                        if (frozen_tokens_ok) {''';assert oldblock in s;s=s.replace(oldblock,newblock,1)
oldcp='''        cp.n_ctx = 512; cp.n_batch = 128; cp.n_ubatch = 128; cp.n_rs_seq = 8;''';newcp='''        cp.n_ctx = 512; cp.n_batch = 128; cp.n_ubatch = 128; cp.n_rs_seq = 8;
        // Filler sets actual granted CPU budget. Fail closed on malformed input.
        const char * thread_env = std::getenv("FILLER_THREADS");
        if (!thread_env) { std::fprintf(stderr, "UNKNOWN missing FILLER_THREADS\\n"); llama_model_free(model); llama_backend_free(); return 2; }
        char * thread_end = nullptr; const long threads = std::strtol(thread_env, &thread_end, 10);
        if (!thread_end || *thread_end || threads < 1 || threads > 96) { std::fprintf(stderr, "UNKNOWN invalid FILLER_THREADS\\n"); llama_model_free(model); llama_backend_free(); return 2; }
        cp.n_threads = (int32_t) threads; cp.n_threads_batch = (int32_t) threads;''';assert oldcp in s;s=s.replace(oldcp,newcp,1)
needle='''        if (ctx && vocab && llama_model_n_layer_nextn(model) > 0) {''';replace='''        if (ctx && (llama_n_threads(ctx) != cp.n_threads || llama_n_threads_batch(ctx) != cp.n_threads_batch)) { std::fprintf(stderr, "UNKNOWN effective thread mismatch\\n"); llama_free(ctx); llama_model_free(model); llama_backend_free(); return 2; }
        if (ctx && vocab && llama_model_n_layer_nextn(model) > 0) {
            std::fprintf(stderr, "CAFE2_EFFECTIVE_THREADS generation=%d batch=%d\\n", llama_n_threads(ctx), llama_n_threads_batch(ctx));''';assert needle in s;s=s.replace(needle,replace,1);assert 'llama_tokenize(' not in s;(D/'candidate.cpp').write_text(s)
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();cand=h(D/'candidate.cpp');header=h(D/'expert_union.hpp');bridge=h(D/'mtp_draft_bridge.hpp');prompt=h(D/'prompt.json');patch=h(D/'source.patch')
proof='''import hashlib,json,os,pathlib,subprocess,sys,tempfile
D=pathlib.Path(%r); S=pathlib.Path(%r)
PINS=%r
PATCH=%r
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
 with os.fdopen(fd,'w') as f:json.dump(d,f,sort_keys=True);f.write('\\n');f.flush();os.fsync(f.fileno())
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
'''%(str(D),str(S),{'candidate.cpp':cand,'expert_union.hpp':header,'mtp_draft_bridge.hpp':bridge,'prompt.json':prompt},patch);(D/'proof.py').write_text(proof)
build=(old/'build.sh').read_text().replace(str(old),str(D)).replace('/mnt/raid0/llm/tmp/df2/cafe2-build-source',str(S));(D/'build.sh').write_text(build)
job=(old/'job.sh').read_text().replace(str(old),str(D));(D/'job.sh').write_text(job)
files=['candidate.cpp','expert_union.hpp','mtp_draft_bridge.hpp','prompt.json','source.patch','proof.py','build.sh','job.sh','supervise.py'];(D/'runtime.sha256').write_text(''.join(h(D/n)+'  '+str(D/n)+'\n' for n in files));seal=h(D/'runtime.sha256')
launch='''#!/bin/bash
set -euo pipefail
D=%s
printf '%%s  %%s\\n' %s "$D/runtime.sha256" | sha256sum -c - >/dev/null
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id %s --class cpu --role build --min-window 1800 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/proof.py check"
'''%(D,seal,rid);(D/'launch.sh').write_text(launch)
for n in ['build.sh','job.sh','launch.sh']:os.chmod(D/n,0o755)
spec={'id':rid,'owner':'h-speculative-decoding-mtp','launcher':str(D/'launch.sh'),'lane':'cpu','estimate_s':1800,'min_window_s':1800,'result_path':str(D/'RESULT.json'),'result_format':'json','decision_rule':'Build-only: accept pinned v10 plus exact CAFE2 expert-union candidate/header/bridge, frozen tokenizer input and CMake integration; full CPU executable with CAFE2_VERIFY_RAW, CAFE2_EFFECTIVE_THREADS and cafe2.expert.window.begin.v1 compiled markers, source/artifact hashes and local library linkage. No native callback, expert union, timing or CAFE-2 verdict.','handoff_task':'handoffs/active/speculative-decoding.md:CAFE-2','priority_rank':45,'kind':'compute','dryrun_native_result':True,'scratch_root':str(D),'keep':['RESULT.json','runs/**','*.sh','*.py','*.cpp','*.hpp','*.json','*.sha256','*.patch','*.md','tokenizer-linkage.txt'],'smoke_predicate':'python3 '+str(D/'proof.py')+' predicate','first_progress_s':300};(D/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
print(json.dumps({'candidate':cand,'header':header,'prompt':prompt,'patch':patch,'launcher_manifest':seal}))
