const grid = document.querySelector("[data-catalog-grid]");
const dialog = document.querySelector("dialog");
const detail = document.querySelector("[data-detail]");
const escape = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let liveWaves = [];
let records = [],
  models = [],
  selected,
  filter = "all",
  query = "",
  tab = "matrix",
  mode = "unified",
  metric = "perreq";
const release =
  "https://github.com/pestopoppa/llama.cpp/releases/tag/production-consolidated-v10";
const sourceURL = (path) =>
  "https://github.com/pestopoppa/epyc-inference-research/blob/main/" + path;
const record = (id) => records.find((r) => r.id === id);
const facts = (pairs) =>
  '<div class="facts">' +
  pairs
    .map(
      ([k, v]) =>
        "<div><span>" + escape(k) + "</span><b>" + escape(v) + "</b></div>",
    )
    .join("") +
  "</div>";
function buildModels() {
  models = [
    {
      id: "qwen38",
      name: "Qwen3.8-27B",
      type: "gpu",
      family: "DENSE · TEXT",
      quant: "Q8_0",
      value: "39.9–40.2",
      unit: "tok/s",
      caption: "Live native MTP · single request · two waves",
      badge: "9-cell KV comparison",
      matrix: record("v10-qwen38-kv-unified-matrix"),
      curve: record("v10-mi210-qwen38-dflash2"),
      depth: 8,
      description:
        "Run a dense 27B model on one MI210. Explore live concurrency, the native-MTP context study, and a separate DFlash2 qualification curve.",
    },
    {
      id: "qwen36",
      name: "Qwen3.6-35B-A3B",
      type: "gpu",
      family: "MIXTURE OF EXPERTS · TEXT",
      quant: "Q8_0 · native MTP",
      value: "93.9",
      unit: "tok/s",
      caption: "Unified KV · 1 request · 2k generation limit",
      badge: "12-cell KV comparison",
      matrix: record("v10-mi210-qwen36-matrix"),
      depth: 4,
      description:
        "35B total parameters, 3B active. Explore the MI210 study up to eight simultaneous requests; this model also has an EPYC CPU result.",
    },
    {
      id: "qwen-vl",
      name: "Qwen3-VL-30B-A3B",
      type: "gpu",
      family: "VISION-LANGUAGE MODEL",
      quant: "Q4_K_M · text-only speed test",
      value: "116.04",
      unit: "tok/s",
      caption: "Single request · speculative decoding off",
      badge: "Concurrency 1 → 4",
      curve: record("v10-mi210-qwen-vl30b"),
      description:
        "A vision-capable 30B MoE on one MI210. This qualification curve measures text-only requests, with no image projector or image workload.",
    },
    {
      id: "qwen36-cpu",
      name: "Qwen3.6-35B-A3B",
      type: "cpu",
      family: "MIXTURE OF EXPERTS · TEXT",
      quant: "Q8_0 · MTP model",
      value: "64.38",
      unit: "tok/s",
      caption: "Frozen v10 CPU qualification · 5 repetitions",
      badge: "Also explored on MI210",
      description:
        "The CPU qualification result for the 35B model. Compare the separately configured GPU study in its MI210 card; these are not matched CPU/GPU trials.",
      cpu: true,
    },
    {
      id: "stt",
      name: "Whisper large-v3-turbo",
      type: "cpu",
      family: "SPEECH RECOGNITION",
      quant: "F16 · frozen speech-v1",
      value: "10.52",
      unit: "seconds",
      caption: "86.5 seconds of audio · 32 threads · n=2",
      badge: "Explore the thread sweep",
      description:
        "Transcribe locally on EPYC. Compare thread counts and CPU affinity using both short and long audio clips.",
      speech: true,
    },
    {
      id: "tts",
      name: "Qwen3-TTS 0.6B",
      type: "cpu",
      family: "STREAMING SPEECH SYNTHESIS",
      quant: "Q8_0 talker + codec · speech-v1",
      value: "84",
      unit: "ms first packet",
      caption: "Short sentence · PCM streaming · median of 3",
      badge: "Latency + real-time factor",
      description:
        "Streaming speech generation on CPU. Inspect first-packet latency, total generation time and audio duration across tested thread counts.",
      speech: true,
    },
  ];
}
function renderCatalog() {
  const visible = models.filter(
    (m) =>
      (filter === "all" || m.type === filter) &&
      (m.name + " " + m.family + " " + m.quant).toLowerCase().includes(query),
  );
  grid.innerHTML =
    visible
      .map(
        (m) =>
          '<article class="card"><div class="card-top"><span class="family">' +
          escape(m.family) +
          '</span><span class="chip">' +
          (m.type === "gpu" ? "MI210" : "EPYC") +
          "</span></div><h3>" +
          escape(m.name) +
          '</h3><div class="subtitle">' +
          escape(m.quant) +
          '</div><div class="metric"><strong>' +
          escape(m.value) +
          "</strong><span>" +
          escape(m.unit) +
          '</span></div><div class="metric-note">' +
          escape(m.caption) +
          '</div><div class="card-foot"><span>' +
          escape(m.badge) +
          '</span><button data-model="' +
          m.id +
          '" aria-label="Explore ' +
          escape(m.name) +
          " on " +
          (m.type === "gpu" ? "MI210" : "EPYC") +
          '">Explore ↗</button></div></article>',
      )
      .join("") ||
    '<p class="empty">No models match. Try a different name or hardware filter.</p>';
}
const table = (headers, rows) =>
  '<div class="table-scroll"><table class="data-table"><thead><tr>' +
  headers.map((h) => '<th scope="col">' + escape(h) + "</th>").join("") +
  "</tr></thead><tbody>" +
  rows
    .map(
      (row) =>
        "<tr>" +
        row.map((c) => "<td>" + escape(c) + "</td>").join("") +
        "</tr>",
    )
    .join("") +
  "</tbody></table></div>";
