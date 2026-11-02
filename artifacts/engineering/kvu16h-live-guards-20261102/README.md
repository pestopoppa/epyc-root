# Live scratch P3/X0 refusal guards — 2026-11-02

The three adjacent patches describe exact edits applied to the named files under
`/mnt/raid0/llm/tmp/x0-27b-quants/`; `source-hashes.txt` records before/after
SHA-256s. These are the historical workspace-89 X0/P3 copies; the checks found
no process or open file using these three paths. The
only FILLERS reference to P3 v2 was a completed job using a vendored copy. The
older `x0_shape_b.py` was not edited because a historical armed row explicitly
pins its source hash.

P3 v2 now refuses unsafe A1 through both the CLI and direct A1/measurement
functions. The X0 probe refuses its CLI before preflight or output and rejects a
direct request-level zero override; shape-B v2 refuses `--with-probe` before
preflight and refuses direct request-level zero overrides. Other copies and separate-server implementations remain outside these
guards. The changes do not erase or reinterpret historical results. Run
`test_live_guards.py` only while these exact scratch paths remain present; it
uses no model or inference.
