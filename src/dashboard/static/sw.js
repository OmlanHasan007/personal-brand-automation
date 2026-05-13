// Career OS Service Worker
// Caches the shell so the app loads instantly even offline
// API calls always go to network (can't cache dynamic data)

const CACHE_NAME = 'career-os-v1';
const SHELL_URLS = [
  '/',
  '/static/manifest.json',
];

// Install — cache the shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(SHELL_URLS).catch(err => {
        console.log('[SW] Shell cache partial failure:', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate — remove old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch strategy:
// - API calls (/api/*): network only — always fresh data
// - Everything else: cache first, network fallback
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls — always network
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ error: 'Offline — connect to your local server' }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    return;
  }

  // Shell — cache first
  event.respondWith(
    caches.match(event.request).then(cached => {
      return cached || fetch(event.request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});
