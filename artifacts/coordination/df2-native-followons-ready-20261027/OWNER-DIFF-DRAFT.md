# Owner-applied DF2 belief wiring — proposed

Copy `df2_row_exact.py` and `df2_native.py` to `scripts/vidya/adapters/`; add `df2-row-exact-akx` to CLI ingest choices and add this entry in `ingest_sources.SOURCES`:

```python
Source("df2-row-exact-akx", "df2_row_exact", _files("belief-native.json", "*/belief-native.json"),
       task="VB-DF2-ROW-EXACT-WRITE",
       note="producer-time DF2 output and diagnostic byte observations; strict same-device/shape/repeat/mutation rederivation; explicit --path only"),
```

Source table row in `scripts/vidya/adapters/README.md`:

`| DF2-20 native output / byte observations | measurement (prospective) | Producer writes native sidecar with source/build, case, raw and same-device residency hashes, explicit controls and output/diagnostic scope; no protocol is asserted. | VB-DF2-ROW-EXACT-WRITE: strict rederivation via df2_row_exact, shared ClaimTuple.grade(), explicit path ingest; no new ladder. |`

Handoff task in `handoffs/active/vidya-belief-substrate-program.md`:

`- [ ] **VB-DF2-ROW-EXACT-WRITE** — Install reviewed DF2 output and byte native producer/projector; register explicit-path ingest, source table and source-seal-bound receipts; require same-device residency, full per-shape/repeat coverage and negative controls; verify actual planning-context canary before calling either loop wired. Reuse measurement ClaimTuple.grade(), never invent a protocol or new ladder.`

GPU drivers require a JSON owner enrollment receipt bound to the resolved installed root, installed registry and adapter hashes, packet producer and source-seal hashes, and an independently retained planning-canary receipt and evidence hash. Use owner-canary.py in this artifact and the exact receipt schema in /mnt/raid0/llm/tmp/codex-ni-20261027-df2-followons-ready/ENROLLMENT-OWNER-INSTRUCTIONS.md. No owner enrollment receipt is issued here. The earlier synthetic registry/ingestion/consumer canary established private-worktree visibility only.
