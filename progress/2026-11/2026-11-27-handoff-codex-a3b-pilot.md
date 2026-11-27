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

Next: codex-a3b-pilot reviews completed cache-safe outputs, measures deterministic and paid guidance, runs the residual legacy pairs, and files accepted-result, token and elapsed-time comparisons.
