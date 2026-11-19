#!/bin/bash
# push_retry.sh -- push a ratification commit to origin main without losing a race.
#
#   source lib/push_retry.sh
#   ratify_push_main_retry <repo-for-lock> <worktree> <lock-agent> <serialized_push.py> <tmp-parent>
#
# Up to 5 attempts. Each attempt holds the serialized-push lock, fetches origin main, REBASES the worktree's
# commit(s) onto it when origin moved, and pushes HEAD:refs/heads/main. NEVER forces. A rebase conflict is
# aborted and refused (return 2, no retry), and so is a rebase that would change the blob of any file the
# commit touched (the receipts pin those hashes): the worktree is put back on its original commit.
# Return 0 = pushed (RATIFY_PUSHED_SHA = the commit now on origin/main; a rebase changes the sha, so callers must
# use it afterwards), 1 = lock/fetch/push still failing after 5 tries, 2 = refused.
ratify_push_main_retry() {
  local repo="$1" wt="$2" agent="$3" pusher="$4" tmp="$5" n=0 tokdir tok prc ours mb p SHA_NOW
  local -a G=(git -c safe.directory='*')
  RATIFY_PUSHED_SHA=""
  while [ "$n" -lt 5 ]; do
    n=$((n+1)); prc=0
    tokdir="$(mktemp -d "$tmp/push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
    if ! /usr/bin/python3 "$pusher" --agent "$agent" --repo "$repo" --lock-name push --acquire --token-file "$tok" >/dev/null; then
      rmdir "$tokdir" 2>/dev/null || true
      echo "push attempt $n/5: could not take the push lock for $repo" >&2; sleep $((n*2)); continue
    fi
    "${G[@]}" -C "$wt" fetch -q origin main || prc=70
    if [ "$prc" -eq 0 ] && "${G[@]}" -C "$wt" merge-base --is-ancestor HEAD origin/main; then
      prc=-1   # the commit is already on origin/main (an earlier attempt landed it): nothing to push, never fast-forward onto the tip
    elif [ "$prc" -eq 0 ] && ! "${G[@]}" -C "$wt" merge-base --is-ancestor origin/main HEAD; then
      echo "push attempt $n/5: origin/main moved; rebasing onto it (never forced)" >&2
      ours="$("${G[@]}" -C "$wt" rev-parse HEAD)"
      mb="$("${G[@]}" -C "$wt" merge-base HEAD origin/main)"
      if ! "${G[@]}" -C "$wt" rebase -q origin/main >/dev/null 2>&1; then
        "${G[@]}" -C "$wt" rebase --abort >/dev/null 2>&1 || true
        prc=71; echo "REFUSING: rebase onto origin/main conflicts in $wt; aborted, nothing pushed" >&2
      else
        for p in $("${G[@]}" -C "$wt" diff --name-only "$mb" "$ours"); do
          if [ "$("${G[@]}" -C "$wt" rev-parse "HEAD:$p" 2>/dev/null || echo gone)" != "$("${G[@]}" -C "$wt" rev-parse "$ours:$p" 2>/dev/null || echo gone)" ]; then
            "${G[@]}" -C "$wt" checkout -q --detach "$ours" >/dev/null 2>&1 || true
            prc=72; echo "REFUSING: origin/main changed $p underneath this ratification (pinned hashes would be stale); not pushed" >&2; break
          fi
        done
      fi
    fi
    SHA_NOW="$("${G[@]}" -C "$wt" rev-parse HEAD)"
    if [ "$prc" -eq 0 ]; then
      AGENT_ID="$agent" EPYC_PUSH_LOCK_HOLDER="$agent" "${G[@]}" -C "$wt" push -q origin HEAD:refs/heads/main || prc=$?
    fi
    /usr/bin/python3 "$pusher" --agent "$agent" --repo "$repo" --lock-name push --release --token-file "$tok" >/dev/null \
      || echo "WARN: push lock release failed for $repo" >&2
    rm -f "${tok:?}"; rmdir "${tokdir:?}" 2>/dev/null || true
    if [ "$prc" -eq 0 ] || [ "$prc" -eq -1 ]; then
      RATIFY_PUSHED_SHA="$SHA_NOW"
      "${G[@]}" -C "$wt" fetch -q origin main 2>/dev/null || true
      return 0
    fi
    case "$prc" in 71|72) return 2 ;; esac
    echo "push attempt $n/5 failed (rc=$prc); retrying" >&2; sleep $((n*2))
  done
  echo "REFUSING: push still failing after 5 attempts in $wt" >&2
  return 1
}
