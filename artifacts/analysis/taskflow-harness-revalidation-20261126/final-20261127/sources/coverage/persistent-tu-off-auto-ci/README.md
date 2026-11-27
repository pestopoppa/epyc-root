# TU OFF automatic CI recovery

This supplemental branch resumes the exact TU OFF paid correction 2 session
after W66 light ON releases GPU slot 1. It holds the existing callback lock
across both continuations and grading, checks the persistent owner grant and
native process identities, and requires main approval of the exact plan and
runner seal. The launcher does not start either server.

The first prompt quotes the actual V2 candidate import exception and its
traceback. The callback preserves the original cap-two rejection and one
measured paid guidance call. It sends no new expert guidance. TU V3 grades each
scope-verified candidate in a pinned, networkless, read-only container after the
native sandbox closes. The result and raw streams remain in the attempt
directory. An accepted checker result still requires independent source review.

The provider retains its 1800-second wall, 32768-token request cap, tools and
sampling. The separate external watchdog limits each continuation to at most
450 seconds, including nominal cancellation grace, and reserves time for grading
and cleanup within the 900-second active branch. The cumulative transport
ledger starts at 91105 available generated tokens after 28895 charged in three
prior attempts. Unknown native usage is charged conservatively by the
qualified transport. A missing charge receipt stops the branch. A pass,
duplicate failure, unchanged candidate, unavailable diagnostic, owner loss,
or deadline ends the branch without starting another continuation.

Run preparation with `ci_callback.py prepare --seal DIGEST --out PLAN.json`.
Main approves the exact SHA-256 of that plan in a JSON object with
`approved_by`, `runner_seal_sha256`, `plan`, and `plan_sha256`. Run
`ci_callback.py launch --seal DIGEST --approval APPROVAL.json
--approval-sha256 APPROVAL_DIGEST --out runs/auto-01` from the agent host.
Only `launch` reaches the native model.
