# Bundle gate verdict templates

These tracked copies preserve the reviewed C3/C4 bundle fixes and C5 R2 fix. They are operational templates: the original absolute build, instrument, slot, and run paths remain unchanged. Publishing them does not execute a gate, promote a kernel, or assert a model result. The existing G1 gate files in this directory remain unchanged.

The parent checks structured results after successful children. C3/C4 reject a false MTP verdict or divergent identity even when the child exits zero. C5 checks greedy identity and runtime smoke, rejects contradictory or malformed evidence, preserves child failures and smoke INCONCLUSIVE exit 5, and rejects unsupported top-level or comparison-level timing verdict fields. Q38FN timing remains an uncalibrated sign observation with `decisive: null`; the wrapper introduces no performance threshold. Smoke uses the producer's existing ratio >= 3 engagement condition.

Run only under an approved CPU compute grant, with the complete body pinned to the grant CPUs:

```bash
bash scripts/champion/fold_gates/regression/test_bundle_gate_verdict.sh
bash scripts/champion/fold_gates/regression/test_bundle_gate_verdict_c5.sh
```

The regressions use synthetic children; they do not start servers, contact an API, run a benchmark, or execute the operational templates. The C5 regression runs the actual producer's serializer/classifier with intercepted arm execution and frozen inputs. It then exercises the original and fixed parent `steps()` bodies with the same producer-generated DIVERGES/LENGTH records and child exit zero, expecting old 0 and fixed 1. JSON rejection cases, completion/death evidence, smoke writes/engagement, and exit 5/7 are covered. The C3/C4 regression also proves a planted failed assertion makes the aggregate harness fail.

`BUNDLE-SOURCES.SHA256` pins exact copies of the three adopted/tested templates and two historical C5 fixtures. The fixtures are reference inputs, never operational entry points. Their bytes come from `/mnt/raid0/llm/tmp/c5-fold-prep/{bundle_gate_c5.sh,greedy_compare_c5.py}`; tracking them removes ephemeral-path dependencies from the regression. Only regression source paths and the standalone Python regression filename change during publication.

C5's first regression attempt failed on 2026-10-25 at 11:42Z: its fixture injected a comparison verdict that the real sign-only producer does not emit, and the proposed helper missed that nested field. That receipt remains at `/mnt/raid0/llm/tmp/codex-ni-20261025-bundle-gate-audit/c5-validation/test.log`. Reviewed R2 passed in an official grant at 11:54Z, including native producer and old/new parent cases; the publication job reruns from this tracked location to validate relative-path adaptation. These are software correctness checks, not inference measurements or a regrade of historical model results.
