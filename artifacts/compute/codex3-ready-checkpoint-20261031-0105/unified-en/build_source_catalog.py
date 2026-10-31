#!/usr/bin/env python3
import hashlib,json,pathlib
D=pathlib.Path(__file__).parent;W=pathlib.Path('/mnt/raid0/llm/whisper.cpp/build/bin');T=pathlib.Path('/mnt/raid0/llm/tmp/codex3-cs8-stt3-transcribe-20261030');M=pathlib.Path('/mnt/raid0/llm/data/stt-cs8-public-20261030/fleurs-validation-pcm/manifest.json');V=pathlib.Path('/mnt/raid0/llm/models/silero-vad-cs22-v0-20261029/ggml-silero-v6.2.0.bin')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
A=pathlib.Path('/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/nemo-traced-v2')
SRC=pathlib.Path('/mnt/raid0/llm/tmp/dive-transcribe-cpp/tc')
keys=('c1r0','c1r1','c2r2','c2r4','c7r7','c13r13')
models={k:pathlib.Path('/mnt/raid0/llm/models/cs8-handy-computer--parakeet-unified-en-0.6b-gguf/parakeet-unified-en-0.6b-Q8_0.gguf') for k in ('c1r0','c1r1','c2r2','c2r4','c7r7','c13r13')}
binaries={k:A/'transcribe-cli' for k in keys}
common=[T/'install/lib'/x for x in ('libtranscribe.so.0.4.0','libggml.so.0.26.0','libggml-base.so.0.26.0','libggml-cpu.so.0.26.0')]
libsets={k:common for k in keys}
libhashes={k:{str(p):sha(p) for p in v} for k,v in libsets.items()};fingerprints={k:hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest() for k,v in libhashes.items()}
source_root=pathlib.Path('/mnt/raid0/llm/data/stt-cs8-public-20261030/google/fleurs/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data')
source_files=[]
for lang,tree_name in [('en_us','fleurs-tree.json'),('it_it','it_it-tree.json'),('de_de','de_de-tree.json'),('fr_fr','fr_fr-tree.json')]:
 tree=D/'source-probe'/tree_name; entries={x['path']:x for x in json.loads(tree.read_text())};source_files.append(tree)
 for rel in (f'data/{lang}/dev.tsv',f'data/{lang}/audio/dev.tar.gz'):
  e=entries[rel];p=source_root/lang/rel.split(f'data/{lang}/',1)[1];blob=p.read_bytes() if p.suffix=='.tsv' else None
  expected=e.get('lfs',{}).get('oid') or e['oid'];actual=hashlib.sha1(f'blob {len(blob)}\0'.encode()+blob).hexdigest() if blob is not None else sha(p)
  if p.stat().st_size!=e['size'] or actual!=expected:raise RuntimeError('FLEURS upstream source mismatch '+str(p))
  source_files.append(p)
pins={'validation_sha256':sha(M),'plan_sha256':sha(D/'PLAN.md'),'models':{k:sha(v) for k,v in models.items()},'runner_binary_sha256':{k:sha(v) for k,v in binaries.items()},'runner_libraries':libhashes,'runner_library_set_sha256':fingerprints,'vad_model_sha256':sha(V),'vad_binary_sha256':sha(T/'build/bin/transcribe-cli'),'research_plan_commit':'d1c7a8ffb'}
if pins['models']!={k:'4b50b6dd862bf6e346929aaf4f5eaacec003bfa3f56462d6c874b41ef2f38795' for k in keys}:raise RuntimeError('model drift')
(D/'INPUT-PINS.json').write_text(json.dumps(pins,sort_keys=True,indent=2)+'\n')
files=[D/x for x in ('PLAN.md','PROFILE.md','INPUT-PINS.json','nemo_job.py','nemo_tokens.py','vocab.json','build_vocab.py','chunk_materialize.py','long_chunk_plan.py','vad_splice.py','smoke-supervisor.py','smoke_admission.py','materialize_dev.py','log_consumer.py','score_validation.py')]+[M,V,T/'build/bin/transcribe-cli']+list(models.values())+list(binaries.values())+[p for libs in libsets.values() for p in libs]
files += [A/x for x in ('asr.original.cpp','asr.traced.cpp','build.sh')]+[SRC/x for x in ('src/arch/parakeet/model.cpp','src/transcribe-tokenizer.cpp','include/transcribe.h')]
score_catalog=T/'SCORER-SHA256SUMS'
if sha(score_catalog)!='74f4c45bacf0ea2da83d9869e5b0f0e33fa8a5a2d3043081c0da7d2f4c18b8a2':raise RuntimeError('scorer catalog drift')
files += [score_catalog]+[T/line.split('  ',1)[1] for line in score_catalog.read_text().splitlines()]
files+=source_files+[pathlib.Path('/mnt/raid0/llm/models/cs8-handy-computer--parakeet-unified-en-0.6b-gguf/source-revision.json')]
files+=sorted((D/'engine').glob('*.sh'))+sorted((D/'engine').glob('*.py'))+sorted((D/'engine').glob('*.json'))
files += [T/'install/lib'/x for x in ('libtranscribe.so.0.4.0','libggml.so.0.26.0','libggml-base.so.0.26.0','libggml-cpu.so.0.26.0')]
raw=''.join(sha(p)+'  '+str(p)+'\n' for p in files);(D/'SOURCE-SHA256SUMS').write_text(raw)
print(json.dumps({'input':sha(M),'plan':sha(D/'PLAN.md'),'catalog':sha(D/'SOURCE-SHA256SUMS'),'files':len(files)},sort_keys=True),flush=True)
