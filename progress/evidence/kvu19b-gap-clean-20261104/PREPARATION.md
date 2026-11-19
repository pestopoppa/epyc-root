# KVU-19b-gap clean remeasurement preparation

Runnable spec: spec.json. Detached source commit1bceceb0514d423ad220888313eafcddc30e485e.
No publication or inference/GPU work was performed. Genuine GPU qualification has NOT RUN.

Scope: six fresh-process alternating AB/BA pairs, unified vs split in the same commit1 library set, gemma3-1b q8_0 at4x16384 and draft1. Quiet whole-host reservation is deliberate because the historical1B timing was host-contended; model process is affinitized to 184-191; actual llama context thread count not measured. Four-CPU qualification is one real model-loaded pair at128 tokens/sequence and2048 real synchronized decode steps. Allocator must supply actual grant before qualification; no offline result qualifies it.

Offline validation: eleven controls passed (actual four-CPU affinity intersection, wrong-grant refusal, exact native output shape/missing/duplicate refusal, changed model stat refusal, arm-order-independent paired percentage deltas, reused-PID refusal and exited-leader no-signal refusal, verified-identity-only registry removal, belief qualification/missing-warrant refusal), shell syntax and sealed runtime catalog checks. These are not a GPU smoke.

No copies, compilation, download, tokenization or weight hashing occurs in the GPU grant. Runtime stat-checks the precomputed model hash receipt, verifies small artifact identities, and runs native inference. Child PID/birth is captured, registered with engine and sampled for MI210 own-PID VRAM plus all selected ggml maps; child gets parent-death KILL and birth-checked captured-PID cleanup escalates TERM/KILL and verifies drain; unexpected remaining group members refuse cleanup without signaling them. STOP/deadline refuses incomplete results. Each native stdout/stderr and per-child lifecycle record is retained. Same-UID custody limitations remain explicit.

Preparation note: a small g++ harness compile on taskset0-3 finished in the tool call before the parent's later no-compile steering arrived. Exact command, source/header input digests, compiler digest and resulting binary digest are retained in assets.json and compile.log. No further compilation was done. If policy requires every build to have an allocator grant, owner should prepare a separate CPU build row before GPU publication; this artifact has no granted-build claim.

Readiness limits: source/manifest/shell/offline controls pass. Actual four-CPU GPU lifecycle, per-PID KFD/HIP mappings and clean-host grant have not been qualified. Do not label the packet READY/PASS until the publisher performs that native smoke. Verified child cleanup atomically removes its own exact PID/birth registration; active children remain registered and unverified cleanup never deregisters them. No parent completion or profiling claim follows this descriptive remeasurement.

Native prospective write hook is implemented using pinned shared ClaimTuple schema; strict adapter projection and planning-context canary remain pending under VB-FA-MASKSKIP. No historical backfill or grade is invented.

Belief success-path control creates a complete synthetic row with actual temporary stdout/stderr, constructs shared ClaimTuple, verifies reps=1 process plus100 correlated steps and raw hashes, and refuses after mutating either raw file. Eleven offline tests passed; no GPU inference.

The native harness does not set cp.n_threads. Exact native context thread count remains unknown; eight host CPUs describes enforced affinity only. ClaimTuple omits threads applicability and records the eight-CPU affinity separately. Four batched sequences are not independent replicates. Binary and recipe unchanged.

Publication-smoke repair: dryrun --job selects first four CPUs in actual grant intersect inherited affinity, then execs taskset before integrity checks or producer launch. Producer independently verifies exactly four CPUs. Launcher selector passes a real offline subprocess test for all0-191 grant and insufficient-grant refusal. Prior checksum refusal executed no model.

Third qualification design preserves prior exposures. Second native pair passed its own four-CPU/lifecycle/custody checks, but independent publisher sampler missed the short subsecond model window; this is not absent GPU execution. Qualification now uses2048 real synchronized decode steps per own128 arm (approximately14s at measured6–7ms/step), without sleeps or fake work. Full protocol remains own16384/100 steps.
