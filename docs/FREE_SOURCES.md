# Sources IPTV gratuites et légales

Ce guide liste les **sources gratuites que vous pouvez importer dans PrimeTV sans
enfreindre la loi** : flux publiés par les diffuseurs eux-mêmes (service public,
services internationaux, chaînes FAST financées par la publicité) et listes
maintenues par des projets open source qui n'indexent que du *free-to-air*.

> ⚠️ **PrimeTV n'héberge aucun flux et n'en fournit aucun.** Ce document décrit
> des sources tierces publiques. Vous restez responsable de ce que vous importez.
> Voir [SECURITY.md](SECURITY.md#drm-et-legalite).

---

## 1. Ce qui est légal — et ce qui ne l'est pas

| ✅ Autorisé | ❌ À éviter |
|---|---|
| Chaînes **free-to-air** (service public : France TV, ARD/ZDF, RTVE, TRT, chaînes d'État…) diffusées en clair sur Internet | « Abonnement IPTV » à 5 €/mois donnant 20 000 chaînes payantes (beIN, Canal+, OSN…) : **revendication non autorisée** |
| Services **FAST** gratuits financés par la publicité (Pluto TV, Samsung TV Plus, Rakuten TV, Plex, Red Bull TV…) | Serveurs **Xtream « panel »** vendus sur Telegram, listes « M3U premium », « activation à vie » |
| Chaînes d'information internationales financées par un État (DW, France 24, Al Jazeera, Euronews, TV5Monde) | Serveurs qui proposent des **matchs de championnat** ou des films récents « en direct » |
| Listes communautaires **iptv-org** / **Free-TV** (flux publics uniquement, retrait sur demande) | Fichiers M3U contenant des **clés DRM** ou des « comptes » partagés |
| Vos **propres** identifiants Xtream si vous avez un abonnement légitime | Tout service demandant d'installer un APK « spécial » ou de désactiver l'antivirus |

**Signaux d'alerte d'une offre pirate** : prix dérisoire, milliers de chaînes
premium, paiement en crypto/Telegram, aucune mention légale, aucun nom d'exploitant,
promesse de « tous les sports », « pas de coupure », procès ou blocages DNS.

En Tunisie, en France et dans l'UE, la réception non autorisée d'un service de
télévision payant et le contournement de mesures techniques de protection sont
punis par la loi. PrimeTV est un **lecteur** : il ne contourne rien.

---

## 2. Les trois sources recommandées

### 2.1 iptv-org (le plus complet, mis à jour quotidiennement)

Projet open source (licence *Unlicense*, ~140 000 ★) qui recense les chaînes du
monde entier **disponibles publiquement**, avec vérification automatique des liens.

| Sélection | URL à coller dans PrimeTV | Chaînes |
|---|---|---|
| Actualités | `https://iptv-org.github.io/iptv/categories/news.m3u` | ≈ 1 040 |
| Sport | `https://iptv-org.github.io/iptv/categories/sports.m3u` | ≈ 460 |
| Jeunesse | `https://iptv-org.github.io/iptv/categories/kids.m3u` | ≈ 430 |
| Cinéma | `https://iptv-org.github.io/iptv/categories/movies.m3u` | ≈ 770 |
| Musique | `https://iptv-org.github.io/iptv/categories/music.m3u` | ≈ 780 |
| Documentaires | `https://iptv-org.github.io/iptv/categories/documentary.m3u` | ≈ 250 |
| Religion | `https://iptv-org.github.io/iptv/categories/religious.m3u` | ≈ 810 |
| **Arabe** (toutes chaînes arabophones) | `https://iptv-org.github.io/iptv/languages/ara.m3u` | ≈ 350 |
| Tunisie | `https://iptv-org.github.io/iptv/countries/tn.m3u` | variable |
| Algérie | `https://iptv-org.github.io/iptv/countries/dz.m3u` | variable |
| Maroc | `https://iptv-org.github.io/iptv/countries/ma.m3u` | variable |
| Égypte | `https://iptv-org.github.io/iptv/countries/eg.m3u` | variable |
| France | `https://iptv-org.github.io/iptv/countries/fr.m3u` | ≈ 250 |
| Turquie | `https://iptv-org.github.io/iptv/countries/tr.m3u` | ≈ 120 |
| Espagne | `https://iptv-org.github.io/iptv/countries/es.m3u` | ≈ 180 |
| **Tout le catalogue** | `https://iptv-org.github.io/iptv/index.m3u` | ≈ 10 000 |

> 💡 Préférez les **sélections** au catalogue complet : l'import est plus rapide,
> le scan plus utile, et l'interface reste lisible. Les compteurs évoluent chaque jour.
> D'autres découpages existent (`index.category.m3u`, `index.language.m3u`,
> `index.country.m3u`, `languages/<iso3>.m3u`, `countries/<iso2>.m3u`).

### 2.2 Free-TV (sélection humaine, une URL par chaîne)

Liste curatée à la main, priorité à la qualité :

```
https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8
```

### 2.3 Flux officiels de diffuseurs (les plus stables)

Ces chaînes publient elles-mêmes leur flux HLS. Une copie prête à l'emploi est
fournie dans [`examples/free-fta-playlist.m3u`](../examples/free-fta-playlist.m3u) :

| Chaîne | Type | Langue |
|---|---|---|
| Al Jazeera English / Arabic | Information | EN / AR |
| France 24 (FR / EN / AR) | Information | FR / EN / AR |
| DW English, Tagesschau 24 | Information | EN / DE |
| NASA TV | Science | EN |
| Red Bull TV | Sport / spectacle | EN |
| franceinfo, France Inter, France Musique, France Culture | Radios publiques | FR |

Chaque diffuseur publie aussi ses flux sur son site officiel (« Regarder en
direct ») : c'est la source la plus fiable pour retrouver une URL quand elle change.

---

## 2.4 Et les chaînes payantes (beIN Sports, Canal+…) ?
Elles ne sont **pas** dans ces listes, et ne le seront jamais : ce sont des services
cryptés (Widevine/PlayReady). Les voies légales (beIN CONNECT via Orange/Ooredoo en
Tunisie, abonnement direct) et l'intégration d'un abonnement autorisé sont décrites
dans **[PAID_CHANNELS.md](PAID_CHANNELS.md)**.

---

## 3. Importer dans PrimeTV (3 méthodes)

### a. Panneau intégré (le plus simple)

**Sources & playlists → onglet Playlists → « Sources libres prêtes à l'emploi »** :
les sélections iptv-org et Free-TV sont proposées par catégorie, avec un bouton
**Importer** qui crée la playlist en un clic (`web/src/lib/freeSources.ts`).

### b. URL personnalisée

**Sources & playlists → Importer → onglet « URL »**, collez l'adresse, validez.
Pour un fichier local, utilisez l'onglet **Fichier** (`.m3u` / `.m3u8`).

### c. API / ligne de commande

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@primetv.io","password":"PrimeTV#2026"}' | jq -r .access_token)

# Import par URL
curl -s -X POST localhost:8080/api/v1/playlists \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Actu iptv-org","url":"https://iptv-org.github.io/iptv/categories/news.m3u"}'

# Import d'un fichier local
curl -s -X POST localhost:8080/api/v1/playlists/upload \
  -H "Authorization: Bearer $TOKEN" -F "file=@examples/free-fta-playlist.m3u"
```

Réponse : `{ total, created, updated, radios, encrypted, categories, epg_urls }`.

---

## 4. Après l'import : les 4 réflexes

1. **Scan** — *Scan & actualisation* teste chaque flux (`HTTP`, type, variantes,
   DRM) et met à jour statut et qualité : `POST /api/v1/scan`.
   Les flux injoignables passent en `offline` sans disparaître du catalogue.
2. **Catégorisation** — automatique (Sport, News, Movies, Kids, Music, Religion,
   Documentary, Culture…) à partir du nom, du groupe et de `tvg-language`.
   Corrigeable chaîne par chaîne (`PATCH /channels/{id}`).
3. **EPG** — associez un guide XMLTV pour le « en cours / à suivre » :
   - *Sources & playlists → EPG XMLTV → « Guides libres recommandés »* (Freeview UK,
     XML-TV-Fr) ;
   - l'association se fait par `tvg-id`, puis `epg_channel_id`, puis nom normalisé.
   Les `tvg-id` d'iptv-org suivent la nomenclature `NomPays.pays` (ex. `France2.fr`),
   que les générateurs XMLTV francophones réutilisent : l'association est immédiate.
4. **Favoris / profils** — chaque profil garde ses favoris et son historique
   (reprise de lecture incluse).

---

## 5. Comportement attendu avec les flux publics

| Situation | Ce que fait PrimeTV |
|---|---|
| Flux **hors ligne** ou déplacé | statut `offline` après scan ; remplacez l'URL dans le détail de la chaîne |
| Flux **geo-bloqué** (ex. DW Deutsch hors UE) | erreur 403 dans le scan ; la chaîne reste listée mais illisible depuis votre réseau |
| Flux **AES-128 / ClearKey** | badge « chiffrée » ; lecture possible si **vous** fournissez la clé (Accès → clés) |
| Flux **Widevine / PlayReady / FairPlay** | détecté et **bloqué** : il faut le lecteur agréé du diffuseur |
| Chaîne **radio** (MP3/AAC) | lecteur audio, icône Radio, filtrable |

Les listes communautaires changent tous les jours : un lien mort n'est pas un bug
de PrimeTV. Le bouton **Synchroniser** d'une playlist remet le catalogue à jour
(chaînes disparues supprimées, nouvelles ajoutées).

---

## 6. Quand une URL ne fonctionne plus

1. Ouvrez la page officielle du diffuseur (« direct », « live ») et cherchez le
   nouveau manifeste (`.m3u8`) dans les outils de développement du navigateur
   (onglet Réseau, filtre `m3u8`).
2. Ou repartez de `https://iptv-org.github.io/iptv/countries/<pays>.m3u`, souvent
   corrigé dans les 24 h.
3. Mettez à jour la chaîne : *détail de la chaîne → URL du flux*, ou
   `PATCH /api/v1/channels/{id}` avec le nouveau `stream_url`.

---

## 7. EPG gratuits

| Guide | Couverture | URL |
|---|---|---|
| Freeview-EPG (dp247) | Royaume-Uni, XMLTV quotidien | `https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml` |
| XML-TV-Fr | France / Belgique / Suisse (auto-hébergement ou instance publique) | `https://xmltvfr.fr/` |
| iptv-org/epg | générateurs par site (à exécuter soi-même) | `https://github.com/iptv-org/epg` |

Un guide pèse de quelques Mo à ~80 Mo : PrimeTV plafonne l'import
(`MAX_XMLTV_BYTES`) et purge les programmes passés lors de chaque synchronisation.

---

## 8. Alternatives légales sans M3U

Si votre besoin est surtout « regarder la TV gratuitement », ces services sont
légaux et ne nécessitent aucun import :

- **FAST** : Pluto TV, Samsung TV Plus, Rakuten TV, Plex Live TV, LG Channels
  (gratuits, financés par la publicité, catalogue propre à chaque pays).
- **Replay des chaînes publiques** : france.tv, ARD/ZDF Mediathek, RTVE Play, TRT İzle.
- **Abonnement légal** : si un fournisseur Xtream vous a fourni des identifiants,
  PrimeTV sait s'y connecter (*Sources → Fournisseur → Xtream*).

---

## 9. Références

- iptv-org — dépôt et listes : <https://github.com/iptv-org/iptv>
- iptv-org — générateurs EPG : <https://github.com/iptv-org/epg>
- Free-TV — sélection curatée : <https://github.com/Free-TV/IPTV>
- XML-TV-Fr — guide francophone : <https://github.com/racacax/XML-TV-Fr>
- Freeview-EPG — guide britannique : <https://github.com/dp247/Freeview-EPG>

*Dernière vérification des dépôts : octobre 2026 (activité confirmée le jour même).*
