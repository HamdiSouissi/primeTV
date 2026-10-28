# Chaînes payantes et cryptées (beIN Sports, Canal+, OSN…) : les voies légales

> **Réponse courte** : PrimeTV ne fournit pas, et ne cherchera pas, de « serveurs »
> ou de listes de chaînes cryptées comme beIN Sports. Ces flux sont soit protégés
> par un DRM infranchissable (Widevine/PlayReady), soit distribués illégalement.
> Ce document explique **pourquoi**, puis **comment regarder ces chaînes légalement**
> et **ce que PrimeTV peut faire avec un abonnement légitime**.

---

## 1. Pourquoi aucune liste « beIN Sports déchiffré » n'est proposée

| Raison | Explication |
|---|---|
| **Technique** | beIN CONNECT (et Canal+, OSN, Netflix…) utilise **Widevine / PlayReady**. La clé de déchiffrement est délivrée par un serveur de licences après authentification, dans un module de sécurité du lecteur. Une URL `.m3u8` seule **ne contient aucune clé** : la « déchiffrer » revient à casser le DRM du diffuseur. |
| **Légal** | Rediffuser ou recevoir sans autorisation un service payant est une infraction (Tunisie : loi sur les communications et la propriété littéraire et artistique ; UE : directive 2001/29/CE §6 ; USA : DMCA §1201). beIN Media Group poursuit activement les revendeurs et les hébergeurs. |
| **Sécurité** | Les listes « premium à 5 €/mois » viennent de panels Xtream pirates : elles servent souvent d'appât (phishing, vol d'identifiants, malware sur le boîtier, revente de données). |
| **Produit** | Même si une telle liste « fonctionnait », elle serait cassée sous 48 h : ces serveurs changent d'URL en permanence pour échapper aux blocages. |

En conséquence, le code de PrimeTV **bloque volontairement** la lecture d'un flux
qui annonce Widevine/PlayReady/FairPlay :

```json
{
  "is_encrypted": true,
  "drm_systems": ["widevine"],
  "message": "Flux protégé par DRM (Widevine/PlayReady). Lecture non prise en charge : utilisez une source libre ou votre propre lecteur agréé."
}
```

Seul le **ClearKey / AES-128** est pris en charge, et uniquement avec une clé que
**vous** fournissez (`PUT /api/v1/channels/{id}/keys`), pour du contenu que vous
êtes en droit de lire (par exemple un flux libre protégé par une clé publique).

---

## 2. Regarder beIN Sports légalement en Tunisie

Les offres ci-dessous sont les canaux officiels. **Les tarifs évoluent** : vérifiez
toujours sur le site de l'opérateur avant de souscrire.

### beIN CONNECT via Orange Tunisie
- Service officiel **beIN CONNECT**, payé depuis le crédit téléphonique (pas de carte bancaire).
- Pass historiquement proposés : **jour ≈ 16 DT**, **mois ≈ 39 DT**, **année ≈ 390 DT**.
- Page : `https://www.orange.tn/bein-connect-orange`
- Donne accès à l'app officielle beIN CONNECT (mobile, tablette, navigateur, TV connectée).

### beIN CONNECT via Ooredoo Tunisie
- Souscription depuis le solde de recharge, portail dédié : `https://www.bein.ooredoo.tn/`
- Mêmes contenus (Ligue des champions, Premier League, LaLiga, Serie A, Ligue 1, NBA,
  beIN Gourmet, Jeem TV, Baraem…).

### Abonnement direct beIN CONNECT
- Site officiel beIN : `https://www.bein.com` → *beIN CONNECT* (selon la région MENA).
- Utile si vous ne passez pas par un opérateur tunisien.

### Autres diffuseurs légitimes selon vos droits
- **Canal+ / OSN** (via opérateur ou abonnement direct), **Amazon Prime Video Channels**
  (selon pays), **Sky**, **DAZN**…
