# PFXC V6 required recipe hyperlink

V6 retains all V5 trace, exact-event, geometry and sizing checks. It adds an automated check of the original owner requirement: “Link artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json and preserve its bytes.” It requires a real hyperlink whose target, resolved from the document location, is the supplied canonical recipe with SHA-256 d3a3cf4f935a00dd9b020ea409f52a26caedfe3cf2325f636ae7c4edd5cf302b.

The existing project-declared markdown-it-py CommonMark parser4.0.0 resolves inline and reference-style links; standard HTMLParser recognizes HTML anchors. Vendored parser assets, mdurl0.1.2 and licenses are pinned in PARSER-PROVENANCE.json. The repository's existing inline-regex link extractor was considered but cannot preserve general reference-style links. No new Markdown link regex is used. Images, fenced examples and unused definitions do not satisfy a hyperlink requirement.

Run the complete checker package with `python3 -IB oracle.py LANE`; retain oracle.py, PARSER-PROVENANCE.json and vendor together. `replay.py` checks17 V5/V6 controls: accepted original main, actual broken GPU ON paid2, a corrected fixture, reference/collapsed/angle-title/HTML forms, two-column tables and colon-prefixed line references, plus external/case/local-target/missing/image/code/recipe-byte/event negatives. AST comparison proves every V5 function unchanged and the verify body changed only by adding the link check before its return. All controls pass and original source bytes/scores are unchanged.

Bound assessment receipts:

- paid-on-coding-assessment/REPORT.json: GPU ON paid2 V6 rc1, generic unresolved required recipe hyperlink; original raw rc1 retained.
- paid-off-recommended-assessment/REPORT.json: GPU OFF paid2 V6 rc0; original raw rc0 retained.
- cpu-numa-assessment/REPORT.json: CPU resource continuation V6 rc0; original raw rc0 retained. Its separate continuation provenance records native correction ordinal0 and neutral placement-restart help, not semantic guidance.

Structural passes still require independent semantic review. No model calls, native tests, source/index changes or commits were made here.

mechanical-followup contains only a prepared additional-feedback row, generic prompt, saved-state binding, owner/slot snapshot and unapproved template. Its id explicitly says post-review-mechanical-3. The original native cap2 outcome and final paid REJECT stay intact; it is not a new paid semantic-guidance round or a minimum-guidance claim. The worker prompt contains no corrected target and no final paid reviewer text. It preserves the saved provider1800-second config and requires an independent owner300-second lifetime/cancellation bound.

The prepared row may be dispatched through unchanged quality.run_row only under main's explicitly held GPU slot3 grant, or as a slot3 job before legacy MM ON in pilot_runtime's upcoming combined boundary. No standalone launcher or implicit grant extension is provided. A preparation snapshot reserves nothing: re-probe owner/controller/GPU birth and content identities, all existing PFX attempts and pending queues, plus idle slot3 at actual dispatch. Old coordinator pending does not cover an external callback. Per-row timeout cancellation must use an isolated worker stop event, never a shared coordinator stop that would cancel peers. Grant/server loss is partial interrupted work, not quality failure, and owned workers/containers must be confirmed stopped without stopping the shared GPU server.

After followup, retain the new attempt's costs and raw grader outcome, then V6-reassess the saved artifact. Prior accepted semantics can be reused only when the rest of the document is byte-identical apart from the required hyperlink target; otherwise source review is needed. The two-character corrected fixture is evaluator-only and must never enter worker inputs.

Next: main stages the two V6-passing independent reviews and chooses the concrete owner-managed executor for the separately counted mechanical exception.
