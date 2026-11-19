# KPF-60 model-free native fixture preparation

`adapter-and-test-cmake.patch` applies on experimental base
`8952a0f693fb923918157eb25117641b74766230` and includes the previously prepared
selection/writer-observer/checked-adapter changes, plus explicit refusal of
nonzero SWA settings and mirrored (`other != nullptr`) cache instances. The
original adapter did not contain those checks. Copy `checked_counter.hpp` to
`src/kpf60-checked-counter.hpp` and `test-kpf60-cache-fixture.cpp` to `tests/`
before configuring the experimental build.

The proposed native C++ fixture constructs an in-memory, two-layer CPU F16
cache without model weights, populates eight cells with three shared cells, and
exercises fragmented selected ranges, explicit expected K/V totals, a real
writer byte-length check, refusal of incomplete inventory, overlapping and
empty ranges, SWA, and a mirrored cache. It requests sentinel preservation on
refusal. The writer check compares length only; it does **not** establish byte
identity or independently parse serialized metadata or data.

No build, test binary, model, benchmark or publisher ran. Only patch whitespace
(`git diff --check`) and source inspection were performed. Constructor, cache
fixture, build/link, fixture assertions and real refusal behavior are unproven.
The source-impact report for the earlier writer symbols was LOW/MEDIUM, with
skipped files uncleared; the newly added fixture friendship and constructor
use have not received a separate graph impact analysis. No hybrid fixture,
GPU residency, backend transfer, byte-count measurement or crossover claim
follows. A source-bound build row, native byte-for-byte independent oracle and
full calibration are still needed. Do not promote this test-only patch.
