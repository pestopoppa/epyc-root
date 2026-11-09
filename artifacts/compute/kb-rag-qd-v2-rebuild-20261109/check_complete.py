#!/usr/bin/env python3
"""rc 0 iff out/RESULT.json is complete with a terminal verdict PASS or FAIL."""
import json, sys
try:
    r = json.load(open('/mnt/raid0/llm/tmp/kb-rag-qd-v2-rebuild-20261109/out/RESULT.json'))
except (OSError, ValueError):
    sys.exit(1)
sys.exit(0 if r.get('complete') and r.get('verdict') in ('PASS', 'FAIL') else 1)
