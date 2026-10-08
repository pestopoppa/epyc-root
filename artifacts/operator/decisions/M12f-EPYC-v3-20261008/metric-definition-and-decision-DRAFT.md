# Proposed versioned EPYC CAS: human review required

This is a reviewable proposal, not an approved metric or measurement protocol. No source, historical report, protocol annex, native event, or grade has been changed. Frozen Research base: 3caaf22fa853daab5c5ae055ca46b67809e2c938. Existing v2 remains the default.

Primary source: https://ahstat.github.io/images/2025-llm1-iclr-paper.pdf Appendix B.3.3 (page 34); https://arxiv.org/html/2501.13121v1. The paper excludes fewer than two gold items from ordering analysis and conditions on fully matched retrieval. Kendall tau is higher-is-better. This proposal deliberately differs from that conditional paper metric: eligible incomplete retrieval contributes zero tau. It must be called an EPYC variant, never paper-equivalent.

## Exact proposed definition

Identifier `epyc_v3_gt_ge2_partial_zero`, scorer_version 3. Let C be the existing chronological question subset and L the existing latest-state subset. Gold count is the existing native `nb_gt`, without redefining gold or matching. E = {q in C: nb_gt(q) >= 2}. For q in E, use the existing native Kendall tau if native full coverage is true; otherwise use 0. Order leg O = sum(tau(q))/|E|. Latest leg F = sum(native F1(q))/|L|. CAS = (F + O)/2 only when both subsets are nonempty. Higher is better. No rescaling of tau, reweighting, or denominator substitution.

If E is empty, O and CAS are JSON null, status `undefined_no_eligible_ordering`; F remains separately visible. If L is empty, F and CAS are null, status `undefined_no_latest`; O remains visible. With both empty the no-eligible-ordering status has precedence. Markdown says undefined and composite suppressed. There is no zero-imputation of an empty leg or silent renormalization. Native raw C count remains present, plus explicit eligible/excluded-zero/excluded-single/eligible-partial counts. Every per-question result, SRS count and bin, chapter-set gold binding, latest F1, coverage check and native tau algorithm remains unchanged.

## Review alternatives

1. Recommended: approve this explicitly versioned EPYC variant after reviewing the exact two-file patch, tests and protocol admission separately. Preserves partial-retrieval penalties and exposes denominators.
2. Paper conditional-match variant: exclude partial retrieval from the order denominator too. Closer to paper but rewards selectivity; needs a different identifier and concrete patch.
3. Retain v2 only: no new metric, but short-gold rows remain in the existing composite.

## Admission and controls

Default API/CLI v2 path remains unchanged. Opt-in uses `--cas-definition epyc_v3_gt_ge2_partial_zero`. Unknown definitions are refused. Existing SRS comparison helper refuses mixed scorer versions. CLI refuses v3 with `--belief-measurements` before reading raw/gold or writing outputs: existing SC67 measurement admission is separate and is not authorized by this source proposal. The paired ROOT candidate concretely refuses every scorer version other than 2 and every CAS definition other than absent or v2_native at the direct-library boundary. Existing v2 summaries remain admitted. New-definition admission needs a separate human-reviewed protocol and source gate. No new ladder is proposed.

The exact patch changes only scorer and its existing test module. Tests cover default/explicit v2 equality, native per-question/SRS/gold preservation, cross-version refusal, short-gold exclusions, incomplete retrieval zero, no eligible or latest rows, denominator/coverage/numeric invalidity, and refusal before outputs/capture. They are prepared but have not been run. AST parsing is preparation only, not native validation.

## Prospective implementation and validation plan

After human metric trust approval and MAIN exact source-phase review: create a fresh owned Research worktree from the frozen base (re-check public ancestry and disjoint changes), materialize exactly the candidate two files, normal hooks and ordinary private commit. Before any validation event MAIN must prospectively enroll the source and definition; use the existing full scorer/comparison module native recipe with the new exact case inventory and whole import/readset closure. No inference. Retain original streams, case identities, native counts and output components. MAIN reviews original evidence before publication/promotion. No operation in this paragraph is authorized by PREP.

M12i v2 replay outputs and original June artifacts remain preserved. Do not recompute or rewrite them using v3; any later diagnostic comparison uses separately named owned outputs and the new version/denominator explicitly.
