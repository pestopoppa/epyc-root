"""Index-free explicit-root search for the isolated P6 candidate.

Pure lexical retrieval, not ColBERT equivalence. No service clients, subprocesses,
index reads or index writes. Admission belongs to the caller. Bounded file reads
and path confinement use the same exploration core as the file-tool adapters.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

MAX_ENTRIES = 4096
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_K = 20
EXTENSIONS = frozenset({'.py', '.c', '.cc', '.cpp', '.h', '.hpp', '.rs', '.go',
                        '.java', '.js', '.ts', '.txt', '.md', '.toml', '.json',
                        '.yaml', '.yml', '.cfg', '.cxx'})


def code_search(root: str, query: str, k: int = 5, *, core) -> dict:
    """Rank lexical hits; return bounded paths/ranges only with coverage metadata."""
    if not query.strip() or len(query) > 1024:
        raise ValueError('query must contain 1..1024 characters, including non-whitespace')
    if isinstance(k, bool) or not isinstance(k, int):
        raise ValueError('k must be an integer')
    k = max(1, min(k, MAX_K))
    base = Path(core.resolve_in_root(root, '.'))
    terms = tuple(dict.fromkeys(re.findall(r'\w+', query.lower())))
    if not terms:
        raise ValueError('query must contain a word')
    hits = []
    visited = scanned = skipped = consumed = 0
    truncated = False

    def entries(directory):
        # Streaming traversal avoids materializing arbitrarily large directories.
        nonlocal visited, truncated, skipped
        with os.scandir(directory) as stream:
            for entry in stream:
                visited += 1
                if visited > MAX_ENTRIES:
                    truncated = True
                    return
                if entry.name.startswith('.') or entry.is_symlink():
                    skipped += 1
                    continue
                if entry.is_dir(follow_symlinks=False):
                    # Iterative traversal below bounds Python call-stack usage.
                    yield Path(entry.path), True
                elif entry.is_file(follow_symlinks=False):
                    yield Path(entry.path), False
                else:
                    skipped += 1

    pending = [base]
    while pending and not truncated:
        directory = pending.pop()
        try:
            for path, is_dir in entries(directory):
                if is_dir:
                    pending.append(path)
                    continue
                if path.suffix.lower() not in EXTENSIONS:
                    skipped += 1
                    continue
                rel = path.relative_to(base).as_posix()
                try:
                    real = core.resolve_in_root(str(base), rel)
                    info = os.stat(real)
                    if not stat.S_ISREG(info.st_mode) or info.st_size > core.MAX_FILE_BYTES:
                        skipped += 1
                        continue
                    remaining = MAX_TOTAL_BYTES - consumed
                    if info.st_size > remaining:
                        truncated = True
                        break
                    # Charge attempted reads too, including unreadable/changing files.
                    consumed += info.st_size
                    text, _ = core._read_text(str(base), rel, max_bytes=min(core.MAX_FILE_BYTES, remaining, info.st_size))
                except (OSError, ValueError):
                    skipped += 1
                    continue
                scanned += 1
                if '\x00' in text:
                    skipped += 1
                    continue
                low = text.lower()
                score = sum(10 * (term in rel.lower()) + low.count(term) for term in terms)
                if not score:
                    continue
                lines = text.splitlines()
                first = next((i for i, line in enumerate(lines, 1)
                              if any(term in line.lower() for term in terms)), 1)
                hits.append({'path': rel, 'score': score,
                             'start_line': max(1, first - 20),
                             'end_line': min(max(1, len(lines)), first + 20)})
                hits.sort(key=lambda hit: (-hit['score'], hit['path']))
                del hits[k:]
        except (OSError, ValueError):
            skipped += 1
    return {'engine': 'root-lexical', 'matches': hits, 'truncated': truncated,
            'entries_visited': min(visited, MAX_ENTRIES), 'files_scanned': scanned,
            'bytes_read_budget_used': consumed, 'skipped': skipped}
