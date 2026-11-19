# Token-efficiency audit — dispatcher era vs main-plus-subagents takeover (2026-11-06)

**Requested by**: operator, 2026-11-06 — "token use since the takeover feels far more efficient than when the
pipeline dispatcher sent out Codex workers and drained weekly budgets within hours. Audit it, say whether I am
right, propose what to do."
**Author**: operator-adhoc-ops-20261105 (audit subagent). **Scope**: read-only; one report, no code changes.
**Scratch scripts** (not committed, re-runnable): `codex_scan.py`, `codex_class.py`, `codex_calls.py`,
`claude_scan.py`, `claude_b.py` in the session scratchpad; each sums per-call `usage` fields from the raw
transcripts. Nothing below is taken from a dashboard.

## 1. Verdict

**Half right.** The dispatcher era did drain Codex budgets in hours — measured, not felt. But the takeover
regime is **not cheap**: it burns the Claude budget about **4× faster per hour** than the same Claude sessions
did during the dispatcher era, and the Claude weekly limit was hit at ~11-06 09:10Z by regime-B work (Opus
and Fable subagents for the friction passes and keeper emergency fixes), before this audit began.

| | Regime A1 — manual Codex keepers (10-24 → 10-31) | Regime A2 — hs-dispatcher-v3 (11-01 → 11-05 09:15Z) | Regime B — takeover, main + subagents (11-05 09:00Z → 11-06 09:10Z) |
|---|---|---|---|
| Codex context tokens / h (in+out, measured) | **300 M/h** (57.5 B / 192 h) | **313 M/h** (32.9 B / 105 h) | 0 |
| Codex weekly budgets consumed | W1 (reset 10-28 07:36) exhausted **11-02 17:42Z** after 5.4 days | W2 (reset 11-04 07:36) exhausted **11-05 ~04:00Z** after **21 h**, 11.4 B tokens | none (quota empty until 11-11 07:36) |
| Claude context tokens / h (in + cache-write + cache-read) | 27 M/h (5.12 B / 192 h) | 29 M/h (3.04 B / 105 h) | **100 M/h** (2.42 B / 24 h) |
| Claude output tokens / h | 42 k/h | 116 k/h | **353 k/h** |
| Claude list-price-equivalent / h (see §2.3) | ~$44/h | ~$54/h | **~$203/h** |
| Share of the Claude week that ended at the limit (10-30 09:10 → 11-06 09:10, $11.5 k-eq) | — | — | **≥42 %** in 24 h |
| Commits landed on origin/main (root repo) | 1 638 (8.5/h) | 3 815 (36/h; 136 index regens) | 215 (8.9/h; 13 regens) |
| Research-repo commits | 255 | 85 | 2 |
| Rows FILED (flag mtime; see caveat) | 411 (10-28..10-31) | 626 (incl. 523 on 11-04, of which 57 % `inconclusive`) | 238 (129 pass / 83 inconclusive / 10 fail / 14 ?) |
| Handoff boxes ticked (added `- [x]` lines) | 873 | 5 098 (4 787 of them in the 11-02/11-03 bulk reconciliations) | 235 |
| Context tokens per commit (own provider) | 35 M Codex + 3.1 M Claude | **8.6 M Codex** + 0.8 M Claude | **11.2 M Claude** |
| Output tokens per commit | 55 k Codex + 4.9 k Claude | 15 k Codex + 3.2 k Claude | 40 k Claude |
| Budget-fraction per commit | n/a (W1 weighting unknown) | ~0.11 % of a Codex week (W2: 100 % / ~890 Codex commits) | **≥0.20 % of a Claude week** (42 % / 215) |

Measured: every token figure (summed from `~/.codex/sessions/**/rollout-*.jsonl` `token_count.last_token_usage`
per API call, and from `~/.claude/projects/-workspace/**/*.jsonl` assistant `usage` fields, deduplicated by
message id); commit counts (`git log origin/main`); FILED counts (flag mtimes); quota-exhaustion times
(last/first rollout around the 11-03 gap; `USAGE-LIMIT` events in `handoff-sessions.log`; the verbatim pane
text "You've hit your usage limit … try again at Nov 11th, 2026 7:36 AM").
Estimated: the Claude week start (unknown; 7 days before the hit is the most generous assumption, so "≥42 %"
is a floor); the dollar normalisation (list prices, §2.3); Codex commit attribution (Codex commits carry no
trailer, so Codex ≈ total − Claude-trailer).
Missing: any machine-readable Codex quota meter; Codex pricing for the models used; a per-row token ledger.

