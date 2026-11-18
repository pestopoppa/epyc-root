# Prepare an isolated candidate hot-stack plan

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

The command generator resolves the production recipe using its original port and role. The planner replaces the binary, library search path, listener port and slot-save directory for the candidate. It records command-generator hashes, a private log and state path for each endpoint, an explicit `endpoint_manifest` for a future isolated smoke consumer, and the GGUF inode-deduplicated prewarm targets. It records prepared model paths and stat identities. The production artifact builder uses an empty private fingerprint ledger during planning, so building the plan does not refresh the serving ledger or hash GGUF tensor data.

Planning creates only `plan.json` in the output directory. There is no apply mode. The plan reports contention matrix freshness and plans serial execution. A separate runtime instrument must obtain live resource grants, validate the current matrix and linkage, prove model content and running affinity/NUMA, execute prewarm and smoke/parity checks, and seal the result after verified cleanup. The orchestrator's quarter-stack smoke command still uses its production default endpoints. This preparation has no promotion authority.
