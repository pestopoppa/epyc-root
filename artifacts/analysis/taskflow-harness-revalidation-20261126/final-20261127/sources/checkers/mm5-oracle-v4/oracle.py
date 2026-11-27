"""Run the V4 contract with unchanged offline V2 evaluator containment."""
import hashlib
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
V2 = HERE.parent / "mm5-oracle-v2"
WRAPPER_SHA = "6619c29e02b97122137357b410da8968344fcf55aa01033a61e55dc611804099"
CHECKER_SHA = "c08d80d2cd4c50599465c75687cc17ea83ebe5632d3ce768b970cc358da48bdd"


def verify(path, sha):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != sha:
        raise RuntimeError(f"sealed evaluator input changed: {path}")
    return content


def main():
    original = V2 / "oracle.py"
    source = verify(original, WRAPPER_SHA).decode()
    verify(V2 / "vision_contract_v2.py", CHECKER_SHA)
    # Preserve V2 image, limits, dependencies, timeouts and mount permissions.
    # Expose the same V2 checker as a module and invoke the new entrypoint.
    old = (
        'f"type=bind,source={HERE / \'vision_contract_v2.py\'},target=/v2.py,readonly",'
    )
    new = (
        'f"type=bind,source={HERE / \'vision_contract_v2.py\'},target=/vision_contract_v2.py,readonly",\n'
        f'        "--mount", {f"type=bind,source={HERE / "vision_contract_v4.py"},target=/vision_contract_v4.py,readonly"!r},'
    )
    entry = '"/v2.py", "/case"'
    if source.count(old) != 1 or source.count(entry) != 1:
        raise RuntimeError("pinned V2 wrapper does not match the versioned entrypoint patch")
    source = source.replace(old, new).replace(entry, '"/vision_contract_v4.py", "/case"')
    exec(compile(source, str(original), "exec"), {"__name__": "__main__", "__file__": str(original)})


if __name__ == "__main__":
    main()
