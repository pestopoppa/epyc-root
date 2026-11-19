#!/usr/bin/env python3
"""Fail-closed parser for the source-pinned p3batch diagnostic clock marks."""
import re
RX=re.compile(r'^P3_CLOCK phase=(begin|end) step=([0-9]+) hsa_tick=([0-9]+) hsa_hz=([0-9]+) mono_before_ns=([0-9]+) mono_after_ns=([0-9]+)$')
def parse(text,steps):
 if type(steps) is not int or steps<1: raise ValueError('steps')
 rows=[]
 for line in text.splitlines():
  if line.startswith('P3_CLOCK_ERROR'): raise ValueError('clock error')
  if not line.startswith('P3_CLOCK'): continue
  m=RX.fullmatch(line)
  if not m: raise ValueError('malformed mark')
  phase=m[1]; step,tick,hz,lo,hi=map(int,m.groups()[1:])
  if hz<1000000 or hz>400000000 or not tick or not lo or hi<lo: raise ValueError('invalid clock')
  if rows and (lo<rows[-1]['hi'] or tick<rows[-1]['tick'] or hz!=rows[0]['hz']): raise ValueError('clock ordering/frequency')
  rows.append(dict(phase=phase,step=step,tick=tick,hz=hz,lo=lo,hi=hi))
 if len(rows)!=2*steps: raise ValueError('count')
 for i,r in enumerate(rows):
  if (r['phase'],r['step'])!=(('begin' if i%2==0 else 'end'),i//2): raise ValueError('phase/step')
 return rows
