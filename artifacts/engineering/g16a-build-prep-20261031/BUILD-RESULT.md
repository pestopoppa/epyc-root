# G16a build prerequisite — 2026-10-31

Private experimental candidate `af90102c7c3659c78b4e4c87698e258525c77000` (tree `c41a880ae27d83a295a37df906dd6492159a5ae6`) descends from frozen production `ffc1bac82eeca6f9099e1ccd9ba49703c460a115` and applies the exact two-file C3 patch. The eight original eval shapes and `1e-7` NMSE threshold are unchanged.

The full `test-backend-ops` target built successfully for CPU (152.53 s, peak whole-tree RSS 1.32 GB) and explicit gfx90a HIP (743.895 s, peak 1.30 GB). The HIP configure/build used the private R6 SMT fallback after an earlier guard-only refusal; evidence preserves both the repair controls and final pass. The linked HIP image SHA-256 is `2c944080746d671414d0cf80fa17e60aca3082e7706a26a973751395d7eb2b56`; source feature and debug-trace symbols were present.

This is build evidence only: no native numerical test, dispatch trace, greedy comparison, keep decision, or production promotion occurred. The separately owned native qualification remains active. No READY row was published because the full build had already completed; the earlier calendar-ready draft was suppressed. Full source archive and build images remain in the declared `/mnt/raid0/llm/tmp/codex-ni-g16a-build-prep-20261031` scratch.
