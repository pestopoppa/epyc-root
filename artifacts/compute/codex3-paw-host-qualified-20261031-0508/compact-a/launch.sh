#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/paw-repair/a-host2
export EPYC_ROOT=/mnt/raid0/llm/tmp/codex3-paw-standard-r2-20261030
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
cd "$D"
printf '%s  %s\n' '1c3d2e5e6fa4a1ac24ba1f22b8f10cb52f0135a274f770a78bedc477f1adce70' "$D/SOURCES.sha256" | sha256sum -c --quiet
printf '%s  %s\n' '4923f295ff54682ef971c67e34962d1093ccffff27a7be9df6168d7eef89bbed' "$D/EARLY.sha256" | sha256sum -c --quiet
sha256sum --strict --quiet -c "$D/EARLY.sha256"
case ${1:-} in
 --job) exit 64;;
 --smoke-normal|--smoke-stop)
  mode="--inside-${1#--}"
  exec env DOCKER_HOST=unix:///var/run/docker.sock docker run --rm --pid=host --network=host --user 1000:1000 --cpuset-cpus "${FILLER_CPUS:?}" --memory 8g -e FILLER_CPUS -v /mnt/raid0:/mnt/raid0 -v /mnt/micron:/mnt/micron -v /home/node:/home/node sha256:ea165e543ea5fa04ab7364570e2b3bdb326402baff066edd563eefd77d8b94f2 /bin/bash "$D/launch.sh" "$mode";;
 --inside-smoke-normal|--inside-smoke-stop)
  export FILLER_CPUS=${FILLER_CPUS:?} FILLER_PORTS=19963 PAW_SMOKE_DEADLINE=$(( $(date +%s) + 275 ))
  if [[ $1 == --inside-smoke-normal ]]; then export PAW_CONTROL_NORMAL=1 PAW_SMOKE_NAME=normal3; else export PAW_CONTROL_NORMAL=0 PAW_SMOKE_NAME=stop; fi
  exec taskset -c "$FILLER_CPUS" /usr/bin/python3 -I "$D/smoke-supervisor.py" 285 -- "$D/.venv/bin/python" "$D/job.py" smoke --epyc-root "$EPYC_ROOT";;
 --engine) export FILLER_RL="$D/region-lock"; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-paw-compact-a-hostfix2-20261031 --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 2400 --port 19963 --stop "$D/STOP" --workdir "$D" --complete-cmd 'test -f /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/paw-repair/a-host2/DONE' --cmd 'env -i PATH=/usr/bin:/bin LANG=C.UTF-8 RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 EPYC_ROOT=/mnt/raid0/llm/tmp/codex3-paw-standard-r2-20261030 FILLER_ID="$FILLER_ID" FILLER_CPUS="$FILLER_CPUS" FILLER_NEEDGPU="$FILLER_NEEDGPU" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_END="$FILLER_END" FILLER_DEADLINE="$FILLER_DEADLINE" FILLER_PORTS="$FILLER_PORTS" WS58_REGIONS="$WS58_REGIONS" taskset -c "$FILLER_CPUS" /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/paw-repair/a-host2/.venv/bin/python /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/paw-repair/a-host2/job.py real --epyc-root /mnt/raid0/llm/tmp/codex3-paw-standard-r2-20261030';;
 '') exec > >(tee -a "$D/ws58-launcher.out") 2>&1; exec env DOCKER_HOST=unix:///var/run/docker.sock docker run --rm --pid=host --network=host --user 1000:1000 -e WS58_REGIONS -e FILLER_CPUS -v /mnt/raid0:/mnt/raid0 -v /mnt/micron:/mnt/micron -v /home/node:/home/node sha256:ea165e543ea5fa04ab7364570e2b3bdb326402baff066edd563eefd77d8b94f2 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
