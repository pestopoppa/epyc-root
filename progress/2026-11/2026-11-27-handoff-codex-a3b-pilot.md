# 2026-11-27 — A3B harness revalidation and task comparison

## C22 busy-slot prompt-cache defect isolated and guarded

The repaired OpenCode run exposed a serving defect rather than a model deadline failure. Exact C22 source `ce6fcbbde` can restore a cached prompt into an explicitly selected slot before checking whether that slot is busy. At GPU time 12:54, a concurrent request restored 91,398 tokens into slot 0's active request after 426 tokens had been processed. Its reported progress ratio became 71.91 (a ratio, not percent), and the log repeated 304 checkpoint replacements at the same position. `prefill-budget budget=0` means uncapped admission, not zero admission.

During the unchanged run, GPU busy was 85–99% in seven of eight pre-break samples, then zero in 44 of 45 later samples. The other active GPU streams fell from about 28–31 to 0.85–0.87 tokens/s while the owned CPU server remained near 95 core equivalents. Source, loaded binary hashes, timestamps and observation windows are retained in the C22 incident artifacts. These observations diagnose the failure; they are not a CPU/GPU benchmark.

Main stopped controller 4142230 at its boundary. CPU 4142995 and GPU 4144485 exited cleanly, death was verified, and KFD was empty. The pre-break PAW thinking draft remains a genuine source-grounding rejection; attempts crossing the serving breakpoint remain qualified. The queued deterministic PAW correction did not run. No interrupted candidate is counted as completion.

## Safe serving configuration qualified on all eight slots

Committed `beb0225b1`: both C22 routes require explicit `--cache-ram 0`, and the adapter serializes upstream requests by physical slot. This bypasses the faulty shared RAM-cache path without removing in-slot KV reuse, tools, subagents, reasoning or session persistence. Queue waits count toward the task deadline and are recorded separately from native TTFT. Queued requests cancelled before forwarding consume no model tokens. All 248 Taskflow tests pass.

Main verified the frozen V4 manifest `7661bb92dd613add2f9af608afc5e5795b375b315de17ee50683c0bda7359d36`. The native eight-slot control passed: each CPU/GPU slot processed 6294 cold prompt tokens, a queued title, a long prompt again, an exact repeated prompt with 6290 cache-hit tokens, and a short 26-token tail. All 40 requests completed. Both qualifier servers exited cleanly. The current V4 Python module bytes match the committed source.

Actual task epoch `cache-safe-01` is active under main-owned exec 65525/controller 1016657: CPU PID 1016704, GPU PID 1016973, four slots each. The same fourteen-row task/mode grid is frozen; the four accepted main-only runs are reused. Main has approved one automatic objective-failure report for each GPU thinking case, separately labeled from paid main guidance and from initial success. No task conclusions are claimed yet for this epoch.

## Residual legacy case coverage prepared

TU-GR-1 and MM-5's corrected same-GPU failures still came from the old restricted harness, so they need new matched replays. Prepared original corrected briefs, source pins, final tightened checks, historical witnesses and private Python 3.12 dependencies. Current-container baseline and positive controls pass the intended pattern. Extra imports and offline path requirements were fixed before model work, rather than counted as model failures. Worker inputs exclude oracle code, positive solutions and prior outputs.

The next local grid will run TU ON/OFF and MM ON/OFF concurrently on four cold GPU slots with a common sampler; two CPU OFF candidates can run alongside them. Two new fresh main-only plans are being staged under the existing measured CLI profile. Corrected VERBATIM evidence is reused; no exhaustive original-six-case replay or intrinsic model ceiling is claimed.

Previous next: codex-a3b-pilot reviews completed cache-safe outputs, measures deterministic and paid guidance, runs the residual legacy pairs, and files accepted-result, token and elapsed-time comparisons.


## First clean outputs and independent main comparison additions

