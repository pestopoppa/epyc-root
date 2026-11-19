import json
from pathlib import Path

from transformers import AutoTokenizer


def encode(model, count):
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
    prefix = Path("/pkt/corpus.txt").read_text()
    ids = tokenizer(prefix, add_special_tokens=False)["input_ids"]
    assert len(ids) >= count
    return ids[:count]


actual = encode("/model", 512)
historical = json.loads(Path("/pkt/prompts-historical.json").read_bytes())["parity"]
assert actual == historical, "current tokenizer no longer reproduces the historical 512-token input"
print(json.dumps({"native": actual, "smoke": encode("/smoke", 4096)}))
