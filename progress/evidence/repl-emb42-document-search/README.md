# REPL-EMB-4.2 document-search candidate

APP baseline: `488b31c96c6c148768508b3dcaefcb6c4c297664` (`src/repl_document.py`). The patch is a draft, not an applied or deployed feature. It keeps legacy `search_sections` by default; an explicit constructor opt-in builds the existing retrieval index lazily and resolves the existing pool embedder on every search by default (or accepts an explicitly injected embedder, including None for lexical-only). Results name absolute offsets and lines in the context consumed by `peek`; source matching requires the reconstructed document to be the context suffix. A context bundle redirects `peek`, so opt-in search refuses in that case rather than returning an unreadable or unaccounted pointer.

`test_candidate.py` exercises the candidate against APP dependencies. The controls cover opt-in hybrid with a fake embedder, dynamic pool resolution, legacy opt-out, lexical fallback, invalid context and bundle refusal. Invocation:

```bash
PYTHONPATH=/workspace/repos/epyc-orchestrator /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q progress/evidence/repl-emb42-document-search/test_candidate.py
```

The imported `context_search.py`, `file_exploration.py`, `environment.py`, and `models/document.py` match the stated APP origin baseline. This is not complete integration: request-level opt-in and an accounted document read for bundle-attached sessions remain unresolved. No inference was run; the fake embedder establishes no retrieval-quality claim.

## Request opt-in candidate (2026-11-02)

`request-opt-in.patch` is the request-path candidate. It adds `ChatRequest.document_search` (default false), requires `force_mode='repl'`, refuses a context bundle at request validation, passes the flag to the document REPL constructor, bypasses script interception for opted-in requests, and returns HTTP 422 if preprocessing did not produce a document. It also rejects streaming, whose path does not attach the document-search environment. It targets APP checkout `9e138e3a3e22ecf8c57cd5bf50beed571d107b54`; it is an unapplied candidate that depends on `document-search.patch`. The patch does not resolve the bundle-attached case or demonstrate an end-to-end running API; it deliberately refuses that combination. Dense retrieval remains subject to the existing pool flag, and this patch does not authorize changing it.

`test_request_optin.py` applies the patch to temporary copies and runs the resulting request model and REPL executor with mocked document processing and task execution. It checks default off, incompatible modes/bundle refusal, request-path guards for missing documents, streaming and script interception, and both enabled/disabled flag propagation. `PYTHONPATH=/mnt/raid0/llm/epyc-orchestrator /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest -q progress/evidence/repl-emb42-document-search/test_request_optin.py` passed 4 tests (one dependency deprecation warning). This proves the candidate seam only; it is not a deployed feature, API end-to-end validation, or retrieval quality result. GitNexus APP upstream impact: `ChatRequest` MEDIUM (44 symbols, 10 direct); `_execute_repl_body` LOW (one direct caller).
