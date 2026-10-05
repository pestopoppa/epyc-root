# NI45 run 37378870278 custody boundary

This worker-owned note records the terminal boundary for the NI45 APP fixture in workflow run `37378870278` (attempt 1). It does not modify shared progress, handoff indices, wiki, claim records, or the source candidate.

The private capture is `/mnt/raid0/llm/ni53-recipe-run-37378870278-20261005`. Its native custody manifest is `custody-manifest.sha256`, covering 148 files; the manifest file SHA-256 is `de98b1ccb51b4e745758be797737af649e7c923aeda132ebf563bb9284c017ca`. All six artifact ZIPs were verified against API-reported sizes and SHA-256 values. The captured Actions logs ZIP SHA-256 is `a2c8b36dabd3d4f4d5fc22cfd80e8723ddd7dd8732b45f1c1cc7912a2a28b88d`.

NI45 postcheck: `extracted/11373111508/postcheck.json` records all11 evidence postchecks `true`; 11/11 exact tests passed, with zero failures, errors, or skips. The full custody and source checks passed. Main independently verified 148 custody files, 88 members across the six ZIPs, 19 Git inputs plus 6 external inputs, and the 11 true postchecks.

The native receipt file SHA-256 is `029fea208adb4ebbab1861f1bbdcd31a2ebc792d59ebf9e62017490f1dbaaa12`; the embedded self-hash is `fb9efc34152246ad043057dee65c5fd0c79743ff20659ad57994d179a64de1bb`. These are distinct fields and must not be conflated.

This records NI45 only. The paired NI53 job remains a separate failed result (8/10 tests; two capture-related failures), and no NI53 pass is implied by this note.

Main publication: exact reviewed source/test bytes are on APP main `f884406e76d12a98254372a819e1fa6248c9223c`. Original public custody and derivative review: [strategy CLI fixtures](../../artifacts/ni05/strategy-cli-fixtures-37378870278/README.md). Two canonical task checkboxes close; shared prospective CI wiring remains open for other scopes.
