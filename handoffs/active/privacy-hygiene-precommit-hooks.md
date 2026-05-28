# Privacy / Secret Hygiene — Pre-Commit Hooks

**Status**: refreshed 2026-05-28 — PII-1 + PII-2 landed; PII-3 re-eval is overdue and is now the only open task
**Created**: 2026-04-24 (via research intake deep-dive — intake-452)
**Updated**: 2026-05-28
**Categories**: knowledge_management, document_processing, tool_implementation
**Priority**: MEDIUM (no immediate incident, but cheap insurance against accidental commits)
**Scope note**: NOT a close for [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) gap #5 (prompt-injection filter). PII span extraction is adjacent to, not a substitute for, adversarial-instruction detection. Gap #5 stays open.

## 2026-05-28 Audit Reset — Executor Start Here

This handoff should now be treated as a scheduled re-evaluation task, not an implementation task. The hook and fixture exist; the missed item is the 30-day checkpoint that was scheduled for 2026-05-24.

**Critique of older structure**: the completion banner was detailed, but the overdue PII-3 task was buried in the original plan. A fresh implementer could accidentally redo PII-1/2 instead of checking whether regex-only operation is good enough after three weeks of use.

**Verified landed evidence**:

- Root commit `788dc3d`: `scripts/hooks/pii_precommit.sh` + 40-example fixture.
- Root commit `bc04c84`: decimal-float false-positive fix.
- Hook scope remains pre-commit only; no pre-push hook has been justified yet.

**PII-3 re-eval runbook (no inference)**:

1. Confirm hooks are still installed in all three repos:
   ```bash
   for repo in /mnt/raid0/llm/epyc-root /mnt/raid0/llm/epyc-orchestrator /mnt/raid0/llm/epyc-inference-research; do
     printf '%s\n' "$repo"
     ls -l "$repo/.git/hooks/pre-commit"
     sed -n '1,40p' "$repo/.git/hooks/pre-commit"
   done
   ```
2. Run the fixture against the current hook logic. If no harness exists, use a temporary branch and staged synthetic files, then reset only those temporary files.
3. Search recent git history for bypass or complaint signals:
   ```bash
   rg -n "pii_precommit|--no-verify|false positive|secret hygiene|account_number" \
     /mnt/raid0/llm/epyc-root/logs \
     /mnt/raid0/llm/epyc-root/progress \
     /mnt/raid0/llm/epyc-root/handoffs
   ```
4. Append a `PII-3 Re-evaluation — YYYY-MM-DD` block below with false positives, false negatives, bypasses, and decision.

**Decision forks**:

| Evidence | Decision |
|---|---|
| Zero observed false negatives and only known decimal-float false positive class | Stay regex-only; mark PII-3 done; archive after index update. |
| >=2 novel missed shapes that a hybrid model would catch | Open a new hybrid/offline-batch handoff; keep pre-commit regex-only for speed. |
| Recurring false positives in normal configs/docs | Tighten regex and extend fixture; rerun PII-3 after the fix. |
| Users bypass with `--no-verify` | Add pre-push defense or clearer hook output, depending on bypass reason. |

## Objective

Install a fast regex-only pre-commit hook that scans staged files for accidentally-committed secrets and account-number-shaped strings across the three EPYC repos. Establish a held-out evaluation fixture so future "should we upgrade to a model-based hybrid" decisions are data-driven, not vibes-driven.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-452 | OpenAI Privacy Parser — inverse of OpenAI Privacy Filter (returns PII spans) | medium | adopt_patterns + narrow adopt_component (this slot) |
| intake-449 | OpenAI Privacy Filter (1.5B MoE PII token-classifier, opf weights) | low (stays bookmarked) | worth_investigating |

Deep-dives:
- [`research/deep-dives/chiefautism-privacy-parser-span-extraction.md`](../../research/deep-dives/chiefautism-privacy-parser-span-extraction.md)
- [`research/deep-dives/openai-privacy-filter-pii-preprocessor.md`](../../research/deep-dives/openai-privacy-filter-pii-preprocessor.md)

## Why this slot, not opendataloader Phase 2

The [`opendataloader-pipeline-integration.md`](opendataloader-pipeline-integration.md) handoff covers PDF → structured-context ingestion for the orchestrator's research/RAG path. Its **gap #5** is *prompt injection filtering*, which is adversarial-instruction detection — a different problem class from PII span extraction.

This handoff covers a **different slot**: pre-commit hygiene across three repos to prevent accidentally-committed credentials/secrets/account-numbers from entering git history. That's a workflow-level concern, not an inference-pipeline concern.

The intake-452 deep-dive's hybrid model+regex pipeline (`HybridPIIParser`, ~600 ms/call CPU) would be too slow to run on every commit anyway. **Regex-only is the correct choice for the pre-commit slot.** Hybrid is reserved for offline batch hygiene if a future incident shows regex is missing things.

## Work Items

### PII-1 — Regex-only pre-commit hook (MEDIUM, ~half day)

Implement `/workspace/scripts/hooks/pii_precommit.sh` and install across the three EPYC repos.

