# KPF-62.3 native vocabulary census, scoped observation

The full attempt reported `CENSUS_COMPLETE`, while the outer run ended rc75 `partial-native-incomplete`. The retained attempt has two complete sequential vocabularies, each 151,936 pieces, with SHA-256 `902ea571177dd0f5092b82e0aa39d562ede8d47efdd7fdde173ef9bf45227b1c` and `c2eb2f9537c5cd877d040f5dacc33ca87dba48c4aac0aa75cc6cd843cf7930af`. Both native stdout markers report `PIECES_COMPLETE 151936 N_VOCAB 151936`. RESULT records matching model metadata and cleanup.

The original result does not independently record all compile/enumeration exits, source/library seal checks, output-limit enforcement and PID/pidfd cleanup required by the decision rule. The historical outer environment and completion-check stderr are not retained; the known FILLER_ID scope defect is a plausible explanation for rc75, not a proven historical cause. The census verdict is inconclusive; alignment, compatibility, quality and the parent selector task remain unknown.

The same-attempt result, two TSVs, native stdout/stderr and mapping evidence were copied before filing to `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf623-census-retained-20261105/`, with a KEEP marker; the TSV digests were checked on that copy. The two TSVs are useful as provisional inputs and must not be promoted to an accepted census merely by a later analysis.

The retained unmodified native `RESULT.json` SHA-256 is `47a215bcbe529d610e8d1b5fb9db65a58df76ae140a3c4dfaa8d7308a431abc5`.
