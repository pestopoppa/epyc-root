#!/usr/bin/env python3
"""Prospective shared CS8-STT1 split policy. No corpus inference in this file."""
LIMIT=30*16000
class NoVadBoundary(ValueError): pass

def plan(n_samples,spans):
 """Partition whole input at last VAD speech-end before each 30 s limit.
 Return adjacent half-open bounds; fail rather than cut inside speech. The caller
 must bind the pinned full-clip VAD stdout and PCM hashes before calling.
 """
 if n_samples<=0: raise ValueError('empty clip')
 prev=0
 for a,b in spans:
  if not (prev<=a<b<=n_samples): raise ValueError('invalid VAD spans')
  prev=b
 bounds=[]; start=0
 while n_samples-start>LIMIT:
  candidates=[b for a,b in spans if start<b<=start+LIMIT and b<n_samples]
  if not candidates: raise NoVadBoundary('no speech end within next 30 seconds')
  end=candidates[-1]
  bounds.append((start,end));start=end
 bounds.append((start,n_samples))
 if any(not (a<b and b-a<=LIMIT) for a,b in bounds): raise AssertionError('invalid partition')
 if bounds[0][0]!=0 or bounds[-1][1]!=n_samples or any(bounds[i][1]!=bounds[i+1][0] for i in range(len(bounds)-1)): raise AssertionError('noncontiguous')
 return bounds
if __name__=='__main__':
 assert plan(16000,[])==[(0,16000)]
 assert plan(800000,[(0,200000),(240000,400000),(500000,700000)])==[(0,400000),(400000,800000)]
 assert plan(960000,[(0,480000),(500000,900000)])==[(0,480000),(480000,960000)]
 try: plan(500000,[(0,500000)])
 except NoVadBoundary: pass
 else: raise AssertionError('cut inside speech')
 for spans in ([(0,500),(499,600)],[(0,600000)]):
  try: plan(500000,spans)
  except ValueError: pass
  else: raise AssertionError('invalid spans accepted')
 print('6 partition/no-cut synthetic fixtures pass')
