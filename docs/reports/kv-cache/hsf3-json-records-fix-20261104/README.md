# HSF-3 valid JSON counter: proposed fix

The patch counts each parsed JSON object before event filtering. Three synthetic controls cover target and non-target objects, malformed and incomplete records, and oversize recovery; two fail against the original source. The patch has not been applied. The lane is not indexed, so a source-bound upstream impact for `progress` and review of its callers are required before applying it. No live census ran in this preparation.
