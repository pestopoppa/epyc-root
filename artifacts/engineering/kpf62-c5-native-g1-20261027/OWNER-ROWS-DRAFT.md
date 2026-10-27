# KPF-62.2 proposed owner jobs — NOT READY / NOT ARMED

Both entries require reviewed source, an official source-PF receipt and sealed dependencies, passing resource-monitor fixtures, live owner admission and separately held build-role grants. No poller PID or grant exists for these entries. Disk floor is 150 GiB free, aggregate sampled RSS cap 24 GiB; the owner must select one CPU quarter and grant duration based on the actual row validator. No GPU device is booked by build or CPU capture.

- `kpf62-native-g1-build-20261027`: `bash /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-c5-api-port/owner-build.sh`; assemble full C5 source, CPU and gfx90a HIP house-flag builds, CPU/HIP linkage verification, build receipt. No model. Duration unmeasured; book after owner reviews actual work and capacity.
- `kpf62-native-g1-capture-20261027`: `bash /mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-c5-api-port/owner-capture.sh`; requires matching reviewed build receipt; generate tiny qwen3/qwen35, native G1 position capture plus refusal controls, finalize via ROOT 297b166 reader and shared grader. This is inference and runs only under the owner's separate grant.

STOP is currently present. Do not remove it or register either row until source, monitor and PF gates have passed. Champion-owner folding, production adoption and benchmark claims are separate.
