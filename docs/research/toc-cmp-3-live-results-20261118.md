# TOC-CMP-3 isolated REPL integration results · 2026-11-18

The official r3 run observed all six planned sessions. The captured turn-3 generation request contained the caller-supplied six-field brief and pinned governance verbatim in all four contract-on sessions. Both baseline requests lacked the contract, as configured. Both manifest requests described and located the omitted turn-1 source output. [Live protocol](../design/toc-cmp-3-live-protocol-20261118.md)

## Session ledger

The two tasks each used the same seed across the three arms. Rows are in run order. Prompt tokens refer to the captured post-boundary generation. Wall seconds cover the full trial and are rounded to two decimals.

| Task | Arm | Boundary | Contract delivered | Exact-match correct | Prompt tokens | Wall seconds |
|---|---|---|---|---|---:|---:|
| Amber ticket | Baseline summary only | Turn 3 | No | Yes | 3,138 | 307.01 |
| Amber ticket | Contract summary only | Turn 3 | Yes | Yes | 3,359 | 320.50 |
| Amber ticket | Contract verbatim manifest | Turn 3 | Yes | Yes | 3,573 | 375.32 |
| Teal ticket | Contract verbatim manifest | Turn 3 | Yes | Yes | 3,604 | 371.06 |
| Teal ticket | Contract summary only | Turn 3 | Yes | No | 3,324 | 383.72 |
| Teal ticket | Baseline summary only | Turn 3 | No | Yes | 3,105 | 295.81 |

All six generation responses completed with HTTP 200 and an SSE `[DONE]`. The teal contract-summary continuation completed on the wire, then the REPL recorded `NameError: name 'teal' is not defined` and terminal state `killed`. The trial had no successful exact completion. It remains observed for literal delivery and incorrect for task accuracy.

## Boundary evidence

- **Summary arms.** Each of the four sessions made one captured model-backed summary request at turn 3. The requests included the fixture marker in the history being folded and returned complete, nonempty HTTP 200 responses. The boundary event counted 353 summary tokens for each amber session and 320 for each teal session. The separate continuation generation identified turn 3 as its history boundary.
- **Manifest arm.** Both sessions made zero summary requests and recorded zero summary tokens. Each post-boundary request described three turn-1 spans in `session.verbatim.md`: code (34 characters at offset 31), output (3,046 amber or 3,044 teal characters at offset 74), and an empty error span. The omitted output contained the corresponding fixture marker. The recorded SHA-256 values matched the verbatim log slices at the declared offsets and lengths.

## Coverage and interpretation

The official run exited with `rc=0`. The native result records `completed=6`, `coverage_complete=true`, `server_exited=true`, `error=null`, and an empty `unobserved` list. The prespecified `completed >= 6` rule passes for coverage. The smoke runs are outside this ledger. [Coverage rule](../../scripts/experiments/toc-cmp-3-live/spec.json)

The evidence establishes literal preservation through the isolated REPL boundary and verifies the manifest's dropped-span references. Semantic entailment, governance compliance, live-hook enforcement, and production-tenant behavior remain untested. The original source remained accessible in REPL context, so exact-match answers serve as descriptive task outcomes and leave isolated recall and summary retention unmeasured. Each arm has two observations, making a single answer worth 50 percentage points. Accuracy and latency are descriptive for these sessions, with no population or efficacy inference. [Live protocol](../design/toc-cmp-3-live-protocol-20261118.md)

The native ledger is `/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-live-r3/native/RESULT.json`, file SHA-256 `6c566398cd6e36790c5f81bbd6b58e0321f3686869ddebafca27123aca4d6f08`. Its trial records link to the trajectories, wire captures, and verbatim logs. The captured request and response files for all reported summary and continuation calls match their recorded digests.
