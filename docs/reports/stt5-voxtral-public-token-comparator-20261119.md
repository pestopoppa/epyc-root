# Voxtral public-fixture token comparator — 2026-11-19

CS-8.STT5: added `scripts/speech/stt5_voxtral_tokens.py`, a strict comparator
for the retained native `CS8_VOXTRAL_*` witnesses. Four model-free test groups
pass, including 14 malformed-witness controls. Missing, empty, truncated,
duplicate, misindexed, overlong and malformed witnesses refuse. All native
IDs, including padding/control tokens, remain in the comparison; unequal lengths
and control-token differences fail without trimming or alignment. The CLI uses
rc0 for exact token agreement, rc1 for disagreement and rc2 for unavailable or
malformed evidence. It reports no transcript, residency or provenance verdict.

The retained public-JFK references parse as complete witnesses: 142 tokens for
480 ms and 136 for 960 ms. These are historical reference counts, not rebuilt
runtime parity. References stay at their original paths:

- `/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/ultra-adapter/probe-voxtral480-traced.log`, SHA-256 `5a1e91db2a59df826ae56c8efd7cfefb1e2f59ed6c942d146cc5e8f2f0cef44e`.
- `/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/ultra-adapter/probe-voxtral960-traced.log`, SHA-256 `90b944541763f10792d833fbc9513a40598890930612059b46b28c06d5c1aeb3`.

The running runtime-build row prevents publishing a final-runtime-bound parity
row this turn. Crisp calibration was armed with no terminal result available.
An initial bounded weight fetch timed out at 543,822,255/4,733,486,848 bytes.
A bounded resumable fetch is continuing in scratch, with an event registered
for `/mnt/raid0/llm/tmp/stt5/voxtral-weights-20261119/restore-result.json`.
Only PASS with the original pinned digest and size admits those bytes. The
receipt records the prepared stat identity for later grant-time drift checks;
no weight hashing belongs inside a grant.

Next: inspect the restoration receipt and file terminal build/calibration
results, then publish a public-JFK 480/960 ms parity row bound to the NEW runtime
hashes and original reference logs. Preserve all 10 prior validation results and
11 exposures, including the exposed UNKNOWN. No model was run this turn; no
validation, WER, rate, advancement or promotion follows. The parent stays open.

GitNexus status and upstream-impact commands both reported no index in this
lane. The new standalone module has no pre-existing callers; no refactor was
performed.
