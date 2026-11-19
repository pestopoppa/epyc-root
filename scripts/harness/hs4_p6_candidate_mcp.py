#!/usr/bin/env python3
"""Isolated P6 candidate additions; never imported by the active MCP server.

Launch from a pinned orchestrator checkout with its Python environment. The
caller must supply admitted read roots. Root-bound search is an explicit lexical
candidate contract; actor compatibility and live catalog acceptance remain gated.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def register_exploration_tools(server, read_roots, *, core=None):
    """Add bounded tools to a row-owned server, admitting only declared read roots."""
    if core is None:
        from src.repl_environment import exploration_core as core

    admitted = tuple(Path(root).resolve(strict=True) for root in read_roots)
    if not admitted or any(not root.is_dir() for root in admitted):
        raise ValueError("at least one existing read-root directory is required")

    def scope(root):
        if not os.path.isabs(root):
            raise ValueError("root must be absolute")
        candidate = Path(root).resolve(strict=True)
        if not candidate.is_dir() or not any(
            candidate == base or base in candidate.parents for base in admitted
        ):
            raise PermissionError("root is outside the admitted read roots")
        return str(candidate)

    @server.tool()
    def code_search(root: str, query: str, k: int = 5, session_id: str = "") -> dict:
        """Index-free lexical search under an admitted root; at most 20 paths/ranges."""
        from scripts.harness.hs4_p6_root_search import code_search as search
        return search(scope(root), query, k, core=core)

    @server.tool()
    def read_range(root: str, path: str, start_line: int = 1,
                   num_lines: int = 120, session_id: str = "") -> str:
        """Read a file under an admitted root; at most 200 lines of 400 characters."""
        return core.read_range(scope(root), path, start_line, num_lines)

    @server.tool()
    def peek(root: str, path: str, n: int = 500, offset: int = 0,
             session_id: str = "") -> str:
        """Read a character page under an admitted root; at most 80000 characters."""
        if not 1 <= n <= 80000:
            raise ValueError("n must be between 1 and 80000")
        return core.read_file_page(scope(root), path, n, offset)

    def matches(root, path, pattern, context, max_hits):
        result = core.grep_file(
            scope(root), path, pattern, context_lines=max(0, min(context, 3)),
            max_hits=max(1, min(max_hits, core.GREP_MAX_HITS)),
            max_context_chars=7 * core.GREP_MAX_LINE_CHARS,
        )
        return {
            "matches": [{"line_num": match.line_num, "line": match.line,
                         "context": match.context} for match in result.matches],
            "total": result.total, "truncated": result.truncated,
            "engine": result.engine,
        }

    @server.tool()
    def grep(root: str, path: str, pattern: str, context: int = 2,
             max_hits: int = 40, session_id: str = "") -> dict:
        """Search one file, capped at 80 hits, 3 context lines and 4 MiB input."""
        return matches(root, path, pattern, context, max_hits)

    @server.tool()
    def peek_grep(root: str, path: str, pattern: str, context: int = 2,
                  max_hits: int = 40, session_id: str = "") -> dict:
        """Return bounded matching lines and surrounding text from one rooted file."""
        return matches(root, path, pattern, context, max_hits)

    @server.tool()
    def outline(root: str, path: str, session_id: str = "") -> str:
        """Return the shared bounded source outline (at most 300 definitions)."""
        return core.outline_file(scope(root), path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orchestrator-root", required=True, type=Path)
    roots = parser.add_mutually_exclusive_group(required=True)
    roots.add_argument("--read-root", action="append", type=Path)
    roots.add_argument("--actor-root", type=Path, help="bind actor exploration calls to this root")
    args = parser.parse_args()
    checkout = args.orchestrator_root.resolve(strict=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.path.insert(0, str(checkout))
    from src import mcp_server

    if Path(mcp_server.__file__).resolve() != checkout / "src/mcp_server.py":
        raise RuntimeError("MCP server did not load from the declared checkout")
    if args.actor_root is not None:
        from scripts.harness.hs4_p6_actor_mcp import register_actor_tools
        register_actor_tools(mcp_server.mcp, args.actor_root)
    else:
        register_exploration_tools(mcp_server.mcp, args.read_root)
    mcp_server._get_plugin_loader()
    mcp_server.mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
