"""Only ROOT source-isolated synthetic controls; never import APP."""
import importlib,os,sys
from pathlib import Path
workspace=Path(os.environ['GITHUB_WORKSPACE']).resolve()
recipe=workspace/'recipe'
os.environ['MF_TRACE_SOURCE']=str(workspace/'app/src/graph/helpers.py')
sys.path.insert(0,str(recipe))
name='tests.test_mf_trace_contract'
module=importlib.import_module(name)
if Path(module.__file__).resolve()!=(recipe/'tests/test_mf_trace_contract.py').resolve():raise RuntimeError('wrong test checkout')
import pytest
raise SystemExit(pytest.main(['--pyargs',name,'-c','/dev/null','--rootdir',str(workspace),
 '--noconftest','--import-mode=importlib','-o','consider_namespace_packages=True',
 '-o','addopts=','-p','no:cacheprovider','-q','--junitxml='+sys.argv[1]]))
