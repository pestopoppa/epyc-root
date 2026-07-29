# Economy of Minds (EoM) — Deep-Dive Refinement

| | |
|---|---|
| **Date** | 2026-06-12 |
| **Intake** | intake-692 |
| **Source** | arxiv:2606.02859 ("Economy of Minds: Emerging Multi-Agent Intelligence with Economic Interactions"), Qi/Kakade/Lakkaraju/Du (Harvard/MIT); code: github.com/zhentingqi/EoM (`hayekmas` package) |
| **Prior verdict** | adopt_patterns — "adopt population-lifecycle (wealth-gated mutation / bankruptcy-gated replacement) into autopilot species management + DAR reward shaping; NOT the literal auction machinery" |
| **Refined verdict** | **downgrade → metaphor-mostly, with ONE small, optional, falsifiable mechanism**. The literal economy is concurrency-bound and not portable. The only transplantable idea — economic credit assignment for *which optimizer-population member to mutate vs retire* — is something autopilot **already implements in soft form** (`species_effectiveness.rate` → budget weights). The genuine delta is narrow: replace the analyst-tuned soft-budget formula in `meta_optimizer.rebalance()` with a self-funding wealth ledger, and add **within-species member turnover** (currently absent). Worth a ~60-LOC shadow experiment only; do not adopt the auction. |

## TL;DR / Refined recommendation

- **The auction is not portable and not needed.** EoM's value lives in a *temporal credit-assignment* trick (bucket-brigade payments chain reward back to whichever agent set up the winning move). That trick requires many agents bidding to act *within a single live episode against a shared environment* — i.e. N-way concurrent serving against one task. Autopilot runs **one config under test per trial, sequentially** (handoff: "separate trials must not run concurrently in one autopilot process", 2026-05-26 parallel-dispatch policy). There is no live multi-agent episode to run an auction over.
- **Autopilot already has the wealth analog.** `ExperimentJournal.species_effectiveness()` computes `rate = pareto_frontier_admissions / total_trials` per species; `MetaOptimizer.rebalance()` turns that rate into a budget weight; `select_species()` does weighted-random sampling over those weights. That **is** "effective species get more action-rights; ineffective species get fewer" — a softmax-over-effectiveness bandit. EoM's economic selection is a different *bookkeeping* of the same idea, not a new idea.
- **The one real gap EoM highlights: there is no member-level turnover.** Autopilot's 5 species are a **fixed roster** (`seeder, numeric_swarm, prompt_forge, structural_lab, evolution_manager`) — a `grep` for `retire | respawn | bankrupt | wealth | kill_species | spawn` across `scripts/autopilot/` returns **zero hits**. Species are never born or killed; only their *budget share* moves, floored at 0.03–0.15 so a species can never be evicted. EoM's contribution relative to us is "kill the persistently-bankrupt member and spawn a mutated/amended replacement." For us the natural unit of "member" is **not the species** (only 5, all structurally useful) but the **within-species candidate** — Optuna param-clusters, prompt variants, flag combos.
- **Smallest portable mechanism (optional):** a self-funding budget ledger that replaces the hand-tuned constants in `rebalance()`. Each species pays a fixed *rent* per trial and earns *reward* on Pareto admission; budget share ∝ running wealth; a species whose wealth goes negative is *demoted to a probe floor* (not deleted — we only have 5). This removes the analyst-chosen `0.30 + rate*0.2` magic numbers. **Falsifiable in one autopilot run in shadow mode** (log both the ledger weights and the current formula weights; never route on the ledger until A/B shows it tracks Pareto contribution better).
- **Honest call:** this is a *bookkeeping refactor of an existing mechanism*, not a capability unlock. Expected upside is marginal (cleaner attribution, fewer magic numbers). Do NOT build the auction, payments, or N-way concurrent serving. Tag intake-692 `adopt_patterns (narrow)` and gate any work behind the shadow A/B below.

## What it is — the actual selection/auction math

EoM (`hayekmas` = "Hayek MAS") frames an agentic task as a market. Verified against the paper HTML and the repo source (`hayekmas/base/mas.py`, `population.py`, `agent.py`).

