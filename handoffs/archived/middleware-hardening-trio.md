# Handoff: Middleware Hardening — Credential Redaction, Script Interception, Cascading Tool Policy

**Created**: 2026-02-18
**Status**: COMPLETE (all 3 gaps implemented)
**Priority**: HIGH
**Triggered by**: Gap analysis of Clawzempic/OpenClaw architecture vs our orchestrator
**Related handoffs**:
- `programmatic-tool-chaining.md` (tool execution pipeline — shared integration surface)
- `delegation-escalation-factual-risk-routing-track.md` (routing — script interception reduces load)
- `orchestration-architecture-optimization-handoff.md` (routing + telemetry — observability overlap)

---

## 1) Executive Summary

Cross-referencing the Clawzempic/OpenClaw proxy architecture against our orchestrator revealed three gaps in our middleware layer. None require architectural changes — all three are additive filters that slot into existing execution paths.

| Gap | Effort | Impact | Risk | Integration Point |
|-----|--------|--------|------|-------------------|
| **A** — Credential Redaction | LOW (1-2 hours) | HIGH (safety-critical) | LOW | Post-tool-execution filter in `ToolRegistry.invoke()` and REPL `execute()` |
| **B** — Script Interception | LOW (2-3 hours) | MEDIUM-HIGH (token savings) | LOW | Pre-routing gate in `ChatPipeline` before graph dispatch |
| **C** — Cascading Tool Policy | LOW-MEDIUM (3-4 hours) | MEDIUM (scalability) | LOW | Replace `ToolPermissions.can_use_tool()` with chain resolver |

Total estimated effort: ~8 hours. All three are independently shippable.

---

## 2) Gap A: Credential Redaction in Tool Outputs

### 2.1 Problem

`security.py` does AST-level *input* validation (blocking forbidden imports, calls, attrs) but **never scans output text**. If a tool returns environment variables, API keys, SSH private keys, or connection strings in its result, those flow unredacted into:
- Model context (token waste + potential regurgitation)
- Session transcripts (persisted to disk)
- API responses (visible to clients)

OpenClaw/Clawzempic implements 5-layer security including automatic credential redaction of "API keys, tokens, SSH keys, connection strings" from all LLM responses and tool outputs.

### 2.2 Design

A stateless post-execution filter applied to all tool/REPL output strings before they enter model context.

```python
# src/repl_environment/redaction.py

import re
from dataclasses import dataclass

@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted_count: int
    categories: frozenset[str]  # e.g. {"aws_key", "ssh_private_key"}

# Pattern registry — each tuple: (name, compiled_regex, replacement)
_CREDENTIAL_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # AWS
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:aws_access_key]"),
    ("aws_secret_key", re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"), None),  # context-dependent, see below

    # Anthropic
    ("anthropic_key", re.compile(r"sk-ant-[a-zA-Z0-9_-]{20,}"), "[REDACTED:anthropic_key]"),

    # OpenAI
    ("openai_key", re.compile(r"sk-[a-zA-Z0-9]{20,}"), "[REDACTED:openai_key]"),

    # GitHub
    ("github_pat", re.compile(r"ghp_[A-Za-z0-9]{36,}"), "[REDACTED:github_pat]"),
    ("github_oauth", re.compile(r"gho_[A-Za-z0-9]{36,}"), "[REDACTED:github_oauth]"),
    ("github_app", re.compile(r"(?:ghs|ghu)_[A-Za-z0-9]{36,}"), "[REDACTED:github_token]"),

    # SSH private keys
    ("ssh_private_key", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    ), "[REDACTED:ssh_private_key]"),

    # Generic bearer tokens
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"), "Bearer [REDACTED:token]"),

    # Connection strings (postgres, mysql, redis, mongodb)
    ("connection_string", re.compile(
        r"(?:postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?):\/\/[^\s\"'<>]{10,}"
    ), "[REDACTED:connection_string]"),

    # Generic long hex secrets (64+ chars, likely API keys or hashes)
    ("hex_secret", re.compile(r"(?<![a-fA-F0-9])[a-fA-F0-9]{64,}(?![a-fA-F0-9])"), "[REDACTED:hex_secret]"),

    # .env style KEY=value on same line
    ("env_secret", re.compile(
        r"(?:API_KEY|SECRET_KEY|ACCESS_TOKEN|AUTH_TOKEN|PASSWORD|PRIVATE_KEY)\s*=\s*[\"']?[^\s\"']{8,}[\"']?"
    ), "[REDACTED:env_value]"),
]


def redact_credentials(text: str) -> RedactionResult:
    """Scan text for credential patterns and replace them.

    Returns:
        RedactionResult with redacted text, count, and categories found.
    """
    if not isinstance(text, str) or len(text) < 16:
        return RedactionResult(text=text, redacted_count=0, categories=frozenset())

    count = 0
    categories: set[str] = set()
    result = text

    for name, pattern, replacement in _CREDENTIAL_PATTERNS:
        if replacement is None:
            continue  # Skip context-dependent patterns
        matches = pattern.findall(result)
        if matches:
            result = pattern.sub(replacement, result)
            count += len(matches)
            categories.add(name)

    return RedactionResult(
        text=result,
        redacted_count=count,
        categories=frozenset(categories),
    )
```

