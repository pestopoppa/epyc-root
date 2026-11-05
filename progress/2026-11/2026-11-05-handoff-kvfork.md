# 2026-11-05 — handoff kvfork

## 00:03Z — File the GDB continue qualification result and ready the missing timeout-cleanup control

KPF-17.GDB-CONTINUE: filed kvfork17-gdb-continue-qual-r2-20261104 inconclusive (rc 0; normal and exit-23 controls passed, timeout cleanup not exercised). Published kvfork17-timeout-qual-20261104 after four-CPU smoke PASS to measure the missing timeout-cleanup clause. The separate model oracle and full qualification remain open.

## 00:18Z — Repair KVU-11c mechanics packet and submit its publisher smoke

Removed incomplete KPF-17 oracle r6 scratch (about 792 MiB). Recovered the reviewed KVU-11c GPU ID lookup correction and sealed the r2 mechanics packet. Publisher queued its model-free smoke because the GPU was busy; no smoke PASS, ready row, target request or parent gate verdict yet. Earlier KPF-61 lineage remains parked after three qualification failures.

## 00:24Z — Publish the group-3 rowflow socket deadline qualification

Published kpf18-g3-rowflow-socket-qual-20261105 after its four-CPU publisher smoke passed six real-socket controls. The full qualification is pending; this does not establish native cancellation, task release, GPU admission or the group-3 layout verdict. Removed the superseded clean KPF-64 r2 source worktree (about 2.1 GiB); retained referenced row inputs and evidence.

## 00:24Z — Publish the group-3 rowflow socket deadline qualification

Published kpf18-g3-rowflow-socket-qual-20261105 after its four-CPU publisher smoke passed six real-socket controls. The full qualification is pending; this does not establish native cancellation, task release, GPU admission or the group-3 layout verdict. Removed the superseded clean KPF-64 r2 source worktree (about 2.1 GiB); retained referenced row inputs and evidence.

## 00:28Z — Repair the GPU mechanics launcher resource claim

KVU-11c: corrected the existing r2 launcher to declare CPUs 184-187 after the GPU-exclusive admission refusal. Publisher accepted the resubmission but queued its model-free smoke because the GPU was busy; no smoke PASS, ready row or TTS result is claimed. Three superseded KPF-50 scratch attempts could not be removed because execution policy rejected the removal.

## 00:33Z — Prepare and submit the immutable-plan qualification row

KPF-17.4-PLAN-QUAL: adopted the sealed model-free native-judge adapter into this lane, retained its 120 s workload and 7 s cleanup limits, and submitted it with a 300 s reservation. Publisher was still running when the session proceeded; PASS and publication are not claimed. Registered ready and smoke-failure events for dispatcher resumption. KVU-11c GPU smoke remains queued.

## 00:35Z — Repair the sealed plan-adapter packet and publish its qualification row

KPF-17.4-PLAN-QUAL: the first publisher smoke failed before job entry because the adapted spec digest did not match SHA256SUMS; all other sealed members matched. Preserved the failure and repaired only that digest. The four-CPU publisher smoke then passed and published kpf174-plan-bound-integration-20261105. Smoke established synthetic native equality, missing-launch refusal and owned PID cleanup only; the full qualification and historical rejudgment remain open.
