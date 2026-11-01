# REPL prefix junction checkpoint: source-derived experiment contract

Source inspection only, 2026-11-01. The inspected frozen llama.cpp tree was at
`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`. This is not a runtime measurement
or proof that any serving binary contains the inspected code. Bind the tested
binary to the frozen build manifest before interpreting the run.

The chat request adapter sets `message_delimiters` from the applied chat
template, overwriting a client field (`tools/server/server-common.cpp:1116`).
`common/chat.cpp` can derive user/assistant delimiters from the actual template,
while specialized and pure-content paths may behave differently. Therefore a
client-provided delimiter or a separated message alone is not proof that the
server recognized a boundary. The completion task tokenizes the effective
delimiters and uses them to find message spans (`server-context.cpp:4430`).

The checkpoint path requires a nonzero checkpoint limit, a completion task, and
a qualifying sequence-removal or SWA state (`server-context.cpp:3562`). Prompt
batching may break at recognized user starts (`:3640`); it then determines
whether the next batch begins at a user start (`:3674`) and creates an eligible
checkpoint before that batch is decoded (`:3696-3725`). Additional guards
include position validity, multimodal state and spacing. Consequently, the
intended junction must be **the recognized start of the volatile user message**;
placing an arbitrary delimiter between text blocks does not establish this.

Before interpreting a junction arm, the harness must fail closed unless it has:

1. The exact applied chat template and effective user delimiter plus rendered
   prompt/token spans, demonstrating that the first volatile user-message start
   is the intended stable/volatile boundary. Preserve any template role tokens
   in the comparison; do not claim a byte-identical prompt if they differ.
2. The actual owned server binary identity and checkpoint configuration, model
   identity, and run-specific slot isolation/reset receipts.
3. Runtime evidence, bound to the same request and slot, that a context checkpoint
   was created at the intended token boundary; distinguish context checkpoints
   from speculative decoding checkpoints. A configured boundary is insufficient.
4. Paired per-turn native `cache_n`, `prompt_n`, and `prompt_ms`, and a separately
   measured closed-loop task-quality gate. Count failures and missing evidence as
   inconclusive, not zero cache or a pass. Record last-turn prompt size for the
   append-state arm.

Compare the junction arm to a no-junction stable-order control under matched
model, tasks, sampling, slot-reset and execution conditions. Since chat message
framing can change the prompt and behavior, record that difference and do not
attribute any accuracy change solely to checkpointing. This contract does not
specify an effect-size threshold or claim a ready-to-publish inference row.
