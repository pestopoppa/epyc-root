# AutoKernel GLM-5.3 external seed receipt — 2026-09-09

## Result

The external GLM-5.3 text/MTP candidate was recorded in AutoKernel's live `ExperimentStore` as **NOT ACCEPTED**. No keep, champion update, release, or production mutation occurred. The current champion remains `ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`.

The durable evidence bundle is:

- directory: `/mnt/raid0/llm/autokernel/loop-memory/external/glm53-core-c463-20260909/`
- envelope: `evidence-envelope.6ab1cd967603a6feb1ef369cc16a3756ea7eb3fd85e924ed847fff1a3cc9507f.json`
- envelope SHA-256: `6ab1cd967603a6feb1ef369cc16a3756ea7eb3fd85e924ed847fff1a3cc9507f`
- ingestion receipt: `ingestion-receipt.json`, SHA-256 `fc1a7c9334449dc6fafe5677f488ef912ad879b68fa127020156cc0ca619d096`

The envelope binds source commit `c463f601bd39d0e313b744c214b8c22f9455bcd3`, tree `1e207d5d3812ce7e57b41fad5c986eabdf1a1a19`, private branch `pestopoppa/llama.cpp:ak/champion-glm53-candidate-20260909`, experimental reference tip `f8e2668b6a951d7c44f3264f87d1bc882299bae5`, and merge base/champion `ef81196d5bdd4190b46dff4ae7eecc333a46c8ce`.

## ExperimentStore rows

All four records use campaign `ak-external-glm53-core-20260909`, status `measured_null`, and external epoch `42a410832477046d76aa848821a4e95a90ab8c61b09a87ac53aef986455d5943`:

| mechanism | attempt ID | disposition |
|---|---|---|
| `akm-external-glm53-core-fold` | `6ab1cd967603a6feb1ef369cc16a3756ea7eb3fd85e924ed847fff1a3cc9507f` | Validated source bundle, not accepted because the Qwen CPU performance observation remains an unresolved hold. No causal effect value was recorded. |
| `akm-glm53-iqk-expert-multirow` | `5f253506d81c4719f9b46bcd8813a8dc793a41944223d20c893310db1ef7f5e2` | Microbenchmark gain did not transfer to the exact short full-model screen; default off. |
| `akm-glm53-q8-rowexact-batch` | `fea70fa555936a9e050041db978b04c60f215d8c321cd17dafdd64d93ed40bfe` | Exact/replay gates passed, but the balanced short full-model screen was negative; default off. |
| `akm-glm53-cpy-outer-rows` | `dda07e5b904b55788cad9dda56de339addd12ed9afe921aff5ce10d4bb21da39` | Model-route mismatch; rejected CPY experiment was reverted by `f8e2668b6`. |

The first API insertion added four rows; an immediate identical second insertion added zero. Database count moved from 2,393 to 2,397. `archive.recall()` retrieved all four records and marked them `same_epoch=false`, `stale_epoch=true`, and `comparable_measurement=false`. Their visible statement/refusal fields carry the durable envelope path, envelope digest, private source branch, exact source commit, and unchanged champion.

The generated `experiments.md` was rendered against the unchanged live loop epoch `28fa1568cb2ba303522d9217547832c717cf9e546d5852732b66092401c496b5`, so the external rows appear as stale rather than relabeling the active loop. SQLite `PRAGMA integrity_check` returned `ok`.

## Copied evidence

The envelope lists and hash-binds 11 copied files; a fresh audit verified all 11 byte counts and SHA-256 digests:

- `handoff.md`
- `cpu-exact-lastnight-result.json`
- `gpu-exact-lastnight-result.json`
- `glm-core-comparison-audit.json`
- `q8-balanced-comparison-audit.json`
- `copy-selector-audit.json`
- `expert-off-response.json`
- `expert-on-response.json`
- `candidate-cpu-identity.json`
- `candidate-hip-identity.json`
- `reference-f8-identity.json`

The retained facts are scoped honestly: CPU 32.152575 versus historical mean 43.280708 is a single candidate observation against historical runs and therefore an unresolved regression signal, not a paired causal estimate; matched GPU DFlash2 was 79.598706 versus historical median 79.245255 with no slowdown signal and no speedup claim; GLM correctness passed 31/31 trajectories with real accepted and rejected drafts.

## Planner discovery

`/mnt/raid0/llm/autokernel/loop-memory/inbox/24-glm53-core-c463-external.md` (SHA-256 `36febdf81774907b731c913c9712fc989e9377d0b3f4c68fe9ccfa3cd4fff17f`) points the next loop to the exact source and envelope. `controller.inbox.read_inbox()` returned the pointer successfully. It is a hypothesis/reuse pointer only; measured disposition remains in `ExperimentStore`.

## Vidya wiring audit

No new source-table row is needed. `scripts/vidya/adapters/README.md:189` already registers “GLM53 text/MTP validation, CPU serving runs and phase-separated profiles” and explicitly includes three-lever bitwise gates, per-node timing, switch ablations, rejected variants, and matched repetitions. `handoffs/active/vidya-belief-substrate-program.md:1674` already owns the prospective work as `VB-GLM53-MTP`.

The existing generic AutoKernel corpus dispatcher does **not** read `ExperimentStore` SQLite rows: it walks schema-bearing JSON/JSONL documents, and this external pre-hook evidence contains no producer-authored ClaimTuple carrier. That is correct for this seed. The `measured_null` rows are loop memory and must not be retrofitted into Vidya as decision-grade claims. The existing `VB-GLM53-MTP` task remains the single prospective wiring home; adding another source entry would duplicate it.
