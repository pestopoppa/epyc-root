import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import resource_budget,pincheck
D=Path(__file__).resolve().parent
pincheck.verify(D,D/"SOURCE-MANIFEST-v15.json",os.environ["YARN_BUNDLE_SHA"],lambda:True)
print(json.dumps(resource_budget.check(Path("/mnt/micron/refactor-yarn-s2-v32-20261031/cohort"))))
