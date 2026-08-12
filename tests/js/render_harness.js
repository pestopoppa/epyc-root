// Execute a dashboard page's script blocks against a payload, under minimal DOM
// stubs, and report what threw and what was rendered. Emits JSON on stdout.
//
// Stubs rather than jsdom on purpose: jsdom is not installed here, and a test that
// skips forever is a test nobody notices is gone. The render path builds HTML strings
// and assigns innerHTML, which these stubs model faithfully enough to execute it.
const fs = require('fs');
const [, , pageJsPath, payloadPath] = process.argv;
const src = fs.readFileSync(pageJsPath, 'utf8');
const data = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));

const made = {};
function mkEl(id) {
  return made[id] || (made[id] = {
    id, style: {}, _html: '',
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text || ''; },
    setAttribute() {}, removeAttribute() {}, appendChild() {}, removeChild() {},
    addEventListener() {}, remove() {}, getContext() { return null; },
    querySelector(s) { return mkEl(id + '>' + s); }, querySelectorAll() { return []; },
  });
}
global.document = {
  getElementById: mkEl, querySelector: (s) => mkEl(s), querySelectorAll: () => [],
  createElement: () => mkEl('created'), createElementNS: () => mkEl('createdNS'),
  addEventListener: () => {}, body: mkEl('body'),
};
global.window = { addEventListener: () => {}, location: { href: '' } };
global.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve(data) });
global.setInterval = () => 0;
global.setTimeout = () => 0;

const NAMES = ['render', 'renderCurrentState', 'renderSections', 'renderActivity',
               'renderReporting'];
const probe = NAMES.map(n => `${n}: typeof ${n}==="function" ? ${n} : null`).join(', ');

let ctx;
try {
  ctx = eval(src + `\n; ({${probe}})`);
} catch (e) {
  console.log(JSON.stringify({ load_error: e.message, threw: ['LOAD: ' + e.message],
                               ran: 0, html: '', rendered_chars: 0 }));
  process.exit(0);
}

const threw = [];
let ran = 0;
for (const name of NAMES) {
  const fn = ctx[name];
  if (typeof fn !== 'function') continue;
  try { fn(data); ran++; } catch (e) { threw.push(`${name}: ${e.message}`); }
}
const html = Object.values(made).map(e => e._html || '').join('');
console.log(JSON.stringify({ threw, ran, html, rendered_chars: html.length }));
