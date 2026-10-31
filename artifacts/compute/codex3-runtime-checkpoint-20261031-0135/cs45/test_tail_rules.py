import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'source'))
from tail_rules import parakeet_fires
short,sc=parakeet_fires([1.0]*50+[0.0]*10,[],1.92,2.5)
long,lc=parakeet_fires([1.0]*50+[0.0]*125,[],5.6,2.5)
assert short==[] and sc is True
assert len(long)==1 and 4.1 <= long[0] <= 4.14 and lc is False
print('synthetic short tail censored, 4s tail long-silence fallback fires: PASS')
