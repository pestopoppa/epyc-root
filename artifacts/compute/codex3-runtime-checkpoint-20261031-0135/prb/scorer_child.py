import json,sys,resource
from pathlib import Path
import sandbox,orch_debug_scorer as s
root=Path(__file__).resolve().parent/'score-tmp';root.mkdir(exist_ok=True)
s._SCORER_TMP_ROOT=root
payload=json.load(sys.stdin)
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3))
resource.setrlimit(resource.RLIMIT_CPU,(15,15))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
sandbox.install_landlock(str(root)); sandbox.install_seccomp()
try: print(json.dumps({'correct':s.score_answer(payload['answer'],payload.get('expected',''),'code_execution',payload['config'])}),flush=True)
except Exception as exc: print(json.dumps({'unknown':type(exc).__name__+': '+str(exc)}),flush=True)
