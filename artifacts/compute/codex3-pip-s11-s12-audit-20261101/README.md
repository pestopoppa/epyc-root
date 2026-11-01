# PIP-02 ODL s11/s12 source and recovery audit

The original s11 and s12 runs were filed as incomplete/failed. The retained per-page audit verifies 25 completed predictions in each shard, including page 285 and page 310, using separately filed source-bound first-client recoveries. The original partial and failure receipts remain historical evidence; this is not a TEDS or parser-quality verdict.

At the withdrawal boundary, both original IDs had filed receipts and terminal records, no live grant, no top-level READY manifest and no matching live process. Their old `ready/armed` records were retained unchanged as historical evidence. Exact-ID withdrawal markers prevent these historical runs from being rediscovered by the updated backlog generator; the existing generator process must load that update through its normal lifecycle. No page was rerun.

`verify.py` recomputes the 166 locally referenced source, prediction, result, log and filing hashes; `VERIFY.log` is the validation at filing time. The evidence paths are local and may not remain available indefinitely. This audit does not assert that all other PIP-02 shards or the full cohort are complete. [belief: cc]
