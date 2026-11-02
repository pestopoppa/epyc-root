# ID-14 — Disposable-host containment design

**Status:** design only. No trial, host mutation, gate mutation, handoff/index edit, or commit was performed. The approved containerized trial is still **not authorized on this host as configured**.

## Boundary

Run the agent tree inside a short-lived, dedicated VM (or equivalent separately administered disposable host), created from a pinned image and destroyed after export. A container on the shared host is insufficient when it can reach a shared Docker socket. The guest must have no host container-runtime socket, host PID namespace, privileged mode, host devices, host network, or writable bind mounts into project or operator data. Do not attach the shared GPU or production runtime for this trial; use a separately provisioned disposable GPU host if GPU execution is essential.

Use a fresh guest-local checkout from an immutable source revision. Give each run a unique guest-local workspace. The only output crossing the boundary is a size-limited, malware-scanned archive of proposed patch files and run metadata, staged to a dedicated quarantine location. Never mount a live repo or let the agent commit/push. Review the patch before applying it separately.

## Controls

1. **Identity and scope:** run under an unprivileged guest account. Pin the Fractal/harness, agent CLI, model, base revision, dependencies, and prompt/config hashes in run metadata. Apply `scope` as an allowlist of writable subdirectories; reject paths outside it at patch collection, including symlinks and traversal. The agent may edit only guest-local files.
2. **Network:** default-deny inbound and outbound traffic. If model access is needed, permit only a controlled egress proxy and explicit model endpoint; block cloud metadata, private/link-local ranges, SSH, repo credentials, and arbitrary DNS. Use an ephemeral least-privilege model credential with a hard provider cap, if supported; revoke it at teardown. Local inference must use a dedicated endpoint on the disposable host, never the shared host's Docker or orchestration control plane.
3. **Budget:** aggregate all child-node budgets at the root controller. Enforce hard run ceilings outside the agent process for wall-clock time and GPU-seconds (plus provider USD where applicable); USD alone is not a valid local-inference ceiling because a local llama-server may report zero vendor spend. Reserve a fixed tranche before launch for drain, logs, artifact export, and teardown; workers cannot spend or reassign this reserve. Abort new work once remaining budget reaches the reserve threshold.
4. **Drain and cleanup:** request drain at iteration boundaries; stop scheduling children, let the current bounded iteration finish, then collect logs and approved outputs. An external watchdog enforces a maximum drain grace period and terminates the VM if exceeded. Destroy the guest, revoke credentials, and verify guest resources are gone. Cleanup does not depend on a cooperative agent.
5. **Evidence:** record per-node parent/child budget debits, wall-clock and GPU-seconds, iteration/drain timestamps, network policy, source/config hashes, exit/termination reason, and exported-file manifest. Missing measurements are explicit unknowns and fail closed against the relevant cap.

## Go/no-go checks before a future trial

- Disposable VM/host ownership and destruction path demonstrated; no shared Docker socket or host project mounts.
- Egress policy tested against metadata/private-network targets and the sole approved model route.
- Scope enforcement tested for out-of-scope paths, symlink escape, and attempted commit/push.
- Root budget aggregation and independent hard watchdog tested, including zero-reported-USD local inference; cleanup reserve remains inaccessible to workers.
- Drain at iteration boundary and forced termination after grace tested; artifact quarantine and teardown evidence captured.
- A named bounded workload, source revision, non-USD ceilings, reserve amount, maximum drain grace, and output quarantine location recorded before execution.

Any failed or unproven check means no run. This document specifies a design and acceptance checks; it does not claim these controls exist or have passed.

## Known gaps / decisions needed to instantiate

- No disposable VM/host provider, image, isolation owner, or destruction evidence is identified in the handoff.
- Numeric wall-clock/GPU-second ceilings, cleanup reserve, drain grace, and provider spend cap are not specified; choose them per bounded workload before trial.
- Model endpoint and egress allowlist are unspecified. Local inference requires a disposable endpoint, not the shared Docker socket or production server.
- Exact Fractal/harness and CLI revisions, permitted writable subdirectories, workload, and quarantined artifact destination are unspecified.
- Isolation policy tests and cleanup verification have not been run. This artifact is design only, not a security certification or authorization to run.
