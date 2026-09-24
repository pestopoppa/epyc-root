# 2026-09-24 — speech vision alignment and the conversation-stack handoff

Ad-hoc operator session with no roster lane. The work was done in the dedicated worktree
`/mnt/raid0/llm/worktrees/speech-conversation-stack-20260924` on branch `lane/speech-conversation-stack-20260924`, cut from
origin/main `c63f4863`.

## What happened

- **Audit of the operator's draft.** The draft ("Speech-Native Interlocutor + External Orchestrator", Step-Audio 2 mini
  as a resident interlocutor with the orchestrator as its only tool) was checked against the host, the code, prior
  research and primary sources. Four read-only investigations ran in parallel.
- **Findings.** The architecture principle holds. Several premises do not:
  - one MI210, not two (0.9–1.9 GiB free);
  - Step-Audio 2 mini runs at 31.25 decode steps/s (TA4), not 25;
  - decode-usable CPU bandwidth is about 150–220 GB/s, not 460;
  - issue #86 shows no ROCm inference;
  - there is no mini tool-call benchmark;
  - there is no runtime for the model on our hardware;
  - the orchestrator has no voice path, real streaming or conversation store.

  KAME's near-zero latency depends on a retrained front-end.
- **Operator decisions D1–D12:**
  - a bake-off, Step-Audio 2 mini against Qwen3-Omni-30B-A3B, with the cascade as baseline;
  - English mandatory and Italian strongly wanted;
  - placement decided by measurement, operator leaning GPU;
  - production on a llama.cpp port;
  - the controller forces substantive turns to the orchestrator;
  - a dedicated voice-turn contract;
  - the client deferred, with remote laptop/phone access as the end state;
  - the cascade kept as fallback.

  A second MI210 arrives within about a month. It is planned for 35B-A3B and possibly the speech plane, and it serves
  as the bench first.
- **Filed** [`handoffs/active/conversation-stack.md`](../../handoffs/active/conversation-stack.md) as INF-79: 44 tasks
  in 8 phases plus absorbed items. The operator draft is preserved at
  `docs/reference/speech/speech-native-interlocutor-operator-draft-20260924.md` with a correction banner.
- **Moved in** from `multimodal-pipeline.md` (INF-41): S-14, the Qwen-Audio-3.0 watch, and the stale Path-C boxes
  (closed as superseded). The S-11a standing rule and the cloning guardrail are carried. INF-41 keeps vision, and its
  Next action is refreshed to S-16.
- **Cross-reference added** to KVU-11b (RTG-57), which said the voice handoff "did not exist".
- **Belief kernel:** a prospective source row in `scripts/vidya/adapters/README.md` plus the task VB-SPEECH-CONV-1,
  filed before any run.

## Not done here (by design)

- CS-1 research intake (needs operator deep-dive selection).
- CS-2 Annex S amendment (human-only).
- All build work. The operator does not need the build-out soon.
