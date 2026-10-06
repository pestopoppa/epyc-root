# HS-4 P6 source contract proposal — shared read-only exploration tools

**Source basis:** APP published 041ec98abba9c93c9b9cf75c07fa6a20ecdee775; Research accepted source pin 12f51c0e8b85f81576502377e0db9d678fbf1029; ROOT current published e0f766c91ae1455878589683aaf1d0ceca857431. Source-only review; no code, import, execution, catalog change, or live MCP operation.

The current P6 task in ROOT handoffs/active/harness-selection-and-integration.md names four shared tools: code_search, peek/read_range, grep, and peek_grep. It says the autokernel seat should retain only its profiling tools. Outline is an actor-only fifth utility today and is a proposed additive compatibility move, not part of the current four-tool task text. Its request for an explicit root is material to safety and behavior.

## Exact source mismatch

- src/mcp_server.py:44-50 runs as a standalone stdio FastMCP process. The OpenCode plugin stamps session_id; tools either ignore it or send it to /chat. There is no current MCP-to-REPLEnvironment resolver or request task-scope propagation.
- src/repl_environment/task_root.py:233-268 stores task roots in a ContextVar or process environment. resolve_task_path() only uses that state for relative paths; absolute paths are returned as realpaths. The standalone MCP process therefore cannot inherit a REPL request's scope merely because it receives the stamped session id.
- src/repl_environment/file_exploration.py:93-140 implements _peek over REPL context or an optional file; file reads first call self._validate_file_path, then resolve under the task-root. Its page unit is characters, not lines. _grep likewise searches the current REPL context when no file is named and uses REPL buffers, logs, limits, and research tracking.
- src/repl_environment/code_search.py:124-153 selects index-free search only when a task root is active; otherwise it uses shared ColGREP/NextPLAID clients. Its documented default limit is five. An arbitrary actor root is not the indexed production corpus, so directly wrapping this method would not preserve the actor's root-scoped search.
- src/repl_environment/combined_ops.py:280-315 gates _peek_grep on REPL_COMBINED_OPS, uses REPL path validation and state, then reads and regex-matches a whole file. A copied version in mcp_server.py would create the second implementation P6 is meant to remove.
- The autokernel seat's actor_tools_mcp.py has root-argument functions and its own caps: READ_DEFAULT_LINES=120, READ_MAX_LINES=200, READ_MAX_LINE_CHARS=400, GREP_DEFAULT_HITS=40, GREP_MAX_HITS=80, GREP_MAX_CONTEXT=3, GREP_MAX_LINE_CHARS=240, GREP_MAX_FILE_BYTES=4 MiB. read_range uses line ranges, which differs from the REPL's character-page contract.

## Compatibility gap: actor-only outline

At the accepted Research pin, actor_opencode_config.py:64 exposes six MCP tools, not five: read_range, grep, outline, code_search, profile_top, symbol_annotate. Its generated system prompt at :374 says “Locate before you read: outline”; actor_tools_mcp.py:574 also recommends outline as a code_search fallback. The P6 task names four shared tools and says the actor server shrinks to two profiling tools. Removing outline would leave an existing prompt and fallback pointing at a tool that no longer exists.

**Recommendation:** extract the bounded outline parser into the same shared read-only service and expose it from the orchestrator MCP as a fifth utility; update the P6 acceptance contract to move outline with the other file/code tools, then preserve the explicit catalog-growth gate. Do not register or remove actor catalog entries before the catalog-change gate has passed its required two inference reruns. This is an additive compatibility fix, not an operator-facing semantic choice. Keeping an actor-side outline wrapper would preserve behavior but would contradict the “two profiling tools only” endpoint.

## Engineering recommendation

Extract the shared, pure read/search/outline operations into one orchestrator module with explicit root and relative path parameters. Keep thin adapters:

1. The REPL adapter derives its effective read set from the existing task scope (root plus permitted read_roots) or current project root, and retains context-only behavior for calls that omit a file path.
2. The MCP adapter requires the caller's root, validates it as a read scope, and passes the same root/path to the shared service. It must not use session_id to guess a REPL context or depend on a process-global environment override.
3. The shared resolver canonicalizes root and target, rejects traversal and symlink escapes before opening, and enforces one documented byte/line cap set. code_search must be root-bound; it cannot silently fall back to a global indexed corpus when the caller supplies another root.

Preserve existing REPL public return semantics in its adapter, especially character offset paging and the no-file context form. Give MCP the actor's bounded line/range and grep result format, using the same shared read/search core; avoid claiming text output is byte-for-byte identical where the unit (characters versus lines) differs. Treat output truncation markers as part of the contract.

Do not decide how the MCP root is selected by a live actor without source proving that root's identity and allowed location. The engineering default is an explicit per-call root with existing task-root read-scope validation; no session-context lookup, new global root, or environment bypass.

## Acceptance examples

- root=/tmp/lane-a, path=src/x.py reads only /tmp/lane-a/src/x.py; ../lane-b/secret and a symlink beneath lane-a that resolves outside are refused.
- A REPL peek(n=500, offset=100) still returns the same 500-character page from its request context; an MCP read_range(path, start_line=1, num_lines=200) stays line-based and caps long lines at 400 characters.
- With root=/tmp/lane-a, code_search can never return a hit from the project-wide ColGREP corpus or another lane.
- grep respects the shared max-hit/context/file-byte caps and reports truncation; peek_grep cannot read an unbounded file or bypass the same path fence.

## Blast/callers to map before implementation

Exact APP callers are _peek, _grep in src/repl_environment/file_exploration.py; _code_search and its task-root/ColGREP/NextPLAID choices in src/repl_environment/code_search.py; _peek_grep in src/repl_environment/combined_ops.py; MCP registration and session_id contract in src/mcp_server.py; actor MCP implementations, caps, and config in Research scripts/kernel_rnd/autokernel/loop/actor_tools_mcp.py and actor_opencode_config.py. The child implementation task should also map _validate_file_path, TaskScope.read_denial, knowledge-fence checks, resolve_task_path, actor tests for traversal/symlink/caps/outline, OpenCode MCP_TOOLS wiring, generated actor prompt text, and tool names that the server already publishes.

**Review boundary:** This is a design/source contract. The next source-only implementation may extract the bounded pure exploration core and thin REPL adapters; map TaskScope.read_denial, knowledge-fence compatibility, existing validation behavior, and exact callers before editing. Do not change the active MCP or actor catalog/config until the explicit catalog gate has passed two inference reruns. Parent/root owns acceptance text and row changes.
