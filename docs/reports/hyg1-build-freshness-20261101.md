# HYG-1 shared build freshness closure — 2026-11-01

HYG-1's stale shared `build-cpu` path and its four associated stale build directories were removed under the broader HYG-1b cleanup. Root commit `8e17643f79` records that all five stale directories were deleted; the contemporaneous inventory is retained at `/mnt/raid0/llm/tmp/inf70/agents/hyg/scan_builds_output.txt`.

I checked the five paths named by HYG-1 in the shared tree `/mnt/raid0/llm/llama.cpp-cpu-fusion-20260829` on 2026-11-01. `build-asan`, `build-cpu-prof`, `build-cpu`, `build-merged-20260903`, and `build-o1` are all absent. The tree has separately named `build-b12` and `build-b12-prof` directories; this check makes no new claim about their contents. No `b7-ple` process was present during the check.

The remaining HYG-1 guard is now in `CLAUDE.md`: build paths, mtimes, and invocation history do not prove artifact contents; require a source/build-manifest binding, a fix-specific symbol/setting, or a version uniquely bound to the expected source. This rule was committed as `d5c4bd62837ef8c5f07c879da596b151adc55416`. The change is documentation-only; no build or inference was run for this closure.

Evidence: HYG-1b cleanup commit `8e17643f79` and scan artifact above; current-path check and guard commit `d5c4bd62837ef8c5f07c879da596b151adc55416`. [belief: cc]
