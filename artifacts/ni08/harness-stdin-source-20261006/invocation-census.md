# P7 OpenCode invocation census

Audit pin: ROOT recipe/source `e6aeaf10af69545945d8c8260c6253f8f7a34a41` (source implementation `79eeb5ea71f27937ffaa08cc9e707b12d7d36f15`). The worktree is private and clean. This is a manual source census; no OpenCode invocation or project runtime was run.

| Current prompt-producing source | Pinned source SHA-256 | Invocation template | Prompt provenance and argv/stdin behavior |
|---|---|---|---|
| `scripts/harness/hs4_p04_acceptance.py` | `31ecd73d4901f6570718af6c1e8930d36c960bd4181b4f57ac9df2605875774a` | `RUN_SH` lines 110–112 | `opencode run --format json --title hs4-p04-acceptance` has no positional prompt; stdin is `< "$EVID/prompt.txt"`. `prepare()` writes `TASK_PROMPT` to `evidence/prompt.txt` at line 248. The P7 synthetic test executes the generated script with a fake executable and checks exact Unicode stdin bytes/no prompt argv; native P7 selects that full module. |
| `scripts/harness/hs19a_acceptance.py` | `6e93460cd0069f04de051c7e89a678bbb99efd00abd11757541b287f14176ead` | `RUN_SH` lines 150–151 | `opencode run --format json --title hs19a-acceptance` has no positional prompt; stdin is `< "$EVID/prompt.txt"`. `prepare()` writes `TASK_PROMPT + "\n"` at line 255. Covered by the selected full module. |
| `scripts/harness/task_delegation_probe.py` | `65eb9376a7a82e96b12bc90114f309e9fc5d894c0c9ec35ca2e9ba1ec933d5fc` | `RUN_SH` lines 354–355 | `opencode run --format json --title {title}{agent_flag}` has only generated title/optional `--agent` arguments; stdin is `< "$EVID/prompt.txt"`. Prompt is written from `v["prompt"]` at line 411. `agent_flag` is empty or ` --agent {v['primary']}` at lines 429–430, never the prompt. Covered by the selected full module. |

Other current CLI commands in those sources are metadata/inspection only: `opencode --version` (hs4:104, hs19a:144, probe:342), `opencode export <session-id>` (hs4:121; hs19a:158,162; probe:362,366), and `opencode debug agent <agent-id>` (probe:348). None takes a user prompt. Probe title/agent formatting is covered above.

Scope checks at the same pin:

- `git grep -n 'opencode run'` finds only the three current production prompt-run templates listed above. Other matches are test assertions/fixtures, historical artifact records and docs (including `tests/harness/test_{hs4_p04_acceptance,hs19a_acceptance,task_delegation_probe}.py`, `artifacts/harness/hs19a-20260927/verdict.json`, `artifacts/harness/hs4-p04-20260926-r3/{opencode.jsonc,verdict.json}`, plus audits/docs). `scripts/system/opencode_event_reaper.sh` and `scripts/system/prune_agent_event_store.py` contain process-management references/comments, not prompt invocations.
- `scripts/hermes/` contains no `opencode` reference or invocation. It launches Hermes-specific commands.
- `.devcontainer/Dockerfile` installs pinned `opencode-ai@1.18.31`; it does not run it.
- `harness/opencode-plugin` sources/config define and lint the integration; they do not launch OpenCode. The P7 capture recipe runs Node's config linter and uses fake OpenCode binaries only in tests.
- No tracked `artifacts/**/run.sh` or historical shell output was edited. `evidence/run.sh` is generated at runtime by the three current harness producers; historical captured output remains immutable.

Pinned test sources: `tests/harness/test_hs4_p04_acceptance.py` SHA-256 `df1357d45876235c2e7b578bc6c06dd78921a62e238ff6481d11ac830afec42d`; `tests/harness/test_hs19a_acceptance.py` SHA-256 `f4ba61650634c7d7068a2a13967ba76f09d36bfd215d05268a3c31912a092767`; `tests/harness/test_task_delegation_probe.py` SHA-256 `12a6b0a4527d4a5e497c726bd351f17d086625406a997e2b9939089b90fad65d`. All three were selected in native run `37538484204` (attempt 1), which passed the 138 exact cases. This only establishes offline source/test conformance.
