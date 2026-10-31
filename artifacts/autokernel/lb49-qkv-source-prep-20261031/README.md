# LB49 actual-QKV source preparation — engineering capsule

Prepared2026-10-31 for AKX-ALL-LB4.9-FU-DIVERGE-05a. Source/fixture verification only; scientific05a and the OPCASES implied-logit propagation addendum remain open.

`REPORT.md` explains source ordering, historical-image limits and unfinished scientific scope. `VERIFICATION.json`, `native.log` and `NEGATIVE.json` preserve bounded native compile/fixture results; `PROVENANCE.json` pins original source/library identities. `qkv_snapshot.h`, `capture_qkv.cpp` and `replay_qkv.cpp` are proposed standalone helper sources, with a genuine prior-op/noncontiguous/exact-alias native fixture. No kernel/store source was modified.

Reproduction requires the pinned historical headers/libraries. `build.sh` and `bounded.py` retain their original absolute paths and are an audit recipe, not a production launcher. They must not be used as a READY packet. No model or binary is included. Parent session owns durable publication and source-family row application.
