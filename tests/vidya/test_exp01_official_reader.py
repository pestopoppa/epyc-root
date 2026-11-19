"""Replay a model-free, original-shaped R2 filing through the public adapter."""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))

import cli  # noqa: E402
from adapters import exp01_official as official, exp01_proxy_capture as capture  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402

DATA = ROOT / "data/vidya/exp01-input-recovery-20261118"
PRODUCER = DATA / "official-capture-preparation/r2"
RECOVERY = DATA / "continuation/full-complete"
RUN_ID = "b" * 32
NOW = datetime(2026, 11, 18, 16, tzinfo=timezone.utc).timestamp()
BENCH_TYPES = {"Q4KM": "Q4_K_M", "IQ4KT": "IQ4_KT", "IQ2XXS": "IQ2_XXS", "IQ2KT": "IQ2_KT"}
TG_NS = {
    "Q4KM": [6_400_000_000, 6_400_000_000],
    "IQ4KT": [5_120_000_000, 5_120_000_000],
    "IQ2XXS": [8_000_000_000, 6_400_000_000, 8_000_000_000],
    "IQ2KT": [8_000_000_000, 6_400_000_000, 5_120_000_000],
}


def _data(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _pin(path, data):
    return dict(path=str(path), size=len(data), sha256=_sha(data), dev=1, ino=2,
                mtime_ns=int(NOW * 1e9), ctime_ns=int(NOW * 1e9))


def _manifest(data):
    return json.loads(data["ready-manifest.json"])


def _binding(files):
    return official._binding(files, _manifest(files), json.loads(files["RESULT.json"]),
                             json.loads(files["RUN.json"]))


def _seal(filing, files, rows):
    manifest = _manifest(files)
    result = json.loads(files.get("RESULT.json", b"{}"))
    origin = Path(manifest["scratch_root"]) / "official/attempt-offline_01"
    raw = b"".join(map(_data, rows))
    files["results.jsonl"] = raw
    terminal = json.loads(files["TERMINAL.json"])
    terminal.update(raw=_pin(origin / "results.jsonl", raw),
                    summary=_pin(origin / "SUMMARY.json", files["SUMMARY.json"]))
    files["TERMINAL.json"] = _data(terminal)
    result.update(unit_id=manifest["id"], mode="official", state=terminal["state"],
                  native_units=len(rows), attempt=str(origin),
                  terminal=_pin(origin / "TERMINAL.json", files["TERMINAL.json"]))
    files["RESULT.json"] = _data(result)
    filing.mkdir()
    official._write_bundle(filing, files, _binding(files))


def _native_bench(model, arm, ordinal):
    def cell(pp, tg, ns):
        rate = (pp + tg) * 1e9 / ns
        return dict(n_prompt=pp, n_gen=tg, samples_ns=[ns], avg_ns=ns, samples_ts=[float(f"{rate:.6g}")],
                    avg_ts=float(f"{rate:.6f}"), n_threads=24, model_filename=model["path"],
                    model_size=model["size"] - 100, model_type=f"qwen35moe 35B.A3B {BENCH_TYPES[arm]}",
                    build_commit=official.INSTRUMENT_SHA[:9], n_gpu_layers=999, cuda=False,
                    gpu_info="", rpc="0", vulkan=False, kompute=False, metal=False, sycl=False, gpu_blas=False)

    return [cell(512, 0, 6_400_000_000), cell(0, 128, TG_NS[arm][ordinal - 1])]


@pytest.fixture
def original_shape(tmp_path):
    # Actual already filed prospective source and recovery inputs. The native units, clocks,
    # allocator and terminal records below are synthetic software controls.
    files = {f"source/{name}": (PRODUCER / name).read_bytes() for name in official.SOURCE_MEMBERS}
    files.update({name: (PRODUCER / name).read_bytes() for name in
                  ("ready-manifest.json", "SOURCE.json", "original-fixed-items.jsonl")})
    files.update({"recovery-seal.json": (RECOVERY / "SEALED-RECEIPT.json").read_bytes(),
                  "recovery-terminal.json": (RECOVERY / "RESULT.json").read_bytes(),
                  "tooling-manifest.json": (DATA / "TOOLING-PINS.json").read_bytes()})
    manifest = _manifest(files)
    origin = Path(manifest["scratch_root"]) / "official/attempt-offline_01"
    rid = manifest["id"]
    mask = list(range(120, 144))
    cpus = "120-143"
    raw_grant = b"regions=120-143 start=2026-11-18T15:59Z end=2026-11-18T17:30Z holds=q5\n"
    files["grant.original"] = raw_grant
    files["grant-ended.original"] = (
        f"rc=0 time=2026-11-18T16:08:10Z reason=complete\njob_id={rid}\nowner={manifest['owner']}\n"
        f"step=job-run\nestimated_wall_s={manifest['estimate_s']}\nstarted=2026-11-18T16:00:00Z\nregions={cpus}\n"
    ).encode()
    files["allocator-complete.original"] = f"complete time=2026-11-18T16:08:10Z id={rid}\n".encode()
    pins = json.loads(files["source/PINS.json"])
    validity = dict(unit="validity", ok=True, why=[], arms={}, instrument=dict(
        tree=capture.INSTRUMENT, commit=official.INSTRUMENT_SHA, tracked_dirty=False, linkage_rc=0,
        kt_kernel_strings=21, fixture=False))
    for arm, model in pins["models"].items():
        meta = model["metadata"]
        validity["arms"][arm] = dict(path=meta["path"], size=meta["size"], mtime=meta["mtime_ns"] // 10**9,
                                     sha256_pinned=model["sha256_pinned"], exists=True, arch="qwen35moe",
                                     types={BENCH_TYPES[arm]: 10}, arch_supported_by_instrument=True)
    libs = {v["path"]: v for key, v in pins["artifacts"].items() if key.startswith("instrument-lib:")}
    build = f"{capture.INSTRUMENT}/build"
    linkage = f"binary : {pins['artifacts']['bench']['path']}\nexpect : libraries under {build}\n"
    linkage += "".join(f"  OK   {Path(path).name} -> {path}\n" for path in libs)
    linkage += f"    libggml-base.so seen                   : 0   (every ggml binary links it)\n"
    linkage += f"ACCEPTED: monolithic ik libggml; all inspected libs inside {build}\n"
    files["linkage.log"] = linkage.encode()

    items = list(map(json.loads, files["original-fixed-items.jsonl"].splitlines()))
    deadline = int(NOW + 90 * 60 - 90)
    alloc = dict(FILLER_ID=rid, FILLER_CPUS=cpus, FILLER_THREADS="24", FILLER_DEADLINE=str(deadline))
    run = dict(schema="epyc.exp01.capture.v1", run_id=RUN_ID, mode="official", started_at=NOW + 0.1,
               pins=pins, source_sha256=_sha(files["SOURCE.json"]),
               grant=dict(raw=raw_grant.decode(), identity=_pin(official.FLAGS / "grants" / f"{rid}.grant", raw_grant)),
               allocation=alloc, planned=dict(speed_arms=list(capture.ARMS), launches_per_arm=3, pp=512, tg=128,
                                             cap_s=5400, paired_item_ids=[item["id"] for item in items],
                                             planned_looks=[2, 3], look_source=_sha(files["source/look.py"]),
                                             launch_deadline=deadline, stop_file=str(origin / "STOP")))
    files["RUN.json"] = _data(run)
    rows = []
    elapsed = 1.0

    def emit(row, **evidence):
        nonlocal elapsed
        elapsed += 0.25
        rows.append(dict(row, belief_capture=dict(schema="epyc.exp01.unit_capture.v1",
                                                   run_id=RUN_ID, mode="official", allocation=alloc,
                                                   written_at=NOW + elapsed, **evidence)))

    def launch(row, tool, args, stdout):
        nonlocal elapsed
        path = f"launches/{row['unit']}"
        duration = 25.0 if row["kind"] == "speed" else 1.0
        start = elapsed + 1.0
        elapsed = start + duration
        pid = 100 + len(rows)
        streams = {}
        for name, data in (("stdout", stdout), ("stderr", b"original captured stderr\n")):
            files[f"{path}.{name}"] = data
            streams[name] = _pin(origin / f"{path}.{name}", data)
        data = _data(dict(schema="epyc.exp01.launch.v1", unit=row["unit"], rc=0, native_rc=0,
                          disposition="complete", pid=pid, argv=[tool["path"], *args], executable=tool,
                          started_at=NOW + start, ended_at=NOW + elapsed,
                          started_monotonic_s=1000 + start, ended_monotonic_s=1000 + elapsed,
                          mapped_artifacts=libs, samples=[
                              dict(monotonic_s=1000 + start + n / 4, own_pid=pid, affinity=mask, mapped=sorted(libs))
                              for n in range(1, 3)
                          ], **streams))
        files[f"{path}.json"] = data
        return _pin(origin / f"{path}.json", data), duration

    def producer_look(*args):
        native = tmp_path / "working-results.jsonl"
        native.write_bytes(b"".join(map(_data, rows)))
        command = [sys.executable, str(PRODUCER / "look.py"), str(native), *args]
        return json.loads(subprocess.check_output(command, env={"LAUNCHES": "3"}))

    emit(validity)
    for ordinal in range(1, 4):
        for first, second in official.PAIRS:
            if first == "Q4KM" and ordinal == 3:
                continue
            for arm in (first, second):
                unit = f"speed-{arm}-{ordinal}"
                model = pins["models"][arm]["metadata"]
                pp, tg = _native_bench(model, arm, ordinal)
                data = _data([pp, tg])
                row = dict(unit=unit, kind="speed", arm=arm, launch=ordinal, rc=0, cpus=cpus, threads=24,
                           gguf=model["path"], pp=pp["avg_ts"], tg=tg["avg_ts"], pp_n=512, tg_n=128,
                           build_commit=tg["build_commit"], type_k=tg["model_type"])
                args = ["-m", model["path"], "-p", "512", "-n", "128", "-r", "1", "-t", "24", "-o", "json"]
                identity, row["duration_s"] = launch(row, pins["artifacts"]["bench"], args, data)
                files[f"{unit}.json"] = data
                files[f"{unit}.err"] = files[f"launches/{unit}.stderr"]
                emit(row, launch=identity, raw=_pin(origin / f"{unit}.json", data))
            if ordinal > 1:
                emit(producer_look(first, second))
    for i, item in enumerate(items):
        for arm in capture.ARMS[:2]:
            unit = f"q-{arm}-{item['id']}"
            model = pins["models"][arm]["metadata"]
            raw = {(0, "Q4KM"): b"<answer>'g'</answer>\r\n", (1, "IQ4KT"): b"<answer></answer>\r"}.get(
                (i, arm), b"fixture wrong answer\r\n")
            answer = raw.decode().replace("\r\n", "\n").replace("\r", "\n")
            row = dict(unit=unit, kind="quality", arm=arm, item=item["id"], rc=0, cpus=cpus, threads=24,
                       item_hash=_sha((item["prompt"] + item["expect_regex"]).encode())[:16],
                       item_native=item, output=answer, correct=bool(re.search(item["expect_regex"], answer)))
            args = ["-m", model["path"], "-p", item["prompt"], "-n", "256", "--temp", "0",
                    "--seed", "42", "-t", "24", "--no-display-prompt"]
            identity, row["duration_s"] = launch(row, pins["artifacts"]["cli"], args, raw)
            emit(row, launch=identity)

    summary = producer_look("SUMMARY", "SUMMARY", str(int(elapsed)))
    files["SUMMARY.json"] = _data(summary)
    files["TERMINAL.json"] = _data(dict(run_id=RUN_ID, mode="official", rc=0, state="complete-unprojected",
                                       ended_at=NOW + elapsed + 1, stop_file_observed=False, deadline_reached=False))
    return files, rows


def _ingest(ledger, path, capsys):
    as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "exp01-proxy-capture",
                   "--path", str(path), "--as-of", as_of, "--only-new"])
    assert rc == 0
    return json.loads(capsys.readouterr().out)


