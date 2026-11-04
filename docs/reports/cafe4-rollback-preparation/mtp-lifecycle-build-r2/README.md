# CAFE-4 lifecycle build R2

Published `cafe4-v10-mtp-lifecycle-build-r2-20261104` after its four-CPU smoke passed. The first-progress predicate validates this run's freshly compiled lifecycle object, source identity, object digest and marker. The executable candidate introduces the real MTP lifecycle through a target verify batch and always returns UNKNOWN pending rollback and fault controls.

This is a build-only qualification. Its full build, native model execution, rollback and fault sensitivity are not established by smoke. The copied spec and scripts preserve the published task-scratch paths for reconstruction and review; runtime remains subject to keeper admission.
