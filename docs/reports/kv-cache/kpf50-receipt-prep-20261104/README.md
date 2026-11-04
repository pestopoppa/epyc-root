# KPF-50 completion receipt preparation

`receipt.py` is a prospective, standalone producer for the existing no-redraw
receipt shape. It requires an existing start marker and typed outcome,
verified-cleanup, before/after clock and nonempty trace-manifest inputs. It
hashes the supplied evidence and trace files, uses an exclusive staging file
and a no-overwrite hard link, and fsyncs the marker directory. The companion
`window_custody.py` is a reviewable copy of the consumer with an additional
recheck of referenced trace bytes when advancing to the next window.

Eight model-free tests pass for missing or changed proofs, clock ordering,
symlinks, no-overwrite, and consumer revalidation. These checks establish
structural binding of producer assertions, not independent truth of cleanup,
clock alignment, scientific validity, or protection from same-UID concurrent
mutation. The production runner does not yet emit these typed inputs and neither
the producer nor the hardened consumer is integrated into the sealed packet.
No profiling, model run, or readiness claim follows.
