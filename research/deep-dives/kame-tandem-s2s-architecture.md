# KAME — Tandem S2S Architecture Deep-Dive (Sakana AI, ICASSP 2026)

**Date**: 2026-04-30
**Intake sources**: intake-511 (paper, arxiv:2510.02327), intake-512 (blog), intake-513 (inference repo `SakanaAI/kame`), intake-514 (finetune repo), intake-515 (HF model card)
**Status**: **REFINE — verdict and recommended action upgraded vs original intake**
**Original intake verdict**: `not_applicable` (all five entries) — file-for-awareness via multimodal-pipeline cross-ref; revisit only if Path D/E TTS unblock revives.
**Revised verdict**: `not_applicable_for_S2S_now` BUT with a **specific transferable text-domain pattern** (oracle-stream conditioning) to flag for `outer-coordinator-learned-head.md` and `learned-routing-controller.md` as a future research probe. **No new handoff stub.** Backend swap to local llama-server is now confirmed trivial (one env var) — documented for future revisit.
**Adoption verdict for S2S**: still **NOT adoptable** — Mimi codec + Moshi front-end remain CPU-infeasible blockers, identical class to Paths A/B/D.
**Hardware target**: EPYC 9655, CPU-only. Not deployable on this hardware until codec stack ports to GGUF/llama.cpp.

---

## 1. Abstract

KAME ("Knowledge-Access Model Extension") is a tandem speech-to-speech architecture from Sakana AI (Kuroki, Kubo, Akiba, Tang) accepted at ICASSP 2026. It pairs a Moshi-derived 4-stream front-end S2S transformer (fast, shallow, knowledge-poor) with an asynchronous text-LLM "back-end oracle" (slow, deep, knowledge-rich). The oracle's text response is fed into the front-end as a **fourth autoregressive stream** alongside Moshi's existing input audio, output audio, and inner-monologue streams. The front-end is specifically fine-tuned via simulated-oracle augmentation to consume this stream and refine its in-flight speech generation as more oracle context arrives. Headline result: MT-Bench-speech 2.05 (Moshi) → 6.43 (KAME w/ GPT-4.1) → 7.70 (Unmute cascaded), with median latency identical to baseline Moshi (~0 ms vs 2.1 s for Unmute). The architecture is paper-claimed and paper-demonstrated to be **back-end agnostic** (GPT-4.1 6.43, Claude-Opus-4.1 6.23), and the reference inference repo's hardcoded `AsyncOpenAI()` is in fact trivially redirectable to any OpenAI-compatible endpoint via `OPENAI_BASE_URL`. **However**, the front-end's audio stack (Moshi + Mimi codec, 7-codebook RVQ acoustic + 1 semantic) has no llama.cpp/GGUF path and is GPU-only in the reference implementation — same blocker class as our existing Path A (Qwen3-TTS C++ port), Path B (MiniCPM-O), Path D (LuxTTS GPU sidecar), and Path E (Qwen3-Omni-30B-A3B watch).

The key intellectual contribution is **not** the closed-API dependency or the Moshi front-end; it is the **oracle-stream conditioning pattern**: a fast streaming generator trained to consume a slower, more knowledgeable LLM's partial outputs as an additional aligned stream. This is the speech-domain analogue of speculative decoding's "draft + verify", but with a critical distinction: KAME does **not** verify or reject oracle tokens — it conditions on them as soft guidance. The front-end always emits its own tokens; the oracle just shapes the conditional distribution.

## 2. Architecture (Paper §2)

### 2.1 Two-Module Tandem Topology

```
      Input audio stream  ──┐
                            │
                            ▼
   ┌────────────────────────────────────────┐         ┌──────────────────────┐
   │  Front-end S2S Transformer (Moshi-4S)  │ ◄────── │ Streaming STT → LLM  │
   │  - 80 ms token cycle                   │ Oracle  │ - 100-500 ms cycle   │
   │  - 4 streams (input audio, output      │ stream  │ - GPT-4.1 (default)  │
   │    audio, inner monologue, ORACLE)     │         │ - Back-end agnostic  │
   └────────────────────────────────────────┘         └──────────────────────┘
                            │
                            ▼
                     Output audio stream
```

