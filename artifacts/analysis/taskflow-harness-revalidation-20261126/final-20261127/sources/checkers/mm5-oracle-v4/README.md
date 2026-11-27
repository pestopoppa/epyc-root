# MM-5 acceptance V4

V4 runs the original encoder and recorder checks and V2's feasible-cap
geometry and byte-identity checks. It retains V3's two additional checks and
corrects the timing of the environment check.

- With the constructor keyword omitted, start a fresh process for each
  environment setting. Set the variable before candidate imports. The unset
  process must send the original image bytes. The process started with
  `ORCHESTRATOR_VL_MAX_PIXELS=784` must send one 28 by 28 patch. Both requests
  exercise the actual server analyzer path against a mocked HTTP response.
- A separate child tests cap 1 on a valid image. It must return within eight
  seconds with clear cap validation or with an image that satisfies the
  positive patch grid and the cap. Those dimensions are impossible for cap
  1. This robustness result remains distinct from feasible-cap acceptance.

Controls cover constructor-time and startup-time environment reads, an
ignored environment cap, an infeasible-cap stall and the untouched baseline.
The startup-time control also records V3's false rejection. Existing oracle
sources and grades are preserved. The same reviewed candidate bytes are
required for all versions.
