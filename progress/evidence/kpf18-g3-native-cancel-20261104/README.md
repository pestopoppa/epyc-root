# KPF-18 G3 cancellation fixture

Three model-free tests exercise the SHA-pinned disabled candidate's `SeedControl` and SSE parser with fake HTTP, slot and log inputs. They cover a same-task cancellation and 32,000-token release witness, rejection of idle without native release, and refusal when another task becomes idle.

Run with `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s progress/evidence/kpf18-g3-native-cancel-20261104 -p test_native_cancel.py`. The test depends on the private candidate under `/mnt/raid0/llm/tmp/kvu/kpf18-integrated-successor-20261104/candidate` and refuses changed transport bytes; it is not a standalone native-run packet. These fake inputs do not establish live cancellation, GPU residency, real task release or full entry readiness. The candidate remains disabled.
