# `.vidya/` — pilot ledger and checkpoints

Shadow-only. Nothing here gates any production decision.
Spec: [`docs/design/vidya-pilot-spec.md`](../docs/design/vidya-pilot-spec.md) §11.

| Path | Committed? | Why |
|---|---|---|
| `ledger.jsonl` | **no** (gitignored) | canonical record, but regenerable from its adapters and ~7.7 MB for a full intake ingest |
| `checkpoints/` | **yes** | an externally held checkpoint is what upgrades the ledger from tamper-*evident* to tamper-*proof* for prior history — git is the external holder |

Rebuild the ledger from the intake index:

    scripts/vidya/cli.py ingest intake --as-of <ISO-8601>
    scripts/vidya/cli.py verify          # chain + every committed checkpoint

`verify` reports `chain_ok` and `checkpoints_ok` separately on purpose. A tamperer who truncates
the log and recomputes the chain leaves `chain_ok=True`; only the committed checkpoint catches
them. Confusing the two would misdiagnose exactly the attack the checkpoint exists for.

## Ledger generations

- **Generation 1 (2026-08-09..10):** 20,331 frames at last attestation. The corpus is NOT
  reproducible from current code: it carried non-intake frames (sealed-manifest projections, a
  one-off correction backfill, write-time telemetry) whose ingestion paths no longer run. The
  gen-1 attestations are preserved in `checkpoints/archive-gen1-2026-08-09-10/` — git history is
  the external holder, and `verify` reports them as history-truncation if ever re-added.
- **Generation 2 (2026-08-26):** rebuilt from `research/intake_index.yaml` alone (12,479 frames,
  dedup-keyed ingest, so re-runs append nothing). Checkpoint `checkpoint-00012479.txt` is the
  current attestation. Non-intake producers (sealed manifests, AutoKernel receipts, …) project
  into the fold from their source sidecars and are checkpointed when their rows are ingested.
  The SC12-ENTRY amendment (intake-110 claim 04, 2026-08-26) re-emitted the checkpoint at the
  same tree size with a different root — the pre-amendment root is preserved in git (commit
  `a8e131af`).
