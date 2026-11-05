# Group-3 native cancellation order qualification

The retained `native_task_log.canceled_task` checks event presence without order, permitting a release before cancellation or cancellation before task launch. This source-bound isolated candidate requires a unique launch and release with every matching cancellation between them; foreign-task cancellations do not count. Its seven synthetic cases compare old and corrected behavior. It is conservative about ambiguous logs; it does not establish a native cancellation, actual task release, integration, GPU admission, or a verdict. Neither the native candidate nor historical results are changed. Full row and four-CPU smoke are separate outcomes.

The original and corrected witness, physical-trace dependency, tests and completion checker are sealed. The candidate is a proposed source change, not installed.
