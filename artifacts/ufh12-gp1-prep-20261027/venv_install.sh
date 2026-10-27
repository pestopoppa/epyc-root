#!/bin/bash
set -euo pipefail
cd /mnt/raid0/llm/tmp/repl-emb-25-26-20261020
uv pip install --python venv/bin/python --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cpu \
  "torch==2.14.1+cpu" "sentence-transformers==6.1.0" "transformers==5.20.1" "model2vec==0.10.0" "numpy" "psutil" "pytest" 
venv/bin/python -m pip --version >/dev/null 2>&1 || true
uv pip freeze --python venv/bin/python > venv_freeze.txt
