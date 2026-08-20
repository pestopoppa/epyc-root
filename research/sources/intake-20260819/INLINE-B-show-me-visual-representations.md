**Show Me: Enabling Coding Agents to Converse Through Compact Visual Representations**

The rapid advancement of large language model-based coding agents has produced systems that score higher on benchmarks of intelligence and capability. Yet the day-to-day experience of collaborating with these agents has, in an important respect, degraded. Agents increasingly respond with dense walls of technical prose—jargon-laden explanations that force the human collaborator to expend significant cognitive effort simply to extract the underlying structure of a design, a change, or a control-flow decision. The remedy proposed here is straightforward: instruct the agent to communicate primarily through concise visual and structural artifacts rather than extended natural-language exposition. The resulting interaction is lighter, faster, and better matched to the strengths of human visual processing. This approach has been packaged as an open skill named `show-me`, available for use with any coding agent that supports skill installation.

### The Problem of Unreadable Agents

Contemporary coding agents frequently generate responses that are, for practical purposes, unreadable at a glance. Screenshots and anecdotes circulating among practitioners illustrate the pattern repeatedly. Yishan Wong (former CEO of Reddit) has publicly noted the difficulty of parsing agent output. Mario Zechner, creator of the `pi` tool, has likewise remarked on the opacity of agent explanations. Connor of Replicas and others have echoed the complaint. In response, Dillon Mulroy published a lightweight skill (`/bro`) whose prompt simply instructs the model:

> Restate your last message. Stop using jargon and speak coherently. State it more simply and concisely, like one human talking to another.

The underlying observation is that agents have become more capable on paper while simultaneously becoming less pleasant and less efficient to work with. The distinctive voice, personality, and "soul" that early users valued in models such as Claude appear to have been attenuated by successive rounds of reinforcement learning. Even models that avoid the worst excesses of corporate tone still default to long, jargon-heavy paragraphs that cause the reader's attention to glaze over. A typical recent response—produced multiple times a day in ordinary development sessions—might occupy an entire screen with dense prose describing a proposed refactoring, leaving the essential architectural shape buried.

### Inspiration and Design Principle

The proposed alternative draws directly on Coda Hale's well-known talk on intuition versus attention in infrastructure systems. Hale observes that analytic processing of large volumes of information is effortful, whereas the human visual cortex, shaped by millions of years of evolution, extracts structure from rich visual input with comparatively little conscious effort. Tools should therefore be optimized for the latter channel. Hale's memorable formulation captures the engineering implication:

> Just as an axe must fit the human hand to be useful, software must fit the human mind to be useful.

Applied to coding agents, the principle yields a simple operational rule: when the agent needs to explain a design, a change, or a control-flow decision, it should prefer compact visual or structural sketches over extended prose. The `show-me` skill implements that rule. Once installed (`npx skills add humanlayer/skills --skill show-me`), the agent can be invoked with `/show-me` (or an equivalent natural-language request) and directed at a route, service, feature, pull request, or open question. The skill is already integrated into the HumanLayer environment, where it additionally benefits from native support for inline Mermaid diagrams and HTML fragments.

The same visual vocabulary proves especially valuable during the program-design phase—the stage in which the shape of the code (types, signatures, call stacks, module boundaries) is negotiated before any substantial implementation occurs. Many contemporary workflows skip this phase and move directly to code generation; the result is frequently a larger volume of subsequent revision. The identical techniques also serve post-hoc exploration of large diffs, allowing a reviewer to identify the structural loci that warrant closer inspection.

### Core Visual Techniques

The skill encourages a small repertoire of representations, each chosen for density of information relative to the cognitive load it imposes.

**Component trees.** On the front end, the agent renders a hierarchical tree that retains only the components, state hooks, and module boundaries that matter for the discussion at hand. All incidental implementation detail is omitted. An example shared in December 2025 showed a React component hierarchy reduced to the essential state-management and boundary points, allowing a reader to grasp the data-flow topology in seconds rather than paragraphs.

