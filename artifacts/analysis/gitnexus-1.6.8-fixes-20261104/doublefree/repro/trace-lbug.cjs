// Diagnostic preload (scratch only): trace @ladybugdb/core connection lifecycle.
'use strict';
const fs = require('fs');
const path = require('path');
const out = process.env.LBUG_TRACE_FILE;
if (out) {
  const L = process.env.LBUG_TRACE_PKG || '/usr/local/share/npm-global/lib/node_modules/gitnexus/node_modules/@ladybugdb/core';
  const lbug = require(L + '/index.js');
  const fd = fs.openSync(out, 'a');
  let seq = 0;
  const ids = new WeakMap();
  let nextId = 1;
  const id = (o) => { if (!ids.has(o)) ids.set(o, nextId++); return ids.get(o); };
  const inflight = new Map(); // connId -> count
  const openResults = new Map(); // connId -> count
  const log = (s) => fs.writeSync(fd, `${Date.now()} #${++seq} ${s}\n`);
  const C = lbug.Connection.prototype;
  C.__origQuery = C.query;
  for (const m of ['query', 'execute', 'prepare']) {
    const orig = C[m];
    C[m] = function (...a) {
      const cid = id(this);
      inflight.set(cid, (inflight.get(cid) || 0) + 1);
      const q = typeof a[0] === 'string' ? a[0].slice(0, 60).replace(/\s+/g, ' ') : m;
      const cur = inflight.get(cid);
      if (cur > 1 || /COPY|IGNORE_ERRORS/i.test(q)) log(`Q.${m} conn=${cid} inflight=${cur} q=${q}`);
      let p;
      try { p = orig.apply(this, a); } catch (e) { inflight.set(cid, inflight.get(cid) - 1); throw e; }
      const done = (r) => {
        inflight.set(cid, inflight.get(cid) - 1);
        const rs = Array.isArray(r) ? r : [r];
        for (const x of rs) if (x && typeof x.close === 'function' && x.constructor && /QueryResult/.test(x.constructor.name)) {
          openResults.set(cid, (openResults.get(cid) || 0) + 1);
          ids.set(x, cid * -1);
          const oc = x.close;
          x.close = function () { if (!this.__closed) { this.__closed = true; openResults.set(cid, openResults.get(cid) - 1); } return oc.apply(this, arguments); };
        }
        return r;
      };
      if (p && typeof p.then === 'function') return p.then(done, (e) => { inflight.set(cid, inflight.get(cid) - 1); log(`QERR conn=${cid} q=${typeof a[0]==='string'?a[0].replace(/\s+/g,' ').slice(0,400):m} err=${String(e && e.message).slice(0,200)}`); throw e; });
      return done(p);
    };
  }
  for (const m of ['close', 'closeSync']) {
    const orig = C[m];
    C[m] = function (...a) {
      const cid = id(this);
      log(`CONN.${m} conn=${cid} inflight=${inflight.get(cid) || 0} openResults=${openResults.get(cid) || 0} closed=${this._isClosed} init=${this._isInitialized}\n${new Error().stack.split('\n').slice(2, 12).join('\n')}`);
      if (m === 'close' && !this._isClosed && process.env.LBUG_TRACE_WARN === '1') {
        const self = this, origQ = lbug.Connection.prototype.__origQuery;
        return (async () => {
          try { const r = await origQ.call(self, 'CALL show_warnings() RETURN *'); const rows = await r.getAll(); r.close();
            log(`WARNINGS n=${rows.length} sample=${JSON.stringify(rows.slice(0,3)).slice(0,600)}`); } catch (e) { log('WARNERR ' + e.message); }
          if (process.env.LBUG_TRACE_CLEAR === '1') { try { const r2 = await origQ.call(self, 'CALL clear_warnings()'); await r2.getAll(); r2.close(); log('CLEARED'); } catch (e) { log('CLEARERR ' + e.message); } }
          return orig.apply(self, a);
        })();
      }
      return orig.apply(this, a);
    };
  }
  const D = lbug.Database.prototype;
  for (const m of ['close', 'closeSync']) {
    const orig = D[m];
    D[m] = function (...a) {
      log(`DB.${m} db=${id(this)} closed=${this._isClosed}\n${new Error().stack.split('\n').slice(2, 8).join('\n')}`);
      return orig.apply(this, a);
    };
  }
  process.on('exit', (c) => log(`EXIT ${c}`));
}
