# Code scoreboard hygiene proposal — NOT LIVE

The operator's 2026-10-31 audit treats closing previously completed work as hygiene, not today's quota. The pinned ws58 counter credits every evidenced first flip, including hygiene. This proposal changes only the daily increment: an explicit `[closure: hygiene]` on the resolved checkbox line excludes that item from today; evidenced total, declines, unsupported items, pace, quota, and the baseline rule are unchanged. It does not infer completion date from a SHA. Marker text on another line has no effect.

`original.sh` is the exact live source snapshot with SHA-256 `f7438930a8a0384ceb96120af86524266adcae31dfffebc7977dc7a9eaa4eb0d`. `proposal.py SOURCE NEW_OUTPUT` refuses any changed source and creates a new output exclusively; it does not edit or deploy the source. Owner review and adoption at the owner's boundary are required before any hygiene checkbox is flipped. No watcher has been changed or restarted.

`test_proposal.py` executes the actual embedded Python counting loop from both the pinned source and the generated proposal against stub Git responses. It checks normal first flip, previously ticked baseline, decline, hygiene, unsupported evidence, off-line marker, and refusal of a changed source. In particular original hygiene is `(total=1, today=1)` and proposed is `(total=1, today=0)`. The original code emits ResourceWarnings from its open work-file handles in the harness; this is unchanged.

Proposed old-work closure (do not apply until the owner confirms the changed counter is live): preserve the complete original task wording and continuation, change its checkbox to `[x]`, and append on the checkbox line `✅ 2026-10-31 — 4b379a46f9f23aa3ee11d9acfbc0eafbbb301fa4; tests/unit/test_daemon_owned_state_ownership.py [closure: hygiene] [no-belief: test fixture repair, not a measurement claim]`. This is prior work, zero new quota, and retains the original date rather than asserting new work.

## Owner adoption at the watcher boundary

From a checkout containing this artifact, the watcher owner can prepare a candidate with:

```bash
set -euo pipefail
src=/mnt/raid0/llm/tmp/compute-flags/ws58-code-scoreboard.sh
candidate=/mnt/raid0/llm/tmp/compute-flags/ws58-code-scoreboard.hygiene-candidate.sh
python3 artifacts/code-scoreboard-hygiene-20261101/proposal.py "$src" "$candidate"
bash -n "$candidate"
diff -u "$src" "$candidate" || test "$?" -eq 1
```

The generator refuses a source whose SHA-256 differs from the pinned base and refuses an existing candidate. Review the sole diff. At the owner's safe boundary, recheck the source against the pin and install the reviewed candidate under the owner's own process-control procedure; verify the installed bytes and then restart the owned watcher at that boundary. Copying a file alone is not deployment: the running shell may already have parsed its embedded Python. Verify the replacement watcher is running the installed version and send an owner receipt before any hygiene closure. The proposing session has not installed or restarted it.

The retained test log was captured with mutex 26 and admitted physical CPUs 74–75, with the R4 admission guard and a 900-second supervisor; this was not a timing or quiet-host claim.

Owner installation commands, executed only after the owner has stopped the owned watcher at its safe boundary and confirmed it has exited:

```bash
printf '%s  %s\n' f7438930a8a0384ceb96120af86524266adcae31dfffebc7977dc7a9eaa4eb0d "$src" | sha256sum -c -
check="${candidate}.verify"
python3 artifacts/code-scoreboard-hygiene-20261101/proposal.py "$src" "$check"
cmp "$candidate" "$check"
rm "$check"
chmod --reference="$src" "$candidate"
mv "$candidate" "$src"
sha256sum "$src"
```

The owner then starts the watcher through its existing owner-managed mechanism, verifies the new process and installed digest, and returns the receipt. Never use a process-name wildcard to stop it.
