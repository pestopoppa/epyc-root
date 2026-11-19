# KVU-19b per-step profiler preparation

`p3batch-clock.patch` adds opt-in HSA clock and monotonic bracket records around
the synchronized measured decode steps of the retained p3batch source. It has
not yet been compiled or run. The HSA and rocprof timestamp domains must be
calibrated before these markers can delimit profiler records; a whole-process
trace alone cannot attribute the measured decode interval. No profiling or
causal result follows from this patch.
