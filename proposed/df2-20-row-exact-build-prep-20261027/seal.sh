#!/bin/bash
set -euo pipefail
B=/mnt/raid0/llm/tmp/codex-ni-20261027-df2-row-exact-prep
T=/mnt/raid0/llm/worktrees/df2-row-exact-c5
cd "$T"
git ls-files -z | sort -z | xargs -0 -r sha256sum > "$B/tracked-relative.sha256"
sed "s@  @  $T/@" "$B/tracked-relative.sha256" > "$B/TRACKED-SOURCE.sha256"
cd "$B"
find /mnt/raid0/llm/kernels/builds/{cpu,gpu}-20261023-141e4bcf5-lbh/tools/ui/dist -type f -print0 | sort -z | xargs -0 -r sha256sum > UI-SOURCE.sha256
sha256sum /usr/bin/cmake /usr/bin/gcc-15 /usr/bin/g++-15 /opt/rocm/bin/hipcc > TOOLCHAIN.sha256
sha256sum "$B"/candidate.patch "$B"/q8_1_bytes_fixture.cpp "$B"/width_probe.cpp "$B"/run_width_probe.py "$B"/predicted_fail_list.jsonl "$B"/final-validation.py "$B"/resource-watch.py "$B"/owned-bootstrap.sh "$B"/build-poller.sh "$B"/build-body.sh "$B"/build-owner.sh "$B"/t1.sh "$B"/pf-region-claimed.sh "$B"/deps/{filler_run12.sh,dryrun_check.py,dryrun_disk_policy.json} "$B"/TRACKED-SOURCE.sha256 "$B"/UI-SOURCE.sha256 "$B"/TOOLCHAIN.sha256 /mnt/raid0/llm/kernels/builds/{cpu,gpu}-20261024-c72ec82f5-c5/CMakeCache.txt /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/epyc-orchestrator/scripts/region-lock /mnt/raid0/llm/epyc-orchestrator/src/runtime/{region_lock_cli,cpu_region_lock,lock_queue,gpu_quiet_lock,instance_topology}.py /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python3 > SOURCE.SHA256SUMS
sha256sum --quiet -c SOURCE.SHA256SUMS
sha256sum --quiet -c TRACKED-SOURCE.sha256
sha256sum --quiet -c UI-SOURCE.sha256
