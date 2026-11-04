"""Exact functions from the reviewed M4 patched runner; fixture, never a launcher.

Full candidate SHA-256: be37320e2a54c31476fb05406f5fffa945fd29275f93f61f0ab25eb9f59ab01a
"""
from __future__ import annotations

def residency_sample_inside_batch(
    samples: list[dict[str, Any]], *, pid: int, batch_start_ns: int, batch_end_ns: int
) -> bool:
    """Require a completed own-PID sample wholly inside the request window.

    Monotonic values share this process's clock; they are not wall timestamps.
    Reject malformed intervals rather than treating an earlier warmup sample as
    evidence of GPU residency during request processing.
    """
    if type(pid) is not int or pid <= 0 or type(batch_start_ns) is not int or type(batch_end_ns) is not int or batch_end_ns < batch_start_ns:
        return False
    for sample in samples:
        start = sample.get('sample_start_monotonic_ns')
        end = sample.get('sample_end_monotonic_ns')
        if (sample.get('pid') == pid and type(start) is int and type(end) is int
                and batch_start_ns <= start <= end <= batch_end_ns):
            return True
    return False

def run_cell(
    *,
    model: ModelSpec,
    np_level: int,
    prompts: list[PromptSpec],
    args: argparse.Namespace,
    output_dir: Path,
    cell_index: int,
) -> dict[str, Any]:
    port = args.port_base + cell_index
    log_path = output_dir / "logs" / f"{model.label}-np{np_level}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_server_command(
        binary=args.llama_server,
        model=model,
        port=port,
        np_level=np_level,
        threads=args.threads,
        context_size=args.context_size,
        ubatch_size=args.ubatch_size,
        kv_type=args.kv_type,
        flash_attn=not args.no_flash_attn,
        jinja=not args.no_jinja,
        mlock=not args.no_mlock,
        extra_args=args.extra_server_arg,
    )
    if args.dry_run:
        return {
            "timestamp": utc_now(),
            "protocol_id": "P-BENCH-3",
            "model": model.label,
            "registry_key": model.registry_key,
            "model_path": str(model.path),
            "np": np_level,
            "server_command": command,
            "dry_run": True,
        }

    proc: subprocess.Popen[str] | None = None
    stop_result: dict[str, Any] | None = None
    try:
        proc = start_server(command, build_env(model.label, args.llama_server), log_path)
        pidfile = os.environ.get('FILLER_PIDFILE')
        if not pidfile:
            raise RuntimeError('owned PID registry missing')
        with open(pidfile, 'a', encoding='utf-8') as owned:
            owned.write(f'{proc.pid}\n')
        wait_for_health(port, args.startup_timeout, proc)
        owner = subprocess.run(['ss', '-ltnp', f'sport = :{port}'], capture_output=True, text=True, check=True)
        if f'pid={proc.pid},' not in owner.stdout:
            raise RuntimeError('health port is not owned by the captured server PID')
        maps = Path(f"/proc/{proc.pid}/maps").read_text().splitlines()
        ggml = [line for line in maps if "libggml" in line]
        prefix = str(args.llama_server.resolve().parent) + "/"
        if not ggml or any(not line.split()[-1].startswith(prefix) for line in ggml):
            raise RuntimeError("live ggml maps do not exclusively name the candidate image")
        (output_dir / f"ggml-maps-{cell_index}.txt").write_text("\n".join(ggml) + "\n")
        kfd = Path('/sys/class/kfd/kfd/proc')
        vram_limit = int(os.environ.get('M4_VRAM_LIMIT_BYTES', '0'))
        own_vram = sum(int(f.read_text()) for f in (kfd / str(proc.pid)).glob('vram_*'))
        device_vram = int(Path('/sys/class/drm/card2/device/mem_info_vram_used').read_text())
        if vram_limit <= 0 or own_vram <= 0 or own_vram > vram_limit or device_vram <= 0 or len(list(kfd.iterdir())) < 1:
            raise RuntimeError('GPU residency/VRAM limit unproven before warmup')
        warmup_prompts = prompts[: args.warmup_prompts]
        if warmup_prompts:
            warmup_path = output_dir / "warmup_requests.jsonl"
            run_prompt_batch(
                port=port,
                model=model,
                np_level=np_level,
                prompts=warmup_prompts,
                n_predict=min(args.n_predict, args.warmup_n_predict),
                request_timeout_s=args.request_timeout,
                requests_path=warmup_path,
            )
        ttft_ms = measure_stream_ttft(port, prompts[0], args.request_timeout) if args.measure_ttft else 0.0
        requests_path = output_dir / "requests.jsonl"
        samples: list[dict[str, Any]] = []
        sample_stop = threading.Event()
        sample_ready = threading.Event()
        vram_limit = int(os.environ.get('M4_VRAM_LIMIT_BYTES', '0'))
        if vram_limit <= 0:
            raise RuntimeError('reviewed own-process VRAM ceiling missing')
        def sample_residency() -> None:
            while not sample_stop.is_set():
                kfd = Path('/sys/class/kfd/kfd/proc')
                try:
                    sample_start_ns = time.monotonic_ns()
                    own = sum(int(f.read_text()) for f in (kfd / str(proc.pid)).glob('vram_*'))
                    device = int(Path('/sys/class/drm/card2/device/mem_info_vram_used').read_text())
                    kfd_count = len(list(kfd.iterdir()))
                    sample_end_ns = time.monotonic_ns()
                    samples.append({'timestamp': utc_now(), 'pid': proc.pid, 'own_vram_bytes': own,
                                    'device_vram_bytes': device, 'kfd_process_count': kfd_count,
                                    'sample_start_monotonic_ns': sample_start_ns,
                                    'sample_end_monotonic_ns': sample_end_ns})
                    if own > vram_limit:
                        os.kill(proc.pid, signal.SIGTERM)
                        sample_stop.set()
                except (OSError, ValueError):
                    samples.append({'timestamp': utc_now(), 'pid': proc.pid, 'error': 'unreadable residency'})
                sample_ready.set()
                sample_stop.wait(1.0)
        sampler = threading.Thread(target=sample_residency, daemon=True)
        sampler.start()
        if not sample_ready.wait(5) or not samples or samples[0].get('own_vram_bytes',0) <= 0 or samples[0].get('device_vram_bytes',0) <= 0 or samples[0].get('kfd_process_count',0) < 1 or samples[0].get('own_vram_bytes',0) > vram_limit:
            sample_stop.set(); sampler.join(timeout=5)
            raise RuntimeError('GPU residency unproven before request batch')
        try:
            batch_start_ns = time.monotonic_ns()
            results, wall_s = run_prompt_batch(
                port=port, model=model, np_level=np_level, prompts=prompts,
                n_predict=args.n_predict, request_timeout_s=args.request_timeout,
                requests_path=requests_path,
            )
            batch_end_ns = time.monotonic_ns()
        finally:
            sample_stop.set(); sampler.join(timeout=5)
        if sampler.is_alive() or not samples or any(s.get('own_vram_bytes', 0) <= 0 or s.get('own_vram_bytes', 0) > vram_limit or s.get('device_vram_bytes', 0) <= 0 or s.get('kfd_process_count', 0) < 1 for s in samples):
            raise RuntimeError('GPU residency unproven during request batch')
        if not residency_sample_inside_batch(samples, pid=proc.pid, batch_start_ns=batch_start_ns, batch_end_ns=batch_end_ns):
            raise RuntimeError('no completed own-PID GPU residency sample within request batch')
        row = summarize_cell(
            model=model,
            np_level=np_level,
            results=results,
            wall_s=wall_s,
            ttft_ms=ttft_ms,
            server_pid=proc.pid,
            server_command=command,
        )
        row["server_log"] = str(log_path)
        row['gpu_residency_during'] = samples
        row['gpu_residency_batch_start_monotonic_ns'] = batch_start_ns
        row['gpu_residency_batch_end_monotonic_ns'] = batch_end_ns
        row['ggml_maps'] = str(output_dir / f"ggml-maps-{cell_index}.txt")
        return row
    finally:
        if proc is not None:
            stop_result = stop_server(proc)
            write_jsonl(
                output_dir / "events.jsonl",
                {
                    "timestamp": utc_now(),
                    "event": "server_stopped",
                    "model": model.label,
                    "np": np_level,
                    "port": port,
                    "result": stop_result,
                },
            )