So: **per hour, regime B spends about one-fifth of the raw context volume of regime A** (100 M vs 330 M
combined/h) and has no runaway loops at all — that is what the operator is sensing. **Per useful outcome and
per unit of weekly budget, regime B is no better, and on Claude it is worse**: the same Claude mains went
from ~$50/h to ~$200/h the moment they became the only engine, and the Claude week ran out in ~2.4 days of
that rate. Both regimes exhaust a provider's week; the dispatcher simply did it faster (21 h) and with far
more visible waste.

## 2. Measurements

### 2.1 Codex, per day (all rollouts, one account `ea623bd6…`)

| day | rollouts | turns | aborted turns | API calls | mean ctx/call | share of input in calls ≥300k | input (B) | output (M) | tokens in aborted turns |
|---|---|---|---|---|---|---|---|---|---|
| 10-24 | 57 | 580 | 4 | 73 280 | 233 k | 51 % | 17.06 | 25.5 | 0.38 B |
| 10-27 | 255 | 674 | 10 | 31 826 | 142 k | 16 % | 4.53 | 10.8 | 0.07 B |
| 10-28 | 173 | 1 374 | 4 | 72 367 | 191 k | 30 % | 13.82 | 31.1 | 0.02 B |
| 10-29 | 38 | 627 | 3 | 48 254 | 217 k | 44 % | 10.49 | 20.0 | 0.04 B |
| 10-30 | 192 | 564 | 5 | 35 332 | 153 k | 17 % | 5.42 | 15.8 | 0.09 B |
| 10-31 | 210 | 550 | 5 | 38 304 | 175 k | 32 % | 6.71 | 15.6 | 0.03 B |
| **11-01** | **1 363** | 6 614 | **787** | 70 309 | 144 k | 23 % | 10.15 | 24.5 | 0.46 B |
| **11-02** | **2 619** | 14 845 | **2 676 (18 %)** | 68 629 | 158 k | 34 % | 10.84 | 17.6 | 0.76 B |
| 11-03 | 28 | 150 | 0 | 5 037 | 172 k | 35 % | 0.87 | 1.7 | — (quota empty) |
| **11-04** | **1 543** | 6 384 | **737** | 50 763 | 135 k | 30 % | 6.85 | 13.2 | 0.24 B |
| 11-05 | 491 | 1 499 | 230 | 15 689 | 106 k | 8 % | 1.67 | 3.6 | 0.05 B |

- 98.9–99.2 % of Codex input every day is `cached_input_tokens`. The volume is **the same context re-sent per
  tool call**, not new material. Every fresh Codex thread starts at ~22 k tokens (21.5 k chars of
  `base_instructions` + a 24 k-char prompt, median); 2 619 cold starts on 11-02 therefore cost ~58 M tokens,
  **0.5 % of that day** — cold starts are not the mechanism.
- The pre-dispatcher keepers (A1) were 2–4 top-level threads/day plus their sub-agents, each running at
  230–450 k context (`ctx_max` 450 k every day from 10-24). Peak hours 10-28 21:00–10-29 05:00 burned
  0.8–1.1 B tokens/h with **zero** new rollouts started — one or two long threads re-sending 450 k per call.
- Model/effort share: 10-28 was a mix (luna/medium 35 %, terra/medium 23 %, terra/low 15 %); **11-02 was 91 %
  `gpt-6.1-terra/high`**, 11-04 75 %, 11-05 85 % — the `~/.codex/config.toml` default, because
  `handoff_sessions.py` passes no `--model`/effort flag (`codex exec --json -`, line 867).
- Two consecutive weekly budgets were consumed: W1 held 66 B raw tokens before exhausting on 11-02 17:42Z
  (nothing ran until the 11-04 07:06Z first rollout); W2 held 11.4 B before exhausting ~11-05 04:00Z. The
  6× difference in raw tokens per budget means **Codex quota is not linear in logged tokens** — the obvious
  candidate is model/effort weighting (W2 was ~85 % terra/high), which the operator's own 11-01 reading
  (124 M input per 1 %, ⇒ ~12.4 B/week at that mix) corroborates for the dispatcher mix. Medium-low
  confidence; it needs the provider's meter.

