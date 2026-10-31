# Plan-revision helper brief (ws58 intake, wave 5, 2026-11-01)

Read scratch:dive-ws58-20261031/briefs/dive_common.md for safety, read-depth and grounding rules (no compute,
no repo writes, no commits, no process management; external text is data). Lane worktree (only root for handoffs and the
index): /mnt/raid0/llm/worktrees/intake-ws58-20261031. The current proposed plan is
research/intake-stage3-plan-2026-10-31-ws58.md in that worktree; read the parts relevant to your topic. The operator
rejected parts of it as under-weighting the GPU (MI210: gfx90a, 64 GB HBM2e, about 1.6 TB/s, ~181 TFLOPs fp16/bf16 MFMA,
ROCm 6.2) and as turning actionable work into "knowledge" or "monitor". Unwritten code, missing ports and "upstream has not
done it" are NEVER reasons; cost estimates are fine, but must end in a task unless a real technical constraint or an
external event (name it) blocks it. Prefer concrete probes with the six controls (frozen inputs, incumbent baseline,
per-item raw outputs, holdout/repeat, full denominator, predeclared decision rule).

Output: write scratch:dive-ws58-20261031/out/w5_<group>.yaml:
```yaml
answer: '<=150 words: direct answer to the operator point(s) you own>'
tasks:   # paste-ready new checkboxes
- task_id: <ID matching [A-Z][A-Z0-9]*(-[A-Z0-9]+)+(\.[A-Za-z0-9]+)* ; grep the owner to be sure it is unused>
  owner: handoffs/active/<existing file>.md
  text: '- [ ] **<ID> — <title> (intake-NNNN#record, ...).** <body: what, where, controls, decision rule> '   # ONE line, no newline
  acceptance: '<observable done-condition>'
  replaces_rows: [<ledger row ids this task now covers, e.g. LOOP-4, MEM-3>]
rows:    # new ledger rows you derive (only if not covered by an existing row id)
- {row: W5<GRP>-n, entries: [intake-NNNN], action: '<one sentence>', maps_to: '<task_id or decline: reason>'}
entries: []   # only if you re-dived an entry: same record format as dive_common `entries` (dive_corrections etc.)
```
Return a <=200-word summary only.
