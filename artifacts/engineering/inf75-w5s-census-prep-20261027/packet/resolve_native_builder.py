"""Resolve the current builder as a pure read-only operation, never start a server."""
import hashlib,json
from pathlib import Path
from src.registry_loader import RegistryLoader
from scripts.server import orchestrator_stack as launcher
from scripts.server.stack_numa import _numa_prefix
D=Path(__file__).resolve().parent;O=D.parent/'orch-main'
registry=RegistryLoader(O/'orchestration/model_registry.yaml',validate_paths=False)
role=registry.get_role('architect_general')
argv=launcher.build_server_command(role,8074,numa_instance=0,prepare_runtime_dirs=False)
base={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'}
env=launcher.build_launch_env('architect_general',base)
sources=[O/'orchestration/model_registry.yaml',O/'orchestration/stack_topology.yaml',
         O/'orchestration/launch_manifest.yaml',Path(launcher.STACK_PRIORS_PATH),Path(launcher.__file__)]
pins=[{'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources]
(D/'native-builder.json').write_text(json.dumps({'argv':_numa_prefix('architect_general',0)+argv,
 'environment':env,'sources':pins,'scope':'resolved current source builder; no launch'},indent=2)+'\n')
