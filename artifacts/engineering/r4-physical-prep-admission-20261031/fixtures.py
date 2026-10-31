import importlib.util
from pathlib import Path
p=Path(__file__).parent
spec=importlib.util.spec_from_file_location('old','/mnt/raid0/llm/tmp/codex3-ap66-20261031/supervisor-esrch-fix/prep_admission.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
import prep_admission as new
now=1800000000
start='2020-01-01T00:00:00+00:00';end='2040-01-01T00:00:00+00:00'
def record(i,r): return (i,f'regions={r} start={start} end={end}')
def run(mod,pair,rows,rs):
 try: mod.check(set(pair),rows,rs,now); return 'allow'
 except ValueError: return 'refuse'
timing={'t':'block-timing-quiet'}; correctness={str(i):'block-correctness' for i in range(4)}
quarters=[record(str(i),f'q{i}') for i in range(4)]
cases=[('free physical beside GPU timing', [74,75],timing,[record('t','184-191,mi210_0')],'allow'),('physical overlap', [74,75],timing,[record('t','74')],'refuse'),('SMT sibling physical overlap',[74,75],timing,[record('t','170')],'refuse'),('whole host timing',[74,75],timing,[record('t','0-95')],'refuse'),('SMT timing',[122,123],timing,[record('t','184-191')],'refuse'),('SMT correctness quarters',[122,123],correctness,quarters,'allow'),('SMT free quarter',[122,123],correctness,quarters[:3],'refuse'),('SMT raw overlap',[122,123],correctness,quarters+[record('0','122')],'refuse'),('unknown class',[74,75],{'t':'unknown'},[record('t','0')],'refuse'),('malformed',[74,75],timing,[('t','bad')],'refuse'),('wrong pair size',[74],timing,[],'refuse')]
assert run(old,*cases[0][1:4])=='refuse'
for name,pair,rows,rs,want in cases:
 got=run(new,pair,rows,rs);print(name,got,flush=True);assert got==want
 if name in ('unknown class','malformed','wrong pair size'): assert run(old,pair,rows,rs)==want
print('original free physical beside GPU timing: refuse; corrected: allow',flush=True)
