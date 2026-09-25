# AMD AI Lab dashboard publication

This directory is the explicit publication snapshot served by the EPYC dashboard
hub at `/amd-ai-lab/`.

- Source repository: `epyc-web`
- Source commit: `f9055b2` (`Show weight quantization prominently on every model card`)
- Snapshot purpose: reviewable static landing page and benchmark recipe draft
- Data status: six model/hardware workspaces; exploratory KV samples, accepted
  qualification curves, live serving waves and CPU speech sweeps carry their
  own sampling, metric definitions and limitations. Retired models do not appear
  as current model cards. Publication updated 2026-09-25.
- Every card opens on a performance matrix; unmeasured dimensions are explicit.
  Headlines lead with the best located eligible measurements, including drafting
  and MTP, with configuration and metric differences retained in the workspace.
- Each card and opened workspace labels weight quantization separately from its
  acceleration/workload recipe; all six labels were checked against source runs.
