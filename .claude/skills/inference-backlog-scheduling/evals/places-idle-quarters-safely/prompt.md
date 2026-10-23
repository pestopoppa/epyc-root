---
tags: [inference-backlog-scheduling]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Bash]
---

You are the compute-calendar owner on the EPYC + MI210 host. It is 2026-11-04 13:05Z and q1 and q2 are idle while the queue has work. Using the snapshot in snapshot.md (treat it as the live FILLERS.md, region-lock status and grants dir), write plan.md: for every placeable row, the bin, the grant window (start/end, UTC) and the writer step it goes in, through to the end of the night (06:25Z) and the 05:00Z quiet window; say what you do with the rows you cannot place and why; and note anything you must NOT grant. Do not run anything on the host; this is a plan only.
Input files: snapshot.md