### 2.3 Integration Points

**Point 1 — `ToolRegistry.invoke()` (`src/tool_registry.py:417-450`)**

After `result = tool.handler(**kwargs)`, wrap the result:

```python
from src.repl_environment.redaction import redact_credentials

# After tool execution, before logging/returning
if isinstance(result, str):
    rr = redact_credentials(result)
    if rr.redacted_count > 0:
        logger.warning("Redacted %d credential(s) from tool '%s' output: %s",
                       rr.redacted_count, tool_name, rr.categories)
        result = rr.text
```

**Point 2 — REPL `execute()` (`src/repl_environment/environment.py`)**

In `_RestrictedREPLEnvironment.execute()`, after capturing stdout/stderr, apply redaction before returning.

**Point 3 — `ToolOutput.to_human()` and `.to_machine()` (`src/tool_registry.py:190-209`)**

Apply redaction in the serialization methods as a defense-in-depth layer.

### 2.4 Edge Cases

- **False positives on hex hashes**: SHA256 hashes in code outputs will be redacted. Mitigation: only redact 64+ char hex strings, and log redactions so the model can request unredacted output if needed via a privileged flag.
- **AWS secret key pattern**: Too broad (any 40-char base64). Keep it disabled by default — only enable in environments with actual AWS credentials.
- **Binary/large outputs**: Short-circuit for text < 16 chars or > 1MB (unlikely to be a credential leak in bulk data).

### 2.5 Tests

```
tests/unit/test_credential_redaction.py
- test_aws_access_key_redacted
- test_anthropic_key_redacted
- test_openai_key_redacted
- test_github_pat_variants_redacted
- test_ssh_private_key_multiline_redacted
- test_bearer_token_redacted
- test_connection_string_variants_redacted
- test_env_secret_key_value_redacted
- test_no_false_positive_on_short_strings
- test_no_false_positive_on_normal_code
- test_multiple_credentials_in_same_text
- test_idempotent_redaction
- test_preserves_non_credential_text_unchanged
```

### 2.6 Feature Flag

```python
# src/features.py
credential_redaction: bool = True  # On by default — safety-first
```

### 2.7 Checklist

- [x] Create `src/repl_environment/redaction.py` with pattern library
- [x] Wire into `ToolRegistry.invoke()` post-execution
- [x] Wire into REPL `execute()` stdout/stderr capture
- [x] Wire into `ToolOutput` serialization
- [x] Add feature flag `credential_redaction`
- [x] Write unit tests (40 tests, all passing)
- [x] Verify no false positives against existing test outputs (4219 passing, 0 regressions)
- [x] `make gates` (gates 1-4 pass; gate 7 nextplaid-reindex pre-existing timeout)

---

## 3) Gap B: Script Interception (Zero-Cost Local Resolution)

### 3.1 Problem

Our `ScriptRegistry` provides prepared scripts for token savings (~92%), but the model must still be invoked to *decide* to call a script. For trivially classifiable requests — timestamps, arithmetic, path manipulation, simple lookups — the model invocation itself is pure waste.

Clawzempic handles "straightforward queries (calculations, timestamps) locally at zero cost" — a pre-LLM interceptor that pattern-matches queries and returns results without touching any model.

