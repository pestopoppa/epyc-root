#!/bin/bash
set -euo pipefail
# Hook: PreToolUse -> Write|Edit
# Validate simple local markdown path references in agent/docs governance files.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
PROJECT_DIR=${CLAUDE_PROJECT_DIR:-$(pwd)}

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

case "$FILE_PATH" in
  agents/* | */agents/* | CLAUDE_GUIDE.md | */CLAUDE_GUIDE.md | README.md | */README.md | docs/guides/* | */docs/guides/* | docs/reference/agent-config/* | */docs/reference/agent-config/*) ;;
  *)
    exit 0
    ;;
esac

if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Validate the POST-edit content, not the pre-edit disk state (audit D13,
# 2026-07-30): reconstruct what the file will contain after this Write/Edit,
# then scan that. Pre-state scanning both missed newly-introduced bad refs and
# wedged the very edit that fixes an existing bad ref.
POST_TEXT=$(printf '%s' "$INPUT" | python3 -c '
import json, sys, pathlib
inp = json.load(sys.stdin)
ti = inp.get("tool_input", {})
path = pathlib.Path(ti.get("file_path", ""))
if "content" in ti:                      # Write
    sys.stdout.write(ti["content"])
elif "old_string" in ti:                 # Edit
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    old, new = ti["old_string"], ti.get("new_string", "")
    if ti.get("replace_all"):
        text = text.replace(old, new)
    else:
        text = text.replace(old, new, 1)
    sys.stdout.write(text)
else:
    sys.stdout.write(path.read_text(encoding="utf-8") if path.is_file() else "")
')
mapfile -t refs < <(printf '%s' "$POST_TEXT" | { rg -o '`[^`]+\.md`' || true; } | tr -d '`' | sed 's/:.*$//' | sort -u)

file_dir=$(dirname "$FILE_PATH")
missing=()
for ref in "${refs[@]}"; do
  [[ "$ref" =~ ^https?:// ]] && continue
  [[ "$ref" == *'*'* ]] && continue
  # Skip template/placeholder paths — illustrative examples, not real links:
  # angle-bracket tokens (<handoff>, <category-key>) or date templates (YYYY-MM-DD).
  [[ "$ref" == *'<'* ]] && continue
  [[ "$ref" == *'YYYY'* ]] && continue
  if [[ "$ref" == /* ]]; then
    [[ -f "$ref" ]] || missing+=("$ref")
    continue
  fi
  # Try resolution in priority order: file's own directory, then project root.
  if [[ -f "$file_dir/$ref" ]] || [[ -f "$PROJECT_DIR/$ref" ]]; then
    continue
  fi
  # Then the standard governance locations, so documented bare references
  # resolve without a broad repository-wide basename search.
  resolved=0
  for d in handoffs/active handoffs/completed handoffs/archived coordination/session-bus; do
    if [[ -f "$PROJECT_DIR/$d/$ref" ]]; then resolved=1; break; fi
  done
  (( resolved )) && continue
  missing+=("$ref")
done

if ((${#missing[@]} > 0)); then
  echo "BLOCKED: unresolved local markdown references in $FILE_PATH:" >&2
  for m in "${missing[@]}"; do
    echo "  - $m" >&2
  done
  exit 2
fi

exit 0
