/**
 * sw.js - Service Worker do VioWeb para operação 100% offline (PWA).
 *
 * Estratégia de Cache:
 * - Cache-first para ativos estáticos, WebAssembly, wheels e modelos.
 * - Network-first com fallback para cache em navegações HTML.
 * - Limpeza automática de caches antigos no evento 'activate'.
 */

const CACHE_NAME = 'vioweb-cache-v0.2.0';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/documentos',
  '/privacidade',
  '/apoiar',
  '/favicon.ico',
  '/manifest.json',
  '/static/favicon.ico',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/pix-qrcode.png',
  '/static/style.css',
  '/static/app.js',
  '/static/bpgdec8.js',
  '/static/scanner.worker.js',
  '/static/templates-data.json',
  '/static/wheels/vioweb-0.2.0-py3-none-any.whl',
  '/static/vendor/pdfjs/pdf.min.js',
  '/static/vendor/pdfjs/pdf.worker.min.js',
  '/static/vendor/zxing/zxing_reader.js',
  '/static/vendor/zxing/zxing_reader.wasm',
  '/static/vendor/pyodide/pyodide.js',
  '/static/vendor/pyodide/pyodide.asm.js',
  '/static/vendor/pyodide/pyodide.asm.wasm',
  '/static/vendor/pyodide/python_stdlib.zip',
  '/static/vendor/pyodide/pyodide-lock.json',
  '/static/vendor/pyodide/cryptography-42.0.5-cp312-cp312-pyodide_2024_0_wasm32.whl',
  '/static/vendor/pyodide/cffi-1.16.0-cp312-cp312-pyodide_2024_0_wasm32.whl',
  '/static/vendor/pyodide/pycparser-2.22-py3-none-any.whl',
  '/static/vendor/pyodide/openssl-1.1.1n.zip',
  '/static/vendor/pyodide/six-1.16.0-py2.py3-none-any.whl',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // Tenta armazenar em cache cada ativo individualmente para tolerar ausências em dev
      for (const asset of PRECACHE_ASSETS) {
        try {
          await cache.add(asset);
        } catch (_) {
          // Ignora falhas em rotas opcionais durante o precache
        }
      }
    }).then(() => self.skipWaiting())
  );
});

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

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Somente intercepta requisições same-origin
  if (url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      if (cachedResponse) {
        // Cache hit: retorna imediatamente
        return cachedResponse;
      }

      // Se não está no cache, tenta buscar na rede e guarda no cache
      return fetch(req)
        .then((networkResponse) => {
          if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
            return networkResponse;
          }
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(req, responseToCache);
          });
          return networkResponse;
        })
        .catch(() => {
          // Se falhar e for navegação HTML, entrega /index.html em cache
          if (req.mode === 'navigate' || req.headers.get('accept')?.includes('text/html')) {
            return caches.match('/index.html') || caches.match('/');
          }
          return new Response('Offline: Recurso indisponível sem conexão.', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain; charset=utf-8' },
          });
        });
    })
  );
});