**Agents.** Each agent `a` carries: a *triggering predicate* `φ_a(o_t)` (a "wake-up condition" — does this agent want to act on the current observation), a *policy* (a prompt), a *fixed bid* `b_a` frozen at creation, and a *wealth* `W_a`. A prompt-generator `G` produces mutations.

**Per-step auction (sequential, within one live episode).** At env step `t`:
1. Eligible set `E_t = { a ∈ P : φ_a(o_t) = 1 }` (`population.get_active()`, optionally thread-pooled only for the *predicate eval*, not for acting).
2. Winner `a_t* ∈ arg max_{a∈E_t} b_a`, random tie-break. Confirmed in `mas.py`:
   ```python
   max_bid = max(a.get_bid() for a in active_agents)
   top_bidders = [a for a in active_agents if a.get_bid() == max_bid]
   winner = random.choice(top_bidders)
   ```
   This is a **first-price** auction on *fixed* bids — there is no learned bidding, no Vickrey/second-price. The "auction" is effectively a static priority with random tie-break.
3. **Bucket-brigade payment** (the actual mechanism of interest), `mas.py`:
   ```python
   payment = winner.get_bid()
   winner.lose_money(payment)
   if prev_winner is not None:
       prev_winner.gain_money(payment)
   ```
   i.e. `W_{a_t*} ← W_{a_t*} − b_{a_t*} + r_t` and `W_{a_{t-1}*} ← W_{a_{t-1}*} + b_{a_t*}`. The winner pays its bid to *the previous step's winner* and pockets the environment reward `r_t`. Chaining these payments backward is a hand-built **temporal credit-assignment** path: an agent that set up a later-rewarded move is compensated by its successor. This is the Holland classifier-system "bucket brigade" — the paper's genuine algorithmic content.

