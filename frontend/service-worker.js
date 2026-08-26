/* ALICE service worker — makes the shell installable and offline-tolerant.

Strategy:
- Static assets (css, js, icons, manifest): cache-first with background
  refresh (stale-while-revalidate) so the app shell loads instantly.
- Navigations (HTML): network-first, falling back to the cached shell, so a
  user who has opened ALICE before can still launch it offline.
- Anything under /api, /ws or /web/proxy is NEVER cached — live data and
  security-sensitive pages must always come from the server.

Bump VERSION to invalidate old caches after a deploy.
*/

const VERSION = "alice-shell-v2.1";
const CACHE_NAME = `${VERSION}-assets`;
const STATIC_ASSETS = [
  "/",
  "/manifest.webmanifest",
  "/css/alice.css",
  "/js/main.js",
  "/js/state.js",
  "/js/bus.js",
  "/js/core.js",
  "/js/audio.js",
  "/js/chat.js",
  "/js/mission.js",
  "/js/panels.js",
  "/js/voice.js",
  "/js/sound.js",
  "/js/md.js",
  "/js/startup.js",
  "/js/webdock.js",
  "/js/notify.js",
  "/js/level.js",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/maskable-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function isStatic(url) {
  return /^\/(css|js|icons|manifest\.webmanifest)(\/|\.|$)/.test(url.pathname) || url.pathname === "/";
}

function isDynamic(url) {
  return /^\/(api|ws|web)/.test(url.pathname);
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== "GET") return;
  if (isDynamic(url)) return; // live data / proxy: always network
  if (url.origin !== self.location.origin) return;

  // Navigations: network first, then cached shell.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put("/", copy));
          return response;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }

  // Static: stale-while-revalidate.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
