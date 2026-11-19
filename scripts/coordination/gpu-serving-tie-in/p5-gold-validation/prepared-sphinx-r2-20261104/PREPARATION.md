P5-2c Sphinx reporting-only repair, same qualification lineage (r2 supersedes first row).

First failure and exact original producer sources retained in lane:
docs/reports/p5-sphinx-first-smoke-20261104/. Pinned official parser correctly
parsed both failures; pytest default summary omitted the passed test's name.
Exact original-script hash remains pinned. offline_eval.py now replaces the
known setup command and appends only -rA --color=no to the exact original tox
command. Test selectors, contents, patches and official parser are unchanged.
No synthesized statuses or parser patch. Prepared image/source guard reused.

Seven synthetic native-outcome and four parser/reporting controls run before
the real controls in every --job launch, taskset-bound to FILLER_CPUS. One test
runs genuine tiny pytest fixtures with system /usr/bin/python3 -m pytest in
TemporaryDirectory under row TMPDIR, parses real stdout through the pinned
official parse_log_pytest_v2, and cleans its directory. This formatter control
uses system pytest; the two real arms immediately afterwards validate the
pinned image pytest. No synthetic container is created and no gold patch is
used by the fixture. Host TMPDIR is the
pre-created control-tmp under this row's scratch; TemporaryDirectory cleans.
Controls log: controls.log. No independent test run claimed: both attempted
24-27 and72-75 timeout1 claims were denied by a full-host timing owner.

Shared270s instrument deadline starts before all controls; scheduler estimate
and min-window300s. Both full gold and no-op arms require every named test
PASSED/FAILED plus source/cleanup proof. Complete-but-wrong controls produce
status COMPLETE, decision FAIL, rc0, and are fileable. Missing/error/skipped/
timeout/cleanup failures refuse completion and retain real partial evidence.
No model execution. Parent reviews and publishes; no full P5-2/isolation claim.
