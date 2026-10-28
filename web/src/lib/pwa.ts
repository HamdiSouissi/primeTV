/**
 * Enregistrement du service worker (PWA installable).
 *
 * - Aucun impact sur le développement : le SW n'est enregistré qu'en production
 *   (`import.meta.env.PROD`), pour ne pas masquer les rechargements à chaud.
 * - En cas de nouvelle version détectée, on demande au SW d'activer
 *   immédiatement puis on recharge une seule fois la page.
 * - Silencieux en cas d'échec (navigateur sans support, contexte non sécurisé,
 *   iframe de prévisualisation…) : l'application fonctionne sans PWA.
 */

const SW_URL = '/sw.js';

export function registerServiceWorker(): void {
  if (!import.meta.env.PROD) return;
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;
  if (!window.isSecureContext) return;

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register(SW_URL, { scope: '/' })
      .then((registration) => {
        registration.addEventListener('updatefound', () => {
          const installing = registration.installing;
          if (!installing) return;
          installing.addEventListener('statechange', () => {
            if (installing.state === 'installed' && navigator.serviceWorker.controller) {
              // Une nouvelle version est prête : on l'active et on recharge.
              installing.postMessage('SKIP_WAITING');
              window.location.reload();
            }
          });
        });
      })
      .catch(() => {
        /* PWA indisponible : on continue sans service worker. */
      });
  });
}
