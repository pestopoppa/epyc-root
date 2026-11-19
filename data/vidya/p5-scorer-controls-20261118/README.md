# Prospective Sphinx scorer-control capture

The private successor runs the same Sphinx gold and no-op scorer from the original preparation packet. It copies the scorer from checked historical bytes and changes its output path and recording of each attempted arm's raw paths. The [custody producer](../../../scripts/vidya/producers/p5_scorer_custody.py) snapshots the allocator grant, checks effective CPU placement and the live window, and records UTC start and completion, original scorer output, raw reports, raw test logs, and source and cleanup identities. On refusal it retains UNKNOWN and the primary error. Publisher smoke uses its own allocator-selected result path. A scorer diagnostic FAIL can still be a complete acquisition.

The five custody tests and eleven original scorer software controls passed without Docker containers. Docker preflight requires the pinned prepared image. The original prepared image and base were absent locally at inspection. The remote immutable base manifest still identifies config `sha256:84fd7981cbcb53fe42d3f314cac61670175b9429ec51abea180f258d6e66f293`. A 35-second bounded pull verified several layers before timing out. The parent is handling image restoration.

## Use the original prepared image

From the EPYC root, create a fresh private packet and check the image admission gate before publication.

```bash
scratch=/mnt/raid0/llm/tmp/vidya-belief-substrate
packet=data/vidya/p5-scorer-controls-20261118
native=$scratch/p5-sphinx-scorer-r1-20261118
python3 -I -B "$packet/stage.py" "$native"
bash "$native/preflight.sh"
ROWFLOW_REPO="$PWD" python3 scripts/coordination/rowflow/publish_row.py "$native/spec.json"
```

Skip staging when that exact private packet already exists. The native row uses the granted CPU quarter, with four allocated cores in publisher smoke. It stops at both arms complete or at refusal, STOP or the earlier of 270 seconds and the allocation deadline.

## Build-only prerequisite if the prepared image is unavailable

The pinned base acquisition is an external preparation step. This immutable digest is the resolved AMD64 manifest, and the local config ID must match the recorded base before the build.

```bash
base='swebench/sweb.eval.x86_64.sphinx-doc_1776_sphinx-8593@sha256:bf09a4f64ca8a2dd3c9e2d252d640ed0239e6b2927fa524e40b6cde7aa0fafc0'
restore=$scratch/p5-sphinx-image-restore
mkdir -p "$restore"
python3 -B scripts/utils/safe_download.py --dest "$restore" -- docker pull --platform linux/amd64 "$base"
docker image inspect --format '{{.Id}}' "$base"

build=$scratch/p5-sphinx-image-build-sealed-20261118
python3 -I -B "$packet/stage.py" --build "$build"
"$build/launch.sh" --preflight
ROWFLOW_REPO="$PWD" python3 scripts/coordination/rowflow/publish_row.py "$build/spec.json"
```

After official rc0, file the original build receipt and stage a fresh native packet with its distinct derived image identity. The sealed scorer still verifies its image checkout and runs both controls.

```bash
native=$scratch/p5-sphinx-scorer-rebuilt-20261118
python3 -I -B "$packet/stage.py" --image-receipt "$build/official/RESULT.json" "$native"
bash "$native/preflight.sh"
ROWFLOW_REPO="$PWD" python3 scripts/coordination/rowflow/publish_row.py "$native/spec.json"
```

The retained Astropy and Sphinx November 4 results lack writer-time grant and completion fields. The prospective Sphinx capture still needs actual image qualification, native execution, registered projection and an actual planning-context canary.
