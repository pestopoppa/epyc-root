#!/usr/bin/env python3
"""Full-question-up-front, twelve-document dependent composite variant.

No model calls on import. Pinned producer rendering/scoring/driver are reused;
changed episode, prompt and execution contract are content-bound in every cell.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

# Sibling is retained with this wrapper when preparing a row outside the lane.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import repl_contract_variant as base

VARIANT = 'upfront-dependent-research-v1'

EXTENSION = r'''
_original_episode = build_episode

def build_episode(i):
    import hashlib
    ep = _original_episode(i)
    rng = random.Random(f"upfront-dependent-v1:{i}")
    ids = [hashlib.sha256(f"upfront-dependent-v1:{i}:{j}".encode()).hexdigest()[:16] for j in range(12)]
    grouped = {kind: [d["text"] for d in ep["docs"] if d["kind"] == kind]
               for kind in ("roster", "site", "budget", "profile", "region")}
    adjustments = [rng.randrange(-20, 21) for _ in range(6)]
    packets = [grouped["roster"], grouped["site"], grouped["budget"]]
    projects = [d["title"].split(": ", 1)[1] for d in ep["docs"] if d["kind"] == "roster"]
    for j, adjustment in enumerate(adjustments):
        lines = [f"project {p} | audit_{j+1} adjustment_k {adjustment if p == ep['project'] else rng.randrange(-20,21)}"
                 for p in projects]
        rng.shuffle(lines)
        packets.append(lines)
    packets += [grouped["profile"], grouped["region"], ["RESEARCH COMPLETE: all twelve documents retrieved."]]
    ep["docs"] = [{"id": doc_id, "title": f"Research packet {j+1}/12",
                   "text": "\n".join(lines + ([f"NEXT_DOCUMENT={ids[j+1]}"] if j < 11 else []))}
                  for j, (doc_id, lines) in enumerate(zip(ids, packets))]
    ep["expected"]["loaded_budget_k"] += sum(adjustments)
    ep["schema"] = "epyc.repl_upfront_episode.v1"
    ep["questions"] = [
        f"Q1: Who leads project {ep['project']}? Preserve the current lead, not the previous lead.",
        f"Q2: Which site and region host project {ep['project']}? Preserve the current site.",
        f"Q3: What is project {ep['project']}'s approved budget_k (not requested_k)?",
        "Q4: Find that lead's hourly rate in the profile packet (packet 10).",
        "Q5: Find that region's cost multiplier percent in the region packet (packet 11).",
        f"Q6: In packets 4-9 find the six adjustment_k values for project {ep['project']}. "
        "Compute loaded_budget_k = budget_k * mult_pct // 100 + the sum of those six adjustments.",
        "Q7: After retrieving all twelve packets, submit FINAL with exactly these seven keys: "
        "lead, site, region, budget_k, lead_rate, mult_pct, loaded_budget_k. "
        "Use strings for lead/site/region and integers for the rest.",
        f"Start with read('{ids[0]}'). Each retrieved packet supplies NEXT_DOCUMENT for the next read.",
    ]
    return ep

INTRO = """You are researching a local frozen document corpus in a Python REPL.
The COMPLETE research question is below from turn 1. No later question will be revealed.
Packets form a dependent chain: roster, site, budget, six project audit adjustments,
lead profiles, region factors, and closeout. Later lookups and the final calculation
need early facts. Retrieve all twelve packets before FINAL; earlier submissions are
rejected with feedback. The REPL permits ONE read(doc_id) per executed cell, in chain
order. You cannot fetch a later packet in the same cell. search is unavailable.
Variables persist: preserve facts and next-document IDs in variables or notes as you
work. Earlier outputs may be abbreviated; the newest output is shown in full.
Only your final seven-field dict is graded. FINAL is a function; do not assign to it.

Complete research question:
{qs}

History:
{hist}
This is turn {t} of at most {tmax}. Reply with exactly one ```python code block.
"""
'''

READ_GATE = '''cursor = 0
read_this_cell = False
def search(term):
    raise RuntimeError("search unavailable: follow read(doc_id) chain")
def read(doc_id):
    global cursor, read_this_cell
    if read_this_cell:
        raise RuntimeError("one document per cell; read the next document in a later turn")
    if cursor >= len(docs) or str(doc_id) != docs[cursor]["id"]:
        raise KeyError("expected the next document in the chain; no packet retrieved")
    d = docs[cursor]
    cursor += 1
    read_this_cell = True
    return d["title"] + "\\n" + d["text"]
'''


def upfront_fixture(text):
    text = base.replace_once(text, 'MAX_TURNS = 9', 'MAX_TURNS = 16')
    text = base.replace_once(text, 'ep["questions"][: min(t, len(ep["questions"]))]', 'ep["questions"]')
    # Replace runner retrieval functions, preserving execution/persistence semantics.
    start = text.index('def search(term):', text.index('_RUNNER ='))
    end = text.index('finals = []', start)
    text = text[:start] + READ_GATE + text[end:]
    text = base.replace_once(text, 'for code in spec["blocks"]:\n',
                             'for code in spec["blocks"]:\n    read_this_cell = False\n')
    text = base.replace_once(text, '"assigned": assigned}',
                             '"assigned": assigned, "research_complete": cursor == len(docs)}')
    text = base.replace_once(text, '        turns.append({"code": code, "obs": obs, "reply": reply})\n        if r["final"]:',
                             '        if r["final"] and not r["research_complete"]:\n'
                             '            obs += "\\nError: premature FINAL rejected; retrieve all twelve packets first."\n'
                             '            turns.append({"code": code, "obs": obs, "reply": reply})\n'
                             '            continue\n'
                             '        turns.append({"code": code, "obs": obs, "reply": reply})\n'
                             '        if r["final"]:')
    # Original reference policies assume progressive Q1..Q7; refuse rather than
    # silently produce a meaningless pilot/mock result with those policies.
    text += EXTENSION + '''

def reference_policy(*args):
    raise ValueError("upfront variant requires its own reference policy; old progressive pilot/mock is invalid")
'''
    return text


def load_driver():
    return base.load_driver(fixture_transform=upfront_fixture, variant=VARIANT,
                            extra_binding={'upfront_wrapper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def main(argv=None):
    driver, binding = load_driver()
    return base.run_bound(driver, binding, list(sys.argv[1:] if argv is None else argv))


if __name__ == '__main__':
    sys.exit(main())
