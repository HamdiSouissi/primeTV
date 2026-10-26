# PrimeTV Mobile — application Android & Web (Flutter)

Client officiel **Flutter** de PrimeTV : il consomme l'API REST (`/api/v1`) et ne contient
**aucun flux** ni aucune playlist. Une seule base de code produit :

* une application **Android** native (ExoPlayer via `video_player`, PiP, plein écran) ;
* une version **Web** compilée (`flutter build web`) servie par Nginx sous `/mobile/`.

---

## 1. Fonctionnalités

| Écran | Contenu |
|---|---|
| **Connexion** | Authentification JWT (email ou pseudo), création de compte, sélection du profil, URL de l'API affichée pour le diagnostic |
| **Tableau de bord** | Compteurs (chaînes, bouquets, playlists, flux actifs), rails « Sport », « Arabe », « Reprendre la lecture », derniers favoris |
| **Chaînes** | Recherche plein texte, filtres catégorie / langue / bouquet / radios, pagination infinie, badge chiffré/DRM, favori en un geste |
| **Favoris** | Liste des favoris du profil, lecteur direct, suppression |
| **Sources** | Import de playlist par URL ou fichier, portail Xtream, sources EPG, synchronisation |
| **Lecteur** | HLS / DASH / MP4 / MPEG-TS / radios, qualité manuelle, sous-titres, plein écran, Picture-in-Picture, reprise et enregistrement d'historique |
| **Réglages** | Multi-profils (création/suppression, PIN), thème sombre/clair/système, mentions légales, déconnexion |

L'app gère également : `pull-to-refresh` sur toutes les listes, mise en cache des jetons dans
`flutter_secure_storage`, thème Material 3, transitions animées, états vides et messages d'erreur
explicites en français.

## 2. Prérequis

* Flutter **≥ 3.22** (Dart ≥ 3.4) — `flutter --version`
* Android SDK 34 + un appareil ou émulateur (pour la cible Android)
* Une instance PrimeTV joignable (API `http://<hôte>:8000` en développement, `:8080` via Nginx
  en production)

## 3. Lancement

```bash
cd mobile
flutter pub get

# Émulateur Android : 10.0.2.2 = localhost de la machine hôte
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1

# Appareil physique : utilisez l'IP LAN de la machine
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000/api/v1

# Version Web locale
flutter run -d chrome --web-port 5174 \
  --dart-define=API_BASE_URL=http://localhost:8000/api/v1
```

`API_BASE_URL` est facultatif : par défaut l'app utilise
`http://10.0.2.2:8000/api/v1` sur Android et `http://localhost:8000/api/v1` sur les autres
plateformes (voir `lib/core/config.dart`). L'URL peut aussi être modifiée depuis l'écran de
connexion (icône serveur), ce qui permet de tester plusieurs backends sans recompiler.

### Comptes de démonstration

```
admin@primetv.io / PrimeTV#2026   (administrateur)
```

Ils n'existent que si le backend a été démarré avec `SEED_DEMO_DATA=true`.

## 4. Builds

```bash
# APK de release (signature : voir docs/DEPLOYMENT.md#4-signature-android)
flutter build apk --release --dart-define=API_BASE_URL=https://tv.example.com/api/v1

# App Bundle pour le Play Store
flutter build appbundle --release --dart-define=API_BASE_URL=https://tv.example.com/api/v1

# Web (servi sous /mobile/)
flutter build web --release --base-href /mobile/ \
  --dart-define=API_BASE_URL=https://tv.example.com/api/v1
```

Les artefacts se trouvent dans `build/app/outputs/flutter-apk/` et `build/web/`.

### Conteneur Docker (Web)

```bash
docker build -t primetv-mobile:latest mobile/
docker run --rm -p 8081:80 primetv-mobile:latest
# http://localhost:8081/mobile/
```

L'image est un build multi-étapes : Flutter compile l'app Web, puis Nginx sert les fichiers
statiques (gzip, cache des assets, fallback SPA, reverse proxy `/api` vers le backend).

