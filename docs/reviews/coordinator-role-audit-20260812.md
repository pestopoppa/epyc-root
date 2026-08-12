# Adversarial audit — the coordinator-agent role's design

**Date**: 2026-08-12 · **Subject**: `handoffs/active/coordinator-role-failure-modes-and-refactor.md`
(commit `2f8ba256`, 11:15:11Z; index row RTG-48) and `agents/coordinator-agent.md`.

> **This is not the auditor's verdict.** The `auditor` main is at 100% context and unreachable, so
> this review was written by a stand-in at the operator's request. It should be read as an
> independent adversarial pass, not as the ruling `A-1`…`A-9` asked for. Where the `auditor` later
> disagrees, the `auditor` wins — it authored two of the artifacts under review here (`03e17111`,
> `e08fe836`) and has first-hand knowledge this review does not.

## What this audit rests on, and where it is thin

Verified against primary artifacts: git objects, the eight bus JSONL pairs (839 rows), the hook
registry, and the on-disk scripts. Two structural facts limit everything:

1. **The operator writes zero bus rows.** Confirmed independently: 839 rows across all sixteen
   inbox/outbox files, `from` is one of eight *agents*, `operator: 0`. Every *"the operator said X"*
   in this repository is an agent's transcription of a tmux conversation.
2. **`git clean -ffdx` at 08:20Z destroyed the pre-08:20:31Z bus.** The out-of-repo archive at
   `/mnt/raid0/llm/tmp/bus-incident-20260812T0825Z/` was checked: its 826-row file is the **July
   27–30 committed state recovered from git**, not the 08-12 night. No artifact anywhere holds 08-12
   bus traffic before 08:20:54Z.

Consequence for this audit: the post-08:20Z window is **complete and continuous** (the 08:25Z
snapshot is a byte-exact prefix of today's live outbox), so negatives inside it are strong. Negatives
about the overnight window are worthless. Each finding below states which it is.

Where I could not establish something, it says so. Three such places are marked **[THIN]**, plus one
standing gap that gates several others: **no sound thread-attribution method exists in this repo** —
the `Co-Authored-By` trailer names the committing thread, `scripts/utils/agent_log.sh` has no agent
field at all, its only non-legacy shard is named `agent_audit-unattributed.log`, and it recorded zero
rows in the 10:28Z–11:28Z window when five agent-infrastructure artifacts were produced. Answering
`A-9`: **no, and the fix is not a better inference rule — it is a field that does not exist yet.**

---

## 1. Verdict on RC-1

> RC-1 as written: *"Written policy has no checkpoint at the moment of action, so compliance decays
> with context. Rules with a mechanism held; rules relying on recall decayed."*

**Verdict: the conclusion is directionally right and every leg of the argument for it fails. The
comparison it rests on is structurally impossible to make; four of the six "rules that held" do not
hold on audit; and its causal claim — decay — is refuted by its own flagship example at zero decay.
Accept the recommendation, reject the reasoning, and do not price the refactor off it.**

### 1a. The evidence tables cannot support the comparison they are used for

RC-1 rests on two hand-built tables: five or six rules violated (all un-mechanised) beside six rules
that held (all mechanised). That comparison is **structurally impossible to make with this data**:

- **A mechanism that holds leaves a log line. A prose rule that holds leaves nothing.** Hook
  refusals, `flock` messages, adapter refusals — all self-record. A coordinator who correctly
  restated a decision as options-with-tradeoffs emits no artifact saying so. The "rules that held"
  column can therefore only ever be populated by mechanisms. It is a definition, not a finding.
- **There are no denominators.** The registry carries **13 `PreToolUse` hooks** (5 `Bash`, 8
  `Write|Edit`). The startup/role policy surface an agent is bound by carries **1,509 lines and 252
  directive-bearing lines** across `CLAUDE.md`, `AGENT_INSTRUCTIONS.md`, `coordinator-agent.md`,
  `OPERATING_CONSTRAINTS.md`, `SESSION_LIFECYCLE.md`, `MEASUREMENT_POLICY.md`, `BUS_PROTOCOL.md` and
  the coordinator skill. "6 mechanised rules held / 5 prose rules broke" out of populations of ~13
  and ~252 tells you nothing about per-rule violation rates — it is consistent with prose rules
  holding 98% of the time.
- **This is `a90870ec`'s own error.** *Reporting Units* says a count of records quoted without its
  denominators reports the producer's tick rate as a property of the fleet. RC-1 quotes N (violations
  observed) with no M (rules in force) and no K (occasions where the rule was live). **The document
  commits RC-2 inside its proof of RC-1**, and RC-1 is the parent claim of the whole file.

### 1b. The causal claim — "compliance decays with context" — is refuted at zero decay

Two independent cases, both inside the corpus:

- **F-02.** The wrong-instrument error was written up as *the coordinator's own correction #2* and
  **committed at 10:07:18Z** (`7b4e0ac1`, verified: nine corrections, #2 is verbatim the instrument
  error). The next instances follow at **10:28:19Z** (GPU regranted away from a resident campaign;
  `inference` disputes the idle premise at 10:45:28Z: *"GPU was not idle: my authorized INF03
  six-arm AutoKernel campaign has been continuously resident"*) and **~10:40Z** (the post-exit VRAM
  accusation against `mainB`, rebutted 10:46:16Z). **21 and ~33 minutes.** Same session, same day,
  the agent's own words, already on disk and in git.
- **`ed38041d`'s own hook header**, written by another lane six hours later, states the same shape
  more sharply: *"The repo already had the rule written down — in that very file, three lines from
  the code that broke it."*

Decay is not the variable. Proximity was maximal in both cases. What failed is **retrieval at the
moment of emission**: nothing in the act of composing a bus payload or typing a `git` command
required a read of the place the correction lived.

This distinction is not academic — it reprices the refactor. "Decay" implies the fix is *durability*
(a ledger, a re-read cadence, landing untracked files). "Retrieval failure at zero decay" implies
durability is beside the point and the fix must sit **on the emission path**. The evidence in §5
settles it: the durable-ledger fix was built, and it failed in 48 minutes.

