# JSON Canvas Integration & Plugin Architecture Redesign

**Created**: 2026-02-05
**Completed**: 2026-02-05
**Status**: COMPLETE (Infrastructure layer)
**Priority**: Medium (infrastructure improvement)
**Actual Effort**: ~4 hours

> **NEXT PHASE**: See `canvas-control-plane-architecture.md` for the integration
> of canvas constraints into the orchestration inference pipeline (routing,
> planning, personalization).

## Implementation Summary

All features implemented and tested:
- `src/canvas_export.py` — Export graphs to JSON Canvas
- `src/canvas_import.py` — Import with diff detection and TOON layer
- `src/tool_loader.py` — Plugin architecture with hot-reload
- `src/tools/canvas_tools/__init__.py` — MCP tools
- 5 manifest.json files for existing tool directories
- `src/mcp_server.py` updated with canvas tools and plugin loader
- 80 new tests (all passing), 2741 total tests pass

See `progress/2026-02/2026-02-05.md` Session 27 for details.

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Part A: JSON Canvas Integration](#part-a-json-canvas-integration)
   - [Background](#background)
   - [JSON Canvas Schema Reference](#json-canvas-schema-reference)
   - [Export Implementation](#export-implementation)
   - [Import/Constraint Mapping](#importconstraint-mapping)
   - [TOON Optimization Layer](#toon-optimization-layer)
   - [MCP Tools](#mcp-tools-for-canvas)
   - [REPL Workflow Integration](#repl-workflow-integration)
3. [Part B: Plugin Architecture Redesign](#part-b-plugin-architecture-redesign)
   - [Current State Analysis](#current-state-analysis)
   - [Target Architecture](#target-architecture)
   - [Tool Manifest Schema](#tool-manifest-schema)
   - [Dynamic Loader Implementation](#dynamic-loader-implementation)
   - [Settings System](#settings-system)
   - [Migration Plan](#migration-plan)
4. [Architecture Reference Tables](#architecture-reference-tables)
5. [Implementation Phases](#implementation-phases)
6. [Testing Strategy](#testing-strategy)
7. [Dependencies](#dependencies)
8. [Bibliographical References](#bibliographical-references)
9. [Open Questions](#open-questions)

---

## Executive Summary

This handoff specifies two related infrastructure improvements:

1. **JSON Canvas Integration**: Export reasoning graphs (HypothesisGraph, FailureGraph) to the open JSON Canvas format for visualization in Obsidian and spatial reasoning augmentation.

2. **Plugin Architecture**: Refactor the monolithic MCP server into a plugin-based architecture with manifests, dynamic loading, and per-tool settings—inspired by Obsidian's 2700+ plugin ecosystem.

**Key Benefits**:
- Visual debugging of agent reasoning via Obsidian
- Human-in-the-loop canvas editing for constraint injection
- Hot-reload tools without restarting Claude Code sessions
- Per-tool configuration and versioning
- Isolation (one broken tool doesn't crash everything)

---

## Part A: JSON Canvas Integration

### Background

JSON Canvas is an open specification created by Obsidian for infinite canvas data. Files use `.canvas` extension and are valid JSON.

**Spec URL**: https://jsoncanvas.org/spec/1.0/
**TypeScript types**: https://github.com/obsidianmd/obsidian-api/blob/master/canvas.d.ts

**Why this matters for inference**:
- Current graphs (HypothesisGraph, FailureGraph) are purely relational
- JSON Canvas adds a **spatial dimension** that encodes priority, grouping, and relationships visually
- Agents can "draw" their working memory; humans can edit it
- Spatial arrangement = attention/priority signal for the agent

### JSON Canvas Schema Reference

#### Top-Level Structure

```json
{
  "nodes": [...],
  "edges": [...]
}
```

#### Node Types

| Type | Required Fields | Optional Fields |
|------|-----------------|-----------------|
| `text` | `id`, `type`, `x`, `y`, `width`, `height`, `text` | `color` |
| `file` | `id`, `type`, `x`, `y`, `width`, `height`, `file` | `color`, `subpath` |
| `link` | `id`, `type`, `x`, `y`, `width`, `height`, `url` | `color` |
| `group` | `id`, `type`, `x`, `y`, `width`, `height` | `color`, `label`, `background`, `backgroundStyle` |

**Common node fields**:
- `id`: Unique string identifier
- `x`, `y`: Position in pixels (integers)
- `width`, `height`: Dimensions in pixels (integers)
- `color`: `"1"`-`"6"` (preset colors) or `"#RRGGBB"` (hex)

**Color presets**:
| Code | Color |
|------|-------|
| `"1"` | Red |
| `"2"` | Orange |
| `"3"` | Yellow |
| `"4"` | Green |
| `"5"` | Cyan |
| `"6"` | Purple |

#### Edge Structure

```typescript
interface CanvasEdgeData {
  id: string;                                    // Required
  fromNode: string;                              // Required: source node ID
  toNode: string;                                // Required: target node ID
  fromSide?: "top" | "right" | "bottom" | "left";
  toSide?: "top" | "right" | "bottom" | "left";
  fromEnd?: "none" | "arrow";                    // Default: "none"
  toEnd?: "none" | "arrow";                      // Default: "arrow"
  color?: string;
  label?: string;
}
```

### Export Implementation

Create `src/canvas_export.py`:

```python
#!/usr/bin/env python3
"""Export REPL memory graphs to JSON Canvas format."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Layout constants
GRID_COLS = 5
NODE_WIDTH = 280
NODE_HEIGHT = 120
H_SPACING = 320  # Horizontal spacing between nodes
V_SPACING = 150  # Vertical spacing between rows

# Color mapping
COLOR_HIGH_CONFIDENCE = "4"    # Green
COLOR_MED_CONFIDENCE = "3"     # Yellow
COLOR_LOW_CONFIDENCE = "1"     # Red
COLOR_FAILURE = "1"            # Red
COLOR_SYMPTOM = "2"            # Orange
COLOR_MITIGATION = "4"         # Green
COLOR_EVIDENCE_SUPPORTS = "4"  # Green
COLOR_EVIDENCE_CONTRADICTS = "1"  # Red


@dataclass
class CanvasNode:
    """A node in the canvas."""
    id: str
    type: str  # "text", "file", "link", "group"
    x: int
    y: int
    width: int
    height: int
    color: Optional[str] = None
    text: Optional[str] = None  # For text nodes
    file: Optional[str] = None  # For file nodes
    url: Optional[str] = None   # For link nodes
    label: Optional[str] = None # For group nodes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON Canvas format."""
        d = {
            "id": self.id,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }
        if self.color:
            d["color"] = self.color
        if self.type == "text" and self.text:
            d["text"] = self.text
        if self.type == "file" and self.file:
            d["file"] = self.file
        if self.type == "link" and self.url:
            d["url"] = self.url
        if self.type == "group" and self.label:
            d["label"] = self.label
        return d


@dataclass
class CanvasEdge:
    """An edge in the canvas."""
    id: str
    from_node: str
    to_node: str
    from_side: Optional[str] = None
    to_side: Optional[str] = None
    from_end: Optional[str] = None
    to_end: Optional[str] = None
    color: Optional[str] = None
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON Canvas format."""
        d = {
            "id": self.id,
            "fromNode": self.from_node,
            "toNode": self.to_node,
        }
        if self.from_side:
            d["fromSide"] = self.from_side
        if self.to_side:
            d["toSide"] = self.to_side
        if self.from_end:
            d["fromEnd"] = self.from_end
        if self.to_end:
            d["toEnd"] = self.to_end
        if self.color:
            d["color"] = self.color
        if self.label:
            d["label"] = self.label
        return d


class CanvasBuilder:
    """Builder for JSON Canvas documents."""

    def __init__(self):
        self.nodes: List[CanvasNode] = []
        self.edges: List[CanvasEdge] = []
        self._node_positions: Dict[str, Tuple[int, int]] = {}

    def add_node(self, node: CanvasNode) -> None:
        """Add a node to the canvas."""
        self.nodes.append(node)
        self._node_positions[node.id] = (node.x, node.y)

    def add_edge(self, edge: CanvasEdge) -> None:
        """Add an edge to the canvas."""
        self.edges.append(edge)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON Canvas format."""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, path: Path) -> None:
        """Save to .canvas file."""
        path.write_text(self.to_json())


def confidence_to_color(confidence: float) -> str:
    """Map confidence score to canvas color."""
    if confidence >= 0.7:
        return COLOR_HIGH_CONFIDENCE
    elif confidence >= 0.4:
        return COLOR_MED_CONFIDENCE
    else:
        return COLOR_LOW_CONFIDENCE


def confidence_to_y(confidence: float, base_y: int = 0) -> int:
    """Map confidence to vertical position (higher confidence = higher on canvas)."""
    # Confidence 1.0 -> y = base_y - 400
    # Confidence 0.0 -> y = base_y + 400
    return base_y + int((1.0 - confidence) * 800) - 400


def export_hypothesis_graph(
    hypothesis_graph,  # HypothesisGraph instance
    output_path: Path,
    include_evidence: bool = True,
) -> Path:
    """
    Export HypothesisGraph to JSON Canvas.

    Layout strategy:
    - Hypotheses arranged in grid by confidence (high confidence = top)
    - Evidence nodes connected below their hypotheses
    - Color indicates confidence level

    Args:
        hypothesis_graph: The HypothesisGraph instance
        output_path: Where to save the .canvas file
        include_evidence: Whether to include evidence nodes

    Returns:
        Path to the saved canvas file
    """
    builder = CanvasBuilder()

    # Query all hypotheses
    result = hypothesis_graph.conn.execute("""
        MATCH (h:Hypothesis)
        RETURN h.id, h.claim, h.confidence, h.tested, h.created_at
        ORDER BY h.confidence DESC
    """)
    rows = result.get_as_df()

    # Create hypothesis nodes in a grid
    for i, (_, row) in enumerate(rows.iterrows()):
        col = i % GRID_COLS
        base_row = i // GRID_COLS

        # Vertical position influenced by confidence
        x = col * H_SPACING + 100
        y = confidence_to_y(row["h.confidence"], base_y=base_row * V_SPACING * 3)

        # Format claim for display
        claim = row["h.claim"]
        if "|" in claim:
            action, task = claim.split("|", 1)
            display_text = f"**{action}**\n→ {task}\n\nConfidence: {row['h.confidence']:.2f}"
        else:
            display_text = f"**{claim}**\n\nConfidence: {row['h.confidence']:.2f}"

        if row["h.tested"]:
            display_text += "\n✓ Tested"

        node = CanvasNode(
            id=row["h.id"],
            type="text",
            x=x,
            y=y,
            width=NODE_WIDTH,
            height=NODE_HEIGHT,
            color=confidence_to_color(row["h.confidence"]),
            text=display_text,
        )
        builder.add_node(node)

    # Add evidence if requested
    if include_evidence:
        # Query evidence relationships
        result = hypothesis_graph.conn.execute("""
            MATCH (e:HypothesisEvidence)-[r]->(h:Hypothesis)
            RETURN e.id, e.evidence_type, e.source, h.id as hypothesis_id, TYPE(r) as rel_type
        """)
        evidence_rows = result.get_as_df()

        evidence_positions = {}
        for i, (_, row) in enumerate(evidence_rows.iterrows()):
            # Position evidence below its hypothesis
            hyp_pos = builder._node_positions.get(row["hypothesis_id"])
            if hyp_pos:
                hyp_x, hyp_y = hyp_pos
                # Offset evidence nodes below
                ev_x = hyp_x + (i % 2) * 150 - 75
                ev_y = hyp_y + NODE_HEIGHT + 50

                evidence_id = row["e.id"]
                if evidence_id not in evidence_positions:
                    is_support = row["e.evidence_type"] == "supports"
                    ev_node = CanvasNode(
                        id=evidence_id,
                        type="text",
                        x=ev_x,
                        y=ev_y,
                        width=200,
                        height=60,
                        color=COLOR_EVIDENCE_SUPPORTS if is_support else COLOR_EVIDENCE_CONTRADICTS,
                        text=f"{'✓' if is_support else '✗'} {row['e.evidence_type']}\nSource: {row['e.source'][:30]}...",
                    )
                    builder.add_node(ev_node)
                    evidence_positions[evidence_id] = (ev_x, ev_y)

                # Add edge from evidence to hypothesis
                edge = CanvasEdge(
                    id=f"edge_{evidence_id}_{row['hypothesis_id']}",
                    from_node=evidence_id,
                    to_node=row["hypothesis_id"],
                    from_side="top",
                    to_side="bottom",
                    color=COLOR_EVIDENCE_SUPPORTS if row["e.evidence_type"] == "supports" else COLOR_EVIDENCE_CONTRADICTS,
                    label=row["e.evidence_type"],
                )
                builder.add_edge(edge)

    builder.save(output_path)
    return output_path


def export_failure_graph(
    failure_graph,  # FailureGraph instance
    output_path: Path,
    include_mitigations: bool = True,
) -> Path:
    """
    Export FailureGraph to JSON Canvas.

    Layout strategy:
    - Failure modes in center, arranged by severity (high severity = top)
    - Symptoms to the left, connected to their failures
    - Mitigations to the right, connected to failures they resolved
    - Causal chains (PRECEDED_BY) shown with dashed edges

    Args:
        failure_graph: The FailureGraph instance
        output_path: Where to save the .canvas file
        include_mitigations: Whether to include mitigation nodes

    Returns:
        Path to the saved canvas file
    """
    builder = CanvasBuilder()

    # Query all failure modes
    result = failure_graph.conn.execute("""
        MATCH (f:FailureMode)
        RETURN f.id, f.description, f.severity, f.first_seen, f.last_seen
        ORDER BY f.severity DESC, f.last_seen DESC
    """)
    failures = result.get_as_df()

    # Center column for failures
    CENTER_X = 600
    SYMPTOM_X = 100
    MITIGATION_X = 1100

    # Create failure nodes
    for i, (_, row) in enumerate(failures.iterrows()):
        y = i * V_SPACING + 100

        # Severity affects color intensity
        severity = row["f.severity"]
        if severity >= 4:
            color = "1"  # Red (high severity)
        elif severity >= 3:
            color = "2"  # Orange
        else:
            color = "3"  # Yellow

        desc = row["f.description"]
        if len(desc) > 100:
            desc = desc[:97] + "..."

        node = CanvasNode(
            id=row["f.id"],
            type="text",
            x=CENTER_X,
            y=y,
            width=NODE_WIDTH,
            height=NODE_HEIGHT,
            color=color,
            text=f"**FAILURE** (severity {severity})\n\n{desc}",
        )
        builder.add_node(node)

    # Query symptoms and their relationships
    result = failure_graph.conn.execute("""
        MATCH (f:FailureMode)-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN s.id, s.pattern, s.detection_method, f.id as failure_id
    """)
    symptoms = result.get_as_df()

    symptom_positions = {}
    symptom_idx = 0
    for _, row in symptoms.iterrows():
        symptom_id = row["s.id"]
        if symptom_id not in symptom_positions:
            y = symptom_idx * 100 + 100
            node = CanvasNode(
                id=symptom_id,
                type="text",
                x=SYMPTOM_X,
                y=y,
                width=250,
                height=80,
                color=COLOR_SYMPTOM,
                text=f"**Symptom**\n`{row['s.pattern'][:40]}`\n({row['s.detection_method']})",
            )
            builder.add_node(node)
            symptom_positions[symptom_id] = y
            symptom_idx += 1

        # Edge from symptom to failure
        edge = CanvasEdge(
            id=f"edge_symptom_{symptom_id}_{row['failure_id']}",
            from_node=symptom_id,
            to_node=row["failure_id"],
            from_side="right",
            to_side="left",
            color=COLOR_SYMPTOM,
        )
        builder.add_edge(edge)

    # Query mitigations
    if include_mitigations:
        result = failure_graph.conn.execute("""
            MATCH (f:FailureMode)-[:MITIGATED_BY]->(m:Mitigation)
            RETURN m.id, m.action, m.success_rate, f.id as failure_id
        """)
        mitigations = result.get_as_df()

        mitigation_positions = {}
        mitigation_idx = 0
        for _, row in mitigations.iterrows():
            mitigation_id = row["m.id"]
            if mitigation_id not in mitigation_positions:
                y = mitigation_idx * 100 + 100

                action = row["m.action"]
                if len(action) > 50:
                    action = action[:47] + "..."

                success_rate = row["m.success_rate"]
                if success_rate >= 0.8:
                    color = COLOR_MITIGATION
                elif success_rate >= 0.5:
                    color = "3"  # Yellow
                else:
                    color = "1"  # Red

                node = CanvasNode(
                    id=mitigation_id,
                    type="text",
                    x=MITIGATION_X,
                    y=y,
                    width=280,
                    height=80,
                    color=color,
                    text=f"**Mitigation** ({success_rate:.0%})\n\n{action}",
                )
                builder.add_node(node)
                mitigation_positions[mitigation_id] = y
                mitigation_idx += 1

            # Edge from failure to mitigation
            edge = CanvasEdge(
                id=f"edge_mitigation_{row['failure_id']}_{mitigation_id}",
                from_node=row["failure_id"],
                to_node=mitigation_id,
                from_side="right",
                to_side="left",
                color=COLOR_MITIGATION,
                label=f"{row['m.success_rate']:.0%}",
            )
            builder.add_edge(edge)

    # Query causal chains (PRECEDED_BY)
    result = failure_graph.conn.execute("""
        MATCH (f1:FailureMode)-[:PRECEDED_BY]->(f2:FailureMode)
        RETURN f1.id as from_id, f2.id as to_id
    """)
    chains = result.get_as_df()

    for _, row in chains.iterrows():
        edge = CanvasEdge(
            id=f"edge_chain_{row['from_id']}_{row['to_id']}",
            from_node=row["from_id"],
            to_node=row["to_id"],
            from_side="top",
            to_side="bottom",
            color="6",  # Purple for causal chains
            label="preceded by",
        )
        builder.add_edge(edge)

    builder.save(output_path)
    return output_path


def export_session_context(
    hypothesis_graph,
    failure_graph,
    episodic_store,  # EpisodicStore instance
    output_path: Path,
    recent_memories: int = 10,
) -> Path:
    """
    Export a combined "session context" canvas showing:
    - Recent memories (center)
    - Related hypotheses (top)
    - Related failures to avoid (bottom, grouped)

    This is the "working memory" canvas the agent can use at session start.

    Args:
        hypothesis_graph: HypothesisGraph instance
        failure_graph: FailureGraph instance
        episodic_store: EpisodicStore instance
        output_path: Where to save the .canvas file
        recent_memories: Number of recent memories to include

    Returns:
        Path to the saved canvas file
    """
    builder = CanvasBuilder()

    # Layout constants
    MEMORY_X = 400
    MEMORY_Y = 400
    HYPOTHESIS_Y = 50
    FAILURE_Y = 800

    # Add group for working context
    context_group = CanvasNode(
        id="group_context",
        type="group",
        x=50,
        y=300,
        width=1200,
        height=400,
        label="Current Session Context",
    )
    builder.add_node(context_group)

    # Add group for high-confidence hypotheses
    hyp_group = CanvasNode(
        id="group_hypotheses",
        type="group",
        x=50,
        y=0,
        width=1200,
        height=250,
        color="4",
        label="High-Confidence Strategies (use these)",
    )
    builder.add_node(hyp_group)

    # Add group for failure warnings
    fail_group = CanvasNode(
        id="group_failures",
        type="group",
        x=50,
        y=750,
        width=1200,
        height=300,
        color="1",
        label="Failure Patterns (avoid these)",
    )
    builder.add_node(fail_group)

    # Get recent memories
    # Note: This requires access to EpisodicStore's retrieval methods
    # For now, we'll create placeholder nodes
    # In actual implementation, query: episodic_store.get_recent(limit=recent_memories)

    for i in range(min(recent_memories, 5)):  # Placeholder
        node = CanvasNode(
            id=f"memory_{i}",
            type="text",
            x=MEMORY_X + (i % 3) * H_SPACING,
            y=MEMORY_Y + (i // 3) * V_SPACING,
            width=NODE_WIDTH,
            height=NODE_HEIGHT,
            text=f"[Recent Memory {i+1}]\n\nPlaceholder for episodic memory content",
        )
        builder.add_node(node)

    # Get top hypotheses (high confidence, tested)
    result = hypothesis_graph.conn.execute("""
        MATCH (h:Hypothesis)
        WHERE h.confidence >= 0.7 AND h.tested = true
        RETURN h.id, h.claim, h.confidence
        ORDER BY h.confidence DESC
        LIMIT 5
    """)
    hypotheses = result.get_as_df()

    for i, (_, row) in enumerate(hypotheses.iterrows()):
        claim = row["h.claim"]
        if "|" in claim:
            action, task = claim.split("|", 1)
            text = f"✓ **{action}**\n→ {task}\n({row['h.confidence']:.0%})"
        else:
            text = f"✓ {claim}\n({row['h.confidence']:.0%})"

        node = CanvasNode(
            id=f"hyp_{row['h.id']}",
            type="text",
            x=100 + i * 240,
            y=HYPOTHESIS_Y + 50,
            width=220,
            height=100,
            color=COLOR_HIGH_CONFIDENCE,
            text=text,
        )
        builder.add_node(node)

    # Get recent failures (to avoid)
    result = failure_graph.conn.execute("""
        MATCH (f:FailureMode)
        WHERE f.severity >= 3
        RETURN f.id, f.description, f.severity
        ORDER BY f.last_seen DESC
        LIMIT 5
    """)
    failures = result.get_as_df()

    for i, (_, row) in enumerate(failures.iterrows()):
        desc = row["f.description"]
        if len(desc) > 60:
            desc = desc[:57] + "..."

        node = CanvasNode(
            id=f"fail_{row['f.id']}",
            type="text",
            x=100 + i * 240,
            y=FAILURE_Y + 50,
            width=220,
            height=100,
            color=COLOR_FAILURE,
            text=f"⚠ Severity {row['f.severity']}\n\n{desc}",
        )
        builder.add_node(node)

    builder.save(output_path)
    return output_path
```

### Import/Constraint Mapping

When a user edits a canvas, the agent can import those changes as constraints.

Create `src/canvas_import.py`:

```python
#!/usr/bin/env python3
"""Import JSON Canvas edits as reasoning constraints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CanvasConstraint:
    """A constraint derived from canvas edits."""
    type: str  # "boost", "suppress", "group", "prioritize"
    target_id: str
    strength: float  # 0.0-1.0
    reason: str


@dataclass
class CanvasGroup:
    """A group of nodes (conceptual cluster)."""
    id: str
    label: str
    member_ids: List[str]


def load_canvas(path: Path) -> Dict[str, Any]:
    """Load a JSON Canvas file."""
    return json.loads(path.read_text())


def parse_canvas_constraints(canvas: Dict[str, Any]) -> List[CanvasConstraint]:
    """
    Parse canvas structure into actionable constraints.

    Heuristics:
    - Nodes higher on canvas (smaller Y) = higher priority
    - Nodes grouped together = conceptually related
    - Color changes from default = user emphasis
    - Deleted nodes (compared to previous export) = suppress
    - New text nodes = user annotations/constraints
    """
    constraints = []
    nodes = canvas.get("nodes", [])
    edges = canvas.get("edges", [])

    # Find the vertical center of the canvas
    if nodes:
        y_values = [n.get("y", 0) for n in nodes]
        y_center = sum(y_values) / len(y_values)
    else:
        y_center = 500

    for node in nodes:
        node_id = node.get("id", "")
        node_type = node.get("type", "")
        y = node.get("y", y_center)
        color = node.get("color")

        # Priority based on vertical position
        # Higher on canvas (smaller Y) = boost
        if y < y_center - 200:
            strength = min(1.0, (y_center - y) / 400)
            constraints.append(CanvasConstraint(
                type="boost",
                target_id=node_id,
                strength=strength,
                reason=f"Positioned high on canvas (y={y})",
            ))
        elif y > y_center + 200:
            strength = min(1.0, (y - y_center) / 400)
            constraints.append(CanvasConstraint(
                type="suppress",
                target_id=node_id,
                strength=strength,
                reason=f"Positioned low on canvas (y={y})",
            ))

        # Color-based emphasis
        if color == "1":  # Red
            constraints.append(CanvasConstraint(
                type="suppress",
                target_id=node_id,
                strength=0.8,
                reason="Marked red (warning/avoid)",
            ))
        elif color == "4":  # Green
            constraints.append(CanvasConstraint(
                type="boost",
                target_id=node_id,
                strength=0.8,
                reason="Marked green (approved/preferred)",
            ))

        # User annotations (new text nodes without known IDs)
        if node_type == "text" and not node_id.startswith(("hyp_", "fail_", "memory_")):
            text = node.get("text", "")
            if text:
                constraints.append(CanvasConstraint(
                    type="annotate",
                    target_id=node_id,
                    strength=1.0,
                    reason=f"User annotation: {text[:100]}",
                ))

    return constraints


def find_groups(canvas: Dict[str, Any]) -> List[CanvasGroup]:
    """
    Find groups and their members.

    Groups are important for understanding conceptual clusters.
    """
    groups = []
    nodes = canvas.get("nodes", [])

    group_nodes = [n for n in nodes if n.get("type") == "group"]

    for group in group_nodes:
        gx, gy = group.get("x", 0), group.get("y", 0)
        gw, gh = group.get("width", 0), group.get("height", 0)

        # Find nodes inside this group's bounding box
        members = []
        for node in nodes:
            if node.get("type") == "group":
                continue
            nx, ny = node.get("x", 0), node.get("y", 0)
            nw, nh = node.get("width", 0), node.get("height", 0)

            # Check if node center is inside group
            node_cx = nx + nw / 2
            node_cy = ny + nh / 2

            if (gx <= node_cx <= gx + gw) and (gy <= node_cy <= gy + gh):
                members.append(node.get("id", ""))

        if members:
            groups.append(CanvasGroup(
                id=group.get("id", ""),
                label=group.get("label", "Unnamed Group"),
                member_ids=members,
            ))

    return groups


def apply_constraints_to_hypothesis_graph(
    hypothesis_graph,
    constraints: List[CanvasConstraint],
) -> int:
    """
    Apply canvas constraints to hypothesis graph.

    Returns number of hypotheses modified.
    """
    modified = 0

    for constraint in constraints:
        if constraint.type == "boost":
            # Increase confidence for boosted hypotheses
            result = hypothesis_graph.conn.execute(
                """
                MATCH (h:Hypothesis {id: $id})
                SET h.confidence = h.confidence + $delta * (1.0 - h.confidence)
                RETURN h.id
                """,
                {"id": constraint.target_id, "delta": constraint.strength * 0.2},
            )
            if len(result.get_as_df()) > 0:
                modified += 1

        elif constraint.type == "suppress":
            # Decrease confidence for suppressed hypotheses
            result = hypothesis_graph.conn.execute(
                """
                MATCH (h:Hypothesis {id: $id})
                SET h.confidence = h.confidence - $delta * h.confidence
                RETURN h.id
                """,
                {"id": constraint.target_id, "delta": constraint.strength * 0.2},
            )
            if len(result.get_as_df()) > 0:
                modified += 1

    return modified


def diff_canvases(
    original: Dict[str, Any],
    edited: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compute diff between original export and user-edited version.

    Returns:
        {
            "added_nodes": [...],
            "removed_nodes": [...],
            "moved_nodes": [...],  # (id, dx, dy)
            "color_changes": [...],  # (id, old_color, new_color)
        }
    """
    orig_nodes = {n["id"]: n for n in original.get("nodes", [])}
    edit_nodes = {n["id"]: n for n in edited.get("nodes", [])}

    orig_ids = set(orig_nodes.keys())
    edit_ids = set(edit_nodes.keys())

    diff = {
        "added_nodes": [edit_nodes[id] for id in (edit_ids - orig_ids)],
        "removed_nodes": [orig_nodes[id] for id in (orig_ids - edit_ids)],
        "moved_nodes": [],
        "color_changes": [],
    }

    # Check for moves and color changes
    for id in (orig_ids & edit_ids):
        orig = orig_nodes[id]
        edit = edit_nodes[id]

        dx = edit.get("x", 0) - orig.get("x", 0)
        dy = edit.get("y", 0) - orig.get("y", 0)
        if abs(dx) > 10 or abs(dy) > 10:
            diff["moved_nodes"].append((id, dx, dy))

        if orig.get("color") != edit.get("color"):
            diff["color_changes"].append((id, orig.get("color"), edit.get("color")))

    return diff
```

### TOON Optimization Layer

**Critical Design Decision**: Canvas files on disk MUST remain standard JSON for Obsidian interoperability. However, when loading canvas data into the agent's context window, TOON encoding provides significant token savings.

#### Format Layering Architecture

| Layer | Format | Purpose | Interoperability |
|-------|--------|---------|------------------|
| **Disk** (`.canvas` files) | Standard JSON | Obsidian, third-party tools, human editing | ✅ Full |
| **LLM Context** (agent reads) | TOON-encoded | 55-65% token reduction | N/A (internal) |
| **Export** (agent writes) | Standard JSON | Interoperability preserved | ✅ Full |

#### Why Not Modify the Disk Format?

JSON Canvas was designed for:

| Feature | Standard JSON | TOON-Modified |
|---------|---------------|---------------|
| Obsidian native support | ✅ Works | ❌ Breaks |
| Third-party tools | ✅ Works | ❌ Breaks |
| Human readability | ✅ Editable | ❌ Binary-ish |
| Forward compatibility | ✅ `[key: any]` | ❌ Unknown |
| Git-friendly diffs | ✅ Line-based | ❌ Opaque |

**Conclusion**: TOON is an internal optimization only—never touches disk.

#### Token Savings Analysis

Based on TOON evaluation (`research/TOON_EVALUATION.md`):

| Canvas Size | JSON Tokens | TOON Tokens | Savings |
|-------------|-------------|-------------|---------|
| 5 nodes, 4 edges | ~180 | ~80 | **56%** |
| 10 nodes, 12 edges | ~450 | ~180 | **60%** |
| 25 nodes, 30 edges | ~1100 | ~420 | **62%** |
| 50 nodes, 60 edges | ~2200 | ~800 | **64%** |

**Threshold**: Apply TOON encoding when `len(nodes) >= 5`.

#### Implementation

Add to `src/canvas_import.py`:

```python
def load_canvas_for_llm(
    path: Path,
    use_toon: bool = True,
    toon_threshold: int = 5,
) -> str:
    """
    Load canvas file, optionally TOON-encode for LLM context efficiency.

    IMPORTANT: This is for READING canvases into agent context only.
    The disk format remains standard JSON for Obsidian compatibility.

    Args:
        path: Path to .canvas file
        use_toon: Whether to apply TOON encoding
        toon_threshold: Minimum nodes to trigger TOON (default: 5)

    Returns:
        Canvas content as string (JSON or TOON format)
    """
    canvas = json.loads(path.read_text())
    node_count = len(canvas.get("nodes", []))

    if use_toon and node_count >= toon_threshold:
        try:
            from src.services.toon_encoder import encode_toon
            return encode_toon(canvas)
        except ImportError:
            # TOON not available, fall back to JSON
            pass

    return json.dumps(canvas, separators=(",", ":"))  # Compact JSON


def canvas_to_toon(canvas: Dict[str, Any]) -> str:
    """
    Convert canvas dict to TOON format for LLM context.

    TOON format for canvas:
    ```
    canvas{nodes,edges}:
    nodes[N]{id,type,x,y,w,h,color,text}:
      n1,text,100,200,280,120,4,**Hypothesis**...
      n2,text,400,200,280,120,1,**Failure**...
    edges[M]{id,from,to,color,label}:
      e1,n1,n2,4,supports
    ```

    Returns:
        TOON-formatted string
    """
    lines = ["canvas{nodes,edges}:"]

    nodes = canvas.get("nodes", [])
    if nodes:
        lines.append(f"nodes[{len(nodes)}]{{id,type,x,y,w,h,color,text}}:")
        for n in nodes:
            text = n.get("text", "")[:50].replace("\n", " ")  # Truncate for context
            color = n.get("color", "")
            lines.append(
                f"  {n['id']},{n['type']},{n['x']},{n['y']},"
                f"{n['width']},{n['height']},{color},{text}"
            )

    edges = canvas.get("edges", [])
    if edges:
        lines.append(f"edges[{len(edges)}]{{id,from,to,color,label}}:")
        for e in edges:
            label = e.get("label", "")
            color = e.get("color", "")
            lines.append(
                f"  {e['id']},{e['fromNode']},{e['toNode']},{color},{label}"
            )

    return "\n".join(lines)


def toon_to_canvas(toon_str: str) -> Dict[str, Any]:
    """
    Parse TOON format back to canvas dict.

    Used when agent generates canvas modifications in TOON format
    that need to be written back to disk as standard JSON.

    Args:
        toon_str: TOON-formatted canvas string

    Returns:
        Standard canvas dict for JSON serialization
    """
    canvas = {"nodes": [], "edges": []}

    lines = toon_str.strip().split("\n")
    current_section = None
    headers = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("nodes["):
            current_section = "nodes"
            # Parse header: nodes[N]{id,type,x,y,w,h,color,text}:
            header_match = line.split("{")[1].split("}")[0]
            headers = header_match.split(",")
        elif line.startswith("edges["):
            current_section = "edges"
            header_match = line.split("{")[1].split("}")[0]
            headers = header_match.split(",")
        elif current_section and line.startswith("  "):
            # Data row
            values = line.strip().split(",", len(headers) - 1)
            item = dict(zip(headers, values))

            # Type conversions
            if current_section == "nodes":
                item["x"] = int(item.get("x", 0))
                item["y"] = int(item.get("y", 0))
                item["width"] = int(item.get("w", 280))
                item["height"] = int(item.get("h", 120))
                item.pop("w", None)
                item.pop("h", None)
                if not item.get("color"):
                    item.pop("color", None)

            if current_section == "edges":
                item["fromNode"] = item.pop("from", "")
                item["toNode"] = item.pop("to", "")
                if not item.get("color"):
                    item.pop("color", None)
                if not item.get("label"):
                    item.pop("label", None)

            canvas[current_section].append(item)

    return canvas
```

#### TOON Integration Points

| Function | TOON Usage | Notes |
|----------|------------|-------|
| `load_canvas()` | No | Returns raw JSON dict |
| `load_canvas_for_llm()` | Yes | Returns TOON string for context |
| `parse_canvas_constraints()` | No | Works on dict, not string |
| `export_*_graph()` | No | Always writes standard JSON |
| MCP `import_canvas_edits()` | Optional | Can accept TOON input from agent |

#### Configuration

Add to canvas tools settings (`src/tools/canvas_tools/settings.json`):

```json
{
  "use_toon_encoding": true,
  "toon_node_threshold": 5,
  "toon_text_truncate": 50
}
```

**TOON Settings Reference:**

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `use_toon_encoding` | bool | `true` | Enable TOON encoding when loading canvases into LLM context |
| `toon_node_threshold` | int | `5` | Min nodes to trigger TOON (below this, JSON is compact enough) |
| `toon_text_truncate` | int | `50` | Max chars of node text in TOON; agent can REPL for full content |

**Why truncate?** Hypothesis claims are typically short (`spec_decode|code_gen`). Full failure traces or long descriptions should be fetched on-demand via `_recall()` or direct graph query. This keeps the canvas summary scannable while preserving access to details.

### MCP Tools for Canvas

Add to `src/tools/canvas_tools/__init__.py`:

```python
#!/usr/bin/env python3
"""MCP tools for JSON Canvas operations."""

from __future__ import annotations

import json
from pathlib import Path

# These will be registered by the dynamic loader
# For now, define the functions

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def export_reasoning_canvas(
    graph_type: str = "hypothesis",
    include_evidence: bool = True,
) -> str:
    """
    Export reasoning graph to JSON Canvas format.

    Args:
        graph_type: Which graph to export ("hypothesis", "failure", "session")
        include_evidence: Whether to include evidence/symptom nodes

    Returns:
        Path to the exported canvas file
    """
    from orchestration.repl_memory.hypothesis_graph import HypothesisGraph
    from orchestration.repl_memory.failure_graph import FailureGraph
    from src.canvas_export import (
        export_hypothesis_graph,
        export_failure_graph,
        export_session_context,
    )

    output_dir = PROJECT_ROOT / "logs" / "canvases"
    output_dir.mkdir(exist_ok=True)

    if graph_type == "hypothesis":
        graph = HypothesisGraph()
        output_path = output_dir / "hypothesis_graph.canvas"
        export_hypothesis_graph(graph, output_path, include_evidence)
        return f"Exported hypothesis graph to {output_path}"

    elif graph_type == "failure":
        graph = FailureGraph()
        output_path = output_dir / "failure_graph.canvas"
        export_failure_graph(graph, output_path, include_evidence)
        return f"Exported failure graph to {output_path}"

    elif graph_type == "session":
        hyp_graph = HypothesisGraph()
        fail_graph = FailureGraph()
        output_path = output_dir / "session_context.canvas"
        # Note: EpisodicStore would need to be initialized here
        export_session_context(hyp_graph, fail_graph, None, output_path)
        return f"Exported session context to {output_path}"

    else:
        return f"Unknown graph type: {graph_type}. Use 'hypothesis', 'failure', or 'session'."


def import_canvas_edits(canvas_path: str) -> str:
    """
    Import user edits from a canvas file as reasoning constraints.

    Args:
        canvas_path: Path to the edited .canvas file

    Returns:
        Summary of applied constraints
    """
    from orchestration.repl_memory.hypothesis_graph import HypothesisGraph
    from src.canvas_import import (
        load_canvas,
        parse_canvas_constraints,
        find_groups,
        apply_constraints_to_hypothesis_graph,
    )

    path = Path(canvas_path)
    if not path.exists():
        return f"Canvas file not found: {canvas_path}"

    canvas = load_canvas(path)
    constraints = parse_canvas_constraints(canvas)
    groups = find_groups(canvas)

    # Apply constraints
    graph = HypothesisGraph()
    modified = apply_constraints_to_hypothesis_graph(graph, constraints)

    lines = [
        f"Imported canvas from {canvas_path}",
        f"Found {len(constraints)} constraints",
        f"Found {len(groups)} groups",
        f"Modified {modified} hypotheses",
        "",
        "Constraints applied:",
    ]

    for c in constraints[:10]:  # Show first 10
        lines.append(f"  - {c.type} {c.target_id}: {c.reason}")

    if len(constraints) > 10:
        lines.append(f"  ... and {len(constraints) - 10} more")

    return "\n".join(lines)


def list_canvases() -> str:
    """
    List available canvas files.

    Returns:
        List of canvas files with modification times
    """
    canvas_dir = PROJECT_ROOT / "logs" / "canvases"
    if not canvas_dir.exists():
        return "No canvas directory found. Export a canvas first."

    files = list(canvas_dir.glob("*.canvas"))
    if not files:
        return "No canvas files found."

    lines = ["Available canvases:"]
    for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
        mtime = f.stat().st_mtime
        from datetime import datetime
        mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        size = f.stat().st_size
        lines.append(f"  {f.name} ({size} bytes, {mtime_str})")

    return "\n".join(lines)
```

### REPL Workflow Integration

**Session Start Workflow**:

```
1. Agent starts new session
2. MCP tool `export_reasoning_canvas(graph_type="session")` is called
3. Canvas saved to `logs/canvases/session_context.canvas`
4. User can open in Obsidian to view/edit
5. User makes edits (moves nodes, adds annotations, changes colors)
6. Agent calls `import_canvas_edits("logs/canvases/session_context.canvas")`
7. Constraints applied to HypothesisGraph
8. Agent proceeds with adjusted confidence scores
```

**Continuous Use**:

```python
# At session start, in session_init.py or similar
def initialize_session_context():
    """Export current reasoning state for user review."""
    from src.tools.canvas_tools import export_reasoning_canvas

    # Export session context
    result = export_reasoning_canvas(graph_type="session")
    print(f"Session context exported: {result}")
    print("Edit in Obsidian and call import_canvas_edits() to apply changes.")
```

---

## Part B: Plugin Architecture Redesign

### Current State Analysis

**Current structure** (`src/mcp_server.py`):
- Single file with all tools defined inline
- 4 tools: `lookup_model`, `list_roles`, `server_status`, `query_benchmarks`
- No configuration, no versioning, no hot reload
- Uses FastMCP with `@mcp.tool()` decorators

**Pain points**:
1. Adding tools requires editing `mcp_server.py` and restarting
2. No per-tool settings
3. No version constraints
4. If one tool crashes, entire server fails
5. No discoverability/documentation beyond docstrings

### Target Architecture

```
src/
├── mcp_server.py              # Core loader only (~100 lines)
├── tool_loader.py             # Dynamic tool loading logic
├── tools/
│   ├── __init__.py
│   ├── registry_tools/
│   │   ├── manifest.json
│   │   ├── __init__.py        # lookup_model, list_roles
│   │   └── settings.json      # Default settings
│   ├── benchmark_tools/
│   │   ├── manifest.json
│   │   ├── __init__.py        # query_benchmarks, compare_results
│   │   └── settings.json
│   ├── server_tools/
│   │   ├── manifest.json
│   │   ├── __init__.py        # server_status, start_server, stop_server
│   │   └── settings.json
│   ├── memory_tools/
│   │   ├── manifest.json
│   │   ├── __init__.py        # query_memories, get_hypothesis_confidence
│   │   └── settings.json
│   └── canvas_tools/          # NEW
│       ├── manifest.json
│       ├── __init__.py
│       └── settings.json
└── tool_settings/             # User overrides (gitignored)
    └── registry_tools.json    # User settings override
```

### Tool Manifest Schema

Create `src/tool_manifest.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MCP Tool Plugin Manifest",
  "type": "object",
  "required": ["id", "name", "version", "tools"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_-]*$",
      "description": "Unique plugin identifier (lowercase, no spaces)"
    },
    "name": {
      "type": "string",
      "description": "Human-readable plugin name"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Semantic version (e.g., '1.0.0')"
    },
    "description": {
      "type": "string",
      "description": "Brief description of plugin functionality"
    },
    "author": {
      "type": "string"
    },
    "minOrchestratorVersion": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "Minimum orchestrator version required"
    },
    "tools": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of tool function names to register"
    },
    "dependencies": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Other plugin IDs this plugin depends on"
    },
    "settings": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["type", "default", "description"],
        "properties": {
          "type": {
            "enum": ["string", "boolean", "integer", "number", "array"]
          },
          "default": {},
          "description": {
            "type": "string"
          },
          "enum": {
            "type": "array"
          },
          "min": {
            "type": "number"
          },
          "max": {
            "type": "number"
          }
        }
      },
      "description": "Configurable settings for this plugin"
    }
  }
}
```

**Example manifest** (`src/tools/registry_tools/manifest.json`):

```json
{
  "id": "registry-tools",
  "name": "Registry Introspection Tools",
  "version": "1.0.0",
  "description": "Query model configurations and orchestrator roles",
  "author": "PACE Team",
  "minOrchestratorVersion": "0.1.0",
  "tools": ["lookup_model", "list_roles"],
  "dependencies": [],
  "settings": {
    "validate_paths": {
      "type": "boolean",
      "default": false,
      "description": "Validate that model paths exist on disk"
    },
    "cache_registry": {
      "type": "boolean",
      "default": true,
      "description": "Cache registry data for faster lookups"
    },
    "cache_ttl_seconds": {
      "type": "integer",
      "default": 300,
      "min": 0,
      "max": 3600,
      "description": "Cache time-to-live in seconds"
    }
  }
}
```

### Dynamic Loader Implementation

Create `src/tool_loader.py`:

```python
#!/usr/bin/env python3
"""Dynamic tool plugin loader for MCP server."""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

ORCHESTRATOR_VERSION = "0.1.0"  # Current orchestrator version


@dataclass
class ToolManifest:
    """Parsed tool plugin manifest."""
    id: str
    name: str
    version: str
    description: str
    tools: List[str]
    min_orchestrator_version: str = "0.0.0"
    dependencies: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)
    author: str = ""


@dataclass
class LoadedPlugin:
    """A loaded plugin with its tools and settings."""
    manifest: ToolManifest
    module: Any
    tools: Dict[str, Callable]
    settings: Dict[str, Any]
    path: Path


def parse_version(version: str) -> tuple:
    """Parse semver string to tuple for comparison."""
    try:
        parts = version.split(".")
        return tuple(int(p) for p in parts[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def version_compatible(required: str, current: str = ORCHESTRATOR_VERSION) -> bool:
    """Check if current version satisfies minimum requirement."""
    return parse_version(current) >= parse_version(required)


def load_manifest(manifest_path: Path) -> Optional[ToolManifest]:
    """Load and validate a tool manifest."""
    try:
        data = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load manifest %s: %s", manifest_path, e)
        return None

    required_fields = ["id", "name", "version", "tools"]
    for field in required_fields:
        if field not in data:
            logger.warning("Manifest %s missing required field: %s", manifest_path, field)
            return None

    return ToolManifest(
        id=data["id"],
        name=data["name"],
        version=data["version"],
        description=data.get("description", ""),
        tools=data["tools"],
        min_orchestrator_version=data.get("minOrchestratorVersion", "0.0.0"),
        dependencies=data.get("dependencies", []),
        settings=data.get("settings", {}),
        author=data.get("author", ""),
    )


def load_settings(plugin_path: Path, manifest: ToolManifest, user_settings_dir: Path) -> Dict[str, Any]:
    """
    Load settings for a plugin.

    Priority (highest to lowest):
    1. User settings override (tool_settings/{plugin_id}.json)
    2. Plugin default settings (tools/{plugin}/settings.json)
    3. Manifest defaults
    """
    settings = {}

    # Start with manifest defaults
    for key, spec in manifest.settings.items():
        settings[key] = spec.get("default")

    # Load plugin default settings file
    plugin_settings_file = plugin_path / "settings.json"
    if plugin_settings_file.exists():
        try:
            plugin_defaults = json.loads(plugin_settings_file.read_text())
            settings.update(plugin_defaults)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load plugin settings %s: %s", plugin_settings_file, e)

    # Load user overrides
    user_settings_file = user_settings_dir / f"{manifest.id}.json"
    if user_settings_file.exists():
        try:
            user_overrides = json.loads(user_settings_file.read_text())
            settings.update(user_overrides)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load user settings %s: %s", user_settings_file, e)

    return settings


class ToolPluginLoader:
    """
    Loads tool plugins from a directory structure.

    Usage:
        loader = ToolPluginLoader(tools_dir, user_settings_dir)
        plugins = loader.load_all()

        for plugin in plugins:
            for name, fn in plugin.tools.items():
                mcp.tool()(fn)  # Register with FastMCP
    """

    def __init__(
        self,
        tools_dir: Path,
        user_settings_dir: Optional[Path] = None,
    ):
        self.tools_dir = Path(tools_dir)
        self.user_settings_dir = Path(user_settings_dir) if user_settings_dir else self.tools_dir.parent / "tool_settings"
        self.loaded_plugins: Dict[str, LoadedPlugin] = {}

    def discover_plugins(self) -> List[Path]:
        """Find all plugin directories containing manifest.json."""
        plugins = []
        if not self.tools_dir.exists():
            logger.warning("Tools directory does not exist: %s", self.tools_dir)
            return plugins

        for child in self.tools_dir.iterdir():
            if child.is_dir():
                manifest_path = child / "manifest.json"
                if manifest_path.exists():
                    plugins.append(child)

        return plugins

    def load_plugin(self, plugin_path: Path) -> Optional[LoadedPlugin]:
        """Load a single plugin."""
        manifest_path = plugin_path / "manifest.json"
        manifest = load_manifest(manifest_path)

        if not manifest:
            return None

        # Version check
        if not version_compatible(manifest.min_orchestrator_version):
            logger.warning(
                "Plugin %s requires orchestrator %s, have %s - skipping",
                manifest.id,
                manifest.min_orchestrator_version,
                ORCHESTRATOR_VERSION,
            )
            return None

        # Dependency check
        for dep in manifest.dependencies:
            if dep not in self.loaded_plugins:
                logger.warning(
                    "Plugin %s depends on %s which is not loaded - skipping",
                    manifest.id,
                    dep,
                )
                return None

        # Load settings
        settings = load_settings(plugin_path, manifest, self.user_settings_dir)

        # Import module
        module_name = f"src.tools.{plugin_path.name}"
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logger.warning("Failed to import plugin module %s: %s", module_name, e)
            return None

        # Inject settings into module
        if hasattr(module, "SETTINGS"):
            module.SETTINGS.update(settings)
        else:
            module.SETTINGS = settings

        # Collect tool functions
        tools = {}
        for tool_name in manifest.tools:
            if hasattr(module, tool_name):
                fn = getattr(module, tool_name)
                if callable(fn):
                    tools[tool_name] = fn
                else:
                    logger.warning("Tool %s in %s is not callable", tool_name, manifest.id)
            else:
                logger.warning("Tool %s not found in plugin %s", tool_name, manifest.id)

        if not tools:
            logger.warning("Plugin %s has no valid tools - skipping", manifest.id)
            return None

        plugin = LoadedPlugin(
            manifest=manifest,
            module=module,
            tools=tools,
            settings=settings,
            path=plugin_path,
        )

        self.loaded_plugins[manifest.id] = plugin
        logger.info(
            "Loaded plugin %s v%s with %d tools",
            manifest.id,
            manifest.version,
            len(tools),
        )

        return plugin

    def load_all(self) -> List[LoadedPlugin]:
        """
        Load all discovered plugins in dependency order.

        Returns list of successfully loaded plugins.
        """
        plugin_paths = self.discover_plugins()

        # Sort by dependencies (simple topological sort)
        # For now, just load in directory order (assumes no complex deps)
        loaded = []

        for path in sorted(plugin_paths):
            plugin = self.load_plugin(path)
            if plugin:
                loaded.append(plugin)

        return loaded

    def reload_plugin(self, plugin_id: str) -> Optional[LoadedPlugin]:
        """
        Reload a specific plugin (hot reload).

        Note: Does not unregister tools from MCP - caller must handle that.
        """
        if plugin_id not in self.loaded_plugins:
            logger.warning("Plugin %s not loaded, cannot reload", plugin_id)
            return None

        old_plugin = self.loaded_plugins[plugin_id]

        # Reload the module
        importlib.reload(old_plugin.module)

        # Re-load the plugin
        return self.load_plugin(old_plugin.path)

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get info about all loaded plugins for introspection."""
        return [
            {
                "id": p.manifest.id,
                "name": p.manifest.name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "tools": list(p.tools.keys()),
                "settings": p.settings,
            }
            for p in self.loaded_plugins.values()
        ]
```

### Settings System

Create `src/tools/registry_tools/__init__.py` (migrated):

```python
#!/usr/bin/env python3
"""Registry introspection tools."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Settings injected by loader
SETTINGS: Dict[str, Any] = {
    "validate_paths": False,
    "cache_registry": True,
    "cache_ttl_seconds": 300,
}

# Cache for registry data
_registry_cache = None
_cache_time = 0


def _get_registry():
    """Get registry with caching based on settings."""
    global _registry_cache, _cache_time
    import time

    if SETTINGS["cache_registry"]:
        now = time.time()
        if _registry_cache and (now - _cache_time) < SETTINGS["cache_ttl_seconds"]:
            return _registry_cache

    from src.registry_loader import RegistryLoader
    _registry_cache = RegistryLoader(validate_paths=SETTINGS["validate_paths"])
    _cache_time = time.time()
    return _registry_cache


def lookup_model(role: str) -> str:
    """Look up model config for an orchestrator role.

    Args:
        role: Role name (e.g., "coder_primary", "architect_general").

    Returns:
        Formatted string with role configuration details.
    """
    try:
        registry = _get_registry()
        role_config = registry.get_role(role)

        speed = role_config.performance.optimized_tps or role_config.performance.baseline_tps or "?"
        speedup = role_config.performance.speedup or "N/A"

        lines = [
            f"Role: {role_config.name}",
            f"Tier: {role_config.tier}",
            f"Description: {role_config.description}",
            f"Model: {role_config.model.name}",
            f"Quant: {role_config.model.quant}",
            f"Size: {role_config.model.size_gb} GB",
            f"Acceleration: {role_config.acceleration.type}",
            f"Speed: {speed} t/s",
            f"Speedup: {speedup}",
        ]

        if role_config.constraints and role_config.constraints.forbid:
            lines.append(f"Forbidden: {', '.join(role_config.constraints.forbid)}")
        if role_config.notes:
            lines.append(f"Notes: {role_config.notes}")

        return "\n".join(lines)

    except KeyError:
        return f"Role not found: {role}"
    except Exception as e:
        logger.warning("Error loading role '%s': %s: %s", role, type(e).__name__, e)
        return f"Error loading role '{role}': {type(e).__name__}: {e}"


def list_roles() -> str:
    """List all configured orchestrator roles by tier.

    Returns:
        Formatted string with all roles grouped by tier.
    """
    try:
        registry = _get_registry()
        lines = []

        for tier in ["A", "B", "C", "D"]:
            roles = registry.get_roles_by_tier(tier)
            if roles:
                lines.append(f"\n--- Tier {tier} ---")
                for r in roles:
                    speed = r.performance.optimized_tps or r.performance.baseline_tps or "?"
                    accel = r.acceleration.type
                    lines.append(f"  {r.name}: {r.model.name} ({accel}, {speed} t/s)")

        return "\n".join(lines) if lines else "No roles configured."

    except Exception as e:
        logger.warning("Error listing roles: %s: %s", type(e).__name__, e)
        return f"Error listing roles: {type(e).__name__}: {e}"
```

### Refactored MCP Server

Update `src/mcp_server.py`:

```python
#!/usr/bin/env python3
"""MCP server with dynamic tool loading.

Loads tool plugins from src/tools/ directory. Each plugin is a subdirectory
containing a manifest.json and __init__.py with tool functions.

Usage (stdio transport, launched by Claude Code):
    python src/mcp_server.py

Configuration (.mcp.json):
    {
      "mcpServers": {
        "orchestrator": {
          "command": "python",
          "args": ["src/mcp_server.py"]
        }
      }
    }
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Resolve paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "src" / "tools"
USER_SETTINGS_DIR = PROJECT_ROOT / "src" / "tool_settings"

sys.path.insert(0, str(PROJECT_ROOT))

# Create MCP server
mcp = FastMCP("orchestrator")


def load_tools():
    """Load all tool plugins and register with MCP."""
    from src.tool_loader import ToolPluginLoader

    loader = ToolPluginLoader(TOOLS_DIR, USER_SETTINGS_DIR)
    plugins = loader.load_all()

    tool_count = 0
    for plugin in plugins:
        for tool_name, tool_fn in plugin.tools.items():
            # Register tool with FastMCP
            mcp.tool()(tool_fn)
            tool_count += 1
            logger.debug("Registered tool: %s from %s", tool_name, plugin.manifest.id)

    logger.info("Loaded %d tools from %d plugins", tool_count, len(plugins))

    # Store loader for introspection
    mcp._plugin_loader = loader


# Built-in introspection tool (always available)
@mcp.tool()
def list_plugins() -> str:
    """List all loaded tool plugins and their tools.

    Returns:
        Formatted list of plugins with their tools.
    """
    if not hasattr(mcp, "_plugin_loader"):
        return "Plugin loader not initialized."

    info = mcp._plugin_loader.get_plugin_info()
    if not info:
        return "No plugins loaded."

    lines = ["Loaded Plugins:"]
    for p in info:
        lines.append(f"\n[{p['id']}] {p['name']} v{p['version']}")
        lines.append(f"  {p['description']}")
        lines.append(f"  Tools: {', '.join(p['tools'])}")

    return "\n".join(lines)


@mcp.tool()
def get_plugin_settings(plugin_id: str) -> str:
    """Get current settings for a plugin.

    Args:
        plugin_id: The plugin identifier.

    Returns:
        JSON-formatted settings.
    """
    if not hasattr(mcp, "_plugin_loader"):
        return "Plugin loader not initialized."

    plugins = mcp._plugin_loader.loaded_plugins
    if plugin_id not in plugins:
        return f"Plugin not found: {plugin_id}"

    return json.dumps(plugins[plugin_id].settings, indent=2)


if __name__ == "__main__":
    # Load plugins before starting server
    load_tools()

    # Run server
    mcp.run(transport="stdio")
```

### Migration Plan

**Phase 1: Directory Structure** (Day 1)

```bash
# Create directories
mkdir -p src/tools/{registry_tools,benchmark_tools,server_tools,memory_tools,canvas_tools}
mkdir -p src/tool_settings

# Create manifest.json for each plugin
# See examples above

# Move existing tool code to __init__.py files
```

**Phase 2: Tool Loader** (Day 1-2)

1. Create `src/tool_loader.py` (copy from above)
2. Create `src/tool_manifest.schema.json` (copy from above)
3. Test loader independently:
   ```python
   from src.tool_loader import ToolPluginLoader
   loader = ToolPluginLoader(Path("src/tools"))
   plugins = loader.load_all()
   print(f"Loaded {len(plugins)} plugins")
   ```

**Phase 3: Migrate Existing Tools** (Day 2)

For each existing tool in `mcp_server.py`:
1. Create plugin directory
2. Create `manifest.json`
3. Move function to `__init__.py`
4. Add `SETTINGS` dict for configuration
5. Test individually

**Phase 4: Update MCP Server** (Day 2-3)

1. Replace `mcp_server.py` with new loader version
2. Test with Claude Code
3. Verify all tools work

**Phase 5: Add Canvas Tools** (Day 3-4)

1. Create `src/canvas_export.py`
2. Create `src/canvas_import.py`
3. Create `src/tools/canvas_tools/` with manifest
4. Test canvas export/import

**Phase 6: Documentation & Testing** (Day 4-5)

1. Add tests for tool loader
2. Add tests for canvas export/import
3. Update CLAUDE.md with new tool architecture
4. Create user documentation for settings

---

## Architecture Reference Tables

### Canvas Node Type Reference

| Type | Required Fields | Optional Fields | Use Case |
|------|-----------------|-----------------|----------|
| `text` | `id`, `type`, `x`, `y`, `width`, `height`, `text` | `color` | Hypotheses, failures, annotations |
| `file` | `id`, `type`, `x`, `y`, `width`, `height`, `file` | `color`, `subpath` | Link to vault files |
| `link` | `id`, `type`, `x`, `y`, `width`, `height`, `url` | `color` | External references |
| `group` | `id`, `type`, `x`, `y`, `width`, `height` | `color`, `label`, `background`, `backgroundStyle` | Conceptual clusters |

### Canvas Color Semantic Mapping

| Color Code | Color Name | Semantic Meaning (This Project) | Use For |
|------------|------------|--------------------------------|---------|
| `"1"` | Red | Warning / Suppress / Low confidence | Failures, low-confidence hypotheses |
| `"2"` | Orange | Caution / Symptom | Symptoms, medium severity |
| `"3"` | Yellow | Neutral / Medium confidence | Untested hypotheses |
| `"4"` | Green | Approved / Boost / High confidence | Mitigations, high-confidence hypotheses |
| `"5"` | Cyan | Informational | Annotations, context |
| `"6"` | Purple | Causal / Relationship | Causal chains (PRECEDED_BY) |

### Spatial Layout Semantics

| Dimension | Mapping | Interpretation |
|-----------|---------|----------------|
| **Y-axis (vertical)** | Confidence/Priority | Higher = more important (smaller Y value) |
| **X-axis (horizontal)** | Category/Time | Left-to-right = chronological or categorical |
| **Proximity** | Relatedness | Closer nodes = conceptually related |
| **Grouping** | Clustering | Nodes in same group = same concept category |
| **Color** | Status | See color semantic mapping above |

### Constraint Type Reference

| Constraint Type | Trigger | Effect on HypothesisGraph |
|-----------------|---------|---------------------------|
| `boost` | Node high on canvas (Y < center - 200) | Increase confidence: `c += δ(1-c)` |
| `suppress` | Node low on canvas (Y > center + 200) | Decrease confidence: `c -= δc` |
| `boost` | Node colored green (`"4"`) | Increase confidence (strength 0.8) |
| `suppress` | Node colored red (`"1"`) | Decrease confidence (strength 0.8) |
| `annotate` | New text node (unknown ID prefix) | Store as user constraint |
| `group` | Nodes inside group bounding box | Mark as conceptually related |

### Plugin Manifest Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique identifier (`^[a-z][a-z0-9_-]*$`) |
| `name` | string | ✅ | Human-readable name |
| `version` | string | ✅ | Semantic version (`X.Y.Z`) |
| `tools` | string[] | ✅ | Function names to register |
| `description` | string | ❌ | Brief description |
| `author` | string | ❌ | Author name/team |
| `minOrchestratorVersion` | string | ❌ | Minimum compatible version |
| `dependencies` | string[] | ❌ | Required plugin IDs |
| `settings` | object | ❌ | Configurable settings schema |

### Settings Priority Order

| Priority | Source | Location |
|----------|--------|----------|
| 1 (highest) | User override | `src/tool_settings/{plugin_id}.json` |
| 2 | Plugin defaults | `src/tools/{plugin}/settings.json` |
| 3 (lowest) | Manifest defaults | `manifest.json` → `settings.{key}.default` |

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DISK LAYER                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Kuzu Graph  │  │ .canvas     │  │ manifest    │             │
│  │ (relational)│  │ (JSON)      │  │ (JSON)      │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TRANSFORM LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ canvas_export│  │ canvas_import│  │ tool_loader  │          │
│  │ (Kuzu→JSON)  │  │ (JSON→TOON) │  │ (manifest→fn)│          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼────────────────┼────────────────┼─────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LLM CONTEXT                               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Agent Working Memory                                  │      │
│  │ - TOON-encoded canvas (55-65% fewer tokens)          │      │
│  │ - Registered tool functions                           │      │
│  │ - Constraint-adjusted confidences                     │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Graph-to-Canvas Mapping

| Graph Entity | Canvas Representation | Layout Rule |
|--------------|----------------------|-------------|
| `Hypothesis` | Text node | Grid, Y by confidence |
| `Evidence` | Text node (smaller) | Below linked hypothesis |
| `FailureMode` | Text node (center) | Y by severity |
| `Symptom` | Text node (left column) | Y by index |
| `Mitigation` | Text node (right column) | Y by index |
| `SUPPORTS` | Green edge | Evidence → Hypothesis |
| `CONTRADICTS` | Red edge | Evidence → Hypothesis |
| `PRECEDED_BY` | Purple edge | Failure → Failure |
| `MITIGATED_BY` | Green edge | Failure → Mitigation |

### TOON vs JSON Token Comparison

| Content | JSON Tokens | TOON Tokens | Reduction | Recommendation |
|---------|-------------|-------------|-----------|----------------|
| Canvas (5 nodes) | ~180 | ~80 | 56% | Use TOON |
| Canvas (10 nodes) | ~450 | ~180 | 60% | Use TOON |
| Canvas (25 nodes) | ~1100 | ~420 | 62% | Use TOON |
| Canvas (<5 nodes) | ~100 | ~60 | 40% | JSON OK |

---

## Implementation Phases

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 1 | Directory structure setup | 0.5 day | None |
| 2 | Tool loader implementation | 1 day | Phase 1 |
| 3 | Migrate existing tools | 1 day | Phase 2 |
| 4 | Update MCP server | 0.5 day | Phase 3 |
| 5 | Canvas tools implementation | 1 day | Phase 4 |
| 6 | Documentation & testing | 1 day | Phase 5 |

**Total: 5 days**

---

## Testing Strategy

### Unit Tests

Create `tests/test_tool_loader.py`:

```python
import pytest
from pathlib import Path
from src.tool_loader import (
    ToolPluginLoader,
    load_manifest,
    parse_version,
    version_compatible,
)


def test_parse_version():
    assert parse_version("1.0.0") == (1, 0, 0)
    assert parse_version("2.10.3") == (2, 10, 3)
    assert parse_version("invalid") == (0, 0, 0)


def test_version_compatible():
    assert version_compatible("0.1.0", "0.2.0")
    assert version_compatible("1.0.0", "1.0.0")
    assert not version_compatible("2.0.0", "1.0.0")


def test_load_manifest(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('''
    {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "tools": ["test_tool"]
    }
    ''')

    manifest = load_manifest(manifest_path)
    assert manifest is not None
    assert manifest.id == "test-plugin"
    assert manifest.tools == ["test_tool"]
```

Create `tests/test_canvas_export.py`:

```python
import pytest
import json
from pathlib import Path
from src.canvas_export import (
    CanvasBuilder,
    CanvasNode,
    CanvasEdge,
    confidence_to_color,
)


def test_canvas_builder():
    builder = CanvasBuilder()

    node = CanvasNode(
        id="test",
        type="text",
        x=100,
        y=200,
        width=200,
        height=100,
        text="Test node",
    )
    builder.add_node(node)

    canvas = builder.to_dict()
    assert len(canvas["nodes"]) == 1
    assert canvas["nodes"][0]["id"] == "test"


def test_confidence_to_color():
    assert confidence_to_color(0.9) == "4"  # Green
    assert confidence_to_color(0.5) == "3"  # Yellow
    assert confidence_to_color(0.1) == "1"  # Red


def test_canvas_round_trip(tmp_path):
    builder = CanvasBuilder()
    builder.add_node(CanvasNode(
        id="n1", type="text", x=0, y=0, width=100, height=100, text="Node 1"
    ))
    builder.add_edge(CanvasEdge(
        id="e1", from_node="n1", to_node="n1", label="self"
    ))

    output_path = tmp_path / "test.canvas"
    builder.save(output_path)

    # Verify it's valid JSON
    loaded = json.loads(output_path.read_text())
    assert len(loaded["nodes"]) == 1
    assert len(loaded["edges"]) == 1
```

### Integration Tests

```python
def test_mcp_server_loads_plugins(tmp_path):
    """Test that MCP server loads all plugins without errors."""
    from src.tool_loader import ToolPluginLoader

    loader = ToolPluginLoader(Path("src/tools"))
    plugins = loader.load_all()

    assert len(plugins) >= 1  # At least registry tools
    assert any(p.manifest.id == "registry-tools" for p in plugins)


def test_canvas_export_hypothesis_graph(tmp_path):
    """Test exporting a real hypothesis graph."""
    from orchestration.repl_memory.hypothesis_graph import HypothesisGraph
    from src.canvas_export import export_hypothesis_graph

    # Use a temporary graph
    graph = HypothesisGraph(path=tmp_path / "test_graph")

    # Add some test data
    h_id = graph.create_hypothesis("test|action", "memory_1")
    graph.add_evidence(h_id, "success", "memory_2")

    # Export
    output_path = tmp_path / "test.canvas"
    export_hypothesis_graph(graph, output_path)

    assert output_path.exists()

    # Verify structure
    canvas = json.loads(output_path.read_text())
    assert "nodes" in canvas
    assert "edges" in canvas
```

---

## Dependencies

### Python Packages

No new packages required. Uses existing:
- `kuzu` (already installed for graph storage)
- `mcp` (already installed for MCP server)
- Standard library: `json`, `pathlib`, `importlib`, `dataclasses`

### External Tools

- **Obsidian** (optional): For viewing/editing `.canvas` files
  - Users should install Obsidian from https://obsidian.md
  - Point Obsidian at the vault containing `logs/canvases/`

---

## Bibliographical References

### JSON Canvas Specification

| Resource | URL | Description |
|----------|-----|-------------|
| **JSON Canvas Spec v1.0** | https://jsoncanvas.org/spec/1.0/ | Official specification |
| **JSON Canvas GitHub** | https://github.com/obsidianmd/jsoncanvas | Reference implementation, MIT license |
| **canvas.d.ts** | https://github.com/obsidianmd/obsidian-api/blob/master/canvas.d.ts | TypeScript type definitions |
| **Obsidian Blog: JSON Canvas** | https://obsidian.md/blog/json-canvas/ | Announcement and rationale |

### Obsidian Plugin Architecture

| Resource | URL | Description |
|----------|-----|-------------|
| **Obsidian API** | https://github.com/obsidianmd/obsidian-api | Type definitions (obsidian.d.ts) |
| **Sample Plugin** | https://github.com/obsidianmd/obsidian-sample-plugin | Official plugin template |
| **Plugin Guidelines** | https://docs.obsidian.md/Plugins/Releasing/Plugin+guidelines | Submission requirements |
| **Developer Docs** | https://docs.obsidian.md | Official documentation |
| **Community Plugins** | https://github.com/obsidianmd/obsidian-releases | Plugin registry (2700+ plugins) |

### TOON Format (Token Optimization)

| Resource | Location | Description |
|----------|----------|-------------|
| **TOON Evaluation** | `research/TOON_EVALUATION.md` | Internal evaluation results |
| **TOON Encoder** | `src/services/toon_encoder.py` | Implementation (7 functions) |
| **TOON Tests** | `tests/unit/test_toon_encoder.py` | 17 unit tests |

**Key Findings** (from evaluation):
- 55-65% token reduction for structured data
- Best for: file listings, tool outputs, canvas data
- Reject for: grep hits (Markdown better)

### Internal Dependencies

| Component | Location | Purpose |
|-----------|----------|---------|
| **HypothesisGraph** | `orchestration/repl_memory/hypothesis_graph.py` | Kuzu-backed confidence tracking |
| **FailureGraph** | `orchestration/repl_memory/failure_graph.py` | Failure pattern anti-memory |
| **EpisodicStore** | `orchestration/repl_memory/episodic_store.py` | SQLite + FAISS memory |
| **MCP Server** | `src/mcp_server.py` | Current tool server |
| **FastMCP** | `mcp.server.fastmcp` | MCP server framework |

### Related Research

| Topic | Reference | Relevance |
|-------|-----------|-----------|
| **MemRL** | arXiv:2601.03192 | Episodic memory for LLM agents |
| **Spatial Reasoning** | — | Canvas = spatial working memory |
| **Plugin Architecture** | Obsidian patterns | 2700+ plugins prove scalability |
| **Graph Visualization** | — | Obsidian graph view for relationships |

### Design Inspirations

| Pattern | Source | Applied To |
|---------|--------|------------|
| **Manifest-based plugins** | Obsidian, VS Code | Tool plugin system |
| **Hot reload** | Webpack, Vite | Plugin reloading |
| **Settings cascade** | CSS, npm config | User > Plugin > Manifest defaults |
| **Spatial semantics** | Whiteboard apps (Miro, FigJam) | Y-axis = priority |
| **Forward compatibility** | JSON Canvas `[key: any]` | Manifest extensibility |

### External APIs and Specs

| Spec | Version | Usage |
|------|---------|-------|
| JSON Schema | draft/2020-12 | Tool manifest validation |
| Semantic Versioning | 2.0.0 | Plugin versioning |
| MCP (Model Context Protocol) | — | Tool registration |
| Kuzu Cypher | — | Graph queries |

---

## Open Questions (With Recommendations)

| # | Question | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | **Canvas file location** | `logs/canvases/` | Keeps with runtime artifacts, gitignored, matches existing `logs/` pattern |
| 2 | **Auto-export on session start** | **Yes** | Small overhead (~50ms), enables human review, creates checkpoint |
| 3 | **Canvas watching** | **No** (manual import) | Avoids fswatch/inotify complexity; explicit `import_canvas_edits()` is predictable |
| 4 | **Settings persistence** | `src/tool_settings/` (gitignored) | Project-local, portable, doesn't pollute `~/.config/` |
| 5 | **Plugin version migrations** | **Warn + use defaults** | Log when schema changes, apply new defaults for missing keys, don't break |
| 6 | **Hot reload scope** | **New calls only** | Simpler, safer, matches VS Code/Obsidian behavior |

### Additional Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **TOON text truncation** | 50 chars + REPL fallback | Agent sees summary, can `_peek()` or query graph for full context |
| **Disk format** | Always standard JSON | Preserves Obsidian interoperability unconditionally |
| **TOON threshold** | 5 nodes | Below this, JSON overhead is minimal (~40 token savings not worth complexity) |
| **Canvas export frequency** | On-demand via MCP tool | Not automatic; agent/user controls when to snapshot |
| **Constraint strength** | 0.2 * position/color factor | Asymptotic update preserves stability (won't overshoot to 0 or 1) |

### REPL Exploration Pattern for Truncated Content

When TOON truncates node text (at `toon_text_truncate` chars), the agent can retrieve full context:

```python
# Agent sees in TOON-encoded canvas:
#   hyp_abc123,text,100,200,280,120,4,**spec_decode|code_gen** Conf...

# Agent wants full hypothesis details:
result = hypothesis_graph.conn.execute("""
    MATCH (h:Hypothesis {id: $id})
    RETURN h.claim, h.confidence, h.tested, h.created_at
""", {"id": "abc123"})

# Or via REPL tool:
_recall(query="spec_decode code_gen", limit=1)
```

This matches existing patterns where summaries trigger deeper exploration.

---

## Files to Create

### Core Canvas Module

| File | Description | LOC (est.) |
|------|-------------|------------|
| `src/canvas_export.py` | Canvas export functions (Kuzu → JSON Canvas) | ~400 |
| `src/canvas_import.py` | Canvas import, constraints, TOON encoding | ~350 |

### Plugin Infrastructure

| File | Description | LOC (est.) |
|------|-------------|------------|
| `src/tool_loader.py` | Dynamic plugin loader | ~300 |
| `src/tool_manifest.schema.json` | JSON Schema for manifests | ~80 |
| `src/tools/__init__.py` | Empty (package marker) | 1 |

### Migrated Plugins

| File | Description | LOC (est.) |
|------|-------------|------------|
| `src/tools/registry_tools/manifest.json` | Registry plugin manifest | ~25 |
| `src/tools/registry_tools/__init__.py` | `lookup_model`, `list_roles` | ~80 |
| `src/tools/registry_tools/settings.json` | Default settings | ~10 |
| `src/tools/benchmark_tools/manifest.json` | Benchmark plugin manifest | ~20 |
| `src/tools/benchmark_tools/__init__.py` | `query_benchmarks` | ~50 |
| `src/tools/server_tools/manifest.json` | Server plugin manifest | ~20 |
| `src/tools/server_tools/__init__.py` | `server_status` | ~40 |

### New Canvas Plugin

| File | Description | LOC (est.) |
|------|-------------|------------|
| `src/tools/canvas_tools/manifest.json` | Canvas plugin manifest | ~30 |
| `src/tools/canvas_tools/__init__.py` | `export_reasoning_canvas`, `import_canvas_edits`, `list_canvases` | ~120 |
| `src/tools/canvas_tools/settings.json` | TOON settings | ~10 |

### Tests

| File | Description | LOC (est.) |
|------|-------------|------------|
| `tests/test_tool_loader.py` | Tool loader unit tests | ~100 |
| `tests/test_canvas_export.py` | Canvas export unit tests | ~150 |
| `tests/test_canvas_import.py` | Canvas import + TOON tests | ~120 |

### Total Estimated LOC: ~1,900

---

## Resume Commands

```bash
# Start implementation
cd /mnt/raid0/llm/claude

# Phase 1: Create directory structure
mkdir -p src/tools/{registry_tools,benchmark_tools,server_tools,canvas_tools}
mkdir -p src/tool_settings

# Phase 2: Create tool loader
# Edit src/tool_loader.py (copy from this handoff)

# Phase 3: Create canvas modules
# Edit src/canvas_export.py
# Edit src/canvas_import.py

# Phase 4: Run tests
pytest tests/test_tool_loader.py tests/test_canvas_export.py -v

# Phase 5: Test MCP server
python src/mcp_server.py  # Test manually with stdio

# Verify gates pass
make gates
```

---

## Completion Checklist

### Phase 1: Directory Structure
- [ ] `src/tools/` directory created
- [ ] Plugin subdirectories created (registry, benchmark, server, canvas)
- [ ] `src/tool_settings/` directory created (gitignored)

### Phase 2: Plugin Infrastructure
- [ ] `tool_loader.py` implemented
- [ ] `tool_manifest.schema.json` created
- [ ] Loader unit tests passing

### Phase 3: Tool Migration
- [ ] `registry_tools` plugin created with manifest
- [ ] `benchmark_tools` plugin created with manifest
- [ ] `server_tools` plugin created with manifest
- [ ] All existing tools working via plugin loader

### Phase 4: MCP Server
- [ ] `mcp_server.py` refactored to use plugin loader
- [ ] `list_plugins()` introspection tool working
- [ ] `get_plugin_settings()` tool working
- [ ] Server tested with Claude Code

### Phase 5: Canvas Integration
- [ ] `canvas_export.py` implemented
- [ ] `canvas_import.py` implemented
- [ ] TOON encoding layer implemented (`load_canvas_for_llm()`)
- [ ] TOON round-trip tests passing (`canvas_to_toon()` ↔ `toon_to_canvas()`)
- [ ] `canvas_tools` plugin created
- [ ] Export/import end-to-end working
- [ ] Canvas viewable in Obsidian

### Phase 6: Testing & Documentation
- [ ] Unit tests: `test_tool_loader.py` passing
- [ ] Unit tests: `test_canvas_export.py` passing
- [ ] Unit tests: `test_canvas_import.py` passing
- [ ] Integration tests passing
- [ ] CLAUDE.md updated with plugin architecture
- [ ] `make gates` passing

### Verification Gates
- [ ] All 5 plugins load without errors
- [ ] Canvas export produces valid JSON Canvas
- [ ] TOON encoding reduces tokens by >50% for 10+ node canvases
- [ ] Obsidian can open exported `.canvas` files
- [ ] User edits in Obsidian import as constraints
- [ ] No regressions in existing MCP tools
