# Voxtral traced-runtime restoration — 2026-11-19

CS-8.STT5: published `stt5-voxtral-traced-runtime-rebuild-r1-20261119`.
Publisher **SMOKE PASS** on CPUs 116–119 at 15:26:19Z: a fresh traced ELF
object satisfied the native witness predicate, followed by clean stop rc75.
The full build completed and its engineering gate was filed **PASS**. No audio or model was opened by this build.

The historical 480/960 ms executables and Q8 weights are absent at their pinned
paths. Original CrispASR source `2aa8d7669fcaa18d98d61a4bc8a077464e6b9919`
remains in the existing clean source worktree. The build reuses it read-only,
checks its commit/diff/untracked state plus the ggml/c2pa commits and clean
state, and pins the retained 480/960 ms trace backends and 960 ms model overlay.
Fresh smoke and grant build directories are separate. It compiles the trace
backends, builds the complete CPU CLI, substitutes the 960 ms model archive
into its library and executable links, checks all three native token witnesses,
and emits final executable/library SHA-256 identities. Unknown link arguments
refuse rather than silently falling back. STOP/deadline drains only the captured
compiler session using the existing independent-runner helper. The publisher's
new-session warning is accounted for: subprocesses inherit the full environment,
including FILLER_ID, and owned compiler sessions are explicitly drained.

Eight model-free restoration controls pass: exact linker replacement, compile
recipe flag/cwd preservation, ambiguous/missing/malformed recipe refusal,
submodule drift/dirty refusal, parent-pin failure propagation and compiled
witness presence. Shared owned-session drain regression checks also pass.

These will be NEW runtime identities, not restoration of the historical binary
hashes. Full build completion proves neither historical byte identity nor
public-fixture parity. Restore the original Q8 model by its recorded revision
and digest, then obtain public-JFK native-token parity before any validation
continuation. Keep the existing 10 results and 11 exposures, including one
exposed UNKNOWN, immutable; never redraw or relabel old receipts with new source
or runtime hashes. CS-8.STT5 remains open; no WER, rate, test or promotion verdict.

Evidence is referenced in place; no logs, source trees or binaries copied into
repository evidence directories. Prepared inputs and publisher receipt:

- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/config.json` SHA-256 `cbab09525f9fcc6501eb35aa107dfe2f0de910a6d5c8f5bc046bb129c6eec5b5`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/spec.json` SHA-256 `b073a2a2366d1b72d9e59be5b29d41e0566039dc2542ff05c5e9b61f8f1c860c`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/stt5_voxtral_restore.py` SHA-256 `283a4b912c891bda7e7d821277e899c4a058d02d32e55fc679af71b035608226`.
- `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/stt5_transcribe_restore.py` SHA-256 `f0c75857f6bc932d3dca737081ccb17f4f03e6bfe37d57ef80555f216f580d03`.
- `/mnt/raid0/llm/tmp/compute-flags/dryrun/stt5-voxtral-traced-runtime-rebuild-r1-20261119/PASS.json` SHA-256 `8602cce4f85272a19fb2ce238efdb863e0ac0290e93f9722dc8bfeb9b04d6134`.

## Filed build verdict

`stt5-voxtral-traced-runtime-rebuild-r1-20261119` ended rc0 complete at
2026-11-19T15:31:34Z. The non-smoke summary reports PASS after both traced ELF
executables linked. The executed driver checks source/submodule/overlay pins
before and after compilation and requires all three native witness strings
in each executable. Seven final artifact identities were emitted.

Summary: `/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/output/summary.json`,
SHA-256 `f175a7042338f28711fafe8dd3fc43da4321769ffb1a202436be6c8c560db3ce`.
Driver: `scripts/speech/stt5_voxtral_restore.py`, git blob
`fb1b65696699f090e4f0a2942316aadf61beb387`; its executed-file digest is retained
above. Source and configuration pins are unchanged.

Artifact paths below are relative to
`/mnt/raid0/llm/tmp/stt5/voxtral-restore-20261119/output/`:

| Artifact | SHA-256 |
|---|---|
| `build/ggml/src/libggml-base.so.0.26.0` | `785ac1a64ad2634d22f7eb3f2376e668d888ff7b1ab1cb4ce117207123db2465` |
| `build/ggml/src/libggml-cpu.so.0.26.0` | `aa026c53ed41fb7aee5d55b13cb25ce2f53ce99212047d8cd85a94382ad7baee` |
| `build/ggml/src/libggml.so.0.26.0` | `0357bb10d7478f5ad55c92fb47462e6d98d94162233ed0dc9b3c24c065aa4bd2` |
| `build/src/libcrispasr.so.0.8.44` | `6dd21bc0b00255b41e486b1b2efa2338325abae411ee087685b6986126ac69b4` |
| `voxtral480/crispasr` | `7b83e261521eb56061b43f779edeb9936d7db606ff34d765f2655753c3a87122` |
| `voxtral960/crispasr` | `ed8d369c5fd91a3c628f5dbca53775ec89b28a0dad6551f55d280df9e49b6449` |
| `voxtral960/libcrispasr.so.0.8.44` | `0edf71d3067d4ac2c10577bfec277957a1d407f40fb7be52913c905b51a3dd90` |

This verdict answers build completion only. Historical byte identity and public
native-token parity remain false/unestablished in the summary; validation was
not exposed. No WER, rate, accuracy or promotion claim follows. Existing ten
results and eleven exposures, including the exposed UNKNOWN, remain unchanged.
The original Q8-weight restoration event has not landed. Next: consume that
registered result, then publish the 480/960 ms public-JFK parity row bound to
these final runtime hashes, original weight digest and retained token witnesses
using `scripts/speech/stt5_voxtral_tokens.py`. Never redraw validation exposures.
CS-8.STT5 stays open. Existing conversation-stack source enrollment and the
committed-conclusion carrier apply; no retrospective measurement warrant.
