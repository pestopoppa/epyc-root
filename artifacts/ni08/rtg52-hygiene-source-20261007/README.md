# RTG-52 hook source reconciliation

MAIN reviewed the exact two-file proposal `19176ad19bd08c25f0c404d49c5ec8ace1e392be`, independently compared its preimages with the integration lane, and parsed both source files without importing them. [Exact source identities](MAIN-source-review.json).

The current parser already removes shell redirections before computing positional arguments and consumes `-F` values; its old task was stale. The remaining source fix makes every refusal explain the operator shell/session environment path and why a command-local environment prefix cannot change the hook environment. Enforcement, authorization and environment lookup are unchanged. Added assertions exercise the refusal through the existing script when it is next run; no new test execution or native pass is claimed.

The protected coordination proposals remain separate and require exact D9 authorization before merge. No override, host process action or deployment is performed.
