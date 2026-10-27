#!/bin/bash
set -euo pipefail
O=/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep/recovery
[[ -f $O/STOP && ! -L $O/STOP && ! -e $O/RECOVERY-COMPLETE && ! -L $O/RECOVERY-COMPLETE ]]
[[ ! -e /proc/1049711 && ! -e /mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-df2-build-recovery-20261027.grant ]]
sha256sum --quiet -c "$O/RECOVERY-SOURCE.sha256"
