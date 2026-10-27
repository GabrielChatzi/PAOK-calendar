// Service worker του PAOKalendar: κάνει τη σελίδα να ανοίγει και χωρίς σύνδεση.
//
// - Η σελίδα και τα εικονίδια αποθηκεύονται κατά την εγκατάσταση.
// - Τα δεδομένα (matches.json, standings.json) έρχονται πρώτα από το δίκτυο, ώστε να είναι
//   πάντα φρέσκα· χωρίς σύνδεση χρησιμοποιείται η τελευταία αποθηκευμένη έκδοση.
// - Σήματα ομάδων και γραμματοσειρές κρατιούνται στη συσκευή μετά την πρώτη φορά.
// - Τα .ics δεν περνούν από εδώ, ώστε οι συνδρομές ημερολογίου να βλέπουν πάντα την τρέχουσα έκδοση.
//
// Αλλάζοντας το VERSION, οι συσκευές κατεβάζουν ξανά τη σελίδα.
const VERSION = "v1";
const SHELL = `paokalendar-shell-${VERSION}`;
const DATA = "paokalendar-data";
const ASSETS = "paokalendar-assets";
const MAX_ASSETS = 300;

const SHELL_FILES = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/apple-touch-icon.png",
  "icons/favicon-32.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys
        .filter((k) => k.startsWith("paokalendar-shell-") && k !== SHELL)
        .map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request, { cache: "no-cache" });
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(request, { ignoreSearch: true });
    if (cached) return cached;
    throw err;
  }
}

async function trim(cache) {
  const keys = await cache.keys();
  for (let i = 0; i < keys.length - MAX_ASSETS; i++) await cache.delete(keys[i]);
}

async function cacheFirst(request) {
  const cache = await caches.open(ASSETS);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  // Και οι «αδιαφανείς» απαντήσεις άλλων site (σήματα) αποθηκεύονται· εμφανίζονται κανονικά σε <img>.
  if (response.ok || response.type === "opaque") {
    cache.put(request, response.clone()).then(() => trim(cache));
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  if (url.origin === self.location.origin) {
    if (url.pathname.endsWith(".ics")) return;
    if (url.pathname.endsWith(".json")) {
      event.respondWith(networkFirst(request, DATA));
      return;
    }
    if (request.mode === "navigate") {
      event.respondWith(networkFirst(new Request("index.html"), SHELL).catch(() => caches.match("./")));
      return;
    }
    event.respondWith(caches.match(request).then((hit) => hit || networkFirst(request, SHELL)));
    return;
  }

  if (request.destination === "image" || request.destination === "font" ||
      url.hostname === "fonts.googleapis.com") {
    event.respondWith(cacheFirst(request));
  }
});
