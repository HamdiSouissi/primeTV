# Sécurité & légalité

## 1. Modèle de sécurité

| Actif | Protection |
|---|---|
| Mots de passe utilisateurs | **PBKDF2-HMAC-SHA256**, 390 000 itérations, sel 16 octets, comparaison en temps constant |
| Jetons API | **JWT HS256** signés avec `SECRET_KEY`, `exp` + `jti` + `iss`, type `access`/`refresh` |
| Identifiants fournisseurs (Xtream) | **Fernet** (AES-128-CBC + HMAC-SHA256), clé dérivée de `SECRET_KEY` ; jamais renvoyés par l'API |
| Clés ClearKey | stockées par chaîne, réservées au propriétaire de la chaîne importée, **jamais journalisées** |
| Base de données | accès réseau interne uniquement, mot de passe fort, `pgcrypto` disponible |
| Cache | Redis interne, sans exposition publique |
| Transport | TLS 1.2/1.3 (Nginx/Traefik), HSTS en production |

## 2. Authentification & autorisation

* `POST /auth/login` accepte email **ou** nom d'utilisateur.
* Jetons d'accès 12 h, refresh 14 j, renouvellement explicite (pas de sliding session silencieuse).
* Un compte désactivé (`is_active=false`) reçoit **403** immédiatement.
* Rôles : `user` et `admin`. Les routes `/admin/*` exigent `role=admin`.
* Toutes les ressources (fournisseurs, playlists, EPG, favoris, historique) sont **scopées par utilisateur**
  ou par profil : un identifiant d'autrui renvoie 404, jamais 403 (pas d'énumération).
* Le front-end (unique application web) stocke les jetons dans `localStorage` via
  `zustand/persist` ; le service worker **ne met jamais en cache** les réponses `/api/**`.

### Rotation de `SECRET_KEY`

```bash
NEW=$(openssl rand -base64 48)
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$NEW|" .env
docker compose up -d backend
```

Conséquences : tous les jetons sont invalidés (reconnexion) et les mots de passe fournisseurs
chiffrés deviennent illisibles → **réenregistrez-les** avant de purger l'ancienne valeur.

## 3. Surface d'attaque & protections

| Risque | Mesure |
|---|---|
| **SSRF** (import d'URL arbitraire) | `validate_remote_url()` : schéma http/https, résolution DNS, blocage loopback/privé/link-local/multicast ; `ALLOW_PRIVATE_STREAM_HOSTS=false` par défaut |
| **Relais ouvert** (proxy) | `/streams/proxy` exige `channel_id` et vérifie que l'hôte appartient au domaine du flux |
| **Injection SQL** | ORM SQLAlchemy paramétré, aucune concaténation |
| **XSS** | React échappe par défaut ; aucun `dangerouslySetInnerHTML` |
| **CSRF** | API sans cookie (Bearer token) + CORS restreint en production |
| **Bruteforce** | rate limit applicatif (300 req/min) + zone Nginx `login_limit` (5 req/min) |
| **Dépassement mémoire** | plafonds de taille (playlist 40 Mo, XMLTV 80 Mo, manifeste 512 Ko), streaming borné |
| **Épuisement CPU/réseau (scan)** | `PROBE_CONCURRENCY`, `PROBE_TIMEOUT_SECONDS`, `SCAN_MAX_CHANNELS` |
| **Secrets dans les logs** | aucun mot de passe/clé journalisé ; erreurs tronquées |
| **Clickjacking** | `X-Frame-Options: SAMEORIGIN`, `frame-ancestors` côté proxy |
| **MIME sniffing** | `X-Content-Type-Options: nosniff` |
| **Fuites d'infos** | `server_tokens off`, pas de stack trace dans les réponses 500 |

### Durcissements recommandés en production

1. `ALLOW_REGISTRATION=false` si l'instance est privée.
2. `CORS_ORIGINS=https://votre-domaine` (jamais `*` avec credentials).
3. `TRUSTED_HOSTS=votre-domaine`.
4. `DOCS_ENABLED=false` si l'API n'est pas destinée à des tiers.
5. Ajouter une authentification d'entrée (Traefik BasicAuth ou SSO) pour une instance publique.
6. Exécuter les conteneurs en utilisateur non-root (déjà le cas du backend : `primetv`).
7. Sauvegardes chiffrées (age/GPG) et stockées hors du serveur.

## 4. Signalement d'une vulnérabilité

Merci de **ne pas ouvrir d'issue publique**. Écrivez à l'équipe du dépôt (GitHub Security Advisory
de préférence) avec :
description, étapes de reproduction, impact, version concernée. Réponse sous 72 h ouvrées.
Aucune prime financière n'est proposée ; les crédits sont mentionnés dans le CHANGELOG.

<a id="drm-et-legalite"></a>

## 5. DRM et légalité

### Ce que fait PrimeTV

* Analyse technique des manifestes : `#EXT-X-KEY` (HLS), `ContentProtection` (DASH).
* Classification : `none`, `aes-128`, `clearkey`, `sample-aes`, `widevine`, `playready`, `fairplay`.
* Affichage d'un badge et blocage de la lecture pour les DRM (Widevine/PlayReady/FairPlay).
* Saisie de clés **ClearKey / AES-128** pour du contenu que l'utilisateur est en droit de lire
  (par exemple un flux libre protégé par une clé publique, ou son propre abonnement).
* Relais de la clé distante **si la source l'autorise déjà** (l'utilisateur y a accès).

