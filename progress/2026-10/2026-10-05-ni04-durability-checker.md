# NI05-04 — docs and handoff durability scan support

MAIN accepted the checker implementation after [NI05 third run 37280071522](https://github.com/pestopoppa/epyc-root/actions/runs/37280071522) passed 77 checker fixtures; exactly one named live-host corpus test was deselected. The canonical NIB2-73e requirement is extension of the checker to docs/handoffs, which the code and fixtures satisfy.

The opt-in prose scan covers declared documentation and handoff roots, resolves local evidence references using the existing repo/main-clone rules, and captures original source hashes, document/line/target identities, readset, UTC, checker revision/digest and native verdicts. Markdown links and percent-escaped paths are handled without converting external URLs or prose advisories into strict registry failures. Ordinary registry validation retains its strict exit behavior.

The producer now authors result-specific decided propositions: native OK states the criterion evaluated true; MISSING, UNREADABLE and EPHEMERAL state false with their exact native verdict; qualified caveats remain unknown and emit no boolean tuple. This corrected write side is research `9042318847d7371542a4780a8fa3f6d9b326cf1c`, included in tested candidate `e98909009f5dd2d148ad0e93029ea9fb85ba031f`; checker SHA-256 is `c46aa7f76064782f03b0db388bef220f301f6ff6d7d397c2e2274eac84eadc10`.

This checkpoint does not assert that the full live registry/raw corpus or every host citation was scanned or repaired. `test_the_real_registry_has_no_durability_errors` requires that corpus and was explicitly excluded off-host. A future broad host scan is a separate execution with its own original native receipt and declared scope. No local tests, inference, reloads, production changes or historical backfill occurred.
