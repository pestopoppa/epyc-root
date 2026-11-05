# Typed snapshot decoder qualification

`kpf131-typed-decoder-qual-20261105` was published after its four-CPU smoke completed rc0. The first smoke stopped when the child heap grew; the corrected custody predicate compares executable and exact file-backed mappings and their hashes, retaining raw maps while allowing anonymous heap growth. Eight synthetic cases include distinct boolean and negative sequence-ID refusals. Full qualification remains pending.

This row uses source-shaped inputs only. It cannot establish compiled ABI, native memory layout, request binding or a historical-control verdict. The historical source files are sealed in `source.json` and remain in the published scratch packet; the repository copy retains their digests and code rather than duplicating the source checkout.
