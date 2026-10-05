# NI28 kernel-store dependency receipt

The reviewed NI28 candidate adds opt-in, immutable dependency receipts around
`verify_kernel_store.sh`. The ordinary verifier invocation remains at the
legacy launch boundary; the receipt path retains request inputs, source
readsets, child linkage records and a sealed validation receipt.

Candidate source commit `79c175ddae66d45231245f280d44100af6999425` was corrected
for synthetic fixture cleanup/counting in
`79622da80d8d4fa5e49181da2b2be8bf371f95a6`. Its corrected candidate CI run
(`37307888066`, after initial run `37306232520` failed on fixture issues) passed
the selected native fixture module: 12 executed, 12
passed, zero failures/errors/skips. The original JUnit declares 12 tests and
contains 12 testcase nodes. CI receipt `560d460ab573b3d339b52b6997226220a79ff94532389955f50f8ce3883ea88c`
validated with `collected=12`, `executed=12`, `passed=12`, and no skips. The
unaltered request, source readset blobs, receipt, JUnit, command log and
validation log are retained under
`/mnt/raid0/llm/tmp/ni28-ci-run-37307888066/`.

This is synthetic off-host validation only. It does not establish the current
production kernel-store state. A separate bounded read-only production capture
has been prepared for main review using an immutable checkout of `79622da`; no
production store capture, host test, build, inference or reload has run.
