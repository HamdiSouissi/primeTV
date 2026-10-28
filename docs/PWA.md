# Application web & PWA

PrimeTV est **une seule application web**. Il n'existe plus d'application mobile
native, d'APK ni de second front-end : le navigateur est la plateforme cible, et
l'installation se fait via les **Progressive Web App** standards (manifeste +
service worker).

---

## 1. Pourquoi une application web unique

| Avant (Flutter Android + Web) | Maintenant (PWA) |
|---|---|
| Deux bases de code (React + Dart), deux builds, deux images Docker | **Un seul front-end** React + TypeScript |
| APK à signer, à distribuer, à mettre à jour | Mise à jour **automatique** à chaque déploiement |
| Lecteur natif ExoPlayer (mais compilation Android nécessaire) | `hls.js` / `dash.js` / `<video>` : HLS, DASH, MP4, MPEG-TS, radios |
| PiP natif Android | **Picture-in-Picture** du navigateur (Chrome, Edge, Safari) |
| Installation par fichier | **Installation en un clic** (écran d'accueil ou bureau) |

Conséquences concrètes : un seul `Dockerfile` de front-end, un seul pipeline CI,
aucun SDK Android à installer, et une expérience identique sur ordinateur,
tablette et téléphone.

## 2. Fonctionnement de la PWA

| Fichier | Rôle |
|---|---|
| `web/public/manifest.webmanifest` | Nom, icônes, couleurs, `display: standalone`, raccourcis (Chaînes, Sport, Guide, Favoris) |
| `web/public/sw.js` | Service worker : app shell en *stale-while-revalidate*, navigation réseau-d'abord, `/api/**` **jamais** mis en cache, flux vidéo non interceptés |
| `web/public/offline.html` | Page de repli en cas de coupure réseau |
| `web/public/icons/*.png` | Icônes 192/512, version *maskable*, icône iOS 180 px (générées par `scripts/generate-icons.py`) |
| `web/src/lib/pwa.ts` | Enregistrement du SW **en production uniquement**, activation immédiate des mises à jour |
| `web/src/components/InstallButton.tsx` | Bouton **Installer** (visible quand le navigateur expose `beforeinstallprompt`) |

### Stratégies de cache

| Ressource | Stratégie | Raison |
|---|---|---|
| HTML de navigation | réseau d'abord → cache → `offline.html` | contenu frais, repli hors ligne |
| JS / CSS / images | *stale-while-revalidate* | démarrage instantané, mise à jour en tâche de fond |
| `/assets/*` (hachés) | cache immuable (Nginx `expires 1y`) | jamais modifiés |
| `/api/**` | **réseau uniquement** | données privées, temps réel, jetons |
| `/streams/proxy`, `.m3u8`, `.mpd`, `.ts`, `.m4s` | non interceptés | le lecteur gère ses propres requêtes `Range` |
| `sw.js`, `manifest.webmanifest` | `no-cache` | mises à jour immédiates |

Le service worker n'intercepte **que** la même origine : il ne voit jamais les
manifestes et segments distants, et ne peut donc pas casser la lecture.

## 3. Installer l'application

### Android (Chrome, Edge, Samsung Internet)
1. Ouvrez l'instance PrimeTV (`https://tv.example.com`).
2. Acceptez le bandeau **Installer**, ou ⋮ → **Installer l'application**.
3. L'icône PrimeTV apparaît dans le tiroir d'applications ; elle s'ouvre en plein écran.

### iOS / iPadOS (Safari)
1. Ouvrez l'instance dans **Safari** (obligatoire pour l'installation).
2. Bouton **Partager** → **Sur l'écran d'accueil** → **Ajouter**.
3. L'app s'ouvre sans barre d'adresse ; les données restent dans le navigateur.

### Ordinateur (Chrome, Edge, Brave)
1. Icône **Installer** dans la barre d'adresse, ou bouton **Installer** de PrimeTV.
2. Une fenêtre autonome est créée (menu Démarrer sous Windows, Launchpad sous macOS).

> **HTTPS requis.** Les service workers n'existent qu'en contexte sécurisé :
> `https://…` ou `http://localhost`. Sur une IP LAN en HTTP, l'application
> fonctionne mais sans installation ni cache hors ligne.

## 4. Mise à jour

1. Déployez la nouvelle version (`./scripts/update.sh` ou `docker compose up -d --build web`).
2. Au chargement suivant, le service worker détecte un `sw.js` modifié, l'active et
   recharge la page une fois (aucune action utilisateur).
3. Pour forcer la reprise : fermez tous les onglets PrimeTV puis rouvrez l'application.

Le `CACHE_VERSION` (`src/lib/pwa.ts` / `public/sw.js`, constante `VERSION`) permet
d'invalider explicitement les anciens caches.

## 5. Vérifier l'installation

```bash
curl -s http://localhost:8080/manifest.webmanifest | jq .name
curl -sI http://localhost:8080/sw.js | grep -i 'content-type\|cache-control'
curl -s http://localhost:8080/ | grep -c 'manifest.webmanifest'
```

Dans Chrome : **DevTools → Application → Manifest / Service Workers**.
Un manifeste valide affiche les icônes, le nom et le bouton *Installability*.

## 6. Régénérer les icônes

```bash
cd web
python3 scripts/generate-icons.py    # écrit public/icons/*.png et public/favicon.png
```

Le script dessine le logo (écran arrondi + triangle *play* sur dégradé indigo/violet)
pixel par pixel et encode les PNG en `zlib` : aucune dépendance Python externe.

## 7. Limites assumées

* **iOS** ne propose pas d'invite d'installation programmatique (procédure manuelle
  ci-dessus) et applique ses propres règles de lecture vidéo en arrière-plan.
* Le **Picture-in-Picture** dépend du navigateur (Chrome/Edge/Safari récents).
* Les **radios** et certains codecs HEVC dépendent du support du navigateur ;
  le proxy relaie le flux mais ne transcode pas (pas de ffmpeg embarqué).
* Le mode hors ligne conserve l'interface et les dernières pages consultées, pas les
  données du catalogue : la lecture nécessite une connexion.
* Les flux **Widevine/PlayReady/FairPlay** restent bloqués (aucun contournement de DRM,
  voir [SECURITY.md](SECURITY.md#drm-et-legalite)).
