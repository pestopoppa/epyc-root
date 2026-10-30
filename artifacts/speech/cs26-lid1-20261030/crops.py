#!/usr/bin/env python3
import hashlib,json,wave,sys
from pathlib import Path
src=Path('/mnt/raid0/llm/tmp/codex3-cs8-stt3-transcribe-20261030/corpus-candidate/manifest.json')
assert hashlib.sha256(src.read_bytes()).hexdigest()=='8116e0bbbb44876f592542a94e31a3717d73ad96e94f80209b5cbd80c9664b10'
r=json.loads(src.read_text())['records']; assert len(r)==3050
out=Path(sys.argv[1]); assert not out.exists()
with out.open('x') as f:
 for item in r:
  with wave.open(item['wav_path'],'rb') as w:
   assert (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(1,2,16000,item['pcm_frames'])
   pcm=w.readframes(w.getnframes())
  assert hashlib.sha256(pcm).hexdigest()==item['pcm_sha256']
  for sec in (1,2,3):
   n=min(item['pcm_frames'],16000*sec); maxoff=item['pcm_frames']-n
   key=('CS-26.LID1:seed-20261030\0'+item['clip_id']+'\0'+str(sec)).encode()
   offset=int.from_bytes(hashlib.sha256(key).digest(),'big')%(maxoff+1)
   pad=16000*sec-n
   crop=pcm[2*offset:2*(offset+n)]+b'\0\0'*pad
   row={'case_id':item['clip_id']+':'+str(sec),'clip_id':item['clip_id'],'language':item['language'][:2],'duration_requested_s':sec,'frames':16000*sec,'valid_frames':n,'pad_frames':pad,'offset_frames':offset,'crop_pcm_sha256':hashlib.sha256(crop).hexdigest(),'source_pcm_sha256':item['pcm_sha256'],'wav_path':item['wav_path']}
   f.write(json.dumps(row,sort_keys=True)+'\n')
