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

## Wrap-up (operator-invoked, 2026-09-24)

**Checklist sync.** Three `[x]` boxes (CS-0a/b/c) record this session's completed work in `conversation-stack.md`. Also:
- `multimodal-pipeline.md` :666, the moot Qwen3.5-Omni cost box, is closed as superseded.
- The earlier commit already closed or moved S-14, three Path-C boxes and the Qwen-Audio-3.0 monitor hook.

**Derived-actionables sweep.**

Filed (4):
1. CS-12 now fixes the stale "HIP/gfx90a, MI210" speech registry descriptions and the "GPU (MI210)" dashboard label.
2. CS-5 notes that the vLLM docker image bundles ROCm 6.4.1 while the host runs 6.2.
3. `heterogeneous-slot-fabric-residency.md` has a correction: its premise that "the orchestrator already stores the transcript" is false for /v1. The store is filed as CS-15.
4. `multimodal-pipeline.md` S-17 notes that its budget figures are stale and points to the current audits.

Explicit declines (3):
- INF-22 P2-9 ("whisper as a GPU tenant") is **not ticked**. Events have overtaken it, but it is another owner's box. It now carries a cross-reference note for its owner to close.
- S-16 and S-17 stay in INF-41 (vision / GPU budget).
- Kimi-Audio and Unmute stay out of the bake-off, recorded under *Not filed here*.

**Index.**
- INF-79 row added and INF-41 re-pointed (previous commit).
- No prune candidates (`index_state` screen: 0).
- No compaction: `conversation-stack.md` is new, and `multimodal-pipeline.md` gained a "speech moved" banner rather than a split.

**Wiki compile.** The whole delta was compiled: 13 sources into 8 pages.
- `multimodal`: the speech-native interlocutor section, the KAME revival gate (c) marked met, and the whisper.cpp WER corrected from 2.35% to 3.37%.
- `autonomous-research`: the reduced-scope planner build.
- `context-management`, `agent-architecture`, `tool-implementation`, `llm-prompting`: context as files, the metrics sibling schema, the perf cache, planner prompt lessons.
- `knowledge-management`, `benchmark-methodology`: belief-kernel wiring, including VB-SPEECH-CONV-1, and recording rules.

Lint gives 0 errors (87 warnings, all pre-existing). cite-check exits 0. The watermark is advanced by a whole-manifest `--touch`.

**README freshness:** passed. **Agent log:** not active this session.
