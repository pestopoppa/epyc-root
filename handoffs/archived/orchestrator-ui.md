# Orchestrator UI Handoff

**Status**: Ready for Aider integration
**Last Updated**: 2026-01-16
**Blocked By**: None
**Priority**: When terminal CLI needed

---

## Quick Resume

### Option A: Production Machine (pace-env)

```bash
# 1. Activate pace-env
source /mnt/raid0/llm/pace-env/bin/activate

# 2. Start orchestrator API
cd /mnt/raid0/llm/claude
PYTHONPATH=/mnt/raid0/llm/claude python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 &

# 3. Install Aider (if needed)
pip install aider-chat

# 4. Configure Aider
cat > ~/.aider.conf.yml << 'EOF'
model: openai/orchestrator
openai-api-base: http://localhost:8000/v1
openai-api-key: dummy
auto-commits: false
stream: true
EOF

# 5. Test Aider
cd /mnt/raid0/llm/claude
aider --no-git --message "What is 2+2?"
```

### Option B: Devcontainer/Python 3.13+ (Requires uv)

Python 3.13 has compatibility issues with aider's dependencies. Use uv to install Python 3.12:

```bash
# 1. Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 2. Install Python 3.12
uv python install 3.12

# 3. Create aider venv and install
uv venv --python 3.12 /tmp/aider-env
uv pip install --python /tmp/aider-env/bin/python aider-chat

# 4. Start orchestrator API (uses workspace venv)
PYTHONPATH=/workspace nohup /workspace/.venv/bin/python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload > /tmp/api.log 2>&1 &

# 5. Configure Aider
cat > ~/.aider.conf.yml << 'EOF'
model: openai/orchestrator
openai-api-base: http://localhost:8000/v1
openai-api-key: dummy
auto-commits: false
stream: true
EOF

# 6. Test Aider with separate venv
echo "What is 2+2?" | /tmp/aider-env/bin/aider --no-git --yes --message "What is 2+2?"
```

### Prerequisites

- [x] Orchestrator API running on port 8000
- [x] `/v1/chat/completions` endpoint working (fixed 2026-01-16)
- [x] Aider installed (Python 3.12 via uv for 3.13+ systems)

### Success Criteria

1. Aider connects to our API without errors
2. Streaming responses render in terminal
3. Repomap generates for `/mnt/raid0/llm/claude`
4. Basic code edit completes (e.g., "add a docstring to this function")

### Verified (2026-01-16)

- [x] Aider's streaming works with our SSE format (tested)
- [x] Mock mode fallback works when llama-server not running
- [x] OpenAI-compat endpoint respects feature flags

### Known Gaps to Investigate

- [ ] Does tool calling pass through correctly?
- [ ] How does Aider handle our multi-turn escalation?
- [ ] Permission flow - can we surface permission_request events?
- [ ] Test with live llama-server instances

---

## Strategy Decision

| Interface | Solution | Rationale |
|-----------|----------|-----------|
| **Terminal CLI** | **Aider** (integrate) | Python, Apache-2.0, litellm backend, active maintenance |
| **Web UI** | Gradio (keep) | Already integrated, web-specific features (artifacts, permissions) |
| **Terminal TUI** | Defer | Build with Textual if needed later |

---

## FOSS Alternatives Analysis

