import json,os,platform,sys,sysconfig,subprocess
from pathlib import Path
from datetime import datetime,timezone
out=Path(sys.argv[1]);out.mkdir(exist_ok=True)
record={"UTC":datetime.now(timezone.utc).isoformat(),"argv":sys.argv,"cwd":os.getcwd(),"python":sys.version,"executable":sys.executable,"platform":platform.platform(),"implementation":platform.python_implementation(),"SOABI":sysconfig.get_config_var("SOABI"),"job_env":{k:v for k,v in os.environ.items() if k.startswith("GITHUB_") or k in ("EPYC_ROOT","PYTHONPATH","PYTEST_DISABLE_PLUGIN_AUTOLOAD","PYTHONDONTWRITEBYTECODE")},"proposal_only":True}
(out/"runtime.json").write_text(json.dumps(record,indent=2)+"\n")
r=subprocess.run([sys.executable,"-m","pip","freeze","--all"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(out/"pip-freeze.stdout").write_bytes(r.stdout);(out/"pip-freeze.stderr").write_bytes(r.stderr);(out/"pip-freeze.exit").write_text(str(r.returncode)+"\n")
