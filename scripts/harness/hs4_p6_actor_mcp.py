"""Isolated fixed-root actor adapters; no production catalog registration.

The actor owns its root at launch. File parsing and regex matching stay in the
shared exploration core. Search deliberately retains the labeled lexical engine.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

MAX_ENTRIES = 4096
MAX_TOTAL_BYTES = 16 * 1024 * 1024


def grep_tree(root, pattern, path='.', max_hits=40, context=0, *, core):
    """Render bounded file/directory grep using the shared per-file regex engine."""
    if not pattern:
        raise ValueError('pattern must be non-empty')
    from src.repl_environment import safe_regex
    safe_regex.compile(pattern)
    target = Path(core.resolve_in_root(root, path))
    root = str(Path(root).resolve(strict=True))
    limit, context = max(1, min(max_hits, 80)), max(0, min(context, 3))
    out = [f'grep /{pattern}/ in {os.path.relpath(target, root)} [python-re]']
    pending = [target]
    entries = charged = total = shown = skipped = 0
    partial = False
    while pending:
        current = pending.pop()
        try:
            current = Path(core.resolve_in_root(root, str(current)))
            if current.is_dir():
                with os.scandir(current) as stream:
                    for entry in stream:
                        entries += 1
                        if entries > MAX_ENTRIES:
                            partial = True
                            break
                        if entry.name.startswith('.') or entry.is_symlink():
                            skipped += 1
                            continue
                        pending.append(Path(entry.path))
                if partial:
                    break
                continue
            info = current.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > core.MAX_FILE_BYTES:
                if current == target:
                    raise ValueError('grep requires a regular file of at most 4 MiB')
                skipped += 1
                continue
            remaining = MAX_TOTAL_BYTES - charged
            if info.st_size > remaining:
                partial = True
                break
            charged += info.st_size
            rel = os.path.relpath(current, root)
            result = core.grep_file(
                root, rel, pattern, context_lines=context, max_hits=limit - shown,
                ignore_case=False, splitlines=True, capture_spans=True,
                max_bytes=min(info.st_size, remaining, core.MAX_FILE_BYTES),
                max_context_chars=7 * core.GREP_MAX_LINE_CHARS,
            )
            if '\x00' in result.source_text:
                skipped += 1
                continue
            total += result.total
            for match in result.matches:
                if shown >= limit:
                    break
                # Always render the actual hit, even if preceding context was capped.
                start = max(1, match.line_num - context)
                before, after = [], []
                for i, line in enumerate(match.context_lines, start):
                    if i == match.line_num:
                        continue
                    rendered = f'{rel}:{i}- {line[:240]}'
                    (before if i < match.line_num else after).append(rendered)
                out.extend(before)
                out.append(f'{rel}:{match.line_num}: {match.line[:240]}')
                out.extend(after)
                shown += 1
            if shown >= limit:
                partial = bool(pending) or total > shown
                break
        except (OSError, ValueError):
            # Invalid regex must be an error, never converted into a false no-match.
            if current == target and not target.is_dir():
                raise
            skipped += 1
    if not total:
        out.append('no matches')
    if partial:
        out.append(f'[truncated: showing {shown} of {total}+ matches; narrow the pattern or path]')
    else:
        out.append(f'[{total} match(es)]')
    if skipped:
        out.append(f'[skipped {skipped} entries; coverage incomplete]')
    return '\n'.join(out)


def register_actor_tools(server, root, *, core=None, research_root=None):
    """Expose the actor's four exploration names with a launch-bound root."""
    if core is None:
        from src.repl_environment import exploration_core as core
    from scripts.harness.hs4_p6_shared_core import candidate_core, DEFAULT_RESEARCH_ROOT
    core = candidate_core(core, research_root=research_root or DEFAULT_RESEARCH_ROOT)
    fixed = Path(root)
    if not fixed.is_absolute() or not fixed.is_dir():
        raise ValueError('actor root must be an existing absolute directory')
    fixed = str(fixed.resolve(strict=True))

    @server.tool()
    def read_range(path: str, start_line: int = 1, num_lines: int = 120,
                   session_id: str = '') -> str:
        """Read one rooted file with numbered lines; capped at 200 lines/400 chars."""
        return core.read_range(fixed, path, start_line, num_lines)

    @server.tool()
    def grep(pattern: str, path: str = '.', max_hits: int = 40,
             context: int = 0, session_id: str = '') -> str:
        """Case-sensitive regex search in rooted files/directories; at most 80 hits."""
        return grep_tree(fixed, pattern, path, max_hits, context, core=core)

    @server.tool()
    def outline(path: str, session_id: str = '') -> str:
        """List shared bounded source definitions; at most 300 entries."""
        return core.outline_file(fixed, path)

    @server.tool()
    def code_search(query: str, k: int = 6, session_id: str = '') -> str:
        """Index-free lexical search, not semantic ColGREP; k capped at 10."""
        from scripts.harness.hs4_p6_root_search import code_search as search
        result = search(fixed, query, max(1, min(k, 10)), core=core)
        out = [f'code_search {query!r} (top {max(1, min(k, 10))}) [root-lexical]']
        for hit in result['matches']:
            out.append(f"{hit['path']}  lines {hit['start_line']}-{hit['end_line']}  score {hit['score']}")
        if not result['matches']:
            out.append('no results')
        if result['truncated'] or result['skipped']:
            out.append('[coverage incomplete: bounded scan or skipped entries]')
        out.append('[paths + line ranges only; read with read_range]')
        return '\n'.join(out)
