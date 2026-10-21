#!/bin/bash
# Dry-run of filler_run2.sh: --gpu-quiet exclusive, --role/--claim-cpus, --precond-cmd (rc=5 build-missing). Fake region-lock + grants dir, no inference.
cd /mnt/raid0/llm/tmp/fillers-3c4ca599 || exit 1
T=/mnt/raid0/llm/tmp/fillers-3c4ca599/dryrun_excl
rm -rf "$T"; mkdir -p "$T/g" "$T/s"
cat > "$T/fakerl" <<'EOF2'
#!/bin/bash
echo "$@" > /mnt/raid0/llm/tmp/fillers-3c4ca599/dryrun_excl/rl.args
while [ "$1" != "--" ]; do shift; done; shift; exec "$@"
EOF2
chmod +x "$T/fakerl"
export FILLER_GRANTS_DIR=$T/g FILLERS_MD=$T/FILLERS.md FILLER_STATE_DIR=$T/s FILLER_POLL=2 FILLER_RL=$T/fakerl FILLER_GPU_LOCK=$T/gpu.lock
printf '| xg | x |\n' > "$T/FILLERS.md"
iso() { date -u -d "@$1" +%FT%TZ; }
grant() { now=$(date -u +%s); echo "regions=$2 start=$(iso $now) end=$(iso $((now+$3)))" > "$T/g/$1.grant"; }
echo "== A: bad combos rejected (rc 64)"
./filler_run2.sh --id bad1 --class cpu --gpu-quiet exclusive --cmd x --stop $T/S; echo "cpu+exclusive rc=$?"
./filler_run2.sh --id bad2 --class gpu --gpu-quiet bogus --cmd x --stop $T/S 2>&1 | tail -1; ./filler_run2.sh --id bad3 --class gpu --claim-cpus 'a-b' --cmd x --stop $T/S 2>&1 | tail -1
echo "== B: gpu exclusive: region-lock gets --cpu-list 0-95 --gpu-quiet exclusive --role bench; job sees host threads 184-191; GPU flock held"
setsid ./filler_run2.sh --id xg --class gpu --gpu-quiet exclusive --cmd 'echo "cpus=$FILLER_CPUS thr=$FILLER_THREADS needgpu=$FILLER_NEEDGPU" > '$T'/job.env; (flock -n 9 && echo gpulock-was-free) 2>/dev/null; sleep 2' --min-window 20 --stop $T/STOP --precond-cmd "test -e $T/BUILD_OK || { echo 'kqroute arm build absent'; exit 5; }" > $T/xg.log 2>&1 &
L=$!
sleep 1
echo "== C: precondition fails (no build) -> rc=5 build-missing, nothing launched"
grant xg mi210_0 200; sleep 6; cat $T/g/xg.ended; ls $T/rl.args 2>&1 | head -1; ls $T/job.env 2>&1 | head -1
echo "== D: build appears -> same poller runs the job under the exclusive claim"
touch $T/BUILD_OK; grant xg mi210_0,184-191 200; sleep 12
echo "rl.args: $(cat $T/rl.args)"; echo "job.env: $(cat $T/job.env)"; cat $T/g/xg.ended
kill $L; sleep 1; ps -p $L >/dev/null 2>&1 && echo "launcher ALIVE" || echo "launcher dead (verified)"
echo "== E: default gpu class unchanged (shared, role build, no cpu-list) and cpu timing mode (role bench, claim 0-95, gpu-quiet shared)"
setsid ./filler_run2.sh --id dg --class gpu --cmd 'sleep 1' --min-window 20 --stop $T/S2 > $T/dg.log 2>&1 & L2=$!
setsid ./filler_run2.sh --id dc --class cpu --role bench --claim-cpus 0-95 --gpu-quiet shared --cmd 'sleep 1' --min-window 20 --stop $T/S3 > $T/dc.log 2>&1 & L3=$!
sleep 1; grant dg mi210_0 200; sleep 7; echo "default gpu rl.args: $(cat $T/rl.args)"
grant dc q2 200; sleep 7; echo "cpu timing rl.args: $(cat $T/rl.args)"; cat $T/g/dc.ended
kill $L2 $L3; sleep 1; for p in $L2 $L3; do ps -p $p >/dev/null 2>&1 && echo "pid $p ALIVE" || echo "pid $p dead (verified)"; done
