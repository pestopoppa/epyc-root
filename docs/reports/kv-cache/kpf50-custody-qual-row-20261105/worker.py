import importlib.util,sys,os,json,hashlib,signal
from pathlib import Path
D=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('sealed_supervisor',D/'supervisor.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
m.D=Path(sys.argv[1]); sys.argv=[str(D/'supervisor.py')]
# Explicit qualification-only hook: no model metadata or target admission is reachable.
def synthetic_admission():
    for p,h in json.loads((D/'inputs.json').read_text()).items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h: raise ValueError('qualification input drift')
m.model_admission=synthetic_admission
signal.signal(signal.SIGTERM,m.stop_signal); signal.signal(signal.SIGINT,m.stop_signal)
m.main()
