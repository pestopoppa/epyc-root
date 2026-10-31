# RVP-C2-12 existing producer and consumer — 2026-10-31

Producer `f744cc220e722d1bda93783959471d44f8e118b0` contains the selected-layout branch. It emits `hard_failure=true` and returns FAIL when a selected noncontiguous layout is unsupported; the flag requires test mode and a suite seed. `git merge-base --is-ancestor f744cc220e722d1bda93783959471d44f8e118b0 ffc1bac82eeca6f9099e1ccd9ba49703c460a115` exited 0, so this producer is in frozen production-source ancestry. The excerpt is from the producer commit, not a newly built or executed binary.

Research main `93c217ec5d743da8f81b430630a03ad3638d106a` retains the console and CSV consumers. HOST unit fixtures in TEST.log pass both unsupported-layout-to-FAIL paths. This is source/fixture verification; no new native backend test, performance result, production edit or build is claimed.
