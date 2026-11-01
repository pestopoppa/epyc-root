# Versioned keeper and guard deployment review

This patch is an initial v2 installation candidate combining the host/GPU qualifier with the separately source-pinned Parakeet and Unified speech scopes. Unified qualification reports its observed c1r0 request; the production recipe remains six contexts. Its fallback names the version router when WS58_QUAL_GATE is absent.

The baseline keeper SHA-256 is a8fc18c67f08fed08c1f74e629083d55cbcd1b9560b21d3029e0e9e0f7b4e5a7; the guard SHA-256 is 2e40f0cf5e93e91c1a55f2d3a22e0e08a209555cdb06c90181764f7546978908. Recheck both before any installation. The deployment test applies to copies, checks the helper bytes against the repository source, verifies v1 and the selector remain unchanged, checks fallback behavior, and runs shell syntax checks.

No live deployment or qualification is claimed. Stage versioned helpers without changing v1; switch the keeper and guard together at the keeper owner's writer boundary. The running keeper has no hot reload. If any v2 receipt has already been issued, retain its exact helper version and design a new versioned transition rather than overwriting it. Do not change the watchdog selector while the old keeper lives.
