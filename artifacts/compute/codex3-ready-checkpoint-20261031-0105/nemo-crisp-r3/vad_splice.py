#!/usr/bin/env python3
"""Draft: apply frozen whisper.cpp VAD compaction policy to native VAD spans."""
import re

def splice(pcm,segments):
 if len(pcm)%2: raise ValueError('PCM16 required')
 n=len(pcm)//2; out=bytearray(); mapping=[]
 for i,(start,end) in enumerate(segments):
  if not (0<=start<end<=n): raise ValueError('bad boundaries')
  if i and start<segments[i-1][1]: raise ValueError('overlapping native spans')
  # Frozen reference rounds detected sample positions to nearest centisecond.
  a=min(((start+80)//160)*160,n-1); b=min(((end+80)//160)*160,n-1)
  end_orig=b
  if i+1<len(segments): b=min(b+1600,n-1)
  if b<=a: raise ValueError('empty quantized span')
  offset=len(out)//2; out.extend(pcm[2*a:2*b]); mapping.append((offset,offset+end_orig-a,a,end_orig))
  if i+1<len(segments): out.extend(bytes(3200))
 return bytes(out),mapping

def parse(text):
 result=[]
 for line in text.splitlines():
  m=re.fullmatch(r'\s*segment: (\d+) start=(\d+) end=(\d+) t0=[\d.]+ t1=[\d.]+',line)
  if m:
   if int(m[1])!=len(result): raise ValueError('segment index')
   result.append((int(m[2]),int(m[3])))
  elif 'segment:' in line: raise ValueError('malformed segment')
 match=re.search(r'^speech segments: (\d+)\s*$',text,re.M)
 if not match or int(match[1])!=len(result) or not re.search(r'^run: ok\s*$',text,re.M): raise ValueError('incomplete VAD output')
 return result

if __name__=='__main__':
 pcm=b''.join(i.to_bytes(2,'little') for i in range(5000))
 out,m=splice(pcm,[(160,480),(3200,4000)])
 assert out==pcm[320:4160]+bytes(3200)+pcm[6400:8000]
 assert m==[(0,320,160,480),(3520,4320,3200,4000)]
 assert parse('run: ok\nspeech segments: 1\n  segment: 0 start=160 end=480 t0=0.010 t1=0.030\n')==[(160,480)]
 try: parse('run: ok\nspeech segments: 1\n')
 except ValueError: pass
 else: raise AssertionError('missing segment accepted')
 print('synthetic splice/parser fixtures pass')
