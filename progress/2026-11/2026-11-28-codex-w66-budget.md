# C22 decode-aware prefill budget

Completed AP-W66-BUDGET on unchanged C22 A3B Q8_0 + MTP D2. Three paired comparisons used fresh four-slot servers, identical restored prefixes and rendered requests, fixed preservation, first-delta peer triggering and 256 generated tokens for each request. Control was 0/0 and treatment 256 prompt tokens / 900 ms. The second pair reversed order. [Report](../../docs/reports/autopilot-w66-prefill-budget.md)

ON 28 decode fell from 81.595/78.257/68.680 s to 21.097/20.591/19.691 s. Paired reductions of 49.0–60.5 s exceeded the 12.915 s observed same-arm repeat range. OFF 56 TTFT rose by 6.4–12.9 s, at ratios 1.078/1.165/1.149, all within 1.30. Joint elapsed increased by 4.36/12.50/9.46 s, all within the 13.48 s repeat range. No resolved joint-completion gain was measured.

Treatment native p99 was 981.4/988.1/259.9 ms under the declared nearest-rank method, missing 900 ms twice. The earlier 27B percentile convention gives 291.3/270.4/257.5 ms. Native finalization is included in the two large terminal samples. Both methods, sample counts, maximum and supplementary delivered-event gaps are retained. Fixed-length timing supplies no accepted-work result. Prefix preservation and the standalone A3B gate remained outside this comparison, with the gate parked.

Rowflow completed rc=0 at 10:20:21 UTC. Twelve observed owned PIDs were absent, KFD empty, private port closed and GPU utilization zero. Archived data reproduces the numeric summary byte for byte. Independent raw-log checks verified all six visits, cache counts, body hashes, cap/seed behavior and native prompt-row conservation.

Next: RTG-02 owns the latency-policy and natural-completion decision; the standalone gate stays parked.
