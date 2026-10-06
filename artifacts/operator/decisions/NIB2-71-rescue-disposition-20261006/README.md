# NIB2-71 branch disposition decision package

**Decision requested:** choose the fate of `rescue/shared-clone-dirty-20260907` (`63ec9f534bc7b1adc15958512019bf371cee0b2a`). The task asks to fold its residue or delete the branch, so review alone does not close it.

**Evidence:** current RESEARCH `origin/main` is `1bace97dc655ab5896291b4571781e53b821d9a3`; CH-8 (`162d17dd0239e7c38bbb318527e0d11ea9456a22`) is its ancestor. The rescue source's expanded ROCWMMA/`GGML_NATIVE` build rationale appears in current `discovery_deployment_factory.py` (main lines 2147–2175) and the host-build guidance is in README lines 155–171; no source-note fold is needed. All 11 changed rescue paths exist on current main with revised contents; adjacent JSON and diff capture blob IDs, SHA-256 values and comparisons. The earlier custody directory contains an exact patch for nine modified paths plus byte-identical copies of both added benchmark scripts. This is complete same-volume custody under `/mnt/raid0/llm/tmp`, not independent off-volume archival storage.

**Option A — retain (recommended):** amend NIB2-71 to preserve the rescue ref as explicitly archival recovery provenance. It retains the exact historical tree and avoids remote ref mutation; close the bounded review without source edits.

**Option B — delete:** first create and verify independent durable custody of the rescue commit and all 11 changed paths, then remove the remote ref. This removes a stale branch but adds custody and ref-deletion work.

No branch, worktree, or project file changed during review. MAIN applies the selected canonical update.
