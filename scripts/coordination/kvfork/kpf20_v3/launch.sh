#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf20-v3
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
precond='printf "%s  %s\n" a569bd805797e8e4a85e5b0fd192d35b5fcbdb981b3c41ad4847e8944757e2e0 /mnt/raid0/llm/tmp/kvfork/kpf20-v3/job.py 316830c77eefeda21a4ebf70aab3fe05977e53e58696fd9f582020614d0921c4 /mnt/raid0/llm/tmp/kvfork/kpf20-v3/filler_run15.sh | sha256sum --check --status && python3 /mnt/raid0/llm/tmp/kvfork/kpf20-v3/job.py --check'
exec bash "$D/filler_run15.sh" --id kvfork20-p2-impact-20261102 --class cpu --role build --claim-cpus 0-95 --gpu-quiet none --min-window 300 --stop "$D/STOP" --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" --cmd "python3 '$D/job.py'" --precond-cmd "$precond"