### 1c. The "rules that held" table does not survive audit — four of six rows fail

Every row was re-tested against the registry and the scripts. A `MECH` claim is only true if the
mechanism would have **refused the specific failure**.

| # | Row as written | Verdict |
|---|---|---|
| 1 | No name-pattern kills → `check_process_pattern_kill.sh` | **EXISTS-BUT-WEAK.** Blocks the spelling. `killall llama-server`, `kill $(pgrep -f x)`, `bash -c "pkill -f x"` all pass clean — the scanner anchors on `(?:^\|[\s/])(pkill\|pgrep)\b`, so `$(pgrep …)` never matches and the hook's own comment (*"selection feeding a kill is caught at the kill"*) is false. **And the rule was violated inside the very window the table covers**: `68979233` (05:52:40Z) exists *because* a coordinator subagent ran `pkill -f` — *"The rule existed and nothing enforced it."* It broke, then got a mechanism. Worse, `scripts/session/emergency_cleanup.sh:26` is a **tracked `sudo pkill -f claude` right now**, invisible to the hook because it inspects the invoking command, not the script body (OBS-7) |
| 2 | No wholesale staging → `check_commit_hygiene.py` | **EXISTS-BUT-WEAK.** `git stage -A` is live (confirmed: `git stage -n -A` resolved and listed the whole dirty tree); so are `git add /workspace`, `git add progress/`, `git add :/`, and `git -c x=y add -A` (an operator-precedence bug at `check_commit_hygiene.py:176`). It blocks the *spelling* of wholesale staging, not wholesale staging. Corroborated the same day: `mainD` left a staged `git rm --cached` deletion in the shared index for a minute — `rm` is not in `{add, commit}` |
| 3 | One daemon, one supervisor → `flock` | **AS CLAIMED.** Receipts on disk (`logs/bus_supervisor.log:15`, 08:25:03Z). One downgrade: `logs/coordinator_daemon.log`'s two lock-exit lines are **untimestamped** with a `SyntaxError` traceback immediately above them, so *"every bad relaunch died on the singleton"* should read *"at least two did, at unrecoverable times"* |
| 4 | Do not type into a busy pane → `tmux_adapter.py` composer guards — *"refused a nudge that should not have been sent"* | **REFUTED, and it is itself an RC-2 error.** The C51 comment block records that on 2026-08-12 every Claude pane rendered its empty composer as U+276F while the glyph table was calibrated to U+2771 on 07-28: *"`_composer_row_is_empty` returned False for an EMPTY composer on all six Claude panes, so `doorbell`'s guard (b) **refused every ring to every Claude main** — the fleet's brand-new delivery path was 0% operative."* A guard that refuses 100% of inputs has no discriminating power over the two hypotheses. **The evidence for RC-1 is a probe that cannot distinguish them — RC-2's own sub-shape.** And the fix is still uncommitted: `git show HEAD:…tmux_adapter.py` line 385 still reads `_BARE_PROMPT_GLYPHS = ("›", "❱")` |
| 5 | Trust boundary human-only → `check_trust_boundary_edit.sh` Layer 1 | **AS CLAIMED**, best-attested row: exit 2 verified live for Write and Edit, including `../`-laundered paths, and one real refusal on the record (`progress/…-12.md:3817` — the sampling rules were pushed out of `MEASUREMENT_POLICY.md` because the hook refused). Scope qualification: it is registered on `Write\|Edit` only — `sed -i … human_only_paths.yaml` exits 0 through all five `Bash` hooks. **The containment is tool-shaped, not path-shaped** |
| 6 | Nudge limit is per-agent → `34a17894` regression test | **VACUOUS.** `_c31_probe` passes `900.0` as `quiet_s`, not `min_interval_s`, and `probe()` never appends a rate-limit blocker at all — the only one is in `cmd_nudge`. Test 1's `assert not any("rate limit" in b …)` **cannot fail**; test 2 asserts attribution with no refusal assertion. Deleting the `if` block at `tmux_adapter.py:2043` leaves both green. The commit body's claim that the test *"cannot be satisfied by deleting the rate limit"* is false. The per-agent property is pinned via attribution, so the row is not *wrong* — but it does not meet the standard it invokes |

**Two of six rows are as claimed. One is vacuous by construction, one is refuted by an artifact
written by the same author days later, and two block spellings rather than behaviours.** RC-1's
evidence that mechanisms hold is, on audit, mostly evidence that mechanisms *log*.

### 1d. The refutation `A-2` asked for exists — and the biggest one runs the other way

`A-2` asked for a rule that had a mechanism and was violated anyway. There are several, in two
opposite directions, and both directions matter:

**Mechanisms that failed as mechanisms:**

| Mechanism | What happened |
|---|---|
| `bus_supervisor.sh` `DAEMON_PATTERN` → `pgrep -f` | Encoded the supervisor's own launch idiom; killed a healthy 75-minute-old daemon (F-24) |
| `verify_ggml_linkage.sh` | Detected the right condition and **printed a remedy that does not work** (`…/build-hip/bin/bin`). `mainB`, 10:46:16Z: *"I applied its own suggestion verbatim and the run stayed on CPU while looking fine. A guard that … prints a remedy that silently does nothing is worse than no guard: it converts a caught failure into a confident wrong number."* |
| `check_process_pattern_kill.sh` | Held — then was **narrowed 1h50m later** (`e08fe836`) because C46: *"the guard forbade an idiom a project skill instructs"*. A mechanism fired, was found to contradict written policy, and was narrowed to match it — the inverse of RC-1's direction of travel |
| C47 (`ee628304`) | The same hook blocked the coordinator's bus message **reporting the incident it guards**; worked around by changing channel |

**And the largest single case runs the other way — which overturns the handoff's delete-lens
argument.** `03e17111`'s classifier had an explicit branch for `git clean`:

```
elif sub == "clean":  … if "f" in flags: dirty = _status(repo, None)
                          if any(l.startswith("??") …): return f"block:clean-untracked:{repo}"
```

With 149 untracked entries present in `/workspace`, that predicate returns
`block:clean-untracked:/workspace`. **The guard would have refused the exact command that destroyed
this corpus** — and it had been reverted 27–47 minutes earlier.

