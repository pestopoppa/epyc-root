# Tencent/AngelSpec

PARTIAL at e02ea36e65d44e6e165c4ba73c139d500e12f2d9. Read README, DFly2 docs and target configs; no train/export/serve or weight round trip. Hy4/Hy4 Flash/GLM use 2048 picks; DS-V4.1 uses 512 plus 128 local, with target-specific dsv41_mla and mHC. Train configs and released weights include DS/GLM, while documented export and serving cover Hy4 variants. Paper numbers do not establish a turnkey vLLM runtime for the released DS/GLM drafts.

[Primary source](https://github.com/Tencent/AngelSpec)

## Evidence checked

- DFly2 selects sparse target positions using the last accepted token. (docs/concepts/dfly2.md:L12-L15 @ e02ea36).
- Draft attention reads existing target MLA latents. (docs/concepts/dfly2.md:L16-L18 @ e02ea36).
- The pinned docs describe DS-V4.1/GLM vLLM serving as future work. (docs/concepts/dfly2.md:L40-L45 @ e02ea36).

## EPYC applicability

MI210 price read-only resident sparse latent gather, layer/slot mapping and verify slope. CPU requires NPS4-local indirect reads. Bounded picks cap draft-attention work with context, without a supported gfx90a/CPU port or guarantee of total speed.

docs/concepts/dfly2.md:L9-L45, configs/vllm_dsv41_flash_dfly2.yaml and angelspec/config/dfly2_dsv41_flash_draft_config.json @ e02ea36. handoffs/active/deepseek-v41-flash-evaluation.md:L1663-L1669,L1786-L1806 @ a660ead. (EPYC root a660ead17).

## Counterevidence and limits

Hy4 Flash model card and press relay repeat Tencent results. Pinned docs flag missing public DS/GLM vLLM serving support for the released weights. No independent MI210 replication found.

## Derived action for review

Use as companion to DFly2. For INF-77 pin target/drafter versions and prove read-only released weight/latent/layer/last-accepted-position mappings, estimate gather bytes versus matched-width MTP/DSpark, then gate experimental serving if economics justify it. INF-50 can reuse target context on full-attention layers separately from native sparse index sharing.

handoffs/active/deepseek-v41-flash-evaluation.md

## Sources surfaced

arXiv:2611.34776 already selected and prior arXiv:2607.25852 indexed. Surface first pinned, working DS-V4.1 adapter if it can resolve serving/export.
