# Production contention matrix prerequisite

The production stack owner runs this on the approved healthy lineup during an authorized quiet
window. Use the orchestrator environment in `/mnt/raid0/llm/epyc-orchestrator` and the native
producer command `.venv/bin/python scripts/server/contention_matrix.py run`. It benchmarks the
configured-primary live role pairs through their production completion endpoints. The models,
recipes and listening processes come from the approved live lineup and `stack_numa.NUMA_CONFIG`
at execution. The producer derives the CPU kernel binary through
`src.registry.kernel_paths.server_binary("cpu")`. Validate the actual live builds and model
identities against the approved relaunch lineup. A copied October file, a topology relabel, a
timestamp update, a topology-only calculation and a role-scoped refresh cannot supply fresh
full-matrix custody.

The production owner validates the completed canonical artifact using
`.venv/bin/python scripts/validate/check_contention_matrix_fresh.py` and retains the native
matrix, invocation, logs and live lineup identity. After installing it through the owner
workflow, run `/usr/bin/python3 -I -B packet/job.py --bind-matrix` from this packet's parent.
The lifecycle owner can then publish the source-pinned successor. Before its whole-host grant
starts, the production owner must authorize a boundary at which the matrix-serving llama
processes and AutoPilot have drained. The original lifecycle runner checks for those processes
before launching its two v10 arms. No production changes or benchmark were run for this repair.