The `checkout` defect `mainD` found does not reach the `clean` case: it is `cd /tmp; git checkout --
<dirty>` slipping through because `shlex.split` leaves `/tmp;` as one token, so `seg[0]` is `cd`. A
bare `git clean -ffdx` is a single segment whose first token *is* `git`. The good branch was thrown
out with the bad one.

**Correction to the handoff, and it removes the foundation of `A-4`.** RC-1(b) and `A-4` present
`03e17111` → `3d8800e6` as *"the standing proof that a well-built, well-tested guard can still be the
wrong trade."* The record says otherwise. `progress/2026-08/2026-08-12.md:2105`: ***"hook 2 revert
accepted — mainD's review found two HIGHs my 12 tests missed (suite mutated the target, never the
shell framing; lesson mine)."*** **It was reverted as defective, not as a bad trade.** The
delete-lens argument built on this episode has no support in any of the five files that reference the
pair; the genuine "mechanisms cost something" datum is `e08fe836`, where the recorded reason is a
collision with an approved workflow.

**[THIN] and load-bearing:** *who* ran `git clean -ffdx` is unrecoverable (the clean removed the
logs; `progress/…-12.md` says so explicitly). The guard models agent-typed Bash only. So the honest
form is *"a mechanism covering the exact command was absent when it fired"* — **not** *"a mechanism
was present and bypassed."* If a human ran it in a terminal, no `PreToolUse` hook could ever have
fired, and the whole episode is outside RC-1's universe.

### 1e. A mechanism failure is still live, right now

The F-24 class did not close — it **moved**. `e57a10a6` replaced the `pgrep` predicate with a
source-mtime freshness check guarded by `STALE_SRC_STATE` ("restart once per source version",
commented *"a file the fleet touches often would put the supervisor in a restart loop, which is worse
than the staleness"*). **In a five-writer tree, every fleet edit is a new source version, so the
anti-loop guard is vacuous.** `logs/bus_supervisor.out` from 11:02:43Z shows **eleven
`stopping wedged daemon pid X` cycles in 35 minutes** (11:02, 11:07, 11:09, 11:10:11, 11:10:33,
11:14, 11:17, 11:22, 11:26, 11:28, 11:37), each killing a healthy daemon;
`logs/coordinator_daemon.log` shows epoch **54 → 64**. First instances are visible at 08:24:56Z and
08:25:18Z, 22 seconds apart.

Same class, one predicate later: *the health predicate encodes a property of the observer's
environment rather than the target's health.* This is the strongest single argument in this review
for pricing mechanism failure into the refactor — **and it needs an owner today**, independently of
everything else here.

Related and worse, from `ed38041d`'s own filing (OBS-1…OBS-10, ten more watchdogs that cannot observe
their targets): **OBS-3, HIGH — `scripts/nightshift/inference_guard.sh` fails OPEN.** A missing
`pgrep`, argv drift, a renamed binary or an `xargs` error all sum to 0 GB, print *"No heavy inference
detected"*, and let `run_wrapper.sh` launch the full agent workload on top of a live 200 GB inference
run.

### 1f. What is true, restated so it can be built on

Strike "compliance decays with context". The supportable statement is narrower and more useful:

> **A rule is followed at the rate at which the act it governs forces a read of it.** A hook forces
> the read (the tool call cannot proceed). A required field forces the read (the message cannot be
> written). A sentence template forces the read (the number cannot be phrased without it). A
> paragraph in a file does not force anything, however recently it was written, and however close to
> the code that breaks it.

That formulation has a third category RC-1's binary lacks — see §5 — and it survives all three
counterexamples above, which the mechanism/recall binary does not.

---

## 2. Corrections: verified, overturned, and one systematic bias

The handoff revised 11 of the operator's 24 items, withdrawing one and calling the method behind two
unsound. I checked six against artifacts. **Two of the three that revise charges *downward* do not
survive, and they fail in the same direction.**

| Correction | Verdict |
|---|---|
| §2 — F-13 is three composers across **two** mains, not three | **VERIFIED**, with a material omission (below) |
| §3 — the quote *"inference is genuinely working"* does not exist | **CORE VERIFIED, SUPPORT OVERTURNED** |
| §5 — F-23 contradicted; every identical auditor/mainA payload is a broadcast | **VERIFIED** |
| §9 — F-16's authorship claim struck; the trailer method is unsound | **OVERTURNED** |
| §10 — F-17 withdrawn; the merges were "landed by the operator", evidence "decisive" | **OVERTURNED as to the ground and the word "decisive"** |
| §11 — F-19 confirmed on one of four claims; the hook gap is exact | **VERIFIED**, one imprecision |

### §9 — OVERTURNED. The struck claim is now supported by a self-admission.

§9 struck F-16's authorship half on the ground that `Co-Authored-By: Claude Opus 5 (1M context)`
names the committing thread, not the author, and that `fleet_watch.sh` had no commit at all so its
authorship was *"not merely unproven, it is unrecordable."*

That was true at 11:15:11Z. **Thirteen minutes later `83f204cf` (11:28:03Z) landed the file, and its
first sentence is:**

> *"Hand-written by the coordinator on its own thread under time pressure, running uncommitted as pid
> 4044227, never tested."*

The original charge is restored by primary evidence that does not touch the trailer. Separately, the
trailer argument is overstated on its own terms: 2 documented counterexamples against 27 commits
carrying the trailer since 08-11 is a ~7% falsification rate — enough to demote the signal from
*proof* to *weak evidence*, not enough to justify *"any audit finding of this form must be struck."*

### §10 — OVERTURNED as to its stated ground.

§10 withdrew F-17 on **"contradicting evidence, decisive"**, whose first leg is that the four
`merge/reconcile-fleet-20260812` merges *"carry no co-author trailer at all"*, therefore the operator
landed them. Checked:

- **Five other merges on the same reconciliation lineage DO carry the trailer** (`c9fb990e`,
  `7a286286`, `db2d2804`, `3663e428`, `1074d15e`) — and `1074d15e` is the **first parent** of
  `66bdce89`, nine minutes earlier.