def test_original_shaped_official_filing_projects_only_located_speed_observations(tmp_path, capsys, original_shape):
    filing, ledger = tmp_path / "official", tmp_path / "ledger.jsonl"
    _seal(filing, *original_shape)
    report = _ingest(ledger, filing, capsys)
    assert (report["rows_projected"], report["frames_emitted"], report["refused"]) == (8, 24, [])
    observations = [capture.project(row) for row in capture.native_rows(filing)]
    assert [row.reps for row in observations] == [2, 2, 2, 2, 3, 3, 3, 3]
    assert {row.metric for row in observations} == {
        "official_proxy_pp512_native_tokens_per_s", "official_proxy_tg128_native_tokens_per_s"}
    assert [row.value for row in observations[:4]] == [80.0, 20.0, 80.0, 25.0]
    assert [row.extra["native_rates"] for row in observations[-3::2]] == [[16.0, 20.0, 16.0], [16.0, 20.0, 25.0]]
    assert {grade(row)[:2] for row in observations} == {("Judged", "Located")}
    assert {row.protocol_id for row in observations} == {""}
    for row in observations:
        assert row.extra["mode"] == "official"
        assert row.applicability["backend"] == "cpu" and row.applicability["threads"] == 24
        assert row.attestation_sha256 == _sha((filing / "results.jsonl").read_bytes())
        assert [look["stop"] for look in row.extra["operational_looks"]] == ["answer", "continue", "continue"]
        assert len(row.extra["paired_quality"]["items"]) == 24
        assert row.extra["paired_quality"]["flips"] == {"correct_to_incorrect": 1, "incorrect_to_correct": 1}
        assert set(row.extra["paired_quality"]["model_identities"]) == {"Q4KM", "IQ4KT"}
    retry = _ingest(ledger, filing, capsys)
    assert retry["frames_emitted"] == 0 and retry["frames_skipped"] == 24


