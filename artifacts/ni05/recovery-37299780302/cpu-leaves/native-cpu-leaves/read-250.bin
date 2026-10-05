import importlib.util
import json
import tempfile
from pathlib import Path

SCRIPT = (
    Path(__file__).parents[2] / "scripts/benchmark/decontaminate_against_embeddings_training.py"
)
spec = importlib.util.spec_from_file_location("decontam", SCRIPT)
decontam = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(decontam)


def test_xxhash64_reference_vectors_and_normalization():
    assert f"{decontam.xxhash64(b''):016x}" == "ef46db3751d8e999"
    assert f"{decontam.xxhash64(b'hello'):016x}" == "26c7827d889f6da3"
    assert decontam.normalize(" HÉLLO\tWorld ") == "héllo world"


def test_exact_then_13gram_filter():
    words = " ".join(f"w{i}" for i in range(26))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        training, evaluation, output = root / "train.jsonl", root / "eval.jsonl", root / "out.jsonl"
        training.write_text(json.dumps({"text": words}) + "\n")
        evaluation.write_text(
            "\n".join(
                json.dumps(row)
                for row in (
                    {"text": words},
                    {"text": " ".join(f"w{i}" for i in range(13))},
                    {"text": "clean unrelated sample"},
                )
            )
            + "\n"
        )
        report = decontam.run(training, evaluation, output, ["text"])
        assert report["rejected"] == 2 and report["kept"] == 1
        assert json.loads(output.read_text())["text"] == "clean unrelated sample"
