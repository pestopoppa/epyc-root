# DCP-11 source wrap draft

- Candidate: `epyc-orchestrator` branch `codex/ni-dcp11-ast-render-ci-20261101`, commit `b7110ec02502113ba8f1554ca54153c734e44bd6` (base `0123e65a1af7cdd0e59c3ad37a62a43189aa1a92`).
- Scope: edit-site Python hits now retain verified AST segments, module imports, and enclosing class headers. The same finalized source ranges drive cost and rendering; ColGREP slices without a valid hash-bound plan fail closed into missing-evidence manifest entries. Full-file evidence remains available when it fits. Legacy direct-read slices keep their raw-slice behavior.
- Validation: hosted GitHub Actions run [41281631425](https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41281631425) succeeded. JUnit reports 298 passed, 0 failures, 0 errors, 0 skipped; pytest duration 14.43s. The runner source SHA manifest verified all included source and dependency-pin files against the candidate checkout. No local tests or production/runtime validation were performed.
- Evidence: see `custody.json` and the unchanged runner artifact files under `ni-code-contracts-41281631425-1/` in this directory. `custody.json` SHA-256 is recorded after write.
- State: candidate only; main review/promotion and any parent handoff update remain with the owning session.

## Final guarded-import follow-up

- Candidate: `ee471a4d3cd6c9a1f81fd3e560495dd1f35dbcd3`, parent is the retained green candidate `b7110ec02502113ba8f1554ca54153c734e44bd6`.
- Module-scope imports under `if` and `try`/`except` control blocks now travel with those blocks. The collector stops at function/class boundaries, so an unrelated local import stays excluded. The new test checks the assembled/routed slice against its token estimate.
- Hosted rerun [41282077353](https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41282077353) succeeded: 299 passed, 0 failures/errors/skips, exit 0, 13.68s. All 23 source-manifest hashes match the candidate Git objects. Original run 41281631425 remains in its own artifact directory unchanged.
- Follow-up runner artifact and custody manifest: `../ci-41282077353/`; custody SHA-256 `026c56da331495af6cf90daacf0923e2f65c7950a1c8dc70c09a9d66092adc61`.
- Candidate is still unpromoted, pending main acceptance.
