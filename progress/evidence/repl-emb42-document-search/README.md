# REPL-EMB-4.2 document-search candidate

APP baseline: `488b31c96c6c148768508b3dcaefcb6c4c297664` (`src/repl_document.py`). The patch is a draft, not an applied or deployed feature. It keeps legacy `search_sections` by default; an explicit constructor opt-in builds the existing retrieval index lazily and resolves the existing pool embedder on every search by default (or accepts an explicitly injected embedder, including None for lexical-only). Results name absolute offsets and lines in the context consumed by `peek`; source matching requires the reconstructed document to be the context suffix. A context bundle redirects `peek`, so opt-in search refuses in that case rather than returning an unreadable or unaccounted pointer.

`test_candidate.py` exercises the candidate against APP dependencies. The controls cover opt-in hybrid with a fake embedder, dynamic pool resolution, legacy opt-out, lexical fallback, invalid context and bundle refusal. Invocation:

```bash
PYTHONPATH=/workspace/repos/epyc-orchestrator /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q progress/evidence/repl-emb42-document-search/test_candidate.py
```

The imported `context_search.py`, `file_exploration.py`, `environment.py`, and `models/document.py` match the stated APP origin baseline. This is not complete integration: request-level opt-in and an accounted document read for bundle-attached sessions remain unresolved. No inference was run; the fake embedder establishes no retrieval-quality claim.
