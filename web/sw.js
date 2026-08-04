// pwa-starter: sw.js @ dd763ca
// Service worker: offline shell + cache-busting.  (Pattern from pwa-starter.)
//
// THE ONE RULE: bump V whenever you change a precached SHELL file. A new V is what refreshes the
// shell — forget the bump and your fix ships to the repo but never to anyone's installed
// home-screen copy (iOS caches the SW aggressively). ../src/sw_lint.py guards this, and app.js
// surfaces a "tap to update" pill so a stuck phone is fixable in one tap.
//
// Strategy, by what the file IS rather than where it lives:
//   HTML/JS + navigations → CACHE-FIRST once installed: paint from the precache with NO network on
//     the critical path, so a load is instant and identical on a fast link, a slow one, or none.
//     Freshness is handled OFF the critical path, because the shell is owned per-generation
//     (cachePut won't overwrite it) and a new deploy MUST bump V anyway (THE ONE RULE): a V bump
//     installs the new shell and lights app.js's update pill. A background revalidate here would
//     just be discarded, so there isn't one. Only an uncached or unbootable request falls through
//     to a bounded network-first fetch, which ALWAYS ends at a real Response. NB this rests on
//     every live url being a SHELL file (it is today): a future NON-shell .html/.js would be
//     served cache-first with no revalidation until a V bump collects the old generation — add
//     such a file to SHELL (and bump V), don't lean on opportunistic caching to refresh it.
//   JSON → paint from cache now. PRECACHED json (opera.json) is owned by the install, so a V bump
//     is what refreshes it; any other same-origin json is stale-while-revalidate
//   images and everything else → cache-first for speed; a V bump is what refreshes them
//   cross-origin (GoatCounter, Spotify links) → straight through, never cached here
//
// The precache is PER-FILE — deliberately never a bare cache.addAll(). That buys self-healing and
// costs a third cache state, PARTIAL, which this whole file then has to reason about. Three
// questions addAll answered implicitly become live, and every function below answers one of them:
//   1. is this version's cache COMPLETE?     → ensureShell() / topUpThenCollect()
//   2. which GENERATION answers a read?      → cacheLookup(), the directional collect
//   3. is a complete-looking cache BOOTABLE? → bootable() / offlineFallback()
// The seven review rounds behind this design: pwa-starter#7.

const V = "haydn-v15";   // <-- BUMP ON EVERY SHELL CHANGE (rename the stem freely; keep the digits)

// "haydn-v" — the stem shared by every cache generation. app.js's VER_PREFIX must match it, and
// the NUMERIC TAIL is load-bearing: it orders generations for the collect below and for
// checkVer()'s ranking in app.js. ../src/sw_lint.py rejects a V without digits at commit time.
const V_STEM = V.replace(/\d+$/, "");

// Numeric generation of a cache name, or null if it isn't one of ours. Used to make the collect
// directional: a worker may only delete caches OLDER than its own.
function verNum(name) {
  const tail = name.startsWith(V_STEM) ? name.slice(V_STEM.length) : "";
  return /^\d+$/.test(tail) ? parseInt(tail, 10) : null;
}

const SHELL = [
  "./", "./index.html", "./scatter.html",
  "./opera.json", "./d3.v7.min.js", "./app.js", "./manifest.json",
  "./favicon.svg", "./favicon-32.png", "./favicon-16.png",
  "./apple-touch-icon.png", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png",
  // NB: the *-preview.png share cards are intentionally NOT precached — they're only for
  // link-scrapers, never rendered in-app, so caching them would just bloat the offline store.
];

// Absolute hrefs of the SHELL, resolved once so cachePut()'s ownership check is a Set lookup and
// not a URL parse per request. self.location is the sw.js URL, so "./" resolves to the scope root.
// MUST stay below the SHELL declaration — a const read from its own TDZ throws at script
// evaluation, which kills the whole worker: no install, no precache, blank screen offline.
const SHELL_HREFS = new Set(SHELL.map(u => new URL(u, self.location).href));

