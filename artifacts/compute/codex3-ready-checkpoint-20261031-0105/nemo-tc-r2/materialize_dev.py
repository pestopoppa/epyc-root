#!/usr/bin/env python3
import hashlib,importlib.util,json,os,pathlib,tarfile,time,wave
D=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('pcm_original','/mnt/raid0/llm/tmp/codex3-cs8-stt3-transcribe-20261030/prepare_full_candidate.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
base=pathlib.Path('/mnt/raid0/llm/data/stt-cs8-public-20261030/google/fleurs/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data');out=pathlib.Path('/mnt/raid0/llm/data/stt-cs8-public-20261030/fleurs-validation-pcm');out.mkdir(exist_ok=True)
rows=[]
for lang in ('en_us','it_it','de_de','fr_fr'):
 folder=base/lang;tsv=folder/'dev.tsv';archive=folder/'audio/dev.tar.gz'; entries=[]
 for i,line in enumerate(tsv.read_text(encoding='utf8').splitlines()):
  r=line.split('\t')
  if len(r)!=7 or not r[0].isdigit() or pathlib.PurePosixPath(r[1]).name!=r[1] or not r[3] or not r[5].isdigit():raise ValueError('invalid TSV')
  entries.append({'clip_id':lang+':'+r[1],'filename':r[1],'language':lang,'ordinal':i,'reference_raw':r[2],'reference_dataset_normalized':r[3],'declared_samples':int(r[5])})
 names={r['filename']:r for r in entries}
 if len(names)!=len(entries):raise ValueError('duplicate')
 dest=out/lang;dest.mkdir(exist_ok=True);found={}
 with tarfile.open(archive,'r|gz') as t:
  for member in t:
   n=pathlib.PurePosixPath(member.name).name
   if n not in names:continue
   if n in found or not member.isfile() or member.size>32*1024*1024:raise ValueError('bad tar')
   raw=t.extractfile(member).read();pcm,props=mod.pcm(raw)
   if props['pcm_frames']!=names[n]['declared_samples']:raise ValueError('frames')
   target=dest/n
   if not target.exists():
    tmp=dest/(n+'.partial')
    with wave.open(str(tmp),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm)
    os.link(tmp,target);tmp.unlink()
   with wave.open(str(target),'rb') as w:actual=w.readframes(w.getnframes())
   if actual!=pcm:raise ValueError('cache mismatch')
   found[n]={'wav_path':str(target),'source_sha256':hashlib.sha256(raw).hexdigest(),'wav_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'frames':props['pcm_frames']}
 if set(found)!=set(names):raise ValueError('missing input audio')
 rows.extend({**r,**found[r['filename']]} for r in entries)
 print(lang,len(entries),flush=True)
manifest={'schema':'cs8-stt5-fleurs-validation/v1','source_revision':'70bb2e84b976b7e960aa89f1c648e09c59f894dd','conversion':'16k mono PCM16; float32 scaled 32768 clipped and truncated','records':rows}
tmp=out/'manifest.partial';tmp.write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True)+'\n');os.replace(tmp,out/'manifest.json');print('manifest',hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest(),flush=True)
