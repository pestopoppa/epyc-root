#!/usr/bin/env python3
import ctypes as C,hashlib,json,sys,time,wave,os,glob
lib=C.CDLL(sys.argv[1]); lib.lid_open.argtypes=[C.c_char_p];lib.lid_open.restype=C.c_void_p
lib.lid_id.argtypes=[C.c_char_p];lib.lid_id.restype=C.c_int
lib.lid_max.restype=C.c_int;lib.lid_detect.argtypes=[C.c_void_p,C.POINTER(C.c_int16),C.c_int,C.POINTER(C.c_float)];lib.lid_detect.restype=C.c_int;lib.lid_close.argtypes=[C.c_void_p]
ctx=lib.lid_open(sys.argv[2].encode()); assert ctx
langs=['en','it','de','fr']; ids={x:lib.lid_id(x.encode()) for x in langs};assert len(set(ids.values()))==4 and min(ids.values())>=0
seen=set()
for prior in glob.glob(os.path.join(os.path.dirname(sys.argv[4]),'worker-*.jsonl')):
 with open(prior) as prev:
  for line in prev: seen.add(json.loads(line)['case_id'])
with open(sys.argv[3]) as f,open(sys.argv[4],'a',buffering=1) as out:
 for line in f:
  case=json.loads(line)
  if case['case_id'] in seen: continue
  out.write(json.dumps({'case_id':case['case_id'],'event':'started'})+'\n');out.flush();os.fsync(out.fileno())
  start=time.monotonic_ns(); rec={'case_id':case['case_id'],'event':'outcome'}
  try:
   with wave.open(case['wav_path'],'rb') as w:
    w.setpos(case['offset_frames']); pcm=w.readframes(case.get('valid_frames',case['frames']))
   pcm+=b'\0\0'*case.get('pad_frames',0)
   assert hashlib.sha256(pcm).hexdigest()==case['crop_pcm_sha256']
   samples=(C.c_int16*case['frames']).from_buffer_copy(pcm); p=(C.c_float*(lib.lid_max()+1))(); t=time.monotonic_ns(); ret=lib.lid_detect(ctx,samples,len(samples),p); elapsed=time.monotonic_ns()-t
   if ret<0: raise RuntimeError('native failure '+str(ret))
   scores={x:p[i] for x,i in ids.items()}; rec.update(status='ok',prediction=max(langs,key=lambda x:scores[x]),scores=scores,native_probabilities=list(p),native_argmax=ret,latency_ns=elapsed)
  except Exception as e: rec.update(status='failure',error=repr(e))
  rec['elapsed_ns']=time.monotonic_ns()-start;out.write(json.dumps(rec,allow_nan=False)+'\n')
lib.lid_close(ctx)
