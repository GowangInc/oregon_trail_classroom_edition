/**
 * Oregon Trail Classroom — Service Worker
 * Simple cache-first for static assets, network-only for API/socket traffic.
 */

const CACHE_NAME = 'oregon-trail-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/host',
  '/host.html',
  '/map',
  '/map.html',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/js/host.js',
  '/static/js/network.js',
  '/static/js/ui.js',
  '/static/js/hunting.js',
  '/static/js/effects.js',
  '/static/js/pwa.js',
  '/static/manifest.json',
  '/static/assets/images/icon-192.svg',
  '/static/assets/images/icon-512.svg',
];

// ------------------------------------------------------------------
// Install — cache the app shell
// ------------------------------------------------------------------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).catch((err) => {
      console.warn('[SW] Failed to cache some assets:', err);
    })
  );
  self.skipWaiting();
});

// ------------------------------------------------------------------
// Activate — clean up old caches
// ------------------------------------------------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// ------------------------------------------------------------------
// Fetch — cache-first for static assets, network for everything else
// ------------------------------------------------------------------
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Never cache WebSocket upgrades or Socket.IO polling
  if (request.mode === 'navigate' && request.headers.get('upgrade') === 'websocket') {
    return;
  }

  // API/socket traffic — go straight to network
  if (url.pathname.startsWith('/socket.io/') || url.pathname.startsWith('/api/')) {
    return;
  }

  // External CDN assets — network only
  if (url.origin !== self.location.origin) {
    return;
  }

  // Static assets — cache first, fallback to network
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request).then((response) => {
        // Optionally cache new same-origin static assets on the fly
        if (response && response.status === 200 && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      });
    }).catch(() => {
      // If both cache and network fail for a navigation, show fallback
      if (request.mode === 'navigate') {
        return caches.match('/');
      }
    })
  );
});
