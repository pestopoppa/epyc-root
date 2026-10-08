"""Whole unchanged copied proposal modules; fixtures only, no real gold or hook installation."""
import os,sys,json
from pathlib import Path
workspace=Path(os.environ["GITHUB_WORKSPACE"]).resolve();recipe=workspace/"recipe";here=Path(__file__).resolve().parent
suite=sys.argv[1];junit=sys.argv[2];manifest=json.loads((here/"source-map.json").read_text());tests=manifest["suites"][suite]["tests"]
if suite=="m12f":
 research=recipe/"proposed/m12f/payload/research";root=recipe/"proposed/m12f/payload/root"
 os.environ["EPYC_ROOT"]=str(root);sys.path[:0]=[str(research),str(research/"scripts/benchmark")]
else:
 os.environ.pop("EPYC_ROOT",None);sys.path.insert(0,str(recipe/"proposed/aud10/payload/scripts/hooks"))
import pytest
raise SystemExit(pytest.main([*[str(recipe/path) for path in tests],"-c","/dev/null","--rootdir",str(recipe),"--noconftest","--import-mode=importlib","-o","consider_namespace_packages=True","-o","addopts=","-p","no:cacheprovider","-q","--basetemp",str(Path(os.environ["RUNNER_TEMP"])/("proposal-native-"+suite)/"fake-tmp"),"--junitxml="+junit]))
