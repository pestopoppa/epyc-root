"""Run `<script> <args...>` as __main__ under canary_guard (same write/socket/subprocess rules)."""
import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import canary_guard  # noqa: E402

canary_guard.install()
sys.path.pop(0)
script = sys.argv[1]
sys.argv = [script, *sys.argv[2:]]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name="__main__")
