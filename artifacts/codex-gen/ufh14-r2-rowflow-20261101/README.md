# UFH14 r2 rowflow publication

The published same-ID row uses the isolated packet at
`/mnt/raid0/llm/tmp/codex-ufh14-r2-republish-20261101`. The spec points at
per-attempt native result units. The archived patch shows the logical changes
against the old packet; it is not a relocation patch and must not be applied
verbatim to the published packet. The archived launcher, helper, manifest and
spec are the actual published versions.

Dry-run completion is separate from the original production marker. A native
unit requires both request groups, timing bindings, wire digests and cleanup
proof. Publication and offline tests do not establish qualification or a
scientific verdict. The keeper owns qualification.
