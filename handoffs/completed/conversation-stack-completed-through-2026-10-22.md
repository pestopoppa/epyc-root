# Conversation stack: completed scope through 2026-10-22

> Historical ledger only; current work lives in [`../active/conversation-stack.md`](../active/conversation-stack.md).

Moved verbatim from the active handoff by the 2026-10-22 operator wrap-up. Every task below was already `[x]`.

### Done this session (2026-09-24)

- [x] **CS-0a — audit the operator draft and ratify the vision.** ✅ 2026-09-24. Checked against the host, the code, prior research and primary sources, with four parallel read-only investigations. The operator settled D1–D12, recorded above.
- [x] **CS-0b — file this handoff as the one home for speech.** ✅ 2026-09-24. The operator draft is preserved with a correction banner. S-14 and the Qwen-Audio-3.0 watch moved from INF-41, and the stale Path-C boxes were superseded. A KVU-11b cross-reference was added. INF-79 row added; INF-41's Next action re-pointed.
- [x] **CS-0c — file the belief-kernel write side before any run.** ✅ 2026-09-24. A prospective row in `scripts/vidya/adapters/README.md` plus VB-SPEECH-CONV-1. Implementing it is CS-3.

## Newly executable Phase-3/4 source scopes — 2026-10-07

Phase3/4 implementation remains executable without a new speech model; real services, timing and model-quality acceptance remain separate. Existing CS-13 owns the design note.

- [x] **CS15-STORE-SOURCE — implement the session-keyed transcript and incremental-summary persistence source.** Existing session SQLite store and lifecycle, role/text/spoken_text/display/timestamps/turn IDs; retain/archive and fenced explicit delete. Summary callbacks receive prior compact state plus every unseen message; refuse overflow rather than silently lose history, keep exact monotonic frontier, preserve prior summary on failure, respect existing session lease fences. Full actual SQLite synthetic controls before integration through VB-CS15-STORE-CONFORMANCE. Voice-route and flag-gated `/v1` consumers remain separately executable CS-15 work; no live store/model or current voice acceptance. ✅ 2026-10-07 — [Source and original31/31](../../artifacts/ni08/cs15-conversation-store-source-20261007/README.md) accepted.
- [x] **CS-VOICE-CONTROLLER-SOURCE — implement mockable turn/controller/cascade interfaces for CS-20/21/23/26.** Inject actual service boundaries, healthy language-compatible selection/fallback, one active turn, session identity, bounded stream/refusal and dependency-ordered cancellation. Full synthetic service/queue controls through VB-CS-VOICE-CONTROLLER-CONFORMANCE. Source foundation only: concrete HTTP transport, streaming PCM, barge-in/client timing and real service acceptance remain separate implementation/evidence pieces. ✅ 2026-10-07 — same [source/native acceptance](../../artifacts/ni08/cs14-voice-stream-source-20261007/README.md).
- [x] **CS14-STREAM-SOURCE — thread request-scoped chunk and cancellation callbacks through the existing primitives/backend seams and add the thin voice SSE bridge.** Preserve existing direct-answer and `/v1` behavior unless real chunks exist; mock actual backend callbacks, async queue bridge, disconnect/deadline, per-turn/session isolation, truthful terminal/persistence behavior and no duplicate character replay. Native verification must be enrolled and reviewed before capture. Real first-token latency remains the separate CS-14 inference acceptance. ✅ 2026-10-07 — MAIN accepted [source and original276/276](../../artifacts/ni08/cs14-voice-stream-source-20261007/README.md).


## Prospective voice payload and explicit-choice controls — 2026-10-07

- [x] **CS16-SOURCE — implement explicit normal/verbatim response fields, display-only payload handling, and exact protected-value controls.** Default spoken/normal requests retain current chunk streaming. Explicit display requests return and persist a display payload without spoken text. Verbatim/protected-value requests buffer until exact protected strings are present; missing strings fail before client emission or assistant persistence. Verify with synthetic route and cascade controls. No semantic-quality, pronunciation/audio-fidelity, first-token, or live-service claim. ✅ 2026-10-07 — [MAIN accepted published source and original31/31](../../artifacts/ni08/cs16-18-success-acceptance-20261007/README.md); no live speech/timing warrant.
- [x] **CS18-SOURCE — expose a typed retain/cancel disposition for an active turn.** A caller supplies `RetainCancelChoice.RETAIN` or `.CANCEL`; retain leaves the stream active, cancel delegates to the existing ordered cancellation chain. Phrase interpretation (including “yeah, exactly” / “no, forget that”) is deliberately outside this source contract. Verify explicit choices, wrong/missing identity refusal, and ordered cancellation with fakes. No phrase-accuracy or live cancel-latency claim. ✅ 2026-10-07 — [MAIN accepted published source and original31/31](../../artifacts/ni08/cs16-18-success-acceptance-20261007/README.md); no live speech/timing warrant.

2026-10-07 MAIN source-reviewed the inactive-default concrete HTTP/WAV continuation at private APP `9c76824f549f45f22cf315e1fb3cb7f832558a13`, including actual MockTransport controller/cascade/CLI integration and bounded payload/cancellation/iterator release. VB-CS20-21-HTTP-CONFORMANCE is prospectively enrolled before hosted native capture. Source review is LOW; concrete native acceptance and CS-20/21 whole-parent real-service gates remain unchecked. No endpoint/server was contacted or reloaded.


## Bounded HTTP/WAV source acceptance — 2026-10-07

- [x] **CS20-21-HTTP-WAV-SOURCE — implement and verify the injected Whisper/SSE/Qwen clients and bounded WAV CLI without service/model execution.** ✅ 2026-10-07 — [MAIN exact source and original26/26 controls](../../artifacts/ni08/cs20-http-wav-success-acceptance-20261007/README.md), only3reviewed voice blobs on fresh APPcurrent-main source. This closes the bounded source slice; actual end-to-end services, audio quality/latency, routing and Annex S/runtime acceptance remain separate CS20/21 parent requirements.

