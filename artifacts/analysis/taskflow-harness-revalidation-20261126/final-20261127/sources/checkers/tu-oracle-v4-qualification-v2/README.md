# TU evaluator V4 qualification

The original TU brief permits skipping only explicit unshare setup permission
refusals. It separately asks for genuine sentinel denial, a probe report for
directory access, and evidence that the grader directory is unreachable. The
pinned design document distinguishes failed probe execution from OS denial.

V4 keeps every V3 phase, exact JUnit file matching, duplicate checks, and
container limits. It adds four controlled cases covering the concrete failures
found during independent review.

- Invalid namespace arguments must fail instead of being treated as permission
  refusals.
- Mount permission failures must still fail if the real scratch mount target
  happens to contain `unshare`.
- A genuine sentinel ENOENT remains unchanged while the directory probe reports
  an unrelated EROFS or a null errno. Neither outcome supplies genuine directory
  denial evidence. Both cases verify that the injector reached the actual probe
  and kept the original sentinel errno.

The checker runs no model. It does not establish real host isolation. V3 results
and approved inputs remain immutable. Qualification first checks the previously
accepted main function/class controls, then checks narrowly changed witnesses
under V3 and V4. It also reruns the exact saved CPU paid2 and GPU Auto-CI2
candidates to compare their historical V3 pass with the new controlled faults.

Run `python3 -B controls.py` to verify pinned sources and fixture preparation.
The owner must run `python3 -B controls.py --execute` to qualify candidate
execution in the read-only and network-disabled evaluator. Review the results
before approving V4 for grading or using its diagnostics as feedback.

Qualification revision 2 keeps the oracle and checker byte-for-byte from the
first V4 source package. The first null-errno control relaxed the test assertion
alone. The accepted reference helper independently rejected null, so the
mutant still enforced the contract and passed V4. The revised fixture relaxes
the helper only for directory/null and relaxes the corresponding test assertion.
The earlier result remains in the original V4 package. No grader logic changed.
