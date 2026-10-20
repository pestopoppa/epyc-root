# DF2-19 protocol (predeclared 2026-10-20, committed before any scoring)

Binding spec: the DF2-19 checkbox in `handoffs/active/dflash2-block-drafter-experimental-build.md`.
This file fixes every choice the checkbox leaves open. Nothing here was tuned on a result.

## Frozen inputs
- Transcripts: the 8 `wire-bodies.jsonl.gz` under `/mnt/raid0/llm/tmp/ds41-c95/results/C{2,4}/cxf{1,12}/r{1,2}/wire/` (sha256 in `prep/manifest.json`).
  The set has 241 turns / 582,991 predicted tokens; DF2-14 recorded 320 turns / 630k. The difference cannot be
  reconciled (DF2-14 scratch is gone) and is reported as unexplained.
- Tokenizer: `allenai/dolma2-tokenizer` rev `5292e5d6c0f40b67cc765fe41bec991cf4345b5c` (file sha256 in manifest).
- Table: `IanMagnusson/count-ngram-tables` rev `5a284fd648f90a45add297fe077233721796e062`, `tables/general-17gb`
  (min history count 12,319, orders 1-6, K=32). Reader: COUNT repo `31fd41ef4be88327d656af48463883628ceb8598`,
  `olmo-core/src/olmo_core/data/count_table.py` (`CountTable` / `_OrderSection.find_rows` / `logprobs_at`).

## Generated text and scored positions
- Turn k's generated items are the new reasoning / assistant-message / function_call items echoed in request k+1.
  Last turn of a run: only the final agent message is recoverable. Turns whose items vanish (auto-compaction) or
  that were aborted are counted as unrecovered turns with their Qwen token count in a separate column.
- Scored positions = Dolma2 tokens of reasoning text, assistant message text, and function_call arguments.
  Framing markers (role/call headers, newlines) are context only. Classes: reasoning, commentary (assistant message in
  a tool-calling turn), final (assistant message in a turn with no function_call), toolargs, patch
  (arguments containing apply_patch / `*** Begin Patch` / `diff --git` / `\n@@ ` / `git apply`).
- Context at a scored position = header (instructions + tools JSON) + all request items + generated tokens so far.

## Arms (all in Dolma2 space)
- (a) request-local: most recent earlier occurrence of the last k tokens (k in {6, 8, 12}; headline k=8) in the
  context; proposal = the token after it. "Runs>=3 coverage" = positions inside a maximal run of >=3 consecutive hits.
- (b) 17 GB table: longest stored history (orders 6..2; order 1 is the unigram row and is never used); top-1 / top-3 by
  stored score. Stored score at the matched order = P(next | history) = 10**decoded log10 score.
- (c) domain table: same row format (K=3 kept), counts built from the OTHER prompt group's transcripts only
  (all distinct pieces, prompt and generated, deduped by content hash), histories of length 1-5.
  Sensitivity: generated-text-only variant.
- (d) unions: any-correct unions of (a,b,c) for top-1 and top-3, plus priority merges for the simulation.
  DFlash2 acceptance is NOT recorded per position in the wire data (per-request `draft_n`/`draft_n_accepted` only),
  so the filed "character-offset alignment" of accepted spans is impossible. DFlash2 enters only through the
  per-turn measured tokens/step, via the overlap model below. This is a deviation from the checkbox text and is reported.

## Holdout (fixed now)
- Prompt group = context id (C2, C4); all four runs of a context replay the same prompt.
  Calibration half = C2. Holdout half = C4. The decision uses C4 only. The reverse direction (C4 calibrate, C2
  holdout) is reported as a secondary robustness check and cannot change the verdict.
- Gate parameters (minimum history length h_min in {1..5}, minimum stored top-1 probability s_min in {0,.1,...,.9})
  are chosen on C2 for each of (b) and (c) separately, maximizing the realistic-gate fitted-overlap gain below.
  Request-local k is chosen on C2 from {6,8,12} for arm (a). Table (c) used for C2 is built from C4 text, and table (c)
  used for C4 from C2 text; the only information from C4 text that reaches parameter selection is through that table.

## Step simulation (DF2-14 reconstructed; DF2-14's code is gone)
- DFlash2 block B=7 (verified: predicted_n / (draft_n/7) equals the server's "mean len"). Per turn, measured tokens/step
  m_t = N_dolma_t / (draft_n_t / 7). Latent DFlash2 correctness D_i ~ Bernoulli(a_i) per position, common random
  numbers across arms (seeded counter hash), 16 seeds, expectation over seeds.
- One step from position p: positions p..p+6; a lookup chain is active while the lookup has a (gated) proposal at each
  successive position; active position correct iff hit; otherwise DFlash2 supplies the position (correct iff D_i). The
  accepted prefix ends at the first incorrect position; the step emits accepted+1 tokens.
- Realistic gate: a gated proposal that is wrong displaces DFlash2 at that position (counted as a miss).
  Oracle gate (upper bound only): lookup overrides only when correct, else DFlash2 stands.
- Overlap scenarios: independent (a_i = q_t everywhere, q_t from m_t by the geometric block formula) and
  fitted-overlap: a_i = q_cov on positions in the arm's hit set H, q_unc,t elsewhere, where (q_cov, q_unc) come from a
  token-weighted regression across calibration turns of q_t on hit fraction, and q_unc,t is set per turn so that the
  turn's mean accept rate matches its measured m_t.
- Merge priority for combined arms: (a) first, then (c), then (b). Baseline for the gain = arm (a) alone under the
  same scenario and the same H (H = union of every arm in the comparison).
- Unrecovered / unscored turns enter the step totals at their measured Qwen tokens and steps for both sides of every
  comparison (no gain, diluting). The gain is reported with and without them; the verdict uses the diluted figure.

## Verdict (predeclared)
GO iff on the holdout (C4), with gates chosen on C2, the fitted-overlap realistic-gate simulated tokens/step gain of
(a + b) over (a) alone, or of (a + c) over (a) alone, is >= +3.0% (point estimate, diluted denominator). Otherwise STOP:
the corpus-table n-gram lane is closed at the 17 GB size. Bootstrap intervals over turns are reported but do not enter
the rule. The oracle-gate cell is an upper bound only. A 142 GB re-screen trigger is recorded only if the lowest
stored-count stratum alone clears +3.0%; the 17 GB table stores no per-history counts, so the order stratum and the
score stratum are the available proxies, and arm (c) has true counts.
Measures token-level n-gram predictability under a retokenization proxy, not drafter acceptance.
