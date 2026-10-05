# 2026-10-05 — HS-OD-5 image sampling controls

HS-OD-5 source commit `f53f9950bc7911b3e75aa0e1bb5bdbb5f1a563f9` is included in
the published orchestrator main package at `41ab07fcdaf9920d0d51520586fddae460cb50b4`
and passed the sixth off-host validation run. The seven explicit image-sampling
fixtures pass: unsupported non-null sampling controls return the declared 422
before vision dispatch, aliases normalize consistently, and omitted or
explicit-null controls retain their default behavior. Text-request behavior
remains covered by the existing cases.

The aggregate run also had three unrelated runtime-flags expiry failures owned
by a separate repair. They do not overlap the HS-OD-5 route or fixture scope.
No local tests ran in this session. Main owns the canonical checkbox and index.
