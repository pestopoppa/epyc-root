# CME-7T diagnosis and intervention decision — 2026-10-25

Desk analysis complete; no source change, model invocation, client/server, build, interpreter test, network, shared write, or GitNexus run. Owner applies completion and durable filing. Canonical ROOT `249855e78`, research `e8d57acd4cac73005b56f9b6906d8707552e4727`. Every numeric diagnostic below is an OBSERVATION about the retained serving artifact (CANDIDATE, no protocol-backed efficacy or quality claim).

## Decision

Choose a **stricter, bounded rationale instruction first**, retaining `max_output_tokens=2048`, temperature 0 and existing penalties. The captured failure is visible, schema-requested deliberation inside the JSON `thinking` string, which runs out of budget before closing the string or emitting the action. It is not evidence that `enable_thinking=false` failed to suppress the model's separate reasoning channel. Prompt ambiguity provokes repeated reinterpretation; the schema asks for reasoning with no length bound. These are the observed mechanism and a supported intervention hypothesis, not proof that an instruction will cure it.

Use the adapter's EXISTING configurable `system_prompt` for the next separately granted candidate, with the following exact proposed text (no implementation or deployment claimed):

> Return only the requested JSON object. Keep every free-text reasoning or thinking field to at most two short sentences and 60 words. Choose the action using the supplied state and legal options; do not repeatedly reinterpret the state or invent alternative histories. Complete all required fields and close the JSON object.

This preserves the required `thinking` field and task schema; it neither adds a grading rule nor rewrites past scores. This policy changes the evaluated system, so a future run must name the prompt text/hash and keep the old run immutable. If the official wrapper is used, main should first expose the already-existing system_prompt argument as an explicit opt-in runner parameter; that small runner change is future work, not a diagnosed source bug and not needed to finish this desk decision. Direct invocations already accept `--system.system-prompt` via CL-Bench configuration. Validate flag parsing with fake transport before requesting a model window.

| Option | Evidence and tradeoff | Decision |
|---|---|---|
| Lower cap | Bounds one attempt's cost but ends the same unfinished JSON sooner. In this very run, valid stateful first replies used 1,052 and 1,846 tokens; caps such as 512 or 1,024 would truncate observed successful outputs. | Keep 2,048 initially. Reconsider only after bounded-instruction observations establish successful completion sizes. |
| Repetition penalty | Native sampler logs show repeat_penalty=1.000, repeat_last_n=64, frequency/presence=0.000. Text repeats concepts and state interpretation, with varied language; no evidence a short-window token penalty resolves it. It can also alter legitimate repeated schema keys/actions and poker reasoning. | No blind penalty value. Isolate as a later candidate only if bounded instructions leave this failure. |
| Stricter instruction | Existing JSON-only instruction constrains outer format, not length. PokerAction explicitly requires unbounded reasoning before action; failed content spends its entire budget there. A concise retry already returns valid JSON in 150 tokens. That retry changes context and is not a controlled efficacy test. | Recommended first candidate; efficacy untested. |

## Still-needed audit and scope

Exact open ROOT task begins: **CME-7T — Find why the first call of a run generates the full 2048-token budget (runs 0 and 1 of the 2026-10-22 smoke; run 2 stopped at 199).** It requests capture and a choice among lower cap, repetition penalty or stricter instruction. The child capture box is already completed at research `2f704ba4a`. `e8d57acd` has no later changes to this adapter source; its installed copy currently hashes identically. Do not duplicate capture. The old “waits for CME-7S raw replies” sentence is stale: s2 COMPLETE is `PASS 2026-10-23T00:40:04Z`. This work finishes the remaining diagnosis/decision using that new evidence, while expressly not reconstructing the missing rejected texts of the older 10-22 events.

## Identity: the new runaway belongs to the baseline

Run receipt: `/mnt/raid0/llm/tmp/cme7-poker-out-s2/run-20261023T003634Z/`. CL-Bench group `2026-10-23T00-36-46.051797Z`, upstream clone commit `5f8c50eb1e84b2eda2ef4faff757dfc812a0ea26`. Raw sidecar contains exactly one runaway and a parse_fail for the SAME response (two records, one failed attempt), timestamp `2026-10-23T00:37:52Z`, interaction 1 / attempt 0.

Exact response ID `chatcmpl-6U1HOEz9UlHrOTaX4BK3gy6b51aAO5fs` joins to `baseline.json`, `instance_traces[0].interactions[0].usage.respond.events[0]`, also duplicated in baseline's flattened interaction view. Instance ID `poker:calling_station:hand:stage0_seed42_hand1`. This is the reset-each-instance **baseline**, not stateful run_0000, run_0001 or run_0002. Do not count the duplicate baseline views as independent events.

| Event | Input/output tokens | Cached input | Identity |
|---|---:|---:|---|
| baseline instance0 first attempt | 457 / 2048 | 0 | failed response ID above |
| same interaction retry | 2608 / 150 | 453 | `chatcmpl-676TFzWZubuoELFAuZ2IG7WmhEgghj5d`; successful CHECK |
| next baseline interaction | 980 / 150 | 0 | `chatcmpl-Q0gLkqRNGJkwkKYSirwnHx5YIuJdQaHt` |
| stateful run0 first call | 457 / 1052 | 0 | valid, trace timestamp 00:37:19.932958 |
| stateful run1 first call | 451 / 110 | 0 | valid, 00:36:51.795889 |
| stateful run2 first call | 457 / 1846 | 0 | valid, 00:37:44.410709 |

