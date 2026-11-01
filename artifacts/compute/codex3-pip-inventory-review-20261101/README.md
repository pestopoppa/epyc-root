# PIP-02 exposure-inventory review snapshot

This is a source and regression-test snapshot, not an execution guard or an eligibility authorization. It inventories both padded and unpadded original shard layouts, discovers attempt roots separately, pins the original plan, checks capture/worker-config scope agreement, and retains ambiguous or unverified capture scopes as UNKNOWN. It must be rerun and independently reviewed under the native campaign locks before any page can be selected.

At the 2026-11-01 host observation, the 755-page snapshot contained 2,108 captures across 27 attempt roots, 690 pages protected by unverified capture scope, and 65 pages with no observed start. The snapshot SHA-256 was `51cb9531cb3c20be0a10074a70048514779c40a9d33467d151143c43e1699d53`; this provisional count is not a claim that 65 pages are safe to execute. Historical unsealed partial results are not silently treated as authenticated completion. No inference, grant, or keeper qualification was performed.

`test_inventory.py` covers the targeted scanner; the full scanner differs only in iterating all 151 shards. Fifteen model-free controls passed; see `TEST.log`. The source uses live host paths and the original model/campaign-specific contracts, so its results must not be generalized to another cohort. [belief: cc]
