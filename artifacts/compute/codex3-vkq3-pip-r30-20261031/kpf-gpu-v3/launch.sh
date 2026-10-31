#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3
SOURCE_SHA=96ca5e50911a1dc0838ecef538986904e0ff077d741f40e0b5100f7083855dee
cd "$D"
printf '%s  %s\n' "$SOURCE_SHA" "$D/SOURCES.sha256" | sha256sum --status -c
timeout 180 sha256sum --strict --quiet -c "$D/SOURCES.sha256"
case "${1:-}" in
 --smoke)
  tag=${2:?}; [[ $tag =~ ^[a-z0-9-]+$ ]]
  if [[ -x /usr/bin/chroot ]]; then
   exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --host-smoke "$tag"
  else
   exec /bin/bash "$D/launch.sh" --host-smoke "$tag"
  fi;;
 --host-smoke)
  (cd /mnt/micron/codex3-lanes/orchestrator; sha256sum --strict --quiet -c "$D/LOCK-MODULES.sha256")
  tag=${2:?}; [[ $tag =~ ^[a-z0-9-]+$ ]]
  if [[ ${KPF181_PREFLIGHT:-} == smoke ]]; then "$D/region-lock.sh" run --help >/dev/null; printf "HOST_SMOKE_ENTRY_OK uid=%s cwd=%s tag=%s\n" "$(id -u)" "$PWD" "$tag"; exit 0; fi
  exec "$D/region-lock.sh" run --gpu-quiet exclusive --timeout-s 300 -- /usr/bin/taskset -c 184-185 /usr/bin/env -i PATH=/opt/rocm/bin:/usr/bin:/bin HOME=/home/node LANG=C LC_ALL=C PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 /bin/bash "$D/smoke_entry.sh" "$tag";;
 --job)
  if [[ ${KPF181_PREFLIGHT:-} == job ]]; then printf "HOST_JOB_ENTRY_OK uid=%s cpus=%s cwd=%s\n" "$(id -u)" "${FILLER_CPUS:?}" "$PWD"; exit 0; fi
  exec /bin/bash "$D/job.sh" full;;
 --host-run)
  (cd /mnt/micron/codex3-lanes/orchestrator; sha256sum --strict --quiet -c "$D/LOCK-MODULES.sha256")
  flags=/mnt/raid0/llm/tmp/compute-flags; grants=$flags/grants; fillers=$flags/FILLERS.md; state=$D/state; runner=()
  if [[ ${KPF181_PREFLIGHT:-} == run ]]; then flags=$D/host-preflight; grants=$flags/grants; fillers=$flags/FILLERS.md; state=$flags/state; mkdir -p "$grants" "$state"; : > "$fillers"; runner=(timeout 2); fi
  exec "${runner[@]}" /usr/bin/env -i PATH=/opt/rocm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/home/node LANG=C LC_ALL=C PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 FILLER_RL="$D/region-lock.sh" FILLER_FLAGS_DIR="$flags" FILLER_GRANTS_DIR="$grants" FILLERS_MD="$fillers" FILLER_STATE_DIR="$state" FILLER_GPU_LOCK=/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock FILLER_POLL=45 /bin/bash /mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh --id codex3-kpf181-27b-gpu-r3-20261031 --class gpu --cmd "exec taskset -c \"\$FILLER_CPUS\" /bin/bash $D/launch.sh --job" --min-window 1800 --stop "$D/STOP" --port 19639 --workdir "$D" --gpu-quiet exclusive --no-fold-siblings --gpu-threads 184-191 --complete-cmd "test -s $D/full/RESULT.json";;
 '')
  if [[ -x /usr/bin/chroot ]]; then
   exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --host-run
  else
   exec /bin/bash "$D/launch.sh" --host-run
  fi;;
 *) exit 64;;
esac
