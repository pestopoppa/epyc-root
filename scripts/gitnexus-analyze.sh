#!/bin/bash
# Re-index this repo via gitnexus, preserving project conventions.
#
# gitnexus 1.6.5 supports --skip-skills. Pass it when available: this project
# keeps GitNexus skills flat at .claude/skills/<name>/, and older bare analyze
# versions either do not generate skills by default or expose only --skills.
#
# --skip-agents-md: do NOT let analyze rewrite the gitnexus section of CLAUDE.md
# / AGENTS.md at all. Protects the lean keep-markered block + avoids re-bloat
# (see feedback_gitnexus_bloat_protection). Re-run this wrapper, never bare
# `gitnexus analyze`.
#
# Before each run we (re-)apply gitnexus-patch.js: gitnexus tracks progress but
# only renders it on a TTY, so under this wrapper / agents it runs silent. The
# patch adds a non-TTY progress printer. It is idempotent + sentinel-guarded and
# self-heals after `npm update -g gitnexus` wipes the package's dist/. Best-effort:
# a patch failure never blocks indexing.
set -euo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
node "$HERE/gitnexus-patch.js" || true
args=(--skip-agents-md)
if gitnexus analyze --help 2>&1 | grep -q -- '--skip-skills'; then
  args+=(--skip-skills)
fi
exec gitnexus analyze "${args[@]}" "$@"
