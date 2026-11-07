# HarnessMM: Recursive Self-Improvement for Harness Token Efficiency

**Intake**: intake-2652 · **Verification**: dive-verified · **Read depth**: FULL · **Source**: https://arxiv.org/abs/2610.32813

## What the dive found

2026-11-06 Stage-2 dive (read_depth FULL; arXiv 2610.32813v1 is the only version, 37 pages read from disk; the Apache-2.0 code release at github.com/YuhuaJiang2002/HarnessMM HEAD 8c4ff0f9 was also read). The mechanism and every headline number reproduce, but the ATTRIBUTION does not: pricing the bypassed calls at the baseline per-call cost, callback removal explains at most 11.6% (HumanEval Codex), 17.5% (HumanEval DeepSeek), 14.3% (MBPP Codex) and 36.0% (MBPP DeepSeek) of the reported saving; the rest is per-call context shrink (tokens/call falls 26-72%). Output tokens RISE in both HumanEval arms (+18.3% DeepSeek, +48.2% Codex) and input accounts for 100.8% of the DeepSeek net saving, so the mechanism as measured removes prefill-side tokens and adds decode - the opposite of what a decode-bound gfx90a deployment would want. Stage-1 errors corrected: the AIME accuracy direction was inverted (87.14% is above No Skill's 86.96%); the cost-interval claim was inverted (the cost interval excludes zero, only correctness includes it); and two MBPP studies were conflated. The code release discloses what the paper does not: the HumanEval DeepSeek-harness actor is a self-hosted Qwen3.5-4B, and the admission path gates on an estimated >1024-token net saving, i.e. a token heuristic rather than a time heuristic.

## Claims and corrections

- claim 0: **unaffected** — Mechanism confirmed at p.4 Sections 4.1-4.3; guards are admitted only when their truth is known, otherwise the slow actor runs.

- claim 1: **unaffected** — Confirmed verbatim, including the six certificate fields and the Eq. 7 boundary check against the physical request ledger. Note the certificate proves omission, not correctness (p.16 D.2).

- claim 2: **overturned** — Stage 1 merged two different MBPP studies and inverted the interval statement. Table 3/4 (the repaired four-condition study) gives full 93.77% @13.17k vs W/o GDR 93.00% @18.03k; the reuse COST interval [4.01,45.57]% EXCLUDES zero while all CORRECTNESS intervals include it. The 95.33% @16.19k arm is 'W/o EDG execution' in Table 3, not Table 5. The single-use-beats-full reversal lives only in the earlier Table 5/6 study (91.44% @15.87k vs 90.27% @16.15k; delta +1.17pp [-3.11,+5.45], cost ratio 0.98 [0.81,1.22]) where nothing is resolvable at 257 tasks.

- claim 3: **unaffected** — The break-even/Substitution Paradox statement is read at Section 3.3 Eq. 3 and Appendix D.3 and is not disputed; D.3 also concedes CPU guard and tool work cannot be added to a token total without a defined resource conversion.

- claim 4: **unaffected** — MiniWoB++ RSI figures read at Appendix A Table 2 / Section 5.6; not disputed. Scope is 32 tasks, so it is a development-set result. NOTE (second-reader pass) - the mis-bound latency/energy anchor was removed; this claim currently has NO supporting anchor and must not be cited until re-anchored at p.8 section 5.6 / Appendix A Table 2.


## Anchors

intake-2652 carries 10 verbatim claim anchors; see `research/intake_index.yaml` for quotes, locators and hashes.


## Actionables

Stage-3 plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
