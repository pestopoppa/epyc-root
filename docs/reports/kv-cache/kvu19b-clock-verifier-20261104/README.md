# KVU-19b profiler clock-check preparation

The model-free checker and five fixture tests exercise clock sample ordering,
frequency and offset arithmetic, witness containment and missing-data refusal.
They do not establish actual HSA-to-profiler clock equivalence, process or
device identity, a valid drift bound, or a GPU calibration result. A named GPU
witness and native profiler collection remain necessary.
