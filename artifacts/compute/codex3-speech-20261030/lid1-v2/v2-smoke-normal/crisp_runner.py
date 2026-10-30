#!/usr/bin/env python3
import ctypes as C,glob,hashlib,json,os,sys,time,wave
from array import array
D=os.path.dirname(os.path.realpath(__file__));arm=sys.argv[1];assert arm in ('silero','firered')
lib=C.CDLL(os.path.join(D,'libsilero_lid_scored.so' if arm=='silero' else 'libfirered_asr_scored.so'))
if arm=='silero':
 lib.silero_lid_init.argtypes=[C.c_char_p,C.c_int];lib.silero_lid_init.restype=C.c_void_p;ctx=lib.silero_lid_init(sys.argv[2].encode(),1)
 lib.cs26_silero_scores.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_float),C.c_int];lib.cs26_silero_scores.restype=C.c_int
 lib.cs26_silero_lang.argtypes=[C.c_void_p,C.c_int];lib.cs26_silero_lang.restype=C.c_char_p;name=lambda i:lib.cs26_silero_lang(ctx,i).decode();lib.silero_lid_free.argtypes=[C.c_void_p]
else:
 lib.cs26_fire_open.argtypes=[C.c_char_p];lib.cs26_fire_open.restype=C.c_void_p;ctx=lib.cs26_fire_open(sys.argv[2].encode())
 lib.cs26_fire_detect.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_void_p)];lib.cs26_fire_detect.restype=C.c_int
 lib.cs26_fire_token.argtypes=[C.c_void_p,C.c_int];lib.cs26_fire_token.restype=C.c_char_p;name=lambda i:lib.cs26_fire_token(ctx,i).decode();lib.cs26_fire_free.argtypes=[C.c_void_p];lib.cs26_fire_close.argtypes=[C.c_void_p]
assert ctx
cpu=lib.cs26_silero_is_cpu if arm=='silero' else lib.cs26_fire_is_cpu
cpu.argtypes=[C.c_void_p];cpu.restype=C.c_int
assert cpu(ctx)==1, 'native backend is not CPU'
seen=set()
for prior in ([] if os.getenv('CS26_ASSIGNED')=='1' else glob.glob(os.path.join(os.path.dirname(sys.argv[4]),'worker-*.jsonl'))):
 with open(prior) as prev:
  for line in prev:seen.add(json.loads(line)['case_id'])
langs=['en','it','de','fr'];names=None
with open(sys.argv[3]) as f,open(sys.argv[4],'a',buffering=1) as out:
 for line in f:
  case=json.loads(line)
  end=float(os.environ['FILLER_END']);reserve=90 if os.getenv('CS26_SMOKE')=='1' else 620
  if os.path.exists(os.environ['FILLER_STOPFILE']) or time.time()+reserve >= end: break
  if case['case_id'] in seen: continue
  out.write(json.dumps({'case_id':case['case_id'],'event':'started'})+'\n');out.flush();os.fsync(out.fileno()); active=sys.argv[4]+'.active'; open(active,'w').write(json.dumps({'case_id':case['case_id'],'start':time.time()}));rec={'case_id':case['case_id'],'event':'outcome'};start=time.monotonic_ns()
  try:
   with wave.open(case['wav_path'],'rb') as w:w.setpos(case['offset_frames']);pcm=w.readframes(case.get('valid_frames',case['frames']))
   pcm+=b'\0\0'*case.get('pad_frames',0);assert hashlib.sha256(pcm).hexdigest()==case['crop_pcm_sha256']
   raw=array('h');raw.frombytes(pcm);samples=(C.c_float*len(raw))(*(x/32768. for x in raw));logits=(C.c_float*256)();original=C.c_void_p();t=time.monotonic_ns()
   n=lib.cs26_silero_scores(ctx,samples,len(samples),logits,256) if arm=='silero' else lib.cs26_fire_detect(ctx,samples,len(samples),logits,256,C.byref(original));latency=time.monotonic_ns()-t
   if n<=0:raise RuntimeError('native detect failure '+str(n))
   if names is None:names=[name(i) for i in range(n)]
   assert n==len(names);ids={}
   for lang in langs:
    found=[i for i,v in enumerate(names) if v.split(',')[0].strip()==lang];assert len(found)==1;ids[lang]=found[0]
   scores={k:logits[i] for k,i in ids.items()};native_top=max(range(n),key=lambda i:logits[i]);native=name(native_top)
   rec.update(status='ok',prediction=max(langs,key=lambda x:scores[x]),scores=scores,native_logits=list(logits[:n]),native_names=names,native_argmax=native,latency_ns=latency)
   if arm=='firered':rec['native_original']=C.string_at(original).decode();lib.cs26_fire_free(original)
  except Exception as e:rec.update(status='failure',error=repr(e))
  rec['elapsed_ns']=time.monotonic_ns()-start;out.write(json.dumps(rec,allow_nan=False)+'\n'); os.unlink(active)
if arm=='silero':lib.silero_lid_free(ctx)
else:lib.cs26_fire_close(ctx)
