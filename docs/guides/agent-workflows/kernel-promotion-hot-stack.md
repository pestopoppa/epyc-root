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

Dedicated cache prewarm, model-content hashing, and architecture/backend-specific cases remain separate work. The plan retains its prewarm target declarations.

## Run the isolated forced-role API smoke

Add `--api-role` to the live runner to exercise the real orchestrator `/chat` route after the stack is ready and the endpoint smokes finish. Choose one chat role named in the prepared plan's `endpoint_manifest`. If the role has multiple rows, pass its isolated `--api-port` explicitly.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B \
  scripts/benchmark/kernel_promotion_hot_stack_runner.py \
  --plan "$scratch/hot-stack-plan/plan.json" \
  --plan-sha256 "$prepared_plan_sha256" \
  --api-role frontdoor --api-port "$isolated_frontdoor_port" \
  --output-dir "$scratch/forced-api-observation"
```

The runner selects the ready owned listener for the role and starts a private API subprocess in the grant's cleanup cgroup. The subprocess mounts the real `/chat` handler with fresh FastAPI state and a single allowed loopback destination. The request supplies exactly one `server_urls` entry and forces real direct mode. The consumer checks that the route constructs exactly that request-sourced backend. The manifest must use canonical `http://127.0.0.1:<port>` origins. Production and default ports are refused across the entire manifest, including auxiliary services, aliases and all launched instances. The app bypasses production startup and MemRL initialization, and uses private runtime paths.

The runner approves each upstream connection and dispatch after rechecking listener identity. It uses the HTTP transport's upload-complete and response-headers timestamps to require a complete affinity, NUMA and backend scan inside the upstream generation request. A scan ending after response headers cannot count. A pass also requires HTTP 200, direct real mode, the requested role as the sole role in the history, a successful answer and one successful upstream generation request.

The observation keeps the exact API request body in `isolated-api/consumer/request.json`, any received response in `isolated-api/consumer/response.body`, and the plan digest, destination, upstream calls and API verdict in `isolated-api/consumer/result.json`. The surrounding `isolated-api/` directory records the worker's identity and exit, the generation witness and any runner refusal. The overall seal requires proved teardown of the API subprocess and the entire stack. The diagnostic carries observation-only status.

To exercise image input, prepare a deterministic PNG in private scratch and compute its SHA-256 before the live grant. For a white field with a centered red square, run the same command with `--api-role worker_vision --api-port "$isolated_vision_port" --api-image "$png_path" --api-image-sha256 "$png_sha256"`. Supply a canonical regular file of at most 1 MiB. Both image arguments are required, and `worker_vision` without them remains a text smoke.

The private probe follows the real forced multimodal `/chat` handler with document preprocessing and OCR disabled. It binds the vision resolver to the exact request-scoped worker URL, refuses fallback destinations, and requires one successful async `/v1/chat/completions` call with the same PNG bytes. `isolated-api/consumer/upstream-request.json` retains the exact upstream JSON. The result records its SHA-256, the decoded image digest, the vision probe scope, and the prepared `--mmproj` path and stat identity. The runner checks the projector and image before dispatch and after the request. The projector loader can buffer the tensors without retaining an mmap. Startup records whether its prepared inode was mapped and checks any observed mapping. The normal main and draft model mapping requirements still apply. The response records what the model answered.

## Acquire an isolated contention observation

`scripts/benchmark/kernel_promotion_contention_acquire.py` is a separate observation-only producer for the native matrix prerequisite. Its immutable Rowflow packet pins the original production declarations, C13 image inventories and topology-matched source matrix. It records the source matrix as stale when applicable; it neither refreshes the canonical file nor relaxes the ordinary runner's fresh-matrix gate.

The CPU diagnostic selects the declared frontdoor alternate on canonical port8180 and worker_vision primary on canonical port8086, then launches them on private booked ports. Their physical CPU sets must be disjoint. The row reserves all96 physical CPUs and carries the Rowflow GPU visibility fence. Every foreign K35 workload blocks acquisition; the producer exempts only its own captured processes after rechecking identity. It never stops another service.

Two solo completion legs and one simultaneous pair use identical fixed request bodies. Each leg must return the complete fixed token count and a positive finite native decode duration. Placement and backend scans must fit inside the request interval, with both endpoints witnessed inside the common concurrent interval. Raw responses, requests, workload refusals, image/model/plan identities and captured-PID cleanup remain in the acquisition directory.

The reported ratio divides the sum of solo decode durations by the longer concurrent decode duration; higher means more aggregate concurrency benefit for these captured legs. One request per leg provides no useful estimate of sampling uncertainty. This is a descriptive instance-pair observation, with no routing allow/deny verdict, quality-parity result, canonical matrix replacement or promotion acceptance. Cleanup failure makes the acquisition fail. The declared stop contract stops after all four legs and cleanup, or on the first admission, identity, workload, request, witness or cleanup failure.

Acquisition relies on the engine’s region-lock provider; its launcher must omit `--self-claim`, because this producer does not acquire a provider claim itself. Keeper execution may use the row-scoped engine snapshot. Admission must bind that exact snapshot to the published engine digest and still require unique live provider/inner ancestors, shared cleanup cgroup and live lock inodes. A completed engine exit is not a native success: file the native `RESULT.json` status and required captures against the decision rule.

Publish the prepared packet through `publish_row.py`. Its software fixtures run in the publisher smoke. Run the acquisition only through the resulting keeper grant.

With `--acquire`, add `--api-role frontdoor` or `--api-role worker_vision` to opt into the forced-role API capture after all four native legs. This mode requires the exact isolated ports 19560 and 19561. It uses the admitted prepared plan digest and bytes, retains the raw API request and response and request-time custody, and requires proved cleanup. Omitting `--api-role` runs the original acquisition.

For an image-bearing acquisition, publish the prepared PNG and include its canonical path and pinned SHA-256 in the packet's acquire command. Use `--acquire --api-role worker_vision --api-image "$png_path" --api-image-sha256 "$png_sha256"`. The four native timing legs run with their existing text workload before the optional image-bearing `/chat` probe.

## Export a private matrix diagnostic

Supply a successful native acquisition's retained packet and a trusted `RESULT.json` digest to the runner's offline export mode. Pass the original prepared plan or its matching counterpart in another private plan directory. The isolated ports and plan contents must match. The export accounts for the generated log, state and slot paths and the recorded age status.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B \
  scripts/benchmark/kernel_promotion_hot_stack_runner.py \
  --plan "$scratch/hot-stack-plan/plan.json" \
  --plan-sha256 "$prepared_plan_sha256" \
  --private-matrix-result "$native_packet/out/RESULT.json" \
  --private-matrix-result-sha256 "$acquisition_result_sha256" \
  --output-dir "$scratch/private-matrix-diagnostic"
```

The exporter checks the result pin and attempt inventory, the frozen producer and prepared plan, and the source matrix bytes and topology. It matches the exact CPU instances and their image and model witnesses, replays the solo and parallel request records, and requires cleanup to account for both captured PID and birth identities. Failed acquisitions and missing or inconsistent captures are refused.

The output is a single `private-matrix-diagnostic.json` record with `observation_only` authority. It links to the native capture by digest. Timing values stay in the original capture. The export is offline and unsealed, with no keeper admission or server launches. Live hot-stack admission and pair selection still require a fresh contention matrix. Routing, timing acceptance and promotion retain their existing gates.