The cache-safe epoch remains live on both C22 servers. PAW GPU ON and common-sampler OFF, NARIQ GPU OFF, and PFXC GPU ON have produced rejected candidates; other rows continue. These are preliminary task results, not a final capacity conclusion. PFXC needed another acceptance repair: the old row-major subsequence check could reject valid side-by-side tables and could miss duplicate events. The source-faithful v4 checker passed 16 offline controls and leaves the original main document accepted. The saved A3B thinking document remains rejected: 44 rows instead of 41, repeating source lines 1314, 1330 and 1429. Original scores and candidate bytes are preserved. Main withdrew its unconsumed inaccurate deterministic feedback and queued the precise v4 report, with hashes and a migration receipt.

Both additional fresh main-only runs completed and their changed Python was reviewed before independent checks. MM-5 passes its sealed check. TU-GR-1 fails the injected namespace permission-refusal control: its environmental skip regex fails to recognize `unshare: write failed /proc/self/uid_map: Operation not permitted`. This is a main-model candidate defect, not a missing tool or sandbox failure. Direct first-pass results are retained; any subsequent repair must have its own measured cost. No six-of-six main success claim is warranted. Native inference and main-comparison measurements remain separate.

Previous next: codex-a3b-pilot reviews further clean outputs, completes measured recovery and independent review, launches the residual local legacy pairs at an owned serving boundary, and files the mode/token/time comparison.


## Accepted interrupted artifact and remaining replay queued

W66 common-sampler GPU OFF reached its 1800-second deadline after 16,482 generated tokens, with a scoped patch that passes both independent regression calls. Main reviewed the real reference-store write and retained fixture assertions. Record the artifact as accepted, while preserving `status=interrupted` and `candidate_status=oracle_pass`: the model had not ended normally. This distinction prevents a timeout from hiding useful completed code or becoming a normal-completion claim.

Main independently verified the sealed legacy runner (9498641010d8c6e910862f38e1f838e28432a7934b205a2a874b3079837c3fd2), including 4155 dependency files. Actual stock-tool scripted controls cover six jobs, two simultaneous cases, same-session reasoning continuation and both unchanged positive oracles. Six native rows are approved. Main-owned watcher PID1815819/exec38040 waits for exact controller1016657 and server start identities to exit, then launches the owned CPU/GPU C22 grid under a new region lock. It is waiting, not running legacy inference yet.

Main stopped only its exact owned v4 feedback helper PID1059357 after validating command-line/start identity, verified its death, then activated tested policy v5 under exec8508. V5 queues one objective-only round for GPU ON and OFF-recommended representatives, skips consumed guidance, and uses revised PFXC grading. Three OFF reports were queued; W66 remains pending. No extra main-model diagnosis call is charged to deterministic feedback.

The separate measured TU main-only repair is launched under exec16235, preserving direct-first-pass failure and all costs. Its separate turn finished in 71.562237s with 57572 input tokens (49792 cached, 7780 uncached), 460 output tokens including 51 explicitly reported reasoning tokens. It changed only the namespace permission-refusal pattern; source/command review and the unchanged independent oracle now pass. Preserve five initial accepted cases plus one accepted after measured repair, not six initial successes. The NARIQ ON deterministic recovery now passes its structural oracle (1436 generated tokens, 172.403s). Structural passage is not semantic acceptance: main launched a fresh, separately metered source review under exec22010, with a neutral ACCEPT/REJECT prompt and no access to the main-only answer. That review finished with REJECT after source checks: it identified material arithmetic, MFMA ownership, grouped-preparation compatibility and unsupported execution claims. The proposal was left unmodified. Its metered cost is 123494 input tokens (91008 cached/32486 uncached), 1016 output tokens including 21 explicit reasoning tokens, and 95.819931s. Main audited three source-only commands and the allowed AMD primary reference. Exact feedback is queued as same-session A3B ON continuation ordinal2; this is one paid diagnosis round after one deterministic round, not a main repair. The structural-pass receipt is retained without becoming semantic acceptance.

PFXC assessment snapshots replay original accepted-main and rejected-A3B artifacts without mutating scores; further terminal-only reassessment is separate from live candidates.

Next: codex-a3b-pilot completes measured main repair, adds deterministic feedback for thinking-off candidates, reviews live corrections, and compares accepted artifacts, normal completions, tokens and elapsed time across all six cases.
