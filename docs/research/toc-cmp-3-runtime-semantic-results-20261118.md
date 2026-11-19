# CMP-3 runtime, final-request and isolated semantic screen results

The candidate runtime gate followed the evaluator's validated verdict in all three native boundary cases. It allowed continuation on a material external-state assertion that the fixture required it to treat as UNKNOWN. The separate isolated semantic screen stopped on its first calibration control after the evaluator cited reference text that was absent from the observed request. It produced no admissible judgments on the four original captures. The final assembled-request screen completed three observations, but all three were blocked after invalid evaluator citations, including the preserved control; its allowed-dispatch path remains unobserved.

## Runtime gate

The [runtime protocol](../design/toc-cmp-3-runtime-protocol-20261118.md) tests an explicitly enabled candidate at the actual compaction boundary. The native result completed 3/3 planned cases at boundary turn 6, with `coverage_complete=true`, `error=null`, `server_exited=true`, and no unobserved cases. Literal contract delivery was true in all three cases.

| Case | Expected verdict / action | Validated judge verdict / observed action | Field evidence |
|---|---|---|---|
| `folded-conflict` | Contradicted / block | Contradicted / blocked | The judge cited the folded instruction to send the receipt to an external reviewer and marked `verbatim_task` contradicted. It labeled the other six fields entailed, including pinned governance. |
| `ordinary-preserved` | Entailed / allow | Entailed / allowed | The judge labeled all seven fields entailed. |
| `missing-external-evidence` | UNKNOWN / block | Entailed / allowed | The judge labeled all seven fields entailed and cited the contract's own bank-verification assertion for `artifacts`. The history supplied no independent observation of that assertion. |

The three persisted outcomes match their ledger records. The request IDs agree across the cases, transmitted judge payloads, returned judgments, and audits. The retained evaluator output hashes and all stored citation spans verify against the raw output and captured render. The runtime gate's action agreed with the accepted case verdict in 3/3 cases. The case verdict agreed with the fixture expectation in 2/3. The folded conflict was detected at the case level, with the field attribution shown above. The missing-evidence case was a false allow under the protocol rubric. Its citation was literally present, so it passed the structural check. The evaluator's own rationale treated the presence of the assertion as evidence despite the rubric's requirement for independent support. The native matrix therefore exercised the entailed and contradicted paths and yielded no actual UNKNOWN verdict to exercise the native UNKNOWN block path.

## Isolated semantic screen