@pytest.mark.parametrize(("change", "reason"), [
    ("allocator-id", "allocator completion marker identifies a different row"),
    ("grant-regions", "original allocator grant differs"),
    ("window", "authorized grant window differs"),
    ("stopped", "incomplete official run"),
    ("mode", "incomplete official run"),
    ("partial", "incomplete official run"),
    ("helper", "source inventory"),
    ("item", "original items bytes differ"),
    ("stream", "launch stdout changed"),
    ("mask", "sample, affinity or process identity"),
    ("duplicate-sample", "sample, affinity or process identity"),
    ("library", "persistent official mapped library identities"),
    ("pid", "out-of-window official launch"),
    ("nan", "out-of-window official launch"),
    ("vector", "native speed does not re-derive"),
    ("parse-error", "native speed does not re-derive"),
    ("look", "operational look does not re-derive"),
    ("stop-order", "incomplete, extra or reordered official units"),
    ("quality", "paired item or quality outcome"),
    ("quality-order", "incomplete, extra or reordered official units"),
    ("summary", "official summary does not re-derive"),
])
def test_altered_original_shaped_filing_refuses_after_outer_reseal(tmp_path, capsys, original_shape, change, reason):
    files, rows = original_shape
    row = rows[1]
    unit = row["unit"]
    ref = f"launches/{unit}"
    launch = json.loads(files[f"{ref}.json"])
    run, terminal = (json.loads(files[f"{name}.json"]) for name in ("RUN", "TERMINAL"))
    if change == "allocator-id":
        files["allocator-complete.original"] = files["allocator-complete.original"].replace(b"id=", b"id=other-")
    elif change == "grant-regions":
        files["grant.original"] = files["grant.original"].replace(b"120-143", b"0-23")
        grant = run["grant"]
        grant.update(raw=files["grant.original"].decode(),
                     identity=_pin(grant["identity"]["path"], files["grant.original"]))
    elif change == "window":
        run["allocation"]["FILLER_DEADLINE"] = str(int(run["allocation"]["FILLER_DEADLINE"]) + 1)
    elif change == "stopped":
        terminal["stop_file_observed"] = True
    elif change == "mode":
        run["mode"] = "publisher-smoke"
    elif change == "partial":
        terminal["state"] = "partial-or-failed"
    elif change == "helper":
        files["source/look.py"] += b"\n# changed look\n"
        source = json.loads(files["SOURCE.json"])
        source["look.py"] = run["planned"]["look_source"] = _sha(files["source/look.py"])
        files["SOURCE.json"] = _data(source)
        run["source_sha256"] = _sha(files["SOURCE.json"])
    elif change == "item":
        files["original-fixed-items.jsonl"] = files["original-fixed-items.jsonl"].replace(b"<answer>", b"<changed>", 1)
    elif change == "stream":
        files[f"{ref}.stdout"] += b"changed"
    elif change == "mask":
        launch["samples"][0]["affinity"] = list(range(24))
    elif change == "duplicate-sample":
        launch["samples"][1] = launch["samples"][0]
    elif change == "library":
        launch["mapped_artifacts"].pop(next(iter(launch["mapped_artifacts"])))
    elif change == "pid":
        launch["pid"] = 0
    elif change == "nan":
        launch["started_monotonic_s"] = float("nan")
    elif change == "vector":
        cells = json.loads(files[f"{ref}.stdout"])
        cells[1]["samples_ts"] = [99.0]
        cells[1]["avg_ts"] = row["tg"] = 99.0
        data = _data(cells)
        files[f"{ref}.stdout"] = files[f"{unit}.json"] = data
        launch["stdout"] = _pin(launch["stdout"]["path"], data)
        old = row["belief_capture"]["raw"]
        row["belief_capture"]["raw"] = _pin(old["path"], data)
    elif change == "parse-error":
        row["parse_error"] = "partial result"
    elif change == "look":
        next(item for item in rows if item.get("kind") == "look")["stop"] = "futility"
    elif change == "stop-order":
        i = next(i for i, item in enumerate(rows) if item.get("kind") == "look")
        rows[i]["unit"] = "look-IQ2XXS-IQ2KT"
    elif change == "quality":
        next(item for item in rows if item.get("kind") == "quality")["correct"] = False
    elif change == "quality-order":
        rows[-1]["unit"] = rows[-2]["unit"]
    elif change == "summary":
        summary = json.loads(files["SUMMARY.json"])
        summary["quality_items_scored"] = 24
        files["SUMMARY.json"] = _data(summary)
    files["RUN.json"], files["TERMINAL.json"] = _data(run), _data(terminal)
    data = files[f"{ref}.json"] = _data(launch)
    row["belief_capture"]["launch"] = _pin(row["belief_capture"]["launch"]["path"], data)
    filing = tmp_path / "official"
    _seal(filing, files, rows)
    report = _ingest(tmp_path / "ledger.jsonl", filing, capsys)
    assert report["frames_emitted"] == 0 and reason in report["refused"][0]["reason"]
    with pytest.raises(ProjectionError, match=re.escape(reason)):
        capture.project({"filing": filing, "measurement_id": f"exp01-official:{RUN_ID}:Q4KM:pp512"})


