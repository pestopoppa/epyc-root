# Kernel promotion quality parity

The offline comparator checks a prospective pack against captured candidate responses. Build and pin the pack before collecting candidate output. Keep the printed SHA-256 in the prospective evidence record and supply that digest when comparing.

```bash
tool=.claude/skills/kernel-promotion/scripts/quality_parity.py
python3 "$tool" build --source production-captures.json --output parity-pack.json
python3 "$tool" compare --pack parity-pack.json --pack-sha256 "$pack_pin" --candidate candidate-captures.json
```

## Capture inputs

The production file uses schema `epyc.kernel_quality_parity_source.v1` and has these top-level fields.

| Field | Contents |
| --- | --- |
| `schema` | Schema identifier. |
| `capture_source` | The capture tool's 40-digit Git `commit` and `tree` and 64-digit `source_sha256`. |
| `shapes` | The deployed shape inventory. Each entry has a unique `id`, a `profile` from the required coverage list below, and an `endpoint` of `/completion` or `/v1/chat/completions`. Include `model_sha256`, `recipe_sha256`, `prompt_template_sha256`, `sampling_sha256`, `scorer_sha256`, `question_pool_sha256`, `endpoint_semantics_sha256`, and `generation_path_sha256`. A `dspark-dflash` shape also pins a positive integer `validated_cap`. |
| `runtime` | Object keyed by shape ID. Each value has `kernel_commit`, `kernel_tree`, and `binary_sha256` for that arm. |
| `items` | Array of unique item IDs with the request, coverage labels, validator, and production capture described below. |

Each item requires `id`, `shape` (the declared shape ID), `request_body`, `prompt_shape` (`short` or `long`), `output_format` (`json`, `prose`, `code`, or `reasoning`), `fixture` (`loader-reshape`, `recurrent-state`, or null), `expected_finish` (`stop` or `length`), `validator`, `dflash_pair` (pair ID or null), and `production` (capture). The full request pins the seed, greedy temperature, cache settings, prompt or messages, and positive token limit. Use `prompt` and `n_predict` for native completions or `messages` and `max_tokens` for chat. Retain the settings that expose returned token IDs on the selected endpoint.

A validator uses `{"id": "...", "expected": ...}`. Choose `json-object-subset.v1` with a nonempty object for structured JSON. For text, choose `exact-text.v1` or `contains-text.v1` with a nonempty string. Pin the expected answer or required fragment independently of candidate output.

