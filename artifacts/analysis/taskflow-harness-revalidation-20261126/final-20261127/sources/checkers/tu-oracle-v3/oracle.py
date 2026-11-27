"""Run the TU contract with a controlled missing-launcher phase in the pinned evaluator."""
import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
CASE = HERE.parent / "coverage/legacy-comparison/cases/TU-GR-1"
WRAPPER_SHA = "8385fe0c79b0726a0b5f4d7f5ace1b7c9cf9779445a96b1733087907560b62c2"
ENV_SHA = "65abb3f4db8cc69ac0a53eca561fa9bc71fbb92dc832ff913f16d125e5289cc2"


def pinned(path, expected):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise RuntimeError(f"sealed evaluator input changed: {path}")
    return content


def main():
    original = CASE / "oracle.py"
    source = pinned(original, WRAPPER_SHA).decode()
    pinned(CASE / "task-env.json", ENV_SHA)
    old_mount = "{SHARED / \"evaluator-support\"},target=/oracles,readonly"
    new_mount = "{_V3_CHECKER},target=/oracles/tu_grader_isolation.py,readonly"
    old_affinity = "'--cpuset-cpus', '84-87'"
    new_affinity = "'--cpuset-cpus', '180-183'"
    for old, new in ((old_mount, new_mount), (old_affinity, new_affinity)):
        if source.count(old) != 1:
            raise RuntimeError("unexpected source change in sealed TU wrapper")
        source = source.replace(old, new)
    exec(compile(source, str(original), "exec"), {
        "__name__": "__main__", "__file__": str(original), "_V3_CHECKER": HERE / "tu_grader_isolation.py",
    })


if __name__ == "__main__":
    main()
