**Multi-Brain Harness Architecture for Concurrent Event Handling in Agent Orchestrators**

A recurring scalability limit appears when an agent must simultaneously maintain interactive conversation with a human operator and process a continuous stream of background events. Typical examples include periodic polling of continuous-integration status, monitoring pull-request feedback, or reacting to fleet-wide updates. As the number of such loops grows, the single conversational session becomes saturated: the agent spends every turn evaluating events, making triage decisions, and never remains available for direct dialogue. This saturation is especially acute for orchestrator- style systems such as FirstMate, whose primary responsibility is to supervise an entire fleet of subordinate agents.

The solution is a multi-brain harness architecture that grants a single logical agent two parallel sessions of attention. One session remains the primary interactive channel; the second operates continuously in the background, triageing events and selectively merging or escalating them. The design draws an explicit analogy to distributed version control: events are treated as commits that can be merged silently between branches, preserving full history while protecting the interactive branch from constant interruption.

### Problem Formulation

When an agent is tasked with long-running supervisory duties—for instance, “babysitting” a pull request by checking every five minutes for CI failures or human comments—the resulting event stream competes directly with user messages for the agent’s limited turn budget. Under load the interactive session degrades into a pure event handler. Context is not lost in the technical sense, yet the human operator experiences the agent as unresponsive. Prompt-caching efficiency also collapses because every background event forces a new, non-prefix-aligned request.

### Architecture: Parallel Sessions with Selective Merge

The multi-brain design introduces two concurrent sessions inside the same harness process:

- The **main session** is the sole channel visible to the human operator (“the captain”). All ordinary dialogue, high-level decisions, and tool invocations initiated by the user occur here.
- The **supervision (background) session** is an independent conversation that can run on a cheaper model. Its sole responsibility is to receive events emitted by background loops, classify them, and decide whether they warrant interrupting the main session.

Most events are classified as routine. Rather than being discarded, they are merged into the main session’s conversation history in the same manner that a Git commit is merged from a side branch. The merge appends a concise note to the main session’s tail but does not generate a new turn; the note becomes visible only when the main session next responds. Consequently, context is never lost, yet the interactive channel remains free.

Events judged to require immediate human attention—for example, a CI pipeline that has finally turned green after a requested merge, or a flaky test that has been re-run and still fails—trigger an explicit wake of the main session. Conversely, every user and agent utterance (but not tool-call results) that occurs in the main session is mirrored into the supervision session. This bidirectional mirroring ensures that the background brain always possesses the operator’s current intent and the agent’s most recent reasoning when it evaluates an event.

Throughout the merge process both sessions’ prompt prefixes remain intact, so the expensive prefix-caching benefits of modern model APIs continue to apply.

### Operational Timeline

Consider a concrete timeline of a pull-request supervision loop. The main session begins in dialogue with the operator. Independently, the supervision session receives the notification “PR opened, CI running.” Because the event is routine, a silent merge occurs: a short note is appended to the main history, yet the main session continues without an intervening turn. Later the operator issues the instruction “merge when CI green”; that utterance is mirrored into the supervision session so that future triage decisions carry the correct policy.

Subsequent routine events—a worker finishing a fix, a flaky test that is re-run and passes—again produce silent merges. Only when the supervision session observes “CI goes green” does it decide that the condition for the operator’s earlier instruction has been met. At that point the main session is woken, the merged history is presented, and the operator sees the concise summary “merged: your fix is in.” The net effect is that the interactive channel stays continuously available while the background brain absorbs the entire polling load.

### Implementation Considerations

The architecture is most readily realized in harnesses that expose deep session-level customizability. The Pi harness (pidotdev) is currently the only widely used runtime in which the dual-session model, bidirectional message mirroring, and protected prompt caching can be composed without invasive changes. The same pattern can be reproduced in any custom harness that permits multiple concurrent conversation contexts and controlled injection of history notes.

Key engineering invariants include:

- Tool-call results and operational side-effects are deliberately excluded from the bidirectional mirror; only human and agent natural-language utterances cross the boundary.
- Merge operations are append-only and never rewrite earlier history, preserving auditability.
- The supervision session may be bound to a lower-cost model without compromising the quality of the main interactive channel.

### Outcome

With the multi-brain design in place, an orchestrator agent can sustain an arbitrary number of background loops—fleet-wide status watches, periodic CI polls, external webhook listeners—while the primary conversational surface remains responsive. Routine events accumulate as silent merges and surface only when the operator next speaks; exceptional events surface immediately. The result is an agent that remains available for dialogue even while performing continuous, high-volume supervisory work.

### References

1. Kun Chen (@kunchenguid). “Multi-brain agent architecture” announcement and accompanying diagram, X post, 24 August 2026.
2. firstmate project documentation, especially the Pi supervision-branch specification and architecture notes (GitHub: kunchenguid/firstmate).
3. Pi (pidotdev) harness capabilities enabling concurrent sessions, message mirroring, and prefix-cache preservation. 