| Tool | Verdict | Rationale |
|------|---------|-----------|
| [Aider](https://github.com/Aider-AI/aider) | **PRIMARY CLI** | Python, Apache-2.0, litellm (easy backend swap), excellent git/repomap |
| [OpenCode](https://github.com/opencode-ai/opencode) | REJECTED | Archived, Go (foreign stack), would require FFI/recompilation |
| Custom Gradio | WEB ONLY | Keep for browser-based use cases, not terminal |

### Detailed Comparison

| Factor | OpenCode | Aider | Our Gradio UI |
|--------|----------|-------|---------------|
| **Status** | ARCHIVED | **ACTIVE** | Active |
| **Language** | Go (Bubble Tea) | **Python** | Python (Gradio) |
| **UI Type** | Terminal TUI | Terminal CLI | Web-first |
| **Local Models** | Generic endpoint | Ollama, OpenAI-compat | Native llama.cpp |
| **Multi-model** | Config-driven | Best-model routing | Orchestrator (escalation, MemRL) |
| **Repo Awareness** | Basic | **Excellent** (repomap) | None (chat-only) |
| **Git Integration** | None | **Native** (auto-commit) | None |
| **License** | Apache-2.0 | Apache-2.0 | Internal |

### Recommended Hybrid Approach

1. **Now**: Continue with Gradio UI for web-specific features
2. **Future**: Evaluate Aider integration for git/repomap capabilities
3. **If needed**: Fork OpenCode for terminal TUI customization

---

## Current Implementation

| File | Lines | Purpose |
|------|-------|---------|
| `src/gradio_ui.py` | 415 | Chat, artifacts, routing visualization |
| `src/api.py` | ~800 | SSE streaming + OpenAI-compatible endpoints |
| `src/sse_utils.py` | ~100 | Event types and formatting |
| `tests/integration/test_frontend_integration.py` | 23 tests | API integration tests |

### Quick Start

```bash
# Start Gradio Web UI (local only)
python -m src.gradio_ui --port 7860

# With public URL (gradio.live)
python -m src.gradio_ui --share

# Start LiteLLM proxy (for LM Studio, etc.)
pip install 'litellm[proxy]'
litellm --config config/litellm_config.yaml --port 4000
```

---

## Implemented Features

- [x] Chat with SSE streaming
- [x] Code artifact display (Python syntax highlighting)
- [x] Routing visualization (JSON panel showing turns, roles, tokens)
- [x] Settings panel with health check
- [x] Copy button on messages
- [x] API URL configuration
- [x] Soft theme with blue/gray colors
- [x] Monospace fonts for code (SF Mono, Monaco, Inconsolata)

---

## Missing Features

| Feature | Priority | Complexity | Notes |
|---------|----------|------------|-------|
| File save dialog | P1 | Low | TODO at `src/gradio_ui.py:291` |
| Thinking display | P2 | Medium | Events received via SSE, no UI tab |
| Tool viz panel | P2 | Medium | Events parsed, not shown in UI |
| Permission UI | P2 | Medium | Approval flow exists in API (`/permission/*`) |
| Multi-lang artifacts | P3 | Low | Add language dropdown to code editor |
| Session management | P3 | Medium | API endpoints exist (`/sessions/*`) |

### Feature Details

#### File Save Dialog (P1)
```python
# Current state (src/gradio_ui.py:291)
# TODO: Implement file save dialog
return gr.Info(f"Code saved ({len(code)} chars)")
```
**Fix**: Use `gr.File` output component or browser download API.

#### Thinking Display (P2)
SSE events include `thinking` type when `thinking_budget > 0`:
```json
{"type": "thinking", "content": "Let me analyze this..."}
```
**Fix**: Add collapsible thinking panel below chat.

#### Permission UI (P2)
API supports permission approval flow:
- `GET /permission/pending` - List pending permissions
- `POST /permission/{id}/approve` - Approve
- `POST /permission/{id}/reject` - Reject

**Fix**: Add modal dialog when `permission_request` event received.

---

## Phase 8: Trajectory Visualization

From `handoffs/active/rlm-orchestrator-roadmap.md`:

### Task 8.1: Enhanced SSE Events

Add trajectory metadata to SSE events for debugging recursive execution:

```python
# src/api.py addition
async def stream_with_trajectory(repl, primitives, request):
    trajectory = []

    for turn in range(request.max_turns):
        trajectory.append({
            "type": "turn_start",
            "turn": turn,
            "role": current_role,
            "timestamp": time.time()
        })

        yield f"data: {json.dumps({'type': 'turn', 'turn': turn, 'role': current_role})}\n\n"

        # Record LLM calls
        for call in primitives.get_recent_calls():
            trajectory.append({
                "type": "llm_call",
                "role": call.role,
                "prompt_preview": call.prompt[:100],
                "response_preview": call.response[:100],
                "tokens": call.tokens,
                "cost": call.cost
            })
```

### Task 8.2: TrajectoryLogger

Session recording for replay and debugging:

```python
# src/llm_primitives.py addition
class TrajectoryLogger:
    def __init__(self, log_dir: str = "logs/trajectories"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self, query: str):
        self.session_id = f"{int(time.time())}_{hash(query) % 10000}"
        self.entries = [{"type": "session_start", "query": query, "ts": time.time()}]

    def log_call(self, role: str, prompt: str, response: str, tokens: int):
        self.entries.append({
            "type": "llm_call", "role": role,
            "prompt": prompt, "response": response,
            "tokens": tokens, "ts": time.time()
        })

    def end_session(self, final_answer: str):
        log_file = self.log_dir / f"{self.session_id}.jsonl"
        with open(log_file, "w") as f:
            for entry in self.entries:
                f.write(json.dumps(entry) + "\n")
```

---

## SSE Event Contract

For building alternative UIs (React, Svelte, etc.) against our API:

| Event Type | Payload | Required | Description |
|------------|---------|----------|-------------|
| `token` | `{type, content}` | Yes | Streaming token |
| `turn_start` | `{type, turn, role}` | Yes | New turn beginning |
| `turn_end` | `{type, tokens, elapsed_ms}` | Yes | Turn complete |
| `thinking` | `{type, content}` | No | Model reasoning (if budget > 0) |
| `tool` | `{type, name, result}` | No | Tool execution result |
| `file` | `{type, path, content, action}` | No | File modification |
| `permission_request` | `{type, id, tool, args}` | No | Awaiting user approval |
| `error` | `{type, message}` | Yes | Error occurred |
| `final` | `{type, answer}` | Yes | Final answer ready |
| `done` | `[DONE]` | Yes | Stream complete |

### Example SSE Stream

```
data: {"type": "turn_start", "turn": 0, "role": "frontdoor"}

data: {"type": "token", "content": "I'll"}

data: {"type": "token", "content": " help"}

data: {"type": "token", "content": " you"}

data: {"type": "turn_end", "tokens": 150, "elapsed_ms": 2500}

data: {"type": "final", "answer": "I'll help you with that task."}

data: [DONE]
```

### Connecting from JavaScript

```javascript
const eventSource = new EventSource('/chat/stream?prompt=' + encodeURIComponent(prompt));

eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
        eventSource.close();
        return;
    }

    const data = JSON.parse(event.data);
    switch (data.type) {
        case 'token':
            appendToChat(data.content);
            break;
        case 'turn_start':
            showRole(data.role);
            break;
        case 'error':
            showError(data.message);
            break;
    }
};
```

---

## Aider Integration Plan (PRIMARY)

### Why Aider

| Feature | Benefit for Us |
|---------|----------------|
| **litellm backend** | Swap to our llama.cpp API with config change |
| **Repomap** | Automatic codebase context for large projects |
| **Git-native** | Auto-commits, diff tracking, branch awareness |
| **Multi-mode** | `/code`, `/architect`, `/ask` match our tiers |
| **Python** | Direct import of our orchestrator modules |
| **Apache-2.0** | Fork/modify freely |

### Integration Approaches

#### Option A: Backend Swap (Minimal)
Point Aider at our orchestrator API via litellm config:

```yaml
# ~/.aider.conf.yml
model: openai/orchestrator
openai-api-base: http://localhost:8000/v1
openai-api-key: dummy
```

Our `/v1/chat/completions` endpoint already exists. Aider becomes a frontend.

#### Option B: Deep Integration (Full Control)
Fork Aider and integrate our modules:

```python
# In forked aider/coders/base_coder.py
from orchestrator.llm_primitives import llm_call
from orchestrator.failure_router import FailureRouter
from orchestrator.repl_environment import REPLEnvironment

class OrchestratorCoder(Coder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.router = FailureRouter()
        self.repl = REPLEnvironment()

    def send_message(self, prompt):
        # Use our orchestrator instead of litellm
        response = llm_call(
            prompt=prompt,
            role=self.get_current_role(),
            escalate_on_failure=True
        )
        return response
```

#### Option C: Hybrid (Recommended)
1. Use Aider as-is for terminal CLI
2. Configure it to hit our `/v1/chat/completions` endpoint
3. Our backend handles routing, escalation, MemRL
4. Aider handles UX, git, repomap

```
┌─────────────────────────────────────────┐
│  Aider CLI (unmodified)                 │
│  - Terminal UX                          │
│  - Git integration                      │
│  - Repomap context                      │
└─────────────────┬───────────────────────┘
                  │ OpenAI-compat API
                  ▼
┌─────────────────────────────────────────┐
│  Our Orchestrator API                   │
│  - /v1/chat/completions                 │
│  - Routing & escalation                 │
│  - MemRL learning                       │
│  - llama.cpp backends                   │
└─────────────────────────────────────────┘
```

### Implementation Checklist

**Phase 1: Basic Integration (Option C - Hybrid)**
- [ ] Install Aider: `pip install aider-chat`
- [ ] Create config: `~/.aider.conf.yml` pointing to our API
- [ ] Test basic prompt/response cycle
- [ ] Verify streaming renders correctly in terminal
- [ ] Test repomap generation on `/mnt/raid0/llm/claude`
- [ ] Document any API compatibility issues

**Phase 2: Validate Features**
- [ ] Test `/code` mode (code generation)
- [ ] Test `/architect` mode (design discussions)
- [ ] Test `/ask` mode (questions about code)
- [ ] Test git auto-commit (if enabled)
- [ ] Test multi-file edits

**Phase 3: Gap Analysis**
- [ ] Document what works vs. what breaks
- [ ] Identify if forking is needed (Option B)
- [ ] Test with different orchestrator roles (frontdoor, coder, architect)
- [ ] Evaluate permission flow integration

---

## Alternative Paths (Lower Priority)

### React/Svelte Web Frontend

For web-only use cases where Gradio is insufficient:

```
┌─────────────────────────────────────────┐
│  React/Svelte Frontend                  │
│  - Modern component architecture        │
│  - Rich artifact rendering              │
└─────────────────┬───────────────────────┘
                  │ SSE/REST
                  ▼
┌─────────────────────────────────────────┐
│  FastAPI Backend (existing)             │
│  - /chat/stream (SSE)                   │
│  - /v1/chat/completions (OpenAI)        │
└─────────────────────────────────────────┘
```

### Textual TUI (If Full-Screen Needed)

If we need a full-screen TUI like OpenCode but in Python:

```python
# Using Textual (Python TUI framework)
from textual.app import App
from textual.widgets import Header, Footer, Input, RichLog

class OrchestratorTUI(App):
    async def on_mount(self):
        # Connect to our SSE endpoint
        pass
```

**Defer until**: CLI proves insufficient for terminal use cases.

---

## Architecture Coupling Assessment

### Tightly Coupled (requires orchestrator)
- MemRL/Q-scoring integration
- Escalation routing visualization
- REPL execution sandbox
- Permission approval flow
- Multi-tier model selection

### Loosely Coupled (portable to any UI)
- SSE event streaming
- OpenAI-compatible `/v1/chat/completions`
- Session management API
- Basic chat functionality

---

## Related Documents

- `handoffs/active/orchestrator.md` - Main orchestrator handoff
- `handoffs/active/rlm-orchestrator-roadmap.md` - Phase 8 trajectory viz details
- `src/api.py` - SSE endpoint implementation
- `src/gradio_ui.py` - Current Gradio implementation

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-16 | Aider over OpenCode | Python (matches stack), active maintenance, litellm backend swappable |
| 2026-01-16 | Aider over custom CLI | Don't reinvent terminal UX; Aider has git/repomap for free |
| 2026-01-16 | Keep Gradio for web | Already integrated; web-specific features (artifacts, permissions) |
| 2026-01-16 | Defer Textual TUI | CLI sufficient for now; build TUI only if full-screen needed |
| 2026-01-16 | Option C (Hybrid) first | Minimal effort; test unmodified Aider against our API before forking |

### Why Not OpenCode?

1. **Archived** - No upstream maintenance, security fixes, or new features
2. **Go language** - Would require learning Go, FFI bridges, or rewriting our Python modules
3. **Terminal TUI only** - Overkill for CLI use case; Aider's simpler CLI is sufficient
4. **MCP overhead** - MCP servers are heavier than our direct Python tool integration

### Why Aider?

1. **Python** - Same language as orchestrator; can import modules directly if needed
2. **litellm** - Backend is swappable via config; point at our `/v1/chat/completions`
3. **Active** - 72% of Aider written by Aider itself; frequent releases
4. **Repomap** - Automatic codebase context we'd have to build ourselves
5. **Git-native** - Auto-commits, branch awareness, diff tracking built-in
6. **Apache-2.0** - Can fork and modify freely if Option C proves insufficient
