# AMD AI Lab dashboard publication

This directory is the explicit publication snapshot served by the EPYC dashboard
hub at `/amd-ai-lab/`.

- Source repository: `epyc-web`
- Source commit: `4602416` (`Add frozen-v10 Qwen3.8-Flash-Next CPU results`)
- Snapshot purpose: reviewable static landing page and benchmark recipe draft
- Data status: seven model/hardware workspaces; exploratory KV samples, accepted
  qualification curves, live serving waves and CPU speech sweeps carry their
  own sampling, metric definitions and limitations. Retired models do not appear
  as current model cards. Publication updated 2026-09-25.
- Every card opens on a performance matrix; unmeasured dimensions are explicit.
  Headlines lead with the best located eligible measurements, including drafting
  and MTP, with configuration and metric differences retained in the workspace.
- Each card and opened workspace labels weight quantization separately from its
  acceleration/workload recipe; all seven labels were checked against source runs.
- Qwen3.8-Flash-Next now has a CPU card with frozen-v10 quality results on the
  served UD-IQ4_XS weights. Its CPU np × context throughput matrix was skipped;
  the post-BIOS predecessor-build speed figure is linked with its different
  binary/weight identity, not presented as a frozen-v10 speed claim.