function segments(key, options, value) {
  return (
    '<div class="segments" aria-label="' +
    escape(key) +
    '">' +
    options
      .map(
        ([id, label]) =>
          '<button data-control="' +
          key +
          '" data-value="' +
          id +
          '" class="' +
          (value === id ? "active" : "") +
          '" aria-pressed="' +
          (value === id) +
          '">' +
          label +
          "</button>",
      )
      .join("") +
    "</div>"
  );
}
function matrixPanel(m) {
  const r = m.matrix,
    aggregate = metric === "aggregate";
  const extra = metric === "accept" || metric === "vram";
  const index = aggregate
    ? mode === "split"
      ? 4
      : 5
    : mode === "split"
      ? 2
      : 3;
  const getValue = (row) => {
    if (!extra) return Number(row[index]);
    const cell = r.study.find(
      (c) =>
        c.arm === mode &&
        c.np === row[1] &&
        c.L === String({ "2k": 2048, "8k": 8192, "32k": 32768 }[row[0]]),
    );
    return metric === "accept"
      ? Number(cell.draft_accept) * 100
      : Number(cell.vram_gib);
  };
  const values = r.matrix.map(getValue);
  const lo = Math.min(...values),
    hi = Math.max(...values);
  const rows = [1, 2, 4, 8]
    .map(
      (np) =>
        '<tr><th scope="row">' +
        np +
        " " +
        (np === 1 ? "request" : "requests") +
        "</th>" +
        ["2k", "8k", "32k"]
          .map((ctx) => {
            const row = r.matrix.find(
              (row) => row[0] === ctx && Number(row[1]) === np,
            );
            if (!row)
              return (
                '<td class="missing">' +
                (ctx === "2k" ? "VRAM guard" : "Out of memory") +
                "<small>No throughput sample</small></td>"
              );
            const value = getValue(row),
              split = Number(row[aggregate ? 4 : 2]),
              unified = Number(row[aggregate ? 5 : 3]);
            const delta = (unified / split - 1) * 100;
            return (
              '<td style="background:rgba(157,117,226,' +
              (0.14 + (0.55 * (value - lo)) / (hi - lo || 1)).toFixed(3) +
              ')">' +
              value.toFixed(1) +
              (metric === "accept" ? "%" : "") +
              "<small>" +
              (extra
                ? metric === "accept"
                  ? "draft acceptance"
                  : "whole-device GiB"
                : mode === "unified"
                  ? (delta >= 0 ? "+" : "") + delta.toFixed(1) + "% vs split"
                  : "split KV") +
              "</small></td>"
            );
          })
          .join("") +
        "</tr>",
    )
    .join("");
  return (
    "<h3>Concurrency × generation / context</h3><p>How much speed does each request keep as the server gets busier?</p>" +
    '<div class="controls">' +
    segments(
      "mode",
      [
        ["unified", "Unified KV"],
        ["split", "Split KV"],
      ],
      mode,
    ) +
    segments(
      "metric",
      [
        ["perreq", "Per-request"],
        ["aggregate", "Aggregate"],
        ["accept", "Acceptance"],
        ["vram", "VRAM"],
      ],
      metric,
    ) +
    "</div>" +
    '<table class="heatmap"><caption class="muted">' +
    (metric === "accept"
      ? "Mean draft acceptance · % · not answer accuracy"
      : metric === "vram"
        ? "Whole-device VRAM after load · GiB · includes other residents"
        : aggregate
          ? "Wall-clock aggregate · tok/s · higher is faster"
          : "Median per-request decode · tok/s · higher is faster") +
    '</caption><thead><tr><th scope="col">Concurrent<br>requests (np)</th><th scope="col">2k generation</th><th scope="col">8k generation</th><th scope="col">32k generation</th></tr></thead><tbody>' +
    rows +
    '</tbody></table><div class="legend">Lower <i></i> Higher within this view</div>' +
    '<p class="note">One wave per cell (n=1), no measured noise floor. The columns are generation limits L, not prompt lengths. Total context c = (L + 1,024) × np. Different completions can change aggregate throughput; percentage differences are observations, not proven gains.</p>' +
    facts([
      ["Native MTP draft depth", m.depth + " tokens"],
      ["KV cache / weights", "Q8_0 / Q8_0"],
      ["Workload", "OlympiadBench hard · temperature 0.6 · seed 42"],
      ["Kernel", "v10 · ffc1bac82 · MI210"],
    ]) +
    (m.id === "qwen38"
      ? "<p>Eight slots exceeded the 62 GiB whole-device guard at 2k, and failed to allocate at 8k/32k. These are missing measurements, not zero speed.</p>"
      : "<p>All 24 mode/shape runs completed. At np=8, L=32k, the allocated pool is 270,336 tokens; the unified per-request ceiling is capped at 262,144.</p>") +
    "<details><summary>Inspect every measured cell and context allocation</summary>" +
    table(
      [
        "L",
        "np",
        "Pool c",
        "Split tok/s",
        "Unified tok/s",
        "Split aggregate",
        "Unified aggregate",
      ],
      r.matrix.map((row) => [
        row[0],
        row[1],
        (
          ({ "2k": 2048, "8k": 8192, "32k": 32768 }[row[0]] + 1024) *
          Number(row[1])
        ).toLocaleString(),
        ...row.slice(2, 6),
      ]),
    ) +
    "</details>"
  );
}
function curvePanel(m) {
  const r = m.curve,
    rows = r.matrix || [
      ["1", "116.04"],
      ["2", "173.45"],
      ["4", "192.92"],
    ];
  const max = Math.max(...rows.map((row) => Number(row[1])));
  return (
    "<h3>" +
    (m.id === "qwen38"
      ? "DFlash2 serving curve"
      : "Vision-model serving curve") +
    '</h3><p>Sum of concurrent requests’ server-reported decode rates · median of three launches per point.</p><div class="bar-chart">' +
    rows
      .map(
        (row) =>
          '<div class="bar-row"><span>np = ' +
          row[0] +
          '</span><div class="bar-track"><div class="bar" style="width:' +
          (Number(row[1]) / max) * 100 +
          '%"></div></div><strong>' +
          row[1] +
          " tok/s</strong></div>",
      )
      .join("") +
    "</div>" +
    (m.id === "qwen38"
      ? '<p class="note">Context 65,536 · 3 launches per point. This DFlash2 measurement is separate from the native-MTP KV matrix. At np=8, the summed decode rate reaches 184.48 tok/s; that sum divided by eight is 23.06 tok/s, not a measured median request rate.</p>'
      : '<p class="note">Context 65,536 · speculative decoding off · three launches per point. Text-only requests with no image projector: this is not image-processing throughput. These accepted v10 qualification runs are distinct from current serving recipes.</p>') +
    table(
      ["Concurrent requests", "Sum of request decode tok/s"],
      rows.map((row) => row.slice(0, 2)),
    )
  );
}

