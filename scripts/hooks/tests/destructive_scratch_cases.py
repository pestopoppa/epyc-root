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
cases = [
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
 ("override", "allow", f"{RF} {T}/x", {"EPYC_ALLOW_SCRATCH_DELETE": "operator: dp 2026-10-25: test"}),
 ("bad override", "block", f"{RF} {T}/x", {"EPYC_ALLOW_SCRATCH_DELETE": "yes please"}),
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
