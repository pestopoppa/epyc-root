#!/usr/bin/env python3
"""Validate this attempt's completed synthetic pair; never a live-model verdict."""
import json
import os
from pathlib import Path

def main():
    try:
        path=Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
        root=Path(os.environ['FILLER_DRYRUN_DIR']).resolve(strict=True)
        if not path.resolve(strict=True).is_relative_to(root):
            return 1
        result=json.loads(path.read_bytes())
        return 0 if (result.get('scope')=='fixture-only' and result.get('capture_kind')=='fixture'
            and result.get('pass') is True
            and result.get('case_sha256')=='a4a4dbe4d264a1fc1572d5eff68314ce169d2990cfded1c5cfa6af6b69b44431') else 1
    except (OSError,KeyError,ValueError):
        return 1

if __name__=='__main__':
    raise SystemExit(main())