function livePanel() {
  return (
    "<h3>One GPU. Four simultaneous requests.</h3><p>The live 27B server was tested with fixed 1,024-token outputs, two waves at each concurrency. These rates include elapsed wall time.</p>" +
    '<div class="bar-chart">' +
    [1, 2, 4]
      .map((np) => {
        const waves = liveWaves.filter((w) => w.conc === np),
          low = Math.min(...waves.map((w) => w.agg_tps)),
          high = Math.max(...waves.map((w) => w.agg_tps));
        return (
          '<div class="bar-row"><span>' +
          np +
          " request" +
          (np > 1 ? "s" : "") +
          '</span><div class="bar-track"><div class="bar" style="width:' +
          (high / 95.3) * 100 +
          '%"></div></div><strong>' +
          low +
          "–" +
          high +
          "</strong></div>"
        );
      })
      .join("") +
    '</div><p class="muted">Total completed tokens / wall time · tok/s · higher is faster</p>' +
    table(
      ["Concurrency", "Wave", "Wall throughput", "Per-request median"],
      liveWaves.map((w) => [
        w.conc,
        w.wave,
        w.agg_tps + " tok/s",
        w.perreq_med_tps + " tok/s",
      ]),
    ) +
    facts([
      ["Shared context pool", "196,608 tokens · unified KV"],
      ["Acceleration", "Native MTP · draft depth 4"],
      ["Output control", "1,024 tokens · ignore_eos · temperature 0"],
      ["Sampling", "2 waves per concurrency · exploratory"],
    ]) +
    '<h3>A longer document in one request</h3><p>A separate depth-8 probe accepted a <strong>124,174-token prompt</strong> in unified mode. Split KV at np=2 rejected it at the 98,304-token slot ceiling. Unified prefill measured 399.9 tok/s in this one probe.</p><p class="note">The KV matrix uses MTP depth 8 and a different workload; the DFlash2 curve uses another recipe and a summed-rate metric. Treat these as separate experiments.</p>'
  );
}
function speechPanel(m) {
  if (m.id === "stt")
    return (
      "<h3>86.5 seconds of audio. 10.52 seconds to transcribe.</h3><p>CPU-only Whisper large-v3-turbo F16. Median processing time over two long-clip or three short-clip repetitions.</p>" +
      table(
        ["Threads / affinity", "11 s clip", "86.5 s clip", "Long-clip RTF"],
        [
          ["8 / 0–7", "4.44 s", "25.54 s", "0.295"],
          ["16 / 0–15", "2.78 s", "16.34 s", "0.189"],
          ["24 / 0–23", "2.17 s", "14.42 s", "0.167"],
          ["32 / 0–39", "1.53 s", "10.52 s", "0.122"],
        ],
      ) +
      '<p class="note">Affinity matters: 32 threads confined to cores 0–31 took 20.47 seconds for the 11-second clip, versus 1.53 seconds when allowed cores 0–39. The fastest long-clip result spans 9.00–12.04 seconds (n=2).</p>' +
      "<h3>Keep CPU room for speech</h3><p>STT and TTS stayed faster than real time together on their tested separate CPU allocations while the CPU LLM was idle. Overlapping an all-core LLM severely degraded speech; these component results do not establish a complete voice-assistant latency.</p>"
    );
  return (
    "<h3>Hear the first packet, then keep streaming.</h3><p>Qwen3-TTS 0.6B Q8_0, PCM streaming. The short output is 4.24 seconds of audio; the long output is 35.68 seconds.</p>" +
    table(
      [
        "Threads",
        "Short first packet",
        "Short RTF",
        "Long first packet",
        "Long RTF",
      ],
      [
        ["8", "113 ms", "0.727", "329 ms", "0.759"],
        ["16", "84 ms", "0.547", "238 ms", "0.595"],
        ["24", "75 ms", "0.609", "185 ms", "0.589"],
        ["32", "85 ms", "0.658", "257 ms", "0.551"],
      ],
    ) +
    '<p class="note">Medians: n=3 short, n=2 long. The 16-thread short first-packet range was 84–420 ms. First packet is not playback-ready latency; the study used a 0.5-second playback buffer for its non-LLM-contention runs.</p>' +
    facts([
      ["16-thread long narration", "35.68 s audio generated in 21.24 s"],
      ["Solo affinity", "0–15 (16-thread headline)"],
      ["Voice settings", "seed 42 · no voice field · PCM"],
      ["RTF", "Processing time / audio duration · lower is better"],
    ]) +
    "<p>Concurrent all-core LLM work can cause severe latency and real-time-factor regressions. Reserve and test CPU capacity before combining services.</p>"
  );
}
function speechRecipe(m) {
  return (
    "<h3>" +
    (m.id === "stt"
      ? "Whisper CPU configuration"
      : "Qwen TTS CPU configuration") +
    "</h3>" +
    facts(
      m.id === "stt"
        ? [
            ["Kernel", "whisper.cpp · production-speech-v1 · b3073792"],
            ["Model", "ggml-large-v3-turbo.bin · F16"],
            ["CPU backend", "HIP_VISIBLE_DEVICES=-1 · -ng"],
            ["Headline launch", "-t 32 · taskset -c 0-39"],
          ]
        : [
            ["Kernel", "qwentts.cpp · production-speech-v1 · 2c1b518"],
            ["Models", "0.6B base Q8_0 talker + 12 Hz Q8_0 tokenizer"],
            ["CPU backend", "GGML_BACKEND=CPU · HIP_VISIBLE_DEVICES=-1"],
            ["Threads", "16 via nprocs shim · SHIM_NPROCS=32"],
          ],
    ) +
    "<p>Each service must use its own build directory in LD_LIBRARY_PATH. The TTS thread limiter is host-specific and the binary has no thread-count CLI flag; consult the study harness before reproducing the configuration.</p>" +
    '<p><a class="source-link" href="' +
    sourceURL("artifacts/speech_cpu_realtime_20260924/README.md") +
    '">Read the full speech study and setup ↗</a></p><p><a class="source-link" href="' +
    sourceURL("artifacts/speech_cpu_realtime_20260924/speech_cpu_bench.py") +
    '">Inspect the reproduction harness ↗</a></p>' +
    '<p class="note">These measurements used the existing frozen speech binaries. The llama.cpp download does not include speech kernels or model weights.</p>'
  );
}

