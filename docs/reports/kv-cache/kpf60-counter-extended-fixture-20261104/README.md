# KPF-60 checked arithmetic extended fixture

This standalone fixture targets the unchanged arithmetic header SHA-256
`a31412f8ae2a875a2a99fc399c24d8c0b84d6208ec0cba9cfe6a2e5e94d0c447`.
It adds explicit missing, duplicate and incorrect inventories; disjoint K/V
ranges; metadata and serialized-total overflow; offset addition overflow;
cross-stream subtotal overflow; invalid bounds and F16 row geometry; and
sticky refusal with all four output fields checked for sentinel preservation.
`NDEBUG` is refused because the fixture uses assertions.

This is uncompiled and unrun source: no test pass, model, native cache,
writer parity, GPU or byte-count result follows. The arithmetic helper still
depends on independently validated tensor, geometry and selected-range
inventories. Full system-header/toolchain reproducibility and native CPU/HIP
calibration are outside this fixture.
