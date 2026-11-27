# When Skills Fail to Compose: Compatibility and Retention in Language Models

[Primary source](https://arxiv.org/abs/2611.34398v1) · intake-3017 · 2026-11-27

Frozen bases, known skill IDs/order, independently trained 20-row soft-prompt blocks. Table 1 matches diagnostic digit cases: one call 0.9–6.4%, sequential 88.2–100% across four bases; record edits 1.1–7.6% vs 99–100% across three, conditional on constituent proficiency. Two calls contain a parsed intermediate and additional work (49 vs 58 prompt tokens, 1.61–2.06× batched latency), so mechanism is not isolated. Internally logged neutral insertion training improves insertion robustness but does not remove interference; matched per-row norm controls show larger trained-partner harm on two Qwen bases, not the other two. Table 2 post hoc replacement by independently learned rows of same operations drops medians 98.0→12.7% and 95.3→0.5% despite every replacement ≥90% alone; held-out operations already score zero. Rehearsal preserves standalone skills on tested tasks with extra training examples; no equal-total-budget retention comparison, and held-out partner transfer on one 0.5B library remains limited (90.4% trained vs 10.4% held out, 5.7% unrepaired). Record editing text procedures with examples help some different-field pairs at 7B but all six order-dependent pairs still interfere; text and input information both changed. No common internal mechanism established and no agent skill router or executable skills tested.

Read §3–§8, Limitations, F.5–F.6 and G, selected figures/table cells. Remaining appendices and full intervention details not read.

## Evidence

- Digit one-call composition accuracy averaged 0.9% to 6.4% in this experiment. [§4.1 Table 1](https://arxiv.org/html/2611.34398v1)
- The post hoc partner replacement comparison drops to 12.7%/0.5% on these bases. [§5.3 Table 2](https://arxiv.org/html/2611.34398v1)
- Rehearsal retention comparison is not equal-total-supervision. [§6.1](https://arxiv.org/html/2611.34398v1)
- Executable or textual skill library implications need separate validation. [§7](https://arxiv.org/html/2611.34398v1)

## Scope and local transfer

Do not transfer numerical failure rates to text/code skills or claim separate calls dominate under equal computation. A standalone pass and rehearsal are distinct from interface compatibility and replay of prior uses. Treat two new seed replacements and single-library held-out repair as bounded evidence.

Harness/MemSkill admission replay: version ordered pair, prompt layout and explicit intermediate schema; compare each skill alone, selected ordered pairs (both directions where meaningful), old partner replay and unfamiliar partners with one-vs-two-call protocol. Capture exact task success, model calls, input/output tokens and latency with reader identity pinned. 9655 serial extra call carries another weight-pass/prefill tax, so test a smaller parser or exact intermediate artifact only with comparable quality. MI210 double call may fit small model with batching, but measure single-request tail and throughput under concurrency; paper’s H100 repair break-evens do not transfer.

Local skills are text/tool bundles, whereas the source trains continuous prompts. The existing null replay records single-task effects. Measure held-out pairs with component-only, combined single-call, explicit two-call and partner-shuffled arms; record step retention, token and tool cost by model. Keep soft-prefix findings separate from text-skill outcomes.

## Sources surfaced

- https://arxiv.org/abs/2605.04970 — Skill Neologisms primary counterpoint. Paper §4.1 and Appendix B.2 reproduce the protocol with strongly asymmetric per-order scores; compare pair-level vs pooled claims.
- https://github.com/YanLin-Quinne/SkillCompatibility — Reported companion, primary link currently returned 404. Re-probe for runnable per-pair fold artifacts.
- https://openreview.net/pdf/10d8c99a615e3bd422b1ab98b8852c469d89a5b2.pdf — Reasoning with Neologisms is a directly relevant empirical comparison, with access challenge on open. Search/discovery only.
