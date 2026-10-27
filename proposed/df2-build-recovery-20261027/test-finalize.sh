#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery
source "$R/finalize.sh"
D=$(mktemp -d "$TMPDIR/df2-recovery-test.XXXXXX")
recovery_fresh "$D/work" "$D/done"
printf 'stale-work\n' > "$D/work"
if recovery_fresh "$D/work" "$D/done"; then exit 1; fi
if finalize_recovery 7 0 "$D/work" "$D/build" "$D/done"; then exit 1; fi
[[ ! -e $D/build && ! -e $D/done ]]
if finalize_recovery 0 70 "$D/work" "$D/build" "$D/done"; then exit 1; fi
[[ ! -e $D/build && ! -e $D/done ]]
if finalize_recovery 0 0 "$D/work" "$D/missing/build" "$D/done"; then exit 1; fi
[[ ! -e $D/build && ! -e $D/done ]]
finalize_recovery 0 0 "$D/work" "$D/build" "$D/done"
cmp "$D/work" "$D/build"; cmp "$D/work" "$D/done"
if finalize_recovery 0 0 "$D/work" "$D/build" "$D/done"; then exit 1; fi
printf 'RECOVERY_FINALIZER_NEGATIVE_AND_EXCLUSIVE_PASS\n'
