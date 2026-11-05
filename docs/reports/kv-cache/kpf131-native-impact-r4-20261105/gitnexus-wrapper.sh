#!/bin/bash
set -euo pipefail
exec /usr/local/bin/node /mnt/raid0/llm/tmp/kvu/kpf131-impact-r4-20261105/tool/dist/cli/index.js "$@"
