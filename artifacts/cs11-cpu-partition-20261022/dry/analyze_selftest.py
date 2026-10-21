#!/usr/bin/env python3
"""Synthetic-data self-test of analyze.py (no inference). Cleans up after itself."""
import json, os, random, shutil, subprocess
R = "/mnt/raid0/llm/tmp/cs11-20261022"; S = f"{R}/dry/antest"
shutil.rmtree(S, ignore_errors=True); os.makedirs(f"{S}/raw")
random.seed(1)
with open(f"{S}/raw/arms.jsonl", "w") as f:
    for role, base in (("frontdoor", 36.8), ("architect_general", 31.2)):
        for i, c in enumerate("FPFPFPF", 1):
            m = base * (1 if c == "F" else 0.76) * random.uniform(.99, 1.01)
            f.write(json.dumps({"kind": "arm", "role": role, "arm": c, "idx": i, "arm_mean_tok_s": m, "n_good": 4,
                                "reqs": [{"tok_s": m * random.uniform(.98, 1.02)} for _ in range(4)], "arm_draft_acc_rate": .5}) + "\n")
for extra in ([], ["--cs9-loss", "0.12", "--cs9-speech-ok", "yes"]):
    o = subprocess.run(["python3", f"{R}/analyze.py", *extra], env={**os.environ, "CS11_DIR": S}, capture_output=True, text=True)
    print(o.returncode, o.stdout[-900:], o.stderr[-500:])
shutil.rmtree(S, ignore_errors=True)
