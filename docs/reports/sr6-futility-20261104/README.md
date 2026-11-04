# SR-6 sealed experiment: futility stop

The three planned windows terminate UNKNOWN under the predeclared stop rule in the active speculative-decoding handoff. W1 retry ended rc1 without a RESULT. W2 retry and W3 ended rc0, but their native results are PARTIAL/UNKNOWN with `DrainError: cannot prove cgroup drained`. A launcher completion code does not override the native UNKNOWN.

The generic drain exception does not distinguish child reaping from cgroup-directory removal; retained evidence does not establish its cause or successful cleanup. Partial output and exposure records are preserved in `partial-output/`, alongside each row manifest, terminal receipt, native result where present, and filed verdict.

The sealed rule forbids rerunning an UNKNOWN window or adaptively extending this experiment. This closes this experiment by futility. It establishes neither a preferred width nor composed-recipe monotonicity and grants no registry-change authority.
