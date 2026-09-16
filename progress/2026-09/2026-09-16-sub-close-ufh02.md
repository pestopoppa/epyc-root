# UFH-02 closure: hermes-outer-shell → completed (sub-close-ufh02, 2026-09-16)

**Trigger:** operator decision HS-4 (2026-09-16). OpenCode is the shell, Hermes-style features are
built inside the orchestrator, and Hermes was not selected. Zero inference.

## Done

- **Findings extracted** to `docs/reference/harness-candidates/` (new directory):
  - `hermes-evaluation-20260916.md`: decision, assets, plugin behaviour, the six bypass paths, the
    memory model, config lessons and follow-up status.
  - `client-surface-audit.md`: the reusable instrument (contract, Steps 1–4 including the HS-1g
    call-verb check, and the 2026-07-04 reference results). HS-4 P0.3 now links to it.
  - `patches/hermes-agent-532a49f1-plugin-slash-commands.patch`: the local-only Hermes commit
    `532a49f1`, which is on no pushed ref, exported so the work is not lost.
- **Open boxes (11):**
  - 2 ticked on existing item-G evidence (multi-turn, delegation; `BULK-hermes-smokes-20260721T042834Z`).
  - 4 closed SUPERSEDED (code execution, memory persistence, latency, compression trigger).
  - 5 closed here and moved: the shell-agnostic `/v1` override validations (streaming with
    overrides, `x_disable_repl` end-to-end, `x_max_escalation` full graph, and the item-P parent
    plus its live `--send` child). They now form one new box, "HS-4 P0.4 carry", in
    `harness-selection-and-integration.md`.
- **Moved** with `git mv` to `handoffs/completed/`. Added a completion header, repointed the moved
  file's sibling links to `../active/`, and fixed inbound links in handoffs (active and archived),
  docs, wiki, research deep-dives and the `run_hermes_smokes.sh` header.
- **Follow-ups already closed elsewhere:** the inert `mempalace:` block (root `91d56181`) and the
  dead `/v1` `recall()` (orchestrator `83c7ed2f`). No Hermes item was filed under AP-04 or AP-54b.

## Left for the owning session

- **Delete the UFH-02 row** in `user-facing-harness-index.md`, then regenerate the index state.
  `index_state.py --check` currently reports `DEAD LINK: row UFH-02` and a stale master generated
  block.
- **Not rewritten** (generated, lock or evidence files that still carry the old `active/` path):
  - `coordination/inference-batch/{entries/30-bulk-campaign.yaml,manifest.yaml,sources.lock.json}`
  - `research/intake_index.yaml`
  - `wiki/source_manifest.json`
  - `scripts/handoffs/closure_audit_triage.json`
  - `artifacts/audit/`, the batch bundles, and the superseded `BACKLOG-DISPATCH-QUEUE.md`
