Native row preparation, 2026-11-02

Scratch spec: `/mnt/raid0/llm/tmp/kvu/k35-native-validation-20261102/row-spec.json`.
Launcher: same directory, `launcher.sh`. Owner publishes; this preparation did not
publish, obtain a grant, start a model, or modify a shared repository.

The row uses the existing `frontdoor_gpu_native_mtp` scenario's exact target,
`/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, with its same-file MTP
head. This is not a replacement drafter for the stale 27B scenario. Full-row arms
use eight host threads (native smoke pins four actual granted CPUs and four threads), one slot, 512 ubatch, 2048 nominal context, identical
prepared prompt, greedy seed 35, 16 maximum output tokens and one-token minimum.
The first arm exercises the reviewed request-zero-to-dedicated-server conversion;
the second uses a fresh native-MTP server. No slot cache path is shared.

Production GPU store `gpu-20260921-ffc1bac82` has been verified outside any grant:
16 server/library files match its SHA256SUMS and `--version` identifies ffc1bac82.
`prepared.json` preserves those digests plus identities for the model, sources,
prompt and catalog. The model's GGUF header and stat identity were checked;
there is no full weight digest claim. The launcher checks cheap stat identities
only; it performs no tokenization, download, weight copying or weight hashing.

Full row reserves GPU and whole-host quiet CPUs, estimate/minimum 600 seconds,
ports 19761 and 19762. Native qualification runs only the first real no-draft
cell and emits its unit to FILLER_DRYRUN_RESULT_PATH only after captured-server
cleanup proves dead/completed. Full results appear only after both cells pass;
failed health ownership, sampling, cleanup or short completion emits no success
unit. Captured server PIDs are registered for engine cleanup. Server spawn overrides
start_new_session=False, retaining the engine process group. The parent_exec.py
exec wrapper arms Linux PR_SET_PDEATHSIG=SIGKILL and verifies the expected parent
both before and after arming. An abrupt worker death therefore kills the execed
server as well. TERM/INT stops the captured server and prevents subsequent cells.
A 100 ms watcher checks STOP/deadline throughout blocking startup/request/sampling
operations, terminates the captured child and escalates to KILL after 3 seconds.
Stop/deadline are also checked before each new cell, with 150 seconds reserved; startup is capped at 120 seconds and
request timeout at 45 seconds. Engine hard-end/group cleanup remains applicable.

Offline checks: 22 tests pass (10 existing reviewed guard tests, 4 packet tests,
and 8 custody/affinity tests). Real lightweight subprocess controls verify retained
PID/group, parent-death cleanup after worker SIGKILL, parent-mismatch refusal,
blocking-operation STOP/deadline interruption and four-CPU inherited/granted
affinity. No model process is used by those controls; launcher
shell syntax passes; rowflow launcher parsing/lint and handoff ownership checks
pass without publication. GitNexus exact K35 run_cell upstream impact: LOW,
3 nodes, no affected runtime processes. Lane itself is unindexed; no reindex was
performed because only isolated new preparation files were created.

Limits: runtime load/architecture compatibility, native cleanup and result-path
behavior are not yet observed. This validation tests lifecycle, not throughput,
quality, graph-memory plateau or global coverage of other runners. ROCm telemetry
is retained by the K35 runner; no certified GPU-residency/benchmark claim follows.
An actual owner publication/qualification is still required. No measurement or
verified finding producer is introduced: result envelopes explicitly mark
measurement_claim=false; these are engineering validation records.
