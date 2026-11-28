"""Stream the pinned W66 replay without invoking any generated actions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
SOURCE = "ce6fcbbde1ee58f165283fbfe74910f47bb2efba"
STORE = Path("/mnt/raid0/llm/kernels/builds/gpu-20261126-ce6fcbbde-c22-composite")
VERIFY = Path("/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
KFD = Path("/sys/class/kfd/kfd/proc")
CPUSET = set(range(88, 96))
ROWFLOW_SUPPORT = "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow"
PREFIX_SHA = "d387b46340e2f82c23008681facbf83b9cc15698aad65e790c11fa4fb03fcb0d"
SOURCES = {"OFF": 2, "ON": 1}
PRIMARY_PEER = {"ON28": ("OFF56", False), "OFF56": ("ON28", True),
                "OFF52": ("ON27", True), "ON29": ("OFF56", True)}
TARGETS = ("ON28", "OFF56", "OFF52", "ON29")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def digest_file(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def wire_bytes(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()


def cpus_in(assignment):
    found = set()
    for region in assignment.split(","):
        start, separator, end = region.partition("-")
        found.update(range(int(start), int(end or start) + 1))
    return found


def save_json(path, obj):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


class Inputs:
    def __init__(self):
        self.pins_path = ROOT / "artifacts/analysis/ap-w66-replay-inputs/requests.json"
        self.pins = json.loads(self.pins_path.read_text())
        trace_path = ROOT / "artifacts/analysis/ap-w66-trace/replay-manifest.json"
        self.trace = json.loads(trace_path.read_text())
        self.state_plan_path = ROOT / "artifacts/analysis/ap-w66-pair-states/plan.json"
        self.state_plan = json.loads(self.state_plan_path.read_text())
        self.primary_peers = {f'{row["mode"]}{row["seq"]}': row["primary_peer"]
                              for row in self.state_plan["requests"]}
        if self.trace["source_csv_sha256"] != self.pins["source_csv_sha256"]:
            raise ValueError("trace and input CSV pins differ")
        csv_raw = subprocess.check_output(
            ["git", "show", f'{self.pins["source_commit"]}:{self.pins["source_csv"]}'], cwd=ROOT)
        if digest(csv_raw) != self.pins["source_csv_sha256"]:
            raise ValueError("source CSV digest mismatch")
        self.ledgers = {}
        self.bound = {}
        for row in self.pins["requests"]:
            mode = "ON" if "-on-" in row["id"] else "OFF"
            path = Path(row["wire_receipt_path"])
            if mode not in self.ledgers:
                lines = [json.loads(line) for line in path.read_text().splitlines()]
                self.ledgers[mode] = (path, {int(line["seq"]): line for line in lines})
            self.bound[f'{mode}{row["seq"]}'] = row
        self.bodies = {}
        self.identities = {}
        for label in (*TARGETS, "ON27"):
            self.load(label)
            self.load(self.predecessor(label))

    def predecessor(self, label):
        mode = label.rstrip("0123456789")
        return f"{mode}{int(label[len(mode):]) - 1}"

    def load(self, label):
        mode = label.rstrip("0123456789")
        ledger, rows = self.ledgers[mode]
        row = rows[int(label[len(mode):])]
        pin = self.bound.get(label)
        body_path = ledger.parent / row["body_ref"]
        if not body_path.is_file():
            body_path = ledger.parent / "bodies" / row["body_ref"]
        zipped = body_path.read_bytes()
        decoded = gzip.decompress(zipped)
        identity = {
            "label": label, "ledger": str(ledger), "body_path": str(body_path),
            "receipt_sha256": digest(canonical(row)), "gzip_sha256": digest(zipped),
            "decoded_sha256": digest(decoded),
        }
        if pin and any(identity[k] != pin[k] for k in
                       ("receipt_sha256", "gzip_sha256", "decoded_sha256")):
            raise ValueError(f"sealed replay digest mismatch for {label}")
        self.identities[label] = identity
        self.bodies[label] = json.loads(decoded)

    def payload(self, label, preserve=None, limit=None, fixed=False):
        body = self.bodies[label].copy()
        if preserve is not None:
            body["chat_template_kwargs"] = {**body["chat_template_kwargs"],
                                            "preserve_thinking": preserve}
        if limit is not None:
            body.pop("max_completion_tokens", None)
            body.pop("n_predict", None)
            body["max_tokens"] = limit
        if fixed:
            body["ignore_eos"] = True
        return body


class WorkInterrupted(Exception):
    pass


class Endpoint:
    def __init__(self, out, inputs):
        self.out = out
        self.inputs = inputs
        self.port = int(os.environ["FILLER_PORTS"].split(",")[0])
        self.deadline = float(os.environ["FILLER_DEADLINE"])
        self.stopfile = Path(os.environ["FILLER_STOPFILE"])
        self.stop = threading.Event()
        self.process = None
        self.samples = []
        self.monitor_error = None
        self.drm = next(p.parent for p in Path("/sys/class/drm").glob("card*/device/gpu_busy_percent"))
        self.raw = self.out / "private"
        self.raw.mkdir(mode=0o700, exist_ok=True)

    def check(self, margin=0):
        if self.stop.is_set() or self.stopfile.is_file() or time.time() + margin >= self.deadline:
            raise WorkInterrupted("stop requested or rowflow deadline approaching")
        if self.monitor_error:
            raise RuntimeError(self.monitor_error)
        if self.process and self.process.poll() is not None:
            raise RuntimeError(f"owned server exited with rc {self.process.returncode}")

    def http(self, route, payload=None, timeout=15):
        data = wire_bytes(payload) if payload is not None else None
        req = Request(f"http://127.0.0.1:{self.port}{route}", data,
                      {"Content-Type": "application/json"})
        return urlopen(req, timeout=timeout)

    def json(self, route, payload=None):
        with self.http(route, payload) as response:
            return json.load(response)

    def start(self):
        self.check(20)
        granted_affinity = cpus_in(os.environ["FILLER_CPUS"])
        allowed_affinity = os.sched_getaffinity(0)
        if not (CPUSET <= granted_affinity and CPUSET <= allowed_affinity):
            raise RuntimeError(f"grant or taskset excludes historical CPUs: {granted_affinity}, {allowed_affinity}")
        os.sched_setaffinity(0, CPUSET)
        self.wait_kfd_idle()
        identity = self.inputs.trace["historical_runtime"]["artifact_identity"]
        required_files = ("bin/llama-server", "bin/libllama-server-impl.so",
                          "bin/libllama.so", "bin/libllama-common.so", "bin/libggml.so",
                          "bin/libggml-base.so", "bin/libggml-cpu.so", "bin/libggml-hip.so")
        current = {name: digest_file(STORE / name) for name in required_files}
        if current != {name: identity["manifest_verified"][name] for name in required_files}:
            raise RuntimeError(f"C22 runtime mismatched {current}")
        stamp = json.loads((STORE / "BUILD-OK.json").read_text())
        if stamp["source_sha"] != SOURCE:
            raise RuntimeError("C22 source mismatch")
        historical = self.inputs.trace["historical_runtime"]
        argv = historical["argv"].copy()
        slots_dir = self.raw / "slots"
        slots_dir.mkdir(mode=0o700, exist_ok=True)
        argv[argv.index("--port") + 1] = str(self.port)
        argv[argv.index("--slot-save-path") + 1] = str(slots_dir) + "/"
        env = os.environ.copy()
        env.update(LD_LIBRARY_PATH=historical["LD_LIBRARY_PATH"], ROCR_VISIBLE_DEVICES="0",
                   HIP_VISIBLE_DEVICES="0", HSA_OVERRIDE_CPU_AFFINITY_DEBUG="0")
        model = Path(argv[argv.index("-m") + 1])
        st = model.stat()
        if [st.st_size, st.st_ino] != identity["model_stat"]:
            raise RuntimeError("model no longer matches the historical file identity")
        linkage = subprocess.run([str(VERIFY), str(STORE / "bin/llama-server"), str(STORE)],
                                 env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, check=True, timeout=15)
        (self.out / "linkage.txt").write_text(linkage.stdout)
        version = identity["identity"]["version"]
        with (self.raw / "server.log").open("w") as output:
            self.process = subprocess.Popen(argv, stdout=output, stderr=subprocess.STDOUT, env=env)
        save_json(self.out / "launch.json",
                  {"driver_pid": os.getpid(), "pid": self.process.pid, "argv": argv, "version": version,
                   "grant_affinity": sorted(granted_affinity), "run_affinity": sorted(CPUSET),
                   "incoming_affinity": sorted(allowed_affinity),
                   "source_sha": SOURCE, "runner_sha256": digest_file(Path(__file__)),
                   "hashes": current, "model": str(model),
                   "model_registry_sha256": identity["model_sha256_registry"],
                   "model_stat": {"size": st.st_size, "inode": st.st_ino, "mtime_ns": st.st_mtime_ns},
                   "started_unix": time.time(), "env": {k: env[k] for k in
                   ("LD_LIBRARY_PATH", "ROCR_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES",
                    "HSA_OVERRIDE_CPU_AFFINITY_DEBUG")}})
        self.monitor = threading.Thread(target=self.observe, daemon=True)
        self.monitor.start()
        cutoff = time.monotonic() + 170
        while time.monotonic() < cutoff:
            self.check()
            try:
                health = self.json("/health")
                if health.get("status") == "ok":
                    break
            except (OSError, TimeoutError):
                pass
            time.sleep(.5)
        else:
            raise RuntimeError("C22 health timed out")
        slots = self.json("/slots")
        if sorted(slot["id"] for slot in slots) != [0, 1, 2, 3] or any(
                slot.get("n_ctx") != 131072 for slot in slots):
            raise RuntimeError(f"expected 4 slots at 131072 tokens each, got {slots}")
        log = (self.raw / "server.log").read_text()
        if not any("kv_unified" in line and line.split("=")[-1].strip() == "'false'"
                   for line in log.splitlines()):
            raise RuntimeError("the startup log does not prove split KV")
        self.initial = self.resources()
        if not self.initial["pid_in_kfd"] or not self.initial["store_hip"] or not self.initial["vram_b"]:
            raise RuntimeError(f"missing live C22 GPU proof {self.initial}")
        save_json(self.out / "slots.json", {"slots": [{"id": s["id"], "n_ctx": s["n_ctx"]} for s in slots],
                                            "kv_unified": False, "residency": self.initial})

    def wait_kfd_idle(self):
        end = time.monotonic() + 6
        while True:
            clients = [p.name for p in KFD.iterdir()]
            if not clients:
                return
            if time.monotonic() >= end:
                raise RuntimeError(f"KFD clients before owned launch: {clients}")
            time.sleep(.25)

    def resources(self):
        pid = self.process.pid
        proc = Path(f"/proc/{pid}")
        kfd_proc = KFD / str(pid)
        maps = (proc / "maps").read_text()
        vram = sum(int(p.read_text()) for p in kfd_proc.glob("vram_*"))
        affinities = sorted({line.split(":", 1)[1].strip()
                             for task in (proc / "task").glob("*/status")
                             for line in task.read_text().splitlines()
                             if line.startswith("Cpus_allowed_list:")})
        for affinity in affinities:
            for part in affinity.split(","):
                limits = part.split("-")
                if int(limits[0]) not in CPUSET or int(limits[-1]) not in CPUSET:
                    raise RuntimeError(f"server affinity escaped grant: {affinity}")
        stats = (proc / "stat").read_text().rsplit(")", 1)[1].split()
        return {"mono_ns": time.monotonic_ns(), "unix_s": time.time(),
                "kfd_pids": sorted(int(p.name) for p in KFD.iterdir()),
                "pid_in_kfd": kfd_proc.is_dir(), "vram_b": vram,
                "store_hip": str(STORE / "bin/libggml-hip.so.0.16.0") in maps,
                "gpu_busy_pct": int((self.drm / "gpu_busy_percent").read_text()),
                "affinity": affinities, "cpu_ticks": int(stats[11]) + int(stats[12])}

    def observe(self):
        with (self.out / "resources.jsonl").open("w") as handle:
            while not self.stop.wait(.25):
                try:
                    row = self.resources()
                except (FileNotFoundError, ProcessLookupError):
                    continue
                except (ValueError, RuntimeError, OSError) as error:
                    self.monitor_error = str(error)
                    return
                self.samples.append(row)
                handle.write(json.dumps(row) + "\n")
                handle.flush()

    def erase(self, slot):
        self.check()
        return self.json(f"/slots/{slot}?action=erase", {})

    def close(self):
        self.stop.set()
        if not self.process:
            return
        self.monitor.join(timeout=2)
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        pid = self.process.pid
        kfd_retire_start = time.monotonic()
        kfd_at_exit = (KFD / str(pid)).exists()
        while (KFD / str(pid)).exists() and time.monotonic() - kfd_retire_start < 10:
            time.sleep(.1)
        result = {"owned_server_pid": pid, "driver_pid": os.getpid(), "server_rc": self.process.returncode,
                  "exists_after": Path(f"/proc/{pid}").exists(), "kfd_after": (KFD / str(pid)).exists(),
                  "kfd_present_at_wait_exit": kfd_at_exit,
                  "kfd_retirement_wait_s": time.monotonic() - kfd_retire_start,
                  "ended_unix": time.time()}
        save_json(self.out / "cleanup.json", result)
        if result["exists_after"] or result["kfd_after"]:
            raise RuntimeError(f"owned process was not fully cleaned up: {result}")

    def stream(self, name, label, body, first=None, route="/v1/chat/completions"):
        self.check(5)
        arrived = time.monotonic_ns()
        raw_path = self.raw / f"{name}.sse.jsonl"
        parsed_path = self.raw / f"{name}.message.json"
        timings, finish, offered = None, None, None
        message = {"content": "", "reasoning_content": "", "tool_calls": []}
        calls = {}
        forward = time.monotonic_ns()
        epochs = []
        with raw_path.open("w") as handle, self.http(route, body, timeout=240) as response:
            status = response.status
            for raw in response:
                self.check()
                now = time.monotonic_ns()
                if not raw.startswith(b"data:"):
                    continue
                field = raw[5:].strip()
                if field == b"[DONE]":
                    break
                event = json.loads(field)
                handle.write(json.dumps({"at_ns": now, "event": event}) + "\n")
                if "error" in event:
                    raise RuntimeError(f"streaming error in {name}: {event['error']}")
                timings = event.get("timings", timings)
                changes = []
                if route == "/completion" and event.get("content"):
                    changes.append("content")
                    message["content"] += event["content"]
                for choice in event.get("choices", []):
                    if choice.get("finish_reason") is not None:
                        finish = choice["finish_reason"]
                    delta = choice.get("delta", {})
                    for key in ("content", "reasoning_content"):
                        if delta.get(key):
                            changes.append(key)
                            message[key] += delta[key]
                    for part in delta.get("tool_calls", []):
                        changes.append("tool_calls")
                        call = calls.setdefault(part.get("index", 0), {"id": "", "type": "function",
                                                "function": {"name": "", "arguments": ""}})
                        call["id"] += part.get("id") or ""
                        for key in ("name", "arguments"):
                            call["function"][key] += part.get("function", {}).get(key) or ""
                if changes and offered is None:
                    offered = {"at_ns": now, "kinds": sorted(set(changes))}
                    if first:
                        first.set()
                if changes:
                    epochs.append(now)
                if event.get("stop") is True and route == "/completion":
                    finish = event.get("stop_type")
        end = time.monotonic_ns()
        if not timings or finish is None:
            raise RuntimeError(f"missing finish or C22 native timings in {name}")
        message["tool_calls"] = [calls[i] for i in sorted(calls)]
        source_body_sha = self.inputs.identities.get(label, {}).get("decoded_sha256")
        request_sha = digest(wire_bytes(body))
        save_json(parsed_path, {"name": name, "label": label, "message": message, "finish_reason": finish,
                                "source_body_sha256": source_body_sha, "request_body_sha256": request_sha})
        on = [x for x in self.samples if forward <= x["mono_ns"] <= end]
        if not on:
            on = [self.resources()]
        resident = all(x["pid_in_kfd"] and x["store_hip"] and x["vram_b"] and
                       x["kfd_pids"] == [self.process.pid] for x in on)
        if not resident:
            raise RuntimeError(f"bad GPU residency during {name}")
        row = {"name": name, "label": label, "slot": body["id_slot"], "client_arrived_ns": arrived,
               "forward_ns": forward, "first_delta": offered, "end_ns": end,
               "ttft_s": (offered["at_ns"] - forward) / 1e9 if offered else None,
               "wall_s": (end - forward) / 1e9,
               "native": timings, "http_status": status, "finish_reason": finish,
               "emitting_sse_events": len(epochs), "source_body_sha256": source_body_sha,
               "request_body_sha256": request_sha, "private_sse_sha256": digest_file(raw_path),
               "private_message_sha256": digest_file(parsed_path), "resource_sample_count": len(on),
               "min_vram_b": min(x["vram_b"] for x in on),
               "max_vram_b": max(x["vram_b"] for x in on), "gpu_busy_pct": {"min": min(x["gpu_busy_pct"] for x in on),
               "max": max(x["gpu_busy_pct"] for x in on), "median": statistics.median(x["gpu_busy_pct"] for x in on)}}
        save_json(self.out / f"{name}.receipt.json", row)
        print(json.dumps({k: row[k] for k in ("name", "native", "ttft_s", "wall_s", "finish_reason")}), flush=True)
        return row

    def snapshot(self, label, preserve):
        key = label + ("-preserve" if preserve else "")
        name = f"{key}.slot"
        snapshot = self.out / f"{key}.state.json"
        slot = self.inputs.bodies[label]["id_slot"]
        if snapshot.exists():
            state = json.loads(snapshot.read_text())
            if all((self.raw / "slots" / x["name"]).stat().st_size == x["bytes"] for x in state["files"]):
                return state
            raise RuntimeError(f"snapshot byte sizes changed for {key}")
        self.erase(slot)
        previous = self.inputs.predecessor(label)
        bound = self.prefix_plan[key]
        target = self.inputs.payload(label, preserve)
        prompt = self.json("/apply-template", target)["prompt"]
        tokens = self.json("/tokenize", {"content": prompt, "add_special": True,
                                         "parse_special": True})["tokens"]
        native_count = self.json("/v1/chat/completions/input_tokens", target)["input_tokens"]
        expected_count = bound["prompt_count"]
        n_cache = bound["prefix_count"]
        prefix_check = {"renderer_token_count": len(tokens), "native_token_count": native_count,
                        "sealed_total_tokens": expected_count, "sealed_prefix_tokens": n_cache,
                        "prefix_sha256": digest(canonical(tokens[:n_cache])),
                        "prompt_sha256": digest(canonical(tokens))}
        if (len(tokens) == native_count == expected_count and slot == bound["slot"]
                and prefix_check["prompt_sha256"] == bound["prompt_ids_sha256"]
                and prefix_check["prefix_sha256"] == bound["prefix_ids_sha256"]):
            body = {"prompt": bound["prefix_ids"], "id_slot": slot, "cache_prompt": True,
                    "n_predict": 1, "stream": True, "temperature": 0, "timings_per_token": True}
            warm = self.stream(f"snapshot-{key}", label, body, route="/completion")
            if warm["native"]["prompt_n"] != n_cache:
                raise RuntimeError(f"native preload count mismatches {label}: {warm['native']}")
            mode = "exact native-rendered target prefix at recorded cache depth, C22 native snapshot"
        else:
            body = self.inputs.payload(previous, preserve, 1)
            warm = self.stream(f"snapshot-{key}", previous, body)
            mode = "bounded immediate-predecessor replay, C22 native snapshot"
        with self.http(f"/slots/{slot}?action=save", {"filename": name}, timeout=180) as response:
            receipt = json.load(response)
        files = [{"name": p.name, "bytes": p.stat().st_size, "sha256": digest_file(p)}
                 for p in sorted((self.raw / "slots").glob(name + "*"))]
        if not files or any(x["bytes"] == 0 for x in files):
            raise RuntimeError(f"empty saved prefix for {key}")
        state = {"mode": mode, "prefix_check": prefix_check,
                 "target": label, "predecessor": previous, "slot": slot, "filename": name,
                 "predecessor_native": warm["native"], "save": receipt, "files": files}
        save_json(snapshot, state)
        return state

    def restore(self, state):
        slot = state["slot"]
        for file in state.get("files", []):
            if digest_file(self.raw / "slots" / file["name"]) != file["sha256"]:
                raise RuntimeError(f"snapshot digest changed before restore: {file['name']}")
        self.erase(slot)
        with self.http(f"/slots/{slot}?action=restore",
                       {"filename": state["filename"]}, timeout=180) as response:
            receipt = json.load(response)
        if (receipt.get("n_read") != state["save"].get("n_written") or
                receipt.get("n_restored") != state["save"].get("n_saved") or
                receipt.get("n_restored", 0) <= 0):
            raise RuntimeError(f"native restored token count differs: {receipt}")
        return receipt


def phase_windows(row):
    end = row["end_ns"] / 1e9
    decode = row["native"]["predicted_ms"] / 1000
    prefill = row["native"]["prompt_ms"] / 1000
    return {"prefill": [end - decode - prefill, end - decode], "decode": [end - decode, end]}


def overlap(first, second):
    return max(0, min(first[1], second[1]) - max(first[0], second[0]))


def union_length(windows):
    length, last = 0, -float("inf")
    for start, end in sorted(windows):
        length += max(0, end - max(last, start))
        last = max(last, end)
    return length


def reductions(rows):
    phases = {row["name"]: phase_windows(row) for row in rows}
    rates = {}
    for phase, counter, timer in (("decode", "predicted_n", "predicted_ms"),
                                  ("prefill", "prompt_n", "prompt_ms")):
        tokens = sum(row["native"][counter] for row in rows)
        native_s = sum(row["native"][timer] for row in rows) / 1000
        window_s = union_length([x[phase] for x in phases.values()])
        valid = [1000 * row["native"][counter] / row["native"][timer] for row in rows
                 if row["native"][timer] > 0]
        rates[phase] = {"tokens": tokens, "native_sum_s": native_s, "approx_phase_union_s": window_s,
                        "tok_s_sum_native": tokens / native_s if native_s else None,
                        "median_request_tok_s": statistics.median(valid) if valid else None,
                        "tok_s_phase_union": tokens / window_s if window_s else None}
    return {"phase_boundaries": "native durations right-aligned to client stream end, approximate",
            "monotonic_s": phases, "rates": rates}


def arm(endpoint, label, pair, kind, fixed=None):
    tag = f"{label}-p{pair}-{kind}" + (f"-fixed{fixed}" if fixed else "")
    target_preserve = True if kind == "preserved" else None
    target_slot = endpoint.inputs.bodies[label]["id_slot"]
    if kind == "cold":
        target_state, target_restore = None, endpoint.erase(target_slot)
    else:
        target_state = endpoint.snapshot(label, target_preserve)
        target_restore = endpoint.restore(target_state)
    body = endpoint.inputs.payload(label, target_preserve, fixed, fixed is not None)
    rec = {"tag": tag, "target_reconstruction": target_state, "target_restore": target_restore}
    if kind != "peer":
        target = endpoint.stream(tag + "-target", label, body)
        peer = None
    else:
        peer_label, peer_first = PRIMARY_PEER[label]
        peer_state = endpoint.snapshot(peer_label, None)
        peer_restore = endpoint.restore(peer_state)
        peer_body = endpoint.inputs.payload(peer_label)
        first_spec = (peer_label, peer_body, "peer") if peer_first else (label, body, "target")
        second_spec = (label, body, "target") if peer_first else (peer_label, peer_body, "peer")
        first_delta = threading.Event()
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_run = executor.submit(endpoint.stream, tag + "-" + first_spec[2],
                                        first_spec[0], first_spec[1], first_delta)
            while not first_delta.wait(.05) and not first_run.done():
                endpoint.check()
            actual = first_delta.is_set()
            second_run = executor.submit(endpoint.stream, tag + "-" + second_spec[2],
                                         second_spec[0], second_spec[1])
            first_row, second_row = first_run.result(), second_run.result()
        target, peer = (second_row, first_row) if peer_first else (first_row, second_row)
        tx, px = phase_windows(target), phase_windows(peer)
        rec.update(peer_label=peer_label, peer_first=peer_first, phase_trigger_observed=actual,
                   historical_peer=endpoint.inputs.primary_peers[label],
                   peer_reconstruction=peer_state, peer_restore=peer_restore,
                   observed_peer_forward_offset_s=(peer["forward_ns"] - target["forward_ns"]) / 1e9,
                   peer_prefill_during_target_decode_s=overlap(tx["decode"], px["prefill"]),
                   peer_decode_during_target_decode_s=overlap(tx["decode"], px["decode"]),
                   peer_decode_during_target_prefill_s=overlap(tx["prefill"], px["decode"]))
    rec.update(target=target, peer=peer, simultaneous=reductions([target, peer] if peer else [target]))
    pin = endpoint.inputs.bound[label]
    rec["historical_token_counts"] = {"fresh": int(pin["prompt_n"]), "cached": int(pin["cache_n"]),
                                      "generated": int(pin["predicted_n"])}
    rec["historical_cache_count_match"] = (target["native"]["prompt_n"] == int(pin["prompt_n"])
                                          and target["native"]["cache_n"] == int(pin["cache_n"]))
    save_json(endpoint.out / f"{tag}.arm.json", rec)
    return rec


def paired_rows(pairs, key):
    return [p[key]["target"] for p in pairs]


def token_counts(row):
    return row["native"]["prompt_n"], row["native"]["cache_n"]


def compare(pairs):
    alone, peers = paired_rows(pairs, "alone"), paired_rows(pairs, "peer")
    mismatch = any(token_counts(a) != token_counts(p) for a, p in zip(alone, peers))
    generation_diverged = any(
        abs(a["native"]["predicted_n"] - p["native"]["predicted_n"]) >
        max(16, 0.1 * min(a["native"]["predicted_n"], p["native"]["predicted_n"]))
        or a["finish_reason"] != p["finish_reason"]
        for a, p in zip(alone, peers))
    out = {"paired_cache_mismatch": mismatch, "material_output_length_or_finish_difference": generation_diverged,
           "all_peer_windows_intersect": all(
             p["peer"]["peer_prefill_during_target_decode_s"] > 1 or
             p["peer"]["peer_decode_during_target_decode_s"] > .25 or
             p["peer"]["peer_decode_during_target_prefill_s"] > .25 for p in pairs),
           "metrics": {}}
    for phase, time_key, count in (("prefill", "prompt_ms", "prompt_n"),
                                   ("decode", "predicted_ms", "predicted_n")):
        # Scale decode rounds to a common token count when deciding whether times are repeatable.
        ref_n = min(r["native"][count] for r in alone + peers)
        a_s = [r["native"][time_key] / 1000 * ref_n / max(1, r["native"][count]) for r in alone]
        p_s = [r["native"][time_key] / 1000 * ref_n / max(1, r["native"][count]) for r in peers]
        deltas = [p - a for a, p in zip(a_s, p_s)]
        variation = max(max(a_s) - min(a_s), max(p_s) - min(p_s))
        margin = variation
        same_arm_counts = all(len({token_counts(r) for r in rows}) == 1 for rows in (alone, peers))
        repeatable = (len(pairs) >= 2 and all(abs(x) > margin for x in deltas)
                      and (all(x > 0 for x in deltas) or all(x < 0 for x in deltas))
                      and out["all_peer_windows_intersect"] and same_arm_counts and not mismatch)
        if phase == "decode" and generation_diverged:
            repeatable = False
        out["metrics"][phase] = {
            "comparison_tokens": ref_n, "alone_s": a_s, "peer_s": p_s, "peer_minus_alone_s": deltas,
            "same_arm_max_range_s": variation, "required_effect_s": margin, "repeatable": repeatable,
            "within_repeat_range": all(abs(x) <= margin for x in deltas),
            "observed_arm_phase_delta_s": [(p["native"][time_key] - a["native"][time_key]) / 1000
                                           for a, p in zip(alone, peers)]}
    return out


def pair(endpoint, label, ordinal, kinds, fixed=None):
    endpoint.check(20)
    record = {"ordinal": ordinal, "order": list(kinds), "fixed_token_cap": fixed}
    for kind in kinds:
        record[kind] = arm(endpoint, label, ordinal, kind, fixed)
    save_json(endpoint.out / f"{label}-p{ordinal}.pair.json", record)
    return record


def smoke(endpoint):
    payload = {
        "messages": [{"role": "user", "content": "Reply READY."}],
        "chat_template_kwargs": {"enable_thinking": False},
        "max_tokens": 16, "temperature": 0, "stream": True, "timings_per_token": True,
        "id_slot": 0, "cache_prompt": True}
    first = endpoint.stream("smoke", "synthetic", payload)
    with endpoint.http("/slots/0?action=save", {"filename": "smoke.slot"}, timeout=15) as res:
        saved = json.load(res)
    restored = endpoint.restore({"slot": 0, "filename": "smoke.slot", "save": saved})
    second = endpoint.stream("smoke-restored", "synthetic", payload)
    if second["native"]["cache_n"] <= 0:
        raise RuntimeError("smoke restore did not reuse cache")
    return {"ok": True, "first": first, "restored": restored, "second": second}


def measure(endpoint, result):
    for label in TARGETS:
        pairs = result["pairs"][label] = []
        schedule = (("alone", "preserved", "peer"), ("peer", "preserved", "alone")) if label == "OFF56" else (
                    ("alone", "peer"), ("peer", "alone"))
        for kinds in schedule:
            record = pair(endpoint, label, len(pairs) + 1, kinds)
            pairs.append(record)
            if "preserved" in record:
                result["preserve_thinking"].append({"ordinal": record["ordinal"], "order": record["order"],
                    "alone": record["alone"], "preserved": record["preserved"]})
            save_json(endpoint.out / "RESULT.json", result)
        verdict = compare(pairs)
        if verdict["material_output_length_or_finish_difference"]:
            peers, alone = paired_rows(pairs, "peer"), paired_rows(pairs, "alone")
            fixed = min(256, min(x["native"]["predicted_n"] for x in peers + alone))
            if fixed >= 32:
                control = pair(endpoint, label, 3, ("alone", "peer"), fixed)
                result["fixed_controls"][label] = control
                a, p = control["alone"]["target"], control["peer"]["target"]
                verdict["fixed_control"] = {
                    "context_matched": token_counts(a) == token_counts(p),
                    "equal_generated_tokens": a["native"]["predicted_n"] == p["native"]["predicted_n"] == fixed,
                    "peer_minus_alone_native_decode_s":
                    (p["native"]["predicted_ms"] - a["native"]["predicted_ms"]) / 1000,
                    "reversed_confirmation_available": False}
        elif not (any(x["repeatable"] for x in verdict["metrics"].values()) and
                  all(x["repeatable"] or x["within_repeat_range"] for x in verdict["metrics"].values())):
            pairs.append(pair(endpoint, label, 3, ("alone", "peer")))
            verdict = compare(pairs)
        result["attribution"][label] = verdict
        save_json(endpoint.out / "RESULT.json", result)
    result["complete"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-inputs", action="store_true")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--out", type=Path)
    cli = parser.parse_args()
    global ROOT
    if cli.root:
        ROOT = cli.root
    inputs = Inputs()
    if cli.validate_inputs:
        print(json.dumps(inputs.identities, indent=2))
        return
    os.umask(0o077)
    is_smoke = os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"
    if is_smoke:
        sys.path.insert(0, ROWFLOW_SUPPORT)
        import ak_row_harness
    out = cli.out / ("smoke" if is_smoke else "run")
    out.mkdir(parents=True, exist_ok=True)
    endpoint = Endpoint(out, inputs)
    signal.signal(signal.SIGTERM, lambda *_: endpoint.stop.set())
    signal.signal(signal.SIGINT, lambda *_: endpoint.stop.set())
    result = {"schema": "epyc.ap-w66-pair.v1", "complete": False, "started_at_unix": time.time(),
              "source_csv_sha256": inputs.pins["source_csv_sha256"],
              "sealed_input_manifest_sha256": digest_file(inputs.pins_path), "sources": inputs.identities,
              "state_plan_sha256": digest_file(inputs.state_plan_path),
              "pair_limit_per_target": 3, "pairs": {}, "fixed_controls": {}, "attribution": {},
              "preserve_thinking": [], "native_inference_only_no_tool_execution": True}
    outcome = None
    try:
        prefix_file = cli.out.parent / "prefixes.json"
        if digest_file(prefix_file) != PREFIX_SHA:
            raise RuntimeError("private C22 tokenizer receipt digest mismatch")
        endpoint.prefix_plan = json.loads(prefix_file.read_text())
        result["private_prefix_receipt_sha256"] = PREFIX_SHA
        load_start = time.monotonic()
        endpoint.start()
        load_s = time.monotonic() - load_start
        if is_smoke:
            outcome = smoke(endpoint)
        else:
            measure(endpoint, result)
    except (Exception, KeyboardInterrupt) as error:
        result.update(error=str(error), error_type=type(error).__name__)
        if is_smoke:
            ak_row_harness.end_smoke("FAIL", 1, str(error), cli.out)
        raise
    finally:
        try:
            endpoint.close()
        except RuntimeError as error:
            result.update(cleanup_error=str(error), complete=False)
            if is_smoke:
                ak_row_harness.end_smoke("FAIL", 1, str(error), cli.out)
            raise
        finally:
            result["ended_at_unix"] = time.time()
            save_json(out / "RESULT.json", result)
    if outcome:
        ak_row_harness.write_smoke_measure("out/smoke",
                                          (outcome["first"]["wall_s"] + outcome["second"]["wall_s"]) / 2,
                                          2, load_s, "streamed synthetic endpoint probe")
        ak_row_harness.end_smoke("PASS", 0, "C22 identity, split KV, residency, streaming and slot restore",
                                 cli.out, extra=outcome)


if __name__ == "__main__":
    main()
