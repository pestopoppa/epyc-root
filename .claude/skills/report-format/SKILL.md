---
name: report-format
description: The fixed shape of every report to the operator — headline result, numbers with unit/baseline/direction, what is running or queued with ETA, what is blocked on what until when and why, the exact commands the operator must run, and a final `Next:` line naming the owner; plus the jargon rule (expand every ID or acronym on first use). Use whenever you write a status, ETA, run-end, wrap-up or "done" report to the operator, answer "status?" / "why is it idle?" / "what is left on X?", or relay another session's result.
---

# Report Format

Origin: operator-steering analysis 2026-11-21 (`/mnt/raid0/llm/tmp/operator-steering-analysis-20261121/REPORT.md`
§2(b)/(c)). About 73 % of the operator's turns compensated for reporting or acting gaps: "status?", "10 % faster
than what?", "which command?", "what are you waiting for?", "what is Q38FN?". This template removes each one.

## The template (six parts, in this order; omit a part only when it is genuinely empty, and say "none")

1. **Headline result** — one sentence: what changed, or the verdict. Not what you did; what is now true.
2. **Numbers** — every number carries its **unit**, its **baseline** (versus what: previous champion, production
   v10, the last run) and its **direction** (better or worse, and which way is better for that metric).
   `decode 41.2 tok/s vs 38.0 production v10 (+8.4 %, higher is better)`, never `10 % faster`.
3. **Running / queued** — each row or job with its owner and an **ETA** (grant end, expected start, or "starts
   when <bin> frees at HH:MMZ"). `python3 scripts/session/status_digest.py` gives sections 1–3 ready-made.
4. **Waiting / blocked** — every "waiting", "blocked", "queued" or "parked" names **on what**, **until when** (time or
   event) and **why**. Idle compute names its placement reason (copy the keeper's IDLE-WHY). A handoff mention names
   its open-box count and the blocker per box (digest section 4). A blocker you last checked more than 1 h ago is
   re-probed first: `python3 scripts/session/recheck_blocker.py <kind> ...` (codex-login, which, python, model,
   disk, row). A CLEAR result means the blocker is gone; act, do not report it.
5. **Operator must do** — exact, copy-paste commands, never a description of them. Pull them from the accumulator:
   `python3 scripts/session/pending_operator_cmds.py combined` (ONE line, or a short script). Add yours first with
   `pending_operator_cmds.py add --cmd '...' --reason '...' --kind sudo|ratify|host`. "None" when nothing is needed.
   A genuine decision goes through AskUserQuestion as an options package, not prose.
6. **`Next:`** — the last line of the report: the next action and who owns it.
   `Next: pipeline-mgmt files dcp12 verdict at 00:20Z when grants/dcp12.ended lands.`

## Jargon rule

Expand every ID, row name, acronym and project term on its **first use in each report**, even if you used it in the
previous message: `Q38FN (Qwen3.8-Flash-Next, the CPU MoE served model)`, `INF-82 (the AutoKernel AKX program
handoff)`, `DTREE-0 (decision-tree routing probe, step 0)`. After the first use the short form is fine. A term the
operator already asked about is never left bare again.

## Checklist before sending

- [ ] Headline is a result, not an activity log.
- [ ] Every number: unit, baseline, direction.
- [ ] Every running/queued item: ETA. Every blocked item: on what, until when, why (re-probed if > 1 h old).
- [ ] Operator commands are literal, from the accumulator; no "please run the ratify".
- [ ] Every ID/acronym expanded once.
- [ ] Last line starts with `Next:` and names an owner.

## Do not

- End on a question when the operator already authorized the action: an authorized action is executed, not
  re-asked.
- Repeat a blocker from an earlier report without re-probing it.
- Report "done" without saying what is left (open boxes) and who does it.
