# HS-TD-2 native turn capture

Set `EPYC_TURN_CAPTURE_LOG` to an absolute JSONL sink path before starting
OpenCode with this plugin. Create its parent directory first. The capture is
off when this variable is absent; the shipped configuration does not enable it.
The opt-in sink contains native user text and tool evidence: select a private
directory. Newly created files use mode 0600; existing files retain their mode.

On `session.status: idle`, the plugin asynchronously reads at most 100 native
messages through `client.session.messages`, with a five-second abort signal.
It records the latest completed non-summary assistant message and the user
identified by its native `parentID`, retaining sibling tool messages from that
request. It never guesses a parent from proximity. Missing parents and native
turn errors have explicit statuses; payloads over 128 KiB become `oversize`
metadata records. No correctness label is inferred from handback.

Four reads may be pending, with no queue. Busy-session duplicate events are
ignored; excess reads warn and drop. Successful writes suppress duplicate final
message IDs in a bounded 256-session process-local cache. Restart, cache eviction,
sink errors and event races mean this is best-effort capture, not an exhaustive
session census. Downstream consumers must deduplicate by session/turn ID and
must not infer a complete denominator from this stream alone. The SDK message
limit bounds message count, not HTTP response bytes or individual part size.

The hook makes no model calls, holds no inference grant, and changes no answer,
permission or routing decision. This is a native input producer for the later
HS-TD-4-backed judge, not a replacement `decision_receipt.v1` implementation.
HS-TD-2 real-session cost/agreement acceptance remains open. Judge execution
requires a qualified row; a session capture alone is not measurement evidence.

API basis: `/mnt/raid0/llm/harness/opencode` commit
`350c726aa8b6b11eb9242040bc5eb7ae837fbf8a`,
`packages/plugin/src/index.ts` (`PluginInput.client`),
`packages/sdk/js/src/gen/sdk.gen.ts` (`Session.messages`) and
`packages/sdk/js/src/gen/types.gen.ts` (`AssistantMessage`, `SessionMessagesData`).
No upstream source has been copied into the lane.

Offline validation: `node --test harness/opencode-plugin/test/*.test.ts`.
Focused capture and hook tests use mocked native SDK reads and perform no inference.

The keeper-only consumer is now `scripts/harness/hs_td2_selfcheck.py`. It reads a
finite, prepared capture JSONL snapshot and calls the worker completions URL
supplied by its qualified row. It imports `src.typed_decisions.prepared_action`
from the explicit `--orchestrator-repo`; it does not reproduce the receipt API.
Its `hs_td2.selfcheck.v1` output embeds the original `decision_receipt.v1`,
capture fingerprint, producer/API file hashes, raw response, confidence and
extra-call elapsed time. Missing/error/oversize captures never enter inference;
malformed judgments and transport failures remain unknown. Changed inputs and
expired receipts cannot yield an accepted judgment. No action is executed.
The model alias is a request, not verified serving identity: `resolved_model`
stays null; the row must supply native worker/model/build/library custody.

Use `python3 scripts/harness/hs_td2_selfcheck.py --help` for arguments. Execution
requires `FILLER_ID`; the plugin does not invoke it. Inputs must be frozen and
validated before publication; duplicates or structurally invalid JSON stop the
snapshot, retaining earlier flushed outputs. Output creation is exclusive and
private (0600). A new output path is required for each attempt. Per-record
unknowns remain in the denominator; rows must retain partial attempts and the
prepared input count. The capture's best-effort coverage limits still apply.
This asynchronous post-turn shadow cannot measure pre-handback latency or gate
handback. No real-session acceptance or worker qualification is implied by its
mocked tests (`python3 -m pytest -q tests/harness/test_hs_td2_selfcheck.py`). Set
`EPYC_ORCHESTRATOR_REPO` for that suite when the sibling repo is elsewhere.
