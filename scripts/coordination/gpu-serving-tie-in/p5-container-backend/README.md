# Experimental P5 container adapter

This is a candidate integration for P5-1, not an approved execution sandbox.
It wraps the research `agentic_swe_harness.py` and creates a fresh container for
each trial. The container uses an immutable local image ID, no network or host
mounts, an unprivileged UID, dropped capabilities, no-new-privileges and fixed
resource limits. The adapter copies four hash-pinned orchestrator containment
sources into the container and routes harness commands and file operations
through `exec_sandbox` there. It removes each owned container at the end of the
trial, with an additional cleanup on wrapper exit.
In a row, the container also inherits the allocated `FILLER_CPUS` cpuset and
is set to auto-remove at exit; its lifetime is bounded by `FILLER_DEADLINE`
(and at most one hour). These controls do not replace real-image qualification.

Requirements: a local Docker image with a writable `/testbed` for UID/GID
`65534:65534`, `bash`, `timeout`, and `python3`; no image-declared volumes; and
a host/container combination where the orchestrator Landlock and network-deny
probes pass. The image's `/opt` and copied containment paths must not be writable
by the trial user. The image ID, runner hash and containment hashes must be
reviewed and pinned before use. Image contents themselves must be trusted.

For a single instance, invoke from the repository root, substituting reviewed
values and scratch paths:

```bash
python3 scripts/coordination/gpu-serving-tie-in/p5-container-backend/run_harness.py \
  --runner /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/agentic_swe_harness.py \
  --runner-sha256 <runner-sha256> \
  --sandbox-source-dir /mnt/raid0/llm/epyc-orchestrator/src/repl_environment \
  --sandbox-sha256-json <scratch-path-to-json> \
  --dataset <swebench-json> --instance-id <instance-id> \
  --container sha256:<full-local-image-id> --arm <arm-label> \
  --out-dir <scratch-output-dir> --server-url <model-server-url>
```

The hash JSON is an object with exactly these filenames as keys and their
SHA-256 hex digests as values: `exec_sandbox.py`, `fence_kernel.py`,
`_fence_rules.py`, `_fence_kernel_shim.py`. For multiple instances, use the
harness `--container-map` JSON, mapping each instance ID to a full immutable
image ID. Harness `--dry-run` prints its plan without starting Docker or proving
containment. Actual inference remains subject to the handoff's row and grant
workflow.

Current checks cover inspection refusals, path traversal and symlink rejection,
and cleanup after a trial exception. A live generic Python-image smoke ran a
contained command and saw socket creation denied; its test container was
removed. This does not qualify a SWE-bench image, prove end-to-end harness or
scorer behavior, or establish complete adversarial isolation. P5-1 remains open.
