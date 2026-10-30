#!/usr/bin/env bash
# Prepared command only; do not run until the R18 full result is final and both launcher and tee have drained.
set -euo pipefail
CAP=/mnt/raid0/llm/tmp/refactor-r18-anchor-integrity-20261030
D=/mnt/raid0/llm/tmp/refactor-oab21-metrics-20261030/r18a-independent-packet
CMP=/mnt/raid0/llm/tmp/refactor-01a16fc3/r18a-recipe-verifiability-20261030/compare_symbols.py
CMP_SHA=08a5e9e15f8ac07d573d8e0c8c38ec4aef6d78820032ec4e2eb0325a3447bf61
ANCHOR_GPU="$CAP/private-view/gpu"
ANCHOR_CPU="$CAP/private-view/cpu"
CAND_GPU="$D/scratch/full/buildgpu"
CAND_CPU="$D/scratch/full/buildcpu"
[[ -f "$D/scratch/full/full-result.json" && -f "$D/tee-drain-full.json" ]] || { echo 'R18 full result/tee-drain receipt missing; do not compare partial output' >&2; exit 75; }
python3 - "$D/scratch/full/full-result.json" "$D/tee-drain-full.json" <<'PYRESULT'
import json,sys
r=json.load(open(sys.argv[1])); t=json.load(open(sys.argv[2]))
if r.get('mode')!='full' or r.get('partial') is not False or r.get('reason') not in ('command_failed','independent_cpu_hip_symbol_identity_pass'):
 raise SystemExit('full candidate is partial or did not reach its comparison step')
if not any(any('compare_symbols.py' in str(x) for x in cmd) for cmd in r.get('commands',[])):
 raise SystemExit('full result does not show the unchanged comparator step')
if not t.get('drained'):
 raise SystemExit('outer launcher tee was not verified drained')
PYRESULT
[[ -f "$CAND_GPU/bin/libggml-hip.so" && -f "$CAND_CPU/bin/libggml-cpu.so" ]] || { echo 'candidate outputs missing' >&2; exit 66; }
[[ -L "$ANCHOR_GPU/bin/libggml-hip.so" && "$(sha256sum "$ANCHOR_GPU/bin/libggml-hip.so" | cut -d' ' -f1)" == f26a166b8ea3089d19a395ae00afa22e917df8eba71ca6ef4be5235d65ea8079 ]] || { echo 'private GPU anchor is not the verified ratified HIP ELF' >&2; exit 65; }
[[ "$(sha256sum "$CMP" | cut -d' ' -f1)" == "$CMP_SHA" ]] || { echo 'comparison tool differs from audited unchanged comparator' >&2; exit 65; }
python3 "$CMP" --anchor-build "$ANCHOR_GPU" --anchor-cpu-build "$ANCHOR_CPU" --candidate-build "$CAND_GPU" --candidate-cpu-build "$CAND_CPU" | tee "$CAP/evidence/R18-PRIVATE-VIEW-SYMBOL-COMPARISON.json"
