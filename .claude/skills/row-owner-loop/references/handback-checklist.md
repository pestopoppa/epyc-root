# Hand-back checklist (SKILL §7)

Verify each claim yourself; an unverified claim is false.

| Claim | Proof command |
|---|---|
| "pushed `<sha>` on `<branch>`" | `git -C /workspace fetch -q origin && git -C /workspace branch -r --contains <sha>` shows `origin/main`; `git cherry origin/main <branch>` prints nothing |
| "published `<id>`" | `ls /mnt/raid0/llm/tmp/compute-flags/ready/<id>.json` or `ls -l …/dryrun/<id>/*SMOKE-QUEUED.json` (age) |
| "smoke PASSed" | `tac …/dryrun/<id>/launcher.out \| grep -m1 '^==== dry run'` says PASS **and** `…/dryrun/<id>/PASS.json` is newer than the last publish |
| "filed" | `ls …/filing-done/<id>.FILED` |
| "built `<lib>` with fix X" | `strings <lib> \| grep <fix symbol/knob>`; bind to commit, never mtime |
| "ticked" | `git show origin/main:<file> \| grep -n '<ID>'` shows `[x]` with a belief tag |

Then: `TaskStop` the agent's leftover background tasks, file/tick, dispatch the next phase in the
same turn, and update the program table.
