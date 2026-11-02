#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/akagg-ch26b-r2-20261101
cd "$D"
# Existing predecessor is admissible only while its exact failed row and launcher remain unchanged.
/usr/bin/python3 -I "$D/guard_predecessor.py"
sha256sum -c INPUT.sha256
printf '%s  %s\n' '6bb4816da6668ae6d1e8cbbd7177f84aabfa2356bd5db352a8e29533ab782853' '/mnt/raid0/llm/kernels/builds/cpu-20261021-49550eda5-c-nemotron/SHA256SUMS' | sha256sum -c -
printf '%s  %s\n' 'd57196173a39faf261b5f95c0fe95bd3d95cf9dcffa5fc0b4be5a11325f3c29a' '/mnt/raid0/llm/kernels/builds/cpu-20261021-49550eda5-c-nemotron/PROVENANCE.md' | sha256sum -c -
(cd /mnt/raid0/llm/kernels/builds/cpu-20261021-49550eda5-c-nemotron/bin && sha256sum -c ../SHA256SUMS)
exec python3 -I "$D/run.py"