### 2.2 Dispatcher mechanics that set the burn (from `scripts/coordination/handoff_sessions.py`, log
`/mnt/raid0/llm/tmp/compute-flags/handoff-sessions.log`, 11-01 14:22Z → 11-05 08:53Z)

- `max_live: 4` (+1 filing slot), `auto_start: true`; every session is told to fan out to 3–5 sub-agents
  (`FANOUT_LINE`, :187) ⇒ effective width 15–25 live Codex threads. Log: START 223, AUTO-START 63, **RESUME
  2 813**, TURN-END 2 969, **UNWRAPPED (refused resume) 1 871**, LANE-REAPED 1 686, ROTATE 153, USAGE-LIMIT 46
  (all on 11-05 04–08Z), STUCK 46. Peak 286 START+RESUME in hour 11-02T10.
- Resume policy: a report whose `next` is `continue`, missing or malformed is "resumed at once" (:31-35) —
  an **unbounded resume loop with no token or wall-clock budget**; threads only rotate at
  `CONTEXT_ROTATE_TOKENS = 150_000` (:1067). The 11-01 ws58 log recorded 110 resumes for 5 rows published.
- Resumes by slug: codex-gen 765, akagg 368, hsf-residency 165, ak-cross-workload 130, kvu 123, kvfork 111.
- The worker pool in `worker_runner.py` (HARD_MAX_CONCURRENT 4, 250 k token ceiling, 5400 s lease kill,
  4 KB brief, 3 attempts) — the design that *has* every guard — was **disabled** the whole time
  (`coordination/session-bus/config.yaml:207 enabled: false`).
- Quota blindness: `handoff_sessions.py` treats a weekly-quota hit as a 30-min pause (`USAGE_RX`), so on
  11-05 it resumed, failed and paused every 30 min from 04:00 until the operator stopped it at 09:15Z
  (`keeper-friction-review-20261105.md` F2).

### 2.3 Claude, by regime window (price-weighted to compare models; list prices Opus/Fable 15/75/18.75/1.5,
Sonnet 3/15/3.75/0.3, Haiku 1/5/1.25/0.1 $/M for input/output/cache-write/cache-read — a normaliser, not a bill)

| window | hours | ctx tokens | output | $-eq | $-eq/h | who |
|---|---|---|---|---|---|---|
| A1 10-24..10-31 | 192 | 5.12 B | 8.0 M | 8 382 | 44 | e3953395 main + 1 264 subagents, 9bcb/3c4c intake |
| A2 11-01..11-05T09 | 105 | 3.04 B | 12.2 M | 5 626 | 54 | e3953395, 7da2a73f, 73998e9f (main-inf22), 3b737de6, 2eec20d1 |
| **B 11-05T09..11-06T09** | **24** | **2.42 B** | **8.5 M** | **4 881** | **203** | 688f713e (this session) $1 976 on 11-05, 73998e9f $1 694 on 11-05 + $1 075 on 11-06 |

Regime-B composition on 11-05: this session — main/opus $654, **sub/opus $1 140**, sub/fable $136, sub/sonnet
$46; main-inf22 — main/opus $838, sub/opus $808. Across 11-05/06 both sessions together ran **$2 645 of Opus
subagents, $242 of Fable subagents and $68 of Sonnet; zero Haiku**. Every subagent that was not Fable ran as
Opus at default effort. The 7-day Claude window ending at the limit: Opus $9 878, Fable $1 237, Sonnet $419,
Haiku $3.

### 2.4 Outcome caveats

- FILED mtimes date the *filing*, not the run: filing was wedged 11-02→11-05 (3 981 `unknown rc=2` alarm
  lines), so the 523 flags of 11-04 are a backlog flush; 57 % were `inconclusive`.
- Commit counts include the keeper's per-turn wrap-up commits and index regens (136 regens in A2; the friction
  review counted 99 "Regenerate handoff index" of 1 083 commits in one 16-h window). Research-repo commits
  (255 / 85 / 2) are the better signal of inference results landed, and they also fell in A2 and B.
- Boxes ticked on 11-02/11-03 (1 468 + 3 319) were bulk reconciliations (vidya review 384→90), not work.

## 3. Mechanisms

### 3.1 Why the dispatcher era drained budgets — candidates confirmed / refuted