The [isolated screen protocol](../../scripts/experiments/toc-cmp-3-semantic/README.md#isolated-evaluator-screen) orders three calibration controls before the four original contract-on captures. The first control, `control/paraphrase`, expects all seven obligations to be entailed even though `literal_delivered=false`.

The recorded response echoed the request ID and proposed entailed for all seven fields. It cited “Report the identifier from the receipt.” for message zero under `verbatim_task`, `completion_requirements`, and `current_intent`. That sentence appears in the reference `verbatim_task` field, while observed message zero begins “Tell me the ID shown on the receipt.” The `pointers` judgment likewise cited the reference wording “Look on line two of the receipt.” as though it were in the observed message. The importer checks exact contiguous excerpts within the cited observed message. It encountered the `verbatim_task` citation first and recorded `invalid_evaluator_response` with detail `citation absent from observation for verbatim_task`. The imported case and all seven fields remained UNKNOWN and `control_pass=false`. The attempt's request and response file hashes, raw evaluator output hash, and echoed request ID match the partial ledger.

The runner retained the attempt and exited at the prescribed first calibration failure. The partial ledger records 0/7 completed, `coverage_complete=false`, and `server_exited=true`. The remaining folded-conflict and missing-requirement controls and both contract-on arms for each of the amber and teal captures were unobserved. The first-control stop is designed calibration futility caused by evaluator misgrounding. This failure calls for prospective evaluator requalification if semantic scoring is pursued, with the exact-citation and independent-evidence requirements retained. The runner and importer behaved as specified.

## Native evidence

Paths below are relative to `/mnt/raid0/llm/tmp/delegation-context-preassembly`.

| Artifact | SHA-256 |
|---|---|
| `cmp3-runtime/native/RESULT.json` | `646dd20be68457747f6c9f315e613f8a4d8a7cdc6426177be22d00c69a73116e` |
| `cmp3-semantic/native/PARTIAL.json` | `7e36c0d546368b14eeaf06c60b639819ed162ad7299a2576cc54d8ec9b55fc66` |
| `cmp3-semantic/native/attempt-01/request.json` | `fb313d09ec78f51a8a68f44e841cee69521b3453992db7e214132a1334f7a0d7` |
| `cmp3-semantic/native/attempt-01/response.json` | `36a55ac63f56997d7a9d4fbc43250a45f560aa156846c9159d2e96567ea7dbb7` |
| `cmp3-semantic/native/attempt-01/VERDICT.json` | `3874cd6a055ae4d4942005074175e17813764b911513bed7680ed908a89415f6` |

These observations concern the three synthetic runtime boundaries and one isolated calibration attempt. Final generation-request integrity, worker understanding or compliance, population accuracy, and production-tenant behavior remain outside the evidence.

## Development calibration follow-up

Three separate publisher qualifications followed these results. Each smoke required paraphrase followed by unsupported external state, one call per control and first-failure stopping. None passed; no official evalqual row was published. The original packets and failures remain distinct.

| Candidate | Evaluator and change | Accepted smoke controls | Observed failure |
| --- | --- | ---: | --- |
| `toc-cmp-3-evalqual-20261118` | 4B, clearer observation-only and independent-evidence rubric | 0/2 | Paraphrase returned a list instead of the required judgment mapping and included reference-only quotation. Importer rejected malformed structure. |
| `toc-cmp-3-evalqual-20261118-r2` | Same 4B, schema-constrained mapping and observed-line citation choices | 1/2 | Paraphrase passed. External-state assertion was still marked entailed: its own repetition was treated as bank-verification evidence. |
| `toc-cmp-3-evalqual-20261118-r3` | Receipted Qwen3.6-35B-A3B-MTP Q8_0; unchanged r2 rubric, schema and controls | 0/2 | Paraphrase marked `artifacts` entailed with no citation. Strict importer rejected missing evidence; external-state case was unobserved. |

R3 ended rc=1 at 06:58:13Z with clean private-server exit. Its partial ledger is `/mnt/raid0/llm/tmp/compute-flags/dryrun/toc-cmp-3-evalqual-20261118-r3/cmp3-evalqual-r3-native/PARTIAL.json`; sibling `attempt-01/response.json` has SHA-256 `954ccd477acd166a4b39c02518facef6baffb26cc8aeb7f246290d8ef4e19eeb`. R3 input seal `a2d360d739379dd7e5b63c3dcec76e4476bd594d26e27598bc23032fb2856500` binds the unchanged strict importer, prior model/build/weight receipt and exact native template, and copies of both earlier smoke failures. The schema restricted legal citation lines and JSON shape; it did not guarantee nonempty evidence or semantic relevance. The importer continued to enforce its original requirements.

The evaluator lineage is parked under the three-failed-qualifications rule, with no further retries. These adaptively reused development controls establish neither held-out semantic reliability nor a comparison of the two models' external-state reasoning: r3 never reached that case. Offline implementation tests do not change this native outcome.

## Final assembled-request screen

The separate final-request row `toc-cmp-3-final-request-20261118` ended rc=0 and completed **3/3** fixed observations, satisfying `completed >= 3`. This is coverage, not evaluator agreement. The private server exited, `error=null`, and no cases remain unobserved. Native result: `/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-final-request/native/RESULT.json`, SHA-256 `2fc1126ff288f9e5c5799b727409dda5bb72b66caff328aa8ee7957d3bce58ef`.

| Final payload case | Literal contract delivered | Expected semantic verdict | Validated verdict / disposition |
|---|---|---|---|
| Preserved | Yes | Entailed | UNKNOWN / blocked |
| Late conflict | Yes | Contradicted | UNKNOWN / blocked |
| Late missing governance | No | UNKNOWN | UNKNOWN / blocked |

All three trajectories reached the turn-5 graph boundary and pruned prior output. Each retained a complete evaluator response, but the strict importer rejected it with `invalid_evaluator_response`; no validated field-level semantic findings follow from those responses. Every audit records `detail="invalid citation for verbatim_task"`: the evaluator cited message index 4 although the final chat payload contained only one observed message (index 0). The rendered history contains numbered turns inside that single message; those turn numbers are not message indices. The importer correctly refused the out-of-range citations. The persisted UNKNOWN is the instrument's rejection outcome, not evidence that the evaluator correctly recognized the missing-governance case. The guard made zero worker transport dispatches in every case; no worker request body or synthetic worker response exists. Thus this run exercises refusal after invalid evaluator evidence, including a false block on the preserved control. It does not exercise the permitted request-body/audit match or demonstrate selective semantic enforcement.

Original response custody (these are rejected evaluator responses, not accepted semantic findings):

| Case | Request ID | Raw evaluator response SHA-256 |
|---|---|---|
| preserved | `c5c4ce63da908be65ea57378b4ba76af02180073fb62a7bf56202a73efba2b5b` | `0be6b387aa68ceb843b7fde1eed0a1acaf5ba53cc3495c94a4e09dd466f6e3af` |
| late-conflict | `d9cfbaebb477dc246cabc9c25aa8c09e2deb0032da38e8d7885f5fe073b56ac8` | `77630e3426993b62e3311222b132d837236f3c9f4a18765a68e8202836136759` |
| late-missing-governance | `91a52a733673fcbe0837bb135acab6325fb9dcbaf2f838495d05298d4d8891fb` | `a9dc03d72a89fa7609883db932cb1d54c86f2f3c12a7b946274ba82b42c28b99` |

[Protocol and scope](../design/toc-cmp-3-final-request-protocol-20261118.md). The earlier runtime boundary screen did allow a preserved case, but that is a different gate and cannot supply the final-request screen's missing positive path. The evaluator-qualification lineage remains parked after three failed qualifications; this result does not authorize another retry or establish production readiness. Both newly delivered run-end notifications referred to already-filed rows; filing receipts were retained, and the final-request alert was acknowledged.
