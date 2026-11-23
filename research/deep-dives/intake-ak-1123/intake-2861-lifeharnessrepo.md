# Dive — lifeharnessrepo — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/Tianshi-Xu/Life-Harness/main/README.md", retrieved: "2026-11-23", sha256: "9c781071f9ca"}
> SOURCE-QUARANTINE: {url: "https://github.com/Tianshi-Xu/Life-Harness @ 4844bbb09e78 (clone, reading material)", retrieved: "2026-11-23", sha256: "n/a"}

Bearing: intake-2858 ledger LH4 (runner needs, local improver, acceptance rule).

## 1. Stage-1 fields
Life-Harness V2 code release; Tianshi Xu, Huifeng Wen, Meng Li (arXiv 2605.22166); MIT, last push 2026-10-13. Categories: autonomous_research, agent_architecture, benchmark_methodology, tool_implementation. Novelty low; relevance medium. Credibility 1 = within 12 months +1. Verdict: adopt_patterns (fresh incumbent re-run, strict gate); LH4 needs a proxy (claim 1).

## 2. Key claims
0. **Runner. CONFIRMED.** `python -m evolution.reproduce --suite agentbench --method life --name NAME --launch` starts from empty H2-H5, runs six TRAIN rounds, seals, scores a fixed TEST; without `--launch` it prints the plan with no model calls. Anchors 0-1.
1. **"A local OpenAI-compatible improver is supported." OVERTURNED as shipped.** The proposer call is hardwired to `MR_HOST + "/protocol/openai/v1/chat/completions"` with `"model": "deepseek-v4-flash"` (`life_evolve/profile.py:984-987`; `ahe_native/connection.py:8-11`; the ALFWorld driver goes through a metering broker, `life_agentbench_run.py:217-233`). A stock llama-server serves `/v1/...` (uncited), so the no-edit route is a loopback proxy mapping `/protocol/openai/v1/*` to `/v1/*`. The improver must return `tool_calls` (requests carry `tools`) and integer `prompt_tokens`/`completion_tokens` (`life_optimizer/context.py:63-66`), and accounting needs three hash-pinned DeepSeek-V4-Flash tokenizer files (`context.py:12-20`). The generic runner has a `completion=` hook (`extensions/runner.py:87,119,178`); an ALFWorld adapter for it was not checked.
2. **Executor and environments. CONFIRMED.** Solver is local by design: `reproduction/reference/manifest.json` records `http://127.0.0.1:8400/v1/chat/completions`, qwen3-4b, temperature 0.0, max_tokens 4096, thinking off. Environments: native ALFWorld venv (ALFWorld 0.4.2, "not established as trajectory-equivalent to the old Docker stack"), AgentRL `controller-v0.2.0` binary on loopback 15020-15023, no-model `smoke_alfworld.py`. Anchor 2.
3. **Size. CONFIRMED (arithmetic mine).** ALFWorld: 6 disjoint TRAIN batches of 50, TEST 109 (`manifest.json`; `life_agentbench_run.py:78-82`); incumbent and candidate each run on the same batch: 100 episodes per round, 600 + 109 + 1 smoke = 710 solver episodes. Optimizer ceiling 10,000,000 tokens, 3 repairs (`profile.py:29`, driver :98). Wall time NOT-FOUND-IN-SOURCE.
4. **Acceptance rule. CONFIRMED.** `strict_improvement`, `life_evolve/profile.py:1413-1435`: exactly 50 unique task ids (:1416-1418), complete 0/1 outcomes, same keys, accept iff total successes strictly greater (:1435); ties reject. Called at `life_agentbench_run.py:256` after the incumbent is freshly re-run on the same batch (:245), unlike PluginRSI's cached parent. Generic runner: `extensions/runner.py:37-47,215`. One extra success in 50 accepts; a binomial standard error near 16.5% is about 5 points, so single-task acceptances can be luck. The setup smoke aborts on any infra error (:301-302).

## 3. Reported results
README repeats paper figures (+28.7 points vs Meta-Harness, +7.5 vs AHE, Qwen3-4B-Instruct, seven environments), labelled paper results. None new.

## 4. Performance-principles table
| Mechanism | MI210 | Zen 5 |
|---|---|---|
| 710 solver episodes, 4B-class, <=20 steps | YES: served role; time not in source | PARTIAL: bandwidth-bound (uncited) |
| Improver, 60k-token cap (v25 value; life_evolve value not read), tool calls | PARTIAL: needs a tool-capable served model | PARTIAL: slower |

## 5. In-house state
`harness-program.md` HIL-6j: 2026-10-22 decision lifts the loop deferment for the HIL-6 pilot only (L1727 @ d785b6d); LH4 keeps its operator-choice gate. No ALFWorld environment in the lane (agentbench AB1). Upstream-present: n/a.

## 6. Derived-actionables ledger
| # | Task | Owner | Compute | Rule |
|---|---|---|---|---|
| LH4a | Refines LH4: record that a local improver needs a `/protocol/openai/v1` to `/v1` loopback proxy (or a four-site patch before `initialize`), tool calls plus integer usage, the pinned Flash tokenizer, and 710 solver episodes. | `harness-program.md` HIL | doc-only | Done when LH4 carries these. |
| LH4b | No-model readiness: native ALFWorld smoke plus `reproduce` without `--launch`, on agentbench AB1's controller. | `eval-tower-program.md` | small CPU row | Does the native stack stand up without Docker? Done on pass or recorded failure. |
| LH4c | Improver conformance probe: replay one recorded proposer request through the proxy to the candidate improver; require `tool_calls` and integer usage. | `harness-program.md` HIL | one short inference row | Done on one valid response or recorded failure. |
| LH4d | DECLINE: DBBench, WebShop, TauBench, AHE, Meta-Harness arms. No ledger row consumes them; AHE needs privileged isolation and a paid gateway. | n/a | n/a | n/a |

## 7. Dive-surfaced sources
None change a row. Decline: `integrations/ahe-native` (AHE indexed per intake-2836).

## 8. Contradiction pass
README numbers are paper numbers; authors state six rounds do not mean equal tokens; optimizer model, host path hardwired; no independent replication.

## 9. Read depth
PARTIAL: README, ALFWorld driver, acceptance code, optimizer call sites, setup guide; solver agent, hooks, tau and AHE code not read; nothing run. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e.

## Anchors (verbatim substrings of page.txt, verified)
0. `--suite agentbench --method life --name life_agentbench --launch`
1. `Omit `--launch` to prepare the exact command plan without model calls.`
2. `| AgentBench common runtime | Core dependencies, AgentRL controller and native workers |`
Claim 1 also: `` `MR_HOST` is the prefix before `/protocol/openai/v1`. `` Claims 3-4 rest on repo code.

## 10. Artifact audit
artifact audit: clean