| candidate | verdict | evidence |
|---|---|---|
| Many parallel workers each loading full context from cold | **Refuted as stated; confirmed in warm form** | Cold starts are 0.5 % of a day (§2.1). The cost is **width × context per call**: 15–25 live threads each re-sending 135–230 k mean context (30–50 % of input in calls ≥300 k) at every tool call. |
| Retry loops on failed smokes and arming | **Partly confirmed** | 787 / 2 676 / 737 aborted turns on 11-01/02/04 (18 % of turns on 11-02) but only 5–7 % of tokens sit *inside* aborted turns. The expensive part is indirect: each failure re-enters the resume loop (2 813 RESUME, 1 871 refusals, 469 smoke-fail notifies on 3 parked rows, a STOPped row granted 1 344 times). |
| Polling / idle-waiting workers | **Confirmed, in the dispatcher not the worker** | `next: continue` ⇒ immediate resume, no budget; 11-01: 110 resumes for 5 rows; the 30-min quota pause loop on 11-05. Workers themselves were told not to poll only by prompt text (`NO_POLL_LINE`). |
| Re-reading large handoffs | **Confirmed as the A1 driver** | Keeper threads owned a whole `handoffs/active/<file>.md` and ran at 450 k context from day one; peak hours with 0 new rollouts and ~1 B tokens/h. The 11-01 log measured 1.7–6.4 M tokens per main-session turn (120–340 k context × every tool call). |
| Workers redoing each other's work | **Not demonstrable from the data** | 1 686 LANE-REAPED and 765 codex-gen resumes suggest duplicated bookkeeping, but there is no per-row token ledger to prove duplicated *work*. Unconfirmed. |
| No stop-on-answer rule | **Confirmed structurally** | Nothing in the dispatcher ends a session on an answer; it ends on quota, on `next: done`, or on the operator. |
| Prompts too large | **Refuted** | Median prompt 5.3 KB file / 24 k chars incl. boilerplate (~6 k tokens); max 20.7 KB. |
| Model / effort mismatch | **Confirmed, probably the budget multiplier** | 91 % of 11-02 tokens at terra/high (config default, no flag), including 1 069 sub-agent rollouts that doctrine says run luna/medium. The 6× raw-tokens-per-budget gap between W1 (mixed) and W2 (85 % terra/high) is best explained by effort-weighted quota. |

Top three, in order: (1) **full-context re-send × width** — the product of 150 k rotation threshold, 450 k
windows and 15–25 concurrent threads; (2) **the unbounded resume loop** that turned every failure into another
full-context turn; (3) **everything at terra/high**.

### 3.2 Why regime B's hourly *volume* is lower, and why it is still expensive