// Which SHELL entries this version's cache is missing. No network — pure cache reads.
//
// One parallel batch rather than an await per entry: app.js pings "ensure-shell" on every load,
// every controllerchange, and every foreground, and each ping runs this TWICE (the top-up, then
// the re-check in topUpThenCollect). Serialized, that's dozens of sequential Cache API round
// trips every time an iOS home-screen app foregrounds with a complete shell and nothing to do.
async function missingFromShell(cache) {
  const c = cache || await caches.open(V);
  const found = await Promise.all(SHELL.map(url => c.match(url)));
  return SHELL.filter((_, i) => !found[i]);
}

// Precache top-up. Deliberately NOT cache.addAll(): addAll is atomic, so a single 404 (a shell
// file renamed and the list not updated, or a mid-deploy blip) rejects the whole install and the
// device ends up with NO cache at all — offline then shows a blank screen. Per-file puts degrade
// instead: whatever fetched is cached, the rest retries.
//
// It also only fetches what's MISSING, which makes it safe to call repeatedly — that's how an
// evicted cache repairs itself. iOS reclaims script-writable storage (Cache API included) under
// pressure and after ~7 idle days, and can leave the cache NAME behind while dropping the
// contents. install only runs on a V bump, so without this top-up a once-evicted cache stays
// empty forever and the app is permanently blank offline.
//
// Returns { transient, permanent }: HOW MANY entries failed in a way a retry could fix, and WHICH
// entries failed in a way no retry ever will. topUpThenCollect() keys the old-cache collect off
// that split, so both have to mean "not cached", not "attempted".
//
// Why the split: the collect waits for a complete precache, so a SHELL entry that can never be
// fetched — a renamed file, a typo'd path — would otherwise keep it waiting FOREVER. Both cache
// generations then live on the device permanently, with the old one still answering (via
// cacheLookup's whole-store fallback) for anything absent from the new one. A 404 is a bug in the
// SHELL list that no amount of retrying repairs, so it must not hold the collect hostage;
// everything genuinely retryable still does. ../src/sw_lint.py catches the repo-side version of
// this at commit time, before it can ship — this path is damage control, not the guard.
//
// Deliberately CONSERVATIVE about what counts as permanent, because guessing wrong trades a
// working offline copy for an empty one. A REDIRECT is transient — a captive portal redirects
// everything, and that is a mobile-normal state, not a broken shell list. 5xx is transient (a
// mid-deploy blip). 408/429 are transient by definition. A 206 is transient — a partial means the
// file IS on the server and some hop answered a plain GET with a range. Only a definite "this URL
// is not on the server" — 4xx other than those — is permanent.
//
// KNOWN LIMITATION: a put() that fails for QUOTA is counted transient, which keeps the old cache
// and so keeps consuming the quota that just ran out. Harmless at this shell's size; a larger
// shell (precached PDFs/media) should evict the old version to make room instead of holding both.
async function ensureShellOnce() {
  try {
    const c = await caches.open(V);
    const missing = await missingFromShell(c);
    const outcome = await Promise.all(missing.map(url =>
      fetch(url, { cache: "reload" })
        .then(resp => {
          // A redirected response can't satisfy a navigation (the SW spec rejects it), and
          // resp.ok is TRUE for a 206 but put() then throws. Skip both rather than poison the
          // entry. Every SHELL entry is same-origin, so there's no opaque case to exempt here.
          if (resp.redirected || resp.status === 206) return "transient";
          if (!resp.ok) {
            return resp.status >= 500 || resp.status === 408 || resp.status === 429
              ? "transient" : "permanent";
          }
          return c.put(url, resp).then(() => "ok", () => "transient");
        })
        .catch(() => "transient")   // offline: leave it for the next attempt
    ));
    return {
      transient: outcome.filter(r => r === "transient").length,
      permanent: missing.filter((_, i) => outcome[i] === "permanent"),
    };
  } catch {
    // CacheStorage itself is unavailable — site data blocked, storage corrupt. Transient by
    // definition, and reporting the whole shell as retryable keeps the old cache as the net.
    return { transient: SHELL.length, permanent: [] };
  }
}

