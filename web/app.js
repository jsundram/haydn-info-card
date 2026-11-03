// pwa-starter: app.js @ dd763ca
// App boot: service-worker registration + a one-tap "update available" pill.
// (Pattern from pwa-starter, trimmed — this app has no cross-origin data to poll
// and its dark mode is media-query-only, so the theme/data/PTR plumbing is omitted.)
//
// Loaded by both index.html and scatter.html. Self-contained: it injects its own
// pill element + styles, so the HTML/CSS files don't need to know about it.

const VER_PREFIX = "haydn-v";   // must match sw.js's V stem — and V's numeric tail is load-bearing
const APP_V = "haydn-v17";      // THIS bundle's version — the code the page is actually executing.
                                // Must EQUAL sw.js's V; ../src/sw-lint.py check 6 fails the commit
                                // on drift. checkVer() compares against this rather than a cache
                                // key: a key says what is STORED, not what is RUNNING.

// Build the little pill, hidden until we know the server is ahead of this device.
function ensurePill() {
  let pill = document.getElementById("sw-update");
  if (pill) return pill;
  pill = document.createElement("button");
  pill.id = "sw-update";
  pill.hidden = true;
  pill.textContent = "Update available — tap to refresh";
  Object.assign(pill.style, {
    position: "fixed", left: "12px", bottom: "12px", zIndex: "9999",
    font: "13px/1 'Helvetica Neue', Arial, sans-serif", padding: "9px 13px",
    border: "0", borderRadius: "999px", cursor: "pointer",
    background: "#42d4f4", color: "#10262b", boxShadow: "0 2px 8px rgba(0,0,0,.25)",
  });
  document.body.appendChild(pill);
  return pill;
}

// Compare the version THIS BUNDLE was built as against the live sw.js on the server.
// Show the pill only when the server is ahead (so a fix that shipped but got stuck
// behind iOS's aggressive SW cache is fixable in one tap).
async function checkVer() {
  // The only question cache keys can answer honestly is "is a worker installed AT ALL", and it is
  // asked purely to keep the pill out of a plain browser tab that has never registered one.
  //
  // This used to rank the keys — highest generation, non-empty only — and treat the winner as the
  // version the device was running. A key cannot report that: it describes what is STORED. sw.js
  // calls skipWaiting() + clients.claim() and topUpThenCollect() drops older generations, so the
  // key set flips to the new version the moment a worker activates, while this page goes on
  // executing the app.js it parsed at launch — clients.claim() reloads nothing. The comparison
  // then read installed === latest on precisely the device that was a release behind, hid the
  // pill, and left nothing to tap; a home-screen copy that is never force-quit holds that state
  // indefinitely. APP_V settles it at the source, so the ranking and the non-empty filter are
  // both gone. Keeping the filter would now do active harm: it hides the pill on a device whose
  // new cache is still the empty placeholder ensureShellOnce() opens before it fetches anything —
  // exactly the stranded device it was written to protect. (pwa-starter#17)
  let installed = false;
  try {
    installed = (await caches.keys()).some(k => k.startsWith(VER_PREFIX));
  } catch {}
  if (!installed) return;                     // nothing installed yet — first visit

  let latest = "";
  try {   // ?_= + no-store dodges both the SW cache and the HTTP cache → the live sw.js
    const src = await (await fetch("./sw.js?_=" + Date.now(), { cache: "no-store" })).text();
    // Read the DECLARATION, not the first prefix-shaped string anywhere in the file: sw.js's
    // comments now cite version names as examples, so an unanchored /haydn-v\d+/ scan would
    // match a comment and pin a permanent "Update available" pill that does nothing when tapped
    // (forceUpdate() clears caches, reloads, and re-reads the same comment). Same expression as
    // ../src/sw-lint.py's ver(); keep the two in agreement.
    latest = (src.match(/const V\s*=\s*"([^"]*)"/) || ["", ""])[1];
  } catch {}                                  // offline: leave latest empty → no false "behind"

  const pill = ensurePill();
  const behind = latest && latest !== APP_V;   // RUNNING bundle vs server, not cache key vs server
  pill.hidden = !behind;
  if (behind) pill.onclick = forceUpdate;
}

async function forceUpdate() {   // drop every cache, reload → SW reinstalls the latest shell
  try { await Promise.all((await caches.keys()).map(k => caches.delete(k))); } catch {}
  location.reload();
}

// Ask the active SW to top up any missing precache entries. iOS can reclaim Cache API contents
// (storage pressure, ~7 idle days) while leaving the registration in place, and sw.js only
// precaches on install — i.e. on a V bump. Without this nudge a device whose cache got evicted
// stays broken offline indefinitely; with it, one online launch repairs it.
function requestShellTopUp() {
  if (!navigator.onLine) return;
  // getRegistration() resolves undefined when there's nothing registered; .ready would just
  // never settle, leaving a pending promise behind on every foreground.
  navigator.serviceWorker.getRegistration()
    .then(reg => { if (reg && reg.active) reg.active.postMessage("ensure-shell"); })
    .catch(() => {});
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("./sw.js").catch(() => {});
  checkVer();
  requestShellTopUp();
  // A registration can exist with no ACTIVE worker for a moment — first install, or the swap
  // during an update — and the ping above is fire-and-forget, so it would simply be dropped and
  // nothing would retry until the next launch. That undercuts the whole "open it once with a
  // connection and it repairs itself" promise, so retry when a worker actually takes control.
  navigator.serviceWorker.addEventListener("controllerchange", requestShellTopUp);
  // iOS home-screen apps RESUME rather than reload — re-check on foreground.
  addEventListener("visibilitychange", () => {
    if (!document.hidden) { checkVer(); requestShellTopUp(); }
  });
}
