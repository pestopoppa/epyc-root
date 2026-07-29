# HALO Spike Results — 2026-07-14

**Status**: completed-not-actionable
**Source handoff**: [`handoffs/active/halo-trace-loop-spike.md`](../../handoffs/active/halo-trace-loop-spike.md)

**Run metadata**

- `/tmp/halo-epyc-run-20260714T110923Z.meta`
- `/tmp/halo-epyc-run-20260714T111035Z.meta`
- `/tmp/halo-epyc-canonical.jsonl` (3,532 spans)
- `/tmp/halo-otlp-sample.jsonl` (OTLP conversion staging file)

## Summary

The HALO evidence checkpoint is closed out as not actionable for this spike. The operator-approved preflight succeeded, the trace conversion path was validated against HALO `SpanRecord`, and the analyzer attempt was blocked before report generation because the local OpenAI Responses endpoint at `http://localhost:8000/v1/responses` returned `404`.

This still leaves useful operational evidence:
- the orchestrator trace journal can be converted into HALO-compatible canonical spans without code changes in `epyc-orchestrator`
- the compatibility transform is now proven against 3,532 spans
- the HALO backend dependency is currently bound to a Responses API surface that the local orchestrator does not expose

## Pre-flight gate

HALO-1 was completed in `/tmp/halo-spike-venv` with `halo-engine==0.1.2`, and `halo --help` worked. This satisfied the supply-chain gate that had originally blocked the spike.

## Converter validation

HALO run #1 on the OTLP sample failed schema validation because `halo-engine==0.1.2` expects canonical span records with:
- `trace_id`
- `span_id`
- `start_time`
- `end_time`
- `resource`
- `scope`
- dict-shaped `attributes`

The original OTLP-shaped sample used camelCase field names and list-style attributes. A temporary compatibility transform wrote `/tmp/halo-epyc-canonical.jsonl`, and that file validated successfully against HALO `SpanRecord`.

## HALO-3 scorecard

Recorded scorecard for the analyzer attempt: **1/4**.

Reason for closure:
- HALO invoked the OpenAI Agents SDK path that targets the Responses API
- the local orchestrator at `http://localhost:8000/v1` returned `404` for `/responses`
- analyzer output never materialized, so the run could not satisfy the falsification gate

## HALO-4

Skipped as not applicable. The go threshold is `>=3/4`, and the HALO-3 attempt closed at `1/4`.

## Close-out

HALO-5 is complete because this outcome note records the final state of the checkpoint. The spike does not warrant immediate pattern lift into active scoped work.

Revisit conditions:
- if the local orchestrator exposes a working Responses endpoint
- if a future HALO release changes the backend contract
- if a later checkpoint needs trace-corpus pattern lifting rather than analyzer execution
