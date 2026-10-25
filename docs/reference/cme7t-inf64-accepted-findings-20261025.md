# Accepted T1 desk audits — CME-7T and INF-64 — 2026-10-25

Prepared against canonical epyc-root ROOT 249855e78d54bdcf9b2e1e255ff02a7072207749, research e8d57acd4cac73005b56f9b6906d8707552e4727, and orchestrator 49c1f749014d5290367413f2898d4e37e2bd1016. Scope is two accepted T1 investigation tasks. This durable record preserves MAIN-accepted desk conclusions; it records conclusions and source locators, not measurement attestations, deployed fixes, live runtime state, or belief-register ingestion.

## CME-7T — diagnosis and intervention choice

CME-7S completed PASS at 2026-10-23T00:40:04Z. The retained run's raw reply file is SHA-256 a9b5ee5a7495bde9ace34746318fb51f55b70dfedd5c000a04c66a4623dd3ef6. It contains one unique 2048-token runaway response, chatcmpl-6U1HOEz9UlHrOTaX4BK3gy6b51aAO5fs, exactly joined to the reset-each-instance baseline's first interaction. The second raw record is a parse-failure for that same response, not another attempt. The response is not from stateful run 0, run 1, or run 2; those first replies used 1052, 110, and 1846 output tokens and were valid. The duplicate baseline trace views are likewise one event.

The response emitted 6297 characters of visible JSON thinking, never reached action, ended with finish_reason=length at 2048 completion tokens, and had reasoning_content=null. The unfinished string repeatedly revisits pot/blind/limp interpretation. The schema requests unbounded reasoning before action, while the prompt describes a posted big blind as an opponent having “called your bet”; this is a plausible trigger for reconsideration, not isolated causal proof. The evidence does not show failure of enable_thinking=false, nor recover the missing rejected text from the older 2026-10-22 events.

Decision: retain the 2048-token cap and current penalties; recommend a separately granted candidate with a bounded rationale instruction. Exact candidate wording and option tradeoffs remain in the task-local CME findings at /mnt/raid0/llm/tmp/codex-ni-20261025-cme7t-diagnosis/FINDINGS.md. Efficacy is untested. No source change, inference, fix, quality gain, or explanation of every historical event is claimed. The retained server receipt identifies build 10345 / dd3d9721c; immutable launch-time model and binary digests are absent.

## INF-64 — current-pin conservative re-screen

At the three verified local Git pins, all 19 historically named modules remain present and match the accepted per-file matrix. Review found 12 with positive source, CLI, dynamic-dispatch, or consumer edges and 7 intentional off-path contracts whose current runtime invocation is not established. Result: 19 retained, 0 proven obsolete, 0 proposed deletions. This completes the requested individual screen; zero deletions is a valid outcome, not an incomplete count.

The 7 off-path dispositions preserve explicitly named contracts; they are not claims of runtime use. The report distinguishes direct imports, dynamic strings/factories, documented CLIs, tests/data/guards, and bounded negative searches. It makes no runtime absence, GitNexus clearance, test-pass, inference, or deletion-safety claim. Source changes and publication remain outside this desk task.

Exact supporting source/test/data inventories and the full module-by-module rationale remain in /mnt/raid0/llm/tmp/codex-ni-20261025-inf64-rescreen/INF-64-REPORT.md, with file digests listed below.

## Belief-capture boundary

These are committed conclusions only after main files them. No native measurement tuple or historical run warrant is inferred. Main should use the existing committed-conclusions pilot VB-CC-PILOT for the CME-7T conclusion, preserving the raw response hash and response-ID join as locators while leaving protocol_id empty and making no efficacy claim. For INF-64, extend the existing VB-INF64-REACHABILITY-CONFORMANCE source evidence with the exact report and readset; do not invent source-class adapters, grading ladders, or historical tuples. Until the existing register accepts the committed conclusion, completion ticks should carry an explicit [no-belief: committed conclusion prepared; register capture not yet applied] marker.

## Input custody

| Input | SHA-256 |
|---|---|
| CME-7T FINDINGS.md | 1c48af9dc3d4637cc4b342e4dd335208b5544f578a6ab10979191a8767f0b8de |
| INF-64-REPORT.md | 94ad54ced756508606eb508a48dec964e2b1e480154870a400973a6efee2073c |
| INF-64 module-blobs.tsv (19 modules) | 80099f4627193eed83b4cf3ea011a25382e71091d0a1ac3d3cbed233fe5b470e |
| INF-64 paired-test-blobs.tsv | b93a61cf6380bd0a8004825014d3d71fa775c5dec5b369c1850c5a36a62d41c9 |
| INF-64 guard-data-blobs.tsv | 4c241624993b259ec07e36590b50432dd8a70a0351c150dd2dcec84b8b34e943 |
| INF-64 dynamic-dispatch-references.txt | 4665e58581d3aa7234bf838dcb0e26f4bb50dc4927cddfeae11fd694eb2e3c34 |

Task-local accepted markers were present but zero-byte (SHA-256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 each); acceptance authority is the parent-provided accepted task IDs CME-7T ead9a9fe and INF-64 4e565a7e, with owner notified.

## Original desk method and limits

Native git show, git grep, cat, sed, and sha256sum reads only. No interpreters, GitNexus, tests, network, launcher execution, shared-tree writes, task arming, push, or inference. No exact-anchor conflict was found in the canonical task/source anchors inspected. The durable destination and repository application are owned by main.

## Exact retry and proposed instruction

The successful retry of baseline response `chatcmpl-6U1HOEz9UlHrOTaX4BK3gy6b51aAO5fs` was `chatcmpl-676TFzWZubuoELFAuZ2IG7WmhEgghj5d`, 2608 input / 150 output tokens, 453 cached input tokens. This changed context and does not establish instruction efficacy. A future separately granted candidate may use the existing configurable system_prompt:

> Return only the requested JSON object. Keep every free-text reasoning or thinking field to at most two short sentences and 60 words. Choose the action using the supplied state and legal options; do not repeatedly reinterpret the state or invent alternative histories. Complete all required fields and close the JSON object.

- [ ] Expose the existing configurable system_prompt as an explicit opt-in wrapper parameter if the official wrapper is used; verify parsing with fake transport, then request a separate model window binding exact prompt/hash and launch identities. Retain 2048 cap/current penalties initially; measure unique baseline/stateful schema failures and usage separately before accepting any remedy. This candidate is untested.

## Durable source custody

The accompanying `artifacts/cme7t-inf64-accepted-20261025/` directory preserves the original accepted CME findings, INF64 report and all five matrix/control reference inventories, plus exact acceptance notices. These original worker reports retain their proposal-time wording; this document records MAIN acceptance ead9a9fe and 4e565a7e. No register ingestion is asserted. These conclusions use explicit no-belief reasons until the existing committed-conclusion capture actually runs.
