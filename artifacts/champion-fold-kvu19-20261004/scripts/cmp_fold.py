#!/usr/bin/env python3
"""cmp_fold.py: exactness criteria for the champion fold candidate (KVU-19a + KVU-19b commit 1 ONLY).

usage: cmp_fold.py <listing exact_*.txt> <crit> <dir_a> <dir_b>
  crit = ident      every supported case bit-identical
         vec_only   every non-identical case is a vec-routed case (hint >= nb, hs 128/256, type != bf16)
         ref        nmse < 5e-4 for every case (dir_b = reference)
Prints one line starting with PASS/FAIL. Exit 0 PASS, 1 FAIL.
"""
import re
import sys

import numpy as np

listing, crit, a, b = sys.argv[1:5]
cases = {}
for line in open(listing):
    if line.startswith("case") and "unsupported" not in line:
        cases[int(line.split()[1])] = line


def vec_routed(line: str) -> bool:
    hint = re.search(r"hint=(\d+)", line)
    nb = re.search(r" nb=(\d+)", line)
    hs = re.search(r"hs=(\d+)/", line)
    typ = re.search(r"type=(\S+)", line)
    if not (hint and nb and hs and typ):
        return False
    return int(hint.group(1)) >= int(nb.group(1)) and int(hs.group(1)) in (128, 256) and typ.group(1) != "bf16"


bad, worst, worst_case, missing, diff = [], 0.0, None, 0, 0
for i, line in sorted(cases.items()):
    try:
        x = np.fromfile(f"{a}/out_{i:02d}.bin", dtype=np.float32)
        y = np.fromfile(f"{b}/out_{i:02d}.bin", dtype=np.float32)
    except FileNotFoundError:
        missing += 1
        bad.append(f"case {i}: output missing")
        continue
    same = x.size == y.size and np.array_equal(x.view(np.uint32), y.view(np.uint32))
    nmse = float(((x - y) ** 2).sum() / max((y ** 2).sum(), 1e-30)) if x.size == y.size else float("inf")
    if nmse > worst:
        worst, worst_case = nmse, i
    if not same:
        diff += 1
    if crit == "ident" and not same:
        bad.append(f"case {i}: not bit-identical nmse={nmse:.3g} :: {line.strip()[:160]}")
    elif crit == "vec_only" and not same and not vec_routed(line):
        bad.append(f"case {i}: differs and is NOT vec-routed nmse={nmse:.3g} :: {line.strip()[:160]}")
    elif crit == "ref" and not nmse < 5e-4:
        bad.append(f"case {i}: nmse={nmse:.3g} >= 5e-4 :: {line.strip()[:160]}")

n = len(cases)
if n == 0:
    print("FAIL no supported cases in listing (vacuous)")
    sys.exit(1)
verdict = "PASS" if not bad else "FAIL"
print(f"{verdict} crit={crit} {n} cases, {n - diff} bit-identical, {diff} differ, missing {missing}, "
      f"worst nmse {worst:.3g} (case {worst_case})")
for line in bad[:20]:
    print("   ", line)
sys.exit(0 if not bad else 1)
