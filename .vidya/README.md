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
