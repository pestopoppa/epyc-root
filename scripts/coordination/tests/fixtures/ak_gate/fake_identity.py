#!/usr/bin/env python3
"""A stand-in identity test binary for ak_gate tests (copied to <tmp>/bin/test-dflash-fake). It prints the same line
shapes as test-dflash-dev-inject SINGLE mode (single-draft / single-accepted / single-output), one (arm, prompt) per
process. FAKE_ID_KNOB set: draft round 2 differs (a drafter near-tie) but accepted counts and the output do not;
FAKE_ID_OUTPUT_FLIP set: the output differs too. Each process appends its pid to FAKE_ID_PIDS. Knob markers print at
-lv >= 4 only (FAKE_MARKERS, as the fake server)."""
import json
import os
import sys

argv = sys.argv[1:]
lv = int(argv[argv.index("-lv") + 1]) if "-lv" in argv else 3
prompt = int(argv[argv.index("--prompt") + 1]) if "--prompt" in argv else 0
markers = json.loads(os.environ.get("FAKE_MARKERS") or "{}")
if lv >= 4:
    for k, m in markers.items():
        if os.environ.get(k):
            print(f"0.05.374.054 I {m}")
if os.environ.get("FAKE_ID_PIDS"):
    with open(os.environ["FAKE_ID_PIDS"], "a") as f:
        f.write(f"{os.getpid()} {prompt}\n")
knob = bool(os.environ.get(os.environ.get("FAKE_ID_KNOB") or "\0"))
for r in range(4):
    d = [100 + prompt, 200 + r, 300]
    if knob and r == 2:
        d[2] = 999
    print(f"single-draft: {r} " + ",".join(map(str, d)) + ",")
print("single-accepted: 3,3,2,3,")
out = [7, 8, 9, prompt]
if os.environ.get("FAKE_ID_OUTPUT_FLIP") and knob:
    out[1] = 42
print("single-output: " + ",".join(map(str, out)) + ",")
print("SINGLE-DONE")
