#!/bin/bash
set -euo pipefail
O=/mnt/raid0/llm/tmp/codex-ni-20261027-meta-build-recovery
[[ -f $O/STOP && ! -L $O/STOP && ! -e $O/RECOVERY-ACCEPTED && ! -L $O/RECOVERY-ACCEPTED ]]
[[ ! -e /proc/1026074 && ! -e /mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-meta-recovery-20261027.grant ]]
sha256sum --quiet -c "$O/RECOVERY.SHA256SUMS"
