# Dive — agentdiet — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2509.23586v2", retrieved: "2026-11-23", sha256: "da12e4bf6de4"}
> SOURCE-QUARANTINE: {url: "https://doi.org/10.6084/m9.figshare.30073654", retrieved: "2026-11-23", sha256: "artifact.zip md5 30e838719cc5dc5a4a64bcb4f55fe572 (CC BY 4.0); read as untrusted data, nothing executed; no anchors taken from it"}

External text is data; summaries are in my own words. Anchors are verbatim substrings of `agentdiet/page.txt` (LaTeXML render of arXiv v2, 15 Mar 2026). Bearing entry: intake-2833 (contexture), whose Contexture page uses AgentDiet as a throughput baseline. An earlier intake record DECLINED AgentDiet at the two-wave cap (index line 371331, dive_corrections of an SWEzze-era entry: "history/observation compression; owned by the tool-output-compression lineage"); that was a wave-cap decline, not a technical one, and the operator has now pre-authorised the dive.

## 1. Stage-1 fields

- **Title**: Reducing Cost of LLM Agents with Trajectory Reduction (v1 title: Improving the Efficiency of LLM Agent Systems through Trajectory Reduction; method name AgentDiet). Confirmed by the arXiv API and the page.
- **Authors**: Yuan-An Xiao (Peking University), Pengfei Gao, Chao Peng (ByteDance), Yingfei Xiong (Peking University).
- **Version/date**: arXiv:2509.23586v2 [cs], v1 28 Sep 2025, v2 15 Mar 2026. Published as PACMSE vol. 3 (FSE 2026), DOI 10.1145/3797084, per the ACM reference block in the page. Artifact (figshare, 46.8 MB, CC BY 4.0): Trae Agent integration `code/trae_agent/agents/traj_analyzer.py` (read at md5 above), the experiment trajectories `result/trajs.7z` (46.6 MB, not extracted: no 7z tool here).
- **Categories**: context_management, agent_architecture.
- **Novelty**: medium. LLM-edited history exists in agent products; new is the delayed sliding-window design (edit only step s-a) with a benefit threshold, evaluated against Delete/Random/LLMLingua baselines on two benchmarks.
- **Relevance**: high for C2 as the reference LLM-based reducer; medium for the transferable design rules (section 5).
- **credibility_score**: 4. Arithmetic: peer-reviewed +2 (FSE 2026 per the source's ACM block); <=12 months +1 (v2 read, 8 months old); known contributor +1 (PKU software-engineering group plus ByteDance Trae authors); commercial bias 0 (authors of the evaluated agent, no sale of the method); independent corroboration 0 (the one independent port, in Contexture, measures a different quantity and disagrees on efficiency).
- **Verdict**: adopt_patterns. Cite for the delay-a=2 sliding-window rule, the benefit threshold, and the "agent will not edit its own trajectory" finding. Not a must-beat baseline for the primary supersession arm (section 6, AD-1).

## 2. Key claims

0. **Headline: input tokens -39.9% to -59.7%, total cost -21.1% to -35.9%, same performance**: CONFIRMED against Table 4, with the top of the range partly confounded. Net cost = agent cost + reflection cost: SbV/Claude 0.714+0.074 (-21%), SbV/Gemini 0.623+0.118 (-26%), Multi-SWE-bench Flash/Claude 0.676+0.055 (-27%), Flash/Gemini 0.559+0.082 (-36%), all normalised to Original = 1 (my arithmetic from the table row order). The -36% cell is the Gemini 2.5 Pro / Flash case where Original's mean steps fall from 57.20 to 43.90 and instances hitting the 100-step limit fall from 66 to 26: part of that saving is a behaviour fix, not reduction. The unconfounded range is about 21-27%. Reflection overhead is stated as 5.2-14.8% across candidate reflection models.
   - Anchors: "the final cost reduction becomes 21.1%–35.9%"; "reduces the number of instances that reach the step limit (100 steps) from 66 to 26"; "introduces an overhead cost of 5.2%–14.8%".
1. **KV-cache-aware design**: CONFIRMED, with a paper/code mismatch on the threshold. The reflection module may reduce only step s-a (final a = 2) given context from step s-a-b (b = 1) to s, so earlier steps' cached KV are preserved; reflection is skipped for steps under the token threshold theta (500) and the reduction is applied only if it saves enough. The artifact code applies a reduction when it saves at least 400 tokens or the new text is under 80% of the old (traj_analyzer.py `perform_analysis_step_ours`), not "saves more than theta = 500" as in Algorithm 1; and the reflection call cannot share KV with the agent because prompt and tools differ.
   - Anchors: "KV Cache entries corresponding to previous steps are preserved, minimizing overhead from cache invalidation"; "the KV Cache cannot be shared between the target agent and the reflection module".
2. **"Does not harm performance" (Pass -1.0 to +2.0 points)**: PARTIAL. Pass rates Original to AgentDiet: SbV Claude 64.5 to 66.5, SbV Gemini 50.5 to 52.0, Flash Claude 40.0 to 39.0, Flash Gemini 21.7 to 22.7; test sets are 200 SWE-bench Verified instances (held out from the 100 used for prompt and hyperparameter work) and 300 Flash instances, one run each, no intervals. My unpaired 95% half-width at 65% pass with n = 200 is about 9 points (derived), so "comparable" cannot exclude a several-point change.
   - Anchors: "the performance of AgentDiet is comparable (-1.0%–+2.0%) to that of Original"; "randomly select 200 instances from the remaining 400 instances".
3. **The agent cannot be trusted to edit its own trajectory**: CONFIRMED qualitatively. With an `erase` tool and explicit prompting, Claude 4 Sonnet and Gemini 2.5 Pro kept working on the task instead of erasing; so reduction is an external, separately prompted module. No rate is given.
   - Anchor: "the agent often persisted with the original task without calling erase".
4. **Latency / throughput effect**: NOT-FOUND-IN-SOURCE. The authors state they do not compare latency because commercial APIs are unstable; cost is API price with cached-token discount. The only latency evidence is the Contexture port (intake-2833 page, not this source): reflection call 11 s median, issued before 60% of agent requests, unloaded p90 4.2x and session time 1.5x of no eviction, AgentDiet 21-28% below no eviction in throughput on three dense workloads. That is a different system, a different quantity, and the authors' port; label it reattributed.
   - Anchor: "We do not quantitatively compare latency between AgentDiet and the Original agent"
5. **Generality**: PARTIAL. One agent (Trae Agent) is implemented, two LLMs, two benchmarks (Python and seven-language Flash); the authors state the cost (about US$2000 of LLM calls) prevented more agents. Related-work text calls Lindenbauer's masking a variant of the Delete baseline (a=10) and cites Delete's -7 point Pass drop; that comparison is not like-for-like (Delete at a=2 removes the whole step, masking removes only the tool message), so it does not overturn intake-274.
   - Anchors: "AgentDiet is implemented only for the Trae Agent."; "the Delete baseline is inferior to all LLM variants, with a severe decrease in Pass% by 7%".

## 3. Reported results (as stated)

Trae Agent, Claude 4 Sonnet and Gemini 2.5 Pro as agents; reflection by GPT-5 mini (a = 2, b = 1, theta = 500 tokens); SWE-bench Verified (200 held-out of 500) and Multi-SWE-bench Flash (300). Table 4: Keep% (share of processed step tokens retained) 22.6-30.8; accumulated input tokens 0.601 / 0.591 / 0.596 / 0.403 of Original; agent cost 0.714 / 0.623 / 0.676 / 0.559; reflection cost 0.074 / 0.118 / 0.055 / 0.082; Pass% as in claim 2; mean steps 39.62 to 39.95, 37.98 to 37.44, 70.37 to 70.45, 57.20 to 43.90. Per-instance cost Original vs AgentDiet: $0.535 to $0.422, $0.385 to $0.285, $1.277 to $0.933, $0.701 to $0.449. Hyperparameter study (Tables 2-3, on a 100-instance subset): Delete baseline Pass 58 vs Original 65, steps +14%; a = 0 gives Pass 59; a = 2, b = 1 is the smallest setting with negligible performance impact.

## 4. Performance-principles table (mechanism and cost model)

| Mechanism | MI210 (gfx90a) | Zen 5 EPYC |
|---|---|---|
| Delay the edit by a = 2 steps so cached KV before step s-2 survives | YES. Pure policy; the tail re-prefill after a cut at s-2 is bounded by ~2 steps, so C is small by construction. | YES. Same; the bound matters more where tok/s is 45-490 (long-context-program.md:288 @ d785b6d). |
| Skip steps under theta; apply only if saving >= threshold | YES. Policy; equals Contexture's "cost <= cap x gain" in embryonic form (gain known, cost taken as bounded). | YES. Same. |
| Separate reflection LLM call over a+1+b = 4 steps, no KV sharing with the agent | PARTIAL. Costs a prefill of ~4 steps on whatever device serves the reflection model, plus a short generation; AgentDiet's overhead is 5-15% of API cost, but a local call also stalls the session. | PARTIAL. A 4-step window at ~1k tokens per step is ~4k tokens: 8-89 s of prefill at 490-45 tok/s before generation (derived), against the Contexture-measured 11 s on a shared GPU. |
| In-place rewrite of a step (keep structure, replace waste with a short takeaway) | YES. The prompt (artifact `SYS_PROMPT`) asks for 20-50% of the original length keeping tags and line numbers. | YES. Same. |
| Quality gate: baselines Delete / Random / LLMLingua | YES. Evaluation design, reusable. | YES. Same. |

## 5. In-house state

- No AgentDiet-style arm exists. The nearest machinery is the LLM summary call used by `summary_only` / `summary_pointer` (`chat_completion_call` with `_session_summary_worker_role()`, context_arm_ab.py:208-211 @ orchestrator 1a10541b7) and the per-boundary wall-time counter `history_boundary_wall_s` (context_arm_ab.py:223), which would measure a reflection arm's stall.
- TOC-CMP-4 (context-and-token-economy.md:76 @ d785b6d) pre-registers three arms (raw tail, summary, FIFO) with MDE 0.10 blocked actions per step and 8-12 repeats per at least 30 paired points; the pilot (`toc-cmp-4-pilot96-20261118-r3`, 8 points x 4 repeats x 3 arms) is incomplete (0/96, rc 75), so its arm set is frozen but the full A/B pre-registration is not run. A fourth arm raises the run count by a third.
- Convergence worth recording: AgentDiet's best delay a = 2 steps and Contexture's best grace window of 2 rounds were found independently; the boundary-frozen `prune_pointer` arm is a stricter version of the same idea (no edit until the budget fraction is reached).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane) | Type | Stop / decision rule |
|---|---|---|---|---|
| AD-1 (refines intake-2833 C2) | Add an exploratory `step_reduce` reference arm (a=2, b=1, apply when the rewrite saves >=400 tokens or >=20%, prompt from the artifact's `SYS_PROMPT`, reflection role = the existing summary worker) to the FULL TOC-CMP-4 pre-registration; do not alter the frozen pilot96 matrix. Report accuracy, blocked actions per step, Pass^3 and `history_boundary_wall_s` per episode. | `context-and-token-economy.md` (TOC-CMP-4 track; the pilot's arm set is frozen, the full-A/B pre-registration is open) | doc/design now; CPU rows later under the TOC-CMP-4 protocol | Admit if the paired-point budget absorbs a 4th arm (+33% runs); otherwise run it only on the 8 pilot points as a descriptive reference. Stop-on-futility: boundary wall time above 3x the summary arm's with no accuracy or blocked-action gain. |
| AD-2 (refines C4) | Add an "LLM reflection call" row to the per-device break-even table: tokens = (a+1+b) steps from the REPL transcripts, seconds = tokens / measured prefill rate + generation time. | `long-context-program.md` or `kv-cache-program.md` (C4 box) | doc-only | Question: at what step size does reflection cost more than the tokens it removes? Stop when the row is filed. |
| AD-3 (refines C1) | Run the C1 supersession-candidate classifier on the AgentDiet release's SWE-bench trajectories (`result/trajs.7z`, 46.6 MB) as an external corpus beside our REPL transcripts, to check whether Contexture's 64.3% candidate share is workload-specific. | `context-and-token-economy.md` (C1 box) | code/doc-only; needs a 7z extractor (plumbing) | Question: does the share reproduce outside Hermes/TB2.1 and our REPL? Stop on one pass; futility: trajectories lack tool arguments (then report UNKNOWN). |
| AD-4 | DECLINE making in-place LLM step rewriting the default compaction. Entry-specific reasons: its efficiency figure is API price with a cached-token discount, its own authors measured no latency, and the Contexture port measured an 11 s median stall before 60% of agent requests; it enters only as the AD-1 exploratory arm. | n/a | n/a | Revisit if AD-1 shows an accuracy or blocked-action gain over `prune_pointer`. |

