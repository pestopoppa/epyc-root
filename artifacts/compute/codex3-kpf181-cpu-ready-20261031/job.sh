#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240
G="$D/scripts/benchmark/kpf18/kpf18_gate.py"
P=/mnt/raid0/llm/tmp/kv-prefix-fork/p1r-20261020/kpf18cpu/run-20261020T163128Z/prompt_set.jsonl
B=/mnt/micron/codex3-lanes/kpf183-chat-build/bin/llama-server
C=/mnt/micron/codex3-lanes/kpf-e332-build/bin/llama-server
: "${FILLER_CPUS:?}" "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}"
case "${1:-}" in
 smoke) argv="$D/control-argv.txt"; out="$D/control-${2:?tag}"; P="$D/public-control-prompts.jsonl"; arms=A; sibs=1; predict=1; min=128;;
 full) argv="$D/full-argv.txt"; out="$D/full"; arms=A,B,C,D; sibs=3; predict=16; min=128;;
 *) exit 64;;
esac
/usr/bin/python3 -B "$D/verify_models.py" "$1"
sha256sum --strict --quiet -c "$D/ALL-BUILD-FILES.sha256"
sha256sum --strict --quiet -c /mnt/raid0/llm/tmp/codex3-kpf183-chat-impl-20261031/BUILD-DIGESTS.txt
sha256sum --strict --quiet -c /mnt/raid0/llm/tmp/codex3-kpf183-e332-build-r2-20261030/BUILD-DIGESTS.txt
cmd=(/usr/bin/python3 -B "$G" kpf181 --cpu --fork-bin "$B" --champion-bin "$C" --argv-file "$argv" --prompt-set "$P" --out "$out" --launch-prefix "taskset -c $FILLER_CPUS" --port 19627 --allow-shape-drift --fork-min "$min" --kpf181-arms "$arms" --kpf181-sibs "$sibs" --kpf181-lengths 16 --kpf-configs as-given,nodraft --n-predict "$predict" --budget-min 1440 --resume)
if [[ $1 == smoke ]]; then exec "${cmd[@]}" --public-control; fi
"${cmd[@]}"
# Champion comparison is a distinct prospective observation. Never re-expose an
# interrupted item6; retain its started marker as unknown instead.
if [[ ! -e "$D/champion.done" ]]; then
  if [[ -e "$D/champion.started" ]]; then echo "champion comparison exposure unknown; retained" >&2; exit 75; fi
  ( set -o noclobber; printf '%s\n' "$(date -u +%FT%TZ)" > "$D/champion.started" )
  sync -f "$D/champion.started"
  /usr/bin/python3 -B "$G" item6 --cpu --fork-bin "$B" --champion-bin "$C" --argv-file "$argv" --prompt-set "$P" --out "$D/champion" --launch-prefix "taskset -c $FILLER_CPUS" --port 19627 --allow-shape-drift --fork-min "$min" --item6-groups 0 --n-predict "$predict" --budget-min 1440
  : > "$D/champion.done"
  sync -f "$D/champion.done"
fi
/usr/bin/python3 -B "$D/finish.py"
