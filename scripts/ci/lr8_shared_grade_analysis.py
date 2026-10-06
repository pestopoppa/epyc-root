"""Off-host ANALYSIS of an existing native receipt; no fixture rerun or new grading rule."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys
import zipfile

CARRIER = "4c0c653baf1654c8c25c66433cf39c8faefd8e52"
SOURCE = "78c889085c61f7255171cd1f4ea161176d2ef473"
NATIVE_RECIPE = "d8647f3a12fd0713bdca646116bd89afa11dace9"
RUN = 37514086438
ARTIFACT = 11437205660
ZIP_SHA = "28f8208a5a64effbf4b19494a3b78cb26bdca8a4a7e333bcecd0f84abfa4f21c"
RECEIPT_FILE_SHA = "71a7dc16e447c4c36dbaa5db6084cfde127ed378b69cee3dd97a4464cf945eed"
CODE_INPUTS = (
    "scripts/ci/native_conformance.py", "scripts/vidya/adapters/__init__.py",
    "scripts/vidya/adapters/ci_conformance.py", "scripts/vidya/claim_tuple.py",
    "scripts/vidya/canonical.py", "scripts/vidya/lattice.py",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write(path: Path, value) -> None:
    with path.open("x") as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write("\n")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def main() -> int:
    workspace = Path(os.environ["GITHUB_WORKSPACE"])
    recipe, carrier = workspace / "recipe", workspace / "carrier"
    result = Path(os.environ["RUNNER_TEMP"]) / "lr8-grade-analysis"
    status = {"state": "preparing", "original_run": RUN, "fixture_rerun": False}
    try:
        if platform.python_version() != "3.13.15":
            raise ValueError("analysis Python pin differs")
        for root, pin in ((recipe, os.environ["GITHUB_SHA"]), (carrier, CARRIER)):
            if git(root, "rev-parse", "HEAD") != pin or git(root, "status", "--porcelain"):
                raise ValueError("analysis source checkout differs or is dirty")
        # Bind actual grader/adapter/producer and recipe bytes before original access.
        code = []
        selections = [(carrier, name) for name in CODE_INPUTS]
        selections += [(recipe, ".github/workflows/lr8-shared-grade-analysis.yml"),
                       (recipe, "scripts/ci/lr8_shared_grade_analysis.py")]
        for index, (root, name) in enumerate(selections):
            mode, kind, oid = git(root, "ls-tree", "HEAD", "--", name).split("\t", 1)[0].split()
            if mode not in {"100644", "100755"} or kind != "blob":
                raise ValueError("analysis input is not a regular Git blob")
            raw = subprocess.check_output(["git", "-C", str(root), "cat-file", "blob", oid])
            path = root / name
            if any(part.is_symlink() for part in (path, *path.parents)) or path.read_bytes() != raw:
                raise ValueError("analysis working input differs from pinned source")
            snapshot = f"code-{index:03d}.bin"
            with (result / snapshot).open("xb") as out:
                out.write(raw)
            code.append({"repository": root.name, "path": name, "mode": mode,
                         "git_blob": oid, "sha256": sha(raw), "snapshot": snapshot})
        context = {"analysis_recipe": os.environ["GITHUB_SHA"], "carrier": CARRIER,
                   "python": sys.version, "platform": platform.platform(), "code_inputs": code,
                   "original_run": RUN, "original_artifact": ARTIFACT, "zip_sha256": ZIP_SHA,
                   "fixture_rerun": False, "context_is_runner_asserted": True}
        write(result / "source-first-context.json", context)
        api = f"repos/pestopoppa/epyc-root/actions/artifacts/{ARTIFACT}"
        metadata_raw = subprocess.check_output(["gh", "api", api])
        with (result / "original-api.json").open("xb") as out:
            out.write(metadata_raw)
        metadata = json.loads(metadata_raw)
        if (metadata["id"] != ARTIFACT or metadata["workflow_run"]["id"] != RUN
                or metadata["workflow_run"]["head_sha"] != NATIVE_RECIPE
                or metadata.get("digest") != "sha256:" + ZIP_SHA or metadata["expired"]):
            raise ValueError("original artifact API identity differs")
        original_zip = result / "original-artifact.zip"
        with original_zip.open("xb") as out:
            subprocess.run(["gh", "api", api + "/zip"], stdout=out, check=True)
        if original_zip.stat().st_size != metadata["size_in_bytes"] or sha(original_zip.read_bytes()) != ZIP_SHA:
            raise ValueError("original ZIP digest differs")
        original = result / "original"
        with zipfile.ZipFile(original_zip) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("duplicate original ZIP members")
            for entry in archive.infolist():
                parts = PurePosixPath(entry.filename)
                if parts.is_absolute() or ".." in parts.parts or stat.S_ISLNK(entry.external_attr >> 16):
                    raise ValueError("unsafe original ZIP member")
                dest = original.joinpath(*parts.parts)
                if entry.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("xb") as out:
                    out.write(archive.read(entry))
        receipt = original / "native/receipt.json"
        if sha(receipt.read_bytes()) != RECEIPT_FILE_SHA:
            raise ValueError("original receipt FILE hash differs")
        sys.path.insert(0, str(carrier))
        sys.path.insert(0, str(carrier / "scripts/vidya"))
        from scripts.vidya.adapters.ci_conformance import native_rows, project_ci_conformance
        from claim_tuple import grade
        rows = native_rows(receipt)  # Existing strict reader reopens original sidecars/JUnit.
        if len(rows) != 1 or rows[0]["record"]["repositories"] != {
                "source": SOURCE, "recipe": NATIVE_RECIPE, "carrier": CARRIER}:
            raise ValueError("original native projection identity differs")
        claim = project_ci_conformance(rows[0])
        q, t, reasons = grade(claim)
        write(result / "shared-grade.json", {
            "kind": "analysis_of_existing_native_receipt", "original_run": RUN,
            "original_artifact": ARTIFACT, "original_zip_sha256": ZIP_SHA,
            "original_receipt_file_sha256": RECEIPT_FILE_SHA,
            "carrier": CARRIER, "analysis_recipe": os.environ["GITHUB_SHA"],
            "claim_tuple": asdict(claim), "grade": {"Q": q, "T": t, "reasons": reasons},
            "fixture_rerun": False, "new_native_receipt_authored": False,
        })
        if sha(original_zip.read_bytes()) != ZIP_SHA or sha(receipt.read_bytes()) != RECEIPT_FILE_SHA:
            raise ValueError("analysis changed an original")
        if (q, t) != ("Judged", "Located"):
            raise ValueError("original observation grade differs from the reviewed expectation")
        status.update(state="graded", grade={"Q": q, "T": t, "reasons": reasons})
        return 0
    except Exception as exc:
        status.update(state="analysis_failed", error=f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        (result / "status.json").write_text(json.dumps(status, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