// install, activate, and the "ensure-shell" message can all fire close together; without this a
// V bump would fetch the whole shell 2-3x on a cellular connection. Callers that arrive mid-run
// join it instead of starting their own.
let shellRun = null;
function ensureShell() {
  return shellRun ??= ensureShellOnce().finally(() => { shellRun = null; });
}

self.addEventListener("install", e => {
  e.waitUntil(ensureShell().then(() => self.skipWaiting()));
});

// REPAIR BEFORE COLLECT, and only collect once THIS version's cache is complete.
//
// addAll's atomicity was a liability (one 404 lost the whole precache) but it was also a guard:
// a failed install meant the new SW never activated, so the previous cache kept serving. Per-file
// puts removed that guard — install now always resolves — so collecting first would let a V bump
// on a dead connection trade a working stale offline copy for an empty new one.
//
// "Complete" here means EVERY FETCHABLE SHELL URL IS PRESENT. It also means they came from the
// SAME deploy, because cachePut() refuses to write SHELL urls (see the note there): each
// generation's shell is fetched once, by the install that created it, so the net this keeps is
// coherent rather than merely complete by entry count.
//
// Keeping the old cache is NOT free, which is why this has to be re-runnable rather than a
// one-shot in activate: CacheStorage.match() iterates caches in CREATION order, so while an old
// version lingers it ANSWERS FIRST and shadows the current shell (caches ['haydn-v8','haydn-v10']
// both holding a URL resolve to the v8 copy). A lingering old cache means the device serves the
// previous release offline, and checkVer() reads the wrong installed version. cacheLookup()
// closes the read-path shadowing by construction, but the storage cost and the checkVer()
// confusion persist until something collects — and activate fires once per SW version, hence the
// retry from the message handler below, the only hook that runs after activation.
async function topUpThenCollect() {
  const { transient, permanent } = await ensureShell();
  if (transient > 0) return transient;              // keep the old cache as a net, try again later

  try {
    // Re-verify rather than trusting that count. ensureShell() dedupes concurrent callers, so a
    // joiner receives a completeness reading taken BEFORE it joined — if eviction landed mid-run,
    // "complete" is already false and we'd collect the net out from under a broken shell. Cheap
    // (cache reads only) and it makes the collect depend on current state, not a stale promise.
    //
    // Entries this run proved PERMANENTLY unfetchable are excluded: they are missing by definition
    // and always will be, so counting them here would re-wedge the collect that the transient/
    // permanent split exists to unwedge.
    const recheck = (await missingFromShell()).filter(u => !permanent.includes(u)).length;
    if (recheck > 0) return recheck;

    // Don't collect while another version is mid-install. From this worker's perspective the
    // incoming release's cache is merely "not V", so deleting it would throw away a precache that
    // is being built right now — and app.js pings us on load, which is exactly when an update
    // installs. Whichever worker activates next runs this same step and collects then.
    const reg = self.registration;
    if (reg && (reg.installing || reg.waiting)) return 0;

    // ...but that guard alone is NOT enough, so the collect is also DIRECTIONAL: only strictly
    // OLDER generations, never "everything that isn't me". An incoming worker calls skipWaiting()
    // as soon as its install resolves, at which point it is `active` with installing and waiting
    // both null — so an outgoing worker still finishing a slow top-up sails past the guard above
    // and deletes the new version's freshly built precache. Comparing generations makes that
    // impossible from either side regardless of who runs when.
    //
    // Caches that aren't ours (verNum → null) are left alone rather than swept: this worker has
    // no claim on them, and "delete everything unfamiliar" is how a SW eats a sibling app's
    // storage on a shared origin. V MUST END IN DIGITS: without a numeric tail verNum(V) is null,
    // `n < null` is false for every cache, and collection silently stops — no error, no symptom,
    // until generations pile up. ../src/sw_lint.py rejects that shape at commit time; this is
    // the runtime half of the contract.
    const mine = verNum(V);
    if (mine === null) return 0;

    const ks = await caches.keys();
    await Promise.all(ks
      .filter(k => { const n = verNum(k); return n !== null && n < mine; })
      .map(k => caches.delete(k)));
  } catch {
    // Storage went away mid-collect. Keep the old cache and retry on the next ping rather than
    // rejecting: this runs inside install's and the message handler's waitUntil().
    return SHELL.length;
  }
  return 0;
}

