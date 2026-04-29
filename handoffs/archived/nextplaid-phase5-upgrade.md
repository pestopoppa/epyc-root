# Handoff: NextPLAID Phase 5 — LateOn-Code 130M + AST Chunking + ColGrep

## Status

**COMPLETE** (ColGrep BLOCKED) — Started 2026-02-13, completed 2026-02-13

Model upgrade + AST chunking fully operational. ColGrep blocked by upstream bug (v1.0.6).

## Scope

Three workstreams:
1. **Model upgrade**: LateOn-Code-edge (17M, 48-dim) → LateOn-Code (130M, 128-dim). +11.2% on MTEB Code (74.12 vs 66.64).
2. **AST chunking**: tree-sitter Python parser extracts semantic code units (functions, classes, methods) instead of naive 1800-char splits. FallbackChunker for non-Python files.
3. **ColGrep CLI**: Agent-facing hybrid search tool from LightOn (same team as NextPLAID). Uses LateOn-Code model for CLI code search.

## Dependency Graph

```
Step 0: Handoff doc (this file)              ─┐
Step 1: Install deps (tree-sitter, colgrep)  ─┤ parallel
Step 2: ColGrep storage safety               ─┘
Step 3: Upgrade container config             ─┐ requires Steps 1-2
Step 4: AST chunker + update indexing        ─┤ requires Step 1
Step 5: Search result formatting + tests     ─┘ requires Step 4
Step 6: Stop/delete/restart/reindex          ── requires Steps 3-5
Step 7: ColGrep init + index                 ── requires Steps 1-2 (independent of 3-6)
Step 8: Verification                         ── requires Steps 6-7
Step 9: Documentation                        ── requires Step 8
```

## Files Modified

| File | Change |
|------|--------|
| `scripts/server/orchestrator_stack.py` | Model name LateOn-Code-edge → LateOn-Code (2 lines) |
| `orchestration/model_registry.yaml` | nextplaid_code entry: model, memory, notes, launch cmd |
| `scripts/nextplaid/index_codebase.py` | Delete chunk_file, import ast_chunker, extend metadata |
| `scripts/nextplaid/reindex_changed.py` | Delete chunk_file, import ast_chunker, extend metadata |
| `src/repl_environment/code_search.py` | Docstring, result formatting with unit_name/unit_type |
| `tests/unit/test_code_search.py` | Mock metadata, new tests for structured fields |

## Files Created

| File | Purpose |
|------|---------|
| `scripts/nextplaid/ast_chunker.py` | Tree-sitter AST parser + FallbackChunker |
| `handoffs/active/nextplaid-phase5-upgrade.md` | This handoff |

## Resume Commands

```bash
# 1. Verify tree-sitter installed
python3 -c "import tree_sitter; import tree_sitter_python; print('OK')"

# 2. Verify colgrep
colgrep --version

# 3. Check container status
python3 scripts/server/orchestrator_stack.py status

# 4. If containers need restart after config changes:
python3 scripts/server/orchestrator_stack.py stop nextplaid-code nextplaid-docs
rm -rf /mnt/raid0/llm/claude/cache/next-plaid/code-indices/*
rm -rf /mnt/raid0/llm/claude/cache/next-plaid/docs-indices/*
rm -f /mnt/raid0/llm/claude/cache/next-plaid/.last_indexed_commit
python3 scripts/server/orchestrator_stack.py start --hot-only

# 5. Full reindex
python3 scripts/nextplaid/index_codebase.py --reindex

# 6. ColGrep index
cd /mnt/raid0/llm/claude && colgrep init . -y

# 7. Run tests
pytest tests/unit/test_code_search.py -v

# 8. Full gates
make gates
```

## Completion Checklist

- [x] tree-sitter + tree-sitter-python installed in pace-env
- [x] colgrep binary installed (v1.0.6) — **BLOCKED**: upstream Rust panic on ONNX model loading
  - **RESOLVED 2026-04-29**: upgraded to v1.2.0 (release 2026-04-10). Changelog: "panic-based error output during GPU initialization is replaced with clear fallback messages" + new `--force-cpu` / `NEXT_PLAID_FORCE_CPU` knob. Binary at `/mnt/raid0/llm/UTILS/bin/colgrep`. Validated `init` + `search` on small sample — falls back to CPU cleanly, returns ranked results.
- [x] ColGrep storage paths on RAID (symlink ~/.config/colgrep → RAID)
  - **Note 2026-04-29**: v1.2.0 default index path is `~/.local/share/colgrep/indices/` (data), `~/.config/colgrep` (config). Re-symlink to RAID before any orchestrator-scale index run.
- [x] orchestrator_stack.py updated with LateOn-Code model name
- [x] model_registry.yaml nextplaid_code entry updated
- [x] ast_chunker.py created with PythonChunker + FallbackChunker
- [x] index_codebase.py uses ast_chunker, passes new metadata fields
- [x] reindex_changed.py uses ast_chunker, passes new metadata fields
- [x] code_search.py formats unit_name/unit_type/signature in results
- [x] test_code_search.py updated with new mock metadata + new tests
- [x] Containers restarted with LateOn-Code 130M (128-dim, ~31GB RAM)
- [x] Full reindex with AST chunks complete (6583 code + 1379 docs = 7962 chunks)
- [ ] ColGrep indexed codebase — was BLOCKED on colgrep v1.0.6 panic; **unblocked 2026-04-29** by v1.2.0 upgrade. Full-codebase index not yet run — deferred pending REPL-integration decision (additive new tool vs replacement for existing `code_search()`/`doc_search()`). See `handoffs/active/repl-turn-efficiency.md` intake-355 entry.
- [x] pytest tests pass (20/20)
- [x] CHANGELOG.md updated
- [x] nextplaid-code-retrieval.md updated with Phase 5
- [x] progress/2026-02/2026-02-13.md updated
- [x] docs/chapters/11, 12, 15 updated
- [x] CLAUDE.md Component Flow updated
- [x] make gates passes

## Future: Docker → Native Migration

NextPLAID doesn't require Docker. `pip install next-plaid` installs the same Rust core via PyO3 bindings. Benefits of migrating:
- Eliminate Docker overhead (~100MB container runtime + volume mount I/O indirection)
- Manage via `orchestrator_stack.py` with same `start_server`/health/reload patterns as llama-servers
- Remove Docker as a dependency entirely
- No significant downsides — Docker only provides isolation we don't need

Migration would involve:
1. `pip install next-plaid` in pace-env
2. Replace Docker `DOCKER_SERVICES` in `orchestrator_stack.py` with native process launch (similar to embedding servers)
3. Update health check paths
4. Test reindex pipeline against native server

## Blocked Tasks Update

Update `orchestration/BLOCKED_TASKS.md` on completion.
