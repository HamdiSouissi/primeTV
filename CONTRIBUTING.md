# Contribuer à PrimeTV

Merci de votre intérêt ! Ce document décrit l'environnement de développement, les
conventions du projet et le processus de contribution.

> **Règle d'or** : PrimeTV est un lecteur IPTV pour des sources **légitimes**. Toute
> contribution facilitant le contournement de DRM ou la diffusion de flux piratés sera
> refusée (voir [docs/SECURITY.md](docs/SECURITY.md#drm-et-legalite)).

---

## 1. Code de conduite

* Soyez respectueux et constructif ; critiquez le code, pas la personne.
* Pas de contenu politique, religieux, haineux ou illégal dans les échanges.
* Les mainteneurs peuvent fermer sans discussion les contributions hors périmètre légal.

## 2. Licence des contributions

En proposant une *pull request*, vous acceptez que votre contribution soit publiée sous
licence **MIT** (voir [LICENSE](LICENSE)). Aucun CLA n'est demandé. Les dépendances
ajoutées doivent être open source sous licence MIT / Apache-2.0 / BSD / ISC.

## 3. Mise en route

```bash
git clone https://github.com/HamdiSouissi/primeTV.git
cd primeTV
./scripts/dev.sh          # crée les venv, installe les dépendances, seed, démarre API + web
```

Ou manuellement :

```bash
# Backend (Python ≥ 3.11)
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cp ../.env.example ../.env           # renseigner SECRET_KEY / POSTGRES_PASSWORD
SEED_DEMO_DATA=true .venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (Node ≥ 20)
cd web
npm install
npm run dev                          # http://localhost:5173, proxy /api → :8000

# Mobile (Flutter ≥ 3.22)
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Comptes de démonstration : `admin@primetv.io` / `PrimeTV#2026` (créé uniquement si
`SEED_DEMO_DATA=true`).

## 4. Arborescence & responsabilités

```
backend/app/
├── api/            # routeurs FastAPI (une ressource = un module) + deps d'auth
├── core/           # config, sécurité, mots de passe, cache, rate limit, pagination
├── db/             # session, base déclarative, init schéma
├── models/         # modèles SQLAlchemy (1 module par domaine)
├── schemas/        # contrats Pydantic exposés par OpenAPI
├── services/       # logique métier : m3u, xtream, streams, classifier, importer,
│                   # epg, xmltv, scanner, proxy, seed
└── main.py         # application, middlewares, handlers d'erreurs
web/src/
├── api/            # client axios + endpoints typés
├── components/     # UI réutilisable (Layout, ChannelCard, VideoPlayer, PlayerOverlay…)
├── hooks/          # react-query (cache, pagination, mutations)
├── pages/          # une page = une route
├── store/          # zustand (auth, ui, toast)
└── test/           # tests Vitest + Testing Library
mobile/lib/
├── core/           # config, client HTTP, stockage sécurisé
├── models/         # modèles Dart (fromJson/toJson)
├── screens/        # écrans (login, dashboard, chaînes, favoris, sources, lecteur, réglages)
├── services/       # ApiService (un point d'entrée HTTP)
├── state/          # AppState (ChangeNotifier)
├── theme/          # thème Material 3 sombre/clair
└── widgets/        # composants partagés
```

## 5. Style de code

### Python

* `ruff` avec une longueur de ligne de 120 (voir `backend/pyproject.toml`).
* Typage systématique (`from __future__ import annotations`, annotations de retour).
* Commentaires et docstrings **en français**, phrases complètes.
* Pas de dépendance lourde (pas de pandas, pas de ffmpeg) sans discussion préalable.
* Les requêtes SQL passent par SQLAlchemy ; aucune concaténation de chaîne SQL.
* Une route = un schéma de sortie Pydantic (`response_model`) + un résumé (`summary`).

### TypeScript / React

* Composants fonctionnels, hooks, `strict` activé ; pas de `any` implicite.
* TailwindCSS uniquement : pas de CSS-in-JS, pas de framework UI propriétaire.
* Les appels réseau passent par `src/api/endpoints.ts` (jamais d'`axios` brut dans une page).
* Les états serveur passent par **react-query** ; l'état global par **zustand**.
* Textes d'interface en français, accessibilité (labels, `aria-*`, focus visible).

### Dart / Flutter

* `flutter_lints`, `const` dès que possible, `SingleChildScrollView` pour les formulaires.
* Les modèles sont immuables (`final`) avec `fromJson` tolérant (valeurs nulles).
* Le réseau passe exclusivement par `ApiService`.

### Git

Messages au format **Conventional Commits** :

```
feat(scan): sonde les manifestes DASH et détecte Widevine
fix(web): corrige la double notification toast
docs(install): ajoute la procédure systemd
test(backend): couvre l'import Xtream
chore(ci): ajoute le job compose
```

* Un commit = un changement cohérent.
* Branche : `feat/…`, `fix/…`, `docs/…` (la branche de travail actuelle peut différer).
* Pas de fichier généré, pas de secret, pas de base de données `.db` dans le dépôt.

## 6. Tests

```bash
./scripts/test-all.sh          # tout : lint + tests + build + smoke API

cd backend && .venv/bin/ruff check app tests && .venv/bin/pytest -q
cd web && npm run lint && npm run test && npm run build
cd mobile && flutter analyze && flutter test
BASE_URL=http://localhost:8000 ./tests/api/smoke.sh
```

Règles :

* **Tout nouveau endpoint** doit avoir au moins un test (succès + cas d'erreur).
* **Tout nouveau composant** non trivial doit avoir un test de rendu.
* Les tests ne doivent pas dépendre d'Internet (les appels sortants sont simulés).
* Un test qui échoue pour une raison d'environnement doit être marqué `skip` avec justification.

## 7. Ajouter une fonctionnalité

### Nouveau champ de chaîne

1. Modèle : `backend/app/models/catalog.py` (+ index si filtré).
2. Schéma : `backend/app/schemas/catalog.py` (`ChannelOut`, `ChannelUpdate`).
3. Import : `backend/app/services/importer.py`.
4. Migration : `docker compose exec backend python -m app.db.init_db` (schéma recréé en dev ;
   en production, fournir une migration SQL documentée — Alembic est décrit dans
   [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)).
5. Frontend : `web/src/api/types.ts` + composant d'affichage.
6. Test backend + test frontend.

### Nouvelle catégorie

Ajoutez une entrée dans `CATEGORY_RULES` (`backend/app/services/classifier.py`) avec ses
mots-clés (dont l'arabe et le français), puis `python -m app.db.init_db` pour insérer la
catégorie. Aucun autre fichier à modifier : les filtres et le dashboard sont génériques.

### Nouveau type de source (ex. fournisseur X)

1. `backend/app/services/<source>.py` : produire un `ParsedPlaylist`
   (`app.services.m3u`).
2. `import_playlist_content()` fait le reste (catégorisation, upsert, EPG).
3. Routeur : exposer sous `/playlists/<source>` avec authentification.
4. Documenter dans `docs/API.md` et `docs/ADMIN_GUIDE.md`.

## 8. Processus de pull request

1. Ouvrez une *issue* pour discuter des changements structurants.
2. Forkez, créez une branche, commitez de façon atomique.
3. Vérifiez localement `./scripts/test-all.sh` (ou `make test`).
4. Décrivez : **quoi**, **pourquoi**, **comment tester**, captures pour l'UI.
5. La CI (`.github/workflows/ci.yml`) doit être verte : lint, tests, build, smoke API,
   validation du compose.
6. Un mainteneur relit ; comptez au moins une approbation pour les changements d'API.

Checklist de revue :

- [ ] Le comportement est couvert par des tests.
- [ ] Aucun secret ni donnée personnelle ajoutés.
- [ ] Les entrées utilisateur sont validées côté API (Pydantic) **et** côté UI.
- [ ] Les erreurs renvoient un code HTTP correct et un message en français.
- [ ] La documentation (`docs/`, README, `docs/API.md`) est mise à jour.
- [ ] L'accessibilité et le responsive ne régressent pas.
- [ ] Aucun DRM n'est contourné ; la politique légale est respectée.

## 9. Signaler un bug

Fournissez : version (`git rev-parse --short HEAD`), OS/navigateur, étapes de reproduction,
comportement attendu/observé, journaux (`docker compose logs backend`) et le `X-Request-Id`
de la réponse en erreur. **Ne joignez jamais** de jeton, mot de passe ou clé.

## 10. Proposer une traduction

Les chaînes d'interface sont en français. Une internationalisation (i18n) est un chantier
identifié : ouvrez une issue avant de commencer pour éviter les doublons. Les catégories et
langues d'import sont déjà multilingues (arabe, français, anglais, turc, espagnol).
