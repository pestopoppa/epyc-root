# Handoff: REPL Permission Tiers for Filesystem Management

**Created:** 2026-01-24
**Status:** Ready to implement
**Priority:** Low (future enhancement)
**Estimated Effort:** Medium

---

## Summary

Implement configurable permission tiers for the REPL environment to enable filesystem management tasks while maintaining security for default operations.

---

## Motivation

Currently the REPL sandbox blocks ALL filesystem operations (open, write, delete). This is appropriate for default orchestration but limits use cases like:
- Filesystem management (cleanup, organization)
- Code generation with file creation
- Batch file operations

A tiered permission system would allow controlled access based on task requirements.

---

## Proposed Design

### Permission Tiers

| Tier | Name | Read | Write | Delete | Shell | Use Case |
|------|------|------|-------|--------|-------|----------|
| 0 | `readonly` | ✓ | ✗ | ✗ | Read-only | Default (safe exploration) |
| 1 | `write_safe` | ✓ | Allowed paths | ✗ | Read-only | Code generation, file creation |
| 2 | `write_any` | ✓ | Any path | ✗ | Limited | Project work |
| 3 | `admin` | ✓ | ✓ | ✓ (confirm) | Full | Filesystem management |

### Implementation Plan

#### 1. Add PermissionTier Enum

```python
# src/repl_environment.py
class PermissionTier(Enum):
    READONLY = 0      # Default: read operations only
    WRITE_SAFE = 1    # Write to allowed paths only
    WRITE_ANY = 2     # Write to any path (with validation)
    ADMIN = 3         # Full access (with confirmation)
```

#### 2. Update REPLConfig

```python
@dataclass
class REPLConfig:
    timeout_seconds: int = 600
    permission_tier: PermissionTier = PermissionTier.READONLY
    allowed_write_paths: list[str] = field(default_factory=lambda: [
        "/mnt/raid0/llm/tmp/",
        "/mnt/raid0/llm/claude/tmp/",
    ])
    require_delete_confirmation: bool = True
```

#### 3. Add Write/Delete Tools

```python
def _write_file(self, path: str, content: str) -> str:
    """Write content to a file (requires WRITE_SAFE or higher)."""
    if self.config.permission_tier < PermissionTier.WRITE_SAFE:
        return "[ERROR: Write permission not granted]"

    # Validate path based on tier
    if self.config.permission_tier == PermissionTier.WRITE_SAFE:
        if not any(path.startswith(p) for p in self.config.allowed_write_paths):
            return f"[ERROR: Path not in allowed write paths]"

    # Write file...

def _delete_file(self, path: str) -> str:
    """Delete a file (requires ADMIN tier)."""
    if self.config.permission_tier < PermissionTier.ADMIN:
        return "[ERROR: Delete permission not granted]"

    if self.config.require_delete_confirmation:
        # Store pending deletion, require second call to confirm
        ...
```

#### 4. Update run_shell for Higher Tiers

```python
# Expand allowed commands based on tier
SHELL_COMMANDS_BY_TIER = {
    PermissionTier.READONLY: {"ls", "cat", "head", "grep", "git status"},
    PermissionTier.WRITE_SAFE: {"ls", "cat", "head", "grep", "git", "mkdir", "cp"},
    PermissionTier.WRITE_ANY: {"ls", "cat", "head", "grep", "git", "mkdir", "cp", "mv"},
    PermissionTier.ADMIN: None,  # All commands allowed
}
```

#### 5. API Integration

```python
# ChatRequest model
class ChatRequest(BaseModel):
    # ... existing fields ...
    permission_tier: str = Field(
        default="readonly",
        description="Permission tier: readonly, write_safe, write_any, admin"
    )
```

---

## Security Considerations

1. **Path Escapes**: Always resolve symlinks with `os.path.realpath()` before validation
2. **Command Injection**: Sanitize shell arguments even with higher tiers
3. **Audit Logging**: Log ALL write/delete operations to `agent_audit.log`
4. **Rate Limiting**: Consider rate limits for destructive operations
5. **Rollback**: Consider snapshot/undo for ADMIN tier operations

---

## Testing Plan

1. Unit tests for each permission tier
2. Integration tests for cross-tier escalation
3. Security tests for path escape attempts
4. Audit log verification tests

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/repl_environment.py` | Add PermissionTier, write/delete tools |
| `src/api.py` | Add permission_tier to ChatRequest |
| `src/prompt_builders.py` | Update tool docs per tier |
| `docs/ARCHITECTURE.md` | Document permission system |

---

## Dependencies

None - can be implemented independently.

---

## Acceptance Criteria

- [ ] All 4 permission tiers implemented
- [ ] write_file() and delete_file() tools working
- [ ] run_shell() respects tier restrictions
- [ ] Audit logging for all write/delete ops
- [ ] Unit tests pass for each tier
- [ ] Documentation updated
