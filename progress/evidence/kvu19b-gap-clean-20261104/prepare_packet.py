from pathlib import Path
import ast,json,hashlib,shutil
D=Path(__file__).resolve().parent
old=Path('/mnt/raid0/llm/tmp/kvu/kvu19a2-gpu-repeat-20261104/producer.py').read_text();tree=ast.parse(old)
needed={'birth_ticks','proc_group_members','terminate_owned','child_setup','maps_proof','read_kfd','validate_cpu_grant'}
support='import os,signal,subprocess,time,ctypes,re\nfrom pathlib import Path\nimport device_identity\nclass Refusal(RuntimeError): pass\n'
support+='\n\n'.join(ast.get_source_segment(old,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in needed)
(D/'custody.py').write_text(support+'\n')
a=json.loads((D/'assets.json').read_text());a['libraries']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (D/'bin').glob('*.so*') if not p.is_symlink()};(D/'assets.json').write_text(json.dumps(a,indent=2)+'\n')