### Ce que PrimeTV ne fait pas et ne fera pas

* Aucune extraction, génération ou devinette de clé.
* Aucun contournement de Widevine / PlayReady / FairPlay.
* Aucune intégration de serveurs de clés non autorisés, de « panels » pirates ou de listes de flux piratés.
* Aucune recherche automatisée de « sources déchiffrées » sur Internet.

### Cadre légal

Selon votre pays, la réception non autorisée de services de télévision payante peut constituer une
infraction pénale, et le contournement de mesures techniques de protection est interdit (par ex.
directive 2001/29/CE en Europe, DMCA §1201 aux États-Unis, lois nationales équivalentes).
Le catalogue de démonstration ne contient que des flux publics de test.

**En cas de doute : n'importez pas la source.**

Cas concret des chaînes sportives payantes (beIN Sports, Canal+, OSN) : voir
[PAID_CHANNELS.md](PAID_CHANNELS.md) — voies légales, tarifs opérateurs et
comportement de PrimeTV face au DRM.

## 6. Données personnelles (RGPD)

| Donnée | Finalité | Base légale | Conservation |
|---|---|---|---|
| Email, pseudo, mot de passe haché | Compte | Exécution du contrat | Jusqu'à suppression du compte |
| Profils (nom, langue, PIN) | Personnalisation | Consentement | Idem |
| Favoris / historique | Reprise de lecture | Consentement | Jusqu'à purge par l'utilisateur |
| Logo d'activité | Sécurité/audit | Intérêt légitime | 90 jours conseillé |
| Journaux techniques | Sécurité | Intérêt légitime | 30 jours (rotation Docker) |

* Aucun traceur publicitaire, aucune dépendance analytics.
* Droit à l'effacement : suppression du compte en cascade (`ON DELETE CASCADE`).
* Droit d'accès/portabilité : les données sont exposées par l'API (`/favorites`, `/history`, `/auth/me`).
* L'auto-hébergement vous place en responsable de traitement : complétez votre registre.

## 7. Recommandations pour les utilisateurs

* Utilisez un mot de passe unique et long ; activez un PIN sur les profils enfants.
* Ne partagez pas votre `.env` ni vos capture d'écran contenant des jetons.
* Vérifiez l'origine de chaque playlist avant import.
* Sur un réseau public, n'utilisez pas d'API en HTTP.
