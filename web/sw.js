// pwa-starter: sw.js @ 8d54c48
// Service worker: offline shell + cache-busting.  (Pattern from pwa-starter.)
//
// THE ONE RULE: bump V whenever you change a precached SHELL file. A new V is what evicts the
// stale cache on activate — forget the bump and your fix ships to the repo but never to anyone's
// installed home-screen copy (iOS caches the SW aggressively). ../src/sw_lint.py guards this,
// and app.js surfaces a "tap to update" tag so a stuck phone is fixable in one tap.
//
// Strategy, by what the file IS rather than where it lives:
//   HTML/JS + navigations → network-first (a push is visible on the next reload without waiting
//     for a SW swap; falls back to cache offline)
//   JSON → stale-while-revalidate (it's data: paint from cache now, refresh behind it)
//   images and everything else → cache-first for speed; a V bump is what refreshes them
//   cross-origin (GoatCounter, Spotify links) → straight through, never cached here

const V = "haydn-v8";   // <-- BUMP ON EVERY SHELL CHANGE
const SHELL = [
  "./", "./index.html", "./scatter.html",
  "./opera.json", "./d3.v7.min.js", "./app.js", "./manifest.json",
  "./favicon.svg", "./favicon-32.png", "./favicon-16.png",
  "./apple-touch-icon.png", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png",
  // NB: the *-preview.png share cards are intentionally NOT precached — they're only for
  // link-scrapers, never rendered in-app, so caching them would just bloat the offline store.
];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k))))   // evict old versions
    .then(() => self.clients.claim()));
});

// Cache-write gate (from pwa-starter, see its CLAUDE.md §Offline). A fetch() only
// REJECTS on a network failure — a 404 or a mid-deploy 502 arrives as a RESOLVED
// response, so an ungated put() overwrites a good cached copy with an error body
// that then survives as the offline fallback until the next V bump.
// Opaque responses (cross-origin no-cors: webfonts, CDN scripts) always report
// ok:false/status:0 no matter how they went, so they're exempt — gating them would
// silently disable font caching and break offline type.
function cachePut(req, resp) {
  if (!resp.ok && resp.type !== "opaque") return;
  const copy = resp.clone();
  caches.open(V).then(c => c.put(req, copy));
}

self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);

  // Cross-origin (GoatCounter, Spotify, d3 CDN if ever used): straight to network, skip the cache.
  if (u.origin !== location.origin) return;

  // The SW must never intercept or cache its own script: app.js probes ./sw.js?_=<ts> to read the
  // live version; caching those probes bloats the cache (a dead entry per resume) and can wedge the
  // "tap to update" tag.
  if (u.pathname.endsWith("/sw.js")) return;

  // Same-origin JSON → stale-while-revalidate: serve the cached copy IMMEDIATELY, refresh
  // behind it (pwa-starter e88a743). opera.json (107 KB) is this app's only data source and
  // both pages fetch it at boot; network-first made every cold start block first paint on a
  // round trip for a committed, precached file that almost never changes. The tradeoff is
  // real but small: an opera.json change lands one load later than an HTML/JS change.
  if (/\.json$/.test(u.pathname)) {
    e.respondWith(caches.match(e.request).then(cached => {
      const net = fetch(e.request).then(resp => { cachePut(e.request, resp); return resp; });
      e.waitUntil(net.catch(() => {}));   // keep the SW alive for the refresh; offline is fine
      return cached || net;               // no cached copy (first run) → wait for the network
    }));
    return;
  }

  // Same-origin: HTML/JS + navigations → network-first; other assets (images) → cache-first.
  const live = e.request.mode === "navigate" || u.pathname.endsWith("/") || /\.(html|js)$/.test(u.pathname);
  if (live) {
    e.respondWith(
      fetch(e.request).then(resp => {
        cachePut(e.request, resp);
        // A 4xx/5xx is a resolved fetch, so .catch() below never sees it — serve
        // the good cached copy instead of handing the app an error page.
        if (!resp.ok) return caches.match(e.request).then(r => r || resp);
        return resp;
      }).catch(() => caches.match(e.request).then(r => r || caches.match("./index.html")))
    );
  } else {
    e.respondWith(
      caches.match(e.request).then(r => r || fetch(e.request).then(resp => {
        cachePut(e.request, resp);
        return resp;
      }))
    );
  }
});
