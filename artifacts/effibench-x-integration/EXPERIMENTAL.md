# Experimental wrapper status

`run_python.py` is preparation, not a validated model-arm execution protocol. Five
synthetic offline tests cover selected fail-closed checks; they do not exercise
the pinned upstream Click stages or the complete 306-item pipeline. The
caller-supplied content manifest establishes consistency with that manifest,
not the provenance of the acceptance-gate dataset. Timing and ranking remain
unvalidated. Do not use this wrapper to claim adoption or decision-grade scores.

Keep dependencies and output directories outside the clean upstream checkout.
An output directory whose final component equals the model name triggers an
upstream layout special case; the wrapper fails closed on that layout. The
GPQA and EffiBench handoff tasks remain open.
