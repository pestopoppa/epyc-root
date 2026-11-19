# KPF-17.4 model-free integration qualification

PREPARED_UNEXECUTED; ready=false. Owner: h-heterogeneous-slot-fabric-residency. launch.sh uses the canonical filler_run15 engine. Grant/CPU ownership is the engine's responsibility; the job makes no independent grant-validation claim.

Full mode checks native exact equality, expected honest/mutant verdicts, and all ten pre-native refusal controls on sealed synthetic group901/c17 data. It writes out/RESULT.json only after successful cleanup. No inference or historical rejudgment occurs.

Engine dryrun mode requires FILLER_DRYRUN=1 or FILLER_SMOKE=1 and a separate FILLER_DRYRUN_RESULT_PATH. It checks the same synthetic baseline plus one missing-launch refusal, labels every output SMOKE_ONLY, and cannot satisfy full completion. Full mode uses MODEL_FREE_QUALIFICATION.

Every job creates an exclusive out/{smoke,full}-UTC-uuid directory. PRE_SEAL and POST_SEAL bind all inputs; END records errors and cleanup outcome. Workload is limited to 120 seconds, shortened to preserve seven seconds of bounded cleanup before grant end. Only the captured child PID is signaled. Missing PID-absence proof prevents success publication. Receipt writing necessarily requires writable storage and a live supervisor; SIGKILL and storage failure cannot guarantee a receipt.

Native sources remain pinned to research commit 1157adc2f007d1b0c45ddc6daf91eafc45358df7. SHA256SUMS seals all local runtime files. No tests, smoke, full qualification, registry publication or inference has been executed.

Launcher precondition checks SHA256SUMS. The engine exports FILLER_ID, FILLER_END, FILLER_STOPFILE and FILLER_CPUS. The worker preserves actual inherited process affinity instead of widening to the declared CPU text.
