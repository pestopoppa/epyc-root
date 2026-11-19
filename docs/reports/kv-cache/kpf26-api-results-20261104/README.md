# KPF-26 API full target diagnostics

Both original API rows completed rc0 and HTTP200 and satisfy their descriptive row rule: retain the two scout outcomes and slot-bound witnesses. The source dataset remains a prospective HS-19a-derived two-scout fixture; this is not historical traffic or a decision-grade performance/outcome gate.

| Arm | Native scouts completed | Required-term outcomes | Native fork tokens per child | Slot/task witnesses | Checkpoint witness |
|---|---:|---|---|---|---|
| OFF | 2/2 | true, false | 0, 0 | slot3/task3; slot2/task4 | absent |
| ON | 2/2 | true, true | 3555, 0 | slot2/task52; slot3/task50 | present, pinned n_tokens3555 |

Each request/response/manifest/trace hash was checked against the result; child summary hashes match raw trace text and the frozen required-term scorer. Raw trace flags independently record INDEX/FORK/LPM=0 or1 with max_skips1, while the result's top-level `flags` remains `unverified`: raw flag data is not universal semantic enablement proof. The ON record includes a captured checkpoint and one native child fork; the other child records zero fork tokens. OFF's false keyword outcome is retained, not converted into a diagnostic execution failure.

Both native scout reports show effective budget240s and complete two scouts without error. The code-diagnostic timeout failure does not make these API observations incomplete. Reuse these answered results; the prepared private600s/route1800s API packet is unsubmitted, future-only, and unnecessary for the original row rule. No API successor is requested. Parent KPF-26 correctness, real-workload, sampling, native belief canary and formal gate requirements remain separate and open.

`off/verdict-proposed.json` and `on/verdict-proposed.json` are scoped PASS proposals with no tick_text; the owning session files them. This agent did not file, tick or commit. Native log/slot files are losslessly compressed, other native files are retained as bytes, with original and stored SHA-256s.

Owner filing: both preserved proposed verdicts were reviewed and filed as scoped descriptive PASS through file_result.py. KPF-26 remains open, gate_pass stays null, and neither accuracy improvement nor performance benefit is established. The later API600 packet remains unsubmitted because these original runs already answered the descriptive question.
