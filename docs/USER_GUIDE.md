# Guide utilisateur

## 1. Se connecter

1. Ouvrez `http://localhost:8080`.
2. Connectez-vous avec le compte fourni à l'installation (`admin@primetv.io` / `PrimeTV#2026`)
   ou créez un compte si les inscriptions sont ouvertes.
3. Vous arrivez sur le **tableau de bord** : nombre de chaînes, bouquets, flux actifs, chaînes chiffrées.

> Le bouton 🌞/🌙 en haut à droite bascule entre thème sombre (par défaut) et clair.
> Le sélecteur de profil dans la barre supérieure change de profil sans se reconnecter.

---

## 2. Importer vos sources

Menu **Sources & playlists** → bouton **Importer**.

| Onglet | À utiliser quand… | Champs |
|---|---|---|
| **URL M3U / HLS** | vous avez un lien `http(s)://…/playlist.m3u` ou un manifeste `.m3u8` / `.mpd` | Nom (optionnel), URL |
| **Fichier** | vous possédez un fichier `.m3u` / `.m3u8` (40 Mo max) | sélection du fichier |
| **Xtream** | votre fournisseur vous a donné URL + identifiant + mot de passe | URL du portail, identifiant, mot de passe |
| **Coller le contenu** | vous voulez coller le texte `#EXTM3U…` | Nom, contenu |

**Ce qui se passe ensuite** : PrimeTV télécharge la playlist, détecte les chaînes et les radios,
classe automatiquement chaque chaîne (catégorie, langue, qualité, bouquet), enregistre les
URLs EPG trouvées (`url-tvg`) et affiche un récapitulatif.

> ⚠️ N'importez que des sources que vous êtes en droit d'utiliser.

### Fournisseurs

Un **fournisseur** regroupe plusieurs playlists/EPG (ex. « Mon abonnement », « Chaînes libres FR »).
Créez-en un avant vos imports si vous voulez organiser et filtrer par fournisseur.

### Resynchroniser

Sur une playlist : bouton **Synchroniser**. Les nouvelles chaînes sont ajoutées, les existantes mises à jour
(nom, logo, catégorie, chiffrement), et les chaînes disparues sont retirées. Les favoris et l'historique
sont conservés (clé stable = URL du flux).

---

## 3. EPG (guide TV)

1. **Sources & playlists → onglet EPG XMLTV**.
2. Ajoutez une URL (`https://…/epg.xml`) **ou** importez un fichier `.xml` / `.xmltv`.
3. Cliquez **Synchroniser**.

L'association se fait automatiquement :
`tvg-id` de la chaîne → `epg_channel_id` → nom normalisé (display-name du XMLTV).
Ensuite, **Guide TV** affiche les programmes par chaîne et le lecteur montre « en cours / à suivre ».

---

## 4. Regarder une chaîne

* Cliquez n'importe où sur une carte de chaîne.
* Le lecteur prend en charge **HLS**, **DASH**, **MP4** et les **radios**.
* Contrôles : lecture/pause, volume, qualité (auto ou manuelle), sous-titres, **Picture in Picture**,
  **plein écran**, reprise pour les contenus à durée.
* Raccourcis clavier : `Espace`/`K` lecture-pause, `M` muet, `F` plein écran, `P` PiP, `Échap` fermer.
* La progression est enregistrée toutes les 20 s ; retrouvez-la dans **Reprendre** sur le tableau de bord
  et dans **Historique**.

---

## 5. Rechercher et filtrer

* **Barre de recherche** en haut : nom, groupe, identifiant TVG. La recherche ignore les accents
  et les diacritiques arabes (« الجزيرة » trouve « الجزيره »).
* Page **Toutes les chaînes** :
  * chips de catégories, bouton **Radios**, case **Chiffrées** ;
  * panneau **Filtres** : langues et bouquets ;
  * tri : **Priorité (sport & arabe)**, **Nom**, **Dernier test**, **Ajout récent** ;
  * pagination en bas.