Lower: one integrating main per session (two sessions), no automatic resume, no polling (zero-token
`Monitor`/`run_in_background` watchers), an operator who stops threads, and Claude prompt caching — 98 % of
Claude context is cache-read at 1/10 price, so 2.4 B ctx tokens cost what 0.3 B uncached would.
Expensive anyway: the fan-out doctrine ("3–5 subagents concurrently, always") was executed with **Opus at
default effort for every subagent** including clerical ones; Fable subagents were spawned for friction passes
despite the 10-04 memory rule; subagents are long (296 in this session, 296 in main-inf22 in ~40 h) and each
carries the full CLAUDE.md + memory + skill preamble (~20–30 k tokens cache-write per spawn — 24 M cache-write
tokens in this session's subagents alone). Output tokens per commit doubled versus A2 (40 k vs 15–18 k):
Claude subagents reason more per unit of landed change than terra workers did.

## 4. Confounds

1. **Task mix.** A was inference row-churn (prep, arm, smoke, file) on 6–8 lanes; B was emergency code fixes
   (friction passes, keeper, filing alarm) plus one kernel-port session. Commits and FILED counts are not the
   same kind of outcome across regimes.
2. **Operator attention.** B had the operator in the loop continuously; A ran overnight unattended. Part of B's
   "efficiency" is a human stopping bad threads — a cost not in any token ledger.
3. **Mid-way fixes.** The 11-01 fixes (10-min resume floor, 150 k rotation) and the 11-05 fixes (stop-file
   grant, filing alarm, dispatcher quota) changed A2 while it ran; 11-05 Codex mean context fell to 106 k.
4. **Accounting.** Codex `last_token_usage` counts cached input at face value and includes reasoning tokens in
   output; its quota weighting is unknown (§2.1). Claude usage splits cache-write/read; weekly-limit weighting
   is likewise unpublished. Cross-provider "tokens" are therefore compared only as volume; budget-fraction is
   the only fair common unit and it is a floor on the Claude side.
5. **Both weeks' Codex were already spent by 11-05** — regime B had no Codex to use, so its all-Claude
   composition is partly forced, not chosen.

## 5. Recommendations (ranked by tokens saved per unit of effort)

1. **Effort/model routing by code, not config default** — one line in `handoff_sessions.py` (and in every
   Claude `Agent` brief): pass `--model`/effort per role; sub-agents luna/medium or Sonnet/Haiku; terra/Opus
   only for the integrating main. Expected: the ~4–6× budget-weighting multiplier disappears; Claude-side
   the Opus-subagent $2.6 k/day becomes ~$0.5 k at Sonnet. Effort: hours.
2. **Per-session token budget with a hard stop** — the worker pool already has `HARD_TOKEN_CEILING` and a
   lease kill; port those two to `handoff_sessions.py`: a session that has consumed N tokens (start: 30 M) or
   M resumes (start: 10) without a new `ready/` or `FILED` artefact is parked, not resumed. Kills the resume
   loop and the "110 resumes for 5 rows" pattern. Effort: a day.
3. **Budget meter and alarm** — a zero-token script that sums `token_count` deltas from the rollout files
   (the scan in this audit runs in ~3 min for a month) and Claude `usage` from transcripts, writes
   `coordination/session-bus/budget.json` {provider, spent_since_reset, resets_at, rate/h, ETA-to-empty},
   and raises an alarm at 50 % and 80 % of a week. Quota hits set `paused_until = resets_at` (friction review
   §6), never a 30-min retry. Effort: a day; it also closes the "quota blindness" defect.
4. **Rotate at 60 k, not 150 k; whole-task turns.** Mean context per call is the single largest factor; a
   60 k cap roughly halves A2's volume at the same width. Effort: one constant plus a brief line.
5. **Width cap by budget rate, not by lanes**: `max_live` becomes f(remaining budget, hours to reset), so a
   fresh week cannot be spent in 21 h; 2 live sessions × 2 sub-agents until the meter proves headroom.
6. **Per-row token accounting at filing**: `tokens_per_task.py` already attributes rollouts to lanes; make
   the FILED record carry `tokens_spent` so cost per result is a column, not an audit.
7. **Circuit breaker on repeat failures**: a row that fails smoke/arming 3× is parked *and its successors
   inherit a cooldown*, instead of 469 notifies on 3 parked rows.

**Dispatcher restart**: **restart, but not as it was.** Restart only after items 1–3 exist (routing, per-session
budget stop, meter with `paused_until = resets_at`), at `max_live: 2` with sub-agent fan-out ≤2, in the
main-plus-subagents shape the worker pool already implements (`worker_runner.py` has the guards; the
`handoff_sessions.py` path has none). Without those three it will spend the 11-11 week in about a day again.
Until then, Codex work is hand-dispatched by the owning main.

**Delete lens — stop doing:**
- Stop "3–5 subagents concurrently, always" as a floor; it is a ceiling. Fan out when the work is parallel;
  the 11-01 log measured fan-out at 70 % of spend.
- Stop Opus/Fable subagents for clerical, filing, grep and status work (memory rules of 10-04 and 10-05
  already say so; §2.3 shows they are not followed under pressure).
- Stop per-turn wrap-up commits and index regens by workers (136 regens in A2); regen once per batch.
- Stop resuming on `next: continue`; stop treating a quota hit as a 30-min pause.
- Stop running the 450 k-context keeper threads of A1 at all; whole-handoff ownership in one thread is the
  single most expensive shape measured here (17 B tokens on 10-24 from 2 threads).

**Doctrine change (two lines)**: *Every dispatched or spawned agent carries an explicit model, effort and
token budget; a spawn without all three is a defect.* *Budget-fraction per landed outcome is reported at every
wrap-up next to tokens per task.*

## 6. Open data gaps

- No provider meter is readable; both weekly limits were discovered by hitting them. Item 3 above is the fix.
- Codex W1 vs W2 raw-token-per-budget differ 6×; the weighting is inferred, not known.
- Claude week start unknown; "≥42 %" is a floor. If the week began after 10-30, regime B's share is higher.
- No per-row token ledger exists for either provider, so "tokens per useful outcome" above uses commits and
  FILED flags as proxies with the caveats in §2.4.