**Between-episode economic selection (the "lifecycle"), `population.py` / `agent.py`:**
- **Rent**: every agent pays `ρ` per task batch → `W_a ← W_a − ρ`. A persistently-unused agent (predicate rarely fires, or fires but loses bids) bleeds out.
- **Bankruptcy → exploration**: agents with `W_a < 0` are deleted. Replacements are drawn stochastically — with prob `p_a` mutate the richest agent (exploit), with prob `p_b` "amend" the bankrupt one (correct its failure mode), with periodic births `p_g`.
- **Wealth → exploitation**: the richest agents are templates; their generator `G` proposes prompt mutations that *preserve the useful wake-up condition / policy* while perturbing behavior.
- **Novice protection** (Eq. 2): a new agent's bid is seeded just above the current max, `b_{a'} = max_{a∈C_t} b_a + ε`, guaranteeing it wins at least once so the market can price it before culling.
- **Population bounded** in `[N_min, N_max]`.

**Concurrency model (decisive for us).** *Within* an episode agents act strictly one-at-a-time across `max_steps_per_episode` (the `for step in range(...)` loop in `mas.py`). The only parallelism is (a) predicate evaluation and (b) **test-time** episodes across worker threads with thread-local snapshots and *no shared wealth mutation*. So the auction does **not** require concurrent *serving* — but it does require a single live multi-agent episode in which many distinct agents each get a turn against one shared, reward-emitting environment. That is the structural prerequisite autopilot lacks.

**Results** (for credibility, not for porting): on Llama-3.1-8B, MATH 57.0% vs ReAct 51.9%; Finance-Agent-Bench 60.0% best vs Multi-Agent-Debate 50.0%; FrontierScience 20.0% vs GEA 5.0%; Gemmini ResNet-50 accelerator DSE 39.3 EDP vs DOSA 80.2 (lower better); Cloudcast 657 vs OpenEvolve 930. Real wins on 5 tasks, but every task is a *single live environment with a step budget* — the regime where bucket-brigade credit assignment pays off. None resembles "evaluate one frozen config end-to-end and score it."

## Fit to EPYC — autopilot's CURRENT lifecycle vs EoM's

**Autopilot's current selection / credit-assignment (grounded in code):**

| Concern | EoM | Autopilot (today) | File |
|---|---|---|---|
| Unit of selection | individual agent (prompt + predicate + bid) | **species** (5 fixed optimizer types) | `meta_optimizer.py:SpeciesBudget` |
| Credit signal | bucket-brigade wealth from `r_t` | `rate = pareto / total` per species | `experiment_journal.py:759` |
| Action-right allocation | first-price auction per step | weighted-random sample over budget | `meta_optimizer.py:136 select_species` |
| Budget update | wealth ledger (rent − bid + reward) | analyst formula `max(0.15, 0.30 + rate*0.2)` etc. | `meta_optimizer.py:104-118` |
| Stagnation response | bankruptcies + new births | `hv_slope < 0.001` → +0.10 to forge/structural | `meta_optimizer.py:120-125` |
| Member turnover | delete `W<0`, spawn mutated/amended | **none** — species roster is fixed, floored ≥0.03 | (no code) |
| Bad-config memory | culling | `failure_blacklist.yaml` + auto-blacklist of rejected drafts | `state_store.py`, `planner_coordinator.py` |
| Within-species elite pick | richest agent mutated | Optuna **cluster-centroid** of top-20% trials | `numeric_swarm.py:223 _cluster_select` |

**The concrete delta is small and lives in two places:**

1. **`meta_optimizer.rebalance()` is a hand-tuned softmax; EoM's ledger is the self-funding version of the same thing.** Today `species_effectiveness.rate` (Pareto contribution) feeds magic-number formulas (`0.30 + rate*0.2`, floors at 0.03–0.15, +0.10 stagnation boosts). EoM replaces all of that with: each species pays rent per trial, earns reward on Pareto admission, budget ∝ wealth. *Same input signal (Pareto contribution), principled bookkeeping instead of constants.* This is the only clean port, and it is a **refactor of existing behavior**, not new capability.

2. **Within-species member turnover is genuinely absent — but the natural "member" is the candidate, not the species.** EoM kills bankrupt *agents*. Our 5 species are all structurally useful (you never want to *delete* the prompt-mutation capability), so species-level bankruptcy is wrong. The faithful analog is at the candidate level: an Optuna param-cluster, a prompt variant, a flag combo that keeps losing should be *retired from the live pool* and a mutated/amended sibling spawned. Autopilot partly has this (`failure_blacklist.yaml`, `mark_epoch()` invalidation, cluster-centroid selection) but it is reactive (blacklist on hard reject) rather than a continuous rent-based bleed-out. EoM's "rent + amend-the-loser" is a cleaner continuous-pressure formulation than blacklist-on-failure — but the upside over the existing blacklist is unproven and likely marginal.

**Where EoM concretely adds value vs what's there:** only (1) — turning the analyst-tuned budget formula into a self-funding ledger so the magic numbers disappear and species share is a transparent function of cumulative earned Pareto reward minus participation cost. Everything else EoM offers is either already present (cluster selection, blacklist, stagnation boost, Pareto credit) or inapplicable (auction, payments, concurrent episode).

## Decision gates & next steps

**Is there a portable mechanism + a minimal test?** Yes — one, narrow, optional.

**Portable mechanism (≈60 LOC, shadow-only):** `SpeciesLedger` alongside `MetaOptimizer`.
- State: `wealth[species]` (init equal). Constants: per-trial rent `ρ`, Pareto-admission reward `R`.
- Update each trial: `wealth[sp] -= ρ`; on Pareto admission `wealth[sp] += R`.
- Derived budget: `budget[sp] = softmax(wealth)` (with a probe floor so no species hits 0 — we keep all 5).
- It consumes the **exact same signal** `species_effectiveness` already feeds `rebalance()`; no new inference, no new eval, no concurrency.

**Minimal test (the decision gate — single autopilot run, shadow):**
1. Run with `AUTOPILOT_SPECIES_LEDGER=shadow`: every rebalance logs *both* the live formula weights and the ledger weights to the journal. **Ledger never routes.**
2. After ≥80 trials, compute correlation between each method's per-species weight and that species' *subsequent* Pareto-admission rate (held-out next-window contribution).
3. **KEEP** (promote ledger to active behind a flag) only if the ledger's weights predict next-window Pareto contribution **strictly better** than the formula AND it removes ≥3 hand-tuned constants. **DROP** otherwise — the formula stays; record "EoM ledger no better than analyst formula" in `program.md` known-dead-ends.

**Explicitly DO NOT:**
- Build the auction, bids, bucket-brigade payments, or any N-way concurrent live episode. Violates the sequential-trial policy and the no-concurrent-inference rule; no environment exists for it.
- Add species-level bankruptcy/deletion (only 5 species, all useful; floors exist for good reason).
- Touch DAR reward shaping for this — the prior rec name-checked DAR, but the bucket-brigade only helps when there is a *multi-step live episode with per-step reward*; routing decisions are single-shot. No DAR action.

**Gate summary:** metaphor-mostly. One ~60-LOC shadow experiment with a hard falsification gate. If the gate fails (likely outcome given the formula already uses the same signal), close intake-692 as `metaphor_only`.

## Risks & contradicting evidence

- **Metaphor risk (HIGH, and partly realized).** EoM is a well-executed *reframing*: a first-price auction on *fixed* bids is just static priority + random tie-break; the wealth ledger is a softmax-over-effectiveness bandit, which autopilot already runs. The genuinely novel piece (bucket-brigade temporal credit) is the one piece that *cannot* transfer because we have no multi-step live episode. Be skeptical of the economic vocabulary — strip it and most of the mechanism is already in `meta_optimizer.py` + `numeric_swarm.py`.
- **Concurrency dependence (DECISIVE).** The auction's value requires many agents each taking a turn against one shared reward-emitting environment within an episode. Autopilot's contract is one frozen config per trial, scored end-to-end, trials strictly sequential (2026-05-26 parallel-dispatch policy; no-concurrent-inference rule). A single-stack *sequential* emulation of the auction would just be "try each candidate one at a time and keep the best" — which is what the Pareto archive + cluster selection already do. The auction adds nothing once de-concurrentized.
- **Single-stack constraint.** No spare serving capacity to host an N-agent live market; the EPYC stack is a fixed role roster sharing one host. Even the bucket-brigade test-time parallelism (thread-local snapshots) maps to nothing we run.
- **Over-fitting to a refactor.** The one portable item is a bookkeeping change with marginal expected upside. The risk is spending real effort to replace working magic numbers with a ledger that performs identically. The shadow gate exists precisely to kill it cheaply if it doesn't beat the formula.
- **Roster-vs-candidate mismatch.** Importing EoM's "delete the bankrupt member" at the species level would be actively harmful (you'd starve a structurally-needed optimizer on a noisy window). The only safe unit is the within-species candidate, where we already have blacklist + epoch invalidation — so even the "turnover" idea is mostly covered.

## Cross-refs

- **Autopilot mechanism (the comparison baseline):** `handoffs/active/autopilot-continuous-optimization.md`; code `epyc-orchestrator/scripts/autopilot/meta_optimizer.py` (budget/select), `experiment_journal.py:759` (`species_effectiveness`), `species/numeric_swarm.py:223` (`_cluster_select`), `failure_blacklist.yaml` + `state_store.py` (culling memory).
- **Selection-mechanism backlog (do not duplicate):** autopilot handoff §"Scoring Upgrade Backlog" — intake-269 (TPO/CEM selection), intake-615/P17 (Bradley-Terry tiebreak), intake-248 (SiliconSwarm cross-species sharing). EoM's ledger operates on the *species-budget* step, which is upstream of all three (those act on the within-species candidate step). Sequence: it does not collide with P17/BT or TPO/CEM; if pursued, A/B the ledger against the current `rebalance()` formula only.
- **Latent-MAS cluster (population/MAS neighbors):** `research/deep-dives/2026-05-19-latent-mas-cluster.md`; intake-544 (RMAS), 555 (LatentMAS), 558 (Dead Weights), 248 (SiliconSwarm). EoM is the *economic-selection* cousin; the latent-MAS cluster is the *communication-substrate* cousin — orthogonal axes.
- **Coordinator/routing context:** `handoffs/completed/tri-role-coordinator-architecture.md`, `handoffs/active/decision-aware-routing.md` (DAR — explicitly **not** a target here; no multi-step live-reward episode), `handoffs/completed/root-archetype-swarm.md`, `swarm-dataset-distillation.md`.
- **Trinity-Evolved methodology cousin:** `research/deep-dives/trinity-evolved-llm-coordinator-methodology.md` (evolutionary LLM-coordinator selection — same family of "select/mutate coordinators by measured contribution").
