"""PR1b: the machine anchoring pass must refuse more readily than it reaches.

A missing anchor costs recall and a later run recovers it. A confident wrong anchor is a fabricated
citation with a hash on it — the failure this whole program was created over. So the tests that
matter are the refusals, and the one that matters most is the negative control: a claim that simply
is not in the document must produce nothing.

The grade cap is tested in test_vidya_alias.py; here we only check that the anchor carries the
`located_by: machine` stamp that triggers it.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from canonical import normalized_quote  # noqa: E402
from machine_anchor import anchor_entry, best_span, terms  # noqa: E402

DOC = (
    "We introduce a chunked Gated-DeltaNet recurrence for long-context decoding. "
    "The state-recomputation kernel is written to a fixed 64-wide block dimension throughout. "
    "Our evaluation covers three model families and two hardware targets. "
    "Throughput improves by 18 percent on the long-context benchmark relative to the baseline. "
    "We leave multi-node scaling to future work."
)


def entry(claims, **kw):
    base = {"id": "intake-900", "url": "https://example.com/paper", "key_claims": claims}
    base.update(kw)
    return base


def test_a_claim_present_in_the_document_is_anchored():
    claims = ["The state-recomputation kernel uses a fixed 64-wide block dimension."]
    got = anchor_entry(entry(claims), document=DOC)
    assert len(got) == 1
    assert "64-wide block dimension" in got[0]["quote"]
    assert got[0]["located_by"] == "machine"


def test_the_quote_hash_is_over_the_normalized_span():
    claims = ["The state-recomputation kernel uses a fixed 64-wide block dimension."]
    a = anchor_entry(entry(claims), document=DOC)[0]
    expected = hashlib.sha256(normalized_quote(a["quote"]).encode("utf-8")).hexdigest()
    assert a["quote_sha256"] == expected


def test_negative_control_a_claim_not_in_the_document_anchors_nothing():
    """The load-bearing test. Reflow the document and this must still return nothing."""
    claims = ["The model was trained with reinforcement learning from human feedback on 40k prompts."]
    assert anchor_entry(entry(claims), document=DOC) == []


def test_a_generic_claim_is_refused_even_if_words_appear():
    """Too few distinctive terms to locate anything — matching on 'evaluation' proves nothing."""
    assert best_span("Our evaluation is thorough.", DOC) is None


def test_an_ambiguous_best_match_is_refused():
    """Two spans fitting equally well means the claim is paraphrased; picking one invents a location."""
    doc = ("The kernel uses a fixed 64-wide block dimension. "
           "Separately, the kernel uses a fixed 64-wide block dimension.")
    assert best_span("The kernel uses a fixed 64-wide block dimension.", doc) is None


def test_an_already_anchored_claim_is_left_alone():
    """A human anchor is never overwritten by a machine one."""
    e = entry(
        ["The state-recomputation kernel uses a fixed 64-wide block dimension."],
        claim_anchors=[{"claim_index": 0, "kind": "page-and-quote", "quote": "human-read span"}],
    )
    assert anchor_entry(e, document=DOC) == []


def test_an_entry_with_no_url_is_skipped():
    e = {"id": "intake-901", "url": None, "key_claims": ["anything at all here"]}
    assert anchor_entry(e, document=DOC) == []


def test_stopwords_do_not_count_as_distinctive():
    assert "the" not in terms("The results of the paper")
    assert "results" not in terms("The results of the paper")


# ---------------------------------------- numeric guard (added after the first real run)

def test_a_numeric_claim_needs_its_number_in_the_span():
    """intake-123: a claim of "1.835% WER" was anchored to a sentence that only NAMED the metric."""
    doc = ("Performance is measured by Word Error Rate (WER) for content consistency "
           "and Cosine Similarity for speaker similarity across all systems evaluated.")
    assert best_span("1.835% average WER, 0.789 speaker similarity", doc) is None


def test_a_span_whose_numbers_contradict_the_claim_is_refused():
    """intake-110: claim said 57-59% and 9-16 points; the span said 56% and 3.3 points.

    Anchoring that would pin a claim to text that refutes it — a fabricated citation carrying a
    checkable quote, which is worse than no anchor at all.
    """
    doc = ("On Qwen3-14B, CRISP cuts reasoning length by up to 56% on MATH-500 while improving "
           "MATH-500 accuracy by up to 3.3 points over the baseline configuration tested.")
    claim = "57-59% token reduction on MATH-500 while improving accuracy by 9-16 points"
    assert best_span(claim, doc) is None


def test_a_matching_number_still_anchors():
    doc = ("Throughput improves by 18 percent on the long-context benchmark, and the "
           "state-recomputation kernel keeps a fixed 64-wide block dimension throughout.")
    hit = best_span("Throughput improves by 18 percent on the long-context benchmark.", doc)
    assert hit is not None and "18 percent" in hit["quote"]


def test_a_year_is_not_a_magnitude():
    """Otherwise every claim mentioning 2024 anchors to a citation line."""
    from machine_anchor import magnitudes
    assert magnitudes("evaluated on AIME 2024 across runs") == set()
    assert magnitudes("improves by 3.3 points") == {"3.3"}


def test_a_non_numeric_claim_is_unaffected_by_the_guard():
    doc = ("The state-recomputation kernel is written to a fixed block dimension and the "
           "scheduler interleaves prefill with decode across the available devices.")
    assert best_span("The scheduler interleaves prefill with decode.", doc) is not None
