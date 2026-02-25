# MCP Knowledge Tools: Remaining Tasks

Complete the remaining tasks for the MCP Integration & Knowledge Tools handoff.

**Handoff**: `handoffs/active/mcp-knowledge-tools.md`

## Your Task

Execute the remaining checklist items from the handoff. Phases 1-2 are already complete (35/35 tests passing). You need to finish Phase 3 (closeout).

### Step 1: Live Smoke Test

Run actual API calls to verify the knowledge tools work end-to-end (not just mocked):

```bash
cd /mnt/raid0/llm/claude
python3 << 'EOF'
from src.tools.knowledge import search_arxiv, search_papers, search_wikipedia, get_wikipedia_article, search_books

# Test arXiv
print("=== arXiv ===")
r = search_arxiv("transformer attention mechanism", max_results=2)
print(f"  success={r['success']}, count={r['count']}")
if r['results']:
    print(f"  first: {r['results'][0]['title'][:60]}")

# Test Semantic Scholar
print("\n=== Semantic Scholar ===")
r = search_papers("speculative decoding", max_results=2)
print(f"  success={r['success']}, count={r['count']}")
if r['results']:
    print(f"  first: {r['results'][0]['title'][:60]}, citations={r['results'][0]['citation_count']}")

# Test Wikipedia search
print("\n=== Wikipedia Search ===")
r = search_wikipedia("large language model", max_results=2)
print(f"  success={r['success']}, count={r['count']}")
if r['results']:
    print(f"  first: {r['results'][0]['title']}")

# Test Wikipedia article
print("\n=== Wikipedia Article ===")
r = get_wikipedia_article("Speculative execution")
print(f"  success={r['success']}, sections={len(r.get('sections', []))}, categories={len(r.get('categories', []))}")

# Test Google Books
print("\n=== Google Books ===")
r = search_books("deep learning", max_results=2)
print(f"  success={r['success']}, count={r['count']}")
if r['results']:
    print(f"  first: {r['results'][0]['title']}")

print("\nAll smoke tests complete.")
EOF
```

If any tool fails, check:
- Network connectivity
- Package imports (`pip show arxiv semanticscholar mwclient google-api-python-client`)
- Rate limits (arXiv has 3s politeness delay, S2 has 100 req/5min)

### Step 2: Write Chapter 24

Create `docs/chapters/chapter-24-knowledge-tools-mcp.md` documenting:

1. **Design decision**: Why hybrid (native + MCP), not full MCP
2. **Knowledge tools**: What each tool does, API rate limits, return schemas
3. **MCP server**: What it exposes, how Claude Code connects
4. **Architecture**: How tools register via YAML, invoke via REPL
5. **Future**: Phase 3 MCP client infrastructure (deferred design)

Reference the existing chapters for style:
```bash
ls docs/chapters/
head -30 docs/chapters/chapter-01-*.md  # See format
```

### Step 3: Update Handoff Table

Add the MCP knowledge tools entry to `handoffs/README.md`:

```markdown
| [mcp-knowledge-tools.md](active/mcp-knowledge-tools.md) | Knowledge tools + MCP server | COMPLETE |
```

### Step 4: Mark Handoff Complete

After Steps 1-3 pass, update the handoff checklist items and then delete the handoff file:

```bash
rm handoffs/active/mcp-knowledge-tools.md
```

### Step 5: Run Gates

```bash
cd /mnt/raid0/llm/claude && make gates
```

## Important Notes

- The `.venv` has a broken Python 3.13 symlink. Use system `python3` (miniforge3).
- `.mcp.json` has been fixed to use `/home/daniele/miniforge3/bin/python3`.
- The `mcp` package is installed in both `.venv` (broken) and system Python (working).
- Do NOT modify `src/tools/knowledge.py`, `src/mcp_server.py`, or tests -- they are reviewed and verified.
- If smoke tests fail due to missing packages: `pip install arxiv semanticscholar mwclient google-api-python-client`
