# Privacy-bounded usage source audit

Accepted2026-10-06: [aggregate](aggregate.json), [independent MAIN recomputation](MAIN-review.json), exact approved [source pins](source/pins.json). Source window2026-08-28T14:52:52.284Z to2026-10-06T19:13:58.282Z. Original immutable result SHA256 `9b55ae0ab357644ca349f070cc32de34993379fc95ad1256ac292a41e71d64a6`, source manifest SHA256 `36f82ac4510578561d2137690ecb2836b3e1f9eefe2b1cd384af15af08e70642`, private projection SHA256 `ec36ab1f4b310818335a0ff147e2e3d899d908d6e9f4b5eba68c7a1771e7f6ef`. Private original custody `/mnt/raid0/llm/tmp/dcp9a-custody-20261006-02` is0700/files0600; no manifest rows, HMAC identities or transcript bodies are published.

The read enumerated1,737JSONLs/2,114,724,330bytes:1,734stable before/after hashes;3moving files and11,362associated rows excluded,0unreadable. Stable allowlisted projection214,334usage rows;0metadata parse failures. Conservative exact-session/UUID/request subset34,412rows after excluding460ambiguous UUID groups and77,378repeated request groups/178,674records, collapsing85identical duplicate extra rows. Cross-session identity semantics remain unknown. This subset is not billing authority or a complete-session/task denominator.

| Descriptive input mix | Stable usage events | Conservative unique-record subset |
| --- | ---: | ---: |
| Cache-read fraction | 96.9609% | 97.7714% |
| Cache-creation fraction | 3.0359% | 2.2276% |
| Uncached input fraction | 0.003154% | 0.001016% |
| All input components/output ratio | 691.0092 | 1195.7190 |

Input denominator is the sum of uncached input, cache-read input and cache-creation input, not the uncached field alone. [Paper§3.1–3.2](https://arxiv.org/html/2607.06906v2) supplies Eq4/Definition1 semantics. No prices or effective-cost estimate are computed. Per-session figures are only a distribution of partial subset input-components-plus-output intensity; they are not complete-session spend or completed-task time. A historical61-transcript cohort is a different cohort and not a checksum target.

**Definition1: not evaluable.** Ordered completed-task quality/time observations under a fixed judge protocol are absent. Coordination share additionally requires native write-time purpose labels (DCP9b/P53); no transcript-content classification or purpose inference is performed. Parent DCP9a remains open for the trajectory component. DCP9A-USAGE and VB-DCP-LOG-USAGE close only this bounded source audit/custody.

The custom stdlib reader byte-scans opaque strings without decoding/materializing bodies and captures only allowlisted scalar identity/time/usage fields. It validates metadata syntax/keys/count types, not every opaque body string's Unicode semantics. Earlier v1/v2 snapshots are excluded, remain private and were not overwritten. MAIN independently read only the allowlisted private projection and source fingerprint manifest to recompute counts, sums, ratios, partial intensity distribution and manifest digests; it did not read raw transcripts. Metadata stays ungraded, with no ClaimTuple reconstruction or new grading ladder.
