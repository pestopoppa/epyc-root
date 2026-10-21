#!/bin/bash
set -uo pipefail
R=/mnt/raid0/llm/worktrees/dpf-sample-yarn-zc-epyc-inference-research-20261021
E=/mnt/raid0/llm/worktrees/dpf-sample-yarn-zc-epyc-root-20261021
cd $R/scripts/analysis && python3 -I -m pytest -q test_rus2_trace_length_probe.py -p no:cacheprovider 2>&1 | tail -4
cd /mnt/raid0/llm/epyc-inference-research && python3 -I $R/scripts/analysis/rus2_trace_length_probe.py --results-dir benchmarks/results --out $E/artifacts/rus-2-20261021/rus2_result.json > $E/artifacts/rus-2-20261021/rus2_table.txt 2>&1
head -c 600 $E/artifacts/rus-2-20261021/rus2_table.txt
python3 -I $E/artifacts/ecr-eb-1-20261021/build_slice.py $E/artifacts/ecr-eb-1-20261021 > $E/artifacts/ecr-eb-1-20261021/build_stdout.txt 2>&1
tail -5 $E/artifacts/ecr-eb-1-20261021/build_stdout.txt
