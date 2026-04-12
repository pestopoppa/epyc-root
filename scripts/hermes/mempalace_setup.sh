#!/bin/bash
set -euo pipefail
# MemPalace MCP Server — Setup for Hermes Outer Shell Integration
# Task H-8: Persistent cross-session memory via MemPalace (19 MCP tools)
#
# MemPalace provides knowledge-graph-backed persistent memory using
# ChromaDB (vector store) + SQLite (structured data). Local-first, MIT licensed.
# Achieves 96.6% LongMemEval recall.
#
# Source: intake-326
# Usage: ./mempalace_setup.sh [--claude-mcp]
#   --claude-mcp  Also register with Claude Code via `claude mcp add`

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${HOME}/.mempalace"
MEMPALACE_PKG="mempalace"
REGISTER_CLAUDE_MCP=false

# =============================================================================
# Parse arguments
# =============================================================================
for arg in "$@"; do
    case "$arg" in
        --claude-mcp) REGISTER_CLAUDE_MCP=true ;;
        -h|--help)
            echo "Usage: $(basename "$0") [--claude-mcp]"
            echo ""
            echo "Sets up MemPalace MCP server for Hermes outer shell integration."
            echo ""
            echo "Options:"
            echo "  --claude-mcp  Register MemPalace with Claude Code via 'claude mcp add'"
            echo "  -h, --help    Show this help"
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $arg"
            exit 1
            ;;
    esac
done

echo "=== MemPalace MCP Server Setup ==="
echo ""

# =============================================================================
# 1. Create data directory
# =============================================================================
echo "[1/4] Setting up data directory..."
mkdir -p "${DATA_DIR}"
mkdir -p "${DATA_DIR}/chroma"
mkdir -p "${DATA_DIR}/sqlite"
echo "  Data directory: ${DATA_DIR}"
echo "  ChromaDB store: ${DATA_DIR}/chroma"
echo "  SQLite store:   ${DATA_DIR}/sqlite"
echo ""

# =============================================================================
# 2. Check/install mempalace
# =============================================================================
echo "[2/4] Checking MemPalace installation..."

if python3 -c "import mempalace" 2>/dev/null; then
    MEMPALACE_VERSION=$(python3 -c "import mempalace; print(getattr(mempalace, '__version__', 'unknown'))" 2>/dev/null || echo "installed")
    echo "  MemPalace already installed (version: ${MEMPALACE_VERSION})"
else
    echo "  MemPalace not found. Attempting installation..."
    echo ""

    # Strategy 1: pip install (works if published to PyPI)
    if pip install "${MEMPALACE_PKG}" 2>/dev/null; then
        echo "  Installed via pip."
    # Strategy 2: git clone + pip install -e (pre-PyPI / development)
    elif [[ -d "/mnt/raid0/llm/mempalace" ]]; then
        echo "  Found local clone at /mnt/raid0/llm/mempalace"
        pip install -e /mnt/raid0/llm/mempalace
        echo "  Installed from local clone (editable mode)."
    else
        echo ""
        echo "  WARNING: Could not install MemPalace automatically."
        echo "  MemPalace may not be on PyPI yet (source: intake-326)."
        echo ""
        echo "  Manual installation options:"
        echo "    Option A (PyPI, when available):"
        echo "      pip install mempalace"
        echo ""
        echo "    Option B (from source):"
        echo "      git clone https://github.com/mempalace/mempalace.git /mnt/raid0/llm/mempalace"
        echo "      pip install -e /mnt/raid0/llm/mempalace"
        echo ""
        echo "  After installing, re-run this script."
        echo ""
        # Continue setup even without install — script creates config and docs
    fi
fi
echo ""

# =============================================================================
# 3. Register as Claude Code MCP server (optional)
# =============================================================================
echo "[3/4] MCP server registration..."

if [[ "$REGISTER_CLAUDE_MCP" == true ]]; then
    if command -v claude &>/dev/null; then
        echo "  Registering MemPalace with Claude Code..."
        claude mcp add mempalace -- python3 -m mempalace.mcp_server
        echo "  Registered: claude mcp add mempalace -- python3 -m mempalace.mcp_server"
    else
        echo "  WARNING: 'claude' CLI not found."
        echo "  Register manually when available:"
        echo "    claude mcp add mempalace -- python3 -m mempalace.mcp_server"
    fi
