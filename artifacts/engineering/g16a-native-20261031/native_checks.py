import re
CASES=[(64,1),(256,1),(2048,1),(4096,1),(8192,1),(2048,2),(4096,2),(8192,2)]
NMSE_GATE=1e-7

def exact_numerical_pass(stdout,prefix,rc):
 text=re.sub(r'\x1b\[[0-9;]*m','',stdout)
 matching=[line for line in text.splitlines() if 'GATED_DELTA_NET('+prefix+'):' in line]
 return rc==0 and len(matching)==1 and matching[0].strip().endswith('OK')

def exact_trace_pass(events,tokens):
 pattern=r'H=32 S_v=128 n_tokens='+str(tokens)+r' n_seqs=2 blocks=512 \(floor (\d+)\), keep_rs=0 K=1'
 for event in events:
  match=re.search(pattern,event['line'])
  if match and 512>=int(match.group(1)):return True
 return False
