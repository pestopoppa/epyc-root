# Dense BF16 8K qualification evidence

The declared row result path `.../lsa-gpu-dense-bf16-8k-20261104/native/RESULT.json` was absent when inspected, despite `rc=0` in the terminal grant record. The row decision is therefore inconclusive: the qualification output does not fill the declared grant-result path.

During the isolated four-core GPU smoke, the full 8204-token development prompt returned the exact gold `92-8-E75FB6` in ten generated tokens. The native evidence capture, mapped HIP DSO, and 19 own-process KFD/VRAM samples are preserved here. `PASS.json` records `job_complete=false` because the completion predicate was evaluated against a separate non-smoke result directory. This is a qualification observation, not proof of a later granted run; no population-quality or speed comparison is claimed. Embedded provenance paths in copied records intentionally remain original.
