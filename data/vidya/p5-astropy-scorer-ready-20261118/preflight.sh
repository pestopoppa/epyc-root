#!/bin/bash
set -euo pipefail
cd /mnt/raid0/llm/tmp/vidya-belief-substrate/p5-astropy-native-r1-20261118
printf '%s  %s\n' '3340c4f84066bdf17b5b0e45f8846ad08016d98edeab15f5ab0cf873085f5357' SOURCE.sha256 | sha256sum --check --status
sha256sum --check --status SOURCE.sha256
test -x /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python
test "$(docker image inspect --format '{{.Id}}' 'sha256:3dcf849904aa1395cff121684a80332a134cd4b34d806514f97c082bdb83b337')" = 'sha256:3dcf849904aa1395cff121684a80332a134cd4b34d806514f97c082bdb83b337'
