# Prepare and smoke-test an isolated candidate hot stack

`scripts/benchmark/kernel_promotion_hot_stack.py` prepares the static command plan for section 5 of the [resident promotion design](https://github.com/pestopoppa/epyc-inference-research/blob/main/docs/design/kernel-promotion-resident-fast-path.md). The output has status `prepared_only`.

Run with the orchestrator's Python environment and a new output directory under `/mnt/raid0/llm/tmp`.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B \
  scripts/benchmark/kernel_promotion_hot_stack.py \
  --spec "$scratch/hot-stack.spec.json" \
  --output-dir "$scratch/hot-stack-plan"
```

The JSON spec uses schema `epyc.kernel_promotion_hot_stack_spec.v1` and has these fields.

| Field | Required contents |
| --- | --- |
| `orchestrator_commit` | Full Git HEAD of the current orchestrator checkout. Launcher and config paths must be clean. |
| `config_sha256` | SHA-256s keyed by `orchestration/launch_manifest.yaml`, `orchestration/stack_topology.yaml`, `orchestration/model_registry.yaml`, `orchestration/derived/stack_priors.yaml`, and `orchestration/contention_matrix.yaml`. |
| `candidate` | `source_commit`, `source_tree`, and `branch`, plus separate `cpu` and `hip` images. Each image supplies its canonical `root`, `inventory` filename, `inventory_sha256`, and `identity_sha256` for `BUILD-IDENTITY.json`. The inventory lists every `bin/` member, including in-directory shared-library aliases. |
| `numa_mode` and `warm_roles` | Choose `full`, `quarter` (the launcher name for the current half instances), or `both`. Include explicitly selected WARM roles alongside the HOT endpoint set. |
| `ports` and `endpoint_tests` | Maps keyed by canonical port string. Every selected endpoint gets a unique isolated TCP port and its planned `chat` or `embedding` test. |
| `resources` | `physical_cpus` CPU list, `gpu_devices` list such as `["ROCm0"]`, and integer `ram_gib`. CPU and GPU claims match the union of generated placements, folding SMT siblings onto their physical CPUs. The RAM value is the requested budget. |

The command generator resolves the production recipe using its original port and role. The planner replaces the binary, library search path, listener port and slot-save directory for the candidate. It records command-generator hashes, a private log and state path for each endpoint, an explicit `endpoint_manifest`, and the GGUF inode-deduplicated prewarm targets. It records prepared model paths and stat identities. The production artifact builder uses an empty private fingerprint ledger during planning, so building the plan does not refresh the serving ledger or hash GGUF tensor data.

## Run the isolated functional smoke

Call the runner from an admitted Rowflow job through the orchestrator Python environment. The runtime supports full-host CPU coverage and either a CPU-only plan or a mixed CPU and single-MI210 plan. Set the job's published RAM and isolated ports to cover the plan. The runner checks the published row, active grant window, stop flag, launcher ancestry, Rowflow cgroup, and live CPU and device lock inodes. CPU-only jobs must carry the Rowflow GPU fence. A mixed job refuses admission while a foreign KFD client is present.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B \
  scripts/benchmark/kernel_promotion_hot_stack_runner.py \
  --plan "$scratch/hot-stack-plan/plan.json" \
  --plan-sha256 "$prepared_plan_sha256" \
  --output-dir "$scratch/hot-stack-observation"
```

Use a new observation directory outside the private plan directory. On each run the runner regenerates the plan from its pinned inputs and requires an exact match and a fresh contention matrix. It verifies both images' loader paths, rechecks prepared model stat identities, and starts the endpoints in order. It waits for each captured process to own its isolated loopback listener and respond healthy before starting the next endpoint.

The runner sends chat or embedding requests only to those owned listeners. It records executable and mapped-library identity, the CPU mask and NUMA policy for every TID found in a stable scan, and per-process KFD and VRAM evidence on HIP. Each functional smoke requires a complete scan after the request is sent and before response headers arrive. A response that finishes before a complete scan fails the smoke. Teardown uses captured pidfds and verifies exit, port closure and KFD departure. `MANIFEST.json` and `COMPLETE` seal the observation after verified cleanup. The manifest records the functional outcome, including failure when the evidence could still be sealed.

Each witnessed HTTP 200 chat response that parses as JSON gets a `response-comparability.json` next to the raw response. `comparable` requires a single finished choice at index zero, a positive completion count within the request limit, nonblank assistant content, and a top-level `tokens` list of nonnegative integer IDs with exactly that count. A `length` finish requires the full limit. A `stop` finish can end early. If the response includes timings, the predicted count must agree with usage. The report uses `diagnostic_incomplete` when any of these checks fails. A server that omits generated token IDs can still pass the functional smoke. `comparable` describes a single capture. A parity verdict requires a separately bound reference response.

## Run the paired concurrency diagnostic

Add `--paired-concurrency` to the runner command to include one additional pair of simultaneous POST requests after the sequential smokes. Startup stays serial. The runner picks the first eligible pair in canonical-port order from the regenerated plan and pinned contention matrix. Both instances must match an explicit `allow` row by role, canonical port, instance index, logical CPU list, and thread count. The endpoints must have disjoint physical CPU claims after folding SMT siblings and must not share a GPU device. A missing eligible pair fails the requested diagnostic.

The two connections rendezvous after listener identity checks and immediately before sending. Each request records its upload completion, response headers, raw response, and complete per-endpoint witness scans. Both scans must fit inside the time between the later upload completion and the earlier response headers. The scan windows must themselves overlap for a positive duration. This is a client-observed concurrency test. It establishes witnessed overlap at two isolated endpoints.

`paired-concurrency/pair.json` records the selected endpoints and matrix row. Per-port directories retain the request, response, HTTP status, and witness scans. Their timestamps share a monotonic origin, and `paired-concurrency/result.json` identifies the overlapping scans or records failures. `result.json` records whether the diagnostic was requested. Missing overlap fails the run, and the seal requires verified cleanup of the entire stack. The output carries observation-only status. Exact output parity requires separately bound reference captures.

Dedicated cache prewarm, model-content hashing, architecture/backend-specific cases, and forced-role orchestration through an isolated API remain separate work. The plan retains its prewarm target declarations. The orchestrator's quarter-stack smoke still uses its production defaults.
