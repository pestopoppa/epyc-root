# KVU-19b multi-clock qualification successor

The original publisher smoke stopped in the verifier: both HSA captures reported 1 GHz, which its unsupported 400 MHz upper bound rejected. This isolated successor accepts a positive uint64 HSA frequency; the unchanged offset helper still refuses mismatched frequencies and invalid brackets. Remaining verifier checks, GPU smoke and full qualification have not passed. This observes individual witness points only, not continuous drift or target attribution. Original failure is retained separately.
