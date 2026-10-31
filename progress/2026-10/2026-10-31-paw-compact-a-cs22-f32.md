# PAW compact A and CS22 F32 parity — 2026-10-31

### 2026-10-31 PAW compact A HOST-fix2 diagnostic

`codex3-paw-compact-a-hostfix2-20261031` completed rc0 with 64/64 original compact-arm native case records and eight bundle hashes verified. Exact decoded-output matches after outer whitespace stripping, out of eight per task: 0=5, 1=5, 2=8, 3=6, 7=7, 8=7, 9=6 and 10=4 (48/64). SDK finish reasons remain UNKNOWN for all cases. This is descriptive compact-arm evidence only; the standard A continuation's failed final source check remains separate, so no standard-vs-compact or PAW-3 gate verdict follows. Original private cases and outputs stay in private custody. [Digest-only audit](../../artifacts/compute/codex3-paw-compact-a-cs22-f32-20261031/). [belief: cc]

### 2026-10-31 CS-22.A1 F32 cache parity subtest

`codex3-cs22-a1-native-f32-cpu-20261030` completed rc0. Independent replay rehashed all 160 native stdout/stderr records and their exposure bindings; 20 clips × right-context settings 0, 3, 6 and 13 produced **80/80 identical nonempty native token-ID pairs** for chunk80 versus single input. The predeclared F32 cache-parity subtest passes. This does not close A1: its original silence, soak, Q8 and startup requirements remain open. [Pins and digest-only audit](../../artifacts/compute/codex3-paw-compact-a-cs22-f32-20261031/). [belief: cc]

No scientific checkbox changed for these two diagnostics.