- Les chaînes sportives gratuites (L'Équipe, Red Bull TV, fédérations) restent
  disponibles dans PrimeTV via le panneau « Sources libres » — voir
  [FREE_SOURCES.md](FREE_SOURCES.md).

> ⚠️ Un « revendeur IPTV » qui propose beIN Sports pour 10 DT/mois **n'a pas de licence**.
> Un revendeur légitime fournit une facture, une raison sociale, un support et un
> contrat ; en Tunisie, les offres commerciales passent par les opérateurs agréés.

---

## 3. Ce que PrimeTV peut faire avec un abonnement légitime

| Votre situation | Utilisation dans PrimeTV |
|---|---|
| Votre opérateur/fournisseur **agréé** vous a donné une **URL M3U/M3U8** | *Sources & playlists → Importer → URL* : import, catégorisation, favoris, EPG |
| Vous avez des **identifiants Xtream** (portail autorisé) | *Sources → Fournisseur → Xtream* (`/api/v1/playlists/xtream`) : import du catalogue |
| Le flux est en **ClearKey / AES-128** et vous détenez la clé | Ajoutez la clé depuis le lecteur (« Ajouter mes clés ») |
| Le flux est en **Widevine / PlayReady** (cas de beIN CONNECT) | ❌ Lecture impossible **par conception** : utilisez l'application officielle de votre diffuseur. PrimeTV reste utile pour organiser vos autres sources, l'EPG et les favoris |

### Importer un abonnement M3U

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@primetv.io","password":"PrimeTV#2026"}' | jq -r .access_token)

curl -s -X POST localhost:8080/api/v1/playlists \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Mon abonnement","url":"https://mon-fournisseur-agree.example/playlist.m3u"}'
```

### Importer un portail Xtream (autorisation requise)

```bash
curl -s -X POST localhost:8080/api/v1/playlists/xtream \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Mon portail","base_url":"https://portail-agree.example:8080",
       "username":"MON_COMPTE","password":"MON_MOT_DE_PASSE"}'
```

Les identifiants sont **chiffrés (Fernet)** en base et ne sont jamais renvoyés par l'API.

---

## 4. Vérifier qu'un fournisseur est sérieux (checklist)

- [ ] Raison sociale, adresse, mentions légales et **CGV** publiques.
- [ ] **Facture** et moyen de paiement traçable (pas de crypto, pas de Telegram).
- [ ] Prix **cohérent** avec le marché (beIN CONNECT ≈ 39 DT/mois : 10 DT/mois pour
      « tout le sport mondial » n'est pas crédible).
- [ ] Aucune promesse de « contourner » un blocage ni d'APK « spécial ».
- [ ] Support joignable, conditions de résiliation claires.
- [ ] Le service nomme les **ayants droit** avec lesquels il est en contrat.

Signaux d'alerte : « activation à vie », « panel », « pas de coupure garantie »,
« tous les sports pour 5 € », paiement uniquement en USDT, aucune identité.

---

## 5. Et si vous voulez seulement le sport gratuitement ?

C'est possible, légalement, pour une partie du contenu :

- **Chaînes publiques** qui diffusent des événements en clair (finales, compétitions
  internationales) — voir les listes « Sport » du panneau *Sources libres*.
- **FAST** : Red Bull TV, L'Équipe, Sport en France, beIN XTRA parfois en accès libre.
- **Résumés et magazines** sur les sites officiels des fédérations (FIFA, CAF, UEFA).

PrimeTV importe ces flux en un clic : [FREE_SOURCES.md](FREE_SOURCES.md).

---

## 6. Résumé

1. Aucun serveur « beIN Sports déchiffré » ne sera fourni : c'est illégal et
   techniquement impossible sans casser le DRM.
2. Les voies légales existent : **beIN CONNECT via Orange Tunisie ou Ooredoo**,
   ou abonnement direct.
3. PrimeTV accepte vos **propres** sources (M3U, Xtream autorisé, ClearKey légitime)
   et **refuse** de lire les flux DRM — c'est une garantie de conformité, pas un bug.
4. Pour le sport gratuit, utilisez le panneau « Sources libres ».

*Voir aussi : [SECURITY.md](SECURITY.md#drm-et-legalite) · [FREE_SOURCES.md](FREE_SOURCES.md) ·
[USER_GUIDE.md](USER_GUIDE.md).*