### 3.2 Design

A lightweight pre-routing classifier in the chat pipeline that matches incoming requests against known-resolvable patterns. If matched, return immediately without graph dispatch.

```python
# src/api/routes/chat_pipeline/script_interceptor.py

import re
import time
from dataclasses import dataclass
from typing import Any

@dataclass
class InterceptionResult:
    matched: bool
    script_id: str | None = None
    result: Any = None
    elapsed_ms: float = 0.0
    pattern_name: str | None = None


# Interceptor patterns — (name, compiled_regex, handler_func)
# Handler receives the match object and returns a result string
_INTERCEPTORS: list[tuple[str, re.Pattern, Any]] = []


def register_interceptor(name: str, pattern: str, handler):
    """Register a new interceptor pattern."""
    _INTERCEPTORS.append((name, re.compile(pattern, re.IGNORECASE), handler))


def _handle_timestamp(match) -> str:
    """Return current timestamp in requested format."""
    from datetime import datetime, timezone
    fmt = match.group("fmt") if match.lastgroup == "fmt" else None
    now = datetime.now(timezone.utc)
    if fmt and "iso" in fmt.lower():
        return now.isoformat()
    if fmt and "unix" in fmt.lower():
        return str(int(now.timestamp()))
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


def _handle_arithmetic(match) -> str:
    """Evaluate simple arithmetic expression."""
    expr = match.group("expr")
    # Strict whitelist: only digits, operators, parens, dots
    if not re.match(r'^[\d\s\+\-\*\/\.\(\)%]+$', expr):
        return None  # Refuse, let model handle
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        return str(result)
    except Exception:
        return None


def _handle_uuid(match) -> str:
    """Generate a UUID."""
    import uuid
    return str(uuid.uuid4())


# Register built-in interceptors
register_interceptor(
    "timestamp",
    r"(?:what(?:'s| is) the (?:current )?(?:time|date|timestamp))"
    r"|(?:current (?:time|date|timestamp))"
    r"|(?:(?:give|get|show)(?: me)? (?:the )?(?:current )?(?:time|date|timestamp))"
    r"(?:\s+(?:in\s+)?(?P<fmt>iso|unix|utc))?",
    _handle_timestamp,
)

register_interceptor(
    "arithmetic",
    r"(?:what(?:'s| is)\s+|calculate\s+|compute\s+|eval(?:uate)?\s+)?(?P<expr>[\d][\d\s\+\-\*\/\.\(\)%]+[\d\)])(?:\s*[=?])?",
    _handle_arithmetic,
)

register_interceptor(
    "uuid",
    r"(?:generate|create|give|get)(?: me)?(?: a| an)?\s+(?:new\s+)?uuid",
    _handle_uuid,
)


def try_intercept(message: str) -> InterceptionResult:
    """Attempt to intercept a message with a local handler.

    Args:
        message: User message text (stripped).

    Returns:
        InterceptionResult — check .matched to see if interception succeeded.
    """
    # Short messages only — long messages are never trivially interceptable
    if len(message) > 200:
        return InterceptionResult(matched=False)

    start = time.perf_counter()

    for name, pattern, handler in _INTERCEPTORS:
        match = pattern.search(message)
        if match:
            result = handler(match)
            if result is not None:
                elapsed = (time.perf_counter() - start) * 1000
                return InterceptionResult(
                    matched=True,
                    script_id=f"intercept:{name}",
                    result=result,
                    elapsed_ms=elapsed,
                    pattern_name=name,
                )

    return InterceptionResult(matched=False)
```

### 3.3 Integration Point

**`src/api/routes/chat_pipeline/` — before `run_task()` dispatches to the graph**

```python
from src.api.routes.chat_pipeline.script_interceptor import try_intercept

# Early in pipeline, after message extraction:
interception = try_intercept(user_message)
if interception.matched:
    logger.info("Script interception: %s (%.1fms)", interception.pattern_name, interception.elapsed_ms)
    # Return result directly without graph dispatch
    return build_response(interception.result, model="local", tokens_saved=estimated_tokens)
```

### 3.4 Extensibility

The `register_interceptor()` API allows adding new patterns without modifying core code. Future interceptors:

