#!/usr/bin/env python3
"""ARCHSWAP-20260927 master-registry transform (epyc-inference-research).

Swaps the architect role LABELS between the two live processes:
  :8074 CPU Qwen3.8-Flash-Next  architect_critic  -> architect_general
  :8083 GPU Qwen3.8-27B Q8      architect_general -> architect_critic
Aliases coder_escalation + ingest_long_context stay on :8083 (host -> architect_critic).

Rule set (PACKAGE.md section 2):
  BINDING follows the PROCESS  : server_mode rows move wholesale (incl. shared_with,
                                  chat_template_kwargs, recipe, env, evidence).
  MODEL facts follow the MODEL : roles.<role> model/acceleration/performance/memory/
                                  paged_attention/backend/candidate_roles/compression/
                                  generation_defaults move with the model.
  IDENTITY stays with the NAME : roles.<role>.tier, description (purpose), system_prompt_suffix.
  ESCALATION follows STRENGTH  : chains/hints/fallbacks whose purpose is "reach the strongest
                                  model" retarget to architect_general (Flash-Next).

Idempotence: refuses to run on an already-transformed file (sentinel check).
"""
from __future__ import annotations

import sys
from pathlib import Path

PATH = Path(sys.argv[1])
SENTINEL = "ARCHSWAP-20260927"
text = PATH.read_text()
if SENTINEL in text:
    sys.exit(f"REFUSING: {PATH} already carries {SENTINEL}")
lines = text.split("\n")


def find_line(exact: str, start: int = 0, end: int | None = None) -> int:
    hits = [i for i in range(start, end or len(lines)) if lines[i] == exact]
    if len(hits) != 1:
        sys.exit(f"anchor {exact!r} in [{start},{end}) matched {len(hits)} times")
    return hits[0]


def top(name: str) -> int:
    return find_line(f"{name}:")


# ── 1. server_mode: swap the two host-row KEYS (rows stay attached to their process) ──
sm = top("server_mode")
sm_end = top("worker_pool")
g = find_line("  architect_general:", sm, sm_end)
c = find_line("  architect_critic:", sm, sm_end)
lines[g] = "  architect_critic:"
lines[c] = "  architect_general:"
BANNER_27B = [
    "  # ── ARCHSWAP-20260927 (operator-decided 2026-09-27) ──────────────────────────────────────",
    "  # THIS ROW IS NOW `architect_critic`. It is the SAME :8083 MI210 process (Qwen3.8-27B Q8) that",
    "  # was `architect_general` until 2026-09-27; only the role LABEL moved. Every fact below —",
    "  # serving_shape, chat_template_kwargs (thinking ON, reasoning_effort medium: a property of THIS",
    "  # model's template, ruling C1), the terse template, shared_with, evidence — is a fact about this",
    "  # PROCESS and moved with it. Dated comments below that say `architect_general` describe this row",
    "  # BEFORE the swap. It still HOSTS coder_escalation and ingest_long_context (operator default:",
    "  # the aliases stay on the fast GPU process). The critic is reached by direct request and by the",
    "  # critique_plan consult skill; the pydantic-graph never reaches it (RI-21, deliberately open).",
]
BANNER_FN = [
    "  # ── ARCHSWAP-20260927 (operator-decided 2026-09-27) ──────────────────────────────────────",
    "  # THIS ROW IS NOW `architect_general`. It is the SAME :8074 CPU process (Qwen3.8-Flash-Next",
    "  # UD-IQ4_XS, full 0-95 instance, holds ALL FOUR CPU region locks) that was `architect_critic`",
    "  # until 2026-09-27; only the role LABEL moved. Purpose: the graph's existing escalation paths",
    "  # (CoderEscalationNode/ArchitectNode -> Role.ARCHITECT_GENERAL, chat_delegation) now reach the",
    "  # strongest model with no new routing code (arm A2 of the operator's thesis experiment).",
    "  # Every fact below — recipe, threads, env, kv_quant, chat_template_kwargs (thinking OFF: this",
    "  # model's measured serving config), evidence — is a fact about this PROCESS and moved with it.",
    "  # Dated comments below that say `architect_critic` describe this row BEFORE the swap.",
    "  # ⚠ DAR-LAT-3h/3i (the :8074 thread/env reconciliation) now apply to THIS role name.",
    "  # ⚠ D2 HAZARD NOW REACHABLE BY ROUTINE TRAFFIC: graph escalation into architect_general can",
    "  #   summon the whole-machine CPU region lock (the D2 ruling kept that behind explicit_request).",
    "  #   Accepted by the operator's swap decision; recorded in the package, not mitigated here.",
]
# insert higher index first so the lower index stays valid
for idx, banner in sorted(((g, BANNER_27B), (c, BANNER_FN)), key=lambda t: -t[0]):
    lines[idx:idx] = banner