**Behavior**:
- Reads staged files via `git diff --cached --name-only -z` and the corresponding staged blobs (NOT working-tree contents — must catch `git add -p` partial stages correctly)
- Gates on **two label categories** (per intake-452 deep-dive's high-precision regex set):
  - `secret` (AWS-key / GitHub PAT / Slack token / private-key-PEM / generic high-entropy 32+ char hex/base64 patterns)
  - `account_number` (long digit runs in non-numeric contexts, with phone-number disambiguation per intake-452's asymmetric override rules)
- Skips files larger than 1 MB (binaries, GGUFs — already gitignored per `feedback_gitignore_binaries`, but defense-in-depth)
- Skips files matching the existing `.gitignore` patterns
- Exit 1 on any match with a clear message naming the offending file + line + label
- Exit 0 on clean staged set

**Reuse pattern**: model after `scripts/hooks/check_filesystem_path.sh` and `scripts/hooks/check_pytest_safety.sh` — pure-bash hooks already established in this directory. Same `set -euo pipefail` + `agent_log` integration.

**Install across three repos**:
- `/mnt/raid0/llm/epyc-root/.git/hooks/pre-commit` (this repo)
- `/mnt/raid0/llm/epyc-orchestrator/.git/hooks/pre-commit`
- `/mnt/raid0/llm/epyc-inference-research/.git/hooks/pre-commit`

Each `pre-commit` should source/exec `pii_precommit.sh` from a known path (suggest: keep the script in `/mnt/raid0/llm/epyc-root/scripts/hooks/` and symlink/source into each repo's hook chain).

**Important**: do not skip hooks (`--no-verify`) when the script flags a real issue — fix the file. False positives should be addressed by tightening regex, not by bypass.

### PII-2 — Held-out evaluation fixture (LOW, ~1 h)

Build `/workspace/research/fixtures/pii_hygiene_eval.jsonl` with **30–50 real-shape examples** drawn from realistic-but-fake credentials and account numbers in the contexts they would actually appear (config files, code comments, test fixtures, docs). Include:

- 10–15 true-positive examples per label (secret, account_number) with known span boundaries
- 5–10 hard-negative examples per label (e.g. high-entropy hashes that are NOT secrets, long timestamps, version IDs that look numeric but aren't account numbers)
- Schema:
  ```json
  {"text": "...", "labels": [{"start": 12, "end": 32, "label": "secret"}], "expected_match": true|false, "context_type": "config|comment|fixture|doc"}
  ```

**Data source guidance**: synthesize examples using realistic prefixes from public docs (AWS CLI examples, GitHub PAT format spec, etc.) — never use real credentials, never paste real secrets into the fixture, even as "fake but real-shape."

### PII-3 — 30-day re-evaluation checkpoint (scheduled, 2026-05-24)

After 30 days of regex-only operation, evaluate whether to upgrade to `HybridPIIParser` (intake-452, ~3 GB opf weights, ~600 ms CPU latency). Decision gate:

- **Upgrade if**: regex-only missed ≥2 novel shapes that the hybrid model would have caught (evidenced by either (a) a real near-miss commit caught manually, or (b) evaluation against the PII-2 fixture showing the hybrid catches additional examples the regex misses)
- **Stay regex-only if**: zero false negatives observed AND zero/low false-positive complaints over 30 days

This is intentionally a **schedule item, not a do-now task**. Set a reminder for 2026-05-24 (e.g. `/schedule` agent or calendar entry).

**Audit update 2026-05-28**: this checkpoint is now overdue. Run the re-eval block above before any other work in this handoff.

## Reporting

- After PII-1 lands: confirm hook fires on a synthetic fixture commit (positive control) and exits 0 on clean commit. Update this handoff with commit SHA + smoke-test summary.
- After PII-2 lands: record the fixture stats (count by label, count of hard-negatives) and any regex tweaks the fixture motivated.
- For PII-3: append a 2026-05-24 evaluation block with the decision and rationale.

## Open Questions

- Should the hook run on `git push` instead of (or in addition to) `pre-commit`? `pre-commit` is faster feedback but `pre-push` is the last line of defense. Recommendation: pre-commit only initially; add pre-push if the eval fixture surfaces shapes the regex misses.
- Should we add a `secrets-baseline` allow-file (analogous to `detect-secrets`) for known-fake test fixtures (PII-2 itself contains realistic-shape fake secrets, which the hook would flag if PII-2 is staged)? Yes — the hook should skip files matching `research/fixtures/pii_*` paths.
- Does any pre-existing CI workflow already cover this? Verify before duplicating: `grep -l "secret\|password" /workspace/.github/workflows/*.yml 2>/dev/null` and the equivalent in epyc-orchestrator and epyc-inference-research.

## Notes

- All actions in this handoff are non-inference. Schedule on next available code-work session.
- Per `feedback_license_not_a_blocker`, do not raise license concerns about the underlying intake-449 opf weights when (or if) PII-3 leads to a hybrid upgrade.
- Per `feedback_opensource_only`, this remains an open-source self-hosted tool path (regex hook + optionally local opf weights).
