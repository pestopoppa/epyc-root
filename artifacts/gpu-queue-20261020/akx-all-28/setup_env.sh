#!/bin/bash
set -euo pipefail
export UV_CACHE_DIR=/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-28/uvcache
export UV_PYTHON_INSTALL_DIR=/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-28/pythons
export TMPDIR=/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-28/tmp
mkdir -p "$TMPDIR"
cd /mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-28
echo "== python"; uv python install 3.12
echo "== venv"; uv venv --python 3.12 venv
echo "== torch (rocm6.2)"; uv pip install --python venv/bin/python --index-url https://download.pytorch.org/whl/rocm6.2 torch==2.5.1+rocm6.2
echo "== tilelang"; uv pip install --python venv/bin/python tilelang
echo "== freeze"; uv pip freeze --python venv/bin/python > freeze.txt
echo DONE
