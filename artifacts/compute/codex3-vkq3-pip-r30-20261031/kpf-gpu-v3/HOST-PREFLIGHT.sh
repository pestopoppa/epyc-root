#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3
cd "$D"
printf 'uid=%s gid=%s groups=%s root=%s chroot=%s\n' "$(id -u)" "$(id -g)" "$(id -G)" "$(stat -Lc '%d:%i' /)" "$([[ -x /usr/bin/chroot ]] && echo present || echo absent)"
KPF181_PREFLIGHT=smoke /bin/bash "$D/launch.sh" --smoke preflight
KPF181_PREFLIGHT=job FILLER_CPUS=184,185 /bin/bash "$D/launch.sh" --job
set +e
KPF181_PREFLIGHT=run /bin/bash "$D/launch.sh"
rc=$?
set -e
printf 'R13_POLL_PREFLIGHT_RC=%s\n' "$rc"
[[ $rc = 124 ]]
