# CF-3c paired continuation diagnostic

**Status** Prospective, 2026-11-18. Category CANDIDATE, instrument class
`bench`.

Can the same frontdoor model serve four deterministic history policies
as intended, and do their byte differences show up in native prompt
tokens and exact receipt recovery? The pilot replays synthetic archived
tool-call histories against a private frontdoor CPU server. Each history
uses real structured assistant, tool and user messages, with synthetic
observations and historical reasoning and one live final continuation.
This exercises the request-history representation and serving template.
An end-to-end agent trajectory or production latency study would require
separate workloads. Each policy makes zero model calls.

The source pin is orchestrator `12afe2858f9dbd4691447926d6cf1864de64348c`.
Its `src/api/routes/openai_compat.py::_compressed_history_dicts` normally
dispatches B2 on more than eight history messages before flattening. The
pilot calls its actual `src.context_compression.ContextCompressor` on that
structured prefix, excludes the final user question from the transform
and sends the selected structured history directly to the private model's
OpenAI-compatible API. This isolates the transform and template from
orchestrator routing and flattening. The route’s history serializer drops
standalone `reasoning_content`; the replay adds this field deliberately to
exercise the A3 candidate. The repository and production flags require
no modification.

| CF-3c arm | Frozen policy |
| --- | --- |
| A0 | Replay the unmodified full history. |
| A1-k4, A1-k8, A1-k12 | Production `ContextCompressor` with `tool_output_age_threshold` 4, 8 and 12 respectively. Preserve its first-three/last-five protected zones and actual pair-boundary alignment and sanitization. The threshold counts middle-zone assistant-toolcall and tool messages together. Once the count meets the threshold, the compressor applies its stubbing policy to all eligible middle-zone observations. |
| A2 | Mandatory observation-truncation anchor. Retain the newest three observations verbatim and truncate older ones to the first 180 characters plus a marker. Preserve reasoning and native tool pair metadata. |
| A3 | `keep_k_latest_wo_reasoning`, with three latest nonempty historical assistant reasoning/text entries retained. Put `omitted` in older nonempty assistant reasoning/text fields. Preserve observations and tool calls. This isolates the deterministic transform described in the ContextRot local-search code and caps the task with an explicit NA rule. |

[ContextRot deterministic transform](https://raw.githubusercontent.com/GAIR-NLP/ContextRot/a993e8104d523e9dc6227c688df3bd1b0e5f5c29/localsearch/src/agents/keep_k_latest_agent_wo_reasoning.py)

Three task histories have 6, 8 and 10 archived tool interactions. Their
middle-zone counts are 5, 9 and 13, respectively, so each k first activates
in a different fixture. The exact receipt appears once in the tool history,
either deep in an older observation, at the head of an older observation,
or deep in a recent observation. Historical reasoning contains no receipt.
Prepare generates each 64-bit receipt, decoy and case seed once and seals
them. The six arms share one seed within each task and rotate the arm order
by task index. There are 18 official cells.

Run Qwen3.6-35B-A3B-MTP Q8_0 on four allocated physical cores using the
frozen CMP-4 v10 CPU build, terse template, split Q8 KV and one private
loopback listener. The harness uses that pilot's prior verified model
receipt and rechecks the model identity by stat and the template and
production CPU libraries by digest. Model weights are never reread.
Keep temperature 0.3, disable prompt caching and new reasoning, and
preserve historical reasoning in the template so A3 must act on its own.
Each cell renders using the server's native template and tokenizes the
rendered prompt before making at most one completion with a common
12,288-token context allowance and 96-token decode cap. A completed
request must reconcile actual native prompt and completion tokens with
this preflight and cap. The native rendered prompt must agree with the
policy-selected observation head/tail markers, assistant reasoning
markers and exact receipt exposure.

Capture the original messages, transform receipt, native template and
tokenizer requests/responses, completion request/response, and trajectory
with schema `epyc.cf3c.native.v1`. The trajectory binds the source/packet
digests, task, arm, seed, limits, usage, finish reason, wall and status.
A complete or partial window receipt binds the process, serving evidence,
native cell files and matrix. Record startup independently. In each arm
report exact matches per attempted cell and accuracy among graded outcomes, the scheduled and
attempted denominators, NA/UNKNOWN and abstention counts, native total
tokens among cells with usage, and wall per attempted cell from transform
through custody and grading. Wall includes native template/tokenizer
overhead. Retain paired cases and per-cell native timings.

A context that cannot reserve the decode allowance or a `length` finish
is budget exhaustion and scores NA. An unexecuted tool request is NA
and counts as non-termination. A stopped response containing the
literal `UNKNOWN` is an abstention. Missing native evidence and transport
failures receive UNKNOWN. Any instrument failure stops the window.
Report all 18 scheduled cells, with unattempted cells labeled. Preserve
partial custody on keeper STOP or deadline.

Publisher smoke exercises all six native render/tokenizer paths on the
longest history and one actual A0 completion to exercise the longest prefill, verifies the listener
exits, and keeps those artifacts outside the official matrix. The
official run stops at 18 attempts, an instrument failure, keeper STOP
or a 3,600-second window cap. Each cell has a 180-second maximum and
one sampling opportunity. These are planning bounds. A clean complete
matrix qualifies the instrument for this diagnostic. The expected
effect is a detectable native token reduction where the policy changes
the history. Three synthetic histories and one seed per history cannot
resolve the 1-percentage-point adoption margin. The dataset and stop
rule support an activation and evidence-custody screen only.
