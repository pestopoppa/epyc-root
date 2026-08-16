# Invariants

The stable core of this fleet's coordination contract. **This file is the canonical
copy.** Every other surface CITES it and must never restate it — a restated rule is a
copy that will miss the next amendment, which is how the fan-out rule's exceptions came
to exist in one of five places.

No origin stories live here. The incidents that produced these rules are in
`handoffs/active/coordinator-role-failure-modes-and-refactor.md` and
`handoffs/active/session-bus-thin-dispatcher.md`; the mechanical protocol is in
`coordination/session-bus/session_bus.schema.json` and
`coordination/session-bus/BUS_PROTOCOL.md`. Keeping the
narrative out of the instruction path is the point: a rule you must read past three
paragraphs to find is a rule that does not fire at the moment of emission.

1. **Single writer.** Each agent writes only its own outbox, heartbeat and cursor;
   authorship is derived from the path, never asserted.
2. **Never block on the bus.**
3. **The daemon is mechanical-only.** It files defects on mechanically checkable
   violations and never grades work.
4. **Trust boundaries are human-only.** `human_only_paths.yaml` is hash-pinned; refuse on
   a pin mismatch. Never sign.
5. **Claims are ACQUIRED, never observed.** The flock is the fact; observing is TOCTOU.
6. **Reclaim of an interactive session is quiesce-and-drain at a boundary.** Pool workers
   get the D6 salvage-kill exception, and nothing else does.
7. **Full coordinator state reconstructs from bus files alone.**
8. **Compute windows are requested via the bus and granted per policy** (rule 11 as
   amended by D4: ownership is policy authorship at the coordination level, not a
   session).
9. **Never tick another agent's checkbox.**
10. **Never edit `human_only_paths.yaml`.**
11. **Never commit another session's in-flight work.** Salvage of a DEAD pool worker's
    tree is the single exception.
12. **No name-pattern kills.** Owned, self-captured pids only; verify death after killing.
13. **Two-sample persistence before any destructive or escalatory action** taken on a
    claim of absence or idleness.
14. **A gating declaration is mandatory on every queue row.**
15. **The measurement trust boundary is human-amendment-only.**
