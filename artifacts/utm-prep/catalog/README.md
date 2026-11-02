# UTM-B1 catalog comparison preparation

`catalog_server.py` provides isolated stdio baseline and candidate processes. Both import the same orchestrator MCP server and initialize its normal plugin loader; the candidate explicitly adds the existing trace-navigation registrar. Nothing modifies or restarts the shared API or changes the default catalog. Both arms must use the same pinned orchestrator checkout and environment. The candidate requires an existing owner-only private directory and an existing owner-owned DB inside it with no filesystem write bits; the DB path is not exposed to the model. Resolve SQLite WAL/sidecar state before making the DB read-only. Use only an approved, appropriately scoped trace DB. The underlying search opens SQLite normally; filesystem permissions, not SQLite URI mode=ro, are the write restriction. This is not a security boundary against the account owner.

**Privacy scope:** `session_id` is accepted by the current registrar but ignored for both `ms.search` and `ms.expand`. Either tool can return records from any session in the selected DB. Use only a DB whose entire contents are safe for this model; per-session isolation requires separately implemented and tested filtering.

**Review status:** This is an unaccepted prototype. Catalog comparison can accept an empty baseline, silently collapse duplicate tool names, and does not bind captures to a pinned app, configuration, or source identity. Inventory tests do not prove actual search or expansion, SQLite read-only behavior, or WAL safety. Resolve these issues and independently review them before using this tool to support an experiment.

Capture catalog snapshots in distinct processes using the orchestrator environment and replace placeholders:

```sh
APP=/path/to/pinned/epyc-orchestrator
PY="$APP/.venv/bin/python"
SCRIPT=/path/to/catalog_server.py
"$PY" "$SCRIPT" inventory --app-root "$APP" --arm baseline > baseline.json
"$PY" "$SCRIPT" inventory --app-root "$APP" --arm candidate --private-root /private/root --db /private/root/trace.sqlite > candidate.json
"$PY" "$SCRIPT" compare --baseline baseline.json --candidate candidate.json
```

`compare` requires exactly ms.search and ms.expand as additions, unchanged existing descriptors, no removals, expected inputs and optional session_id. To wire a future isolated harness attempt use `serve` with corresponding arm arguments instead of `inventory`. The candidate server must be launched by the harness; this file does not change the existing --enable-mcp fixture, prepare an OpenCode config, or launch inference.

Validation 2026-11-02: separate local FastMCP inventory processes using the installed orchestrator environment and an empty owner-only synthetic database produced the exact two additions, no changed/removed tools; negative checks rejected a missing tool, changed existing description, and DB outside its private root. The empty DB was used only for catalog introspection; real navigation, model consumption and retrieval quality were not evaluated.

Before publishing a row: freeze the passing task set and exact before/after catalog snapshots; pin and verify current model, endpoint, app source and candidate launcher; provision a valid private read-only DB; prepare matched baseline/candidate OpenCode configs and separate attempt directories; solve distinct arm/repeat identity in the native runner and SC86; confirm permissions, cost/duration, the two candidate reruns, and the stated failure/token-ratio decision rule. Do not use the historical MCP-disabled r3 result as the matched baseline. No inference was run.