function overviewPanel(m) {
  if (m.speech) return speechPanel(m);
  return (
    "<h3>Large-model inference on CPU</h3><p>" +
    escape(m.description) +
    "</p>" +
    facts([
      ["Generation throughput", m.value + " tok/s"],
      ["Hardware", "AMD EPYC 9655"],
      ["Weight quantization", m.quant],
      ["Qualification sampling", "5 fresh process launches · 1 request each"],
      ["Observed range", "62.60–65.30 tok/s"],
      ["Actual input / output", "965 prompt tokens / 128 generated tokens"],
      ["Configured context / slots", "12,800 tokens / 4 slots"],
      ["CPU recipe", "96 threads · native MTP depth 4"],
    ]) +
    '<p class="note">This is a single qualification point using the model’s production-role recipe. No np × context matrix is available in this published record. It should not be compared directly with a differently configured GPU experiment.</p>'
  );
}
function recipePanel(m) {
  if (m.speech) return speechRecipe(m);
  if (m.cpu)
    return (
      "<h3>EPYC CPU qualification recipe</h3>" +
      facts([
        ["CPU / placement", "96 threads · NUMA interleave across all nodes"],
        ["Environment", "GGML_IQK=1 · OMP_NUM_THREADS=1"],
        ["Backend", "CPU only · all GPU visibility disabled"],
        ["KV / acceleration", "Q8_0 · flash attention · MTP depth 4"],
        ["Server allocation", "np=4 · context=12,800"],
        ["Memory flags", "--mlock --no-mmap"],
      ]) +
      '<p>The qualification sends one measured request per fresh process; four configured slots do not demonstrate four-user CPU throughput. The current larger context configuration is a different operating point.</p><p><a class="source-link" href="' +
      sourceURL(
        "data/kernel-v9-candidate/promotion-plan-20260921/champion-ffc1bac82-cpu/commands.sh",
      ) +
      '">Exact recorded commands ↗</a></p><p><a class="source-link" href="' +
      release +
      '">Get the frozen CPU binaries ↗</a></p>'
    );
  if (!m.matrix)
    return (
      '<h3>Reproduce from the source record</h3><p>The source includes the qualification settings and measurement protocol. Check these before comparing your own system.</p><p><a class="source-link" href="' +
      sourceURL(
        m.curve ? m.curve.source : record("v10-cpu-production-matrix").source,
      ) +
      '">Read the measured configuration ↗</a></p><p><a class="source-link" href="' +
      release +
      '">Download the frozen llama.cpp release ↗</a></p><p>Model weights are downloaded separately. The recorded drivers include launch flags and request settings; adapt their local paths before use.</p>'
    );
  const name =
    m.id === "qwen38"
      ? "Qwen3.8-27B-Q8_0.gguf"
      : "Qwen3.6-35B-A3B-MTP-Q8_0.gguf";
  return (
    "<h3>The matrix recipe</h3><p>Example for np=2 and L=8,192 (total context 18,432). Set MODEL to your separately downloaded GGUF and GPU_BIN to the extracted GPU bin directory. HIP/ROCm runtime dependencies must be installed.</p><pre><code>" +
    escape(
      'export LD_LIBRARY_PATH="$GPU_BIN/../lib:$GPU_BIN"\n"$GPU_BIN/llama-server" -m "$MODEL" \\\n  -ngl all -fa on --no-mmap -t 8 -tb 8 \\\n  -b 2048 -ub 2048 -ctk q8_0 -ctv q8_0 \\\n  --spec-type draft-mtp --spec-draft-n-max DEPTH \\\n  -np 2 -c 18432 --kv-unified --reasoning off'.replace(
        "DEPTH",
        String(m.depth),
      ),
    ) +
    "</code></pre><p>Measured artifact: <code>" +
    escape(name) +
    '</code>. The original runs pinned host CPUs 184–191 and used the terse template. Adapt CPU affinity to your machine and consult the source driver for the complete template and harness settings. This is a launch example, not the full benchmark harness.</p><a class="source-link" href="' +
    release +
    '">Release downloads + verification guide ↗</a>'
  );
}
function evidencePanel(m) {
  const ids =
    m.id === "qwen38"
      ? [
          "v10-qwen38-kv-unified-matrix",
          "v10-mi210-qwen38-dflash2",
          "v10-qwen38-production-traffic",
          "v10-qwen38-unified-context",
        ]
      : m.matrix
        ? ["v10-mi210-qwen36-matrix"]
        : m.curve
          ? ["v10-mi210-qwen-vl30b"]
          : m.speech
            ? ["speech-production-v1-cpu-baseline"]
            : ["v10-cpu-production-matrix"];
  return (
    "<h3>Follow the measurement</h3><p>Each result retains its recipe and scope. Source links open the research repository and may require access.</p>" +
    ids
      .map((id) => {
        const r = record(id);
        return (
          "<section><h3>" +
          escape(m.cpu ? "Qwen3.6-35B CPU qualification" : r.title) +
          "</h3><p>" +
          escape(
            m.cpu
              ? "Five repetitions, one measured request per launch; frozen v10 CPU qualification."
              : r.detail,
          ) +
          "</p><p><strong>" +
          escape(m.cpu ? "64.38 tok/s median decode" : r.headline) +
          '</strong></p><a class="source-link" href="' +
          sourceURL(r.source) +
          '">Read source evidence ↗</a></section>'
        );
      })
      .join("") +
    (m.speech
      ? '<p><a class="source-link" href="' +
        sourceURL(
          "artifacts/speech_cpu_realtime_20260924/raw/summary_tables.md",
        ) +
        '">Speech sweep tables, sample counts and ranges ↗</a></p>'
      : "") +
    '<p class="note">Measurements are from September 2026. Frozen source identity does not turn an exploratory sample into a ratified performance claim.</p>'
  );
}
function renderDetail() {
  const m = selected;
  const tabs = [
    ...(m.id === "qwen38" ? [["live", "Live serving"]] : []),
    ...(m.matrix ? [["matrix", "KV matrix"]] : []),
    ...(m.curve ? [["curve", "Serving curve"]] : []),
    ...(!m.matrix && !m.curve ? [["overview", "Results"]] : []),
    ["recipe", "Configuration"],
    ["evidence", "Evidence"],
  ];
  detail.innerHTML =
    '<div class="detail-heading"><span class="chip">' +
    (m.type === "gpu" ? "AMD Instinct MI210 · gfx90a" : "AMD EPYC 9655") +
    '</span><h2 id="detail-title">' +
    escape(m.name) +
    "</h2><p>" +
    escape(m.description) +
    '</p></div><div class="tabs" aria-label="Model sections">' +
    tabs
      .map(
        ([id, label]) =>
          '<button data-tab="' +
          id +
          '" class="' +
          (id === tab ? "active" : "") +
          '" aria-pressed="' +
          (id === tab) +
          '">' +
          label +
          "</button>",
      )
      .join("") +
    '</div><div class="panel">' +
    (tab === "live"
      ? livePanel()
      : tab === "matrix"
        ? matrixPanel(m)
        : tab === "curve"
          ? curvePanel(m)
          : tab === "recipe"
            ? recipePanel(m)
            : tab === "evidence"
              ? evidencePanel(m)
              : overviewPanel(m)) +
    "</div>";
}
grid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-model]");
  if (!button) return;
  selected = models.find((m) => m.id === button.dataset.model);
  tab =
    selected.id === "qwen38"
      ? "live"
      : selected.matrix
        ? "matrix"
        : selected.curve
          ? "curve"
          : "overview";
  mode = "unified";
  metric = "perreq";
  renderDetail();
  dialog.showModal();
  dialog.scrollTop = 0;
});
detail.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button) return;
  let focus;
  if (button.dataset.tab) {
    tab = button.dataset.tab;
    focus = '[data-tab="' + tab + '"]';
  } else if (button.dataset.control) {
    if (button.dataset.control === "mode") mode = button.dataset.value;
    else metric = button.dataset.value;
    focus =
      '[data-control="' +
      button.dataset.control +
      '"][data-value="' +
      button.dataset.value +
      '"]';
  } else return;
  renderDetail();
  detail.querySelector(focus)?.focus({ preventScroll: true });
});
document
  .querySelector("[data-close]")
  .addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) {
    const r = dialog.getBoundingClientRect();
    if (
      event.clientX < r.left ||
      event.clientX > r.right ||
      event.clientY < r.top ||
      event.clientY > r.bottom
    )
      dialog.close();
  }
});
document.querySelectorAll("[data-filter]").forEach((button) =>
  button.addEventListener("click", () => {
    filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach((b) => {
      b.classList.toggle("active", b === button);
      b.setAttribute("aria-pressed", String(b === button));
    });
    renderCatalog();
  }),
);
document
  .querySelector("input[type=search]")
  .addEventListener("input", (event) => {
    query = event.target.value.trim().toLowerCase();
    renderCatalog();
  });
async function init() {
  try {
    const response = await fetch("data/catalog.json");
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    records = data.records;
    liveWaves = data.live_waves;
    buildModels();
    renderCatalog();
  } catch (error) {
    grid.innerHTML =
      '<p class="empty" role="alert">The benchmark data could not be loaded. Please reload this page. ' +
      escape(error.message) +
      "</p>";
  }
}
init();
