# Kernel release manifests

A manifest is the running ledger of one next-production kernel set: one table, one row per feature, keep, fix, model-support or test-harness item that the champion carries, may carry, or has excluded. Current manifests: [`llama-v11-manifest.md`](llama-v11-manifest.md) (next llama.cpp production, built from `ak/champion/llama-cpp-ffc1bac82eec`) and [`speech-v2-manifest.md`](speech-v2-manifest.md) (`production-speech-v2`: whisper.cpp + qwentts.cpp).

## Rules (operator directive 2026-10-20)

1. **Fold only into champions.** Features and performance improvements are folded into a champion branch; nothing is promoted to production piecemeal. The next production kernel upgrade must be significant.
2. **Same-commit update.** Every fold, keep, exclusion, rebase, branch push or deletion, and owner change edits the affected manifest row in the same commit. A row never leaves the table; a superseded row points at its successor.
3. **Evidence discipline.** Gains are copied from the cited artifact, never recomputed or invented. A per-keep AutoKernel percentage is a 5-pair screening number, not a marginal or additive effect (aggregate CH-16).
4. **Presence gate = promotion gate.** Each row names the gate that proves it is still in a candidate (ancestry/`git cherry`, an op test, a `strings` probe, a bench cell). A promotion candidate must pass the presence gate of EVERY row whose status is `in champion`, and every `pending fold` row must be folded, excluded with a reason, or deferred explicitly before the freeze. A row with no gate is a defect.
5. **At-risk check.** Before a promotion, list rows that are kept but unfolded, local-only (not on the `fork` remote), on a stale base, or owned by a gone session, and resolve each.

Production trees stay frozen; the manifests are read-only analysis documents and never authorize a build or a branch switch in a frozen tree.
