# TOC-CMP-3 controlled artifact probe

Prepare before publication: `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B scripts/experiments/toc-cmp-3-probe/prepare.py`. This uses the orchestrator's installed dependencies for candidate rendering. It verifies the sealed CMP2 receipt and unchanged model file identity, without rehashing weights, applies the independent candidate diff to a detached scratch worktree, executes its real boundary and render for every fixture, and seals the renders, source base, diff and runtime in a new packet. Publish the resulting packet spec through rowflow. No inference is run during preparation.

Fixture turns are written through the candidate's real verbatim logger. Their logs are retained and sealed in the packet, so the omission manifest's character offsets and digests refer to actual source spans. The candidate worktree and packet remain under `/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3`; preparation refuses an existing packet or candidate to preserve prior custody. The grant reads frozen renders and verifies the candidate identity; it does not prepare fixtures or tokenize inputs.

The fixed design has 36 two-turn sessions, six rules by three arms by two counterbalanced orders, or 72 model requests. Arms are baseline summary_only, contract-on summary_only, and contract-on verbatim_manifest. The summarizer is a deterministic fixture deliberately omitting the rule, not a measurement of production compactor quality. The contract's own boundary and render inject governance; the model receives the frozen candidate output. Expected artifact effect: exact pin retention 12/12 in each contract arm and absence in baseline. Behavioral outcomes use CMP2 simulated-tool predicates; exact retention is only a ceiling, never compliance. One outcome changes an arm fraction by 1/12, or a rule fraction by 1/2; this is descriptive and supports no powered population or deployment claim.

Stop on answer after the fixed matrix. Stop on futility at the first infrastructure, protocol, or candidate identity failure, STOP, deadline or 2700 seconds; do not retry. Partial and unknown outcomes remain unknown. Smoke uses one sibling pair and requires verified private-server exit. `completed >= 36` is a coverage criterion, not an efficacy decision.

The contrast evaluates the brief and pinned governance as a combined package; it does not isolate their separate effects. There is no retrieval endpoint, so manifest-only retrieval benefit is not measured. No live-trajectory BAPS or Pass^3 claim is made. Literal exact-string W/X fixture classes do not establish semantic entailment.

CPU-grant repair (2026-11-18): the successor row id ends in `20261118-r2`,
and its scratch root has the suffix `-r2`. The job restricts itself and its
children to four distinct physical cores within the inherited grant; it
accepts either four threads or their eight-thread SMT expansion and keeps
four inference threads. Insufficient physical cores are refused. The
failed predecessors supply no behavioral evidence. See TOC-CMP-2r in the
[owning handoff](../../../handoffs/active/context-and-token-economy.md) for
preserved evidence, successor rows and qualification status.
