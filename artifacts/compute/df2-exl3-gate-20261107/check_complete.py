#!/usr/bin/env python3
import json, sys
try:
    r = json.load(open("/mnt/raid0/llm/tmp/df2-exl3-gate-20261107/out/RESULT.json"))
except Exception:
    sys.exit(1)
sys.exit(0 if r.get("verdict") in ("PASS", "FAIL") else 1)
