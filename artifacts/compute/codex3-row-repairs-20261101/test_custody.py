import hashlib
from pathlib import Path

def test_recovered_freeze():
    path = Path(__file__).with_name("requirements-freeze.txt")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "f133fc7fe76c72e24d294dfa1bee242d70375841959782ce78b80841cd0f9111"