self.addEventListener("activate", e => {
  e.waitUntil(topUpThenCollect().then(() => self.clients.claim()));
});

// app.js pings this on every online load, foreground, and controllerchange, so an evicted
// precache heals on the next launch with a connection instead of waiting for the next V bump —
// and a collect deferred at activate time (incomplete shell, or an install in flight) gets
// retried here.
//
// NB: the collect deliberately lives in topUpThenCollect() and not inside ensureShellOnce(),
// which also runs during install — deleting the old cache then would strand pages still
// controlled by the previous worker.
self.addEventListener("message", e => {
  if (e.data === "ensure-shell") e.waitUntil(topUpThenCollect());
});

// Cache-write gate (from pwa-starter, see its CLAUDE.md §Offline). A fetch() only REJECTS on a
// network failure — a 404 or a mid-deploy 502 arrives as a RESOLVED response, so an ungated
// put() overwrites a good cached copy with an error body that then survives as the offline
// fallback until the next V bump.
// A redirected response can't be used to satisfy a navigation, so caching one is another route
// to a blank screen. 206 needs its own clause because resp.ok is TRUE for a partial and
// cache.put() then throws. The opaque exemption is inert here (no cross-origin request reaches
// this function — the fetch handler passes other origins straight through) but kept so a future
// cross-origin handler doesn't silently stop caching.
function cachePut(req, resp) {
  // SHELL entries are owned by ensureShellOnce() and by nothing else. Letting opportunistic
  // request traffic write them too is what produced MIXED-GENERATION caches: V is whatever the
  // CURRENT worker declares, so a shell file whose bytes changed on the server got overwritten in
  // the current cache one file at a time while its neighbours kept their older entries — no V
  // bump needed, one redeployed file is enough. Each page here is a document plus d3 plus
  // opera.json plus app.js, a coupled set; a document from one deploy driving scripts from
  // another is exactly the confusing-bug class. Skipping SHELL makes "a V bump is what refreshes
  // them" literally true: each generation's shell is fetched once, by the install that created it.
  if (SHELL_HREFS.has(req.url)) return;
  if (resp.redirected || resp.status === 206) return;
  if (!resp.ok && resp.type !== "opaque") return;
  const copy = resp.clone();
  // The .catch() matters: non-GET requests, 206s, and quota exhaustion all surface at put(), and
  // an uncaught rejection in a SW is just noise in a log nobody reads — the caller's response has
  // already been returned either way.
  caches.open(V).then(c => c.put(req, copy)).catch(() => {});
}

// Read the CURRENT version first, then fall back to the whole store.
//
// CacheStorage.match() scans caches in CREATION order, so a lingering old version outranks the
// current one — collecting promptly only closes that shadowing by timing. Scoping the first
// lookup to V closes it by construction: the old cache can still fill a gap (it's the net that
// makes a failed V bump survivable) but it can no longer outrank a complete current shell.
//
// NEVER REJECTS. This is called from inside the offline catch handler, the last stop before
// offlineFallback() — a throw there escapes as a rejected respondWith(), and WebKit paints the
// same blank white screen this file exists to prevent. A bare caches.match() can't throw, but
// caches.open(V) can (site data blocked in Safari, corrupt or evicted storage). Resolve undefined
// instead and let the caller reach the fallback.
async function cacheLookup(req) {
  try {
    const c = await caches.open(V);
    const hit = await c.match(req);
    if (hit) return hit;
  } catch {}
  try {
    return await caches.match(req);
  } catch {
    return undefined;
  }
}

