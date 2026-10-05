import json, sys
from pathlib import Path
import pytest
output,module_path,rootdir=Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]).resolve()
class Capture:
    def pytest_collection_finish(self,session):
        output.write_text(json.dumps({"schema":"ni61.pytest_collection.v1","module_path":module_path,"count":len(session.items),"nodeids":[item.nodeid for item in session.items]},sort_keys=True)+"\n",encoding="utf-8")
rc=pytest.main(["--collect-only","-q","-p","no:cacheprovider",f"--rootdir={rootdir}",module_path],plugins=[Capture()])
raise SystemExit(rc)
