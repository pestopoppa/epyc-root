"""Off-host whole-module controls with explicit repo roots; no APP or conftest."""
import importlib,os,sys
from pathlib import Path
workspace=Path(os.environ['GITHUB_WORKSPACE']).resolve()
recipe=workspace/'recipe';research=workspace/'research'
sys.path[:0]=[str(research),str(recipe),str(recipe/'scripts/vidya')]
# Explicit namespaces must find the selected real ROOT/Research sources, never another checkout.
modules=(
 'scripts.kernel_rnd.autokernel.loop.test_graph_profile_capture',
 'scripts.kernel_rnd.autokernel.loop.test_graph_profile_reader',
 'tests.test_graph_profile_measurement',
)
for name in modules:
 module=importlib.import_module(name)
 expected=(research/name.replace('.','/')).with_suffix('.py') if name.startswith('scripts.kernel_rnd.') else (recipe/name.replace('.','/')).with_suffix('.py')
 if Path(module.__file__).resolve()!=expected.resolve():raise RuntimeError('selected module resolved outside exact checkout')
import pytest
raise SystemExit(pytest.main(['--pyargs',*modules,'-c','/dev/null','--rootdir',str(workspace),
 '--noconftest','--import-mode=importlib','-o','consider_namespace_packages=True',
 '-o','addopts=','-p','no:cacheprovider','-q','--junitxml='+sys.argv[1]]))
