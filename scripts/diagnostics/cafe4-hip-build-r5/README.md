CAFE-4 failure-attribution HIP build qualification (R5)
========================================================

Row `df2-cafe4-modes-hip-build-r5-20261119` builds the failure-attribution
candidate from epyc-root commit `da4a54ac03aba5ec1d95db5e1b68aec8794e954d`.
It reuses the R4 driver contracts and existing detached v10 diagnostic tree,
with a separate scratch root `/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r5-20261119`.
Production and previous qualified outputs are untouched.

Generated candidate SHA-256:
`e6546aa7417e40efecdd2bb03de61416bf62ae21b7c1369b7161e443201f835d`.
Header SHA-256:
`f544e718f34f2b7347d2ceeebf566eb575250c20760720676682512573507848`.
`inputs.json` binds all five prepared inputs. The compiled smoke object and
full executable must now contain `CAFE4_TRIAL_FAILURE` and
`CAFE4_CONTROL_FAILURE` as well as the six existing markers. Full qualification
retains exact defined IQK/HIP exports, local six-library linkage, artifact
hashes, the Clang IQK compatibility setting and gfx90a configuration/content.
This is build qualification only; native error gate **0.743863867** remains
fixed and unevaluated. Lower error is better.

Validation: **8/8 ELF-fixture regression tests PASS** against this R5 driver;
launcher shell syntax PASS and pinned source/input validation PASS.
`publish_row.py` accepted publication but returned **queued for smoke**.
No four-CPU smoke PASS or full build result is claimed. Smoke will compile the
candidate object and exercise the existing IQK negative/fixed translation-unit
checks; full scheduled build is required before publishing native GPU controls.
Stop on source mismatch, build/linkage failure, STOP or deadline; stop on
answer at a validated full receipt. No model is loaded by this row.

Next: consume smoke outcome (repair any failure); file the scheduled R5 build
receipt when available, then publish fresh native GPU width2/3 normal and
explicit-fault controls without changing the numerical gate. CPU R2 is independent.
[no-belief: build-row publication and validator tests only; smoke queued]
