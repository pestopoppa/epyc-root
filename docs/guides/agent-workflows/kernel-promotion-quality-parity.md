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
