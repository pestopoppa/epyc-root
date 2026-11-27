# MM-5 acceptance V3

V3 runs the unchanged original encoder and server-recorder checks and the V2
feasible-cap geometry and byte-identity checks. It adds two independently
reported checks.

- The pinned brief names `ORCHESTRATOR_VL_MAX_PIXELS`. With no keyword override,
  inspect the actual request produced with the environment variable unset and
  with a positive cap of 784. The unset request must contain the original bytes,
  and the capped request must decode to one 28 by 28 patch. HTTP and serving-call
  recording are mocked within the existing network-isolated evaluator.
- An additional robustness probe sends a valid synthetic image with a cap of 1.
  A bounded subprocess must return with clear cap validation or return a valid
  image satisfying the positive grid and cap. The latter is impossible on a
  28-pixel grid at this cap. This check uses an eight-second child deadline and
  is reported separately from the original feasible-cap question.

The original and V2 checker bytes, source artifacts and results retain their
own hashes. V3 does not reclassify an earlier scoped pass or change the task
brief. Owner assessments record all three check outcomes and retain references
to earlier grades for the exact same patch.
