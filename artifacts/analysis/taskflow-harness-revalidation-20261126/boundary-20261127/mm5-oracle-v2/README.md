# MM-5 additive acceptance

The original brief requires raw bytes for an image already within its cap and aspect-preserving resize on the 28-pixel grid when resizing is needed. This version invokes the original sealed `vision_contract._check_encodings` in full, then checks those requirements on additional source-independent fixtures.

The original cap of 784 allows only one patch. The additional 7,840-pixel witnesses allow narrower and wider dimensions after the minimum-side constraint. They require the source orientation as a necessary condition and accept multiple valid rounded resolutions. On ordinary aspect ratios the two rounded axes must admit one common scale. All inputs use feasible caps at or above 784.

The four replay results are control evidence. The owner records final assessments separately. Use the reviewed grade lane for an unchanged saved attempt.

```bash
sha256sum -c SOURCE-CONTROL.sha256
nice -n 19 taskset -c 180-183 /usr/bin/python3 -IB oracle.py "$REVIEWED_GRADE_LANE"
```

The evaluator uses the pinned image and dependencies, read-only mounts, no network, and an inner timeout. It writes no scores into the original attempt. The owner can use the last assertion line as objective feedback without supplying a source-specific repair.
