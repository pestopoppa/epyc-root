#!/usr/bin/env python3
"""Rewrite cross-doc markdown links in site_src/ for MkDocs build.

Each source file in site_src/ came from a known epyc-root-relative path
(wiki/, research/deep-dives/, repos/<sibling>/docs/chapters or guides).
Links inside those files were written assuming they'd resolve relative
to their original location. For the published site they need to either:

1. Point at a sibling published page (rewrite to relative site path), or
2. Point at GitHub for unpublished content (handoffs/, progress/, etc.)

Run AFTER scripts/docs/build-site-src.sh and BEFORE `mkdocs build`.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE_SRC = ROOT / "site_src"
ORCH_REPO = Path(os.environ.get("ORCH_REPO", str(ROOT / "repos" / "epyc-orchestrator")))
RES_REPO = Path(os.environ.get("RES_REPO", str(ROOT / "repos" / "epyc-inference-research")))

GH_ROOT = "https://github.com/pestopoppa/epyc-root/blob/main"
GH_ORCH = "https://github.com/pestopoppa/epyc-orchestrator/blob/main"
GH_RES = "https://github.com/pestopoppa/epyc-inference-research/blob/main"
GH_LLAMA = "https://github.com/pestopoppa/llama.cpp/blob/production-consolidated-v5"


def build_published_map() -> dict[str, str]:
    """Map epyc-root-relative source path → site_src-local path."""
    m: dict[str, str] = {}

    wiki_dir = ROOT / "wiki"
    if wiki_dir.exists():
        for p in wiki_dir.glob("*.md"):
            if p.name == "INDEX.md":
                continue
            m[f"wiki/{p.name}"] = f"topics/{p.name}"

    dd_dir = ROOT / "research" / "deep-dives"
    if dd_dir.exists():
        for p in dd_dir.glob("*.md"):
            if p.name == "INDEX.md":
                continue
            m[f"research/deep-dives/{p.name}"] = f"deep-dives/{p.name}"

    orch_chapters = ORCH_REPO / "docs" / "chapters"
    if orch_chapters.exists():
        for p in orch_chapters.glob("*.md"):
            if p.name == "INDEX.md":
                continue
            m[f"epyc-orchestrator/docs/chapters/{p.name}"] = f"subsystems/orchestrator/{p.name}"

    res_chapters = RES_REPO / "docs" / "chapters"
    if res_chapters.exists():
        for p in res_chapters.glob("*.md"):
            if p.name == "INDEX.md":
                continue
            m[f"epyc-inference-research/docs/chapters/{p.name}"] = f"subsystems/research/{p.name}"

    res_guides = RES_REPO / "docs" / "guides"
    if res_guides.exists():
        for p in res_guides.glob("*.md"):
            m[f"epyc-inference-research/docs/guides/{p.name}"] = f"subsystems/research/{p.name}"

    return m


PUBLISHED = build_published_map()
# Reverse map: site_src-local path → source. Only files in this map are rewritten;
# hand-written pages (site_src/index.md, section index.md, about.md, stories/*)
# are left untouched.
REVERSE = {v: k for k, v in PUBLISHED.items()}


def source_path_for(site_path: Path) -> str | None:
    """Return the original epyc-root-relative source path, if this file
    came from a canonical source. Returns None for hand-written pages."""
    try:
        rel = site_path.relative_to(SITE_SRC).as_posix()
    except ValueError:
        return None
    return REVERSE.get(rel)


def split_anchor(link: str) -> tuple[str, str]:
    if "#" in link:
        path_part, anchor = link.split("#", 1)
        return path_part, "#" + anchor
    return link, ""


def normalize_to_epyc_path(link_path: str, source_rel: str) -> tuple[str, str] | None:
    """Resolve link_path to a canonical key.

    Returns (key, repo) where:
      - key is repo-relative path (no leading slash)
      - repo is one of 'root', 'orchestrator', 'research', 'llama'
    Returns None for external URLs, anchors, or unresolvable paths.
    """
    if not link_path:
        return None
    if link_path.startswith(("http://", "https://", "mailto:", "ftp://", "tel:")):
        return None
    if link_path.startswith("/workspace/"):
        return (link_path[len("/workspace/"):], "root")
    if link_path.startswith("/mnt/raid0/llm/"):
        rest = link_path[len("/mnt/raid0/llm/"):]
        if rest.startswith("epyc-orchestrator/"):
            return (rest[len("epyc-orchestrator/"):], "orchestrator")
        if rest.startswith("epyc-inference-research/"):
            return (rest[len("epyc-inference-research/"):], "research")
        if rest.startswith("llama.cpp/"):
            return (rest[len("llama.cpp/"):], "llama")
        if rest.startswith("epyc-root/"):
            return (rest[len("epyc-root/"):], "root")
        return None
    if link_path.startswith("/"):
        return None  # other absolute paths — leave alone
    # Relative to source_rel
    src_dir = os.path.dirname(source_rel)
    # Source might be "epyc-orchestrator/docs/chapters/X.md" — repo-relative
    if source_rel.startswith("epyc-orchestrator/"):
        repo = "orchestrator"
        src_dir_in_repo = os.path.dirname(source_rel[len("epyc-orchestrator/"):])
        resolved = os.path.normpath(os.path.join(src_dir_in_repo, link_path))
        if resolved.startswith(".."):
            # Walks out of orchestrator repo — fall through to root-relative
            resolved_root = os.path.normpath(os.path.join("epyc-orchestrator", src_dir_in_repo, link_path))
            return (resolved_root.lstrip("./"), "root")
        return (resolved, repo)
    if source_rel.startswith("epyc-inference-research/"):
        repo = "research"
        src_dir_in_repo = os.path.dirname(source_rel[len("epyc-inference-research/"):])
        resolved = os.path.normpath(os.path.join(src_dir_in_repo, link_path))
        if resolved.startswith(".."):
            resolved_root = os.path.normpath(os.path.join("epyc-inference-research", src_dir_in_repo, link_path))
            return (resolved_root.lstrip("./"), "root")
        return (resolved, repo)
    # Default: epyc-root file (wiki/, research/deep-dives/)
    resolved = os.path.normpath(os.path.join(src_dir, link_path))
    return (resolved, "root")


def rewrite_link(link: str, source_rel: str, current_site: Path) -> str:
    """Return the new link string. Leaves it alone if unrecognized."""
    path_part, anchor = split_anchor(link)
    if not path_part:
        return link  # pure anchor

    norm = normalize_to_epyc_path(path_part, source_rel)
    if norm is None:
        return link
    key, repo = norm

    # Map repo-relative key into the PUBLISHED key namespace
    if repo == "root":
        pub_key = key
    elif repo == "orchestrator":
        pub_key = f"epyc-orchestrator/{key}"
    elif repo == "research":
        pub_key = f"epyc-inference-research/{key}"
    else:
        pub_key = None

    if pub_key and pub_key in PUBLISHED:
        target_rel_to_site = PUBLISHED[pub_key]
        target_path = SITE_SRC / target_rel_to_site
        rel = os.path.relpath(target_path, current_site.parent)
        return rel + anchor

    # Not published — point at GitHub
    if repo == "orchestrator":
        return f"{GH_ORCH}/{key}{anchor}"
    if repo == "research":
        return f"{GH_RES}/{key}{anchor}"
    if repo == "llama":
        return f"{GH_LLAMA}/{key}{anchor}"
    return f"{GH_ROOT}/{key}{anchor}"


# Match inline markdown links [text](url), excluding image syntax ![]()
INLINE_LINK_RE = re.compile(r'(?<!\!)\[([^\]]*?)\]\(([^)\s]+)\)')


def process_file(path: Path) -> tuple[int, int]:
    """Rewrite links in one markdown file. Returns (rewrites, skipped_in_code)."""
    source = source_path_for(path)
    if source is None:
        return (0, 0)

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    in_fence = False
    rewrites = 0
    new_lines: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            new_lines.append(line)
            continue
        if in_fence:
            new_lines.append(line)
            continue

        def repl(m: re.Match) -> str:
            nonlocal rewrites
            text_part = m.group(1)
            link = m.group(2)
            new_link = rewrite_link(link, source, path)
            if new_link != link:
                rewrites += 1
            return f"[{text_part}]({new_link})"

        new_line = INLINE_LINK_RE.sub(repl, line)
        new_lines.append(new_line)

    new_text = "\n".join(new_lines)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
    return (rewrites, 0)


def main() -> int:
    if not SITE_SRC.exists():
        print(f"ERROR: site_src not found at {SITE_SRC}", file=sys.stderr)
        return 1

    total = 0
    files_touched = 0
    for path in sorted(SITE_SRC.rglob("*.md")):
        if not path.is_file():
            continue
        n, _ = process_file(path)
        if n:
            files_touched += 1
            total += n

    print(f"Link rewriter: {total} links rewritten across {files_touched} files.")
    print(f"Published-map covers {len(PUBLISHED)} source files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
