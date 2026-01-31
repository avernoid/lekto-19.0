const CACHE_NAME = 'partner-portal-v1';
const OFFLINE_URL = '/partner_offline/static/src/offline.html';

const ASSETS_TO_CACHE = [
    OFFLINE_URL,
    '/partner_offline/static/src/css/style.css',
    '/partner_offline/static/src/js/partner_portal.js',
    '/web/static/lib/bootstrap/css/bootstrap.css', // Basic styles
    '/web/static/lib/fontawesome/css/font-awesome.css', // Icons
];

self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Install');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[ServiceWorker] Caching offline page and assets');
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activate');
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    console.log('[ServiceWorker] Removing old cache', key);
                    return caches.delete(key);
                }
            }));
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    // 1. Navigation Requests (HTML pages) -> Network First, then Offline Fallback
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    return caches.open(CACHE_NAME)
                        .then((cache) => {
                            return cache.match(OFFLINE_URL);
                        });
                })
        );
        return;
    }

    // 2. Static Assets (JS, CSS, Images in static folder) -> Cache First, then Network
    if (event.request.url.includes('/static/') || event.request.url.includes('/web/image')) {
        event.respondWith(
            caches.match(event.request)
                .then((response) => {
                    return response || fetch(event.request);
                })
        );
        return;
    }

    // 3. Default -> Network Only
    event.respondWith(fetch(event.request));
});