Thus the new artifact does NOT reproduce “runs0/1 both hit 2048.” It supplies direct text evidence for a surviving first-interaction failure of the same kind. The cache report concerns stateful runs0–2 (14/14/20 calls), not this baseline retry; `history_rewind=0` in that report does not contradict the baseline's 2608→980 prompt shrink. Cache prompt-prefix ratio 0.9977 PASS establishes CME-7S evidence availability, not quality improvement or cure of the runaway.

## Text and schema evidence

Raw content is 6,297 characters, starts a JSON object and a `thinking` string, and never reaches an `action` key. `reasoning_content` is null; `finish_reason=length`, `completion_tokens=2048`. Error: `EOF while parsing a string at line 2 column 6295`. No code fence or outer prose accounts for the failure. Literal backslash-n sequences occur 66 times; `Pot|pot` appears 33 times, `called` 33 times, `look` eight times (case-sensitive native jq scan counts). These are descriptive counts of one reply, not a repetition-effect experiment.

Minimal representative excerpt:

> “Wait, let's re-read carefully.” … “This phrasing is tricky.” … “Is it possible that 'Opponent called your bet of 10' means Tom called the Big Blind? i.e., Tom is Limping?”

The content repeatedly recomputes pot totals and debates whether the blind is an active bet, then approaches the correct limp interpretation but ends `So, Tom Limp` mid-string. It is semantic reconsideration with repeated terms, not just a single token/stanza mechanically copied.

Pinned upstream `src/tasks/exploitable_poker/task.py` defines `PokerAction.thinking` first with description “Your reasoning about the hand situation and why you chose this action,” no bound, followed by action and optional amount. Its prompt chooses “Opponent called your bet of {current_bet}” whenever chips_to_call==0 and current_bet!=0; that includes a posted big blind. At this query: Big blind, J-clubs/7-hearts, pot20, chips990, opponent CALL, chips_to_call0, legal FOLD/CHECK/RAISE, min raise20. A small blind completing to10 plus posted BB10 explains pot20; it need not imply a discretionary new BB bet. The supplied phrase is misleading for this state. It plausibly triggers the visible reconsideration; no isolated prompt ablation proves strict causality. Do not silently patch upstream task text: a wording fix changes the benchmark instrument and should be versioned separately if pursued.

Pinned research `system.py::_schema_instruction` only says JSON-only/conform to schema. `respond()` stores query+instruction once for prefix stability; passes failed reply plus the validation error in ephemeral retry messages; stores only the successful reply. `_chat()` sends temperature0, max_tokens2048, chat_template_kwargs.enable_thinking=false, but no JSON-schema `response_format` or grammar, and no extra penalties. Therefore the server is not enforcing JSON closure or a length limit on the `thinking` field. This is an accurately implemented prompt-only adapter, not a newly established transport/parser bug. A grammar would prevent some format failures but cannot itself make an unbounded string finish before a finite token cap.

## During-event server correlation and pins

`server.log` uses relative process times, not UTC. It does not print this response ID. The match to **slot3/task9** is by the contemporaneous unique first-prompt457/output2048 signature and timestamp ordering, not an explicit ID join. Task9 starts at0:12.971583, prompt457, has repeated DURING progress samples from n_decoded100 at0:16.978186 to2012 at1:15.139373, and completes at1:17.845733 with eval64027.38ms/2048tokens (total64864.60ms). This supports sustained visible generation, not a post-window inference. Slot2/task761 then matches retry input2608/output150: restores checkpoint n_past453; prompt evaluates2155 tokens; output150; total6413.34ms. Server task IDs are never substituted for CL-Bench run IDs.

Startup identifies build10345 (`dd3d9721c`), model `/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, four slots n_ctx_slot196608, MI210/ROCm buffers, chat template thinking=0. Retained linkage receipt binds binary and libraries to `/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c/bin`. Do not relabel this run as frozen production build10303/v10 merely because its recipe was initially described that way. Recipe/job are current retained files, not immutable launch-time manifests. No launch-time executable SHA/model SHA or full installed-source revision manifest is present in this receipt; current source hash equality is corroboration, not proof of historical byte identity. No diagnosis here requires executing that binary, inferring current residency, or adding invented pins.

## Verification and limits

Read-only native git show/rg/cat/sed/jq/sha256sum used; no preflight test was needed or run because no code was edited. One initially over-streaming jq scan command produced duplicated output; corrected array-wrapped scans yielded the single counts above. No duplicate output was treated as an extra reply. Hashes and compact native-extracted joins are saved alongside this report. All task-local artifacts retained for main's durable filing; no worktree or build artifact created.

CME-7T can be completed as a diagnosis/choice task. This does NOT certify a production fix, tested instruction efficacy, quality gain or explanation of every historical 10-22 event. A future granted instruction candidate should retain raw capture, record the exact prompt/hash and model/build/source identities at launch, report stateful and baseline failures separately, count unique response IDs, and compare schema completion and usage before changing the cap or penalties. Higher reward is better; lower runaway/parse-failure incidence and output-token cost are better; avoid accepting a latency saving that merely moves failures to shorter truncations.
