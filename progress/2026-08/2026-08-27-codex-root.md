# Progress — codex-root — 2026-08-27

## Session objective

Acquire the official Qwen3.8-Flash-Next FP8 checkpoint for future inference research, retire the
superseded DeepSeek V4 Flash local test path, and leave a durable evaluation handoff.

## Completed

- Confirmed RAID capacity for the 172.82 GiB official FP8 model.
- Downloaded `Qwen/Qwen3.8-Flash-Next-FP8` to
  `/mnt/raid0/llm/models/Qwen3.8-Flash-Next-FP8`.
- Verified the complete 185,563,783,823-byte payload: 145 files, 131 shards, all ModelScope SHA-256
  checks passing, no partials. Recorded ModelScope revision
  `f88480ebce48d6daed69eac86aab43b4122ad799` and checksum-identical Hugging Face weight pin
  `bcd9f01ddc9cff2316eb84281bebcd5b058bddce`.
- Deleted the local DeepSeek V4 Flash model and retired its active testing documentation; it will not
  be used as a local comparator.
- Created `INF-63`, an active inference-research handoff that begins with a `qwen4_exp`/block-FP8
  backend audit and proceeds through bounded residency, coherence, performance, capability, and
  retention gates. Production llama.cpp support is explicitly not a dependency.

## Validation

- Artifact integrity: PASS (all upstream hashes; exact file/shard counts; no partial files).
- Handoff coverage/index validation: PASS (`index_state.py --check`: 0 problems).
- Wiki compilation: PASS (Qwen/DeepSeek source cluster synthesized; structural/link lint: 0 errors;
  source-manifest drift: none; writer evidence policy: valid).
- README freshness: PASS (no warnings).

## Next action

Dispatch `INF-63` Phase 0 when an inference-research lane is free: select a compatible backend and
run the bounded load/coherence smoke under a governed compute window.
