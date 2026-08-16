// Service Worker para Cancionero PWA
// Cachea los recursos y permite funcionamiento offline

const CACHE_NAME = 'cancionero-v1';
const urlsToCache = [
  '/JAVA-Cancionero/',
  '/JAVA-Cancionero/index.html',
  '/JAVA-Cancionero/manifest.json'
];

// Instalar el SW y cachear recursos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(urlsToCache).catch(() => {
        // Si falla, continuar igual (la app necesita red para Firestore)
      });
    })
  );
  self.skipWaiting();
});

// Activar el SW
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Servir desde caché, fallback a red
self.addEventListener('fetch', event => {
  // Solo cachear GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(response => {
      if (response) {
        return response;
      }
      return fetch(event.request).then(response => {
        // No cachear requests de Firestore ni URLs externas
        if (!response || response.status !== 200 || response.type === 'error') {
          return response;
        }
        // Cachear solo las URLs locales de Cancionero
        if (event.request.url.includes('github.io/JAVA-Cancionero')) {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
        }
        return response;
      });
    }).catch(() => {
      // Si falla la red y no está en caché, retornar la versión en caché si existe
      return caches.match('/JAVA-Cancionero/index.html');
    })
  );
});
