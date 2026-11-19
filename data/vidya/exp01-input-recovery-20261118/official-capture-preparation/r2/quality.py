#!/usr/bin/env python3
"""EXP-01 quality slice: each pinned item on control then intervention (greedy, seed 42); one unit per item x arm.
ITEMS jsonl: {"id","prompt","expect_regex"}; item hash = sha256(prompt + expect_regex). Resume by unit id."""
import hashlib, json, re, subprocess, sys, time, os

from capture import emit

R, items, cli, cpus, threads, end, stop = sys.argv[1:8]
arms = dict(a.split("=", 1) for a in sys.argv[8:])
done = {json.loads(l).get("unit") for l in open(R) if l.strip()}
for line in open(items):
    it = json.loads(line)
    h = hashlib.sha256((it["prompt"] + it["expect_regex"]).encode()).hexdigest()[:16]
    for arm in ("Q4KM", "IQ4KT"):
        u = f"q-{arm}-{it['id']}"
        if u in done or not arms.get(arm):
            continue
        if os.path.exists(stop) or time.time() >= int(end):
            sys.exit(0)
        t = time.time()
        p = subprocess.run(["taskset", "-c", cpus, cli, "-m", arms[arm], "-p", it["prompt"], "-n", "256", "--temp", "0",
                            "--seed", "42", "-t", threads, "--no-display-prompt"], capture_output=True, text=True, env=dict(os.environ,EXP01_LAUNCH_UNIT=u))
        out = p.stdout
        rec = {"unit": u, "kind": "quality", "arm": arm, "item": it["id"], "item_hash": h, "rc": p.returncode,
               "correct": bool(re.search(it["expect_regex"], out)), "duration_s": round(time.time() - t, 2), "output": out, "item_native":it, "cpus":cpus,"threads":int(threads)}
        emit(R,rec)
