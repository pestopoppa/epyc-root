# 2026-10-21 noninf-offline

- Skipped (already worked by workspace-f8 or inputs absent): PB-QCOST-1, HSF-3.1, HSF-4, HSF-5, WP-15, RT-6, RT-2.1; SPEC-RNG.1 is a llama.cpp tree change (main's).
- Built the write sides: dispatch.v1 (`src/backends/dispatch_log.py`) for WP-15.1 and HSF-3.1a on fleet, passthrough and direct lanes; epyc-orchestrator main 78f68032 (034113a4 fleet, 78f68032 lanes). Takes effect at next stack start.
- Parents WP-15 and HSF-3.1 stay open (need two traffic windows).
- Follow-ups (orchestrator main 249d7da5, f4fe9307, 058e674b): server-derived client class with class_source, autopilot planner x_client_class, round-robin infer_streaming handed_off, served-model identity (WP-15.2, unticked: live check owed). 162 tests green under region-lock after the quiet window.
