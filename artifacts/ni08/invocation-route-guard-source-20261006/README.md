# AP61 invocation-log route guard source acceptance — 2026-10-06

MAIN accepts test-only APP source `e17b5e9f69fac549beba06f5d39d0de3662d625f`, published byte-identically at APP main `041ec98abba9c93c9b9cf75c07fa6a20ecdee775` with normal serialized publication. The old five-file list is replaced by a recursive scan of every current route source. Both method and direct-name `get_invocation_log()` calls are prohibited; comments/strings and request-local `repl._invoked_tools` remain allowed. Meaningful positive/negative syntax controls are included.

[Independent MAIN Git/AST review](MAIN-source-review.json) binds all46 current route files, finds zero prohibited calls, and proves the only changed file is `tests/unit/test_invocation_log_request_scope.py` (SHA-256 `bf0435bd43c21b0d3710ead0f52e4a3016d99655779c72619516f3014814eb89`). Manual blast radius LOW: test coverage only. No product source or runtime behavior changes. [Publication](publication.json) verifies exact accepted blob and remote main.

Validation is static source review, AST syntax/census and normal governance hooks; no pytest/import/collection or native fixture capture was performed. This is no runtime/concurrency/telemetry-quality measurement. The bounded syntax guard does not resolve arbitrary aliases, dynamic getattr or dataflow. AP62's separate diagnostic snapshot contract remains open.
