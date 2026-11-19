# HSF-3 incremental census: inconclusive

The granted `kvu-hsf3-incremental-20261104` row exited rc=1 and produced no native RESULT.json. The end receipt is retained in `grant.ended`. This does not establish appended-record counts or a gap distribution.

A static diagnosis found that the sealed prior result contains a 69,820,239-byte progress frontier, exceeding the original census script's 67,108,864-byte per-file cap. The present input inventory contains 124 progress JSONL files, with a maximum size of 69,820,239 bytes; the reader refuses any file above its cap. The prior contains 124 distinct progress frontier seals. No captured traceback establishes it as the actual exit cause.
