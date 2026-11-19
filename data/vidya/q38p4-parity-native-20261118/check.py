import json
import os
from pathlib import Path
import sys

from settings import ROOT


def main():
    smoke = len(sys.argv) > 1 and sys.argv[1] == "smoke"
    env = os.environ.get("FILLER_DRYRUN_RESULT_PATH")
    if smoke and not env:
        return 1
    path = Path(env) if smoke else ROOT / "official" / "RESULT.json"
    try:
        result = json.loads(path.read_bytes())
        timestamp = int(os.environ.get("FILLER_SMOKE_T0", "0"))
        return int(not (result["accepted"] is True
                        and result["mode"] == ("smoke" if smoke else "native")
                        and result["status"] in ({"smoke-pass"} if smoke else {"match", "divergence"})
                        and (not smoke or result["finished_ns"] >= timestamp * 10**9)
                        and Path(result["capture"]).is_file()))
    except (OSError, ValueError, KeyError, TypeError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
