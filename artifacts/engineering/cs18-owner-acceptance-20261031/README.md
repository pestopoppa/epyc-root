# CS-18 parent source acceptance — 2026-10-31

APP implementation `4639d190b957c2e594b89423cdc8afaed2a36048` fixes two demonstrated generation-boundary cancellation races. Retirement now resets the event while holding the admission lock; cancellation sets its signal and snapshots the response under that same lock. HTTP close remains outside it. Existing typed retain/cancel policy, Cascade forwarding and first-party request-disconnect cancellation continue through the existing `_cancel_only` path.

The source proof copied from that implementing commit pins source/test bytes and native logs: two expected original failures, two repaired controls, 45 affected controls passing on the native project Python 3.11, plus touched-file Ruff. The parent matched source/test hashes against the committed objects. These are software fixtures; no live endpoint, audio, microphone, latency, deployment or backend-persistence measurement is asserted. CS-19 and CS-23 remain open. Earlier typed controller work is historical; the new contribution is the demonstrated race repair.

The exact original checkbox words are preserved. Its first physical line names the implementing SHA, committed native test/proof and no-belief marker. This prepared owner patch is not a published tick until its normal ROOT checkpoint reaches main. [no-belief: source implementation and native regression controls]
