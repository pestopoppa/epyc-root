**Visual Codebase Atlases: Using Large Language Models to Generate Interactive Architecture Diagrams for Human–AI Collaboration**

Discussing large or complex software systems with a language model is frequently hindered by the limitations of purely textual representations. Linear source listings, file trees, and even static Mermaid diagrams force both the human and the model to reconstruct spatial and data-flow relationships through repeated verbal description. A practical alternative that has emerged is to instruct a model such as Claude to synthesize an interactive visual atlas of an entire codebase. In the resulting artifact the architecture is rendered as a navigable isometric diagram whose components are sized according to real line counts, whose edges carry animated data-flow markers, and whose individual nodes can be expanded to reveal concrete data snippets. The technique converts the codebase itself into a shared spatial workspace that both parties can point at, inspect, and reason over.

### Motivation and Core Technique

The motivating observation is straightforward: human visual cortex is far more efficient at extracting structure from a spatial layout than from walls of prose or undifferentiated code. When an LLM is asked to "turn this repository into a visual diagram," it is therefore asked to perform three complementary tasks:

1. Recover the dominant modules, their responsibilities, and the primary data and control flows that connect them.
2. Map those elements onto a consistent visual grammar (isometric blocks, hatched drafting-paper backgrounds, color-coded domains, animated particles).
3. Emit a self-contained interactive document—most commonly a single HTML file—that supports pan, zoom, hover tooltips, and drill-down inspection of live data values.

Because the model already possesses the repository context (via tools that read files or via an earlier indexing step), the generated atlas is grounded in actual source rather than in an abstract description. Subsequent conversation can then refer to concrete visual elements ("the tall stack labeled R on the right-hand side," "the cluster of moving dots leaving the evaluation games box") instead of re-explaining file paths and call chains.

### Anatomy of a Generated Atlas: The Rivers-of-Empire Evolution Harness

A concrete illustration is the atlas produced for the repository `rivers-of-empire` (Rust rewrite). The diagram presents a turn-based 4X game engine together with an outer evolutionary harness that uses a language model to breed successive generations of strategy programs ("doctrines").

The top status bar records quantitative state at the moment of rendering: four model roles are active, eighteen runs have completed (eight of them in the current era), 582 distinct doctrines have been bred, 41 340 games are on record, and two game engines exist of which one has not yet been switched on.

On the left-hand rail the system is decomposed into three strata:

- **The Evolution Loop** contains the Strategy Archive (P), Parent Selection (S), Doctrine Writers (D and D1), Evaluation Games (R), Rating (H), Recording & Write-up (C and C1), Game-Summarizing Model (S3), and Embedding & Filing (E).
- **Supporting the Loop** comprises the Model-Call Driver (OP), Shared Library (L and L4), Reserve Pool (V), and Progress Measurement (X).
- **The Game** itself consists of the Game Engine (G), Doctrine API (W), and Standalone Export (B).

The central canvas renders these components as an isometric city of rectangular prisms whose heights reflect source size. Edges between prisms carry continuous streams of small animated dots; each dot is a concrete data snippet (a doctrine identifier, a game result vector, an embedding, a rating) that the viewer can hover or click to inspect. The visual grammar therefore simultaneously communicates topology, relative complexity, and live data movement.

The right-hand panel supplies two complementary narratives. Under "What it does" the atlas states that the repository is a turn-based 4X game plus a closed evolutionary loop: a language model writes a strategy program, the program plays sixty games against the existing population, the results become a rating and a written description, and the description decides where the program is filed. The best of what is filed becomes the parent for the next round. The diagram itself is therefore a depiction of a single iterative cycle—archive → select parent → write new doctrine → play → rate → write-up → embed and file → return to archive. Everything to the left of a vertical dividing plane belongs to the game; everything to the right belongs to the harness that evolves strategies for that game. The panel further observes that nearly every hard problem encountered in the system turned out to be a measurement problem (how to score a game that never finished, how to rank programs that never played each other, how to decide whether two strategies are meaningfully different) rather than a pure generation problem. The tall vertical structures in the diagram correspondingly emphasize the measuring components.

Interaction controls allow the viewer to resume the animated flow, advance one step, reset the view, hover any block for a plain-language description, switch to a "How it's built" tab that surfaces the concrete implementation and any currently failing conditions, or "go inside" a structure to examine its internal execution steps.

### Practical Benefits for Human–AI Dialogue

Once such an atlas exists, several recurring friction points in code-centric conversation diminish:

- Orientation cost collapses. Instead of repeatedly listing directories or pasting call stacks, both parties can gesture at the same spatial object.
- Data-flow questions become direct inspections of the animated particles rather than verbal reconstructions.
- Architectural drift is immediately visible: a newly added module that does not yet appear in the atlas, or a data path that has gone silent, stands out against the established layout.
- Measurement and control-flow issues—often the true bottlenecks—are foregrounded by the visual emphasis on rating, recording, and progress-measurement blocks.

The same technique scales to ordinary application codebases. Other practitioners have produced analogous isometric "city" visualizations in which packages become districts, files become buildings, and function call volumes become traffic density, confirming that the approach is not limited to evolutionary or agentic systems.

### Implementation Notes and Emerging Tooling

In practice the generation step is performed by supplying the model with repository access and a carefully worded request that specifies the desired visual style (isometric, hatched drafting paper, animated data dots, dual "what it does / how it's built" panels). The model emits a self-contained HTML artifact that can be opened offline. Subsequent refinements—adding a missing edge, enlarging a block whose line count has grown, or inserting a new drill-down—are themselves conversational edits against the same artifact.

Community response has already produced reusable prompts and skills that systematize the process (for example, "codebase-atlas" skills that enforce consistent visual grammar and interaction affordances). Complementary experiments have pushed the idea further into fully interactive games or three-dimensional cityscapes, yet the essential value remains the creation of a persistent, inspectable spatial model that both human and model can inhabit while discussing the underlying code.

### Conclusion

By converting a codebase into an interactive visual atlas whose moving data particles can be examined in place, language models become far more effective partners for architectural reasoning. The technique does not replace source control, static analysis, or conventional documentation; it supplies a complementary spatial medium in which the structure and the live behavior of a system can be pointed at rather than continually re-described. As repositories grow and as human–AI collaboration becomes the dominant mode of software development, such shared visual workspaces are likely to become a standard intermediate representation—generated, refined, and consulted alongside the code itself.

### References

1. FleetingBits (@fleetingbits). Post describing Claude-generated visual codebase diagrams with inspectable data-flow dots, 13 August 2026, including the rivers-of-empire evolution-harness atlas.
2. Community-derived "codebase-atlas" skill prompts and HTML generators circulating in response to the original post (August 2026).
3. cmaughan. Draxul repository (GitHub), an independent three-dimensional city-style visualization of a codebase inspired by the same technique.
4. Related experiments turning generated atlases into interactive games or HTML structural dumps (public replies, 14 August 2026).
