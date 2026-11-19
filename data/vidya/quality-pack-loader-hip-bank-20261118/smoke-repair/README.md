# Architect-general HIP loader bank smoke repair

The original 05:22:36 UTC publisher smoke failed in preflight when the GPU grant supplied CPUs 184–191 and the smoke expected a four-CPU process mask. The repaired capture binds its process to the first four CPUs in its granted affinity before launching the pinned v10 HIP smoke. Full capture still requires the exact eight-CPU profile. Ten v10 runtime and build files had ctime-only drift. The repair checked each original SHA-256 before refreshing the exact stat pin. The four requests and their validators are preserved, and the byte-identical template is pinned at its relocated path.

The owner resubmitted the repaired packet and the publisher queued smoke because the GPU was busy. Native smoke and production admission are pending in this receipt. [Publication disposition](hip-bank-repair-publication.json)

[Original publisher failure](FAIL-1.json) and [original native result](native-result.json) retain the failure bytes. The publisher moved the failure receipt to its superseded directory during resubmission. [Preparation report](hip-bank-prep-report.json)

Check the archived files with `sha256sum -c ARCHIVE.sha256`. To reconstruct the native packet in the scratch path specified by `row.spec.json`, copy the source files named in `SOURCE.sha256`. For each `*.original-bytes.json` envelope, base64-decode `bytes_b64` to the original filename and verify its `sha256`. The envelope for `README.md` contains the packet's original documentation. Check the reconstructed bytes with `sha256sum -c SOURCE.sha256`.
