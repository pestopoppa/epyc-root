# 2026-10-24 — LRC-RI-EXTRACT-SOURCE publication wrap

## Outcome

Published the main-reviewed source change for `LRC-RI-EXTRACT-SOURCE` to `epyc-orchestrator` from an isolated integration candidate based on the then-current `origin/main` (`1f4c2bdb8632d9ac27657a784dcce68ee8cd6aa0`). The candidate contains only the three approved commits, cherry-picked in order, and preserves all upstream commits. Stable patch IDs match the source commits exactly:

| Source commit | Integrated commit | Patch ID |
|---|---|---|
| `79fcf1326b3c2d66ddde6c9f1fb055f4e9ad01c8` | `893c9628` | `18fa64eaff2963509a031572a7b9ce242d89de52` |
| `d350a8478d629d006975725c05157a22f9a1a4e8` | `5fea45b2` | `e0c5fd2639e6f3bf76dd4eaf3d9ba6e305b3f4ed` |
| `944486649c965e541642a0c9e839533f9f4a9887` | `503b9ffa` | `d38a7d62a018f0406397549fdb5e446e1440a4d5` |

The integrated branch `codex/ni-20261024-lrc-extract-source-integrated` was pushed. Its promotion merge `743bd71632e90d4d59f63f54c02a99d5a420e73f` is now `epyc-orchestrator origin/main`. Net diff from the integration base is exactly three paths: `scripts/graph_router/extract_training_data.py`, `tests/unit/test_graph_router_action_space.py`, and a one-line comment in `scripts/autopilot/species/structural_lab.py`. `git diff --check` passed. No tests were rerun during publication.

## Validation evidence

The reviewed validation pin is source commit `944486649c965e541642a0c9e839533f9f4a9887`, using the immutable launcher `/mnt/raid0/llm/tmp/learned-routing-controller/lrc-ri-extract-source-20261024/focused-tests-v3.sh` (SHA-256 `8111c6368a5723973b7f0638b2cfbbc2d763b891663f58463cad261a2e3c5163`). Its grant-backed run completed at 2026-10-24 14:35 UTC: 4 passed, 9 deselected, 4 warnings, 0.34 s, exit code 0. Captured output and status are `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/lrc-extract-v2/test.log` and `status.json`.

The extractor now uses the requested DB by default, chooses an NPZ only when explicitly requested, rejects a positive update threshold when the NPZ lacks captured counts, and reports DB candidate/included/excluded counts. Existing action/feature order and Q weights remain preserved. The FAISS fixture uses canonical action order and normalized `[1/32] * 1024` values. The earlier one-failure/three-pass run is retained in the audit; its fixture-order defect was fixed without a production behavior change.

This work is limited to offline extraction. No live-store mutation, re-embedding, training, model calls, routing enablement, API operation, reload, build or production change was performed. The test result verifies focused extraction behavior only; it is not a census of the full store or a data-quality claim.

## ROOT closeout

Main reviewed and approved the bounded two-path ROOT closeout on 2026-10-24. The handoff checkbox records only the completed extraction-source task; it does not claim training, live-store work or routing enablement. The isolated ROOT branch `codex/ni-20261024-lrc-extract-source-root-wrap` started from `8c15737d0f46d213b8ea05438f6f1b670da59b58` and was fast-forward-synced to fresh peer-published `origin/main` `0082dfb1e3125ec4cbe7379f1ec388b50315d8e7` before the wrap-up checks. The routing index's current next action remains EP-5 and does not need a row refresh for this task. No index row or source-table row was authored; no wiki compilation, pruning, archive or completed-handoff change was made.

The authorized bus drain reported that the coordinator daemon is unavailable (PID 3327121 absent); it also reported no routed messages or acknowledgements owed to this identity. This did not block the independent publication work.

## Wrap-up gates

- `python3 scripts/handoffs/index_state.py --check`: exit 0, 0 problems. The generated master rollup now reflects one fewer open item in routing-and-optimization; the live row's EP-5 next action is unchanged.
- The index check reported the existing warning that 138 active handoffs have no `**Scratch**` field; examples: `agent-file-prose-compression.md`, `agent-world-env-synthesis.md`, and `agentic-serving-harness-fixes.md`.
- The changed-document cite-check was clean (29 citations across two documents, 23 `ok`, 6 `record`). The full default cite-check also exited 0 over 4,592 citations in 220 documents: 2,964 `ok`, 1,377 `record`, 194 `review`, 23 `weak`, and 34 `unknown`; those unresolved entries are outside this task's changed claims.
- `python3 .claude/skills/project-wiki/scripts/check_readme_freshness.py`: exit 0 with no warnings.