def test_archive_duplicate_refuses(tmp_path, original_shape):
    filing = tmp_path / "official"
    files, rows = original_shape
    _seal(filing, files, rows)
    with tarfile.open(filing / official.ARCHIVE, "w:gz") as archive:
        for _ in range(2):
            member = tarfile.TarInfo("RUN.json")
            member.size = len(files["RUN.json"])
            archive.addfile(member, io.BytesIO(files["RUN.json"]))
    with pytest.raises(ProjectionError, match="duplicate or excessive"):
        capture.native_rows(filing)


@pytest.mark.parametrize("filing", [PRODUCER / "smoke", RECOVERY])
def test_source_smoke_and_recovery_have_no_official_entry(filing):
    with pytest.raises(ProjectionError, match="completion-binding"):
        capture.native_rows(filing)


def test_packager_copies_acquired_grant_and_checks_before_publishing(tmp_path, monkeypatch, original_shape):
    files, rows = original_shape
    _seal(tmp_path / "original-shaped-test", files, rows)
    manifest, report, run = (json.loads(files[name]) for name in ("ready-manifest.json", "RESULT.json", "RUN.json"))
    _, locations = official._file_map(_binding(files), manifest, report, run)
    origin = Path(report["attempt"])
    originals = {original: files[name] for name, original in locations.items()}
    originals.update({origin.parent.parent / name: files[f"source/{name}"] for name in official.SOURCE_MEMBERS})
    originals.update({origin / name: data for name, data in files.items()
                      if name.startswith(("launches/", "speed-"))})
    # Route only this test's virtual file identities. The packager and verifier still perform all their normal checks.
    original_read = official._read
    monkeypatch.setattr(official, "_read", lambda path, limit: originals[path] if path in originals
                        else original_read(path, limit))
    args = (locations["ready-manifest.json"], None, locations["grant-ended.original"],
            locations["allocator-complete.original"])
    output = tmp_path / "packed"
    official.pack(*args, output)
    assert json.loads((output / official.MARKER).read_bytes())["grant_copy_source"] == "RUN.grant.raw"
    assert len(capture.native_rows(output)) == 8
    with pytest.raises(FileExistsError):
        official.pack(*args, output)
    originals[locations["allocator-complete.original"]] = b"complete missing-original-identity\n"
    with pytest.raises(ValueError):
        official.pack(*args, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()
