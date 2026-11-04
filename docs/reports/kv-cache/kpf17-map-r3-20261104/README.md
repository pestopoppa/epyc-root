# KPF-17 map revalidation r3

`kvu-kpf17-map-revalidation-r3-20261104` completed rc 0. The full attempt accepted the complete private five-DSO baseline, passed the synchronization barrier and refused the in-place-mutated `libggml.so` on the second `custody.validate_maps` call. The attempt ID, nonce, context hash, source hash and input seal are retained in `RESULT.json` and `input-seal.json`; the grant end is retained in `grant-ended.txt`.

This tests only detection at the second map capture. It does not establish safety after final revalidation, build identity, native loading or the whole custody chain.