- **Front-end** runs at 80 ms cycle (12.5 Hz codec frame rate, matching Mimi).
- **Back-end** STT continuously transcribes input audio, feeds partial transcripts to the LLM at 100-500 ms cadence. LLM generates a candidate response, streams it as oracle tokens back to the front-end.
- **Asynchrony**: the two modules are not synchronized. Front-end emits speech immediately on receiving input audio; oracle text arrives in irregular chunks and is consumed when available.

**Critical detail**: The oracle is NOT a verifier. The front-end always generates speech tokens at 80 ms cadence regardless of whether oracle text has arrived. When new oracle text arrives, it is enqueued as additional context tokens on the oracle stream and influences subsequent generations.

### 2.2 Oracle Stream Mechanism (the load-bearing piece)

This is the heart of the architecture and the most-misread part of the intake summary.

The oracle stream is **not** cross-attention from an external module. It is **not** prefill into a single context. It is a **fourth autoregressive token stream within a 4-stream Moshi-style joint transformer**, alongside:

1. Input audio stream (encoded user speech)
2. Inner monologue stream (text representation of system response — Moshi's existing text-aligned stream)
3. Output audio stream (acoustic codes for system speech)
4. **Oracle stream (NEW in KAME)** — encodes back-end LLM's partial response

The S2S transformer auto-regressively models all four streams jointly. At each 80 ms tick, the model receives the current state of all four streams as input and predicts the next token on each. The oracle stream's tokens are externally written (when the back-end produces them) rather than self-predicted.

**Conflict resolution**: Because the back-end LLM is asynchronous, multiple candidate responses can overlap in time. KAME uses a "most-recent-wins" policy: when a new oracle response arrives, it replaces (rather than concatenates onto) the previous one. Each new oracle sentence is prefixed with a dedicated boundary special token so the front-end can distinguish refresh events from continuation.

**Tokenization**: Oracle text is tokenized with the same tokenizer as the inner-monologue stream — meaning the front-end already "speaks the language" of the oracle stream from the inner-monologue training. This is a key architectural choice: the oracle stream rides on existing text-tokenizer infrastructure.

### 2.3 Why This Required Front-End Re-Training

The front-end **must** be trained to use the oracle stream — you cannot graft this onto a pretrained Moshi at inference time. Reasons:

- The oracle stream is a **new input modality** that the original Moshi has no embedding table for. Pretrained Moshi has 3 streams (input audio, output audio, inner monologue), not 4.
- The front-end must learn the conditioning behavior: when oracle text says "X", the output speech should drift toward expressing X without copying verbatim (otherwise it sounds robotic and breaks on contradictory updates).
- The front-end must learn graceful handling of **contradictory oracle updates** (the paper notes KAME can self-correct when later oracle text contradicts earlier oracle text — this is a learned behavior).

This means **adopting KAME requires retraining the front-end** even if you swap the oracle backend. The architecture is back-end agnostic at inference (oracle text is just text), but the front-end audio model is fixed weights tied to a specific Moshi base.

### 2.4 Training: Simulated Oracle Augmentation (Paper §3)

The training-data problem: real recorded conversations don't come with "what an LLM oracle would have said at each timestamp" annotations. KAME solves this with a synthetic data pipeline (paper Fig. 3, Table 1):

For each utterance with N total words, at time t the model has heard n(t) words. Define completeness `r(t) = n(t)/N`. Map to **hint level ℓ(t)** ∈ {0..5}:

| ℓ | r(t) range | History | Hint | Prompt instruction to simulator LLM |
|---|---|---|---|---|
| 0 | [0, 0.5) | yes | none | (no hint — generate plausible response from heard prefix) |
| 1 | [0.5, 0.65) | yes | yes | "Refer only to keywords from the hint string." |
| 2 | [0.65, 0.8) | yes | yes | "Include content different from the hint." |
| 3 | [0.8, 0.95) | yes | yes | "Don't copy the hint verbatim." |
| 4 | [0.95, 1) | yes | yes | "Use the hint." |
| 5 | [1, 1] | — | — | (use hint directly as final oracle text — no LLM call) |

This produces a sequence of progressively-converging oracle sentences mapped to timestamps, faithfully simulating real-time LLM behavior at training time without requiring a live LLM in the training loop. The "hint" is the recorded ground-truth response.

**Datasets used**:
- 22,800 dialogues from 11,996 MMLU-Pro entries
- 11,742 dialogues from 7,428 GSM8K entries
- 22,040 dialogues from 12,012 HSSBench entries

Question-answer pairs are converted to conversational style via TTS + word-aligner.

**Training objective**: combined text+audio loss with audio loss weighted ×1.5. All other hyperparameters identical to original Moshi.

### 2.5 Benchmarks (Paper Table 2)

MT-Bench-speech subset (excludes Coding/Extraction/Math/Roleplay/Writing as ill-suited to speech). LLM-as-judge scoring, averaged across 6 runs.

| System | Reasoning | STEM | Humanities | Avg | Median latency |
|---|---|---|---|---|---|
| Moshi (baseline) | 1.32 | 1.94 | 2.88 | 2.05 | 0.0 s |
| **KAME w/ GPT-4.1** | **5.44** | **6.65** | **7.19** | **6.43** | **0.0 s** |
| KAME w/ Claude-Opus-4.1 | 5.72 | 6.53 | 6.43 | 6.23 | 0.0 s |
| Unmute cascaded (w/ GPT-4.1) | 7.08 | 8.35 | 7.67 | 7.70 | 2.1 s |

**Interpretation**:
- KAME closes 80% of the Moshi → Unmute quality gap (4.38 of 5.65 points).
- Latency is identical to Moshi (0.0 s median = system starts speaking before user finishes speaking) vs Unmute's 2.1 s.
- **Back-end agnosticism is empirically demonstrated**: training was done primarily with GPT-4.1-nano as the back-end, but inference with GPT-4.1 (different model from training) and with Claude-Opus-4.1 (entirely different vendor) both work with minor quality variation.
- The gap to Unmute is attributed to "premature generation" — KAME starts speaking before knowing what to say, then can self-correct via oracle updates, but redundant text from corrections drags down LLM-as-judge scores. When KAME is forced to delay its response (silence padding), MT-Bench score initially improves with delay but then plateaus, confirming the trade-off is real.

### 2.6 Authorship & Provenance

- **Authors**: So Kuroki, Yotaro Kubo, Takuya Akiba, Yujin Tang
- **Affiliation**: Sakana AI, Tokyo
- **Venue**: ICASSP 2026 (paper dated arxiv:2510.02327v1, 26 Sep 2025)
- **Hardware**: not explicitly disclosed (inference is GPU; reference impl uses `--device cuda` examples)
- **License**: Repo MIT + inherited LICENSE.audiocraft (Moshi's dual-licensing carries forward)

## 3. Reference Implementation Audit (`SakanaAI/kame` repo)

### 3.1 Module of Interest: `src/kame/server_oracle.py`

This is the file that wires the oracle backend.

**Confirmed by direct repo inspection (WebFetch)**:

- **HTTP client**: `AsyncOpenAI` from `openai` package (official OpenAI Python SDK, async variant)
- **Instantiation** (line ~328): `self.client = AsyncOpenAI()` — no arguments
- **Endpoint called** (line ~404): `self.client.chat.completions.create(model="gpt-4.1", messages=..., stream=True)`
- **Streaming**: yes (`stream=True`, `async for chunk in stream:`)
- **Model**: hardcoded `"gpt-4.1"` — no env var, no CLI flag exposed
- **Request fields**: `model`, `messages`, `stream`. No tool calls, no JSON mode, no response_format. **The interface is the most generic possible OpenAI Chat Completions call.**
- **Oracle injection path** (lines ~370-420 → ~859-918): tokens flow `OpenAI stream chunks` → `oracle_queue` → `opus_loop()` → `lm_gen.update_oracle_tokens_streaming()` (the front-end model's oracle-stream tokenizer).
- **System prompt** (lines 34-43): hardcoded constant `SYSTEM_PROMPT`, instructs the model to predict the User's dialogue flow and generate a suitable next response, max 30 words, avoid non-pronunciation symbols, speak confidently.

### 3.2 Backend-Swap Viability — REVISED FROM INTAKE

**Intake assumed**: closed-API dependency = adoption blocker for open-source-only policy.

**Actual situation**: `AsyncOpenAI()` with zero args calls `os.environ.get("OPENAI_BASE_URL")` and `os.environ.get("OPENAI_API_KEY")` internally. This is documented openai-python SDK behavior since v1.0 (Nov 2023).

**Implication**: To repoint KAME's oracle backend at a self-hosted llama-server:

```bash
export OPENAI_BASE_URL=http://localhost:8000/v1
export OPENAI_API_KEY=dummy   # llama-server ignores it but SDK requires non-empty
python -m kame.server_oracle ...
```

llama-server's `/v1/chat/completions` endpoint (enabled by default on `llama-server`) is a faithful OpenAI-compat shim — it accepts `model`, `messages`, `stream`. No tool-calling/JSON-mode/vision are required by KAME, so even llama-server's reduced compat surface is sufficient.

**But**: model name `"gpt-4.1"` is hardcoded in the source. llama-server ignores the model field if only one model is loaded, but if multiple are served the call will fail. This is a one-line source patch (or a `sed` on install). Not a real blocker.

**Conclusion**: Backend swap to local llama-server is **trivial — one env var + optionally one one-line patch**. The "closed-API dependency" framing in the intake was incorrect.

### 3.3 What Is Actually CPU-Infeasible

The blocker is NOT the oracle backend. The blocker is the **front-end S2S model itself**:

- **Moshi front-end** is a 7B-class joint audio-text transformer. PyTorch reference, GPU-required. No GGUF support. Same blocker class as Path A (Qwen3-TTS llama.cpp port that outputs noise) and Path D (LuxTTS GPU sidecar).
- **Mimi codec** (Moshi's encoder/decoder): 8-codebook RVQ at 12.5 Hz, neural-codec ConvNet. Not a GGUF candidate.
- **Streaming STT component** (Sakana repo uses Google Cloud Speech-to-Text). This IS easily replaceable with our existing port-9000 faster-whisper service.

So the real cost of adopting KAME is:

1. ❌ Port Moshi front-end to llama.cpp/GGUF — **same problem class as Path A's blocked work**.
2. ❌ Port Mimi codec to llama.cpp — **same problem class as Path A's blocked work**.
3. ✓ Replace Google STT with port-9000 Whisper — trivial.
4. ✓ Repoint OpenAI client at local llama-server — trivial.
5. ❌ Get the trained KAME model weights — HF model card exists (intake-515) but checkpoints are derived from Moshi's licensed weights. Re-training requires the audio dataset pipeline + the simulated-oracle augmentation pipeline + GPU training compute we don't have.

Items 1 and 2 alone are existential blockers. The fact that backend swap (item 4) is easy doesn't help when items 1 and 2 are unsolved.

## 4. EPYC Mapping — Why It Still Doesn't Fit

| KAME requirement | EPYC reality | Block? |
|---|---|---|
| Moshi front-end, GPU PyTorch inference | CPU-only, 1.1 TB DRAM, no GPU | **HARD** — same class as multimodal-pipeline Path A |
| Mimi codec (audio encoder/decoder) | No GGUF/llama.cpp port for neural codecs | **HARD** — same class as Qwen3-TTS sidecar |
| Streaming STT (Google Cloud in repo) | Have faster-whisper on port 9000 | OK — trivial swap |
| Back-end LLM = GPT-4.1 via OpenAI | Open-source-only policy | **NOT a block** — `OPENAI_BASE_URL` swap to local llama-server is one line |
| Front-end retrained for oracle stream | We don't have training infra for Moshi-class S2S | **HARD** — even if weights existed, fine-tuning requires their audio data pipeline |
| Real-time 80 ms decode of 7B-class joint audio model | CPU 7B-class decode achievable but joint audio modality unproven on llama.cpp | **HARD** |

**Bottom line**: KAME and the existing TTS Paths A/B/C/D/E are all blocked by the same underlying problem — **neural codec audio stacks have no production-grade CPU-only inference runtime**. KAME does not change this.

## 5. Transferable-Pattern Audit (the most valuable section)

The user asked specifically: is "tandem fast-shallow + slow-deep with mid-stream injection" meaningfully distinct from existing EPYC patterns? Audit:

### 5.1 vs Speculative Decoding (drafter/verifier, intake-153 RLM, MoE-spec)

| Aspect | KAME oracle stream | Speculative decoding |
|---|---|---|
| Fast model role | Generates output tokens | Generates draft tokens |
| Slow model role | Provides conditioning text | Verifies/corrects drafts |
| Coupling | Conditioning (soft guidance) | Token-level accept/reject (hard) |
| Output authority | Fast model emits final tokens | Slow model emits final tokens (after verify) |
| Training requirement | Fast model retrained on 4-stream | Drafter trained against verifier vocabulary |
| Asynchrony | Slow model arbitrarily slower than fast | Slow model dominates wall-clock |

**Verdict: meaningfully distinct.** KAME's oracle does NOT verify and does NOT have output authority — it shapes the conditional distribution. This is a **conditioning** pattern, not a verification pattern. Speculative decoding wouldn't tolerate the slow model arbitrarily lagging behind; KAME tolerates it because the fast model is always the speaker.

### 5.2 vs worker_explore + coder routing (cheap-first → escalate)

| Aspect | KAME | EPYC cheap-first |
|---|---|---|
| Workflow | Both run in parallel from t=0 | Sequential: cheap first, escalate on confidence |
| Output | Single stream, fused at fast model | One model emits, the other doesn't |
| Output during slow inference | Fast model already speaking | Cheap model emits, hidden from user if escalated |
| Updates to in-flight output | Yes (oracle text replaces, fast model self-corrects) | No (cheap model output is final or discarded) |

**Verdict: meaningfully distinct.** EPYC cheap-first is sequential branch selection. KAME is parallel multi-stream conditioning with mid-stream updates. The "self-correct on contradictory oracle update" behavior has no EPYC analogue.

### 5.3 vs Hermes outer-shell + EPYC inner

| Aspect | KAME | Hermes-outer-shell |
|---|---|---|
| Outer module | Slow LLM (knowledge oracle) | UX/skills/multi-platform gateway |
| Inner module | Fast S2S (audio generator) | Inference/routing/escalation |
| Information flow | Outer → inner via aligned token stream | Outer → inner via API params (`routing_override`) |
| Coupling timescale | Sub-second, mid-utterance | Per-request boundary |

**Verdict: meaningfully distinct.** Hermes coordination is at request boundaries, with no notion of mid-stream injection of partial outer-model output into the inner-model's autoregressive context.

### 5.4 vs Trinity outer-coordinator-learned-head (intake-474)

| Aspect | KAME | Trinity coordinator |
|---|---|---|
| Decision frequency | Mid-utterance, continuous | Per-turn or per-task |
| Decision space | What text to inject as conditioning | Which (LLM, role) to dispatch |
| Coupling | Token-stream concatenation | Routing decision |

**Verdict: distinct, but adjacent.** Trinity is per-turn dispatch, KAME is intra-turn conditioning. Both involve a fast/cheap controller and a pool of slower deeper models, but at different time scales.

### 5.5 Is There a Genuinely Novel Text-Domain Pattern?

The pattern **"fast streaming generator + slow oracle, with oracle output written into a dedicated trained-in conditioning stream the generator was retrained to consume, with most-recent-update-wins semantics on contradictory updates"** is genuinely distinct from the four existing EPYC patterns above. **But** in the text-only domain, this pattern collapses to something close to existing techniques:

- If both modules are text models with the same tokenizer, "oracle stream injection" looks like **soft prompt prefix injection at runtime**, which is a known technique.
- The interesting bit (asynchronous most-recent-wins) needs a streaming generator that can have its prefix mutated mid-generation. We don't have this in our stack — our `llama-server` doesn't support post-hoc context replacement during a streaming generation.
- The trained-in fourth-stream conditioning is the architecturally novel piece, but it requires base-model re-training on a 4-stream-aware token layout.

**Where this could slot in EPYC**, if pursued:
- **`outer-coordinator-learned-head.md`** — KAME suggests a coordination primitive Trinity doesn't have: the inner inference can be **continuously updated** by the outer Claude/coordinator while still emitting tokens, rather than the outer waiting for the inner's full output before re-deciding. This is the "speak-while-thinking" extension to the coordination action space.
- **`autopilot-continuous-optimization.md`** — analogous: a fast experiment-running loop (inner) with mid-experiment hint injection from a slower planning/verification loop (outer Claude). The "most-recent-wins" semantics on hint refresh is the directly transferable mechanic.
- **`learned-routing-controller.md` Phase 4** — if the routing classifier had access to a slow oracle's progressive estimates of task difficulty / required model class, it could revise its routing mid-decode. Today routing is one-shot per request.

**Recommendation**: file the "oracle-stream conditioning, most-recent-wins, mid-decode update" pattern as a footnote inside the OC-0 design-space-reference table in `outer-coordinator-learned-head.md`, NOT as a new handoff. The pattern is interesting but speculative and doesn't have a near-term implementation path. Adding it as a row in the OC-0 table satisfies file-for-awareness without spawning new work. **Per CLAUDE.md "Agents & Automation" policy, the actual table edit requires user approval — this deep-dive only proposes the action.**

## 6. SHANKS Comparison (intake-future, arxiv:2510.06917)

SHANKS ("Simultaneous Hearing and Thinking for Spoken Language Models", same Q4 2025) explores adjacent territory: speak-while-thinking for spoken LM via **streaming chunked input + unspoken chain-of-thought reasoning generated while listening**. Headline numbers: 37.1% higher interruption accuracy, 56.9% of tool calls completed before user finishes their turn.

### 6.1 KAME vs SHANKS

| Aspect | KAME | SHANKS |
|---|---|---|
| Architecture | Tandem (2 models, fast + slow oracle) | Single model with streaming chunked input |
| Reasoning during input | None (relies on external oracle) | Internal CoT generated as user speaks |
| Interruption support | Implicit (most-recent-wins oracle) | **Primary contribution** (37.1% interrupt acc.) |
| Tool calls | Not addressed | **Primary contribution** (56.9% pre-completion) |
| Open weights | Front-end ties to Moshi (gated weights) | No code or weights in webpage |
| CPU feasibility | None (Moshi+Mimi blocker) | Unknown, depends on base model |

### 6.2 Does SHANKS Supersede KAME?

**No, they solve different problems.**

- KAME: knowledge-augmented S2S (deep knowledge from large LLM injected into small fast S2S)
- SHANKS: latency-reduced reasoning (model thinks during user's turn, not after)

If we ever revisit the speech-interface space, SHANKS is more interesting for **agentic** workflows (tool use, interruption-driven dialogue) while KAME is more interesting for **knowledge-grounded Q&A**. They are complementary, not competing. **Both are blocked on the same underlying audio-stack-on-CPU problem.**

For the future-watch list, SHANKS is the better target because:
1. Tool-call-during-speech is more aligned with EPYC's agentic orchestrator focus than knowledge-grounded chat.
2. SHANKS's contribution is a **reasoning recipe** (chunked-input + unspoken CoT), which is more transferable to text-only domains than KAME's audio-stream conditioning.
3. The SHANKS pattern (think while reading user input) maps onto our existing architecture more cleanly: it's analogous to running the planner during user prompt streaming rather than after EOS.

**Recommendation**: when refreshing the multimodal-pipeline cross-ref, point the future-watch row at **both** intake-511 (KAME) AND a new intake stub for SHANKS (when ingested). Don't replace KAME with SHANKS — track both.

## 7. Refined Recommendation

### 7.1 Intake Verdict — REFINE

**Original**: `not_applicable` for all five entries (intake-511 through 515), with action = "file-for-awareness via multimodal-pipeline cross-ref; revisit only if Path D/E TTS unblock revives."

**Revised**: keep `not_applicable` for the **S2S system as a whole** (the front-end + Mimi + Moshi blocker is unchanged), but with the following refinements:

1. **Correct the closed-API framing in the intake entry**. The intake says "reference impl uses OpenAI Chat Completions + Google STT, violating open-source-only policy". This is technically true of the *current default config*, but the underlying interface is OpenAI-compat-generic and trivially repointable to llama-server via `OPENAI_BASE_URL`. The closed-API dependency is **convenience, not architecture**. Update intake-513 to reflect this — keep the verdict, fix the reasoning.

2. **Add the transferable-pattern row to the OC-0 design-space-reference table** in `outer-coordinator-learned-head.md`. KAME demonstrates a coordination primitive (oracle-stream conditioning, most-recent-wins, mid-decode update) that Trinity does not. This is a competitive-intelligence row, not an adoption commitment. **Requires user approval per CLAUDE.md policy on sub-agent index changes.**

3. **Add SHANKS to the future-watch list** alongside KAME, not replacing it. Different problem (latency-reduced reasoning vs knowledge-augmented response). When SHANKS gets a separate intake entry, cross-link to KAME's deep-dive.

### 7.2 No New Handoff Stub

The transferable-pattern observation (§5) does not warrant a new handoff. It is a pattern note, not an actionable plan. Filing it as a row in the OC-0 design-space-reference table is the correct level of investment.

### 7.3 Backend-Swap Documentation

Document for future revisit (e.g., in this deep-dive's §3.2): if Path A/D ever unblocks the audio stack, the KAME oracle backend swap to llama-server is one env var. This information is now captured here so a future agent doesn't redo the analysis.

### 7.4 Path Back to Relevance — What Would Have to Change

For KAME to become actionable on EPYC:

1. **Moshi/Mimi must port to llama.cpp or get a credible CPU-only PyTorch path** (e.g., torch CPU + AVX-512 BF16 numerics). This is the same prerequisite as Path A/D. If this lands, multiple TTS paths unblock simultaneously and KAME becomes one of several adoption candidates.
2. **Open-weight KAME checkpoint** — currently Moshi-derived weights have license complexity, and the KAME training pipeline (simulated-oracle augmentation + Moshi-base fine-tune) requires GPU compute we don't have. Check intake-515 (HF model card) periodically to see if Sakana ships weights.
3. **A real EPYC voice-interface use case** — currently the multimodal-pipeline TTS work is LOW priority and de-prioritized vs CPU optimization and routing. KAME (or any voice S2S) revives only if the user actually wants voice interaction.

If all three above resolve, KAME's adoption decision is simpler than most TTS paths because the oracle backend is trivially repointed at our stack.

## 8. Cross-References

- `/workspace/handoffs/active/multimodal-pipeline.md` — primary handoff KAME cross-refs into; current TTS state (Paths A-E)
- `/workspace/research/deep-dives/qwen35-omni-tts-unblock.md` — sibling DD on Qwen3.5-Omni (Scenario C, also blocked, same class)
- `/workspace/research/deep-dives/luxtts-cpu-tts-candidate.md` — Path D baseline, the strongest current EPYC TTS unblock candidate
- `/workspace/research/deep-dives/voicebox-multi-engine-tts-studio.md` — Voicebox studio (intake-396) multi-engine TTS reference
- `/workspace/research/deep-dives/hume-tada-text-acoustic-alignment.md` — TADA long-form synthesis (intake-402)
- `/workspace/handoffs/active/outer-coordinator-learned-head.md` — proposed home for the transferable-pattern row (KAME oracle-stream conditioning) in the OC-0 design-space-reference table
- `/workspace/handoffs/active/hermes-outer-shell.md` — sibling outer-shell architecture (compared in §5.3)
- `/workspace/handoffs/active/learned-routing-controller.md` — possible mid-decode-revision target (compared in §5.5)

## 9. Decision Summary

| Question | Answer |
|---|---|
| Is the oracle backend trivially swappable to local llama-server? | **YES** (one env var) |
| Is the S2S front-end CPU-deployable on EPYC? | NO (Mimi codec + Moshi joint audio model, same blocker as Paths A/D) |
| Is the transferable pattern genuinely distinct from existing EPYC patterns? | YES (oracle-stream conditioning ≠ spec-dec, ≠ cheap-first, ≠ Hermes outer-shell, ≠ Trinity coordinator) |
| Should KAME become actionable now? | NO — front-end blocker unresolved |
| Should the intake verdict change? | REFINE — correct the closed-API framing; verdict stays `not_applicable`; add SHANKS to future-watch; propose transferable-pattern row in OC-0 table (user approval required) |
| Does SHANKS supersede KAME? | NO — different problem (reasoning latency vs knowledge depth); track both |
| New handoff stub? | NO — pattern note in existing OC-0 design-space-reference table is the right level |

---

**Author**: deep-dive agent, 2026-04-30
**Length**: ~5,400 words
**Status**: complete; final reply summarizes structured analysis for the parent agent
