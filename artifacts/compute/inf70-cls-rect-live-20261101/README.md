# CLS-RECT-1a live token capture row

This bundle defines one bounded live harness1 arm to establish that the production
server returns generated token IDs in the response (`token_source == "response"`).
The row was published 2026-11-01; no live result is claimed here.

## Runtime design

- Use the production CPU kernel store at `/mnt/raid0/llm/kernels/production/cpu`.
  The server SHA-256 is pinned to `4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c`
  and version `10303 (ffc1bac82)`, matching `scripts/session/verify_llama_cpp.sh`.
- Use the served UD-IQ4_XS split model under
  `/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/`.
- Claim CPU region `0-95`, with `--claim-cpus 0-95`; run with `taskset -c 0-95`,
  `numactl --interleave=all`, and 48 OpenMP threads, matching the harness1 recipe.
- Do not use `arm_hot.sh`: the v10 server has no live knob-page support, while that
  script requires `GGML_KNOB_FILE` to be mapped. This validation needs no knob changes.
- The client uses the promoted harness1 token-ID and classifier functions. It appends
  and fsyncs one JSONL row after each prompt, resumes from the next missing prompt,
  and checks `FILLER_STOPFILE` and `FILLER_DEADLINE` between prompts. Rowflow's dry run can stop after the first
  persisted row; ordinary completion requires all 24 prompts.
- The runner owns the server PID, sends TERM, waits, escalates to KILL if necessary,
  and verifies the PID is gone. The rowflow engine also has its 600-second process
  group cleanup path.

## Files

- `launcher.sh`: rowflow v15 launcher template. Install it and its sibling files into
  a job directory under `/mnt/raid0/llm/tmp/` before publication.
- `run_live_arm.sh`: pinned server launcher, request runner, and cleanup.
- `live_arm.py`: bounded client using the existing harness1 client helpers.
- `spec.json`: the published rowflow specification, pointing at the scratch install.
- `install_to_scratch.sh`: copies only this bundle's runnable files to the rowflow
  scratch job directory.

## Acceptance evidence

The first emitted result row must contain `token_source: "response"`, a non-empty
`token_ids` list, and the pinned classifier ID. The row also stores response text,
native stop type, request timing, token count, and the selected token source.
The runner records binary identity, model shard paths and verified sidecar digests,
environment, process maps, NUMA placement, and THP/RSS. A first row with
`retokenized`, `absent`, `NO-TOKEN-IDS`, or `REFUSED` does not satisfy CLS-RECT-1a.

The owner installed this bundle in scratch and published the row; the keeper's dry run
is the first live arm. Shell syntax, Python compilation and JSON parsing were checked.
