# Owner handoff: exact scratch reclaim

- [x] Stage and sweep the 16 present members of the operator-approved 19-path
  manifest; retain the three absent members as `absent-no-action`. Completed
  2026-10-28 with MAIN mapping review and owner purge timing authorization.
  The observed free-space delta and audit hashes are in
  [the progress record](../../progress/2026-10/2026-10-28-exact-reclaim.md).
  [belief: cc]

The empty isolated trash batch and its mapping, receipt and fsynced move
journal remain as custody evidence. Purge intent/completion pairs are retained
in the safety audit and the cited sweep log. The separate proposed scratch
tooling requires owner review and integration; its ratification draft does not
alter policy. The three duplicate native captures remain under their existing
KEEP because individual relative receipt references have not been remapped.

This is a prepared owner handoff; it does not edit the shared domain indices.
