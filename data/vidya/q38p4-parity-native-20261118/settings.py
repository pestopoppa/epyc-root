from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROW = "q38p4-greedy-parity-20261118-r1"
HF = Path("/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507")
SMHF = Path("/mnt/raid0/llm/models/Qwen3-0.6B-PAW-smoke-c1899de")
GGUF = ROOT / "model/Qwen3-4B-Instruct-2507-BF16.gguf"
SMGGUF = Path("/mnt/raid0/llm/tmp/compute-flags/handoff-sessions/mi210-big-model-and-acceleration-roadmap/q38p4-v4/qwen3-0.6b-bf16.gguf")
C6 = "729599d69871181d67af715a4c2f9162d5153a2e"
SOURCE = Path("/mnt/raid0/llm/worktrees/kernels/refactor-c6-20261030")
BIN = Path("/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6/bin")
IMAGE = "vllm/vllm-openai-rocm@sha256:4fcd39b758b660c4e9c345c021e2ea8f0ccdb31e3c32507d676cc3005ae83fba"
IMAGE_ID = "933f693c6b3b67b39ba789fac7f276251ab017908290bd8c39d10b0f702dae52"
PORTS = {"llama": 19433, "vllm": 19434}
FULL_CPUS = set(range(184, 192))


def llama_args(smoke):
    return [str(BIN / "llama-server"), "-m", str(SMGGUF if smoke else GGUF), "-ngl", "99",
            "-fa", "on", "-c", "8192", "-np", "1", "-t", "4" if smoke else "8",
            "--load-threads", "4" if smoke else "8", "--host", "127.0.0.1",
            "--port", str(PORTS["llama"]), "--no-webui", "--alias", "m"]


def vllm_args():
    return ["python3", "-m", "vllm.entrypoints.openai.api_server", "--model", "/model",
            "--served-model-name", "m", "--dtype", "bfloat16", "--max-model-len", "8192",
            "--max-num-seqs", "1", "--no-enable-prefix-caching", "--generation-config", "vllm",
            "--gpu-memory-utilization", "0.70", "--seed", "0", "--host", "127.0.0.1",
            "--port", str(PORTS["vllm"])]


def argv_bytes(args):
    return b"\0".join(arg.encode() for arg in args) + b"\0"
