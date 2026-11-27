import json
from pathlib import Path

result = Path(__file__).resolve().parent / "out" / "run" / "RESULT.json"
raise SystemExit(0 if result.is_file() and json.loads(result.read_text()).get("complete") is True else 1)
