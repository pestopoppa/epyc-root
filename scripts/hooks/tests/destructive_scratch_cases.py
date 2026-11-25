"""Fixture cases for test_destructive_scratch_hook.sh. Emits JSON to stdout.

Dangerous strings are assembled from pieces so this file itself never contains a runnable
delete line. Args: FIXTURE_DIR (mktemp dir holding purge_batch.py) FAKE_ROOT.
"""
import json
import sys

fx, fake = sys.argv[1], sys.argv[2]
R = "rm"; RF = R + " -" + "rf"; T = "/mnt/raid0/llm/tm" + "p"
W = "/mnt/raid0/llm/work" + "trees"; TR = "/mnt/raid0/llm/." + "trash"; ST = "/mnt/raid0/llm/sta" + "te"
RT = "shutil" + ".rmtree"
RD = "os.rm" + "dir"
DEL = "-" + "delete"


def _fixture(name: str, body: str) -> str:
    """Write a script fixture into the (mktemp) fixture dir; return its path."""
    p = f"{fx}/{name}"
    with open(p, "w") as f:
        f.write(body)
    return p


# Target-scoped script scan (operator 2026-11-25): the primitive must TARGET a protected root.
py_root_rmtree = _fixture("tp_rmtree_root.py",
    f"import shutil\nfrom pathlib import Path\nROOT = Path('{T}')\n{RT}(ROOT / 'old')\n")
sh_root_rf = _fixture("tp_rf_root.sh", f"#!/bin/bash\necho start\n{RF} {W}/stale\n")
sh_root_find = _fixture("tp_find_root.sh", f"#!/bin/bash\nfind {TR}/b1 -mtime +7 {DEL}\n")
py_runend = _fixture("fp_runend_mkdtemp.py",
    f"import os, tempfile\nTMP = '{T}'\nFLAGS = '{T}/compute-flags'\n"
    f"def probe():\n    d = tempfile.mkdtemp(prefix='runend-')\n    {RD}(d)\n    return FLAGS\n")
py_mkdtemp_under_root = _fixture("fp_mkdtemp_dir_root.py",
    f"import shutil, tempfile, os\nwork = tempfile.mkdtemp(dir='{T}')\nsub = os.path.join(work, 'a')\n"
    f"{RT}(sub)\n{RT}(work)\n")
py_tempdir_ctx = _fixture("fp_tempdir_ctx.py",
    f"import os, tempfile\nOUT = '{ST}/x.json'\nwith tempfile.TemporaryDirectory() as td:\n"
    f"    p = os.path.join(td, 'f')\n    os.re" + "move(p)\n")
py_obfuscated = _fixture("tp_obfuscated_two_hop.py",
    f"import os, shutil\nBASE = '{T}'\n_parts = ['a', 'b']\nmid = os.path.join(BASE, *_parts)\n"
    f"victim = mid + '/c'\n{RT}(\n    victim,\n    ignore_errors=True,\n)\n")
sh_obfuscated = _fixture("tp_obfuscated_two_hop.sh",
    f"#!/bin/bash\nset -euo pipefail\nD={ST}\nE=\"${{D}}/q\"\nfor x in \"$E\"/*; do\n  find \"$x\" {DEL}\ndone\n")
py_loop_taint = _fixture("tp_for_loop.py",
    f"from pathlib import Path\nROOT = Path('{T}')\nfor p in ROOT.iterdir():\n    p.unl" + "ink()\n")
