# 2026-11-17 autokernel

## C13 fold recorded (operator-approved 2026-11-17)

Champion candidate C13 = `bda43aa17c11b671e0e203e7eb7bf4f1303bc273` (branch `llama.cpp-experimental-c12-lb49-sinks-20261117` = C12 `457d5fc52` + 4 LB4.9 sinks commits; default-off, compiled out when GGML_IQK_FLASH_ATTENTION=OFF as in the C12 recipe). Evidence: ak-lb49-sinks-gate-c12-20261117 PASS (80 cases, max NMSE 1.75e-9, mutant red on all 4 routes); lb49-sinks-identity-c12-20261117 PASS (default-off greedy identical).

Records: champion headline now C13 (C12 predecessor, C10 last promoted); AKX-ALL-LB4.9 ticked in autokernel-akx-program.md (AKX-ALL-LB4 left open, it names the iqk FA fold decision); manifest row V11-143. Open fold work now rebases on C13. No compiles or inference run.
