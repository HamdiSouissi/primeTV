/*
 * PrimeTV — service worker (PWA installable)
 * ---------------------------------------------------------------------------
 * Stratégies :
 *   • app shell (HTML, JS, CSS, images) : « stale-while-revalidate » → démarrage
 *     instantané, mise à jour en arrière-plan ;
 *   • navigation : réseau d'abord (contenu frais), repli sur le cache puis sur
 *     /offline.html ;
 *   • API (/api/**) : jamais mise en cache (données privées et temps réel) ;
 *   • flux vidéo (proxy, .m3u8, .ts, .mpd) : non interceptés (le lecteur gère
 *     ses propres requêtes Range).
 *
 * Aucune dépendance externe : ce fichier est servi tel quel par Nginx/Vite.
 */
const VERSION = 'v1.0.0';
const SHELL_CACHE = `primetv-shell-${VERSION}`;
const RUNTIME_CACHE = `primetv-runtime-${VERSION}`;

const SHELL_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/manifest.webmanifest',
  '/favicon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

/** Installe le service worker et précharge l'app shell. */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_ASSETS))
      .catch(() => undefined)
      .then(() => self.skipWaiting()),
  );
});

/** Supprime les caches des versions précédentes. */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith('primetv-') && key !== SHELL_CACHE && key !== RUNTIME_CACHE)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

/** Une requête ne doit jamais être mise en cache. */
function isBypassed(url) {
  if (url.pathname.startsWith('/api/')) return true;
  if (url.pathname.startsWith('/docs') || url.pathname.startsWith('/redoc')) return true;
  if (url.pathname.endsWith('.m3u8') || url.pathname.endsWith('.mpd')) return true;
  if (url.pathname.endsWith('.ts') || url.pathname.endsWith('.m4s')) return true;
  return false;
}

/** Navigation : réseau d'abord, repli cache puis page hors connexion. */
async function handleNavigation(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open(RUNTIME_CACHE);
    cache.put(request, response.clone()).catch(() => undefined);
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    const shell = await caches.match('/index.html');
    if (shell) return shell;
    return (await caches.match('/offline.html')) ?? Response.error();
  }
}

/** Assets statiques : stale-while-revalidate (ou cache-first si immuable). */
async function handleAsset(request) {
  const cached = await caches.match(request);
  const network = fetch(request)
    .then(async (response) => {
      if (response.ok && response.type !== 'opaque') {
        const cache = await caches.open(RUNTIME_CACHE);
        cache.put(request, response.clone()).catch(() => undefined);
      }
      return response;
    })
    .catch(() => undefined);

  if (cached) {
    // Une requête vers /assets/ est immuable : pas besoin de la rafraîchir.
    return cached;
  }
  const response = await network;
  return response ?? Response.error();
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  // Ne gère que la même origine : les flux distants ne sont jamais interceptés.
  if (url.origin !== self.location.origin) return;
  if (isBypassed(url)) return;

  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(request));
    return;
  }
  event.respondWith(handleAsset(request));
});

/** Permet à l'application de forcer l'activation d'une nouvelle version. */
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
});