// Subresources a cached document cannot BOOT without, per document. Per-file precaching means the
// cache can legitimately hold a document while a script it needs is still missing (one 500 during
// install), and the shell fallback below is navigation-only by design — so offline, the document
// is served, its d3 request gets an empty 504, and the inline boot throws "d3 is not defined"
// before anything renders: a bare header, no content, no error, no hint. Serving the honest
// offline page instead is strictly better — it says what to do, and one online launch repairs
// the precache.
//
// Both pages die without d3 (their inline boot uses it immediately). app.js is deliberately NOT
// listed — it only adds the update pill, so a page without it still renders fully. opera.json is
// deliberately NOT listed either: both pages .catch() the data fetch and show their own error,
// which beats the generic fallback.
const BOOT_DEPS = {
  "": ["./d3.v7.min.js"], "index.html": ["./d3.v7.min.js"],
  "scatter.html": ["./d3.v7.min.js"],
};

// Request pathname → BOOT_DEPS key, relative to the SW scope (works under a subpath too).
const SCOPE_PATH = new URL("./", self.location).pathname;
function docKey(pathname) {
  return pathname.startsWith(SCOPE_PATH) ? pathname.slice(SCOPE_PATH.length) : pathname;
}

// Uses cacheLookup(), not a V-scoped read: a dep that only survives in the previous generation's
// cache will still be SERVED from there, so it counts as present. The gate has to model what the
// subresource request will actually get, or it fires on pages that would have booted fine.
async function bootable(pathname) {
  const deps = BOOT_DEPS[docKey(pathname)] || [];
  return (await Promise.all(deps.map(u => cacheLookup(u)))).every(Boolean);
}

// The FALLBACK network fetch is BOUNDED by these timers. Cache-first (the live branch) means the
// common, fully-cached load never reaches them; they run only when the cache can't answer — a
// first run, or an evicted/partial shell — where a slow-but-alive link ("lie-fi": a weak cell
// signal, a captive portal that half-answers) would otherwise hang respondWith() on a fetch that
// never settles: the very blank screen this file fights, now with no end. Bounding turns that into
// an eventual real Response.
//
// TWO bounds, because a timeout costs differently in the two states:
//   WARM (a cached copy in hand — even a non-bootable one to fall back to): short. There's a real
//     page one lookup away, so a stale-but-instant paint beats waiting on a dead-slow link.
//   COLD (NOTHING cached — a first run, or a shell iOS evicted under storage pressure / after ~7
//     idle days, the routine case ensureShellOnce() documents): longer, because the only fallback
//     is offlineFallback()'s "try again" page and a working-but-slow link that would have delivered
//     the real app at 8s shouldn't be cut off at 3s. But NOT unbounded: an evicted shell on a weak
//     signal is exactly the reported failure, and an eventual honest page beats a permanent blank.
const NET_TIMEOUT_MS = 3000;
const NET_TIMEOUT_COLD_MS = 15000;

// Reject `promise` if it hasn't settled within `ms`, so a timeout routes into the offline catch
// rather than stranding respondWith() on a fetch that never settles. The underlying fetch is
// untouched — racing a timer against it doesn't abort it — so the caller keeps it alive under
// waitUntil. clearTimeout on settle so a resolved fetch doesn't hold a pending timer (and the SW)
// awake for the remainder of the window.
function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("network timeout")), ms);
    promise.then(
      v => { clearTimeout(timer); resolve(v); },
      err => { clearTimeout(timer); reject(err); }
    );
  });
}

