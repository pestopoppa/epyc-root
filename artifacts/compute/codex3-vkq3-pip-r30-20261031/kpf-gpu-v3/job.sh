#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3
G="$D/scripts/benchmark/kpf18/kpf18_gate.py"
P=/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/prompt_set.jsonl
B=/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/llama-server
C=/mnt/micron/codex3-lanes/kpf181-e332-hip-build/bin/llama-server
: "${FILLER_CPUS:?}" "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_ID:?}"
case "${1:-}" in
 smoke) argv="$D/control-argv.txt"; out="$D/control-${2:?tag}"; P="$D/public-control-prompts.jsonl"; arms=A; sibs=1; predict=1; ceiling=48;;
 full) argv="$D/full-argv.txt"; out="$D/full"; arms=A,B,C,D; sibs=3; predict=256; ceiling=60;;
 *) exit 64;;
esac
/usr/bin/python3 -B "$D/verify_models.py" "$1"
sha256sum --strict --quiet -c "$D/GPU-BINARIES.sha256"
sha256sum --strict --quiet -c "$D/E332-GPU-DIGESTS.sha256"
export HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0
cmd=(/usr/bin/python3 -B "$G" kpf181 --fork-bin "$B" --argv-file "$argv" --prompt-set "$P" --out "$out" --launch-prefix "taskset -c $FILLER_CPUS" --port 19639 --allow-shape-drift --fork-min 1024 --kpf181-arms "$arms" --kpf181-sibs "$sibs" --kpf181-lengths 16 --kpf-configs as-given,nodraft --n-predict "$predict" --budget-min 240 --resume --gpu-window-id "$FILLER_ID" --no-device-claim 'exclusive gpu-quiet held by enclosing launcher' --vram-ceiling-gib "$ceiling")
public=()
if [[ $1 == smoke ]]; then
 # Control-only threshold exercises a real fork on the public 512-token source.
 for i in "${!cmd[@]}"; do if [[ ${cmd[$i]} == --fork-min ]]; then cmd[$((i+1))]=128; fi; done
 public=(--public-control)
fi
"${cmd[@]}" "${public[@]}"
# Do not redraw an interrupted comparator.  Its marker survives restarts.
cmp="$out/comparator"; mkdir -p "$cmp"
if [[ ! -e "$cmp/DONE" ]]; then
 if [[ -e "$cmp/STARTED" ]]; then echo 'comparator exposure unknown; preserved without replay' >&2; exit 75; fi
 if [[ -e $FILLER_STOPFILE || $(date +%s) -ge $FILLER_DEADLINE ]]; then exit 75; fi
 ( set -o noclobber; printf '%s\n' "$(date -u +%FT%TZ)" > "$cmp/STARTED" )
 sync -f "$cmp/STARTED"
 groups=0,2,4,7; cmp_predict=256
 if [[ $1 == smoke ]]; then groups=0; cmp_predict=8; fi
 /usr/bin/python3 -B "$G" item6 --fork-bin "$B" --champion-bin "$C" --argv-file "$argv" --prompt-set "$P" --out "$cmp" --launch-prefix "taskset -c $FILLER_CPUS" --port 19639 --allow-shape-drift --fork-min 1024 --item6-groups "$groups" --n-predict "$cmp_predict" --budget-min 240 --gpu-window-id "$FILLER_ID" --no-device-claim 'exclusive gpu-quiet held by enclosing launcher' --vram-ceiling-gib "$ceiling" "${public[@]}"
 : > "$cmp/DONE"; sync -f "$cmp/DONE"
fi
if [[ $1 == full ]]; then /usr/bin/python3 -B "$D/finish.py"; else /usr/bin/python3 -B "$D/finish.py" --control "$out"; fi
