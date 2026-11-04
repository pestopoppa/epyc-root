"""PR2d-backfill: author `depends_on` where the counterfactual test actually passes.

The 60-edge sample labelled 11 edges "evidential". Applying the authoring test to each one --
*if that entry's claim were retracted tomorrow, would a claim in THIS entry have to change?* --
only four survive. "Evidential" in the sample meant an intellectual dependency was in the
neighbourhood; `depends_on` demands that a specific claim moves. Recording that gap is the point:
the 18% figure is an upper bound on authorable dependencies, not an estimate of them.

One of the four runs the OPPOSITE way to the citation that suggested it: intake-1067 (2020) cannot
depend on intake-1043 (2021); the RAMiCS paper depends on the Gradel-Tannen construction.
"""
import re
import sys

import yaml

PATH = "research/intake_index.yaml"
APPLY = "--apply" in sys.argv

DEPS = {
    "intake-1062": [{
        "entry": "intake-1050",
        "claim_index": 4,
        "why": ("Our claim that the alpha/beta/gamma models of CCE and BRD are ORIGINAL to the 2009 "
                "chapter is an assertion about what the 2007 Carneades paper does NOT contain. If "
                "intake-1050's content record is wrong, this originality claim is wrong."),
    }],
    "intake-1043": [{
        "entry": "intake-1067",
        "claim_index": 2,
        "why": ("Theorem 17 characterizes lfp/gfp as sums over derivation trees proved in "
                "S-infinity[A] and 'transported by universal property' — that universal property is "
                "Proposition 30 of Gradel & Tannen (intake-1067). Retract the construction and the "
                "transport step has nothing to stand on. Note the direction: the citation edge runs "
                "1067 -> 1043, but 1067 is 2020 and 1043 is 2021, so the dependency is the reverse."),
    }],
    "intake-976": [{
        "entry": "intake-972",
        "claim_index": 1,
        "why": ("The 6.11% figure is computed across a named corpus of benchmarks that includes "
                "Mercury (intake-972). If Mercury's record is retracted or its results change, the "
                "denominator of this measurement changes with it."),
    }],
    "intake-982": [{
        "entry": "intake-939",
        "claim_index": 1,
        "why": ("This claim is ABOUT intake-939 — that its sqrt(2) citation is faithful and properly "
                "hedged, and that it does not itself over-claim. If intake-939's claims are "
                "retracted or restated, this assessment of them is no longer about anything."),
    }],
}

# Not authored, with the reason, so the decision is legible rather than a silent drop.
DECLINED = {
    ("intake-1016", "intake-451"): "the 'released refiner' claim is about Continual Harness's own "
                                   "release, not the Meta-Harness repo; cannot establish without a re-read",
    ("intake-1042", "intake-1038"): "the circuit-depth results hold for absorptive semirings "
                                    "generally; they do not rest on the Deletion Property",
    ("intake-946", "intake-956"): "the probe FAILED end-to-end decode and its author is blocked, so "
                                  "it establishes nothing the card claims rest on",
    ("intake-960", "intake-964"): "the perf_knowledge ridge-point error was found by internal "
                                  "inconsistency (arch.md vs memory.md), not against the oracle",
    ("intake-970", "intake-953"): "ENAMEL's right-censoring primitive stands independently of "
                                  "SWE-fficiency; the relationship is audit, not dependency",
    ("intake-985", "intake-976"): "CodeContests+ substitutes for DMC-Optim's test-construction half, "
                                  "not for anything in intake-976",
    ("intake-989", "intake-990"): "the corroboration claim targets MemHarness, not Dark Room; the "
                                  "edge that would carry it points elsewhere",
}

raw = open(PATH).read()
before = yaml.safe_load(raw)
e = {x["id"]: x for x in before}
for eid, deps in DEPS.items():
    assert eid in e, eid
    assert not e[eid].get("depends_on"), f"{eid} already has depends_on"
    for dep in deps:
        assert dep["entry"] in e, dep["entry"]
        n = len(e[eid].get("key_claims") or [])
        assert 0 <= dep["claim_index"] < n, (eid, dep["claim_index"], n)

lines = raw.splitlines(keepends=True)
ENTRY = re.compile(r"^- id:\s*(\S+)\s*$")
out, current, added = [], None, 0
for ln in lines:
    m = ENTRY.match(ln)
    if m:
        if current in DEPS:
            block = yaml.safe_dump({"depends_on": DEPS[current]}, default_flow_style=False,
                                   allow_unicode=True, width=10**6, sort_keys=False)
            out.extend("  " + x + "\n" for x in block.splitlines())
            added += 1
        current = m.group(1)
    out.append(ln)
if current in DEPS:
    block = yaml.safe_dump({"depends_on": DEPS[current]}, default_flow_style=False,
                           allow_unicode=True, width=10**6, sort_keys=False)
    out.extend("  " + x + "\n" for x in block.splitlines())
    added += 1

text = "".join(out)
after = yaml.safe_load(text)
got = {x["id"]: x for x in after}
assert len(after) == len(before)
for eid, deps in DEPS.items():
    assert got[eid]["depends_on"] == deps, eid
for x in before:
    for k, v in x.items():
        assert got[x["id"]][k] == v, (x["id"], k)

print(f"depends_on authored on {added} entries "
      f"({sum(len(v) for v in DEPS.values())} edges); {len(DECLINED)} declined")
for (s, t), why in DECLINED.items():
    print(f"  declined {s} -> {t}: {why}")
if APPLY:
    open(PATH, "w").write(text)
    print("written")
else:
    print("(dry run)")