else
    echo "  Skipped (use --claude-mcp flag to register with Claude Code)."
    echo "  Manual command:"
    echo "    claude mcp add mempalace -- python3 -m mempalace.mcp_server"
fi
echo ""

# =============================================================================
# 4. Write config file
# =============================================================================
echo "[4/4] Writing MemPalace config..."

CONFIG_FILE="${DATA_DIR}/config.yaml"
if [[ -f "$CONFIG_FILE" ]]; then
    echo "  Config exists: ${CONFIG_FILE} (not overwritten)"
else
    cat > "$CONFIG_FILE" << 'CONFIGEOF'
# MemPalace MCP Server Configuration
# Generated by mempalace_setup.sh
# See: intake-326

storage:
  # ChromaDB for vector similarity search
  chroma_path: ~/.mempalace/chroma
  # SQLite for structured data (knowledge graph, agent diary)
  sqlite_path: ~/.mempalace/sqlite/mempalace.db

server:
  # MCP transport (stdio for Claude Code integration)
  transport: stdio
  # Data directory root
  data_dir: ~/.mempalace

# Embedding model for ChromaDB (default: local sentence-transformers)
# MemPalace uses local embeddings — no cloud API calls needed.
embedding:
  model: all-MiniLM-L6-v2
  device: cpu
CONFIGEOF
    echo "  Created: ${CONFIG_FILE}"
fi
echo ""

# =============================================================================
# Summary and verification instructions
# =============================================================================
echo "=== Setup Complete ==="
echo ""
echo "Data directory:  ${DATA_DIR}"
echo "Config file:     ${DATA_DIR}/config.yaml"
echo ""
echo "--- Available MCP Tools (19) ---"
echo ""
echo "  Palace Management:"
echo "    palace_create        Create a new memory palace"
echo "    palace_list          List all palaces"
echo "    palace_delete        Delete a palace"
echo "    palace_info          Get palace metadata and stats"
echo ""
echo "  Memory Read/Write:"
echo "    palace_read          Read memories by key or query"
echo "    palace_write         Write a memory to a palace"
echo "    palace_update        Update an existing memory"
echo "    palace_delete_memory Delete a specific memory"
echo "    palace_search        Semantic search across memories"
echo "    palace_list_memories List all memories in a palace"
echo ""
echo "  Knowledge Graph:"
echo "    kg_add_entity        Add entity to knowledge graph"
echo "    kg_add_relation      Add relation between entities"
echo "    kg_query             Query the knowledge graph"
echo "    kg_visualize         Get graph visualization data"
echo ""
echo "  Navigation:"
echo "    palace_navigate      Walk through palace rooms/loci"
echo "    palace_map           Get spatial map of a palace"
echo ""
echo "  Agent Diary:"
echo "    diary_write          Write an agent diary entry"
echo "    diary_read           Read diary entries (by date/tag)"
echo "    diary_search         Search diary entries"
echo ""
echo "--- Verification Steps ---"
echo ""
echo "  1. Check MemPalace is importable:"
echo "     python3 -c \"import mempalace; print('OK')\""
echo ""
echo "  2. Test MCP server starts:"
echo "     python3 -m mempalace.mcp_server --help"
echo ""
echo "  3. If registered with Claude Code, verify:"
echo "     claude mcp list | grep mempalace"
echo ""
echo "  4. In a Claude Code session, the 19 tools should appear as:"
echo "     mcp__mempalace__palace_create, mcp__mempalace__palace_read, etc."
echo ""
echo "--- Hermes Integration ---"
echo ""
echo "  MemPalace MCP is configured for the Hermes outer shell."
echo "  When Hermes connects via the orchestrator API, MCP tools"
echo "  provide persistent cross-session memory (96.6% LongMemEval recall)."
echo "  See: scripts/hermes/hermes-config.yaml (mempalace section)"