# ── 2. roles: swap the KEYS, then restore per-role IDENTITY fields ──
ro = top("roles")
ro_end = top("process_layout")
rg = find_line("  architect_general:", ro, ro_end)
rc = find_line("  architect_critic:", ro, ro_end)
assert rg < rc


rg_stop = rc
rc_stop = find_line("  architect_coding:", rc, ro_end)
gen_row = lines[rg:rg_stop]
cri_row = lines[rc:rc_stop]


def extract(row: list[str], key: str) -> tuple[int, int]:
    s = [i for i, ln in enumerate(row) if ln.startswith(f"    {key}:")]
    assert len(s) == 1, (key, s)
    s = s[0]
    t = s + 1
    while t < len(row) and row[t].startswith("      "):
        t += 1
    return s, t


def replace_field(row: list[str], key: str, new: list[str]) -> list[str]:
    s, t = extract(row, key)
    return row[:s] + new + row[t:]


gen_sps = gen_row[slice(*extract(gen_row, "system_prompt_suffix"))]
cri_sps = cri_row[slice(*extract(cri_row, "system_prompt_suffix"))]
cri_desc = cri_row[slice(*extract(cri_row, "description"))]

# new architect_general = the Flash-Next row (was critic) with general's identity
new_gen = ["  architect_general:"] + [
    "    # ── ARCHSWAP-20260927: this row is the Qwen3.8-Flash-Next model block that was",
    "    # roles.architect_critic until 2026-09-27. MODEL facts (model, acceleration, performance,",
    "    # memory, paged_attention, candidate_roles, compression point, generation_defaults) moved",
    "    # WITH the model; the role's IDENTITY (tier A, purpose, system_prompt_suffix) stayed here.",
    "    # RegistryLoader reads model + acceleration from THIS block; server_mode.architect_general",
    "    # (the :8074 row) holds port/slots/launch config. Keep in sync.",
] + cri_row[1:]
new_gen = replace_field(new_gen, "tier", ["    tier: A"])
new_gen = replace_field(new_gen, "description", [
    '    description: "System architecture, invariants, acceptance tests - emits IR only. 2026-09-27'
    " ARCHSWAP (operator-decided): served by Qwen3.8-Flash-Next UD-IQ4_XS on the full CPU instance"
    " (:8074, the process that was architect_critic) so the graph's existing escalation paths reach"
    " the strongest model. Top of the escalation chain. The 27B's E-7 stamps moved with the 27B to"
    ' roles.architect_critic."',
])
new_gen = replace_field(new_gen, "system_prompt_suffix", gen_sps)

# new architect_critic = the 27B row (was general) with critic's identity
new_cri = ["  architect_critic:"] + [
    "    # ── ARCHSWAP-20260927: this row is the Qwen3.8-27B Q8 model block that was",
    "    # roles.architect_general until 2026-09-27. MODEL facts moved WITH the model; the role's",
    "    # IDENTITY (tier B, purpose, system_prompt_suffix) stayed here. Dated comments below that",
    "    # say `architect_general` / `this role's :8083 process` describe the row BEFORE the swap;",
    "    # the :8083 process is now server_mode.architect_critic and still hosts coder_escalation",
    "    # and ingest_long_context.",
] + gen_row[1:]
new_cri = replace_field(new_cri, "tier", ["    tier: B"])
new_cri = replace_field(new_cri, "description", [
    '    description: "' + cri_desc[0].split("description:", 1)[1].strip() + " — 2026-09-27 ARCHSWAP (operator-decided), served by Qwen3.8-27B Q8 on the MI210 (:8083, the process"
    " that was architect_general; host of coder_escalation + ingest_long_context). Reached by direct"
    " request and the critique_plan consult skill; not an escalation target.\""
] if len(cri_desc) == 1 else sys.exit("critic description is multi-line; unexpected"))
new_cri = replace_field(new_cri, "system_prompt_suffix", cri_sps)
lines[rg:rc_stop] = new_gen + new_cri

text = "\n".join(lines)