| Pattern | Category | Example Query |
|---------|----------|---------------|
| `path_join` | file | "join /foo and bar/baz" |
| `base64_encode` | encoding | "base64 encode hello world" |
| `json_format` | formatting | "pretty print this JSON: {...}" |
| `word_count` | text | "how many words in ..." |
| `model_status` | system | "what models are running" (reads orchestrator_stack status) |

### 3.5 Safety Constraints

- **Max message length**: 200 chars. Longer messages are never intercepted.
- **Arithmetic eval**: Strict character whitelist (`[\d\s\+\-\*\/\.\(\)%]`) — no builtins, no names.
- **No side effects**: Interceptors must be pure functions (read-only). Any write/mutation must go through the full pipeline.
- **Fallthrough on failure**: If a handler returns `None`, the message falls through to normal routing.

### 3.6 Tests

```
tests/unit/test_script_interceptor.py
- test_timestamp_current_time
- test_timestamp_iso_format
- test_timestamp_unix_format
- test_arithmetic_simple_addition
- test_arithmetic_complex_expression
- test_arithmetic_rejects_non_numeric
- test_uuid_generation
- test_long_message_not_intercepted
- test_ambiguous_message_falls_through
- test_no_match_returns_unmatched
- test_handler_failure_falls_through
- test_register_custom_interceptor
```

### 3.7 Feature Flag

```python
# src/features.py
script_interception: bool = False  # Off by default — opt-in during validation period
```

### 3.8 Checklist

- [x] Create `src/api/routes/chat_pipeline/script_interceptor.py`
- [x] Wire into chat pipeline before graph dispatch (Stage 0 in `_handle_chat()`)
- [x] Add feature flag `script_interception`
- [x] Add telemetry: intercepted requests logged with pattern name and elapsed_ms
- [x] Write unit tests (29 tests, all passing)
- [ ] Add `model_status` interceptor that reads `orchestrator_stack.py status` output (deferred — future enhancement)
- [x] Tests passing (4219 existing + 29 new, 0 regressions)

---

## 4) Gap C: Cascading Tool Policy Resolution

### 4.1 Problem

`ToolPermissions` (`src/tool_registry.py:65-98`) implements flat allow/deny:
1. Check `forbidden_tools` (deny)
2. Check `allowed_tools` (allow)
3. Check `allowed_categories` + `web_access`

This is a **single layer**. As we add more agent tiers, delegation contexts, and task-specific constraints, we need the ability to stack multiple policy layers where each layer only narrows — never expands — the tool set.

OpenClaw implements a 5-layer cascading chain: Global → Provider → Agent → Group → Sandbox, with group-based tool expansion (`group:fs` → `read, write, edit, apply_patch`) and a "deny always wins" invariant.

### 4.2 Design

```python
# src/tool_policy.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence


# Tool group expansion — shorthand for common tool sets
TOOL_GROUPS: dict[str, frozenset[str]] = {
    "group:read": frozenset({"list_dir", "read_file", "search_files", "web_fetch"}),
    "group:write": frozenset({"write_file", "edit_file", "run_shell"}),
    "group:code": frozenset({"list_dir", "read_file", "search_files", "write_file", "edit_file", "run_shell"}),
    "group:data": frozenset({"query_db", "read_file", "search_files"}),
    "group:web": frozenset({"web_fetch", "web_search"}),
    "group:math": frozenset({"calculate", "plot"}),
    "group:all": frozenset(),  # Special: means "all tools" — expanded at resolution time
}


@dataclass(frozen=True)
class PolicyLayer:
    """A single layer in the policy chain.

    Rules:
    - `allow` expands the set (but only within what the previous layer allowed)
    - `deny` always removes, regardless of allow
    - Empty allow = "inherit everything from previous layer"
    - Both allow and deny can use group: prefixes
    """
    name: str
    allow: frozenset[str] = field(default_factory=frozenset)
    deny: frozenset[str] = field(default_factory=frozenset)

    def expand_groups(self, all_tools: frozenset[str]) -> tuple[frozenset[str], frozenset[str]]:
        """Expand group: prefixes in allow/deny sets."""
        expanded_allow: set[str] = set()
        for item in self.allow:
            if item.startswith("group:"):
                group = TOOL_GROUPS.get(item, frozenset())
                if item == "group:all":
                    expanded_allow.update(all_tools)
                else:
                    expanded_allow.update(group)
            else:
                expanded_allow.add(item)

        expanded_deny: set[str] = set()
        for item in self.deny:
            if item.startswith("group:"):
                group = TOOL_GROUPS.get(item, frozenset())
                expanded_deny.update(group)
            else:
                expanded_deny.add(item)

        return frozenset(expanded_allow), frozenset(expanded_deny)


def resolve_policy_chain(
    layers: Sequence[PolicyLayer],
    all_tools: frozenset[str],
) -> frozenset[str]:
    """Resolve a chain of policy layers into a final allowed tool set.

    Each layer narrows (never expands beyond) the previous result.
    Deny always wins at every layer.

    Args:
        layers: Ordered policy layers (outermost first).
        all_tools: Universe of all registered tool names.

    Returns:
        Final set of allowed tool names.
    """
    # Start with full tool universe
    current = all_tools

    for layer in layers:
        expanded_allow, expanded_deny = layer.expand_groups(all_tools)

        # Apply allow (intersect — can only narrow)
        if expanded_allow:
            current = current & expanded_allow

        # Apply deny (always removes)
        current = current - expanded_deny

    return current
```

