# Committed-conclusion history repair

Class-A pilot confirmation reached a historical deletion of `multimodal-pipeline.md` at `24b06884f` before the exact later conclusion. A path-limited revision walk includes deletion commits; reading their absent blobs previously aborted anchoring.

The resolver now skips a failed historical blob read only when literal full-tree lookup proves the path absent. Present-path read failures and failed verification still raise; current-ref reads and quote audits retain their strict behavior.

The deletion/reintroduction regression failed before this repair; all 16 focused adapter tests passed afterward (15 carrier tuples, zero violations). No grading rule changes.