self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);

  // cache.put() rejects for anything but GET ("Request method is not GET"), and a form POST is
  // mode === "navigate" — so without this it walks straight into the live branch and cachePut().
  if (e.request.method !== "GET") return;

  // Cross-origin (GoatCounter, Spotify, d3 CDN if ever used): straight to network, skip the cache.
  if (u.origin !== location.origin) return;

  // The SW must never intercept or cache its own script: app.js probes ./sw.js?_=<ts> to read the
  // live version; caching those probes bloats the cache (a dead entry per resume) and can wedge the
  // "tap to update" pill.
  if (u.pathname.endsWith("/sw.js")) return;

  // Navigations are decided FIRST, ahead of the .json test below: a document request must always
  // end at a real page — including a direct navigation to a .json URL, which the SWR branch would
  // otherwise answer offline with a rejected respondWith (a bare network error), not the fallback.
  const live = e.request.mode === "navigate" || u.pathname.endsWith("/") || /\.(html|js)$/.test(u.pathname);

  // Same-origin JSON → serve the cached copy IMMEDIATELY instead of blocking first paint on a
  // round trip. opera.json (107 KB) is this app's only data source and both pages fetch it at
  // boot; network-first made every cold start block on it even with a good cached copy.
  if (!live && /\.json$/.test(u.pathname)) {
    e.respondWith(cacheLookup(e.request).then(cached => {
      // PRECACHED json is NOT revalidated: cachePut() refuses to write SHELL urls (they're
      // ensureShellOnce()'s to own), so revalidating opera.json would fetch 107 KB and discard
      // it — cellular spent for nothing on every launch of both pages. A V bump is what
      // refreshes it, which THE ONE RULE already requires. Conditional on a cached copy
      // EXISTING, so a first run or an evicted entry still falls through to the network.
      if (cached && SHELL_HREFS.has(e.request.url)) return cached;
      const net = fetch(e.request).then(resp => { cachePut(e.request, resp); return resp; });
      e.waitUntil(net.catch(() => {}));   // keep the SW alive for the refresh; offline is fine
      // No cached copy (first run) → wait for the network, but END AT A RESPONSE: a first run
      // offline was the one branch left that could settle respondWith() with a rejection.
      return cached || net.catch(() => offlineFallback(e.request));
    }));
    return;
  }

  // Same-origin: HTML/JS + navigations → CACHE-FIRST; other assets (images) → cache-first too.
  //
  // The old strategy here was network-first, and it hid a mobile-common failure: fetch() only
  // rejects on a real failure, so a connection that is UP but crawling ("lie-fi" — a weak cell
  // signal, a captive portal that half-answers) makes the fetch hang rather than reject. The
  // offline catch never fired, respondWith() stayed pending, and WebKit painted a blank screen —
  // "internet, but too slow to answer," the reported bug. Network-first also fetched the shell on
  // every load only to DISCARD it: cachePut refuses to overwrite SHELL urls, and the shell is
  // every live url this app serves. So the latency bought no freshness the update pill doesn't
  // already deliver.
  //
  // Cache-first fixes both: paint straight from the precache, no network on the critical path,
  // instant whether the link is fast, slow, or gone. Freshness is off this path (a V bump installs
  // the new shell and lights the pill; see the strategy note up top). The network is touched only
  // when the cache CAN'T answer — a first run, or an evicted/partial shell — and that fetch is
  // bounded so even it can't hang on lie-fi.
  //
  // One accepted consequence of serving the shell from cache rather than the network: during a
  // partial install (V bumped, top-up not yet complete), cacheLookup()'s whole-store fallback can
  // pair a new-generation document with an old-generation subresource — index.html@vN with
  // app.js@vN-1 — until the collect completes. bootable() guards d3 (a page dies without it) but
  // not app.js, which only adds the update pill, so the window is cosmetic and self-heals.
  if (live) {
    e.respondWith((async () => {
      const cached = await cacheLookup(e.request);

      // Serve the cached copy immediately. A navigation must also be BOOTABLE — a cached document
      // whose d3 is missing renders a bare header, worse than the honest fallback — so a
      // non-bootable navigation drops through to the network path instead.
      if (cached && (e.request.mode !== "navigate" || await bootable(u.pathname))) {
        return cached;
      }

      // No usable cached copy: first run, or an evicted/partial shell. Go to the network, bounded
      // EITHER WAY (see the try below): short when a fallback page is in hand, longer
      // (NET_TIMEOUT_COLD_MS) on a true first run where offlineFallback() is the only floor — but
      // never unbounded, so it always ends at a real Response.
      const net = fetch(e.request).then(resp => {
        cachePut(e.request, resp);   // a no-op for SHELL urls; repair is ensureShell()'s job
        if (!resp.ok) {
          // A 4xx/5xx is a RESOLVED fetch, not a rejection. For a subresource, a good cached copy
          // beats handing the app an error body. For a NAVIGATION, though, the only cached copy
          // reachable here already FAILED bootable() (cache-first would have served it otherwise),
          // so returning it is the bare-header render the file rejects as worse than the honest
          // fallback — throw so the catch decides (→ offlineFallback), don't serve the broken doc.
          if (e.request.mode === "navigate") throw new Error("http " + resp.status);
          return cacheLookup(e.request).then(r => r || resp);
        }
        return resp;
      });
      try {
        // Bounded either way (see NET_TIMEOUT_*): WARM has a page to fall back to, COLD has only
        // offlineFallback — but NEITHER may hang. A timeout, an offline rejection, or a navigation
        // 5xx (thrown above) all land in the catch.
        return await withTimeout(net, cached ? NET_TIMEOUT_MS : NET_TIMEOUT_COLD_MS);
      } catch {
        // Keep the fetch alive so its eventual result is available to the next request (a no-op
        // when it already rejected). Resolving respondWith() to undefined is the original
        // blank-screen bug — WebKit fails the navigation with "Returned response is null" and iOS
        // paints a blank white page — so every branch below ends at a real Response.
        e.waitUntil(net.catch(() => {}));

        // For a navigation, a document that can't load its d3 renders a bare header — worse than
        // the honest fallback. Re-checked LIVE (not from the pre-network snapshot): an
        // "ensure-shell" repair can land inside the timeout window and flip this true.
        if (e.request.mode === "navigate" && !(await bootable(u.pathname))) {
          return offlineFallback(e.request);
        }
        // The ./index.html fallback is doubly gated:
        //   - NAVIGATIONS only: `live` also matches .js, and handing HTML to an uncached
        //     d3.v7.min.js request makes the script fail to PARSE instead of failing cleanly.
        //   - the ROOT document only: this app has two pages, and answering an uncached
        //     scatter.html navigation with the card page hands the user the wrong document —
        //     the honest offline page beats a page they didn't ask for. What the root fallback
        //     still catches: query-variant navigations like "./?x=…", which miss the exact-match
        //     lookup above.
        const key = docKey(u.pathname);
        const shell = e.request.mode === "navigate" && (key === "" || key === "index.html")
          ? await cacheLookup("./index.html") : null;
        // Re-read the cache rather than trusting the pre-network snapshot: an "ensure-shell" repair
        // (app.js pings it on every load) can land during the timeout window, and the fresh copy
        // should win over the snapshot when it does.
        return (await cacheLookup(e.request)) || cached || shell || offlineFallback(e.request);
      }
    })());
  } else {
    e.respondWith(
      cacheLookup(e.request).then(r => r || fetch(e.request).then(resp => {
        cachePut(e.request, resp);
        return resp;
      }).catch(() => offlineFallback(e.request)))
    );
  }
});

