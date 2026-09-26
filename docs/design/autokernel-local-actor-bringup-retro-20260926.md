# AutoKernel local-actor bring-up: a retrospective

**Status:** findings, durable. The practices distilled from it are in
[`docs/guides/agent-workflows/agent-loop-design.md`](../guides/agent-workflows/agent-loop-design.md) →
*Bringing up a new actor model or backend*. The preventive work is filed as `- [ ]` tasks (§6).
**Date:** 2026-09-26 (window 2026-09-23 18:06Z → 2026-09-26 17:51Z)
**Incident:** [`INC-20260926-local-actor-bringup`](../reference/agent-config/INCIDENT_LOG.md#inc-20260926-local-actor-bringup)
**Handoffs:** INF-77 [`deepseek-v41-flash-evaluation.md`](../../handoffs/active/deepseek-v41-flash-evaluation.md)
(DS41-C10, C17, C20-C48), INF-78
[`autokernel-orchestrator-actor-backend.md`](../../handoffs/active/autokernel-orchestrator-actor-backend.md)
(OAB-1..32), [`autokernel-rebuild-program.md`](../../handoffs/active/autokernel-rebuild-program.md) (R23-37, R23-40)
**Why this exists:** operator directive, 2026-09-26: "project knowledge (not just your Claude memories) MUST
learn from" this bring-up.

Sources: git history, committed handoff text, the campaign evidence store, session transcripts and memory
notes. Inferences are labelled. Commits are in epyc-inference-research unless marked *root* or *orch*.

---

## 0. TL;DR

- **It took ~57.5 h from launching the first local-weight planner (09-23 18:06Z) to the first real candidate
  measurement (09-26 15:32Z).** That spanned 11 run/state directories, and 10 of them scored nothing.
- **The model was not the main problem.** Of ~26 distinct failure incidents, ~11 were opencode harness
  semantics and ~12 were latent AutoKernel or harness bugs that the local model's longer, more numerous calls
  exposed. ~3 were model capability and ~4 were process mistakes. The categories overlap a little.
- **Most of it could have been caught for zero GPU time** by a fake-model wire test of the exact actor
  invocation, plus a stub end-to-end dry iteration that exercises stop, resume, kill and continuation after a
  keep. The same scripted-fake-server technique later found the 14:52Z critic-permission bug in minutes.
- **The first locally-authored keep:** `akm-ds41-gemm4xn-2x-unroll`, +4.535% on the paired A/B. It is not yet
  confirmed at serving (§3).
- **Two latent bugs were still live when this was written.** An experimental CPU campaign cannot continue past
  its first keep (DS41-C45, fix in progress). Keep anchor builds run at `-j1`, which costs ~1 h per keep with 95
  cores idle (DS41-C46).

## 1. Had a local model ever run in the AutoKernel loop before?

**No.** Every AutoKernel actor from the loop's start through 2026-09-23 was a cloud model:
- Claude Fable 5.1 through the `claude` CLI, plus `gpt-5.6-sol` through `codex exec` (`f81bbeb6`, 09-03);
- Opus 5 (`1ffe4fdf`, never launched);
- DeepSeek V4 Flash through opencode, calling an external API (`c2bfe916`, 09-03);
- then back to codex + Fable (`81bd756c`, 09-07).

`loop/actors.py`'s `Backend.kind` only ever distinguished `codex | claude | opencode`. That is a transport
choice, not a locality one.

The DS41 campaign then swapped the planner twice in about 15 hours:
1. **09-23 18:06Z:** the live production CPU frontdoor, `opencode:qwen-local/qwen3.8-flash-next@high` on
   :8074. It produced two proposals, taking 97 and 41 minutes. `ef287ba9` (09-24 01:13Z) had to widen the actor
   timeout, which assumed cloud latency.
2. **Run 7, 09-24 09:10Z:** the GPU `qwen-gpu/qwen3.8-27b` on :8083 (DS41-C17). Most of the friction below
   happened on this seat.

Local models were used heavily elsewhere, but never in the shape AutoKernel needs. Autopilot scores single-turn
or short-REPL proposals inside orchestrator-owned gates. The orchestrator's `ARCHITECT_MODES = {"direct",
"delegated"}` (`seeding_types.py:379-386`) excluded REPL agentic use for this same 27B until an INF-78 scoped
exception landed on 09-25. That was one day *after* AutoKernel had run the model agentically for 24+ hours
through a third-party CLI the orchestrator does not gate.

The only planned local-model reasoning validation, `architect-model-selection-bench.md`, was gated and never
run. *Inference, absence-of-evidence:* a grep of `epyc-orchestrator/src/autopilot_core/*.py` finds no
local-model-as-agentic-actor path.

## 2. Failure classes, chronologically (UTC)

| When | Symptom | Root cause | Cost | Fix |
|---|---|---|---|---|
| 09-23 18:06 → 09-24 ~01:00 | CPU planner (:8074) made 2 proposals, taking 97 and 41 min | The actor timeout assumed cloud latency. Local decode is slower, and prefill dominates on large tool output | 2 calls, ~2.3 h, then swapped for the GPU 27B | `ef287ba9` (`--actor-timeout-s`) |
| 09-24 09:16-09:55 (run 7) | First 27B proposal discarded whole. The repair then invented a stand-in file (`src/verify/replay.ts`) | `_run_agent` discarded any rc≠0 reply unread, and opencode exits 1 after a recovered internal tool error. The repair ran over an empty retry with no report to ground it | ~39 min; iteration 0 lost | `e9495971` → `21ca61b0` (DS41-C20) |
| 09-24 (run 7) | A ~100 KB prompt came near opencode's 128 KiB argument limit. 2,982 quotes were re-escaped. Long replies were cut off by the pipe (65,536 or 98,304 bytes, against 328,871 via a file) | The prompt went through argv, not stdin, and opencode/Bun does not drain a pipe on exit | Any long call could silently lose a real reply | `e9495971` (stdin prompt, file capture, prompt cut from 95.7k to 75.9k chars) |
| 09-24 (bounded seat v1) | 12 steps at 1,626 decoded tok/step (266 on the plain seat), context full at step 12, no hypothesis | The agent's `prompt:` config **replaced** opencode's terse system prompt instead of appending to it | ~35 min arm wasted | Config v2 uses `instructions`, not `prompt` |
| 09-24 ~10:17 (run 7 halt) | TERM did not stop the run, and `run.py` respawned a TERM'd actor | SIGTERM drains. A planner or critic call IS the stage, and the in-flight actor never checked `should_stop()` | Manual TERM+KILL. Run 3's planner had earlier survived a stop by 65 min | `1c7d0a2d` (DS41-C22) |
| 09-24 09:42 (run 7) | The 27B overflowed its 98,304-token slot at ~45 steps, and opencode self-compacted, losing detail each cycle | `-c 196608 -np 2` gave split KV, so 98,304 tokens per slot. The opencode conversation is append-only | Every arm of the later A/B compacted at least once | `-kvu` (RTG-57); structural fix INF-78 OAB-7 |
| 09-24 12:00 (run 7) | `symbol_annotate` reported "no samples" on a populated profile | perf matches the full demangled name, and the planner typed the short name | 2 wasted profiling calls | `1c7d0a2d` (DS41-C23) |
| 09-24 13:07 → 15:32 (run 8) | Run 8 stopped at 0 measurements, and a ~2 h calibration was discarded | `run.py` held every CPU region lock through the full-target floor calibration, which timed out the production frontdoor's `/chat` | ~2.5 h of calibration | Relaunched as run 9 (DS41-C25); open gap DS41-C26 |
| 09-25 01:30-07:15 | A misread `touch STOP` killed run 9b (it was meant as a batch-boundary drain). The relaunch was held for an invented "off-hours" rule | `STOP` forwards SIGTERM immediately. The "protect the daytime frontdoor" rule contradicted the operator's standing "nothing else uses this compute" | ~2.5 h of idle CPU and 1 discarded planner call | Operator ruling 07:15Z: never idle; use `pause`/`--rounds`, not `STOP` |
| 09-25 07:59-08:47 | An author call died in 6 s: "Failed query: insert into project…" | The event reaper's no-op VACUUM of the 10.8 GB `opencode.db` held a 34 s exclusive lock, and opencode's 5 s busy_timeout expired. A completed critic reply was attributed to the wrong session | ~1 h; metrics corrupted until fixed | *root* `9177edaa`; `e57e93ea` (`snapshot:false`, `opencode_store_error`, session-scoped metrics) |
| 09-25 (runs 3-9c) | Every Q4/Q5 dot-kernel candidate was silently dropped by `gates.op_scope` before the build, with no disposition | The gate required `unpack_q4_scales*` markers that exist only in another tree. **0 of ~15 attempts ever built**, and this predates the local switch | 15 attempts of author work | `c7215eb5` (DS41-C29): gate widened, every abandonment logged |
| 09-25 10:53-14:40 (run 9d) | A resumed build hit `RatchetRefused`, and a ~4 h calibration was discarded on kill | The resume path re-retained a patch that was already retained, so the new sidecar diverged from the immutable stored one | ~4 h of calibration | `71c46655` (DS41-C31) |
| 09-25 ~11:17 | `enable_thinking` and `reasoning_effort` never reached the planner, and `--planner-effort high` was a no-op | opencode sends `chat_template_kwargs` only for models it flags as reasoning-capable, and the local provider is not flagged. There was also no output cap: one turn wrote 30,447 tokens | Silent for ~1 day | OAB-20..22; kwargs injection `fcf0be97` |
| 09-25 (OAB-9) | Context-as-files halved the first-step context but **raised** wall time (+45% and +17%) | A thin prompt made the 27B explore more. The RLM benefit needs a scaffold that pulls context precisely | 2 GPU-hour pairs | Inline context stays the default |
| 09-26 ~06:18-10:55 (run 10g) | The planner abstained for **13 straight batches**, citing a "~220 GB/s" read ceiling | Stale seeded evidence from before the 2026-09-21 BIOS/config change. A fresh `bench_readbw` measured 399.6-449.4 GB/s full-screen | 13 batches, ~4.5 h | DS41-C36 (remeasured, inbox corrected); freshness gate DS41-C48 |
| 09-26 (run 10g) | With thinking off, the author wrote 5 AVX-512 patches the critic rejected. With thinking uncapped, it deliberated for 74k tokens and made **zero edits** | No compile sandbox before the critic. The author had neither forced thinking nor an action rule | 5 rejected patches and one 74k-token call | `fcf0be97`; `5175633d` (OAB-25, `ak-check`) |
| 09-24 → 09-26 | opencode **silently clamps** `max_tokens` to 32000 | Undocumented behaviour. The fix is `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX` | Every larger output budget was inert for ~2 days | `fcf0be97` (OAB-24) |
| 09-25 → 09-26 | One planner call ran for 61 min of small turns and never replied | There was no per-call token or wall budget | ~1 h | `eeab67ba` (OAB-23, planner only; every backend is OAB-32) |
| 09-25 → 09-26 (recurring) | Abandoned candidates silently dropped. Empty author reports lost. ACCEPTED hypotheses discarded on authoring failure | Recoverable failures were treated as unrecoverable | Unknown number of accepted hypotheses | `c7215eb5`, `7b076f8d`, `1848ba08`, `2a66c211`, `71c46655`; test OAB-31 |
| 09-25 → 09-26 | Swapping the actor model or config orphaned queued checkpoints and the planner's do-not-repeat history | Resume and history comparability were bound to the full epoch, which includes the actor roster, not to the measurement identity | Root cause of much of the discard class | `f0349c4b`, `136ad3d0`, `3cbdccea`; ratified `P-AK-SEARCH-1-A3.1` (*root* `1680efbb`); code DS41-C44 |
| **09-26 13:37** | A widened CPU route resolved to op_scope `unresolved` | The route lookup required exact planner-written symbols (`tinyBLAS_Q0_AVX<...>::gemm4xN (template body...)`) | Candidate refused before build | `77f8bf58` |
| **09-26 14:01** | `oracle_unavailable`: the independent CPU quant/GDN reference probes failed with "cannot execute cc1plus" | The harness compiled its **own** reference probes under the candidate's launch env (an allowlist with no PATH) | Candidate refused at the oracle | `7037165f` |
| 09-26 ~14:52 (runs 10h and 10i) | Critic pass 1 was lost repeatedly: a read-only opencode session **ended with no final text** | Without `--auto`, opencode auto-rejects any `ask`-class permission (`external_directory`, `doom_loop`, `.env`) *and ends the session*. A configured `deny` only fails that one call. This was verified against a scripted fake model server | Lost critic passes on 2 runs, on the critical path | `b8d6a046` (deny with an allowlist, `CRITIC_NEVER_ASK`) |
| 09-26 ~15:03 | A refused resumed checkpoint fell through to the planner, which abstained | `_iterate`'s schedule was a fixed `[resume]+fresh`, drawn once per pool | 1 batch | `2a060a41` |
| 09-26 (same window, unrelated to the switch) | `campaign_cli --verify-artifacts` ran twice for an actor-only change, each time re-hashing the 519 GB model | Wrong verification scope for the change type | ~5.5 h | Process rule recorded |
| **09-26 15:31-15:32 (run 10i)** | **First real measurement.** `akm-ds41-gemm4xn-2x-unroll` passed critic 2 and every gate at 15:31Z, and entered a full-screen paired A/B at 15:32Z | All of the above had landed in the previous ~3 h (six lanes `d643d794`, then `fcf0be97`, `77f8bf58`, `7037165f`, `b8d6a046`, `2a060a41`) | — | DS41-C39 ✅ |
| 09-26 (keep) | Each keep's anchor build runs at `-j1` | R23-40 fixed HIP `-j64` non-reproducibility (`f4f13116`) and applied `-j1` to every campaign. gcc reproducibility at `-j64` was never checked | ~1 h per keep on a CPU/gcc campaign, with 95 cores idle | Open: DS41-C46 |
| **09-26 17:51** | The next batch after the keep refused: "restored champion of record differs from current anchor" | Experimental CPU continuations never carry `cor_anchor`, so **an experimental campaign cannot continue past its first keep** | The campaign halts at every keep | In progress: research lane `lane/ak-cor-continue-20260926` (DS41-C45) |

**Campaign-store ground truth** (`/mnt/raid0/llm/tmp/ak-ds41-cpu-decode-20260923/store/experiments.md`, 45
records from 09-25T18:49Z to 09-26T14:27Z, **no keeps** before run 10i):

| Outcome | Records |
|---|---|
| abstained | 22 |
| planner_transient | 6 |
| patch_rejected | 6 |
| stopped_mid_formation | 4 |
| gate_refused | 2 |
| scope_blocked, resume_rejected, patch_rounds_exhausted, hypothesis_rejected, authoring_failed | 1 each |

## 3. The first keep, and its caveat

Run 10i produced the campaign's first locally-authored AutoKernel keep.

- **Candidate:** `akm-ds41-gemm4xn-2x-unroll`, a 2x unroll of tinyBLAS `gemm4xN`.
- **Planner:** `qwen-gpu/qwen3.8-27b`, local.
- **Author:** best-of-2 on the same local model. The winner was `a0-off` (thinking off): 11 steps, and
  `ak-check` op-test PASS.
- **Critic:** external `deepseek/deepseek-flash`.
- **Timeline:** passed critic 2 and every gate at 15:31Z, then a full-screen paired A/B from 15:32Z.
- **Verdict:** KEPT at **+4.535%** (batch-000001, 204 min).
- **Accumulated standing:** the keep's accumulate bench recorded **+7.304% compounded** against the champion of
  record. The anchor advanced from `00d118d44876` to anchor-gen-001, `cafb59c3bf67`.
- **Variance caveat.** The keep's anchor-guard A/A measured **+19.443%** between two builds with **identical code
  digests**. The loop records this as an "R21-10 instrument excursion". A same-code A/A four times larger than
  the keep's own delta means the serving measurement's variance is not yet characterised on this campaign. The
  serving gate is the real confirmation. It fires at 13.81% compounded, or every 4 keeps. Until then, quote the
  keep as "+4.535% paired A/B, unconfirmed at serving" (DS41-C47).

## 4. Attribution (~26 incidents; rough counts; categories overlap)

- **opencode harness semantics, ~11.** Argv re-quoting, pipe truncation, `prompt` replacing the system prompt,
  compaction template echo, good stdout discarded on exit 1, append-only context forcing compaction, the
  undocumented 32k output clamp, the reasoning-capability allowlist excluding local providers, the SQLite
  VACUUM lock collision, and the session-ending permission `ask` path. None of this is model-specific: it hits
  any model driven through opencode this way.
- **Latent AutoKernel and harness bugs, pre-existing and exposed rather than created, ~12:**
  - the stop/orphan-actor race (C22);
  - the op_scope marker gate (C29), which predates the switch;
  - the resume `RatchetRefused` (C31);
  - epoch/resume identity (OP-60);
  - the discard-on-recoverable-failure family;
  - resume-queue scheduling (`2a060a41`);
  - exact-symbol route lookup (`77f8bf58`);
  - reference probes in the candidate env (`7037165f`);
  - the refused-resume fall-through;
  - experimental continuation past a keep (C45);
  - the `-j1` CPU anchor build (C46);
  - calibration ignoring stop (C26).

  Shorter, rarer cloud calls had seldom exercised these paths.
- **Local-model capability, ~3.** Slow, prefill-bound CPU decode. Verbose, undirected reasoning with no natural
  stopping point (74k tokens, zero edits). Never using the fan-out tool it was offered (0 scouts in 69+ steps).
- **Process and operator mistakes, ~4.** The mid-calibration stop that blocked the frontdoor, `STOP` misused as
  a drain, the invented "off-hours" hold, and the redundant 519 GB `--verify-artifacts` re-hash.

## 5. What would have caught most of it before going live

These are the checklist in
[agent-loop-design → *Bringing up a new actor model or backend*](../guides/agent-workflows/agent-loop-design.md#bringing-up-a-new-actor-model-or-backend).
In short:

1. **A fake-model wire test of the exact actor invocation** before any real inference. Check that:
   - stdout survives to a file at full length;
   - both exit-code paths are handled;
   - a compaction echo is not parsed as an answer;
   - the timeout covers a slow reply;
   - permission semantics hold: `ask` vs `deny`, with and without `--auto`.

   This alone covers most of the opencode bucket.
2. **A stub end-to-end dry iteration.** Kill mid-formation, kill mid-calibration, `touch STOP`, resume after a
   mid-build kill, **and continue past a keep**. This surfaces C22, C26, C31 and C45 in seconds.
3. **"Never silently discard produced work," enforced by a test.** Every drop writes a disposition record. The
   discard family was the costliest and most-repeated class, and C29's 0-of-15 went unseen for seven runs.
4. **Key comparability on the measurement identity, not on the actor roster, from day one** (A3.1).
5. **Explicit per-call token and wall budgets for "free" local compute.** A cloud API's cost made the budget
   implicit.
6. **A freshness check on seeded numeric evidence.** Re-measure host ceilings after BIOS or config changes
   before they can drive abstention.
7. **The harness's own reference probes must run in the candidate's launch env.** Test this.
8. **Gate agentic local-model use the way the orchestrator already gates it.** *Not filed as a separate task:*
   INF-78's objective is to move AutoKernel's actors behind the orchestrator, which carries that gating, so a
   second gate in the loop would duplicate it.

## 6. Where each prevention is filed

| Prevention | Task | State |
|---|---|---|
| Fake-model wire-test harness as a standard gate for any new actor seat | INF-78 OAB-29 | open |
| Stub end-to-end dry iteration, including stop/resume/kill and continuation after a keep | INF-78 OAB-30 | open |
| Discard-invariant test with a mandatory disposition record | INF-78 OAB-31 | open (partial: `c7215eb5` logs op_scope abandonments) |
| Default per-call budgets on every backend and every role | INF-78 OAB-32 | open (planner only: OAB-23) |
| Experimental CPU campaign continues past a keep (`cor_anchor`) | INF-77 DS41-C45 | in progress, `lane/ak-cor-continue-20260926` |
| gcc `-j64` anchor-build reproducibility; allow parallel CPU anchor builds if proven | INF-77 DS41-C46 | open; HIP stays `-j1` (R23-40/R23-41) |
| Re-confirm the +4.535% / +7.304% keep at the serving gate | INF-77 DS41-C47 | open |
| Freshness gate on seeded numeric evidence in the campaign inbox | INF-77 DS41-C48 | open |
| Comparability on the measurement epoch | INF-77 DS41-C44 | in progress (ratified A3.1) |
| Reference probes in the candidate env | `7037165f` | done |
| Binding rule: no new actor seat runs live before its wire test | `scripts/operator/ratify_actor_seat_wire_test_20260926.sh` | awaits operator (human-only path) |

## 7. Sources

- Git, research: `e9495971`, `704ef037`, `ef287ba9`, `1c7d0a2d`, `21ca61b0`, `ce5800cb`, `0bf2d7c2`,
  `f4a5d240`, `751ec730`, `e57e93ea`, `bdd0a951`, `eeab67ba`, `fcf0be97`, `5175633d`, `d643d794`, `77f8bf58`,
  `7037165f`, `b8d6a046`, `2a060a41`, `f0349c4b`, `136ad3d0`, `3cbdccea`, `c7215eb5`, `7b076f8d`, `1848ba08`,
  `2a66c211`, `71c46655`, `f4f13116` (R23-40 `-j1`).
- Git, root: `9177edaa`, `1680efbb`.
- Git, orchestrator: `9124c7f1`, `88e22777`, `7d0ce447`, `86cdeaf3`, `b9e004e3`.
- Progress: `progress/2026-09/2026-09-23-main-dsv41.md`, `progress/2026-09/2026-09-26-ak-ds41-main.md`.
- Campaign store: `/mnt/raid0/llm/tmp/ak-ds41-cpu-decode-20260923/store/experiments.md`, and
  `state-run10i/.../actor-replies/{actor-calls.jsonl,author-panel.jsonl}`.
- Working draft this doc supersedes: `/mnt/raid0/llm/tmp/ak-local-planner-retro-20260926.md`. It was corrected
  here: the draft called 15:05-15:32 "the first keep", when 15:32Z was the start of the measurement and the
  keep verdict came from batch-000001. This doc also adds the 13:37Z, 14:01Z, 17:51Z and `-j1` rows.
- Two claims rest on absence of evidence or on a secondary summary rather than a primary line: §1's "Autopilot
  never runs a local model agentically", and the exact time of the DS41-C17 swap.
