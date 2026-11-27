W66 worker-local replay found no worker/independent-checker disagreement.

| Frozen candidate | Original combined acceptance | Runtime alone | Serial alone | Independent checker |
| --- | --- | --- | --- | --- |
| Unchanged baseline | fail | fail | pass | fail |
| GPU OFF common sampling final | pass | pass | pass | pass |
| GPU OFF recommended final | fail | fail | pass | fail |

The baseline root cause is the nonexistent `store/runtime-preparation/fixture-runtime-selection` reference. Recommended's final root cause is `runtime integration lacks a durable selection receipt`, subsequently wrapped by `RunAborted`. These are test-fixture failures rather than an absent worker dependency. Both tests use pytest's `autokernel.loop` package namespace.

Common's two saved final edits completed at epoch milliseconds 1795740340967 and 1795740422619. Its final runtime test passed at 1795740434507; its final serial test passed at 1795740445296, roughly 1.56 seconds before terminal interruption (1795740446858). Earlier failure outputs predate its final edits. It therefore did retest the passing final fix; this trace does not establish continued debugging after a known final pass. Recommended's last edit completed 1795742589892; its subsequent runtime tests still failed. `EDIT-STATE.json` replays every successful edit from the pinned baseline and exactly matches each final candidate hash.

The session includes diagnostic patches to `scripts.kernel_rnd.autokernel.loop` while pytest exceptions originate in `autokernel.loop`. Those commands also pipe to tail/head/grep, hiding upstream failures and returning a pipeline status unrelated to pytest. The fresh stock namespace probe confirms the same source path loads as two different module and PhaseJournal class objects; this is a diagnostic-script concern, not evidence of a worker/oracle environment mismatch.

`replay.py` imports the unchanged qualified stock Sandbox and canonical case stager configuration. Each of three fresh containers uses the same image, Python packages, readonly reference closure, Git metadata/config, executable, context/generation configuration, and bounded CPUs. Baseline files are hash checked; the exact final target file is copied from the saved artifact after checking RESULT's recorded SHA. Every command has full stdout/stderr logs and real subprocess return codes. The independent oracle is byte-identical and invoked via canonical `--pytest` mode. No prompt or model session is created; upstream port 1 provides no model endpoint. Native form servers exist only as required by the stock Sandbox lifecycle, and each owned container is verified removed.

`REPLAY.json` binds raw RESULT/session/case/checker/baseline/final-source hashes before and after and records unchanged sources. Original raw scores and all private source state remain intact. This is a deterministic acceptance/environment diagnostic, not a new model attempt, timing comparison, or thinking-time causal result. The stock container metadata pins the image/dependency/executable mounts. The copied Git metadata avoids any git add/commit commands; pytest fixture repositories use their normal isolated Git setup.

Next: main integrate the scoped chronology and acceptance findings; retain common's oracle-pass interrupted status and recommended's oracle-fail interrupted status separately.