// Terminal fallback: always a real Response, never undefined. Navigations get a readable page
// (the precache is empty or unbootable — the one thing that fixes it is one online launch, which
// ensureShell() then uses to repair itself); subresources get a plain 504.
//
// Inline CSS by necessity: this page renders precisely when the precache is empty, so no
// stylesheet or webfont can be assumed. Palette matches the app (#f5f5f5/#1a1a1a bodies, the
// update pill's #42d4f4 accent).
function offlineFallback(req) {
  if (req.mode !== "navigate") {
    return new Response("", { status: 504, statusText: "Offline" });
  }
  return new Response(
    `<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Offline — Haydn Quartets</title>
<style>
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:#f5f5f5;color:#222;font:16px/1.5 system-ui,-apple-system,sans-serif}
  main{max-width:22em;padding:2em;text-align:center}
  h1{font-size:1.15em;margin:0 0 .6em}
  p{margin:.6em 0;color:#555}
  button{margin-top:1.2em;border:0;border-radius:999px;padding:.7em 1.3em;
         background:#42d4f4;color:#10262b;font-size:1em;cursor:pointer}
  @media (prefers-color-scheme:dark){ body{background:#1a1a1a;color:#eee} p{color:#aaa} }
</style>
<main>
  <h1>Offline, and nothing cached yet</h1>
  <p>The offline copy of this app hasn't been stored on this device — or the system reclaimed it
     to free up space.</p>
  <p>Open it once with a connection and it will rebuild itself for offline use.</p>
  <button onclick="location.reload()">Try again</button>
</main>`,
    { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
  );
}
