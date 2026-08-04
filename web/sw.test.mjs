#!/usr/bin/env node
// Behavioral tests for web/sw.js's fetch handler — the offline / "lie-fi" contract that this file
// exists to hold. sw.js is dense with invariant-carrying prose; this is the executable half.
//
// It loads sw.js UNMODIFIED under mocked Service Worker globals (self, caches, fetch, Response,
// URL) and a FAKE clock, so the network-timeout bounds (NET_TIMEOUT_MS / NET_TIMEOUT_COLD_MS) are
// exercised deterministically and instantly instead of by real waiting. No dependencies.
//
//     node web/sw.test.mjs
//
// Exits non-zero on any failed assertion, so it drops straight into CI (see .github/workflows).
import { readFileSync } from "node:fs";

// ---- fake clock ------------------------------------------------------------
// sw.js's withTimeout() is the only timer user; the rest of the code is microtask-driven. A "slow"
// fetch simply never settles, so advancing this clock past a bound is what fires the timeout.
let now = 0;
let nextTimer = 1;
const timers = new Map();
const fakeSetTimeout = (fn, ms) => { const id = nextTimer++; timers.set(id, { at: now + (ms || 0), fn }); return id; };
const fakeClearTimeout = (id) => { timers.delete(id); };
const flush = async (n = 60) => { for (let i = 0; i < n; i++) await Promise.resolve(); };
async function tick(ms) {
  const target = now + ms;
  await flush();
  for (;;) {
    let dueId = null, dueAt = Infinity;
    for (const [id, t] of timers) if (t.at <= target && t.at < dueAt) { dueId = id; dueAt = t.at; }
    if (dueId === null) break;
    const t = timers.get(dueId);
    timers.delete(dueId);
    now = t.at;
    t.fn();
    await flush();
  }
  now = target;
  await flush();
}

// ---- mocked SW environment -------------------------------------------------
const ORIGIN = "https://ex.test";
const BASE = ORIGIN + "/haydn-info-card/";
const b = (p) => BASE + p;

let fetchMode = "ok";        // "ok" | "slow" | "offline" | "offline-heal"
let fetchStatus = 200;       // status for "ok" mode
let fetchCalls = 0;
let healEntry = null;        // [url, response] inserted by "offline-heal" before it rejects
const CACHE = new Map();     // url -> response

const makeResponse = (body, { status = 200, redirected = false, type = "basic" } = {}) => ({
  _body: body, status, ok: status >= 200 && status < 300, redirected, type,
  clone() { return makeResponse(body, { status, redirected, type }); },
});
const href = (r) => (typeof r === "string" ? new URL(r, self.location).href : r.url);
const req = (url, mode = "no-cors") => ({ url, method: "GET", mode });

const self = {
  location: new URL(BASE + "sw.js"),
  registration: {},
  clients: { claim: async () => {} },
  skipWaiting: async () => {},
  _listeners: {},
  addEventListener(t, fn) { (this._listeners[t] ||= []).push(fn); },
};
const location = self.location;
const ResponseCtor = function (body, init = {}) { return makeResponse(body, { status: init.status || 200 }); };

const cacheApi = {
  async match(r) { return CACHE.get(href(r)); },
  async put(r, resp) { CACHE.set(href(r), resp); },
  async keys() { return [...CACHE.keys()].map((url) => ({ url })); },
};
const caches = {
  async open() { return cacheApi; },
  async match(r) { return CACHE.get(href(r)); },
  async keys() { return ["haydn-v15"]; },
  async delete() { return true; },
};
const fetchImpl = async (r) => {
  fetchCalls++;
  if (fetchMode === "offline") throw new Error("offline");
  if (fetchMode === "offline-heal") { if (healEntry) CACHE.set(href(healEntry[0]), healEntry[1]); throw new Error("offline"); }
  if (fetchMode === "slow") return new Promise(() => {});   // never settles → only a timeout ends it
  return makeResponse("NET:" + href(r), { status: fetchStatus });
};

// ---- load sw.js under those globals ----------------------------------------
const src = readFileSync(new URL("./sw.js", import.meta.url), "utf8");
new Function("self", "location", "caches", "fetch", "Response", "URL", "setTimeout", "clearTimeout", src)(
  self, location, caches, fetchImpl, ResponseCtor, URL, fakeSetTimeout, fakeClearTimeout,
);
const fetchHandler = self._listeners.fetch[0];

// Drive one request through the handler; returns a promise for whatever respondWith() settles to.
function start(request) {
  let settle;
  const done = new Promise((res) => (settle = res));
  fetchHandler({ request, respondWith: (p) => Promise.resolve(p).then(settle), waitUntil() {} });
  return done;
}
const bodyOf = (r) => (r ? (r._body ?? "(generated page)") : "(undefined!)");
const isPending = async (p) => (await Promise.race([p.then(() => false), flush().then(() => true)]));

