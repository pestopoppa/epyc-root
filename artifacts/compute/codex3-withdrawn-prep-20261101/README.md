# Prep-only withdrawal handling

The backlog generator already honors `ready/<id>.withdrawn` for manifests, but previously rediscovered a withdrawn ID through `inference_prep`. The fix applies the same exact-ID check to prep entries. Regression controls cover prep-only rows, rows with both sources, unrelated IDs, and piloted handoffs; 12 coordination tests passed.

Five historical codex3 HIL15b continuation IDs have withdrawal markers. Their original unit 05–20 collection is exhausted: 44 known outcomes, four retained UNKNOWN, and no unexposed slots. Original finalization is on main at `b63d061edff7b82182083545dcf4fdd085f55a94`; this does not claim full 60-slot quality or a verdict for unknown cases. The separately owned scientific-v2 cohort is unchanged. [belief: cc]

This source commit does not replace or restart the already-running backlog generator; its installed process must load the updated source through its normal lifecycle.
