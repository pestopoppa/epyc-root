#!/bin/bash
set -euo pipefail
cd /mnt/raid0/llm/tmp/vidya-belief-substrate/p5-sphinx-scorer-r1-20261118
printf '%s  %s\n' 'c8ab38f868eae9a20b7518b38a7ae78587a3386dc0bd9282adbbeca5e876d5ed' SOURCE.sha256 | sha256sum --check --status
sha256sum --check --status SOURCE.sha256
test -x /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python
test "$(docker image inspect --format '{{.Id}}' 'sha256:a5f693152c2178356658d94655f2265ae787ba662337237e48cf2945c679e82d')" = 'sha256:a5f693152c2178356658d94655f2265ae787ba662337237e48cf2945c679e82d'
