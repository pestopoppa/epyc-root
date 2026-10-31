// Execute a dashboard page's script blocks against a payload, under minimal DOM
// stubs, and report what threw and what was rendered. Emits JSON on stdout.
//
// Stubs rather than jsdom on purpose: jsdom is not installed here, and a test that
// skips forever is a test nobody notices is gone. The render path builds HTML strings
// and assigns innerHTML, which these stubs model faithfully enough to execute it.
//
// OPTIONAL third-and-later argv entries name the render functions to call. With
// none, the default NAMES list runs and nothing about the existing callers
// changes. This exists because the two freshness envelopes live in
// `renderCommandBand` and `renderProgression`, and `renderCommandBand` is fed by
// a DIFFERENT endpoint (/api/kernel/live) than the default list (/api/kernel) —
// adding it to NAMES would make every existing caller run it against a payload
// it was never written for.
const fs = require('fs');
const [, , pageJsPath, payloadPath, ...wanted] = process.argv;
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
    // `replaceChildren` is used by the command band's stepper. Without it the
    // stub throws a TypeError and the band's freshness verdict never renders —
    // a missing stub method is indistinguishable from a page-side fault.
    replaceChildren() {}, insertAdjacentHTML() {},
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

const NAMES = wanted.length ? wanted
  : ['render', 'renderCurrentState', 'renderSections', 'renderActivity',
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
// `by_id` is ADDITIVE, and it exists because a whole-page substring check is a
// key that is too wide: asserting that "100%" is absent from the joined page
// failed on the "+3.100%" in an unrelated table. A test that can only ask about
// the whole page cannot ask about one panel, so it asks a looser question and
// then passes (or fails) for the wrong reason. Existing consumers read
// `html`/`threw`/`ran` and are untouched.
const by_id = {};
for (const [id, el] of Object.entries(made)) by_id[id] = el._html || '';
// `text_by_id` is likewise ADDITIVE. Some verdicts are written with textContent
// rather than innerHTML, and a harness that only reports innerHTML cannot see
// them — an assertion about such an element would silently be an assertion about
// the empty string, which passes for the wrong reason.
const text_by_id = {};
for (const [id, el] of Object.entries(made)) text_by_id[id] = el._text || '';
// `class_by_id` is likewise ADDITIVE, and it exists because a mutation got
// through. A freshness badge carries its verdict in TWO places: the word in its
// text node, and the state in its className, which is what COLOURS it. Swapping
// only the class yields a green pill reading "STALE" — one producer's liveness
// painted over another's silence, with the correct word still sitting on it. The
// harness reported innerHTML and textContent, neither of which can see that, so
// the assertion was unwritable and folding two producers' envelopes into one went
// undetected by a suite that had a test named for exactly that risk. Existing
// consumers read `html`/`threw`/`ran`/`by_id`/`text_by_id` and are untouched.
const class_by_id = {};
for (const [id, el] of Object.entries(made)) class_by_id[id] = el.className || '';
console.log(JSON.stringify({ threw, ran, html, by_id, text_by_id, class_by_id,
                             names: NAMES, rendered_chars: html.length }));
