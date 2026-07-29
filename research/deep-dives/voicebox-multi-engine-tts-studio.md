# Voicebox Deep-Dive: Multi-Engine TTS Studio

**Intake**: `intake-396` (https://github.com/jamiepine/voicebox)
**Date**: 2026-04-17
**Scope**: Evaluate whether voicebox's engine-adapter / chunking / queue
patterns are directly reusable for an EPYC CPU-only TTS sidecar that could
unblock the TTS component of `handoffs/active/multimodal-pipeline.md`.

**TL;DR**: Voicebox is a desktop voice-cloning *studio* (Tauri + FastAPI +
Python). The backend architecture is cleaner than expected and the
TTS-engine abstraction (`backend/backends/base.py`), chunker
(`backend/utils/chunked_tts.py`), and serial queue
(`backend/services/task_queue.py`) are decoupled from UI concerns and
cheaply reusable. **The ROCm/CPU "multi-platform" story is largely
README marketing**: there is no ROCm auto-configuration code anywhere in
the repo, and CPU is merely "works, just slow" for every engine except
LuxTTS and Kokoro. Net: take the three ~50-300 line utilities as a
starting template; do not chase voicebox itself.

---

## 1. Engine Adapter Design (specific patterns)

### 1.1 `TTSBackend` Protocol (`backend/backends/base.py`)

Voicebox uses a Python `typing.Protocol` (structural typing, not an ABC) —
backends are duck-typed. The surface is deliberately small (6 methods):

```python
@runtime_checkable
class TTSBackend(Protocol):
    async def load_model(self, model_size: str) -> None: ...
    async def create_voice_prompt(
        self, audio_path: str, reference_text: str, use_cache: bool = True,
    ) -> Tuple[dict, bool]: ...                       # (prompt, was_cached)
    async def combine_voice_prompts(
        self, audio_paths: List[str], reference_texts: List[str],
    ) -> Tuple[np.ndarray, str]: ...
    async def generate(
        self, text: str, voice_prompt: dict, language: str = "en",
        seed: Optional[int] = None, instruct: Optional[str] = None,
    ) -> Tuple[np.ndarray, int]: ...                  # (audio, sample_rate)
    def unload_model(self) -> None: ...
    def is_loaded(self) -> bool: ...
```

Returning `(audio: np.ndarray, sample_rate: int)` as the lingua franca is
smart: it decouples the chunker, effects pipeline, WAV encoder, and SSE
layer from engine-specific tensors. Every non-CPU device handoff
(`.detach().cpu().numpy().squeeze()`) happens inside the backend.

### 1.2 `ModelConfig` Declarative Registry

Instead of per-engine `if/elif` in routes, each backend class publishes a
list of `ModelConfig` dataclasses:

```python
@dataclass
class ModelConfig:
    model_name: str          # "qwen-tts-1.7B"
    display_name: str        # "Qwen TTS 1.7B"
    engine: str              # "qwen"
    hf_repo_id: str          # "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    model_size: str = "default"
    size_mb: int = 0
    needs_trim: bool = False
    supports_instruct: bool = False
    languages: list[str] = field(default_factory=lambda: ["en"])
```

Dispatch helpers (`engine_needs_trim`, `engine_has_model_sizes`,
`get_model_config`, `load_engine_model`, `unload_model_by_config`,
`check_model_loaded`) all iterate the config list. Adding a new engine is
a new backend file plus a dict entry in `get_tts_backend_for_engine()`.

**Quality assessment**: clean, not messy glue. One ugly spot:
`get_tts_backend_for_engine()` still has a hardcoded `if engine == "...":`
chain (`backend/backends/__init__.py` lines ~430-480) to avoid importing
every heavy backend eagerly (torch imports are ~3s). That's a reasonable
lazy-load trade-off but contradicts the otherwise data-driven design.

### 1.3 Shared Base Utilities (`backends/base.py`, 280 lines)

This file does NOT contain a base class — all TTS backends are independent
classes that only share free functions:

- `is_model_cached()` — inspects `~/.cache/huggingface/hub` for
  `*.safetensors` / `*.bin` and `.incomplete` markers.
- `get_torch_device(allow_mps, allow_xpu, allow_directml, force_cpu_on_mac)` —
  returns a device string. **NOTE: no ROCm branch** — ROCm on Linux just
  appears as `"cuda"` to PyTorch, same device-string path.
- `empty_device_cache(device)` — `torch.cuda.empty_cache()` /
  `torch.xpu.empty_cache()`. Required for per-model-unload to actually
  free VRAM.
- `model_load_progress(model_name, is_cached)` context manager —
  monkey-patches `tqdm` to drive HF download progress into an SSE pub/sub.
- `combine_voice_prompts()` — loads, normalizes, concatenates multi-sample
  reference audio.
- `patch_chatterbox_f32()` — librosa returns float64; Chatterbox assumes
  float32; one library gets monkey-patched at load time. Dead-giveaway
  that per-engine integration still needs custom patches.

**Reusable for EPYC**: `is_model_cached`, `empty_device_cache`, and the
`ModelConfig` registry + dispatch helpers are drop-in useful for a
CPU-only orchestrator sidecar. `get_torch_device` is uninteresting for
our use.

### 1.4 Instance Management

```python
_tts_backends: dict[str, TTSBackend] = {}
_tts_backends_lock = threading.Lock()
```

One cached backend *per engine*, lazy-instantiated under a threading lock
(double-checked locking pattern). This is what enables "load Chatterbox
and Qwen simultaneously in different VRAM regions" claimed in README —
nothing fancy, just no forced eviction. For EPYC's CPU-only sidecar this
map becomes "at most one loaded engine at a time" (RAM pressure). Per-
model unload (`unload_model_by_config`) is exposed as a REST endpoint.

---

## 2. CPU / ROCm Backend Reality

### 2.1 ROCm: README-only, not code

**Finding**: The README table claims `Linux (AMD) → PyTorch (ROCm) →
Auto-configures HSA_OVERRIDE_GFX_VERSION`. The docs page
`docs/content/docs/overview/gpu-acceleration.mdx` repeats this and even
tells the user what common values are (RX 6000 → `10.3.0`, RX 7000 →
`11.0.0`, Vega → `9.0.0`).

**The code does not do this.** `grep -i -E "rocm|hsa|amd|gfx"` across the
entire repo (926 lines of `tauri/src-tauri/src/main.rs`, all Python
backends, all setup scripts, Dockerfile, justfile) returns zero matches
except the docs. `platform_detect.py` only distinguishes MLX vs PyTorch;
`get_torch_device()` only checks `torch.cuda.is_available()` (which does
cover ROCm's hipified CUDA), MPS, XPU, and DirectML.

**Independent confirmation**: Issue #368 ("not detecting my amd gpu") —
user with RX 6600 (gfx1032, needs `HSA_OVERRIDE_GFX_VERSION=10.3.0`)
reports voicebox runs on CPU, not detecting the GPU. Open, no patch.

**Implication for EPYC**: Voicebox provides zero ROCm tooling beyond
"install a ROCm-compatible PyTorch wheel yourself and it might work."
**Do not cite voicebox as ROCm prior art.** If/when EPYC pursues an AMD
path, start from ROCm-torch's own detection + the fact that the PyTorch
CUDA API covers ROCm transparently — voicebox is no reference here.

### 2.2 CPU: genuinely works only for LuxTTS + Kokoro

The same GPU-acceleration doc's CPU section is more honest than the
feature matrix:

> Some engines work better than others on CPU:
> - Kokoro 82M — runs at realtime on modern CPUs
> - LuxTTS — exceeds 150x realtime on CPU
> - Chatterbox Turbo (350M) — usable but slow
> - Larger models (Qwen 1.7B, Chatterbox Multilingual, TADA 3B) — painful

The LuxTTS backend has the only explicit CPU-tuning code:

```python
# luxtts_backend.py:_load_model_sync
if device == "cpu":
    threads = os.cpu_count() or 4
    self.model = LuxTTS(model_path=LUXTTS_HF_REPO, device="cpu",
                        threads=min(threads, 8))
```

Every other backend just passes `device="cuda"` or falls through to
`device="cpu"` without per-platform knobs. **So "CPU coverage" is really
"LuxTTS on CPU + nothing else tuned."** That said, LuxTTS on a 128-core
EPYC is interesting (threads capped at 8 in voicebox; we could lift that
cap trivially).

Independent benchmark (ysharma3501/LuxTTS repo, third-party blog): CPU
synthesis ~12s for a short phrase, memory <1GB. That's "faster than
realtime" on a laptop and likely much faster on EPYC — but the claim is
unverified on our hardware.

### 2.3 Intake correction

The intake notes listed "ROCm/CPU backend coverage" as an adoptable
pattern. **Remove ROCm from that bullet.** CPU coverage is really just
LuxTTS-specific and deserves a standalone intake-401 follow-up, not a
voicebox credit.

---

## 3. Chunking Algorithm Details

Source: `backend/utils/chunked_tts.py` (~240 lines). This is the most
production-quality piece of code in the repo.

### 3.1 Splitter

```python
def split_text_into_chunks(text: str, max_chars: int = 800) -> List[str]:
```

Priority ladder for finding a split position inside each `max_chars`
window:

1. **Sentence-end** (`.!?\s` or CJK `。！？`) — the last match inside
   the window, with two exclusions:
   - Periods after frozenset of 25 abbreviations (`Mr`, `Dr`, `i.e`,
     `a.m`, `u.s.a`, etc.)
   - Periods preceded by a digit (decimal numbers like `3.14`)
2. **Clause boundary** (`;:,—`) — last match, same bracket-tag exclusion.
3. **Whitespace** (`rfind(" ")`) — any space.
4. **Safe hard cut** — at `max_chars - 1`, but never inside a paralinguistic
   bracket tag like `[laugh]`.

Paralinguistic tags are treated as atomic via a pre-compiled regex
`_PARA_TAG_RE = re.compile(r"\[[^\]]*\]")` and `_inside_bracket_tag()`
check at every decision point.

### 3.2 Crossfade concatenation

```python
def concatenate_audio_chunks(chunks, sample_rate, crossfade_ms=50):
    crossfade_samples = int(sample_rate * crossfade_ms / 1000)
    result = np.array(chunks[0], dtype=np.float32, copy=True)
    for chunk in chunks[1:]:
        overlap = min(crossfade_samples, len(result), len(chunk))
        fade_out = np.linspace(1.0, 0.0, overlap, dtype=np.float32)
        fade_in  = np.linspace(0.0, 1.0, overlap, dtype=np.float32)
        result[-overlap:] = result[-overlap:] * fade_out + chunk[:overlap] * fade_in
        result = np.concatenate([result, chunk[overlap:]])
```

**Linear equal-power crossfade** (not constant-power / square-root).
Default 50ms. Works, simple, cheap. Constant-power would be more correct
for non-correlated signals but for adjacent TTS chunks sharing a voice
prompt the correlation is high and linear is fine. Range 0-200ms matches
the README slider; 0ms = hard cut, which the code handles correctly
(short-circuit on `overlap > 0`).

### 3.3 Seed per chunk

```python
chunk_seed = (seed + i) if seed is not None else None
```

Varies the RNG per chunk to decorrelate artifacts; stays deterministic
for `(text, seed)` pair. Small but thoughtful.

### 3.4 Quality verdict

**Production-quality, not naive.** The abbreviation list, bracket-tag
safety, CJK punctuation, decimal-number handling, and deterministic
per-chunk seed cover the common failure modes. What's *missing*:

- No Unicode sentence segmentation (no ICU / spaCy / nltk); pure regex.
  Fails on languages without `.!?` — Thai, Khmer, some Chinese.
- No length equalization — a long "sentence" that exceeds `max_chars`
  falls through to clause/space/hard cut, which can produce a 50-char
  chunk followed by an 800-char chunk (audible pacing change).
- No context window passthrough — each chunk is generated fresh with only
  the voice prompt, not prior audio context, so prosody resets at each
  boundary. This is a universal TTS issue, not voicebox-specific.

### 3.5 Reusable for EPYC

**Yes.** `split_text_into_chunks()` + `concatenate_audio_chunks()` +
`generate_chunked()` are ~170 lines total, pure numpy/regex, no engine
coupling. They depend only on the `backend.generate()` coroutine
signature `(text, voice_prompt, language, seed, instruct) →
(np.ndarray, sample_rate)`. A direct copy into an EPYC TTS sidecar is
viable after we decide on our own `voice_prompt` representation.

**License**: Voicebox is MIT, no attribution friction.

---

## 4. Queue / SSE Architecture

### 4.1 Serial-execution generation queue

Source: `backend/services/task_queue.py` — a remarkably tiny 40 lines:

```python
_generation_queue: asyncio.Queue = None

async def _generation_worker():
    while True:
        coro = await _generation_queue.get()
        try:
            await coro
        except Exception:
            traceback.print_exc()
        finally:
            _generation_queue.task_done()

def enqueue_generation(coro):
    _generation_queue.put_nowait(coro)

def init_queue():
    global _generation_queue
    _generation_queue = asyncio.Queue()
    create_background_task(_generation_worker())
```

**One worker, unbounded queue, asyncio-native.** Enqueued items are raw
coroutines returned by `run_generation(...)`; they carry all their state.
The worker's `while True` loop serializes every TTS inference so only one
model uses the GPU at a time. Failures are logged but do not kill the
worker. No priorities, no preemption, no cancellation.

**Limits**: unbounded queue + no backpressure means a malicious or
runaway client can OOM the process. No persistence — on crash, in-flight
generations are lost (there is a separate "stale generation recovery" in
the models layer that marks DB rows as failed on startup).

### 4.2 SSE progress layer

Source: `backend/routes/generations.py::get_generation_status` +
`backend/utils/progress.py::ProgressManager`.

Pattern: a `GET /generate/{id}/status` endpoint opens an SSE stream; a
background loop polls the SQLite row every 1s, emits a JSON event, and
closes when `status in ("completed","failed")`. **Polling, not pub/sub**
at the generation level — simple and robust.

For model downloads, the `ProgressManager` *is* pub/sub:
`asyncio.Queue`-per-listener with `call_soon_threadsafe` bridging from
the tqdm background thread. Throttled to 0.5s interval / 1% progress
delta to avoid saturating clients. This is the piece worth borrowing if
EPYC sidecar streams download progress.

### 4.3 Reusable for EPYC

The serial queue is 40 lines and immediately useful for any CPU-only
sidecar where one inference saturates the cores. **Recommend**:
- Copy the queue as-is.
- Add a bounded queue size and a reject-on-full policy (missing in voicebox).
- Keep the DB-polling SSE pattern for generation status — it's cheaper
  to reason about than queue-routed pub/sub and our sidecar is single-
  tenant.
- Borrow `ProgressManager` only if we need multi-listener download
  progress; otherwise skip.

---

## 5. Chatterbox Multilingual — 23 languages claim

README claims 23 languages for Chatterbox Multilingual. The
`ModelConfig` entry in `backends/__init__.py` explicitly enumerates
them: `zh, en, ja, ko, de, fr, ru, pt, es, it, he, ar, da, el, fi, hi,
ms, nl, no, pl, sv, sw, tr`.

This is just an advertised list passed through the HF repo
(`ResembleAI/chatterbox`). The voicebox backend does not test, validate,
or fine-tune per language — it passes `language` through to the
upstream model and trusts ResembleAI. No tokenizer swap, no G2P. For
EPYC-relevant comparison: if we needed Hebrew, Arabic, or Hindi TTS,
Chatterbox is one of the few open options (VoxCPM2 is 30-lang but GPU-
only; LuxTTS is English-only per HF card, ambiguous per blog reviews;
Qwen3-TTS is 10-lang). Relevant to the broader LuxTTS vs alternatives
decision but not currently unblocking anything.

---

## 6. Tauri / Rust overhead

`tauri/src-tauri/src/main.rs` is 926 lines of process-management code:
spawn the Python sidecar, monitor parent PID, handle Windows
`taskkill` vs POSIX `kill`, watchdog sentinels, port conflict
resolution. **None of this is engine-relevant.**

The backend runs as an independent FastAPI server on port 17493. The
Tauri app launches it as a sidecar but could equally be pointed at a
remote URL (and voicebox has a "Remote Mode" documented — it literally
just sets a base URL).

**Extract-only path**: clone the repo, take `backend/` wholesale, drop
`tauri/`, `app/`, `web/`, `landing/`, delete
`backend/services/cuda.py` (which auto-downloads voicebox-branded CUDA
binaries from GitHub Releases — useless outside voicebox), and you have
a standalone ~15k-line FastAPI TTS service. The Dockerfile already does
exactly this (3-stage build, frontend → python → runtime, final image
is `python:3.11-slim + ffmpeg + backend/`). **This is the practical
extraction boundary** — the Dockerfile is our template.

---

## 7. Reusable Patterns for EPYC TTS Sidecar

Graded by extraction effort and EPYC value:

| Pattern | Lines | Effort | Value for EPYC | Recommendation |
|---|---|---|---|---|
| `TTSBackend` Protocol | ~50 | Trivial | High — clean contract for future engines | **Adopt as-is** |
| `ModelConfig` registry + dispatch helpers | ~150 | Low | Medium — EPYC has its own `model_registry.yaml` | Adapt: merge schema into EPYC registry |
| `chunked_tts.py` (split + crossfade + driver) | ~240 | Low | **High — directly unblocks long-form TTS** | **Adopt with minor edits** |
| Serial `asyncio.Queue` worker | ~40 | Trivial | High — matches single-inference CPU constraint | **Adopt, add bounded size** |
| `ProgressManager` SSE pub/sub | ~150 | Medium | Low — overkill for single-tenant sidecar | Skip unless we need multi-listener download UX |
| DB-polling SSE status endpoint | ~30 | Trivial | Medium — simple progress visibility | Adopt if we expose a REST API |
| `model_load_progress()` tqdm monkey-patch | ~60 | Low | Low — nice-to-have download UX | Skip initially |
| `is_model_cached()` HF cache introspection | ~40 | Trivial | Medium — avoids spurious downloads on restart | Adopt |
| `empty_device_cache()` helper | 10 | Trivial | Low (we're CPU-only) | Skip |
| Dockerfile (3-stage build, slim runtime) | ~60 | Trivial | Medium — reference for containerization | Adopt as template |
| Watchdog / parent-PID monitoring | ~100 | — | None | Skip (orchestrator already handles this) |
| Per-engine hardcoded patches (`patch_chatterbox_f32`) | — | — | Signal — expect this per engine | Noted, not copied |

**Total**: ~550 lines of Python are worth copying into an EPYC TTS
sidecar. That's a 1-2-day extraction, not a multi-week build.

---

## 8. Verdict Delta

### Initial intake

- novelty: **medium**
- relevance: **high**
- verdict: **adopt_patterns**

### Post-deep-dive

- novelty: **medium** (unchanged — no new architecture, just clean
  packaging of known components)
- relevance: **high → medium-high** (downgraded) — TTS pipeline is still
  blocked, but voicebox doesn't deliver the "CPU/ROCm multi-backend"
  angle that made it look like a silver bullet. The genuinely reusable
  patterns (chunker, queue, protocol) are small and would save maybe a
  week of work, not months.
- verdict: **adopt_patterns** (unchanged), but **scope narrowed**:
  - Do: port `chunked_tts.py`, `task_queue.py`, `TTSBackend` Protocol,
    `is_model_cached`, Dockerfile template.
  - Do not: cite voicebox's ROCm support (it's README-only).
  - Do not: extract voicebox as-a-whole; it's a desktop studio with
    studio-specific concerns (stories editor, effects chains, timeline,
    Whisper transcription, multi-track mixing) that pull in ~2/3 of the
    backend code we don't need.
  - Do not: block on voicebox for multimodal-pipeline. The real
    unblocker is LuxTTS (intake-401) or another CPU-feasible engine;
    voicebox is a packaging reference, not a dependency.

### Changes from initial intake

1. **ROCm support is fiction** — no code, no auto-config, no detection.
   One open GitHub issue (#368) confirms real users on AMD fall back to
   CPU silently. Drop "ROCm backend coverage" from the adoptable-patterns
   list.
2. **CPU coverage is LuxTTS-specific, not universal** — only LuxTTS
   has per-CPU thread tuning; the other 4 engines are "works, just
   painful" per voicebox's own docs. The CPU story belongs to LuxTTS
   (intake-401), not voicebox.
3. **The adapter is cleaner than expected** — `typing.Protocol` + dataclass
   config registry is a well-designed 6-method surface, not messy glue.
   `backends/base.py` is 280 lines of genuinely shared utilities, not
   duplicated code.
4. **The chunker is production-quality** — abbreviations, bracket tags,
   CJK, decimal numbers, per-chunk seed decorrelation. Not naive. Direct
   copy target.
5. **The queue is 40 lines** — "serial asyncio.Queue worker" is its
   entire implementation. Adopt and add a bounded size. Do not
   over-engineer.
6. **Tauri/Rust is pure process-management** — the Dockerfile already
   shows the extraction boundary: frontend stage is droppable, backend
   stage runs standalone. No Rust needed for an EPYC sidecar.

### Reusable-patterns priority for multimodal-pipeline.md unblock

1. **`chunked_tts.py`** → highest leverage; fixes the "how do we do
   long-form TTS on any engine" problem generically.
2. **`task_queue.py`** → trivial to add, matches our CPU-serial
   reality.
3. **`TTSBackend` Protocol + `ModelConfig`** → shape the EPYC TTS
   sidecar so adding VoxCPM2, LuxTTS, Qwen3-TTS, TADA each means one
   new backend file.
4. Everything else: optional.

### What voicebox does NOT unblock

- It does not provide a CPU-inference engine we don't already know
  about. LuxTTS was discovered *through* voicebox (intake-401), not
  delivered by it.
- It does not provide AMD / ROCm integration code.
- It does not provide formal benchmarks — no MOS, WER, RTF numbers for
  any engine on any hardware.
- It does not provide GGUF / llama.cpp integration for any TTS engine.

**Final call**: voicebox is a **pattern reference**, not a **dependency
or reference implementation** for EPYC's TTS sidecar. Copy three
utilities, skim the Dockerfile, close the tab.