Par défaut, les chaînes **sportives** et **arabes** remontent en tête.

---

## 6. Favoris

* Cœur sur une carte = ajout/retrait immédiat.
* Les favoris sont **propres à chaque profil** (compte adulte ≠ profil enfant).
* Page **Favoris** → **Synchroniser** renvoie la liste actuelle au serveur (utile après plusieurs appareils).
* App Android : onglet **Favoris**, même comportement.

---

## 7. Profils

Menu **Réglages → Profils** :

* **Ajouter** un profil (nom, option enfant, code PIN 4–8 chiffres) ;
* **Activer** pour basculer (le profil actif colore l'interface et isole favoris/historique) ;
* **Modifier** langue et mode enfant ;
* **Supprimer** (au moins un profil doit rester).

Le profil actif est envoyé à l'API via `X-Profile-Id`.

---

## 8. Chaînes chiffrées et clés

Les cartes affichent un badge violet avec le type : `AES-128`, `CLEARKEY`, `WIDEVINE`, etc.

| Badge | Ce que vous pouvez faire |
|---|---|
| `AES-128` / `CLEARKEY` | Si vous **possédez** la clé (contenu libre, abonnement), ouvrez le lecteur → **Ajouter mes clés** → saisissez `KID` et `KEY` (hex). Le badge devient « Clés utilisateur actives ». |
| `WIDEVINE` / `PLAYREADY` / `FAIRPLAY` | Lecture **bloquée** avec message explicite. PrimeTV ne contourne pas les DRM. |

Filtrer : page **Toutes les chaînes → Filtres → Chaînes chiffrées uniquement**.

> Sans clé, un flux chiffré ne peut pas être lu : c'est normal. Ajoutez plutôt d'autres sources libres.

---

## 9. Scanner / actualiser

Page **Scan & actualisation** :

1. choisissez le périmètre (tout le catalogue ou une playlist) ;
2. laissez **Tester réellement les flux** activé ;
3. **Lancer le scan**.

Le job tourne en arrière-plan : vous pouvez quitter la page. La progression affiche
chaînes traitées, actives, hors ligne, chiffrées, DRM, ainsi que les logs.
L'historique des scans est conservé.

Après un scan, les cartes affichent « En ligne » / « Hors ligne » / « Chiffrée » et la qualité
détectée dans le manifeste (HD, FHD, 4K…).

---

## 10. Application Android

1. Installez l'APK fourni par votre administrateur (ou compilez-le, voir [INSTALL.md](INSTALL.md)).
2. Renseignez l'URL de l'API si elle n'est pas intégrée : elle est fixée à la compilation
   (`--dart-define=API_BASE_URL=…`).
3. Onglets : **Accueil** (stats, sport, arabe, reprendre), **Chaînes** (recherche + filtres),
   **Favoris**, **Sources** (import URL / coller M3U, scan), **Réglages** (profils, thème, déconnexion).
4. Lecture : bouton plein écran, favori, clés ClearKey.

---

## 11. Questions fréquentes

**Les images des logos ne s'affichent pas ?**
Certains serveurs bloquent le hotlinking. Le lecteur affiche alors les initiales de la chaîne.

**Un flux « En ligne » ne se lit pas ?**
Le serveur peut refuser le navigateur (User-Agent, CORS, token expiré). Essayez « Ouvrir la source »,
puis relancez un scan. Certains flux sont géo-restreints.

**Puis-je regarder plusieurs chaînes à la fois ?**
Non : un flux par lecteur. Ouvrez plusieurs onglets si nécessaire (les flux sont relayés par le proxy).

**Mes favoris ont disparu ?**
Vérifiez le profil actif : les favoris sont isolés par profil.

**Comment changer mon mot de passe ?**
Réglages → Sécurité → mot de passe actuel + nouveau (8 caractères minimum).
