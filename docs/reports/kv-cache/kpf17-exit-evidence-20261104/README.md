# KPF-17 oracle exit-evidence preparation

The patches and GDB event helper require an observed zero exit of the captured
inferior and reject a continue return while it remains live. Three model-free
tests passed, including actual GDB normal-exit and interrupted-stop controls.
On this host the tested stop event did not expose a signal name; the event and
live-inferior state remain recorded and the interrupted control cannot pass.
This preparation is not integrated into the sealed native packet and does not
establish why the earlier INVALID attempt stopped or any model verdict.
