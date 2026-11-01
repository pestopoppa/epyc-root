# TD-17 APP publication addendum

Added after the partial-wrap draft; scratch-only, for ROOT to apply to durable progress/handoff when authorized.

- APP main publication commit: `5cb3f2c9a7d510f498acbd77eaaed587a59d5399`.
- First parent / prior fresh APP main: `f0310d9db781f3dd0a2a4d122cc4efcf7425e929` (TU publication already present).
- Second parent / CI-reviewed TD-17 candidate: `027427c223d53a0b5a95541e5e2e49cd2cf0dc5d`.
- Published under the canonical APP serialized push lease with `--fetch --push`; push output says `f0310d9d..5cb3f2c9 HEAD -> main` and `PUSH VERIFIED`; `origin/main` carries HEAD, and `git cherry origin/main HEAD` is empty.
- Native `git merge-tree --write-tree` merge produced tree `c0de7fd0475fc85a6c46fb9096ef76ed42540355`. Diff from f0310d9d contains exactly the five TD-17 paths. Each resulting blob equals the corresponding blob in candidate 027427c2. `git diff --check` is clean; shared index tree equals HEAD tree; worktree status is clean.
- Five final source SHA-256 values match the pre-transaction preservation hashes: workflow `8ca555be8997782cd2021087afdb5a7dd685794f519f1047e95995feefaff27a`; adapter `6d1d41d7cf9b221a7d649e3769e3bebbeb90166aa048b40f3e12d0d35d393e51`; test `a09734633a47f812936c6a5becf42bb5ce7c32387c4c61e0274fbebab59a1682`; fixture README `4d0050e8ccf7cc2f1212b3e253c7835fb7b1b376d39af676af7efc154a744532`; frozen data `763949cdf07f422cbb3c4bd040392944034ae4caf23a07de08fcef04cfd1eb33`.
- Hosted tests remain the accepted run 41287440906 (70 passed, exit 0). No new test rerun, model call, or calibration result was produced by the merge.
- TD-17 remains open: this source adapter and model-free controls do not complete the required TD-18 live per-model-pin native/JSON metric report. No checkbox or quota credit is claimed.
