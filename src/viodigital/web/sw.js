/**
 * sw.js - Service Worker do VioDigital para operação 100% offline (PWA) com auto-atualização.
 *
 * Estratégia de Cache Híbrida:
 * - Cache-First para runtimes imutáveis (/static/vendor/ Pyodide, ZXing, PDF.js e ícones).
 * - Network-First (com revalidação e fallback offline) para o motor Python (.whl),
 *   lógica JS/CSS e páginas HTML, garantindo que alterações locais entrem em vigor
 *   imediatamente sem perder a capacidade de operar 100% offline.
 * - Limpeza automática de caches antigos no evento 'activate'.
 */

const CACHE_NAME = 'viodigital-cache-v0.2.0-__BUILD_HASH__';

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
  '/static/wheels/viodigital-0.2.0-py3-none-any.whl',
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

function isImmutableVendorAsset(pathname) {
  return (
    pathname.startsWith('/static/vendor/') ||
    pathname.startsWith('/static/icon-') ||
    pathname === '/static/pix-qrcode.png' ||
    pathname === '/favicon.ico' ||
    pathname === '/static/favicon.ico'
  );
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then(async (cache) => {
        for (const asset of PRECACHE_ASSETS) {
          try {
            const req = new Request(asset, { cache: 'reload' });
            const resp = await fetch(req);
            if (resp && resp.ok) {
              await cache.put(asset, resp);
            }
          } catch (_) {
            // Ignora falhas em rotas opcionais durante o precache offline
          }
        }
      })
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) =>
        Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME)
            .map((name) => caches.delete(name))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;

  // 1. Ativos pesados e imutáveis (Pyodide, ZXing, PDF.js, ícones): Cache-First
  if (isImmutableVendorAsset(url.pathname)) {
    event.respondWith(
      caches.match(req).then((cachedResponse) => {
        if (cachedResponse) return cachedResponse;
        return fetch(req).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // 2. Motor Python (.whl), código da aplicação (JS/CSS) e HTML: Network-First com fallback offline
  event.respondWith(
    fetch(req, { cache: 'no-cache' })
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(req, responseToCache));
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(req).then((cachedResponse) => {
          if (cachedResponse) return cachedResponse;
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
