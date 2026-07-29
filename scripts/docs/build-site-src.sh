#!/bin/bash
# Populate site_src/ from canonical sources before `mkdocs build`.
#
# Sources:
#   wiki/                            -> site_src/topics/
#   research/deep-dives/             -> site_src/deep-dives/
#   <orchestrator>/docs/chapters/    -> site_src/subsystems/orchestrator/
#   <research>/docs/chapters/        -> site_src/subsystems/research/
#   <research>/docs/guides/          -> site_src/subsystems/research/ (alongside chapters)
#
# Sibling repo paths can be overridden via env:
#   ORCH_REPO=/path/to/epyc-orchestrator
#   RES_REPO=/path/to/epyc-inference-research
#
# Defaults:
#   - GitHub Actions: ${GITHUB_WORKSPACE}/repos/<name> (set by checkout step)
#   - Local:          /workspace/repos/<name>          (the canonical symlinks)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SITE="$ROOT/site_src"

ORCH_REPO="${ORCH_REPO:-$ROOT/repos/epyc-orchestrator}"
RES_REPO="${RES_REPO:-$ROOT/repos/epyc-inference-research}"

if [[ ! -d "$ORCH_REPO/docs/chapters" ]]; then
    echo "ERROR: orchestrator chapters not found at $ORCH_REPO/docs/chapters" >&2
    echo "       Set ORCH_REPO env or run after checking out the sibling repo." >&2
    exit 1
fi

if [[ ! -d "$RES_REPO/docs/chapters" ]]; then
    echo "ERROR: research chapters not found at $RES_REPO/docs/chapters" >&2
    echo "       Set RES_REPO env or run after checking out the sibling repo." >&2
    exit 1
fi

echo "Populating $SITE from canonical sources..."

# Topics (wiki) — copy everything EXCEPT INDEX.md (we provide our own index.md)
mkdir -p "$SITE/topics"
# Wipe only the article files we manage; preserve the hand-written index.md
find "$SITE/topics" -maxdepth 1 -name '*.md' ! -name 'index.md' -delete
for f in "$ROOT/wiki/"*.md; do
    base="$(basename "$f")"
    [[ "$base" == "INDEX.md" ]] && continue
    cp "$f" "$SITE/topics/$base"
done

# Deep-dives — copy everything except INDEX.md; preserve hand-written index.md
mkdir -p "$SITE/deep-dives"
find "$SITE/deep-dives" -maxdepth 1 -name '*.md' ! -name 'index.md' -delete
if [[ -d "$ROOT/research/deep-dives" ]]; then
    for f in "$ROOT/research/deep-dives/"*.md; do
        base="$(basename "$f")"
        [[ "$base" == "INDEX.md" ]] && continue
        cp "$f" "$SITE/deep-dives/$base"
    done
fi

# Sibling chapters
rm -rf "$SITE/subsystems/orchestrator" "$SITE/subsystems/research"
mkdir -p "$SITE/subsystems/orchestrator" "$SITE/subsystems/research"

cp "$ORCH_REPO/docs/chapters/"*.md "$SITE/subsystems/orchestrator/"
# Rename orchestrator INDEX.md → index.md (don't shadow MkDocs section index)
if [[ -f "$SITE/subsystems/orchestrator/INDEX.md" ]]; then
    rm "$SITE/subsystems/orchestrator/INDEX.md"
fi

cp "$RES_REPO/docs/chapters/"*.md "$SITE/subsystems/research/"
if [[ -d "$RES_REPO/docs/guides" ]]; then
    cp "$RES_REPO/docs/guides/"*.md "$SITE/subsystems/research/" 2>/dev/null || true
fi
if [[ -f "$SITE/subsystems/research/INDEX.md" ]]; then
    rm "$SITE/subsystems/research/INDEX.md"
fi

echo "Done."
echo "  topics:                    $(ls "$SITE/topics" | wc -l) files"
echo "  deep-dives:                $(ls "$SITE/deep-dives" 2>/dev/null | wc -l) files"
echo "  subsystems/orchestrator:   $(ls "$SITE/subsystems/orchestrator" | wc -l) files"
echo "  subsystems/research:       $(ls "$SITE/subsystems/research" | wc -l) files"
