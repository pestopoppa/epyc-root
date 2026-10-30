import os,subprocess,sys
from pathlib import Path
from src.repl_environment.exec_sandbox import wrap,Policy,credential_paths
D=Path(__file__).parent;root=D/('gold-fence-'+str(os.getpid()));root.mkdir();(root/'prompt.json').write_text('{"prompt":"fixture"}')
deny=credential_paths()+[str(D/'CONTROL-PRIVATE.json'),'/mnt/raid0/llm/datasets','/mnt/raid0/llm/hf-home/datasets','/mnt/raid0/llm/tmp/evl34-real-natural-delegation-20261029','/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/hotpot-validation-first10.json']
script='''import sys\nfrom pathlib import Path\nassert Path(sys.argv[1]).read_text()\nfor x in sys.argv[2:]:\n try:open(x,'rb').read(1)\n except PermissionError:pass\n else:raise AssertionError('restricted source readable: '+x)\nprint('prompt readable and known gold/source paths denied')'''
arrow='/mnt/raid0/llm/hf-home/datasets/hotpotqa___hotpot_qa/distractor/0.0.0/1908d6afbbead072334abe2965f91bd2709910ab/hotpot_qa-validation.arrow'
cmd,extra=wrap([sys.executable,'-c',script,str(root/'prompt.json'),str(D/'CONTROL-PRIVATE.json'),arrow,'/mnt/raid0/llm/datasets/turnbench-dev-c29aa4e6/MANIFEST.json','/mnt/raid0/llm/hf-home/datasets/Eureka-Lab___phy_bench/default/0.0.0/d6d91c787b7abb865eb2490a328bf85a9f5095f0/dataset_info.json','/mnt/raid0/llm/tmp/evl34-real-natural-delegation-20261029/prospective-hotpotqa-pilot-v1.json'],policy=Policy(),extra_allow=[str(root)],deny_paths=deny)
env=os.environ.copy();env.update(extra)
p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=10)
assert p.returncode==0,(p.stdout,p.stderr)
print(p.stdout.strip())
