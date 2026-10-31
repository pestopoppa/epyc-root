#!/bin/bash
set -euo pipefail
cd /mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3
printf '%s  %s\n' a85e01088325dd35ff199a7fb0004711a750f6446f1d9852b3e419a30647402e qualify_when_quiet.py | sha256sum --status -c
exec /usr/bin/python3 -B qualify_when_quiet.py
