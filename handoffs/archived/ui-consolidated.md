# UI Consolidated Handoff

**Created**: 2026-02-03
**Status**: Active — index & evaluation reference
**Purpose**: Single reference for all UI/interaction work across the project

---

## 1. Work Item Index

| # | Work Item | Reference | Port(s) | Status |
|---|-----------|-----------|---------|--------|
| 1 | Orchestrator UI (Aider + Gradio) | [`handoffs/active/orchestrator-ui.md`](orchestrator-ui.md) | 8000 | Ready for Aider integration |
| 2 | Gradio Web UI | `src/gradio_ui.py` (424 lines) | 7860 | Deprecated but functional |
| 3 | OpenAI-compat API | `src/api/routes/openai_compat.py` (360 lines) | 8000 `/v1/*` | Production, 23 integration tests |
| 4 | SSE Event Contract | [`orchestrator-ui.md` §SSE](orchestrator-ui.md) | 8000 | Documented, tested |
| 5 | Whisper Voice Server | [`handoffs/active/voice_recognition_setup.md`](voice_recognition_setup.md) | 9000 | **COMPLETE** — large-v3-turbo, RTF 0.356x |
| 6 | PersonaPlex Full-Duplex Voice | [`handoffs/active/personaplex_voice_interface.md`](personaplex_voice_interface.md) | — | **BLOCKED** (Moshi arch not in llama.cpp) |
| 7 | Phase 8: Trajectory Viz | [`handoffs/active/rlm-orchestrator-roadmap.md`](rlm-orchestrator-roadmap.md) §Phase 8 | 8000 (SSE) | LOW PRIORITY |
| 8 | Document Formalizer (OCR) | LightOnOCR-2-1B | 9001 | Production |
| 9 | Vision Pipeline | Qwen2.5-VL-7B / Qwen3-VL-30B-A3B | 8086/8087 | Production |
| 10 | **Screenpipe** (NEW) | [§2 below](#2-screenpipe-evaluation) | — | To evaluate |
| 11 | **OpenClaw** (NEW) | [§3 below](#3-openclaw-reference-patterns) | — | Reference only (patterns to borrow) |

---

## 2. Screenpipe Evaluation

**What**: 24/7 local screen+audio capture → SQLite → AI-powered natural language search.
MIT, TypeScript/Rust. ~15GB/mo storage, ~10% CPU, 4GB RAM.
Repo: `github.com/mediar-ai/screenpipe`

### Integration Points

| Our Component | Screenpipe Role |
|---|---|
| Orchestrator API (8000) | MCP queries fed as context to orchestrator |
| MemRL episodic memory | Screen captures as memory episodes (complement explicit logging) |
| Aider CLI | MCP bridge — "what file was I looking at 10min ago" |
| Gradio Web UI | Display screenpipe search results in side panel |
| Whisper (9000) | Screenpipe handles ambient audio; Whisper handles directed speech |
| Vision models (8086/8087) | Screenshots → VL model for understanding captured screens |

### MCP Quick Start

```bash
claude mcp add screenpipe -- npx -y screenpipe-mcp
```

### Evaluation Checklist (Phase B)

- [ ] Install screenpipe, verify local-only operation
- [ ] Test MCP queries from Claude Code: "what was I working on 30 minutes ago"
- [ ] Measure CPU impact during active inference (96 threads saturated)
- [ ] Measure CPU impact during idle
- [ ] Test feeding screenshot to VL model (8086) for captioning
- [ ] Measure storage growth rate on `/mnt/raid0/llm/screenpipe/`
- [ ] Test disabling screenpipe audio (keep Whisper as directed-speech handler)
- [ ] Compare screenpipe OCR vs our LightOnOCR (9001)

### Deferred Concerns

- **CPU budget**: ~10% CPU acceptable at idle, but during inference (96 threads) could cause contention. Consider run-only-when-idle policy.
- **Storage**: 15GB/mo on `/mnt/raid0/` is fine (4TB RAID), but needs rotation policy.
- **Privacy**: Continuous capture — document what's captured and add exclusion rules.
- **Audio overlap**: Screenpipe has own audio capture. Disable it; keep Whisper (9000) for directed speech.

---

## 3. OpenClaw Reference Patterns

**What**: Self-hosted personal AI assistant. Node.js/TypeScript. WebSocket gateway (`ws://127.0.0.1:18789`). Multi-channel messaging, voice, browser automation.
Repo: `github.com/nichochar/open-claw`

**Key difference**: OpenClaw proxies to cloud models (Claude/GPT via OAuth). We run local llama.cpp. Their model layer is irrelevant — their UI/channel/voice patterns are the value.

### Patterns to Borrow

| Pattern | Source | Our Use | Priority |
|---|---|---|---|
| Channel abstraction (Telegram/Discord) | Multi-channel messaging | Telegram bot adapter for orchestrator | Phase C |
| TTS integration | ElevenLabs wrapper | Reference for Piper TTS (local, interim) | Phase C |
| Voice wake mode | Wake word → listen → respond | Inform PersonaPlex pseudo-duplex | Phase E |
| Browser automation (CDP) | Puppeteer/CDP control | Enhance agentic benchmark suite | Low |
| Session sandbox (Docker) | Per-session isolation | Reference for REPL environment isolation | Low |

### Skip (Not Applicable)

- **Gateway WebSocket protocol** — our REST+SSE is sufficient
- **Skills/plugin registry** — we use MCP servers + Python imports
- **OAuth model auth** — we run local models
- **Live Canvas / A2UI** — interesting but too early; revisit at Phase 8

---

## 4. Consolidated Roadmap

### Phase A — Now
**Aider CLI integration** (documented in [`orchestrator-ui.md`](orchestrator-ui.md))
- Point Aider at `http://localhost:8000/v1/chat/completions` via litellm
- Verify streaming, multi-turn, model selection
- Known gaps: tool calling, escalation visibility, permission flow

### Phase B — Next
**Screenpipe evaluation + Gradio gap closure**
- Run evaluation checklist from §2
- Decide MCP-only vs custom API adapter
- Gradio P1: thinking/reasoning display, file save dialog
- Gradio P2: permission UI, multi-model selector

### Phase C — Later
**Messaging + Voice output**
- Telegram bot adapter (pure Python via `python-telegram-bot`, ref OpenClaw channels)
- Piper TTS for interim local voice output (fill missing TTS gap)
- Trajectory visualization (Phase 8 from roadmap — TrajectoryLogger + SSE metadata)

### Phase D — Future
**Frontend modernization** (only if Gradio proves insufficient)
- React or Svelte web frontend with full orchestrator integration
- Textual TUI (only if full-screen terminal UI needed)

### Phase E — Blocked
**PersonaPlex full-duplex voice**
- Blocked on Moshi architecture support in llama.cpp
- See [`personaplex_voice_interface.md`](personaplex_voice_interface.md) for unblock options

---

## 5. Port Map — UI-Facing Services

| Port | Service | Protocol | Notes |
|------|---------|----------|-------|
| 7860 | Gradio Web UI | HTTP | Deprecated, still functional |
| 8000 | Orchestrator API | HTTP (REST+SSE) | Main entrypoint, OpenAI-compat `/v1/*` |
| 8086 | Vision Worker | HTTP | Qwen2.5-VL-7B (llama.cpp server) |
| 8087 | Vision Escalation | HTTP | Qwen3-VL-30B-A3B (llama.cpp server) |
| 9000 | Whisper STT | HTTP | OpenAI-compat `/v1/audio/transcriptions` |
| 9001 | Document Formalizer | HTTP | LightOnOCR-2-1B (PDF OCR) |

Internal-only ports (8080-8085, 8090) not listed — see `CLAUDE.md` server topology.

---

## 6. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-16 | Aider over OpenCode | Python stack match, active maintenance, litellm backend |
| 2026-01-16 | Aider over custom CLI | Don't reinvent terminal UX; Aider has git/repomap |
| 2026-01-16 | Keep Gradio for web | Already integrated; web-specific features only |
| 2026-01-16 | Defer Textual TUI | CLI sufficient; build only if full-screen needed |
| 2026-01-16 | Option C (Hybrid) first | Minimal effort: unmodified Aider against our API |
| 2026-02-03 | Screenpipe: evaluate MCP-first | Lowest integration effort; MCP gives Claude Code direct access |
| 2026-02-03 | OpenClaw: reference only | Borrow patterns (channels, TTS, voice); skip their runtime |
| 2026-02-03 | Telegram first for messaging | Lightweight bot API, personal use, pure Python (`python-telegram-bot`) |
| 2026-02-03 | Piper TTS as interim | Local, fast, no cloud dependency; PersonaPlex is full-duplex target |
| 2026-02-03 | Skip Node.js dependency | Borrow OpenClaw patterns in Python; avoid adding Node to stack |

---

## 7. Monitor Before Pickup

**Check these repos/resources for changes before resuming work on any phase.**

| Repo | What to Check | Affects |
|------|---------------|---------|
| [mediar-ai/screenpipe](https://github.com/mediar-ai/screenpipe) | MCP server updates, new query capabilities, breaking changes | Phase B (screenpipe eval) |
| [nichochar/open-claw](https://github.com/nichochar/open-claw) | Channel adapter patterns, voice mode changes, new integrations | Phase C (messaging, voice patterns) |
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | Moshi architecture support (issues/PRs mentioning "moshi" or "mimi") | Phase E (PersonaPlex unblock) |
| [kyutai-labs/moshi](https://github.com/kyutai-labs/moshi) | GGUF conversion scripts, community ports to llama.cpp | Phase E (PersonaPlex unblock) |
| [rhasspy/piper](https://github.com/rhasspy/piper) | New voices (especially EN/IT), performance improvements, API changes | Phase C (TTS interim) |
| [paul-gauthier/aider](https://github.com/paul-gauthier/aider) | litellm integration changes, new `/voice` features, breaking API changes | Phase A (Aider integration) |
| [python-telegram-bot/python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) | Major version changes, async API updates | Phase C (Telegram bot) |
| [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | New model releases, int8 CPU optimizations | Item 5 (Whisper server) |

### Quick Check Commands

```bash
# Check llama.cpp for Moshi support (PersonaPlex blocker)
gh search issues --repo ggml-org/llama.cpp "moshi" --state open
gh search prs --repo ggml-org/llama.cpp "moshi" --state all

# Check screenpipe releases since last eval
gh release list --repo mediar-ai/screenpipe --limit 5

# Check Aider changelog for breaking changes
gh release view --repo paul-gauthier/aider --json tagName,body | jq -r '.body' | head -50
```

---

## 8. Open Questions

1. **Screenpipe storage path**: `/mnt/raid0/llm/screenpipe/` or dedicated partition? 15GB/mo accumulates.
2. **CPU contention**: Screenpipe during active inference — run only when idle, or accept overhead?
3. **MCP vs API**: Use screenpipe MCP directly with Claude Code, or build orchestrator adapter?
4. **Whisper overlap**: Disable screenpipe audio capture, or let both run with different roles?
