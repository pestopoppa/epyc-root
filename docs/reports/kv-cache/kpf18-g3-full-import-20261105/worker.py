import importlib.util,json,sys
from pathlib import Path
base=Path(sys.argv[1]); p=base/'driver.py'
spec=importlib.util.spec_from_file_location('kpf18_actual_driver',p); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
items={name:str(Path(m.__file__).resolve()) for name,m in sys.modules.items() if getattr(m,'__file__',None) and str(Path(m.__file__).resolve()).startswith(str(base))}
print(json.dumps({'module_count':len(items),'modules':items,'main_callable':callable(mod.main),'setup_callable':callable(mod.setup),'gate_run_callable':callable(mod.gate.Run)}))
