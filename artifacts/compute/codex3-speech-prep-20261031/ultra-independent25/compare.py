import json, pathlib, sys
import numpy as np
try:
 ref=pathlib.Path(sys.argv[1]); native=pathlib.Path(sys.argv[2]); result=json.loads((ref/'result.json').read_text()); steps=[list(map(int,line.split())) for line in (native/'steps.tsv').read_text().splitlines() if line and line[0].isdigit()]
 if any(len(s)!=5 for s in steps) or not steps: raise ValueError('malformed steps')
 def stats(name,a,b):
  if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError(f'{name} shape/finite {a.shape} {b.shape}')
  delta=np.abs(a-b);print(name,'shape',a.shape,'max_abs',float(delta.max()),'mean_abs',float(delta.mean()),'rmse',float(np.sqrt(np.mean(delta**2))))
 f=np.load(ref/'frontend.npy',allow_pickle=False)[0];mask=np.load(ref/'attention_mask.npy',allow_pickle=False)[0];mel=np.fromfile(native/'mel.f32',dtype='<f4').reshape(-1,128)
 print('frontend raw shapes',f.shape,mel.shape,'valid mask',int(mask.sum()),'mask length',len(mask))
 if len(mask)!=len(f) or int(mask.sum())!=len(mel) or not np.array_equal(mask,np.arange(len(mask))<len(mel)):raise ValueError('frontend mask mismatch')
 stats('frontend valid',f[:len(mel)],mel)
 e=np.load(ref/'encoder.npy',allow_pickle=False)[0];en=np.fromfile(native/'encoder.f32',dtype='<f4').reshape(-1,1024);stats('encoder',e,en)
 l=np.load(ref/'joint_logits.npy',allow_pickle=False).reshape(-1,8198);ln=np.fromfile(native/'joint_logits.f32',dtype='<f4').reshape(-1,8198);stats('joint_logits',l,ln)
 ids=result['token_ids_including_blanks'][0][1:];dur=result['durations'][0][1:];ni=[s[2] for s in steps];nd=[s[4] for s in steps]
 if len(ids)!=len(l) or len(dur)!=len(ids) or len(steps)!=len(ln):raise ValueError('step count mismatch')
 print('torch token IDs',ids);print('native token IDs',ni);print('torch durations',dur);print('native durations',nd)
 print('token mismatches',[(i,a,b) for i,(a,b) in enumerate(zip(ids,ni)) if a!=b]);print('duration mismatches',[(i,a,b) for i,(a,b) in enumerate(zip(dur,nd)) if a!=b])
 sys.exit(1 if ids!=ni or dur!=nd else 0)
except Exception as e:
 print('HARNESS ERROR',repr(e));sys.exit(2)