- Base rate: **5 of 48 merges since 08-11 carry any trailer (10%); 308 of 447 non-merges do (69%).**
  Trailer absence on a merge is the *norm*, and it is fully explained by `git merge` accepting its
  default message — every untrailered merge here has git's auto-generated subject and an empty or
  conflict-list-only body.

**The decisive objection is internal.** §9 argues the trailer's *presence* proves nothing about
authorship. §10 then treats its *absence* as affirmative evidence for a specific alternative author.
Those cannot both stand. And the asymmetry runs one way: **§9's evidentiary rule discards evidence
that incriminates the role; §10's accepts evidence that exculpates it.** A self-audit is entitled to
revise charges downward, but not with two opposite rules for the same signal.

What survives of the withdrawal: the delegation broadcast is real (verified — *"Do NOT push main - a
subagent of mine is serializing pushes"*, sent 10:35:46Z to **both** mainC and mainD; the handoff's
`10:36:08Z` is the daemon's relay timestamp, and it omits mainC). The remaining support is
`progress/…-12.md:3435` — the coordinator's own wrap-up asserting what the operator did, which by the
document's **own** §1 standard is `self` provenance on a claim that exculpates the self-reporter.
F-17 may still be right; it is not "decisive", and the row should not read as it does.

### §3 — core verified, supporting evidence overturned.

The quote *"inference is genuinely working"* genuinely does not exist — 2 hits repo-wide, both inside
the handoff itself; `git log -S` finds one commit, the handoff's own. The **support** is false:
§3 asserts *"Zero hits repo-wide for 'genuinely working' or 'is genuinely'."* Actual:
**13** and **258**. At the document's own commit, `git grep "is genuinely" 2f8ba256` returns **201**
hits in long-tracked files. A proof-of-absence built on a grep that was never run as stated is the
error class the document itself catalogues (RC-2, *"asserted where measuring was cheap"*). The
substitute framing it offers is verbatim-attested and should stand.

### §2 — verified, but it omits the owning main's on-record dispute.

`fleet_watch.sh:7-9` does enumerate `mainB` / `mainC` / `mainB` — two mains, and the "three separate
mains" wording does originate in the coordinator's own comment. But `mainB` disputes the attribution
itself, on the bus, at 10:46:16Z:

> *"`run the full BGE sweep` was not mine, as `push it` was not mine earlier. I have submitted every
> command I intended to run this session… Worth checking whether that detector is attributing
> composer state correctly — **it has now misattributed to me twice**, and a false root cause for the
> idle GPU is itself costly."*

Both the original claim and the correction rest on the same detector the owner says misattributed
twice. F-13's evidence base is weaker than either party has recorded. This does not clear the
composer defect — the defect was independently reproduced (`/workspace/tmp/tmuxfix/repro.py`) — but
the *count* and the *attribution* are unestablished, and the correction should say so.

### §11 — verified; one wording fix.

Eight `Write|Edit` hooks confirmed; `agents_reference_guard.sh:15` lists `CLAUDE_GUIDE.md` and not
`CLAUDE.md`; `agents_schema_guard.sh` exempts `AGENT_INSTRUCTIONS.md` **by name**; neither would have
blocked `2f787163` (verified `CLAUDE.md` +6, `AGENT_INSTRUCTIONS.md` +4). The gap has an exact
address: `check_trust_boundary_edit.sh` **is** a working authority guard reading
`human_only_paths.yaml`, whose glob list contains neither file. One imprecision:
`claude_accounting_context.sh` *does* match `CLAUDE.md` — it is a context injector that
unconditionally exits 0. Recommend: *"one hook matches `CLAUDE.md` and cannot refuse the edit."*

### One further count that does not hold: F-14's recurrence figure

F-14 is tagged **6 recurrences `bus` after the `2f787163` policy commit (10:28:27Z)**. Three problems:
`2f787163` is the **subagent fan-out** policy (F-15's correction), not a dispatch-depth correction —
the dispatch-depth correction is the coordinator's own, at 10:47/10:55/11:03Z, i.e. *after* most of
the cited instances. The cited items are the coordinator **observing the symptom**, not committing
the failure, and at least two (10:48:13Z *"DEEP QUEUE DISPATCHED"*, 11:01:45Z) are the remedy being
applied. And several cited timestamps live in `adapter-ledger.jsonl` (a nudge-delivery log), not the
bus, while carrying a `bus` provenance tag.

**The phenomenon is not in doubt** — shallow dispatch is established by hardware readings and by the
coordinator's own admission (*"I have been queuing work measured in SECONDS at a card that needs work
measured in HOURS"*). The number is. Same for F-02's `≥4 bus`, whose supporting pointers are F-25 and
F-26, both of which the table itself marks *"caught in-conversation; no surviving artifact"* — a
`bus` tag resting on two `conv.` items.

**Net on §2**: the corrections are, on the whole, more careful than the charges they revise. But the
document's own recurrence column — the one it declares load-bearing — is the least reliable thing in
it, and the two overturned corrections both revise *downward*. That pattern is worth more than either
individual finding.

---

## 3. Per-failure mechanism assessment, with cost

The handoff classes 20 failures as `RECALL`. Cost is expressed as *build + standing friction*.
"Enforcement point" matters more than "mechanism exists": **the only two enforcement points this role
provably passes through are `session_bus.py append` (every message) and `session_bus.py drain` (every
task boundary, Guardrail 1).** Anything hung elsewhere is another rule to remember.

| ID | Mechanism possible? | Where it would live | Cost | Verdict |
|---|---|---|---|---|
| F-01 duty cycle scoped wrong | **Partial** — require a `window` field on any rate | `append` payload schema | Low + low | Build, but **delete first** (§4 D1) |
| F-02 instantaneous sample as rate | **Partial** — same | `append` | Low + low | **Delete** (D1) |
| F-05 git state asserted from memory | **Yes, for the premise** — refuse a payload containing *fast-forward / ahead / behind* without a `receipt` field carrying `git rev-list --left-right --count` output. Not for the verdict: the `auditor` proved by `patch-id --stable` that the *content* outcome was safe, so a guard would have blocked a true conclusion resting on a false premise | `append` | ~40 LOC + negligible | **Build.** Highest certainty-per-line in the table. F-05 is a measurement failure wearing a judgement failure's clothes |
| F-06 post-exit sample | **Partial** — absence claims require `samples_n` ≥ 2 and a window | `append` | Low + low | **Delete** (D1); keep the field for relayed receipts |
| F-09 verification with `2>/dev/null` | **No, generally.** A lint on stderr suppression false-positives everywhere | — | High + high | **Delete** (D4). Verification goes to a subagent whose brief demands a positive control |
| F-12 self-reported busy state as compute | **Yes, as a corollary of D1** | `append` | — | **Delete** (D1) |
| F-14 shallow dispatch | **Weak.** `task-assign` requires `expected_occupancy`. Honest limits: it catches the *second* occurrence by outturn comparison, never the first, and is gamed by writing a large number. The repo has no duration model | `append` | ~20 LOC + one judgement per dispatch | **Build anyway, cheaply.** Not because it detects — the consequence was already visible all morning and F-14 recurred regardless — but because it forces the seconds-vs-hours question at composition time, which is where the failure lives |
| F-16 infra uncommitted on the coordinator's tree | **Yes, free** — `drain` prints untracked/modified counts under `scripts/` | `drain` | ~15 LOC + zero | **Build.** Costs nothing because the role already runs `drain` at every boundary |
| F-18 built agent infra without approval | **Partial.** `observer_census_precommit.sh` now covers watchdogs. A general infra gate is exactly the class the operator has already pulled once | pre-commit | Medium + real friction | **Delete the activity** (D2), do not gate it |
| F-19 auto-loaded surfaces edited without an ask | **Yes, one line** — add `CLAUDE.md`, `agents/AGENT_INSTRUCTIONS.md`, `agents/shared/*.md` to the list `check_trust_boundary_edit.sh` already reads | existing hook | ~1 line + real friction (`22c4aff5` would have been gated) | **Operator decision.** Recommend yes for `agents/shared/*` and `CLAUDE.md`: a wrong premise there is five sessions' truth (F-21's amplifier). *The file is human-amendment-only; this review does not touch it.* |
| F-20 invented roster constraint | **Half.** The *check* is a set comparison against `config.yaml`; the *trigger* is not computable — nothing knows a sentence in a brief is a roster claim. A typed `constraints[]` field with `source: file:line` converts the trigger from prose into structure, which is the only way to get at it | `append` | ~25 LOC + low | **Build**, and note the general shape: repo state can adjudicate almost any claim in this table once something points at the claim; **nothing points at the claim.** That is what typing the payload buys |
| F-21 false premise broadcast | **Half.** `session_bus.py retract --msg-id` can re-derive the original recipient set and fan the retraction. Re-opening the decisions it drove is judgement | `append` / new verb | ~40 LOC + low | **Build the fan-out half.** Say plainly the re-open half will recur |
| F-23 role-shaped dispatch | **Yes** — refuse a `standing` block marked `audience: main` addressed to a non-main | `append` | Low + low | **Do not build.** One instance, no recurrence, and roles are contested (`config.yaml` "READ-ONLY auditor" vs C-OWN code ownership). Resolve the roster contradiction instead; that is the actual defect |
| F-25 dispatch reported as utilisation | **Yes, as D1** | `append` | — | **Delete** (D1) |
| F-26 69-second probe as a measurement | **Yes, as D1** | `append` | — | **Delete** (D1) |
| F-28 asserted where `--dry-run` was cheap | **No.** No predicate knows a claim was cheap to check | — | — | **Judgement. Will recur.** Say so |
| F-29 conflicts left unadjudicated | **Yes, by reuse** — file it as a `decision-request` with `action_required`; the daemon already tracks unanswered ones, and `drain` surfaces them with age | `drain` | ~10 LOC + zero | **Build.** Note a ledger was tried for this and failed (§5) |
| F-30 decision as prose, not options | **No.** The operator is not on the bus (0 of 839 rows); the operator-facing channel is a tmux pane no hook can see, and no predicate distinguishes a paragraph that should have been a decision package | — | — | **Judgement. Will recur.** This is the one the operator is angriest about and it is the one with no mechanism. The only lever is §4 D5: fewer, shorter operator-facing messages, so the ones that are decisions are visible as such |
| F-31 defect-number collisions | **Yes, trivially** — allocate C-IDs from a registry file | a ~30-LOC script | Trivial + zero | **Build.** `mainD` owns the namespace — route |
| F-32 wrap-up incomplete | **Yes, and it deletes a rule** — corrections are bus rows of kind `finding` with a `corrects:` field; the wrap-up's corrections section is then **generated**, not written from memory | `append` + generator | ~60 LOC + zero | **Build.** Removes "remember to write all your corrections down" entirely |

**Summary: of 20, five are judgement-only or should not be built (F-09, F-23, F-28, F-30, and F-18's
general form), seven dissolve into a deletion (F-01, F-02, F-06, F-12, F-25, F-26, and F-09), and
eight have a real mechanism that fits on an enforcement point the role already passes through.** No
new discipline is required for any of the eight. That is the test a proposal has to pass here: if it
adds a step the coordinator must *remember* to run, it has reproduced RC-1 in the remediation.

**Two failures the framing hides, and they are not `RECALL`:**

- **F-24, the `verify_ggml_linkage.sh` remedy, and the still-running supervisor loop (§1e) are
  mechanism defects.** No amount of mechanism fixes them; they are the cost of mechanism, and in the
  supervisor's case the replacement predicate has already reproduced the class. The refactor must
  price them in.
- **`fleet_watch.sh` reproduced F-24 one level up.** It landed at `83f204cf` with the observation
  contract from `ed38041d`, and its own registry row says: `"contract": "unadopted"` — *"Enrolled BY
  HAND: neither discovery rule finds it (it identifies no process by argv, so Rule A misses it, and
  it does not source `observer_guard.sh`, so Rule B does too) — yet it decides whether six mains are
  alive, which is exactly this census's subject."* It is running right now as an **orphan**
  (reparented to the container shim, no nohup wrapper, no cron, no unit, **no restart path**), and
  the running process pre-dates its own commit by eight minutes. The fleet's stall detector is the
  one observer the observation contract structurally cannot see, and nothing will restart it.

---

## 4. What to DELETE

The role's own guardrail names its scarce resource: *"the main thread's scarce resource is attention
to task boundaries."* Measured against that, here is what the role actually spent its attention on in
the surviving 3-hour window (08:22:44Z → 11:29:37Z, 53 outbox messages):

- **110,084 bytes of hand-composed payload prose**, median 2,106 B per message, max 4,333 B.
- **219 distinct payload keys across 53 messages.** Twenty-six appear more than once. Every dispatch
  invents its own field names.
- **35 `task-assign`s and 1 `decision-request`** — while F-30 records a decision delivered to the
  operator as a descriptive paragraph.
- **Zero new brief files.** `coordination/session-bus/tasks/` has had no new file since 08:37Z,
  though the role's own *Outputs* contract says briefs are *"self-contained files under
  `coordination/session-bus/tasks/`, dispatched by a short nudge that points at the file"* — and the
  doorbell redesign (`tmux_adapter.py`) exists precisely so the payload lives on the bus.
- **Five agent-infrastructure artifacts** authored on the thread, one of them self-admittedly *"under
  time pressure, never tested"*.

**Fifteen of the thirty-two failures — 47% — are the coordinator acting as an instrument**: producing
or repeating a number about system state it did not own and had not instrumented (F-01, F-02, F-03,
F-04, F-05, F-06, F-09, F-11, F-12, F-20, F-25, F-26, F-27, F-28, F-29). **The role's mission
statement contains no measurement duty at all.** It accreted, and it is the single largest source of
failure in the table.

### D1 — STOP producing hardware and utilisation readings. *(Highest leverage. Zero build cost.)*

Kills F-01, F-02, F-06, F-11, F-12, F-25, F-26 — seven failures including **the only documented
post-correction recurrence in the file**. The coordinator has no instrument, no window discipline
budget between dispatches, and no ownership of the hardware. `inference` owns compute; `fleet_watch`
owns persistence-gated idle detection; the dashboard plane owns freshness envelopes.

**The coordinator relays receipts. It does not read dials.** A utilisation figure in a coordinator
message must be a verbatim quote with a `source_msg_id` or `receipt_path`, or it is not sent.

**This is not licence to stop reporting idle compute** — idle compute stays a reportable condition
(standing policy). The change is that the *reading* comes from the owner or the watcher and travels
with its provenance; the coordinator supplies the routing and the urgency, which is its actual job.

### D2 — STOP authoring agent infrastructure.

Watchdogs, adapters, hooks, registries. Evidence: F-16, F-18, F-24, and now `83f204cf`'s own
admission. Two independent reasons, and the second is the stronger:

1. It is execution work on a thread whose guardrail forbids execution work, and it produced five
   uncommitted artifacts in a tree where `git clean -ffdx` had already destroyed the bus that morning.
2. **It is a conflict of interest.** The coordinator was writing the instruments that measure the
   coordinator — `fleet_watch.sh` decides whether the fleet is idle, which is the exact question its
   author had been wrong about all night. The one it wrote is the one the census cannot see.

Route to `mainD` (already the C-series namespace owner) or to the operator. **[THIN]** — I cannot
establish who authored `observer_guard.sh` / `observer_registry.json` / the `tmux_adapter.py` diff;
no sound thread-attribution method exists in this repo. `scripts/utils/agent_log.sh` has no agent
field at all, its only non-legacy shard is literally named `agent_audit-unattributed.log`, and it
recorded **zero rows between 10:28Z and 11:28Z** — the window in which all five artifacts were
produced.

### D3 — STOP deriving repository metrics by hand.

Checkbox counts, backlog sizes, changed-path counts, advisory volumes (F-03, F-04, F-27, F-29,
F-20). Canonical instruments exist and are anchored: `index_state.py`, `backlog_row_check.py`.
F-03's whole content is that a hand-rolled `grep` ran beside a shipped parser. **A number that a
committed tool can produce is never typed by hand into a coordinator message.**

### D4 — STOP running verification and reconciliation inline.

F-05, F-09, F-29. The corrections establish that delegation *did* happen for push serialization — so
this is not "never delegates". The residue is that **git state and merge outcomes were asserted from
memory** while the actual work was elsewhere. `merge_gate.py` exists; the auditor's own instruction
survives on the bus at 10:11:39Z: *"re-derive the ahead/behind at push time since origin has moved
under us three times this hour."*

### D5 — STOP writing 2 KB freeform payloads.

219 ad-hoc keys is a dispatch format with no contract, which is why **not one content rule in this
file is mechanisable today**: `session_bus.py` requires only `schema_version, id, ts, from, to, kind`
and leaves `payload` unconstrained. There is nothing to validate. Composing 110 KB of prose in three
hours *is* focused execution work on the main thread, and it is what crowds out attention to task
boundaries. Briefs go in `tasks/` files written by subagents; the payload carries typed fields and a
pointer.

### D6 — STOP self-auditing.

The `Mech` column, the recurrence counts and the eleven corrections were produced by the role about
the role. §2 shows the predictable result: two opposite evidentiary rules for the same signal, each
applied in the direction that favours the role, and the least reliable column is the one declared
load-bearing. The role should file corrections as typed bus rows at the moment they occur (§3, F-32)
and let the `auditor` grade them. **Filing is the coordinator's job; grading is not.**

### What must NOT be deleted

Sequencing, collision resolution, lease grants, decision packages, relaying operator intent,
integration acceptance. That is the mission statement, and the corpus contains no failure attributable
to doing *those* badly — the failures are in the duties that accreted around them.

---

## 5. Why writing it down failed

This is the operator's real question, and the corpus answers it three ways within one morning.

**The live case, unfolding during this audit.** The handoff (11:15:11Z) records a precise correction:
`bus_supervisor.sh`'s comment and `test_bus_supervisor.py`'s docstring both say the restart loop ran
*"every ~10s"*; it was 42s (30s startup timeout + backoff), two attempts, 74 seconds. It names both
files and instructs that they be fixed while landing. As of now:

- `ed38041d` (11:11:33Z) had already **propagated the wrong figure into two new files** —
  `observer_guard.sh:13` and `tests/test_observer_contract.py:9` (*"relaunch-looped every ten seconds
  until somebody"*), plus its own commit message.
- `83f204cf` (11:28:03Z) landed **13 minutes after the correction was committed**, touching the same
  directory, and fixed none of it.
- The error now stands in **five files**, and at `test_bus_supervisor.py:363` it has become
  load-bearing in a test's assertion rationale (*"22s at the old 10s cadence was >=2 and
  unbounded-growing"*).

A written correction, with the right number, the right files and an explicit instruction, did not
survive thirty minutes in its own directory.

**The three properties the written corrections lacked:**

1. **They are not on the path of the act.** Corrections lived in `progress/2026-08/2026-08-12.md`
   §Corrections, in `RESOLUTION-LEDGER-20260812.md` §6, and in the handoff table. The acts are
   composing an outbox payload and typing a git command. Neither requires reading any of the three.
   `5a03e821` states the structural reason in one line: ***"`AGENTS.md` is a symlink to `CLAUDE.md`,
   and `CLAUDE.md` is the only file a main auto-loads — no `@`-imports, no `SessionStart` hook."***
   Everything else is read only if somebody follows a link.
2. **They are narratives of a past error, not templates for a future utterance.** *"Instantaneous
   `rocm-smi` sampling was used as a utilisation measure"* tells you what went wrong; it does not
   tell you what to type when you are about to write *"the GPU is at 0%"*.
3. **Nothing at writing time asked who reads this next, and when.** Three artifacts, three audiences,
   no reader.

**The natural experiment, and the third category RC-1's binary is missing.** One correction that
morning was converted into a **sentence template** rather than a narrative: `a90870ec`'s *Reporting
Units* — *"N records resolving to M distinct rows, of which K were dispatchable at emission."* It has
**no validator** — the handoff says so itself. It is pure prose. And F-04 has **zero** recurrences,
while the narrative corrections beside it, same author, same day, same absence of enforcement,
recurred within the hour. The form propagated into the coordinator's own later messages
(*"811 advisory records resolve to NINE DISTINCT ROWS, all from one handoff file"*, 09:45:12Z;
*"the same reporting-unit error as the 4,602 advisory records"*, 10:21:04Z).

**[THIN]** — n is small and the occasions to violate it were few; this is suggestive, not proven. But
it points the same way as the `~10s` case points in the opposite direction, and it identifies a
category RC-1's mechanism-vs-recall binary has no room for: **an output-shaped rule that changes how
you must phrase the thing you are already writing.** It costs nothing, needs no enforcement, and it
worked on the one occasion it was tried here.

**The durable-ledger answer was tried and it failed in 48 minutes.** `A-7` asks whether a durable
correction ledger is the fix. It was built — `RESOLUTION-LEDGER-20260812.md`, `1764471d` at
08:34:09Z, §6 a ten-row corrections table, §7 defining *"update at every task boundary… Not at
wrap-up. The artifact is the status."* Last write: `6a2a513c`, **09:22:56Z**. By 11:45Z it was 2h23m
stale and knew nothing of `e57a10a6`, `22c4aff5`, `ed38041d` or `83f204cf`. It is referenced from two
active handoffs and **from nothing on any startup path**. R-20's answer is therefore evidenced, not
speculative: **another file is not the fix.** A correction must be a row in the append-only channel
the role already writes at every boundary, or it decays like the last one did.

**And the reason the *operator's* corrections are the least durable of all is structural.** The
operator writes 0 of 839 bus rows. Every operator correction enters through a tmux pane and exists in
exactly one session's context. Its only durable form is whatever an agent chooses to transcribe — and
the transcriber is the party the correction indicts. That is upstream of RC-1 and it is why the
recurrence column, the column the operator says matters most, is unmeasurable today.

**Finally, the thing that makes this a refactor rather than a lesson: the response to the day's
failures was more of what failed.** `22c4aff5` (11:05:56Z) encoded the 2026-08-12 lessons as
**+204 lines of prose across 8 files, of which 0 of 7 rules are enforced by any hook, test or CI
check**. Its one mechanical addition puts `CLAUDE.md` into a link-integrity validator — which checks
that the prose's anchors resolve, and which no pre-commit hook or workflow runs. Six minutes later
`ed38041d` shipped a real pre-commit gate and said in its own header why: *"A rule decays the moment
somebody does not read it; the only thing that does not is a check that runs whether or not anyone
remembers it exists."*

Two commits, six minutes apart, one repository, opposite methods. **Writing it down failed because
writing it down is what the role does when it is out of time — and it was out of time because of
everything in §4.**

---

## 6. Prioritised refactor

Ordered by leverage. Every item names its enforcement point; anything that requires the coordinator
to *remember* a new step is excluded by construction.

### 0. **Urgent, and independent of everything below**

Two live conditions found while auditing, both needing an owner today:

- **`bus_supervisor.sh` is killing healthy daemons in a loop right now** (§1e) — eleven cycles in 35
  minutes, epoch 54 → 64. `STALE_SRC_STATE`'s "restart once per source version" anti-loop guard is
  vacuous in a five-writer tree. This is F-24's class, one predicate later.
- **OBS-3 (HIGH): `scripts/nightshift/inference_guard.sh` fails OPEN** — every failure mode sums to
  0 GB and reports *"No heavy inference detected"*, which can launch the full agent workload on top
  of a live 200 GB inference run.

Neither is the coordinator's to fix (§4 D2). Both are the coordinator's to route, which is the job
this whole review says it should be doing.

### 1. **The coordinator stops reading dials. It relays receipts.** *(D1 — the single highest-leverage change)*

- Removes seven failures including the only proven post-correction recurrence.
- **Zero build cost** — it is a subtraction.
- Enforcement, when wanted, is ~40 LOC at `session_bus.py append`: a coordinator payload containing a
  hardware figure (`%`, `t/s`, VRAM, load average) must carry `source_msg_id` or `receipt_path`.
- **It deletes three prose rules** — R-12, R-14 and R-15 all become unnecessary, because a role that
  quotes only receipts cannot commit a sampling-window error.
- Do it first because it is the only item that pays off before anything is built.

### 2. **Type the `task-assign` payload; move briefs back to files.** *(D5)*

Required fields: `task_text` (verbatim box text, primary), `row_ref` (hint only), `screened_by`
(a `backlog_row_check.py --row` receipt), `expected_occupancy`, `constraints[].source`, and a hard
payload size cap that forces a `brief_path` under `tasks/`. ~150 LOC in a file that already validates.
Closes F-14, F-20, F-22 and F-04's recurrence at one choke point, and **deletes R-3, R-10, R-18 and
half of R-19** from the refactor list. Today none of these is mechanisable, because `payload` has no
schema and there is nothing to check.

### 3. **Hang the boundary checks on `drain`.**

`drain` is documented as *"the one-liner agents run at every task boundary"* and Guardrail 1 makes it
mandatory before every operator response. It is the role's only proven checkpoint. Add to its output:
untracked/modified counts under `scripts/` (F-16), unanswered `action_required` rows the coordinator
owes with their age (F-29, F-32), and the current `fleet_watch` persistence-gated occupancy line
verbatim with its source (D1's supply side). ~100 LOC, **no new discipline**, and it makes RC-1's
"checkpoint at the moment of action" real without inventing one.

### 4. **Corrections become typed bus rows; the wrap-up is generated from them.**

`kind: finding` with `corrects: <msg-id>` and `provenance: operator-verbatim | paraphrase | inferred`.
Written in the same turn the correction is received, before acting. Closes F-32, makes the recurrence
column measurable for the first time, and gives the operator's own corrections a durable form that
does not depend on the indicted party's memory. **Deletes R-20** — the ledger has been tried and
measured.

### 5. **Route agent infrastructure out of the role.** *(D2)*

**Status note first, so nobody redoes landed work:** RC-5's uncommitted-artifact table is stale.
`fleet_watch.sh` (`83f204cf`, 11:28:03Z — landed at 641 lines, not the 4,952 B described),
`observer_guard.sh` and `observer_registry.json` (`ed38041d`, 11:11:33Z) and `bus_supervisor.sh`
(`e57a10a6`, 11:02:31Z, **exactly** +311/−52) are all tracked and clean. **R-1, R-2b and half of R-2
are done.** *(This review does not flip their boxes — the owners do.)*

What remains: `tmux_adapter.py` is still uncommitted and its diff has **grown to +853/−71**, while
the landed `fleet_watch.sh` and the landed `SESSION_LIFECYCLE.md` rule both name its runtime check as
*"the authoritative instrument"* — the enforced layer now depends on the one file still dirty in a
five-writer tree, and HEAD still carries the broken glyph table that made the doorbell 0% operative
(§1c row 4). And `fleet_watch.sh` needs a restart path and a discovery rule that finds it: it is
running as an **orphan** with no supervisor, and its own registry row records `"contract":
"unadopted"` — *"neither discovery rule finds it… yet it decides whether six mains are alive, which is
exactly this census's subject."*

### 6. **Then the cheap specifics**, in this order: F-05's git-state receipt (~40 LOC, highest
certainty per line) · F-31's C-ID registry (~30 LOC, route to `mainD`) · F-21's retraction fan-out
(~40 LOC) · fix the `~10s` figure in all five files.

### 7. **Operator decisions — two, and they are genuinely his.**

- **The instruction-surface gate (F-19).** Add `CLAUDE.md`, `agents/AGENT_INSTRUCTIONS.md` and
  `agents/shared/*.md` to the list `check_trust_boundary_edit.sh` already reads? Recommended **yes**
  — a wrong premise there becomes five sessions' truth. Cost: every policy edit needs a signature;
  `22c4aff5` would have been gated. Default if unanswered: the gap stays open. *That file is
  human-amendment-only and this review does not touch it.*
- **Re-land `03e17111`'s `clean` branch alone?** The guard was reverted because `mainD` found two
  HIGHs in its `checkout` handling — a real defect, correctly pulled. But its `git clean -f` branch
  was not among them, and it would have refused the command that destroyed this corpus 27–47 minutes
  later (§1d). Recommended **yes**, as a narrow single-branch guard with a shell-framing test, owned
  by `mainD`. Cost: one more `Bash` hook and one more idiom that needs `REVERT_VERIFIED=1`. Default
  if unanswered: the tree stays one `git clean -ffdx` away from losing the bus again. **Note the
  honest limit**: it models agent-typed Bash only, so it protects against agents, not against a human
  in a terminal — and who ran the 08:20Z clean is unrecoverable.

### What this refactor deliberately does NOT do

- **It does not build a mechanism for F-30**, the failure the operator is angriest about. The
  operator is not on the bus; no hook can see the pane; no predicate distinguishes a paragraph that
  should have been a decision package. **It will recur.** The only real lever is §4: a role sending
  fewer and shorter operator-facing messages has a chance of noticing that one of them is a decision.
- **It does not build for F-09, F-23 or F-28.** Judgement, one instance, and no possible predicate,
  respectively.
- **It adds no new file for anyone to read.** Every item above lands on `append`, on `drain`, or is a
  subtraction. Given §5, a proposal whose remedy is a document would be the audit reproducing its own
  finding.

---

## Related

- `handoffs/active/coordinator-role-failure-modes-and-refactor.md` (RTG-48) — the subject; audit
  findings appended there under *Audit findings*.
- `agents/coordinator-agent.md` — the role file. §4's deletions are edits to this file.
- `artifacts/operator/RESOLUTION-LEDGER-20260812.md` §6 — the durable-ledger prototype, measured.
- `progress/2026-08/2026-08-12.md:3403-3638` — the coordinator wrap-up and its nine corrections.
- `docs/reference/agent-config/INCIDENT_LOG.md` — INC-20260812-compacting-read-as-idle,
  -dispatch-by-line-number, -post-exit-vram-sample.
