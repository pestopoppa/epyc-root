#!/bin/bash
set -euo pipefail

# Alert on critical repo state that is not protected by pushed git history.
# Intended for the future ATTESTATION artifact and for F4 backup preflight.

REPOS=(
  "epyc-root:/mnt/raid0/llm/epyc-root"
  "epyc-orchestrator:/mnt/raid0/llm/epyc-orchestrator"
  "epyc-inference-research:/mnt/raid0/llm/epyc-inference-research"
  "epyc-llama:/mnt/raid0/llm/llama.cpp"
)

EXIT_CODE=0

audit_repo() {
  local name="$1"
  local repo="$2"

  if [[ ! -d "$repo/.git" ]]; then
    printf 'WARN repo_missing_git name=%s path=%s\n' "$name" "$repo"
    EXIT_CODE=1
    return
  fi

  printf '## %s (%s)\n' "$name" "$repo"

  local dirty
  dirty="$(git -C "$repo" status --short)"
  if [[ -n "$dirty" ]]; then
    printf 'ALERT dirty_worktree name=%s\n%s\n' "$name" "$dirty"
    EXIT_CODE=1
  else
    printf 'OK clean_worktree name=%s\n' "$name"
  fi

  while IFS=$'\t' read -r branch upstream; do
    [[ -z "$branch" ]] && continue
    if [[ -z "$upstream" ]]; then
      printf 'ALERT branch_no_upstream name=%s branch=%s\n' "$name" "$branch"
      EXIT_CODE=1
      continue
    fi

    local counts behind ahead
    counts="$(git -C "$repo" rev-list --left-right --count "$upstream...$branch" 2>/dev/null || true)"
    if [[ -z "$counts" ]]; then
      printf 'WARN branch_compare_failed name=%s branch=%s upstream=%s\n' "$name" "$branch" "$upstream"
      EXIT_CODE=1
      continue
    fi
    read -r behind ahead <<<"$counts"
    if [[ "${ahead:-0}" -gt 0 ]]; then
      printf 'ALERT unpushed_commits name=%s branch=%s upstream=%s ahead=%s behind=%s\n' \
        "$name" "$branch" "$upstream" "$ahead" "${behind:-0}"
      EXIT_CODE=1
    fi
  done < <(git -C "$repo" for-each-ref --format='%(refname:short)%09%(upstream:short)' refs/heads)
}

for entry in "${REPOS[@]}"; do
  audit_repo "${entry%%:*}" "${entry#*:}"
done

exit "$EXIT_CODE"
