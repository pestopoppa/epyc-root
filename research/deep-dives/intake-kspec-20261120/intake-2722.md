# nari-labs/Qwen3.8-27B-NariQ-GGUF (model card)

- **Intake**: intake-2722 (`intake-2722#record`)
- **Source**: https://huggingface.co/nari-labs/Qwen3.8-27B-NariQ-GGUF
- **Verification**: dive-verified · read depth PARTIAL
- **Disposition**: declined; handoffs: none
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Companion card; its accuracy table restates the paper (not corroboration). Cite only the file list, the fork requirement and the stated backend limits.

## Key claims (anchored)

0. The card table reports DeepSWE fully solved share BF16 38.9 (44), NariQ 3-bit 41.6 (47), 2.5-bit 40.7 (46); these are the paper counts as a percent of 113, not an independent replication.
   - Card results table: "BF16 (53.8 GB) 38.9 (44) 62.6 (154)"
1. The card states pre-Ampere GPUs fall back to slow CPU execution and AMD and Intel GPUs are not supported yet.
   - Card Known limits: "GPUs older than Ampere fall back to slow CPU execution, and AMD and Intel GPUs are not supported yet"

## Claim corrections

- claim 0: **reattributed** — Restatement of the paper (same counts); not corroboration.
- claim 1: **unaffected** — Confirmed verbatim.

## Dive record

2026-11-20 Stage-2 dive (sonnet, together with intake-2721). PARTIAL: card tail is the verbatim base-model card (skimmed); chat-template blob skipped. Card files 10.12/8.44/6.75 GB at 3.0/2.5/2.0 bpw plus 0.93 GB BF16 mmproj; MTP not included; speed table RTX PRO 6000 only (3.0 bpw 88.9 tok/s at 4K vs UD-IQ3_XXS 94.7, so not faster on that GPU). Card BF16 size 53.8 GB vs paper 55.6 GB (minor). lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)
