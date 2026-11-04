# KPF-17a exactness completion

The preserved CPU run passed 86 original and 111 extended cases, including 25 shared-trunk cases. The completed ROCm suite records 89 supported bitwise-equal cases and 22 declared unsupported cases; all 25 shared cases are supported. The separate ROCm preservation run records 64 supported original-versus-extended cases equal under both skip settings, with the same 22 unsupported cases.

Both GPU rows ended rc=0 with native completion and source/build/library custody. Each supported GPU invocation required at least two during-process own-HIP mapping and positive per-PID KFD VRAM samples. The harness enforces shared-mask controls and finite output. These results close KPF-17a only; they establish no serving speed, adoption, production-kernel change, or completion of the remaining KPF-17 clauses.

RESULT.json records the case counts, native result hashes and library identities. The accompanying filed verdicts preserve the decision rules and scope. This committed conclusion is an observation; no measurement warrant is retrofitted.
