from pathlib import Path
import json

import producer as p
from settings import (ROOT, ROW, HF, SMHF, GGUF, SMGGUF, C6, SOURCE, BIN, IMAGE, IMAGE_ID,
                      PORTS, llama_args, vllm_args, argv_bytes)

assets = {}


def pin(path):
    path = path.resolve(strict=True)
    key = str(path)
    if key not in assets:
        stat = path.stat()
        assets[key] = {"sha256": p.file_sha(path), "size": stat.st_size,
                       "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns, "inode": stat.st_ino, "device": stat.st_dev}
        after = path.stat()
        assert (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) == (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ), f"asset mutated during pinning: {path}"
    return assets[key]["sha256"]


def explicit(paths):
    return {str(path): pin(path) for path in paths}


def save(path, value):
    p.artifact(path, value)


historical = json.loads((ROOT / "IDENTITY.json").read_bytes())
assert pin(ROOT / "corpus.txt") == historical["corpus_sha256"]
assert pin(ROOT / "prompts-historical.json") == historical["prompts_sha256"]
assert GGUF.stat().st_size == historical["model"]["gguf_bytes"]
llama_pin = pin(BIN / "llama-server")
runtime_links = {
    "libggml-hip": pin(BIN / "libggml-hip.so"),
    "libamdhip64": pin(Path("/opt/rocm/lib/libamdhip64.so")),
}
image, = json.loads((ROOT / "vllm-image-inspect.json").read_bytes())
assert image["Id"] == "sha256:" + IMAGE_ID and IMAGE in image["RepoDigests"]
vllm_path_digests = {}
for line in (ROOT / "vllm-pins.txt").read_text().splitlines()[:4]:
    digest, filename = line.split()
    assert p.SHA.fullmatch(digest)
    vllm_path_digests[filename] = digest
vllm_links = {prefix: next(digest for name, digest in vllm_path_digests.items()
                          if Path(name).name.startswith(prefix + ".so"))
              for prefix in ("libamdhip64", "libtorch_hip")}
tokens = json.loads((ROOT / "tokens.json").read_bytes())
for mode, base, gguf in (("native", HF, GGUF), ("smoke", SMHF, SMGGUF)):
    smoke = mode == "smoke"
    receipts = ROOT / "receipts" / mode
    receipts.mkdir()
    model_files = sorted(base.glob("*.safetensors")) + sorted(base.glob("*.safetensors.index.json"))
    model_files += [base / "config.json", base / "generation_config.json"]
    model = {"identity": base.name, "hf_files": explicit(model_files),
             "gguf": {"path": str(gguf), "sha256": pin(gguf)}}
    if smoke:
        conversion = {"existing_smoke_gguf": model["gguf"],
                      "historical_conversion_log_sha256": pin(gguf.parent / "convert.log"),
                      "scope": "small-model smoke only"}
    else:
        conversion = {"gguf": model["gguf"], "source_commit": C6, "image": IMAGE,
                      "converter_sha256": pin(SOURCE / "convert_hf_to_gguf.py"),
                      "conversion_script_sha256": pin(ROOT / "convert.sh"),
                      "conversion_log_sha256": pin(ROOT / "convert.log"),
                      "historical_gguf_sha256": historical["model"]["gguf_sha256"],
                      "equals_historical_gguf": pin(gguf) == historical["model"]["gguf_sha256"]}
    tokenizer = {"files": explicit(base / name for name in (
                     "tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")),
                 "code_sha256": pin(ROOT / "render_tokens.py"),
                 "corpus_sha256": pin(ROOT / "corpus.txt"), "image": IMAGE,
                 "prompt_tokens_sha256": p.digest(p.canonical(tokens[mode])),
                 "old_512_input_reproduced": not smoke, "add_special_tokens": False}
    llama = {"source_commit": C6, "server_files": explicit(path for path in sorted(BIN.glob("*.so*"))
                                                        if path.is_file()),
             "version_report_sha256": pin(ROOT / "c6-version.txt"),
             "ggml_linkage_report_sha256": pin(ROOT / "c6-ggml-linkage.txt"),
             "executable_sha256": llama_pin, "argv": llama_args(smoke),
             "ld_library_path": str(BIN) + ":/opt/rocm/lib"}
    vllm = {"wheel_version": "0.33.0+rocm100", "build_commit": None, "image": IMAGE,
            "image_id": IMAGE_ID, "image_inspect_sha256": pin(ROOT / "vllm-image-inspect.json"),
            "installed_wheel_provenance_sha256": pin(ROOT / "vllm-wheel-provenance.txt"),
            "installed_sources_and_libraries": vllm_path_digests, "argv": vllm_args()}
    for name, receipt in (("model", model), ("conversion", conversion), ("tokenizer", tokenizer),
                          ("llama", llama), ("vllm", vllm)):
        save(receipts / (name + ".json"), receipt)
    plan = {
        "run_id": ROW, "mode": mode, "prompt_token_ids": tokens[mode], "max_tokens": 128,
        "client_sha256": pin(ROOT / "producer.py"),
        **{name + "_receipt_sha256": pin(receipts / (name + ".json"))
           for name in ("model", "conversion", "tokenizer")}, "arms": {},
    }
    for engine, build, runtime, argv, links in (
        ("llama", C6, llama_pin, llama_args(smoke), runtime_links),
        ("vllm", None, IMAGE_ID, vllm_args(), vllm_links),
    ):
        plan["arms"][engine] = {"build_sha": build, "runtime_sha256": runtime, "links": links,
                                "argv_sha256": p.digest(argv_bytes(argv)), "port": PORTS[engine],
                                "runtime_receipt_sha256": pin(receipts / (engine + ".json"))}
    p.validate_plan(plan)
    save(ROOT / (mode + "-plan.json"), plan)
save(ROOT / "asset-pins.json", assets)
