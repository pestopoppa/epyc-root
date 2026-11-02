#!/bin/bash
set -euo pipefail
umask 077
D=/mnt/raid0/llm/tmp/handoff-kvu-16i-c5-20261101
ID=handoff-kvu-16i-c5-replay-20261101
SOURCE_SHA=11aca2bf4db205cbd449e30a1b9136e4e2755a1766e025a4ada24e5987362432
BIN=/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildhip/bin
cd "$D"
case ${1:-} in
 --job)
  case ${FILLER_DRYRUN:-missing} in 0|1) ;; *) echo 'invalid/missing FILLER_DRYRUN' >&2; exit 64;; esac
  actual=$(sha256sum SOURCE-SHA256SUMS); actual=${actual%% *}
  [ "$actual" = "$SOURCE_SHA" ] || { echo 'source catalog mismatch' >&2; exit 65; }
  sha256sum -c --quiet SOURCE-SHA256SUMS
  sha256sum -c --quiet RUNTIME-INPUTS.sha256
  sha256sum -c --quiet /mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/jobs/hip-q0-v2/ELF.sha256
  export LD_LIBRARY_PATH="$BIN:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib"
  proof="$D/pin-proof-${FILLER_DRYRUN}-$$.txt"
  tmp="$proof.tmp"
  { printf 'source_catalog_sha256=%s\n' "$SOURCE_SHA"; sha256sum RUNTIME-INPUTS.sha256; /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$BIN/llama-server" "$BIN"; } > "$tmp"
  mv -- "$tmp" "$proof"
  /usr/bin/python3 -c 'import os,sys; p=sys.argv[1]; f=os.open(p,os.O_RDONLY); os.fsync(f); os.close(f); d=os.open(os.path.dirname(p),os.O_RDONLY|os.O_DIRECTORY); os.fsync(d); os.close(d)' "$proof"
  export KVU16I_PIN_PROOF="$proof"
  exec /usr/bin/python3 -B "$D/producer.py";;
 --engine)
  export FILLER_RL="$D/region-lock"
  case ${FILLER_DRYRUN:-missing} in
   1) complete="$D/QUALIFICATION.json"; cmode=qualification ;;
   0) complete="$D/TERMINAL.json"; cmode=full ;;
   *) echo 'invalid/missing FILLER_DRYRUN' >&2; exit 64;;
  esac
  exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id handoff-kvu-16i-c5-replay-20261101 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-191 --gpu-threads 184-191 --min-window 4800 --stop "$D/STOP" --port 18196 --workdir "$D" --complete-cmd "/usr/bin/python3 -B $D/completion.py $cmode $complete" --cmd "env -i PATH=/usr/bin:/bin LANG=C.UTF-8 FILLER_DRYRUN=$FILLER_DRYRUN FILLER_ID=\"\$FILLER_ID\" FILLER_CPUS=\"\$FILLER_CPUS\" FILLER_NEEDGPU=\"\$FILLER_NEEDGPU\" FILLER_STOPFILE=\"\$FILLER_STOPFILE\" FILLER_END=\"\$FILLER_END\" FILLER_DEADLINE=\"\$FILLER_DEADLINE\" FILLER_PORTS=\"\$FILLER_PORTS\" FILLER_PIDFILE=\"\$FILLER_PIDFILE\" FILLER_GRANTS_DIR=\"\${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}\" WS58_REGIONS=\"\$WS58_REGIONS\" /bin/bash $D/launch.sh --job";;
 '')
  exec > >(tee -a "$D/ws58-launcher.out") 2>&1
  exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /usr/bin/env "FILLER_DRYRUN=${FILLER_DRYRUN:-0}" "FILLER_DRYRUN_DIR=${FILLER_DRYRUN_DIR:-}" "FILLER_STATE_DIR=${FILLER_STATE_DIR:-}" "FILLER_FLAGS_DIR=${FILLER_FLAGS_DIR:-}" "FILLER_GRANTS_DIR=${FILLER_GRANTS_DIR:-/mnt/raid0/llm/tmp/compute-flags/grants}" "FILLER_POLL=${FILLER_POLL:-5}" "FILLER_EST_WALL_S=${FILLER_EST_WALL_S:-7200}" "WS58_REGIONS=${WS58_REGIONS:-}" "FILLER_OWNER=${FILLER_OWNER:-handoff-kvu}" /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
