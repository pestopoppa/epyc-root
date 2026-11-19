# M-12k smoke custody verdict, 2026-11-19

The 64,515th memory was written by the **plan-review external scorer**, not the normal task-outcome scorer. Custody identification is complete; M-12k remains open for the source fix, API integration and a passing qualification before any answer-quality run.

## Native observation

Read-only SQLite inspection found 64,515 rows. The added record has id
`62d15276-7aeb-4528-af5f-1ee148adcf31`, embedding_idx `64514`, SQLite rowid
`64519` (rowid is not the count), action `plan_review:parse_failure`, action_type
`plan_review`, outcome `failure`, Q=0, and created_at
`2026-11-19T15:26:23.031396+00:00`. Its record source is `external`, task_type
`coder`, and review_feedback is `parse_failure:extraction reply carried no parseable JSON`.

Its objective is the exact 199-character prefix of the whitespace-normalized
pilot prompt `mmlu_pro_business_00126`, one of the two smoke items. This binds
the write to the smoke's business question; the retained record cannot distinguish
ON from OFF, so no arm attribution is claimed. The smoke observed 64,514 before
and 64,515 after. No store rows were edited or removed.

Native evidence (no copied database or log):

- `epyc-orchestrator/orchestration/repl_memory/sessions/episodic.db`, logical row
  above: SHA-256 `c0fbe9a40e7b94659ba6082cbb1bdb4a44215880219c90007a644d5922f878fb`
  over UTF-8 `json.dumps(dict(row), sort_keys=True, separators=(',', ':'))`,
  selecting `rowid,*` by `embedding_idx=64514`.
- `/mnt/raid0/llm/tmp/m12k-gpu-20261119T1500Z/out/smoke/m12k-gpu-frontdoor-memory-ab-20261119.json`,
  SHA-256 `5accda020487bac59928419d7354069468f0aba0225ffc056fc9223b9562ca96`.
- `epyc-inference-research/data/ufh13-thesis/pilot_pool.json`, SHA-256
  `0898013e86b365d89cf941205e19e3843d4d3cd21f869d4db917496f030aa3c5`.

## Mechanism and zero-model reproduction

Source inspected at `epyc-orchestrator` commit
`94cd4320172eaaa1cb6ae19d5bc4c2fc86c106f4` (the named files have no tracked
working-tree changes):

- `src/api/routes/chat_review.py`, blob `fc8495c0bb75d9c0ed13f453581efbc6b4fd72e0`:
  `_store_plan_review_episode` calls `score_external_result` with
  `action=plan_review:<decision>` and a context that omits request_source.
- `orchestration/repl_memory/q_scorer.py`, blob
  `1136ce84a0ec584f5281c3ad76d8c32a5a1280aa`: `score_external_result` explicitly
  bypasses the progress-log reader, builds source=`external`, and creates/updates
  episodic memory. The separate `score_task` probe exclusion cannot protect it.
- `src/api/routes/chat_pipeline/routing.py::_plan_review_gate` stores any returned
  review, including `parse_failure`. A failed HTTP request can therefore already
  have stored a review before its final failure response.

Executed the actual `_store_plan_review_episode` AST function in an isolated
namespace with a recording scorer, no progress logger, a truthy hybrid router,
a stub stats updater and `task_ir.request_source='probe'`. **PASS reproduction:**
one scorer call, `action=plan_review:parse_failure`, reward=-1, and no
request_source in its arguments/context. No model, embedder, API or database
write was invoked. Separately, **PASS** the normalized prompt-prefix assertion.
This reproduces the source defect; it does not attest the running API's loaded
revision. The native row supplies the observed writer signature.

## Repair acceptance retained under M-12k

Before rerun, suppress episodic writes for smoke/probe/health at this external
write boundary while preserving review decisions and request routing. Add
regressions for all three non-learning sources (no scorer/store mutation) and
an ordinary learning request (review still scored). Preserve both A/B arms'
review behavior and the existing unchanged-store smoke assertion. Do not mask
the defect by changing the expected row count to 64,515 or disabling review in
only one arm. Integrate the fix in the orchestrator's owning lane, and attest
the loaded API revision at its owner's reload boundary.

The four non-200 smoke responses remain infrastructure failures, not incorrect
answers or evidence of no memory benefit. Existing API log lines
340112–340145 identify architect/coder fallbacks to unavailable backends.
The next qualification must serve the routes the API may select and preserve
HTTP failures in its receipts. Do not force both arms to the frontdoor or call
an HTTP 429 an unserved-role verdict without backend evidence.

This turn changes only the root-lane findings and handoff. No runtime repair,
API reload, row publication, production store restoration or answer-quality
claim is made. GitNexus status/impact found no index; the required indexing
wrapper refused CPU admission. The changed surface is documentation only.
