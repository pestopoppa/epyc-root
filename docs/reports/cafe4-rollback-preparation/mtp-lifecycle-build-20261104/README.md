# Real-MTP lifecycle executable build receipt

Scheduled row cafe4-v10-mtp-lifecycle-build-r2-20261104 ended rc0 complete at 2026-11-04T07:18:07Z. Native receipt mode=build binds v10 ffc1bac82, exact CMake patch, candidate and bridge digests, executable/DSO hashes and local llama-common/llama/ggml linkage. The original proof checks the MTP_LIFECYCLE string before writing the receipt. Verdict: PASS for the declared full-build prerequisite only.

The native executable digest is ded82680d1268bd896d69c82d0045704e1fc5c9482e86dfc053ee23253716cbc. Compilation is not model execution. This candidate intentionally returns UNKNOWN after the lifecycle marker until rollback and fault controls are connected; it supplies no native MTP, rollback, fault-sensitivity or performance verdict. Parent CAFE-4 stays open. Scheduled compiled files are additionally hardlinked at /mnt/raid0/llm/tmp/df2/cafe4-lifecycle-compiled-20261104/ before filing permits reaping.