## 5. Tests & qualité

```bash
cd mobile
flutter analyze          # lints (analysis_options.yaml)
flutter test             # tests unitaires (lib/models, config)
flutter test --coverage  # rapport coverage/lcov.info
dart format --output=none --set-exit-if-changed lib test
```

Les tests couvrent la désérialisation des modèles (`Channel`, `ChannelPage`, profils),
la normalisation des URLs de médias et les valeurs par défaut de configuration. Ils
n'exigent ni réseau ni émulateur.

## 6. Arborescence

```
mobile/
├── lib/
│   ├── core/
│   │   ├── config.dart       # API_BASE_URL, résolution des URLs relatives, constantes
│   │   ├── api_client.dart   # client HTTP, gestion des erreurs et du 401
│   │   └── storage.dart      # jetons (secure storage) + préférences
│   ├── models/models.dart    # User, Profile, Channel, Playlist, Epg, Stats…
│   ├── services/api_service.dart  # toutes les routes de l'API
│   ├── state/app_state.dart  # ChangeNotifier : session, filtres, favoris, thème
│   ├── theme/app_theme.dart  # thèmes Material 3 sombre/clair
│   ├── widgets/common.dart   # cartes, badges, états vides, champs, boutons
│   ├── screens/
│   │   ├── login_screen.dart
│   │   ├── home_shell.dart       # navigation à 5 onglets
│   │   ├── dashboard_screen.dart
│   │   ├── channels_screen.dart
│   │   ├── favorites_screen.dart
│   │   ├── sources_screen.dart
│   │   ├── player_screen.dart
│   │   └── settings_screen.dart
│   └── main.dart             # bootstrap, providers, routes
├── test/models_test.dart
├── android/                  # projet Gradle complet (PiP, INTERNET, cleartext dev)
├── Dockerfile                # build Flutter Web + Nginx
├── nginx.conf
└── pubspec.yaml
```

## 7. Détails d'implémentation

* **HTTP** : `package:http`, JSON strict, erreurs normalisées en `ApiException`
  (`statusCode` + `message`). Un 401 purge la session et renvoie vers la connexion.
* **État** : un seul `AppState` (`ChangeNotifier`) exposé par `provider` ; les écrans
  écoutent sélectivement pour limiter les reconstructions.
* **URLs relatives** : l'API renvoie des URLs de lecture relatives
  (`/api/v1/streams/proxy?…`) ; `AppConfig.absoluteMediaUrl()` les préfixe avec l'origine
  du backend avant de les passer au lecteur.
* **Sécurité** : jetons dans le Keystore/Keychain (`flutter_secure_storage`), aucun secret
  dans le code. HTTPS obligatoire en production ; `usesCleartextTraffic` n'est activé que
  pour le développement local.
* **PiP** : `MainActivity` active `android:supportsPictureInPicture`, l'app bascule en PiP
  sur `onUserLeaveHint`. La lecture Web utilise l'API Picture-in-Picture du navigateur
  quand elle est disponible.
* **DRM** : l'app affiche un badge et un message explicite pour les flux Widevine/PlayReady
  et n'effectue aucun contournement (voir `docs/SECURITY.md#drm-et-legalite`).

## 8. Dépannage

| Symptôme | Solution |
|---|---|
| `Cleartext HTTP traffic not permitted` | utilisez HTTPS, ou vérifiez que `usesCleartextTraffic` est bien dans `android/app/src/main/AndroidManifest.xml` (dev) |
| Écran blanc après connexion | l'URL de l'API est probablement `localhost` sur un appareil physique → IP LAN |
| `flutter pub get` échoue | vérifiez l'accès à pub.dev ; en entreprise, configurez `PUB_HOSTED_URL` |
| Vidéo noire | codec non supporté par ExoPlayer ou flux hors ligne ; testez un flux HLS public |
| PiP absent | vérifiez la version d'Android (≥ 8.0) et l'autorisation système |

Voir aussi [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) pour les problèmes côté API.
