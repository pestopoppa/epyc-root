from __future__ import annotations

from pathlib import Path

from scripts.kb_rag import eval_k7


def test_score_case_counts_each_file_once(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    c = tmp_path / "c.md"
    for path in (a, b, c):
        path.write_text("# doc\n")

    results = [
        {"file": str(c), "score": 0.9},
        {"file": str(a), "score": 0.8},
        {"file": str(a), "score": 0.7},
        {"file": str(b), "score": 0.6},
    ]

    scored = eval_k7.score_case([str(a), str(b)], results, cutoffs=(1, 3, 4))

    assert scored["found_count"] == 2
    assert scored["recall@1"] == 0.0
    assert scored["recall@3"] == 0.5
    assert scored["recall@4"] == 1.0
    assert scored["perfect@3"] is False
    assert scored["perfect@4"] is True
    assert scored["first_evidence_rank"] == 2
    assert scored["all_evidence_rank"] == 4


def test_evaluate_summarizes_config_and_protocol(tmp_path: Path) -> None:
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("# a\n")
    b.write_text("# b\n")

    cases = [
        {
            "id": "c1",
            "protocol": "hotpotqa_template",
            "query": "alpha",
            "resolved_evidence_files": [str(a)],
        },
        {
            "id": "c2",
            "protocol": "locomo_template",
            "query": "beta",
            "resolved_evidence_files": [str(a), str(b)],
        },
    ]
    configs = [eval_k7.EvalConfig("maxsim"), eval_k7.EvalConfig("rerank_w0.3", rerank=True)]

    def fake_query(text: str, **kwargs):
        if text == "alpha":
            return [{"file": str(a), "score": 1.0}]
        return [{"file": str(a), "score": 1.0}, {"file": str(b), "score": 0.9}]

    rows = eval_k7.evaluate(
        cases=cases,
        configs=configs,
        index_dir=tmp_path / "idx",
        top_k=2,
        cutoffs=(1, 2),
        query_fn=fake_query,
    )
    summary = eval_k7.summarize_rows(rows, cases, configs, cutoffs=(1, 2))

    assert len(rows) == 4
    assert summary["case_count"] == 2
    assert summary["protocol_counts"] == {
        "hotpotqa_template": 1,
        "locomo_template": 1,
    }
    assert summary["configs"]["maxsim"]["overall"]["mean_recall@1"] == 0.75
    assert summary["configs"]["maxsim"]["overall"]["mean_recall@2"] == 1.0
    assert summary["configs"]["maxsim"]["overall"]["perfect@2"] == "2/2"


def test_load_cases_normalizes_seed_schema(tmp_path: Path) -> None:
    evidence = tmp_path / "e.md"
    evidence.write_text("# evidence\n")
    case_file = tmp_path / "cases.json"
    case_file.write_text(
        """
        {
          "version": 1,
          "cases": [
            {
              "id": "case_a",
              "protocol": "hotpotqa_template",
              "query": "Where is evidence?",
              "evidence_files": ["%s"]
            }
          ]
        }
        """
        % evidence
    )

    cases, metadata = eval_k7.load_cases(case_file)

    assert metadata["version"] == 1
    assert cases[0]["id"] == "case_a"
    assert cases[0]["resolved_evidence_files"] == [str(evidence.resolve())]
