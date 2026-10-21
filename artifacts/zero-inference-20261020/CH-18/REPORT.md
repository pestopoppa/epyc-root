# CH-18 support (2026-10-20). gh queried live; champion = ak/champion/llama-cpp-ffc1bac82eec = dd3d9721c
| PR | state | upstream merge commit | in champion dd3d9721c? |
|---|---|---|---|
| #30514 plain KV honours PARTIAL_ONLY | MERGED 2026-10-15 | e467e5b5e | NO (src/llama-kv-cache.cpp has no PARTIAL_ONLY at dd3d9721c or ffc1bac82) |
| #26004 checkpoints in slot file | MERGED 2026-10-08 | 033df86b6 | PORT 1c999e15b (not ancestor; port commit) |
| #30574 draft state in slot file | MERGED 2026-10-15 | ea736c1d5 | PORT deb387b8b |
| #30580 SWA reuse off-by-two | MERGED 2026-10-15 | 61ad80bf9 | NO; tools/server/server-context.cpp:3398 @ffc1bac82 and :3759 @dd3d9721c both still `pos_next - n_swa - (has_new_tokens ? 0 : 1)` |
| #30141 MTP get/set_state | OPEN | - | no (watch) |
| #29480 iSWA seq_pos_max | OPEN | - | no (watch) |
| (extra) #27870 MMA barrier | MERGED 2026-09-07 | b74f590ea | not ancestor of champion/v10 |
| (extra) #28576 fp32 VKQ MFMA | MERGED 2026-09-14 | bfdc32183 | not ancestor |
| (extra) #26640 slot media | MERGED 2026-08-12 | 5d9e5ac30 | not ancestor |
Note: all upstream commits exist in the object DB but none is an ancestor of dd3d9721c/ffc1bac82 (squash-merge/port lineage); "in champion" = ported commit only.

## Launch recipes: explicit --spec-draft-p-min / --spec-draft-n-max?
Repo /mnt/raid0/llm/epyc-orchestrator.
- Launcher scripts/server/orchestrator_stack.py:_append_spec_decode_args: n-max emitted as `--spec-draft-n-max` (L478-479) when registry draft_max>0; p-min emitted ONLY if registry draft_p_min is set, and as `--draft-p-min` (L482-483), not `--spec-draft-p-min`. That is an accepted alias (llama.cpp common/arg.cpp:3948 @dd3d9721c `{"--spec-draft-p-min","--draft-p-min"}`).
- frontdoor (:8070; orchestration/model_registry.yaml acceleration at L1724-1732 and L2025-2032): spec_type draft-mtp, draft_max 4, NO draft_p_min -> n-max explicit, p-min NOT passed (rides upstream default, as the CH-18 text suspected).
- :8083 architect_critic (registry L1878-1883): draft-dflash, draft_max 7, NO draft_p_min -> n-max explicit, p-min NOT passed.
- Contrast: architect_general :8074 (L1932-1933) and L2240-2241 set draft_p_min 0.5 explicitly.
Not checked: stack_topology drafter_selection overrides at runtime (no live argv inspected).

## Proposed recorded list text (replace "Record in this handoff..." state)
Recorded 2026-10-20: #30514 MERGED e467e5b5e (not in champion; enters via pull), #26004 MERGED 033df86b6 (folded as port 1c999e15b), #30574 MERGED ea736c1d5 (folded as port deb387b8b), #30580 MERGED 61ad80bf9 (not in champion; server-context.cpp:3759 @dd3d9721c still carries the old threshold), watch #30141 and #29480 both OPEN. Launch-recipe check: frontdoor (draft_max 4) and :8083 (draft_max 7) pass --spec-draft-n-max explicitly but omit p-min (registry has no draft_p_min); only :8074 passes 0.5.

## Checkbox: CH-18 remains open: the "every check has a recorded result" clause still needs the candidate full-build checks (KPF-19.1, KVU-12.2 gate b, Gemma restore, checkpoint size). The list + recipe sub-check can be recorded now.
