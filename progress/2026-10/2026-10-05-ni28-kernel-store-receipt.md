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
was run using an immutable checkout of `79622da`; no host unit-test suite, build, inference
or reload was run. The original producer command exited 0 and recorded seven
linkage checks (CPU launch; GPU launch and ambient; STT launch and ambient; TTS
launch and ambient), each with exit 0 and zero non-OK libraries. The native
reader independently returned valid with no diagnostics. The receipt records
only dependency verification; it does not establish inference, residency,
performance, or a new `ClaimTuple`.

The unmodified receipt is under
`/mnt/raid0/llm/artifacts/ni28-store-capture-20261005.eQEysE/receipts/20261005T130426Z-12e23f9cdff4/`.
Native receipt seal SHA-256 is
`6ee3b6f98e040cc2608381e823aab08ed3dd882a803109435c4673cc04550053`, capture
SHA-256 is
`ff810a42d6bdc6f7c523812446b7db8b954fe8ae6f1399e836741d678805b07f`, and
request SHA-256 is
`9e8ff12a87c5272488576ec9fde0bd1da30a5de29f819b4d8aa9466e6033d49f`. The full
original artifact archive remains unchanged under
`/mnt/raid0/llm/artifacts/ni28-store-capture-20261005.eQEysE/`.

The SHA-256 of the complete original receipt file is `976dd1d36e1ff0ca3d517083ea3e8fe779582923244d3bf00749f4fb9cccf081`. All four captured `link_path` values use `kernels/production/`; the recorded build directories are their canonical resolved targets.
