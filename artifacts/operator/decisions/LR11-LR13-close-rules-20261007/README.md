# Human decision package — LR-11 / LR-13 close-time scratch rules

**Decision required:** whether to ratify the exact two-file, additive-only amendment in `artifacts/operator/lr11-lr13-close-rules-20261007.patch`. It clarifies that closing a completed ticket/PR requires the owning main to inventory declared scratch roots and lane worktrees, record retained paths/owners, and release only main-approved paths through the existing cleanup gate. It also requires each subagent brief to state private completion-record duties and scratch retention/release ownership. Prefixes remain discovery aids; no prefix-wide deletion, cleanup hook, cron, or auto-wrap is authorized.

## Context

LR-11 records 207 of 606 audited worktrees in the `codex-ni*`/`ni0X` lane class left behind after their owning ticket closed, and LR-13 requires explicit subagent record and scratch-lifetime rules. The existing wrap-up has a cleanup gate, but ticket-close inventory/retention ownership and brief-level private record/cleanup boundaries are not yet expressed in these two shared-policy surfaces. Those files are human-amendment-only.

The exact two additions were reviewed in the private source proposal under source commit `83004c1137015a9fc8d0cf411e648432bc51a1c9`; the patch SHA-256 is `e604ea87390029a4ea3d9f155d9d00dcb2dc4deae7c4d951e6b9e73687ec686b`. They were checked against the published ROOT `e7ff59beef6a625510020deb4f1e3da6ceed768b` preimage as well: the two policy blobs are `8290442dafcd0ad85d59947b625014d8392765d0` and `6cc2c3f52c6323cabedf755f7b54ccc8e0c1f5e8`. The patch applies cleanly there and adds lines only. A target whose blobs differ must refuse and be reviewed again.

## Options

**A. Ratify the bounded two-file amendment (recommended).** Apply the pinned patch under a typed human terminal signature, emit the consolidated, decision, and keyed receipts, and commit exactly the two policy files plus those three receipts through a private Git index, then refresh only those five preflight-clean ordinary-index entries. This creates a clear close-time inventory and retention record while preserving the existing cleanup gate and human control over each deletion. Cost: modest close-time recordkeeping. Risk: a close owner could omit an inventory; the receipt records the exact text change but does not prove future compliance. Reversible by a later human-only amendment.

**B. Keep status quo and leave LR-11/LR-13 open.** Do not amend the shared rules; continue using existing scratch cleanup practices without a ratified close-time policy. Cost: no policy rollout. Risk: ticket-close lane worktrees remain outside a common close checklist, and subagent scratch retention/record duties stay less explicit. No files or receipts change.

## Recommendation and default

Recommend **A**, limited to the exact reviewed additions. It defines an inventory and main-owned release checkpoint without enabling deletion by lane prefix or changing the existing cleanup safety gate. If no choice is made, default is **B**: no policy change, no signature or receipts, and LR-11/LR-13 remain open.

This package does not authorize a cleanup run, hook/cron installation, host change, shared-policy edit by an agent, or instruction-refresh claim. After ratification and merge, instruction refresh and acknowledgements remain separate work.

## Signing procedure

Run from the dedicated isolated operator checkout `/mnt/raid0/llm/worktrees/ni08-lr11-lr13-operator-20261007` after MAIN publishes and validates this ordinary package. The shared `/workspace` checkout may lag and will refuse when its protected preimages differ. The script's default `ROOT` is its own checkout. Review only (writes nothing):

```bash
bash artifacts/operator/ratify_lr11_lr13_close_rules_20261007.sh --review
```

If choosing A, the human operator—not an agent—runs this directly in an interactive terminal and types their own name:

```bash
RATIFY_OPERATOR='<your name>' bash artifacts/operator/ratify_lr11_lr13_close_rules_20261007.sh --apply --attest RATIFY-LR11-LR13-CLOSE-RULES-20261007
```

Use `--no-commit` only if the operator specifically wants the exact changes and receipts left uncommitted for inspection. The script defaults to committing the five exact ratification paths through a private index, with no push. The apply path rejects non-TTY execution, untyped/system/agent signers, changed patch/preimage pins, dirty target paths, partial prior application, failed receipt validation, and any non-additive or structurally invalid post-state. On refusal after receipt emission, it preserves the consolidated receipt under a unique `.refused.*.receipt.json` path before restoring the protected policy files; it removes only the new decision/keyed receipt artifacts. Re-running a fully ratified bundle is a no-op; partial states refuse for manual review.


The repository rule is explicit: `coordination/session-bus/human_only_paths.yaml` marks `agents/shared/*.md` human-only, and `agents/shared/OPERATING_CONSTRAINTS.md` § Operator Decision Requests states: “The operator signs from a terminal.” Chat consent cannot supply this receipt; run the signing command in a separate interactive terminal, without `!` or a chained activation command. MAIN will independently review the signed commit before normal publication.
