"""Run a hash-bound prior oracle with only its contained CPU affinity adapted."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REVIEW = HERE / "REVIEW.json"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise RuntimeError(f"reviewed bytes changed: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    review = json.loads(REVIEW.read_bytes())
    row = review["rows"][args.id]
    for name, expected in row["input_sha256"].items():
        verify(Path(name), expected)
    if not args.execute:
        print(json.dumps({"id": args.id, "verified_inputs": len(row["input_sha256"]), "inference_calls": 0}))
        return
    oracle = Path(row["oracle"])
    lane = Path(row["lane"])
    if row["kind"] == "python":
        sys.path.insert(0, review["legacy_package"])
        from prepare import file_map
        expected = json.loads(Path(row["case"]).read_bytes())["baseline_files"]
        for name, change in row["changed_files"].items():
            if change is None:
                expected.pop(name)
            else:
                expected[name] = change
        if file_map(lane) != expected:
            raise RuntimeError("complete frozen grade lane differs from the baseline plus reviewed paths")
        source = oracle.read_text()
        old, new = "'--cpuset-cpus', '84-87'", "'--cpuset-cpus', '180-183'"
        if source.count(old) != 1:
            raise RuntimeError("unexpected contained oracle affinity location")
        # Preserve the sealed evaluator and its containment, changing only the CPU list.
        command = [sys.executable, "-IB", "-c",
                   "import sys; p=sys.argv[1]; lane=sys.argv[2]; sys.argv=[p,lane]; "
                   "exec(compile(sys.stdin.read(),p,'exec'),{'__name__':'__main__','__file__':p})",
                   str(oracle), str(lane)]
        proc = subprocess.run(command, input=source.replace(old, new).encode(),
                              capture_output=True, timeout=185)
    else:
        proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)],
                              capture_output=True, timeout=30)
    out = HERE / "grades" / args.id
    out.mkdir(parents=True)
    (out / "stdout.log").write_bytes(proc.stdout)
    (out / "stderr.log").write_bytes(proc.stderr)
    (out / "RESULT.json").write_text(json.dumps({
        "id": args.id, "rc": proc.returncode, "oracle_sha256": row["input_sha256"][str(oracle)],
        "candidate_patch_sha256": row["candidate_patch_sha256"],
        "cpu_affinity": "180-183", "only_contained_affinity_adapted": row["kind"] == "python",
        "raw_results_preserved": True, "source_recommendation": row["source_recommendation"],
        "stdout_sha256": digest(out / "stdout.log"), "stderr_sha256": digest(out / "stderr.log"),
        "model_calls": 0,
    }, indent=2) + "\n")
    for name, expected in row["input_sha256"].items():
        verify(Path(name), expected)
    print(json.dumps({"id": args.id, "rc": proc.returncode, "result": str(out / "RESULT.json")}))
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