// ---- assertions ------------------------------------------------------------
let pass = 0, fail = 0;
const ok = (name, cond, detail = "") => { if (cond) { pass++; console.log("  ok   -", name); } else { fail++; console.log("  FAIL -", name, detail); } };
function reset(mode = "ok", status = 200) { CACHE.clear(); fetchMode = mode; fetchStatus = status; fetchCalls = 0; healEntry = null; now = 0; timers.clear(); }
const seedBootableShell = () => { CACHE.set(BASE, makeResponse("CACHED_ROOT")); CACHE.set(b("index.html"), makeResponse("CACHED_INDEX")); CACHE.set(b("scatter.html"), makeResponse("CACHED_SCATTER")); CACHE.set(b("d3.v7.min.js"), makeResponse("CACHED_D3")); CACHE.set(b("app.js"), makeResponse("CACHED_APP")); };

(async () => {
  // --- cache-first happy path: instant, zero network -----------------------
  reset("slow"); seedBootableShell();
  let r = await start(req(BASE, "navigate"));
  ok("cached+bootable nav → cache, 0 fetches", bodyOf(r) === "CACHED_ROOT" && fetchCalls === 0, `body=${bodyOf(r)} fetches=${fetchCalls}`);

  reset("slow"); seedBootableShell();
  r = await start(req(b("d3.v7.min.js")));
  ok("cached subresource → cache, 0 fetches", bodyOf(r) === "CACHED_D3" && fetchCalls === 0, `fetches=${fetchCalls}`);

  reset("slow"); seedBootableShell();
  r = await start(req(b("scatter.html"), "navigate"));
  ok("scatter nav → its OWN page (not index)", bodyOf(r) === "CACHED_SCATTER" && fetchCalls === 0);

  // --- first run ------------------------------------------------------------
  reset("ok");
  r = await start(req(BASE, "navigate"));
  ok("first-run online nav → network response", bodyOf(r) === "NET:" + BASE && fetchCalls === 1);

  reset("offline");
  r = await start(req(BASE, "navigate"));
  ok("first-run offline nav → real fallback page", r && r.status === 503, `status=${r && r.status}`);

  reset("offline");
  r = await start(req(b("icon-192.png")));
  ok("uncached image offline → real 504", r && r.status === 504, `status=${r && r.status}`);

  // --- ISSUE 1: the COLD (no-cache) path must be BOUNDED, not infinite ------
  reset("slow");   // nothing cached + lie-fi: the previously-unbounded path
  let p = start(req(BASE, "navigate"));
  await tick(3001);
  ok("cold lie-fi nav still pending at 3s (WARM bound must not apply)", await isPending(p));
  await tick(14000);   // now ~17s total, past the 15s COLD bound
  r = await p;
  ok("cold lie-fi nav → bounded, honest fallback (issue 1)", r && r.status === 503, `status=${r && r.status}`);

  // --- WARM bound: cached-but-unbootable + lie-fi resolves at 3s ------------
  reset("slow");
  CACHE.set(BASE, makeResponse("CACHED_ROOT"));   // doc cached, d3 absent → not bootable
  p = start(req(BASE, "navigate"));
  await tick(2999);
  ok("warm lie-fi nav still pending just before 3s", await isPending(p));
  await tick(3);
  r = await p;
  ok("warm lie-fi nav → fallback at ~3s (does NOT wait 15s)", r && r.status === 503, `status=${r && r.status}`);

  // --- ISSUE 2: a navigation 5xx must NOT serve the unbootable cached doc ---
  reset("ok", 500);
  CACHE.set(BASE, makeResponse("CACHED_UNBOOTABLE_ROOT"));   // cached but d3 absent
  r = await start(req(BASE, "navigate"));
  ok("nav + server 500 → honest fallback, not bare doc (issue 2)", r && r.status === 503 && bodyOf(r) !== "CACHED_UNBOOTABLE_ROOT", `status=${r && r.status} body=${bodyOf(r)}`);

  // subresource 5xx keeps the old behavior (a real response, not a fallback page)
  reset("ok", 500);
  r = await start(req(b("app.js")));
  ok("subresource + server 500 → returns the response (unchanged)", r && r.status === 500, `status=${r && r.status}`);

  // --- ISSUE 3: the catch re-reads the cache, catching a mid-window repair --
  reset("offline-heal");
  CACHE.set(b("d3.v7.min.js"), makeResponse("CACHED_D3"));      // so bootable() passes in the catch
  healEntry = [b("scatter.html"), makeResponse("REPAIRED_SCATTER")];   // "ensure-shell" repairs during the fetch
  r = await start(req(b("scatter.html"), "navigate"));
  ok("catch re-reads cache → serves mid-window repair (issue 3)", bodyOf(r) === "REPAIRED_SCATTER", `body=${bodyOf(r)}`);

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