cases = [
 ("script rmtree ROOT/x", "block", f"python3 {py_root_rmtree}", {}),
 ("script rf root", "block", f"bash {sh_root_rf}", {}),
 ("script find root delete", "block", f"bash {sh_root_find}", {}),
 ("script obfuscated two-hop multi-line rmtree", "block", f"python3 {py_obfuscated}", {}),
 ("script obfuscated shell two-hop find", "block", f"bash {sh_obfuscated}", {}),
 ("script for-loop over root unlink", "block", f"python3 {py_loop_taint}", {}),
 ("script runend mkdtemp+rmdir", "allow", f"python3 {py_runend}", {}),
 ("script mkdtemp(dir=root) rmtree", "allow", f"python3 {py_mkdtemp_under_root}", {}),
 ("script TemporaryDirectory remove", "allow", f"python3 {py_tempdir_ctx}", {}),
 # (name, expected, command, env)
 ("rf tmp", "block", f"{RF} {T}/x", {}),
 ("r worktrees", "block", f"{R} -r {W}/foo", {}),
 ("long recursive", "block", f"{R} --recursive {T}/x", {}),
 ("find delete", "block", f"find {T}/a -" + "delete", {}),
 ("find exec rm", "block", f"find {T}/a -exec {R} {{}} ;", {}),
 ("py -c rmtree trash", "block", f"python3 -c \"import shutil; {RT}('{TR}/abc')\"", {}),
 ("py -c os.remove", "block", f"python3 -c \"import os; os.re" + f"move('{T}/f')\"", {}),
 ("purge_batch file", "block", f"python3 {fx}/purge_batch.py", {}),
 ("var after root", "block", f"{RF} {T}/$X", {}),
 ("braced var after root", "block", f"{RF} \"{T}/${{X}}\"", {}),
 ("heredoc python", "block", f"python3 - <<'EOF'\nimport shutil\n{RT}('{ST}/x')\nEOF", {}),
 ("chain cd", "block", f"cd /x && {RF} {T}/y", {}),
 ("dotdot", "block", f"{RF} {T}/a/../b", {}),
 ("rmdir nonempty", "block", f"rmdir {fake}/full", {"EPYC_DESTRUCTIVE_SCRATCH_ROOTS": fake}),
 ("fake root rf", "block", f"{RF} {fake}/full", {"EPYC_DESTRUCTIVE_SCRATCH_ROOTS": fake}),
 ("assigned literal var", "block", f"X={T}/q; {RF} $X", {}),
 ("guarded_rm", "allow", f"bash scripts/safety/guarded_rm.sh {T}/x", {}),
 ("trash-sweep", "allow", "bash scripts/safety/trash-sweep.sh --older-than 7", {}),
 ("reclaim_scratch", "allow", "python3 scripts/system/reclaim_scratch.py plan", {}),
 ("mktemp subst", "allow", f"{RF} \"$(mktemp -d)\"", {}),
 ("mktemp trap idiom", "allow", f"TMP=$(mktemp -d); trap '{RF} \"$TMP\"' EXIT; echo hi", {}),
 ("mktemp var rm", "allow", f"TMP=$(mktemp -d); {RF} \"$TMP\"", {}),
 ("bare tmp", "allow", f"{RF} /tmp/foo", {}),
 ("scratchpad", "allow", f"{RF} /tmp/claude-1000/x/scratchpad/y", {}),
 ("plain rm", "allow", f"{R} {T}/single.txt", {}),
 ("ls", "allow", f"ls -la {T}", {}),
 ("grep -r word", "allow", f"grep -r rmtree {T}", {}),
 ("echo mention", "allow", f"echo \"{RF} {T}/x\"", {}),
 ("unknown var", "allow", f"{RF} $UNKNOWN", {}),
 ("rmdir empty", "allow", f"rmdir {fake}/empty", {"EPYC_DESTRUCTIVE_SCRATCH_ROOTS": fake}),
 # LOOP-53 (operator decision B, 2026-11-02): no override exists; the old env name is ignored.
 ("former override env ignored", "block", f"{RF} {T}/x", {"EPYC_ALLOW_SCRATCH_DELETE": "operator: dp 2026-10-25: test"}),
 ("malformed former override ignored", "block", f"{RF} {T}/x", {"EPYC_ALLOW_SCRATCH_DELETE": "yes please"}),
 ("script sans root", "allow", f"python3 {fx}/harmless.py", {}),
 ("tmp-prefix lookalike", "allow", f"{RF} /mnt/raid0/llm/tmp-other/x", {}),
]
out = [{"name": n, "expect": e, "input": {"tool_name": "Bash", "tool_input": {"command": c}}, "env": v}
       for n, e, c, v in cases]
out.append({"name": "non-Bash tool", "expect": "allow",
            "input": {"tool_name": "Write", "tool_input": {"command": f"{RF} {T}/x"}}, "env": {}})
out.append({"name": "no command", "expect": "allow", "input": {"tool_name": "Bash", "tool_input": {}}, "env": {}})
out.append({"name": "malformed json", "expect": "allow", "raw": "{not json", "env": {}})
json.dump(out, sys.stdout)
