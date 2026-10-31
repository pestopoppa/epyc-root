#!/usr/bin/env python3
"""Create a shared, hash-bound indexed chunk record from already captured spans."""
import hashlib,io,os,pathlib,wave
from long_chunk_plan import LIMIT,NoVadBoundary,plan

def digest(b): return hashlib.sha256(b).hexdigest()
def materialize(rec,spans,out):
 source=pathlib.Path(rec['wav_path']);blob=source.read_bytes()
 if digest(blob)!=rec['wav_sha256']: raise ValueError('source WAV mismatch')
 with wave.open(io.BytesIO(blob),'rb') as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,16000):raise ValueError('format')
  n=w.getnframes();pcm=w.readframes(n)
 if digest(pcm)!=rec['pcm_sha256']:raise ValueError('source PCM mismatch')
 ident=rec.get('clip_id',rec.get('id'))
 item={'id':ident,'original_pcm_sha256':rec['pcm_sha256'],'original_wav_sha256':rec['wav_sha256'],'original_wav_path':str(source),'n_samples':n,'sample_rate':16000,'channels':1,'pcm_encoding':'s16le','status':'ok','chunks':[]}
 if n>LIMIT and spans is None: raise ValueError('long clip needs captured VAD spans')
 try: bounds=plan(n,spans or [])
 except NoVadBoundary:
  item['status']='void_no_vad_boundary';return item
 out=pathlib.Path(out);out.mkdir(exist_ok=True,parents=True)
 key=hashlib.sha256(ident.encode()).hexdigest()
 for i,(start,end) in enumerate(bounds):
  data=pcm[start*2:end*2]
  if len(bounds)==1: path=source;wh=rec['wav_sha256']
  else:
   path=out/f'{key}.{i:03d}.wav'; buffer=io.BytesIO()
   with wave.open(buffer,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(data)
   b=buffer.getvalue();wh=digest(b)
   try:
    with path.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
   except FileExistsError:
    if digest(path.read_bytes())!=wh:raise ValueError('chunk path collision')
  item['chunks'].append({'index':i,'start_sample':start,'end_sample':end,'wav_path':str(path),'wav_sha256':wh,'pcm_sha256':digest(data)})
 return item

def verify_record(item):
 if (item['sample_rate'],item['channels'],item['pcm_encoding'])!=(16000,1,'s16le'): raise ValueError('bad format')
 if item['status']=='void_no_vad_boundary':
  if item['chunks']:raise ValueError('VOID has chunks')
  return
 if item['status']!='ok' or not item['chunks']:raise ValueError('bad disposition')
 pos=0; assembled=hashlib.sha256()
 for i,c in enumerate(item['chunks']):
  if c['index']!=i or c['start_sample']!=pos or not pos<c['end_sample']<=item['n_samples'] or c['end_sample']-pos>LIMIT:raise ValueError('bad chunk coverage')
  path=pathlib.Path(c['wav_path']);b=path.read_bytes()
  if digest(b)!=c['wav_sha256']:raise ValueError('chunk WAV mismatch')
  with wave.open(io.BytesIO(b),'rb') as w:
   if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,16000,c['end_sample']-pos):raise ValueError('chunk format')
   pcm=w.readframes(w.getnframes())
  if digest(pcm)!=c['pcm_sha256']:raise ValueError('chunk PCM mismatch')
  assembled.update(pcm);pos=c['end_sample']
 if pos!=item['n_samples']:raise ValueError('incomplete cover')
 if assembled.hexdigest()!=item['original_pcm_sha256']:raise ValueError('chunks do not reconstruct original PCM')
