#!/usr/bin/env python3
"""Indicative native canonicalization timing, deterministic synthetic inputs."""
import hashlib,json,os,platform,statistics,sys,time
from pathlib import Path
src=Path('/workspace/repos/epyc-orchestrator/src/inference/prefix_cache.py')
pin='8f075d9dd5716abb7838be75779c57c4031663a58eebbfd080efff0f39e929cb'
if hashlib.sha256(src.read_bytes()).hexdigest()!=pin:raise SystemExit('source mismatch')
sys.path.insert(0,'/workspace/repos/epyc-orchestrator')
from src.inference.prefix_cache import canonicalize_prompt
patterns={'plain':'A simple example of a text prompt with ordinary words.\n','mixed':'2024-01-15T10:30:00Z 550e8400-e29b-41d4-a716-446655440000\r\n\n\nHello world! '}
rows=[]
for length in (256,10000,100000,1000000):
 for name,pattern in patterns.items():
  text=(pattern*(length//len(pattern)+1))[:length]
  expected=canonicalize_prompt(text)
  for _ in range(5):assert canonicalize_prompt(text)==expected
  reps=100 if length<=10000 else 20 if length<=100000 else 3
  samples=[]
  for batch in range(9):
   start=time.perf_counter_ns()
   for _ in range(reps):canonicalize_prompt(text)
   samples.append((time.perf_counter_ns()-start)/reps)
  rows.append({'chars':length,'pattern':name,'samples_ns_per_call':samples,'median_ns_per_call':statistics.median(samples),'reps_per_batch':reps,'output_chars':len(expected)})
if hashlib.sha256(src.read_bytes()).hexdigest()!=pin:raise SystemExit('source changed')
print(json.dumps({'schema':'kv6.native-synthetic-timing.v1','source_sha256':pin,'python':sys.version,'affinity':sorted(os.sched_getaffinity(0)),'cpu':platform.processor(),'timing_scope':'R6 shared-host synthetic; median of 9 batches, not isolated production latency','rows':rows},sort_keys=True))
