# 2026-10-20 — retire Qwen3.8-Flash-Next IQ4_XS-uniform (keeper UD-IQ4_XS)

Operator ruling, 2026-10-20: *"if we don't plan to use this model, we should probably fix the
orchestrator config issues, the handoffs referencing it, and focus on UD-IQ4 XS instead. This will
allow us to reclaim more space."*

This entry covers the reference retarget only. The 98.4 GB GGUF is still on disk; deleting it is the
operator's action.

## What changed (branches `retire/iq4xs-uniform-20261020`, three repos)

- **research**
  - `scripts/lib/qwen38_flash_next_recipe.py` (rev 2026-10-20) now sets `TRUNK_*` to the UD-IQ4_XS
    3-shard set, with `TRUNK_SHARDS` holding path, bytes and sha256 for each shard. The validators
    iterate every shard, because shard 1 is metadata only.
  - The uniform file is kept as `MEASURED_TRUNK`, and every `HEADLINES` entry carries
    `measured_on_artifact`. The retired path now raises a `RecipeViolation`.
  - The UD census was computed with gguf-py over the shard headers: 5.839 GB/token, 7.002 bpw and
    6.671 B active. The same script reproduces the uniform file's 4.166 / 4.995 / 6.671 exactly.
  - Master registry: retirement notes and a corrected `qwen38_flash_next_ud_iq4xs_local.description`.
- **orchestrator**: the lean registry was recompiled from the edited master. Only the description
  and the header changed. Descriptors and priors are content-identical, so they were not touched.
- **root**
  - INF-70 HARNESS-1 `arm_{cold,hot}.sh` now default to the UD shards and evict all three.
  - PROD-3 in `cpu-decode-roofline-program.md` records the ruling and the epoch reset.
  - EXL3-6c5 and the iqk Step 3 / admission criterion drop the uniform arm.
  - The AMD-lab card text in `dashboard/static/amd-ai-lab/app.js` was updated.

## Measurement consequence

Every INF-70 CPU-decode headline was measured on the retired uniform file. That covers 23.16, 33.370
and 43.281 / 27.893 t/s, and also 52.661 and 52.7.

UD streams +40% bytes per token, and OP-32 measured UD −13% on decode. A re-bench on the served
artifact is therefore expected to read lower. That is an epoch reset, not a regression.

## Not done here

- `epyc-web/app.js` carries the same card sentence and needs the same edit.
- The AK `ak-q38fn-cpu-decode-20261003` lane already targets UD. Its seed inbox prose mentions uniform
  as history only.
- Graveyard row: drafted in the hand-back. Write it only after the operator deletes the file.
