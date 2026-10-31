#!/bin/bash
set -euo pipefail
cd /mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3
printf '%s  %s\n' 0149cf92ce8b1cd41de3c355eb5a6ea8189db575195ecf89d64c7b5e8e8dcfd8 publish_when_qualified.py | sha256sum --status -c
exec /usr/bin/python3 -B publish_when_qualified.py
