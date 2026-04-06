#!/bin/bash
set -euo pipefail
# Hook: PreToolUse → Write|Edit
# Blocks writes to the root SSD. Allows /mnt/raid0/, .claude/ config,
# and devcontainer /workspace (if backed by a non-root filesystem).

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Allow /mnt/raid0/* (project data)
if [[ "$FILE_PATH" == /mnt/raid0/* ]]; then
  exit 0
fi

# Allow .claude/ config paths (e.g. ~/.claude/, project .claude/)
if [[ "$FILE_PATH" == */.claude/* ]]; then
  exit 0
fi

# Allow devcontainer /workspace if it's on a non-root filesystem.
# Compares mount device of /workspace against / to detect RAID/external mounts.
if [[ "$FILE_PATH" == /workspace/* || "$FILE_PATH" == /workspace ]]; then
  root_dev=$(df --output=source / 2>/dev/null | tail -1)
  workspace_dev=$(df --output=source /workspace 2>/dev/null | tail -1)
  if [[ -n "$workspace_dev" && "$workspace_dev" != "$root_dev" ]]; then
    exit 0
  fi
fi

echo "BLOCKED: Write to '$FILE_PATH' denied. All files must be on /mnt/raid0/ (or a devcontainer /workspace on a non-root device). Root FS is a 120GB SSD." >&2
exit 2
