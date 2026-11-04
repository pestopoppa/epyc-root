# KPF-50 cleanup-evidence preparation

The standalone writer uses a child-free single-threaded subreaper, captures
child PID and birth identity, reaps its owned children and requires both an
empty child list and ECHILD before publishing a typed cleanup receipt. Two
model-free subprocess tests passed, including a nested adopted child that
prevents publication while live.

The writer is not integrated into the existing runner. It does not establish
GPU residency, scientific validity, or protection from same-UID races.
