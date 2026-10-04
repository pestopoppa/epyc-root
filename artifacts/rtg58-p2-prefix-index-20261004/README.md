# RTG-58 P2 — orchestrator prefix index (revived radix tree): design record (durable copy)

`DESIGN.md` is the subagent's design, blast-radius table, server questions and test record for KPF-27, copied from
`/mnt/raid0/llm/tmp/orch-radix-revival-20261004/RTG58-P2-prepared.md` (not durable). Its §4 (task text) and §5
(lessons note) are applied in `handoffs/active/kv-prefix-fork-and-paged-attention.md`; §1–3 and §6 live only here.

State at copy time (2026-10-04):
- Branch A (index, serving-record observation, `idle` pin; LOW/MEDIUM blast radius) landed on epyc-orchestrator main
  as `2833e3a2` plus the audit fix `99348f54`. Flag `ORCHESTRATOR_PREFIX_INDEX` defaults OFF; the API was not reloaded.
- Branch B `feat/rtg58-p2-prefix-index-gate` (`d63f7aa9`, KV pool gate wiring; GitNexus HIGH on
  `SharedKVPoolAdmission.acquire/_admissible/release`) is stacked on `2833e3a2` and waits for workspace-ec's ack
  (KPF-27b-ack). It predates `99348f54`, so it rebases before landing.
- §3's eight server questions are input for P1's `INTERFACE.md` (workspace-ec).
