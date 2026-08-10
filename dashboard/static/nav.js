/* EPYC shared dashboard nav — RTG-47 Phase 0.
 *
 * THE ONE cross-dashboard nav. Before this, every page hand-copied a `<nav>`;
 * they were written at different times and drifted into a link matrix with holes
 * (audit 1.3 in handoffs/active/dashboard-architecture-restructure.md) — reaching
 * AutoKernel meant routing through the handoff board, and cross-server URLs were
 * re-derived ad hoc in three places. Links now come from ONE machine-readable
 * registry (`dashboard/registry.json`), inlined ahead of this file by
 * `server.nav_asset()` as `window.__EPYC_DASHBOARDS`, so a new dashboard is a
 * registry row rather than a fifth hand-edited header.
 *
 * DEPENDENCY-FREE AND HOST-AGNOSTIC. No framework, no globals beyond this IIFE,
 * no layout assumptions about the page it lands on (it styles only its own
 * container and links, and takes its colours from the host's CSS variables with
 * fallbacks). It is safe to include anywhere, including on :8000's page later.
 *
 * FAILS QUIET, NOT WRONG: no registry, an empty registry or a hostile shape ⇒ one
 * console line and nothing rendered. The LOUD version of that fact belongs to
 * `/api/dashboards` and the handoff board's directory strip, which can say
 * *why* it is empty; a nav that draws an error banner into every page header
 * cannot.
 */
(function () {
  "use strict";

  var NAV_ID = "epyc-nav";
  var STYLE_ID = "epyc-nav-style";
  var LEGACY_ID = "orchestrator-legacy";
  var warned = false;

  function warnOnce(msg) {
    if (warned) return;
    warned = true;
    try { console.warn("[epyc-nav] " + msg); } catch (e) { /* no console: fine */ }
  }

  /* location.port is "" for the protocol default, and the registry always
   * carries an explicit port — so compare like with like or every page on a
   * default port would render with no active link. */
  function currentPort() {
    if (location.port) return String(location.port);
    return location.protocol === "https:" ? "443" : "80";
  }

  /* "/kernel/" and "/kernel" are the same page (the hub rstrips the route);
   * "" and "/" are the root. */
  function normPath(p) {
    var s = String(p == null ? "" : p).replace(/\/+$/, "");
    return s === "" ? "/" : s;
  }

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var css = [
      ".epyc-nav{display:flex;flex-direction:row;flex-wrap:wrap;align-items:center;",
      "gap:14px;font-size:12px;line-height:1.5}",
      ".epyc-nav .epyc-nav-link{display:inline-flex;align-items:center;gap:5px;",
      "font-size:12px;white-space:nowrap;text-decoration:none;",
      "color:var(--muted,#8b949e);transition:color .12s ease-in-out}",
      ".epyc-nav .epyc-nav-link:hover,.epyc-nav .epyc-nav-link:focus{",
      "color:var(--accent,#60a5fa);text-decoration:underline}",
      /* border-bottom/padding are neutralised, not inherited: several host pages
       * carry a `nav a.active{border-bottom:2px solid …}` rule left over from the
       * hand-rolled navs, and one page decorating its active link differently from
       * the next is the drift this component replaces. */
      ".epyc-nav .epyc-nav-link.active{color:var(--accent,#60a5fa);font-weight:650;",
      "border-bottom:0;padding-bottom:0}",
      ".epyc-nav .epyc-nav-chip{font-size:9px;letter-spacing:.04em;text-transform:uppercase;",
      "padding:0 4px;border-radius:8px;border:1px solid currentColor;",
      "color:var(--muted,#8b949e);opacity:.7}"
    ].join("");
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.appendChild(document.createTextNode(css));
    (document.head || document.documentElement).appendChild(style);
  }

  function mount() {
    var host = document.getElementById(NAV_ID);
    if (host) return host;
    if (!document.body) return null;
    host = document.createElement("nav");
    host.id = NAV_ID;
    document.body.insertBefore(host, document.body.firstChild);
    return host;
  }

  function render() {
    var list = window.__EPYC_DASHBOARDS;
    if (!Array.isArray(list) || list.length === 0) {
      warnOnce("no dashboard registry on this page (window.__EPYC_DASHBOARDS is " +
               (Array.isArray(list) ? "empty" : "absent") + ") — nav not rendered. " +
               "See /api/dashboards for why.");
      return;
    }
    var host = mount();
    if (!host) {
      warnOnce("no #" + NAV_ID + " element and no <body> to create one in — " +
               "nav not rendered.");
      return;
    }
    injectStyle();
    host.classList.add("epyc-nav");

    var port = currentPort();
    var here = normPath(location.pathname);
    var frag = document.createDocumentFragment();
    var rendered = 0;

    for (var i = 0; i < list.length; i++) {
      var e = list[i];
      if (!e || typeof e !== "object" || !e.path || e.port == null) continue;
      var a = document.createElement("a");
      a.className = "epyc-nav-link";
      a.href = location.protocol + "//" + location.hostname + ":" + e.port + e.path;
      a.textContent = String(e.title == null ? e.id : e.title);
      if (e.blurb) a.title = String(e.blurb);
      if (String(e.port) === port && normPath(e.path) === here) {
        a.className = "epyc-nav-link active";
        a.setAttribute("aria-current", "page");
      }
      if (e.id === LEGACY_ID) {
        var chip = document.createElement("span");
        chip.className = "epyc-nav-chip";
        chip.textContent = "legacy";
        a.appendChild(chip);
      }
      frag.appendChild(a);
      rendered++;
    }
    if (!rendered) {
      warnOnce("dashboard registry carries no usable entries (each needs a port " +
               "and a path) — nav not rendered.");
      return;
    }
    host.textContent = "";
    host.appendChild(frag);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
})();
