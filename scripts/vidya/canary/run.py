#!/usr/bin/env python3
"""Run one replay; missing dependencies and crashes are UNKNOWN, never a pass."""
import json
import subprocess
import sys
from pathlib import Path

if len(sys.argv) < 2 or sys.argv[1] not in ("a", "b", "cc"):
    raise SystemExit("usage: run.py a LABEL ROOT | run.py b | run.py cc ROOT")
script = Path(__file__).with_name("canary_" + sys.argv[1] + ".py")
proc = subprocess.run([sys.executable, str(script), *sys.argv[2:]], text=True,
                      stdout=subprocess.PIPE)
print(proc.stdout, end="")
markers = [line.removeprefix("CANARY_RESULT: ") for line in proc.stdout.splitlines()
           if line.startswith("CANARY_RESULT: ")]
try:
    result = json.loads(markers[-1]) if len(markers) == 1 else {}
    if not isinstance(result, dict):
        raise ValueError("non-object result")
    expected = {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}
    if expected.get(result.get("status")) != proc.returncode:
        raise ValueError("missing or inconsistent result")
except (ValueError, TypeError):
    result = {"loop": sys.argv[1].upper(), "status": "UNKNOWN",
              "reason": "replay unavailable or crashed", "child_exit": proc.returncode}
print("GATE_RESULT:", json.dumps(result))
sys.exit({"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[result["status"]])
