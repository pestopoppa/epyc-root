# Ward 088 oracle evidence

CPU result: all five bounded cases finished (tied, native-unit, random, projected5k, PCA projection); native unit reports zero failures. Random and projected 5k fixtures report exact selected indices, and PCA query/key projections and selected attention outputs report max absolute difference 0 for the recorded cases. The tied unit was completed in qualification and its retained receipt was consumed by the continuation. This is fixture conformance only, with no model quality or timing claim.

HIP result: the 513-key author tie fixture and 27B-shaped synthetic suite passed. The tied and native witnesses report five and 21 overlapping own-process residency samples respectively, rc=0 and the mapped HIP library digest. The tied case was carried from qualification; native-27b ran in the continuation. These are fixture checks, not an inference, performance, or promotion result.

The manifest and ended records are preserved verbatim; direct-run provenance and qualification/continuation split are not represented as independent full pairs. Original receipt files retain their original absolute scratch paths. `SHA256SUMS` binds the copies in this directory so they remain inspectable if the scratch is reclaimed. Model weights and binaries are not copied.
