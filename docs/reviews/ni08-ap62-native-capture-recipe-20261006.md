# NI08 AP62 invocation-log bounded native-capture recipe (proposal)

This recipe exercises the reviewed request-log snapshot synchronization controls against the
selected synthetic unit-test module at APP commit `578865fb633d09839547a54f6bf9378b0b934dd6`.
It does not start the API/server, invoke a real tool or model, run inference, claim production
concurrency rates, or claim deployment. The suite is run with `ORCHESTRATOR_MOCK_MODE=1`,
`--noconftest`, an explicit empty pytest config, disabled plugin autoload/cache/bytecode, and an
isolated runner virtual environment.

The selection is 14 exact JUnit identities: all original request scoping and ring-buffer controls,
including append and clear concurrent-write cases, plus the updated deterministic writer-lock
instrumentation. The 434-path AST-resolved APP source readset (including the actual tool registry,
REPL-environment import closure, route AST guard inputs, test module and `tests/conftest.py` as an
explicit exclusion) is bound alongside the exact ROOT carrier, shared adapter/grader, task row,
workflow, case manifest, package-version manifest, requirements and generated source context.
The readset includes the recursive tracked-module import graph for the selected test and its imported package initializers, plus all original route-scanner inputs; dynamic string imports remain a stated static-analysis limit. Dependencies are installed only from the hash-locked wheel closure recorded from APP `uv.lock`.

The existing native fixture carrier must report the exact 14 identities with no failures, errors or
skips. The retained receipt is projected through the existing `ci_conformance` adapter and
`ClaimTuple.grade()` and must remain at its existing `Judged/Located` ceiling. Input SHA-256 maps are
compared before and after shared grading. Status is initialized before setup, and original JUnit,
receipt/readset, source context, dependency/environment records and validation are uploaded even
when setup or capture fails.
