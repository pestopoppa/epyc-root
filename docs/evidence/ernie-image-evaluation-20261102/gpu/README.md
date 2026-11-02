# ERNIE attention graph trace candidate

This unapplied diagnostic patch targets experimental stable-diffusion.cpp revision `f3a7fe957d1e615d8766084f000dc3fabf8d7775`. It passed `git apply --check` there; its SHA-256 is `0855344f865836348d0d814769bf15a2288c9feab6eb6a569059ca6e91388200`.

The candidate logs which attention graph branch was selected after the backend support check. It is not compiled or run, records graph construction rather than kernel execution, and instruments a shared helper: attribution to ERNIE DiT needs further evidence. A separate experimental build, source and binary identity, request-scoped trace, and in-run GPU residency are needed before interpreting any A/B. No inference, fix or speed claim follows from the patch.
