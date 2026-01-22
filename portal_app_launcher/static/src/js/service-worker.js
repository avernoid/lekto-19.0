const CACHE_NAME = 'portal-app-v5';
const urlsToCache = [
    '/',
    '/my/home',
    '/portal_app/manifest.webmanifest',
    '/portal_app_launcher/static/description/icon.png',
    '/portal_app_launcher/static/src/offline.html', // Pre-cache OFFLINE PAGE
];

self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching files');
                return cache.addAll(urlsToCache);
            })
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_NAME) {
                        console.log('Service Worker: Clearing Old Cache');
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached response if found (Static assets)
                if (response) {
                    return response;
                }
                // Otherwise network request (HTML Pages / LIVE DATA)
                return fetch(event.request)
                    .then(function (response) {
                        // Check if valid response
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Clone response for caching
                        var responseToCache = response.clone();

                        caches.open(CACHE_NAME)
                            .then(function (cache) {
                                // SMART CACHING STRATEGY
                                // 1. Cache static assets (CSS, JS, Images, Fonts) aggressively
                                if (event.request.url.match(/\.(js|css|png|jpg|jpeg|gif|ico|woff|woff2|ttf|svg)$/) ||
                                    event.request.url.includes('/web/content/') ||
                                    event.request.url.includes('/static/')) {
                                    cache.put(event.request, responseToCache);
                                }
                            });

                        return response;
                    })
                    .catch(function () {
                        // OFFLINE FALLBACK
                        // If network fails and it's a navigation request (page load), show offline.html
                        if (event.request.mode === 'navigate') {
                            return caches.match('/portal_app_launcher/static/src/offline.html');
                        }
                    });
            })
    );
});
