# Paired v10-vs-champion serving receipt, 2026-10-04 (raw run dir LOST)

14 paired launches (P = v10 ffc1bac82, C = champion 1bceceb05) on the :8083 DFlash2 argv, ab_probe serving probe.
tg +0.61% [95% CI -0.20, +1.41] (P 40.125 / C 40.369 tok/s), pp -0.21%, identity C==P on every launch.

The raw run directory `/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/receipt-ab/paired-20261004T094057Z/`
(per-launch probe JSONs, server logs, result.json, standing-ab.json, writer-samples.json sha256 be6abd6d...) was deleted
at ~11:37Z by a subagent's `rm -rf receipt-ab/paired-*` dry-run cleanup glob. Not recoverable.

Surviving evidence (this directory): the full run log (every arm's residency/linkage/placement/build_info verification
and ab_probe's RESULT line) and the four loop-memory records written by `production ingest-serving` at 10:34Z, which
carry both arms' per-launch tg/pp samples, protocol and host facts. Their `source.path` now dangles.