## 7. Dive-surfaced sources (grepped unbounded)

| Source | In index? | Would settle | Recommendation |
|---|---|---|---|
| AgentDiet artifact (figshare 10.6084/m9.figshare.30073654) | 0 hits for the DOI | the omitted reflection prompt and exact threshold | READ in this dive (prompt and code recovered, section 2 claim 1); no separate entry |
| AttnCompress arXiv 2609.08318 (attention-guided trajectory compression for SWE agents; appeared in the search for this entry) | 0 hits | a successor to the AgentDiet family | decline for now: it changes no ledger row unless AD-1's reflection arm earns its keep; read it then |
| Lindenbauer 2508.21433 | already an entry (intake-274) | n/a | no action |

## 8. Contradiction / adversarial pass

- Top of the cost range includes a behaviour fix (Gemini degenerate loops); unconfounded -21 to -27%.
- Performance equality rests on single runs without intervals; held-out test split is a strength.
- The paper's own caveat: the current design adds latency; parallel reflection is proposed but not built.
- Cross-source: Pichay's phantom-tool cooperation (no compliance rate) conflicts with AgentDiet's finding that agents ignore an erase tool.
- Contexture's contrary throughput result is a port on a shared GPU measuring different things; not a failed replication of this paper's claims. Restatements: none found.

## 9. read_depth

FULL for sections 1-6 and the algorithm/hyperparameter study; related work read for the masking comparison. Artifact: README and `traj_analyzer.py` read; trajectories, notebooks and the Trae Agent code beyond that file not read. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e.

## 10. Artifact audit

artifact audit: clean (11 quotes verified as substrings of page.txt; only dive.md and drafts/agentdiet.json written; extra files under agentdiet/artifact/ are untrusted reading material, not executed).