# ── 3. targeted restatements elsewhere (exact, counted) ──
REPL: list[tuple[str, str, int]] = [
    # alias rows: host is now architect_critic
    ("    alias_of: architect_general   # documentation; the load-bearing binding is server_mode.architect_general.shared_with",
     "    alias_of: architect_critic    # documentation; the load-bearing binding is server_mode.architect_critic.shared_with (ARCHSWAP-20260927: the :8083 host row was renamed architect_general -> architect_critic)", 1),
    ("    alias_of: architect_general    # documentation; the load-bearing binding is\n                                   # server_mode.architect_general.shared_with",
     "    alias_of: architect_critic     # documentation; the load-bearing binding is\n                                   # server_mode.architect_critic.shared_with (ARCHSWAP-20260927)", 1),
    ("      type: none  # alias: no own draft; inherits architect_general's draft-mtp recipe\n      inherits_spec_from: architect_general",
     "      type: none  # alias: no own draft; inherits the :8083 host's draft-mtp recipe\n      inherits_spec_from: architect_critic   # ARCHSWAP-20260927: :8083 host renamed", 1),
    ("      type: none\n      inherits_spec_from: architect_general\n      spec_type: draft-mtp        # the INHERITED recipe",
     "      type: none\n      inherits_spec_from: architect_critic   # ARCHSWAP-20260927: :8083 host renamed\n      spec_type: draft-mtp        # the INHERITED recipe", 1),
    ("      inherits_spec_from: architect_general\n      lookup: false\n      corpus_retrieval: true\n    performance:",
     "      inherits_spec_from: architect_critic   # ARCHSWAP-20260927: :8083 host renamed\n      lookup: false\n      corpus_retrieval: true\n    performance:", 1),
    ("      inherits_from: architect_general\n",
     "      inherits_from: architect_critic   # ARCHSWAP-20260927: the :8083 27B's evidence now lives under roles.architect_critic\n", 1),
    ("      shared_gguf_with: architect_general\n",
     "      shared_gguf_with: architect_critic   # ARCHSWAP-20260927: :8083 host renamed\n", 1),
    ("      type: none\n      inherits_spec_from: architect_general\n      spec_type: draft-mtp\n",
     "      type: none\n      inherits_spec_from: architect_critic   # ARCHSWAP-20260927: :8083 host renamed\n      spec_type: draft-mtp\n", 1),
    # alias descriptions
    ('onto architect_general\'s :8083 GPU process; alias, launches no server of its own.',
     "onto architect_general's :8083 GPU process; alias, launches no server of its own. 2026-09-27 ARCHSWAP: the :8083 host role is now architect_critic (same process, same model).", 1),
    ('    description: "Long-context ingest alias — resolves to the architect_general process',
     '    description: "Long-context ingest alias — resolves to the :8083 process (architect_general until 2026-09-27, architect_critic since the ARCHSWAP)', 1),
    ('    description: "Large document ingestion, synthesis & summarization. 2026-09-22: ALIAS on\n      architect_general\'s :8083 MI210 process',
     '    description: "Large document ingestion, synthesis & summarization. 2026-09-22: ALIAS on\n      the :8083 MI210 process (host role architect_critic since the 2026-09-27 ARCHSWAP)', 1),
    # escalation chains: terminal hop follows STRENGTH (Flash-Next = architect_general)
    ("    - worker_general\n    - frontdoor\n    - architect_general\n    - architect_critic  # terminal hop 2026-07-31: boosted reasoning\n",
     "    - worker_general\n    - frontdoor\n    - architect_critic   # ARCHSWAP-20260927: the 27B middle hop, now under its new label\n    - architect_general  # ARCHSWAP-20260927: terminal hop = Flash-Next (was architect_critic)\n", 1),
    ("    description: Boosted-reasoning escalation — terminal hop is the 122B adversarial critic\n    chain:\n    - frontdoor\n    - architect_general\n    - architect_critic\n",
     "    description: Boosted-reasoning escalation — terminal hop is Qwen3.8-Flash-Next (architect_general since the 2026-09-27 ARCHSWAP; was the critic)\n    chain:\n    - frontdoor\n    - architect_critic   # ARCHSWAP-20260927: the 27B middle hop, now under its new label\n    - architect_general  # ARCHSWAP-20260927: terminal = Flash-Next, the whole-machine-lock holder (D2 triggers unchanged)\n", 1),
    # routing hints: "reach the strongest model" follows strength; critique stays with the critic
    ("- if: '''boosted reasoning'' in objective or ''deep reasoning'' in objective'\n  use:\n  - architect_critic\n",
     "- if: '''boosted reasoning'' in objective or ''deep reasoning'' in objective'\n  use:\n  - architect_general   # ARCHSWAP-20260927: strongest model (Flash-Next) — was architect_critic\n", 1),
    ("- if: escalation.max_level == 'B3' and task_type == 'code'\n  use:\n  - architect_critic\n- if: escalation.max_level == 'B3' and 'reasoning' in objective\n  use:\n  - architect_critic\n",
     "- if: escalation.max_level == 'B3' and task_type == 'code'\n  use:\n  - architect_general   # ARCHSWAP-20260927: B3 = strongest model (Flash-Next) — was architect_critic\n- if: escalation.max_level == 'B3' and 'reasoning' in objective\n  use:\n  - architect_general   # ARCHSWAP-20260927: B3 = strongest model (Flash-Next) — was architect_critic\n", 1),
    # external API hard-task fallback follows the big model
    ("      fallback_role: architect_critic  # 2026-07-31 RETARGETED.",
     "      fallback_role: architect_general  # ARCHSWAP-20260927: follows the big model (Flash-Next) back to\n                                       # architect_general. History: 2026-07-31 RETARGETED.", 1),
    # catalogue rows: PRIMARY role follows the model
    ("    - architect_critic       # 2026-09-22: PRIMARY, :8074 CPU\n    - ingest_long_context    # CANDIDATE only. Served by architect_general's :8083 (ruling C2, 2026-09-22), not :8074\n",
     "    - architect_general      # 2026-09-27 ARCHSWAP: PRIMARY, :8074 CPU (was architect_critic 2026-09-22..27)\n    - ingest_long_context    # CANDIDATE only. Served by the :8083 27B (architect_critic since the 2026-09-27 ARCHSWAP; ruling C2), not :8074\n", 1),
    ("    - architect_general   # 2026-08-20: PRIMARY, :8083 MI210 ROCm0\n    - coder_escalation    # 2026-08-20: alias on the same :8083 process\n",
     "    - architect_critic    # 2026-09-27 ARCHSWAP: PRIMARY, :8083 MI210 ROCm0 (was architect_general 2026-08-20..09-27)\n    - coder_escalation    # 2026-08-20: alias on the same :8083 process\n", 1),
    # process_layout grouping comment + list annotations
    ("  #   :8074                = architect_critic ALONE (Qwen3.8-Flash-Next)\n  #   :8083                = architect_general + coder_escalation + ingest_long_context\n",
     "  #   :8074                = architect_general ALONE (Qwen3.8-Flash-Next) — ARCHSWAP-20260927, was architect_critic\n  #   :8083                = architect_critic + coder_escalation + ingest_long_context — ARCHSWAP-20260927, host was architect_general\n", 1),
    ("  - architect_general     # MOVED from warm_mmap; GPU-resident on ROCm0, :8083\n  - coder_escalation      # MOVED off :8070 — alias on architect_general's :8083\n  - architect_critic      # 2026-09-22: Qwen3.8-Flash-Next, CPU, :8074, tier hot, SOLE role\n",
     "  - architect_general     # ARCHSWAP-20260927: Qwen3.8-Flash-Next, CPU, :8074, tier hot, SOLE role\n  - coder_escalation      # alias on the :8083 27B (host architect_critic since ARCHSWAP-20260927)\n  - architect_critic      # ARCHSWAP-20260927: Qwen3.8-27B Q8, GPU-resident on ROCm0, :8083 host\n", 1),
    ("  - ingest_long_context   # 2026-09-22: alias on architect_general's :8083 (was CPU :8085)\n",
     "  - ingest_long_context   # 2026-09-22: alias on the :8083 27B (host architect_critic since ARCHSWAP-20260927)\n", 1),
    # server_mode port-map header comment
    ("  #   8070 frontdoor (+worker_summarize alias) · 8074 architect_critic (NEW 2026-07-31)\n  #   8083 architect_general (+coder_escalation alias)",
     "  #   8070 frontdoor (+worker_summarize alias) · 8074 architect_general (ARCHSWAP-20260927; was architect_critic)\n  #   8083 architect_critic (+coder_escalation, +ingest_long_context aliases; ARCHSWAP-20260927, was architect_general)", 1),
    # runtime_defaults timeout comments (values unchanged: both 600)
    ("      architect_general: 600   # 2026-07-31: REPOINTED",
     "      architect_general: 600   # ARCHSWAP-20260927: now Qwen3.8-Flash-Next CPU :8074 (value unchanged). History: 2026-07-31: REPOINTED", 1),
    ("      architect_critic: 600    # 122B MoE hybrid, inherited from architect_general 2026-07-31.",
     "      architect_critic: 600    # ARCHSWAP-20260927: now Qwen3.8-27B Q8 GPU :8083 (value unchanged). History: 122B MoE hybrid, inherited from architect_general 2026-07-31.", 1),
    ("      coder_escalation: 120    # 2026-07-31: alias on architect_general's :8083 MI210 27B",
     "      coder_escalation: 120    # 2026-07-31: alias on the :8083 MI210 27B (host architect_critic since ARCHSWAP-20260927)", 1),
    # voice pipeline requirement: the GPU reasoning role is now architect_critic
    ("voice turns must reason on\n    # the GPU (architect_general), which is the voice-pipeline requirement.",
     "voice turns must reason on\n    # the GPU (the :8083 27B — architect_critic since ARCHSWAP-20260927; was architect_general), which is\n    # the voice-pipeline requirement.", 1),
]
for old, new, n in REPL:
    k = text.count(old)
    if k != n:
        sys.exit(f"replacement anchor matched {k} (want {n}): {old[:90]!r}")
    text = text.replace(old, new)

PATH.write_text(text)
print(f"ok: {PATH}")
