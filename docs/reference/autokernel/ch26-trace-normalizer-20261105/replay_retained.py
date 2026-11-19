"""Replay one already-retained child-scoped switch from each CPU, no live capture."""
import hashlib
import json
import struct
import sys
from pathlib import Path
from trace_normalizer import parse_format, decode_sample

ROOT = Path('/mnt/raid0/llm/tmp/akagg/ch26-r2-retained')
EXPECTED = '57ff7749b88c79078afd42a62b7a19b487b92d8111b98d398eeb0032aac97d77'

def main():
 raw=(ROOT/'manifest.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=EXPECTED: raise ValueError('manifest digest mismatch')
 doc=json.loads(raw)
 if doc['schema']!='epyc.ch26.owned-child-perf-evidence.v1' or len(doc['captures'])!=4: raise ValueError('unexpected manifest')
 cpus=set()
 for c in doc['captures']:
  cpu=c['cpu']
  if cpu in cpus or cpu not in range(4): raise ValueError('CPU census differs')
  cpus.add(cpu)
  if c['raw_file'] != f'cpu-{cpu}.ring': raise ValueError('invalid raw path')
  ring=(ROOT/c['raw_file']).read_bytes()
  if hashlib.sha256(ring).hexdigest()!=c['raw_sha256'] or len(ring)!=c['raw_size']:raise ValueError('ring custody mismatch')
  if c['tail']!=0 or c['head']<8 or c['head']>len(ring):raise ValueError('unexpected ring range')
  typ,_,size=struct.unpack_from('<IHH',ring)
  if typ!=9 or size!=c['head'] or size>len(ring):raise ValueError('expected exactly one perf sample')
  fields=parse_format(c['trace_format'],c['tracepoint_id'])
  e=decode_sample(ring[8:size],cpu=cpu,event_id=c['event_id'],tracepoint_id=c['tracepoint_id'],fields=fields)
  if e['prev_tid']!=c['target']['pid'] or e['sample_pid']!=c['target']['pid'] or e['sample_tid']!=c['target']['pid']:raise ValueError('owned child identity mismatch')
  print(f"cpu={cpu} prev_tid={e['prev_tid']} next_tid={e['next_tid']} timestamp_ns={e['timestamp_ns']}")
 print('Four retained child-scoped switch samples decoded; coverage and contention remain unproven.')
if __name__=='__main__':main()
