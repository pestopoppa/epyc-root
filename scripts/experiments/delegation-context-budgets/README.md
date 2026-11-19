# Per-operator delegation context budget candidate

The candidate selects input-component budgets by the existing operator identity
`(delegate_to, delegate_mode)`, before the specialist REPL is constructed.
It is pinned to orchestrator `de0f114415be7d5ffb5cb6cbd9a40032329c54ef`.
The patch contains only the source changes and their new regression tests;
[source identities and validation](../../../docs/research/delegation-context-budgets-candidate-20261118.json)
bind its bytes. No application checkout, deployment or production configuration
was changed. No native inference ran.

Set `ORCHESTRATOR_DELEGATION_CONTEXT_BUDGETS` to a JSON object, for example:

```json
{"worker_general":{"repl":{"context_chars":600,"discovery_budget":1000}}}
```

An absent policy or component uses the current global setting: the existing
`specialist_context_chars` cap and a discovery budget of 2000. The policy may
reduce either component down to zero, but cannot exceed either global limit.
Zero discovery budget skips assembly. Every entry is validated, including
entries for other roles/modes; malformed JSON, unknown fields/roles/modes,
booleans, fractional values, negative values and excess caps fail before the
specialist executes. Modes are the actual `react` and `repl` modes; OpenMLE's
improve/crossover/debug operators and their card counts have no direct mapping
to this path and are not copied into it.

The context cap retains the existing trim function, which can append a
three-character ellipsis. Discovery uses the packer's cost estimate, not a
hard tokenizer-enforced bound. These are component caps: question, brief,
corpus context, prompt framing, subsequent tool outputs and total prompt
length keep their existing behavior. In compact-specialist-prompt mode the
existing prompt builder does not consume `corpus_ctx`; configuring discovery
does not imply that its output reaches that prompt. No quality or latency
benefit is inferred from having a configurable cap.

The required offline-first baseline is
[the retained size audit](../../../docs/research/delegation-context-sizes-20261118.json).
Reproduce from the original trace with:

```bash
python3 -m scripts.research.delegation_context_sizes \
  /mnt/raid0/llm/tmp/inference_tap_events.jsonl --out /tmp/context-sizes.json
```

Question: what parent/child character sizes are observable by role before
changing allocation? This is a finite census of one historical capture,
with no sampling-error claim or effect-size inference. Stop after one pass;
malformed input stops the audit. The input SHA-256 and producer/pairer hashes
are in the output. The DCP-14 pairing rule groups by `parent_request_id` and
selects the latest earlier non-delegate prompt. Later-parent fallbacks,
truncated pairs and orphan worker calls stay separate. This grouping is a
descriptive heuristic, not proof that a particular parent caused a child.

Of 347 pairs, 61 have complete prompts and earlier parents; 230 later-parent
fallbacks and 56 truncated pairs are excluded from size summaries. There
are also 172 worker calls with no parent prompt. Included median captured
characters are:

| Parent → child | Pairs | Parent median | Child median |
|---|---:|---:|---:|
| architect_critic → worker_general | 20 | 780 | 491 |
| architect_general → worker_general | 22 | 780 | 715.5 |
| frontdoor → worker_general | 19 | 858 | 1704 |

The trace spans historical configurations and does not provide a reliable
operator/mode label. These counts cannot calibrate mode-specific caps,
establish token savings, or predict task quality. Defaults remain unchanged.

Validation: **88 application tests pass**, including 24 new controls, seven
existing DCP wiring tests and 57 existing delegation tests. The new controls
exercise both real specialist-loop modes with mocked model transport, verify
context trim and discovery forwarding, preserve question/brief, and reject
invalid policy before REPL construction. **Six root audit/adjacent tests pass**.
Ruff passes for changed application modules/new tests and new root modules;
patch reverse/forward applicability and whitespace checks pass. `make gates`
stops because `shellcheck` is absent, so full-gate acceptance is not claimed.

To review the candidate, create a detached worktree at the pinned commit,
apply `candidate.patch`, and run:

```bash
ORCHESTRATOR_MOCK_MODE=1 python -m pytest -q \
  tests/unit/test_delegation_context_budgets.py \
  tests/unit/test_dcp4_wiring.py tests/unit/test_chat_delegation.py
```

The original validation used the application's existing venv Python and
`/usr/lib/python3/dist-packages` for pytest 7.4.4; no packages were installed.
Production enablement, cap tuning, quality comparison and full application
integration remain outside this candidate's result. Belief source registration
is `VB-DELEGATION-CONTEXT-SIZES-WIRE`; only committed conclusions are eligible
for the existing observation carrier until its planning-context canary passes.
