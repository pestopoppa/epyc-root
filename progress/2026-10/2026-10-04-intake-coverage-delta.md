# Research-intake coverage delta — implementation

Operator explicitly requested implementation of `ID-RI-COVERAGE-DELTA`, previously filed by the
[practical-application retrospective](../../docs/reviews/research-intake-practical-applications-20261004.md).
This is an existing workflow repair, not a new intake, source expansion or application campaign.

## Scope and isolation

Implementation uses branch `intake/coverage-delta-20261004` at
`/mnt/raid0/llm/worktrees/intake-decision-tools-coverage-20261004`, based on root
`86fab2e6d69e5fa9136d8704cd0e4e857bb092b1`. The shared checkout's unrelated tracked/untracked
changes are preserved. Independent agents own instructions, the opt-in validator and regression
fixtures; main owns integration, review and durable accounting. No intake entry, historical approved
plan or retained campaign checkpoint is edited. The installed Codex mirror is also updated in place.

GitNexus status is current only for the older shared checkout. Impact/context queries cannot resolve
`validate_plan_payload` in that graph; risk remains UNKNOWN, not LOW. Direct inspection identifies
the opt-in CLI/wrapper path and regression callers. No graph metadata is erased or a frozen kernel
modified. Graph refresh and test suites require CPU admission; occupied regions are not bypassed.

The session-bus drain refused `codex-intake-20261003` because it is not a roster identity. No other
writer is impersonated and no roster configuration is changed.

## Intended operational behavior

- Review selected verified mechanisms against current consumer behavior before generating IDs.
  A source-first opportunity scan makes declared applications visible even if both ID inventories
  omit them; it does not prove exhaustive discovery.
- Bind recommendations to declared owners and exact checkbox text, with operational outcome,
  acceptance and main review. An ID in another owner, an enabling component or an adjacent fix is
  not evidence that the requested behavior is supplied.
- Reconcile Stage-3 actionable additions and complete verbatim steering in memory. Stage 3 writes
  only the plan; Stage 4 requires reconciled checkpoint identity and actually applied task text.
- Require the version-2 payload on new Stage-3 plans, while preserving legacy completed-payload
  validation and the default index validator. Machine checks remain structural, not a semantic
  classifier, ROI score or authorization.

The existing intake conformance source and `VB-RI-OPS-WIRE` registration cover these fixtures.
Native capture/projection remains explicitly prospective; ordinary tests make no measurement,
source-completeness or semantic-equivalence claim. No new evidence class or grading ladder is added.

## Accepted implementation and verification

The existing opt-in validator now enforces version 2 for new Stage-3 plans, including a checkpoint
that attempts to bypass it with an older filing payload. Historical unversioned/integer-v1 Stage-4
payloads keep the legacy path. Default `validate_index` is unchanged.

Coverage checks preserve recommendation source/action text; union plan-only additions without
checkpoint writes; reconcile unique verbatim steering rows and declared references; bind each
outcome to exact owner checkbox text and acceptance; require P/K/M opportunity reviews; and reject
unresolved reviews, dangling scan references and unmapped proposed tasks. Exact incumbent text
supports same-ID refinements. Stage 4 requires already reconciled additions/steering and actual
applied task/stub/index-row text. It cannot discharge a task with a self-mention or a task in another
owner. All checks remain read-only, with explicit malformed-input errors.

The first integrated suite found two failing source/action immutability mutations; these exposed
table cells not yet compared with the retained ledger. The fix binds those cells, with citation
suffixes permitted only without changing source identity. Final acceptance ran under CPU region q1:

- `pytest -c pytest.ini .claude/skills/research-intake/scripts/tests/test_validate_intake_plan.py
  tests/skills/test_research_intake_id_sequencing.py
  tests/skills/test_research_intake_disposition_backfill.py -q`: **73 tests, 218 subtests passed**.
- Skill-creator frontmatter/scaffold validation passed for both the project skill and installed
  Codex mirror.
- Default wrapper and completed decision-tools opt-in plan/checkpoint validation each passed:
  **1,895 entries**. The historical plan/checkpoint hashes remain unchanged.

The installed mirror and its default prompt prioritize concrete operational outcomes. Its source
lookup now distinguishes an up-to-date project lane/origin revision from the older shared checkout;
unrelated shared work is never reset to deploy the instructions.

An independent read-only forward-test on four synthetic raw scenarios retained termination,
runtime action scoring, actual cross-harness/SFT work and native looped feasibility instead of
substituting enabling work or production admission. It also exposed ambiguous wording around
optional validation, preapproval task packages and unverified hypotheses; these were clarified.
This is qualitative illustration, not blind behavioral validation or proof of improvement: prior
normative examples were visible in its instruction read. Future discovery readers receive raw
artifacts without the post-reader rubric, retained in the existing tests.

GitNexus refresh ran via the project wrapper under q0 and its nonblocking repository lock
(59,984 nodes, 86,993 edges). Even the refreshed lane graph cannot resolve the hidden validator
symbols; impact remains UNKNOWN. Direct callers were inspected. No graph metadata was deleted.
`git diff --check` and the strict lane-location check passed. The implementation closes one own
handoff checkbox; the three operational application proposals from the retrospective remain open
and were not executed by this skill repair.

The final handoff integrity gate passed with **zero problems**; citation validation checked 81
references across the two changed owners with no blocking citations. Existing review/unknown
warnings and 162 legacy missing-Scratch declarations remain visible, not suppressed. The generated
research/evaluation open count drops by one. No index pruning, archival or wiki compilation sweep
is performed during this per-task close-out.