### 4.3 Integration

**Replace `ToolPermissions.can_use_tool()` in `ToolRegistry`**

The existing `_permissions: dict[str, ToolPermissions]` becomes `_policy_chains: dict[str, list[PolicyLayer]]`.

```python
# In ToolRegistry.can_use_tool():
def can_use_tool(self, role: str, tool_name: str, context: dict | None = None) -> bool:
    """Check tool access through cascading policy chain."""
    if tool_name not in self._tools:
        return False

    # Build chain: global → role → context-specific
    chain = list(self._global_policies)  # Always present

    if role in self._role_policies:
        chain.extend(self._role_policies[role])

    # Task-specific constraints (e.g., read-only delegation)
    if context:
        if context.get("read_only"):
            chain.append(PolicyLayer(name="task:read_only", deny=frozenset({"group:write"})))
        if context.get("no_web"):
            chain.append(PolicyLayer(name="task:no_web", deny=frozenset({"group:web"})))

    all_tools = frozenset(self._tools.keys())
    allowed = resolve_policy_chain(chain, all_tools)
    return tool_name in allowed
```

**Backward compatibility**: The existing `ToolPermissions` dataclass and `load_permissions_from_registry()` can be adapted to emit `PolicyLayer` objects, so `model_registry.yaml` doesn't need changes.

### 4.4 Policy Chain for Current Tiers

| Layer | Source | Purpose |
|-------|--------|---------|
| **Global** | Hardcoded | Base deny list (e.g., never allow `raw_exec` regardless of role) |
| **Role** | `model_registry.yaml` `tool_permissions` | Role-based allow/deny (frontdoor gets `group:all`, workers get `group:read`) |
| **Task** | `TaskIR.constraints` | Per-task narrowing (read-only delegation, no-web tasks) |
| **Delegation** | Runtime | When B3 delegates to C-tier workers, inject constraints dynamically |

### 4.5 Edge Cases

- **Empty allow in all layers**: Results in full tool set (no restriction). This matches current behavior for unconfigured roles.
- **Conflicting allow/deny**: Deny always wins within the same layer, and layers only narrow. This is monotonically restrictive — mathematically impossible to accidentally grant elevated access.
- **Performance**: `resolve_policy_chain()` is O(layers * tools). With ~10 tools and ~4 layers, this is negligible (<1us).

### 4.6 Tests

```
tests/unit/test_tool_policy.py
- test_empty_chain_allows_all
- test_single_deny_removes_tool
- test_deny_wins_over_allow_in_same_layer
- test_layers_only_narrow_never_expand
- test_group_expansion_read
- test_group_expansion_write
- test_group_expansion_all
- test_nested_deny_across_layers
- test_role_policy_from_registry_yaml
- test_task_read_only_constraint
- test_delegation_injects_constraint
- test_backward_compat_with_tool_permissions
- test_unknown_group_ignored
```

### 4.7 Feature Flag

