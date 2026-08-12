# Keyed receipt index — the C39 contract

One file per SIGNED operator gate: `<GATE_ID>.json`, schema
`session_bus.receipt_index.v1`. Each file is a **POINTER to the receipt, never a
copy** — duplicating a signature would create a second source of truth. The
coordinator-daemon's spent-gate check stats exactly this path
(`spent_receipt_for(gate_id)`), so a gate with no file here is presented as
pending even if its receipt exists elsewhere on disk. That is the failure that
re-presented two already-signed gates for 13 days (audit
`artifacts/audit/completion-flurry-wiring-audit-20260811.md` §D).

## Authoring contract for new ratifiers (token-bearing `--attest` scripts)

At `--attest` time, AFTER writing your receipt, also write the keyed index —
and refuse in preflight if the index already exists (double-signing must fail
loudly at the script, not read wrong in the queue). Canonical snippet (adapt
`receipt`/`token` variable names; see `ratify_consolidated_era_rows_20260811.sh`
for a live example):

```python
index_dir = os.path.join(os.path.dirname(receipt), "receipts")
os.makedirs(index_dir, exist_ok=True)
index_path = os.path.join(index_dir, f"{token}.json")
with open(index_path, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": token, "indexed_by": "attest", "receipt": receipt,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
```

Keep ratifiers **self-contained** — do NOT source a shared snippet at runtime: a
signed artifact whose behaviour depends on an unpinned external file is no
longer the thing the operator validated. The mechanism that keeps this contract
honest is checking, not memory:

- **Authoring/static**: `scripts/operator/check_ratifier_receipt_contract.sh`
  (exit 1 on any signable token script lacking the write, or any on-disk
  ratified receipt lacking its index; writes nothing).
- **Runtime/bus**: `scripts/coordination/session_bus_coordinator.py
  backfill-receipts --check` (bus-known gates; mainD, C39).

Out of scope: dry-run/apply-generation amendment vehicles with no token argv —
their gates never enter `token-queue.md`.
