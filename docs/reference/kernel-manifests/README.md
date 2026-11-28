# Kernel release manifests

A manifest is the running ledger of one next-production kernel set: one table, one row per feature, keep, fix, model-support or test-harness item that the champion carries, may carry, or has excluded. Current manifests: [`llama-v11-manifest.md`](llama-v11-manifest.md) (next llama.cpp production, built from `ak/champion/llama-cpp-ffc1bac82eec`) and [`speech-v2-manifest.md`](speech-v2-manifest.md) (`production-speech-v2`: whisper.cpp + qwentts.cpp).

## Rules (operator directive 2026-10-20)

1. **Fold only into champions.** Features and performance improvements are folded into a champion branch; nothing is promoted to production piecemeal. The next production kernel upgrade must be significant.
2. **Same-commit update.** Every fold, keep, exclusion, rebase, branch push or deletion, and owner change edits the affected manifest row in the same commit. A row never leaves the table; a superseded row points at its successor.
3. **Evidence discipline.** Gains are copied from the cited artifact, never recomputed or invented. A per-keep AutoKernel percentage is a 5-pair screening number, not a marginal or additive effect (aggregate CH-16).
4. **Presence gate = promotion gate.** Each row names the gate that proves it is still in a candidate (ancestry/`git cherry`, an op test, a `strings` probe, a bench cell). A promotion candidate must pass the presence gate of EVERY row whose status is `in champion`, and every `pending fold` row must be folded, excluded with a reason, or deferred explicitly before the freeze. A row with no gate is a defect.
5. **At-risk check.** Before a promotion, list rows that are kept but unfolded, local-only (not on the `fork` remote), on a stale base, or owned by a gone session, and resolve each.

## Champion serving config (operator directive 2026-11-24)

The [v11 A3B candidate evidence and worker gates](../../reports/v11-performance-closeout.md) track model-specific trials before the promotion package binds a serving role.

From C22 on, each champion ships a serving-config artifact next to its manifest, at
`docs/reference/kernel-manifests/serving-configs/<champion>.serving-config.json`. For each served model and
role it carries:

- **optimal**: the fastest screened serving config (server argv deltas, np, b/ub, KV, ctx checkpoints,
  cache-ram, drafter and draft window, sampling defaults where the role allows them to move);
- **tradeoffs**: a table of throughput vs latency vs temperature/acceptance vs memory, so a change such
  as a temperature move is an informed one;
- **alternates**: 2-3 named configs, for example `latency`, `throughput` and `low-temperature` (T 0..0.6; operator 2026-11-24: no high-temperature testing, T > 1.0);
- **provenance** on every entry: the row id, RESULT.json path and sha256, and the store it ran on.

Validation (`scripts/champion/serving_config/validate_serving_config.py`; both programmatic callers, `package.sh`
and the orchestrator's `serving_config_registry.py`, run it with `strict_files=True`, so a missing RESULT.json or
a sha mismatch fails the package): an `argv_delta` row for a value-taking flag must carry a typed `value`
(`|` and whitespace are rejected; only a known bare switch omits it); `np`, `ctx_checkpoints` and `cache_ram_mib`
are compared against the server's `registry_runtime` snapshot, like the `serving_shape` fields, and a difference
needs its delta flag; throughput numbers derived from a row's own aggregate are labelled `DERIVED` in
`throughput_basis`.

At production promotion the package writes the registry `serving_shape` and its alternates from this
artifact. That registry write is a stack change bundled into the kernel promotion, under the same single
operator signature. Implementation: CHAMPION-SERVING-CONFIG-1 and PROMOTION-REGISTRY-SERVING-1 in
`handoffs/active/kernel-champion-and-promotion.md`.

Production trees stay frozen; the manifests are read-only analysis documents and never authorize a build or a branch switch in a frozen tree.