**Call stacks.** For orchestration, control-flow, or backend-shaped problems, a vertical call-stack diagram—modeled after the classic debugger view—makes the sequence of invocations immediately apparent. Dillon Mulroy popularized a compact textual rendering of this shape; Tanishq later contributed a tool that extracts the same information directly from an abstract-syntax tree, enabling the agent to generate accurate stacks without manual reconstruction.

**Diagrams.** When a chat interface supports inline Mermaid (or an equivalent rendering engine), the agent emits state diagrams or sequence diagrams. These remain the preferred formats because they map cleanly onto the most common reasoning tasks. Occasional "slop" still appears, yet the visual form is almost always easier to scan than the corresponding prose.

**File layouts.** A shallow directory tree annotated with a single line of responsibility per entry answers the dual questions "Where does this live?" and "What is the natural scope of this refactor?" The representation is deliberately minimal; depth is sacrificed for immediate legibility.

**Pseudocode.** Algorithmic or procedural logic is often clearest when expressed as lightly typed pseudocode rather than fully elaborated source. The resulting block is shorter and free of language-specific ceremony.

**Types and signatures.** Before any implementation exists, the agent can surface the essential type definitions and function signatures—the internal "shape" that is too detailed for an architecture document yet still critical for correctness. These declarations serve as a lightweight contract that subsequent code generation must satisfy.

**Diff syntax.** When most of a structure is unchanged, the agent reuses familiar unified-diff notation. A component-tree change, a call-stack modification, a file-layout adjustment, or even a control-flow sketch can each be expressed as a short patch. The eye is drawn immediately to the delta.

**HTML mock-ups and diagrams.** For user-interface prototyping, simple HTML fragments have largely replaced heavier design tools for many teams. The agent can emit self-contained HTML that the developer opens in a browser or, inside HumanLayer, renders inline. The same medium supports explanatory diagrams that mix layout, annotation, and lightweight interaction.

Collectively these forms replace walls of prose with artifacts that the visual system can parse at a glance. The agent is still free to add brief clarifying sentences, but the primary communication channel is structural rather than linguistic.

### Related Work and Extensions

Matt Pocock's `/teach` skill, which generates HTML explainers, provided early inspiration for the HTML-based techniques. Independent practitioners have already begun extending the idea: some wrap every pseudocode block in a language-fenced code region for improved readability; others push the agent further by asking it to re-represent a problem in the form that makes the solution most obvious. Complementary open-source tools such as Scratchpad and Sideshow demonstrate that richer combinations of Markdown, Mermaid, LaTeX, call stacks, and HTML can be composed into persistent visual workspaces.

### Practical Adoption

Installation is a single command. Once present, the skill is invoked either by the slash command `/show-me` or by a natural-language request such as "this is too much content—show me" or "/show-me as an HTML explainer." The agent then selects the most appropriate visual form (or a small combination of forms) for the current topic. Feedback and customizations are welcomed; practitioners are invited to share results with the HumanLayer community.

By aligning the agent's output modality with the strengths of human visual cognition, the `show-me` approach restores a measure of fluency to human–agent collaboration. The technique does not claim to solve every problem of agent reliability or long-horizon planning; it simply removes an unnecessary source of friction that has grown more acute as models have become more capable. In that respect it is a modest but practical step toward tools that truly fit the human mind.

### References

1. Hale, C. "Intuition vs. Attention." Talk on infrastructure systems (YouTube).
2. Wong, Y. Public remarks on agent readability (X post, August 2026).
3. Zechner, M. Commentary on agent opacity (X post, August 2026).
4. Mulroy, D. `/bro` skill for simplified language and call-stack visualizations (X posts, 2026).
5. Tanishq. AST-derived call-stack extraction tool (X post, August 2026).
6. Pocock, M. `/teach` skill generating HTML explainers (X).
7. HumanLayer Skills repository. `show-me` skill: `npx skills add humanlayer/skills --skill show-me`.
8. HumanLayer documentation and program-design guidance (hlyr.dev).
