#!/usr/bin/env node
// Idempotent patcher: teach `gitnexus analyze` to emit progress under non-TTY.
//
// WHY: gitnexus already computes pipeline progress and feeds it to a cli-progress
// SingleBar (dist/cli/analyze.js). That bar is a TTY widget — cli-progress
// defaults to noTTYOutput:false, so when stdout is not a terminal (our wrapper /
// the agent harness capture output) it renders NOTHING for the entire multi-minute
// run. The data exists; it's just thrown away. This injects a tiny non-TTY
// renderer that prints plain `[gitnexus +Ns] NN% | <phase>` lines to stderr on
// every phase change AND on a 15s heartbeat (so the long single-threaded tail —
// cross-file / MRO / Leiden communities / process tracing — still shows liveness).
//
// DURABILITY: gitnexus is a global npm package; `npm update -g gitnexus` wipes
// dist/. This patch is sentinel-guarded and re-applied by scripts/gitnexus-analyze.sh
// on every invocation, so it self-heals after upgrades.
//
// SAFETY: best-effort. If an anchor isn't found (upstream refactored analyze.js)
// the script warns and exits 0 WITHOUT modifying the file — it must never block or
// corrupt an analyze run.
'use strict';

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SENTINEL = 'EPYC-NONTTY-PROGRESS-PATCH v1';

function resolveAnalyzeJs() {
  // Allow override for testing against a scratch copy.
  if (process.env.GITNEXUS_DIST_ANALYZE) return process.env.GITNEXUS_DIST_ANALYZE;
  let binReal;
  try {
    const bin = execSync('command -v gitnexus', { shell: '/bin/bash' }).toString().trim();
    binReal = fs.realpathSync(bin); // .../dist/cli/index.js
  } catch {
    return null;
  }
  const candidate = path.join(path.dirname(binReal), 'analyze.js');
  return fs.existsSync(candidate) ? candidate : null;
}

function pkgVersion(analyzeJs) {
  try {
    // analyze.js -> dist/cli/, package.json is two dirs up at the package root.
    const root = path.resolve(path.dirname(analyzeJs), '..', '..');
    return require(path.join(root, 'package.json')).version || 'unknown';
  } catch {
    return 'unknown';
  }
}

// Each entry: a unique anchor that must exist verbatim, and its replacement.
function buildPatches(version) {
  const stateBlock =
`    // Track elapsed time per phase
    let lastPhaseLabel = 'Initializing...';
    let phaseStart = Date.now();`;

  const stateBlockPatched = stateBlock + `
    // ${SENTINEL} (gitnexus ${version}) — non-TTY progress renderer.
    const __EPYC_NON_TTY = !process.stdout.isTTY;
    let __epycLastPhase = null;
    let __epycLastPrint = 0;
    const __epycEmit = () => {
        if (!__EPYC_NON_TTY) return;
        const now = Date.now();
        const phaseChanged = lastPhaseLabel !== __epycLastPhase;
        if (!phaseChanged && now - __epycLastPrint < 15000) return;
        __epycLastPhase = lastPhaseLabel;
        __epycLastPrint = now;
        const el = Math.round((now - phaseStart) / 1000);
        process.stderr.write(\`[gitnexus +\${el}s] \${Math.round(barCurrentValue)}% | \${lastPhaseLabel}\\n\`);
    };`;

  const updateBarBody =
`        const display = elapsed >= 3 ? \`\${phaseLabel} (\${elapsed}s)\` : phaseLabel;
        bar.update(value, { phase: display });
    };`;

  const updateBarBodyPatched =
`        const display = elapsed >= 3 ? \`\${phaseLabel} (\${elapsed}s)\` : phaseLabel;
        bar.update(value, { phase: display });
        __epycEmit();
    };`;

  const timerBlock =
`    const elapsedTimer = setInterval(() => {
        const elapsed = Math.round((Date.now() - phaseStart) / 1000);
        if (elapsed >= 3) {
            bar.update({ phase: \`\${lastPhaseLabel} (\${elapsed}s)\` });
        }
    }, 1000);`;

  const timerBlockPatched =
`    const elapsedTimer = setInterval(() => {
        const elapsed = Math.round((Date.now() - phaseStart) / 1000);
        if (elapsed >= 3) {
            bar.update({ phase: \`\${lastPhaseLabel} (\${elapsed}s)\` });
        }
        __epycEmit();
    }, 1000);`;

  return [
    { name: 'state-block', from: stateBlock, to: stateBlockPatched },
    { name: 'updateBar-body', from: updateBarBody, to: updateBarBodyPatched },
    { name: 'elapsedTimer', from: timerBlock, to: timerBlockPatched },
  ];
}

function main() {
  const target = resolveAnalyzeJs();
  if (!target) {
    process.stderr.write('gitnexus-patch: could not locate gitnexus dist/cli/analyze.js — skipping (analyze will run unpatched).\n');
    return 0;
  }

  let src = fs.readFileSync(target, 'utf8');
  if (src.includes(SENTINEL)) {
    process.stderr.write(`gitnexus-patch: already patched (${SENTINEL}).\n`);
    return 0;
  }

  const version = pkgVersion(target);
  const patches = buildPatches(version);

  // Verify every anchor exists exactly once before mutating anything.
  for (const p of patches) {
    const count = src.split(p.from).length - 1;
    if (count !== 1) {
      process.stderr.write(
        `gitnexus-patch: anchor "${p.name}" found ${count}x (expected 1) — gitnexus ${version} internals changed; skipping (analyze will run unpatched).\n`);
      return 0;
    }
  }

  for (const p of patches) src = src.replace(p.from, p.to);

  // Atomic write next to the target.
  const tmp = target + '.epyc-tmp';
  fs.writeFileSync(tmp, src, 'utf8');
  fs.renameSync(tmp, target);
  process.stderr.write(`gitnexus-patch: applied non-TTY progress patch to ${target} (gitnexus ${version}).\n`);
  return 0;
}

process.exit(main());