```python
# src/features.py
cascading_tool_policy: bool = False  # Off by default — validate chain equivalence first
```

### 4.8 Checklist

- [x] Create `src/tool_policy.py` with `PolicyLayer` and `resolve_policy_chain()`
- [x] Define `TOOL_GROUPS` matching current tool categories
- [x] Add `_global_policies` and `_role_policies` to `ToolRegistry`
- [x] Add adapter: `ToolPermissions` → `PolicyLayer` (backward compat via `permissions_to_policy()`)
- [x] Add `context` parameter to `ToolRegistry.can_use_tool()`
- [x] Wire task-level constraints (`read_only`, `no_web` context keys)
- [x] Add feature flag `cascading_tool_policy`
- [x] Write equivalence test: old `can_use_tool()` == new chain (`test_equivalence_with_legacy`)
- [x] Write unit tests (27 tests, all passing)
- [x] Tests passing (4246 total, 0 regressions from changes)

---

## 5) Implementation Sequence

```
Gap A (Credential Redaction)    ←── no dependencies, ship first (safety)
    ↓
Gap B (Script Interception)     ←── independent, ship second (savings)
    ↓
Gap C (Cascading Tool Policy)   ←── depends on understanding tool registry deeply
```

Gaps A and B are fully independent and can be implemented in parallel. Gap C touches `ToolRegistry` internals and benefits from the familiarity gained working on Gap A's integration.

---

## 6) Success Metrics

| Gap | Metric | Target |
|-----|--------|--------|
| A — Redaction | Zero credential leaks in 30-day audit of tool outputs | 0 leaks |
| A — Redaction | False positive rate on existing test suite outputs | < 2% |
| B — Interception | Fraction of simple queries resolved without model call | > 5% of total (measured over 7 days) |
| B — Interception | Latency for intercepted queries | < 1ms |
| C — Policy | Equivalence with current `can_use_tool()` for all existing roles | 100% match |
| C — Policy | New delegation constraints expressible without code changes | Yes (config-only) |

---

## 7) Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Credential redaction false positives mask legitimate output (e.g., SHA256 hashes in code) | MEDIUM | LOW | Log all redactions; 64+ char hex threshold; feature flag |
| R2 | Script interception answers incorrectly for ambiguous queries | LOW | MEDIUM | 200-char limit; strict regex; fallthrough on any uncertainty |
| R3 | Arithmetic eval in interceptor is exploitable | LOW | HIGH | Strict char whitelist; no builtins; empty namespace; tested |
| R4 | Policy chain migration breaks existing role permissions | LOW | HIGH | Equivalence test required before flag-on; old path retained |
| R5 | New TOOL_GROUPS don't match actual tool names in registry | LOW | MEDIUM | Validate group contents against loaded tools at startup |

---

## 8) References

- [OpenClaw Architecture Deep Dive (DeepWiki)](https://deepwiki.com/openclaw/openclaw/15.1-architecture-deep-dive)
- [OpenClaw Three-Layer Design (BetterLink)](https://eastondev.com/blog/en/posts/ai/20260205-openclaw-architecture-guide/)
- [Clawzempic API Documentation](https://api.clawzempic.ai/docs)
- [Clawzempic Routing Documentation](https://www.clawzempic.ai/docs/routing)

---

## 9) Onboarding Investigation Commands

```bash
# Understand current tool registry and permissions
python3 -c "
from src.tool_registry import ToolRegistry, load_from_yaml
r = ToolRegistry()
r.load_permissions_from_registry('orchestration/model_registry.yaml')
load_from_yaml(r, 'orchestration/tool_registry.yaml')
for role in ['frontdoor', 'coder_escalation', 'worker_general']:
    tools = r.list_tools(role)
    print(f'{role}: {len(tools)} tools — {[t[\"name\"] for t in tools]}')"

# See current security patterns
cat src/repl_environment/security.py

# Check existing script registry entries
ls orchestration/script_registry/ 2>/dev/null || echo "No script registry directory yet"

# Check chat pipeline entry point for interception hookpoint
grep -n "run_task\|dispatch\|graph" src/api/routes/chat_pipeline/*.py | head -20

# Check tool invocation for output filter hookpoint
grep -n "handler\|result" src/tool_registry.py | head -20
```