Each capture has `request_sha256`, `response_b64` (the base64-encoded original UTF-8 response body), and `response_sha256` (hash of the decoded bytes). The request hash covers UTF-8 bytes of JSON serialized with sorted keys, ASCII escaping, and compact separators. A DFlash capture also has `server_instance` (a launch-specific identity), `parallel_slots` (integer 1), and `effective_n_max` (equal to the request's `speculative.n_max` and the effective cap echoed in the raw response). Use the same server instance for all pairs of a DFlash shape within an arm.

The candidate file uses `epyc.kernel_quality_parity_candidate.v1` and adds the prospective `pack_sha256`. Reuse the production `capture_source` and `shapes`. Supply the candidate's own `runtime` for the same shape inventory and an `items` array of `{"id": "...", "capture": {...}}` entries, one per pinned request. Capture on the declared runtime and preserve the original response bytes. The offline tool checks those bytes and the supplied capture records. Live binary, topology, and cleanup verification belong to the capture runner.

## Coverage and outcomes

The minimum is 32 distinct requests, with at least four per declared shape and four cap-0 / positive-cap request pairs. Required shape profiles are `frontdoor-cpu-moe-mtp`, `worker-general-cpu-moe-mtp`, `architect-critic-cpu-mtp`, `ingest-long-context-recurrent-no-spec`, `architect-general-hip`, `worker-vision-hip-mmproj`, and `dspark-dflash`. Every prompt shape, output format, regression fixture, and finish condition must appear. Tags describe the pinned fixtures and their intended coverage. The caller declares the inventory and fixture categories before the candidate capture.

| Report status | Next action |
| --- | --- |
| `pass` (exit 0) | Record an observation. Exact output tokens, text including exposed reasoning, finish, and semantic checks agreed across the pack. |
| `fail` (exit 1) | Run the full candidate quality suite for diagnosis. A content, token, finish, or semantic mismatch blocks parity. |
| `incomplete` (exit 2) | Repeat the entire affected role window for missing candidate items, missing token IDs, or missing raw completion counts. A banked production gap selects full quality regeneration. |
| `identity_drift` (exit 2) | Run full quality regeneration when the declared serving or capture identity changes. |

The tool rejects malformed, duplicate, incomplete-coverage, or hash-invalid inputs with exit 2. Completion counts must agree with returned IDs when exposed and with the request limit for a length finish.

Every report carries `observation_only: true`, `quality_transfer_authorized: false`, and `promotion_authorized: false`. An operator attestation covers the pack, banked captures, coverage, stopping rule, and exact tool sources before a future protocol can use these observations for quality transfer.

## Prospective comparison records

Pass `--capture comparison.json` to `compare` to retain a sealed record at the comparison boundary. The destination must not exist. The record retains the exact pack and candidate bytes, their hashes, the prospective pack pin, comparator source hash, coverage, individual checks and the native report or input failure. An unsuccessful comparison remains unsuccessful after capture; a capture does not authorize quality transfer or promotion.

The reader replays the original comparison with the hash-matching comparator. A changed report or input, a pre-hook report, or an incompatible comparator is refused. Runtime and serving identities remain declarations from the supplied captures; this offline record cannot establish that a declared binary served a request. Software fixtures establish reader behavior only. The first genuine prospective comparison and its planning-context canary remain required by `VB-V9-8-QUALITY-PACK-WIRE`.

Inspect projection without writing a ledger:

```bash
python3 scripts/vidya/cli.py ingest quality-pack-comparison --path comparison.json --dry-run
```

Only complete pass/fail observations project. Invalid, incomplete and identity-drift records retain their original outcomes without producing a numeric claim. The shared grader determines the observation's warrant; no comparison outcome supplies promotion authority.

## Capture both arms under one Rowflow grant

The [prospective request inputs](../../../data/vidya/quality-pack-live-20261118/request_inputs.json) pin 32
requests from seven preserved source plans. They retain the admitted architect-critic and DFlash production
policies, the replacement ingest request for `SOUTH` and governing record `E59`, and the original frontdoor
JSON request whose token streams diverged in the prior isolated capture. The four vision requests retain their
original PNGs and request bytes. Their strict stop and semantic policies are prospective. Source receipts
remain in their original records.

Materialize the request bodies, question-pool and scorer digests, model identities, and expected template
digests under canonical host scratch. The printed SHA-256 binds the materialized file.

```bash
prepare=scripts/benchmark/kernel_promotion_quality_prepare.py
inputs="$PWD/data/vidya/quality-pack-live-20261118/request_inputs.json"
input_pin=e9b8d9d40b88851de2299b8fba372c8e0f5920abd47315747251a87313855914
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B "$prepare" requests \
  --inputs "$inputs" --inputs-sha256 "$input_pin" \
  --out "$scratch/prospective-requests.json"
```

The seven isolated recipes preserve the original packet arguments and request endpoints. Inspect the
arguments, placement sources, model and template paths and digests, and role mappings with the
`recipes` command. The two HIP templates are read from the paths in the original launch arguments.
The planner checks their content against the original template digest, including when the archive
describes a different copy of the same template.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B "$prepare" recipes \
  --inputs-sha256 "$input_pin" --out "$scratch/quality-recipes.json"
jq 'map_values(.mapping)' "$scratch/quality-recipes.json" > "$mappings"
sha256sum "$mappings"
```

To prepare an arm, use `kernel_promotion_hot_stack.py --spec "$spec" --output-dir "$arm_dir"`
with the following specification.

| Field | Required contents |
| --- | --- |
| `schema` | `epyc.kernel_promotion_quality_stack_spec.v1` |
| `orchestrator_commit`, `config_sha256`, `candidate` | The ordinary stack planner's checkout, config and image pins. Use each arm's own sealed CPU and HIP images. Stage a separate verified copy of the production images. |
| `request_inputs_sha256` | Digest of the checked-in prospective request inputs. Regeneration uses the pinned input, original recipe envelopes and archived CPU-affinity witnesses. |
| `ports` | Seven distinct non-production loopback ports keyed by profile. Both arms use the same map. The role mapping's canonical port is a provenance anchor. Several isolated profiles can share that anchor and still have separate listeners. |
| `resources` | `physical_cpus` set to `0-95`, `gpu_devices` set to `["ROCm0"]`, and integer `ram_gib` of at least 112, the largest serial source row's budget. |

The planner matches the CPU slices' thread count and CPU affinity to their archived server records.
Both HIP slices use the original recipe affinity on CPUs 184–191. The isolated launcher adds local NUMA
memory binding on node 2 for frontdoor and node 3 for the remaining slices. The dedicated plan uses
distinct state and log paths and opens one listener at a time during quality capture.

Once both arms have private prepared plans, supply the digest of each plan and a pinned JSON mapping keyed
by the seven profile IDs. Use the same detached orchestrator checkout for assembly and live execution. The
assembler checks the frozen production image, regenerates both plans, verifies their exact serving paths and
model/template pins, and runs the live adapter's configuration preflight before writing the configuration.
Supply the canonical path to a durable Git checkout containing the capture commit and the canonical path
to the ratified production freeze JSON.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B "$prepare" config \
  --inputs "$inputs" --inputs-sha256 "$input_pin" \
  --production-plan "$production_plan" "$production_pin" \
  --candidate-plan "$candidate_plan" "$candidate_pin" \
  --mappings "$mappings" "$mappings_pin" --orchestrator "$pinned_orchestrator" \
  --source-repository "$capture_repository" --production-attestation "$freeze_attestation" \
  --capture-commit "$capture_commit" --startup-timeout-s 360 --request-timeout-s 600 \
  --observation-dir "$scratch/quality-observation" --out "$scratch/quality-capture.json"
```

Run the live adapter with a prepared configuration and a new private output directory under host scratch.
For a detached orchestrator checkout, the row launcher imports the capture adapter and sets
`planner.ORCHESTRATOR` to the same canonical checkout passed to the assembler before calling `main()`.
The direct invocation below uses the planner's default checkout.

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B \
  scripts/benchmark/kernel_promotion_quality_capture.py \
  --config "$scratch/quality-capture.json" \
  --config-sha256 "$config_pin" \
  --out "$scratch/quality-observation"
```

Build the configuration and pin its exact bytes before publication. The schema is `epyc.kernel_quality_live_capture.v1`.

| Field | Required contents |
| --- | --- |
| `schema` | `epyc.kernel_quality_live_capture.v1`. |
| `source_repository` and `capture_source` | Canonical path to a Git repository containing the committed capture adapter, and its `commit`, `tree` and `source_sha256` as in the offline format. The adapter checks the committed file against the executed copy, including for a row snapshot. |
| `tool_sha256` | Hashes keyed by `planner`, `preparer`, `runner`, `evidence`, `linkage`, `workload_guard`, `k35` and `comparator`. The adapter's `tool_files()` identifies the installed files. |
| `production_attestation` | Canonical path to the ratified v10 final freeze JSON. The adapter checks the fixed ratification digest, frozen branch, commit and tree, and the staged binary and hot libraries against the production store. |
| `arms` | Object with `production` and `candidate` entries. Each provides canonical `plan`, `plan_sha256`, and the offline `runtime` object keyed by shape. The plans must be in distinct private directories and pin the same full Rowflow port and resource assignments. Stage a separate copy of the ratified production image for its plan. The regular planner rejects overlap and hardlinks with the serving tree. Both plans must regenerate exactly with a fresh, topology-matched matrix. |
| `shapes` | The complete offline serving-shape inventory. The adapter validates the serving path pins against both prepared arms. |
| `mappings` | One entry per shape ID with integer `canonical_port`, integer `numa_instance`, serving `role` and exact request `path`. Each maps to one planned loopback generation listener in each arm. Multiple profiles can share the same instance when their planned role and generation settings match. |
| `models` | Object keyed by canonical GGUF path with precomputed `sha256` and five-element `stat` identity (device, inode, size, mtime ns, ctime ns). Include all files resolved from `-m`, `-md` and `--mmproj`, including every split shard on each selected listener. Establish these digest-to-stat bindings before the grant. Live checks compare stat, startup mappings and prepared model identities. Template verification reads template bytes or a GGUF header. |
| `items` | Prospective offline item fields, omitting `production` and adding the explicit canonical `request_sha256`. Use the actual body sent to each endpoint, including image bytes as PNG or JPEG data URLs in the vision shape's chat requests. |
| `startup_timeout_s` and `request_timeout_s` | Integer per-listener startup and per-request budgets in seconds, up to 3600 and 1800 respectively, additionally bounded by the live grant. |

Compute the adapter-specific shape digests with `shape_digests(plan, endpoint, shape, artifact_integrity, models)` using the pinned orchestrator's artifact-integrity module. The recipe digest covers the launcher arguments, environment, roles, placement and device after normalizing the isolated executable, library directory, listener port and slot-storage path. The model digest covers the ordered canonical paths and precomputed content digests of target, drafter and projector files. The template digest covers the effective chat template or the `raw-native-prompt.v1` marker for direct native prompts. The endpoint digest covers the exact POST path, canonical JSON body, raw JSON response body and non-streaming mode. The generation-path digest binds those four digests. Sampling, scorer and question-pool pins refer to the predeclared experiment inputs. The full configuration and request pins bind the individual settings, prompts and expected answers.

The row must reserve full-host CPU placement, every isolated plan port, the plan RAM budget and the MI210. Capture runs serially by arm and isolated listener. All requests for a DFlash shape run on one owned `-np 1` listener in each arm, with the cap read from each raw response echo. Configuration assembly requires a fresh topology-matched matrix for both arms and one prepared endpoint for every prescribed shape.

The experiment asks whether the two isolated kernels produce exactly matching returned token IDs, content and reasoning for the predeclared requests. It uses the fixed comparator coverage, with at least 32 distinct requests and four DFlash pairs. This is exact agreement for a finite pack. HTTP or custody failure stops collection at the affected request. A production semantic failure or missing production token IDs or completion counts stops the run before candidate capture. The adapter finalizes and checks the production pack and its SHA-256 file before starting the candidate arm. Candidate token or count gaps produce comparator `incomplete` when the recorded comparisons otherwise agree.

The output preserves the original configuration, ordered request pins, prepared plan bytes, admission and workload screens, startup identity, exact sent bodies and raw HTTP response bodies. Each eligible response has a complete placement and backend scan after upload and before response headers, with exact scan timestamps. Each listener has a captured-PID exit, port and KFD cleanup record. The final `comparison.json` is the existing comparator's native record. The surrounding `MANIFEST.json` and `COMPLETE` bind the live evidence after proved cleanup. A sealed failed attempt can retain diagnostics. Require `result.json` status `pass`, `cleanup_proved=true` and a matching seal when checking an observation for successful completion. The exit codes are 0 for pass, 1 for a comparator mismatch and 2 for incomplete or refused capture.

The capture and comparison carry observation-only authority. A row that runs the socket-free fixtures establishes software behavior. A full prospective live observation and its planning-context canary remain separate acceptance evidence.
