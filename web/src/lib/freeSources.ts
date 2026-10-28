/**
 * Catalogue de sources **libres et légales** proposé dans l'interface.
 *
 * Règle de sélection :
 *  1. le flux appartient au diffuseur (chaîne publique ou service FAST) et il est
 *     publié volontairement, **ou**
 *  2. la liste est maintenue par un projet open source qui n'indexe que des flux
 *     publics (iptv-org, Free-TV) et qui respecte les demandes de retrait.
 *
 * Sont volontairement exclus : les abonnements revendus, les « panels » Xtream
 * pirates, les listes de chaînes payantes et tout contournement de DRM.
 * Voir `docs/FREE_SOURCES.md` et `docs/SECURITY.md`.
 */

export interface FreeSource {
  /** Identifiant stable (utilisé comme clé React). */
  id: string;
  /** Nom affiché. */
  name: string;
  /** Description courte (une ligne). */
  description: string;
  /** URL de la playlist M3U/M3U8. */
  url: string;
  /** Catégorie de présentation. */
  group: FreeSourceGroup;
  /** Estimation du nombre de chaînes (indicatif, évolue avec la source). */
  channels: string;
  /** Emoji/icône textuelle affichée sur la carte. */
  emoji: string;
  /** Provenance : projet communautaire ou diffuseur. */
  kind: 'communauté' | 'diffuseur';
}

export type FreeSourceGroup = 'Actualités' | 'Sport' | 'Divertissement' | 'Régions & langues';

const IPTV_ORG = 'https://iptv-org.github.io/iptv';
const FREE_TV = 'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8';

export const FREE_SOURCES: FreeSource[] = [
  {
    id: 'iptv-org-news',
    name: 'Actualités internationales',
    description: 'Chaînes d’information publiques du monde entier (DW, France 24, Al Jazeera, Euronews…)',
    url: `${IPTV_ORG}/categories/news.m3u`,
    group: 'Actualités',
    channels: '≈ 1 000',
    emoji: '📰',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-arabic',
    name: 'Chaînes arabes',
    description: 'Toutes les chaînes arabophones indexées (actualités, sport, religion, divertissement)',
    url: `${IPTV_ORG}/languages/ara.m3u`,
    group: 'Régions & langues',
    channels: '≈ 350',
    emoji: '🌍',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-sports',
    name: 'Sport',
    description: 'Sportives gratuites et fédérations (chaînes publiques, ligues, sports extrêmes)',
    url: `${IPTV_ORG}/categories/sports.m3u`,
    group: 'Sport',
    channels: '≈ 460',
    emoji: '⚽',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-france',
    name: 'France',
    description: 'Chaînes françaises gratuites (info publique, chaînes locales, web TV)',
    url: `${IPTV_ORG}/countries/fr.m3u`,
    group: 'Régions & langues',
    channels: '≈ 250',
    emoji: '🇫🇷',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-turkey',
    name: 'Turquie',
    description: 'Chaînes turques gratuites (TRT, Haber, chaînes locales)',
    url: `${IPTV_ORG}/countries/tr.m3u`,
    group: 'Régions & langues',
    channels: '≈ 120',
    emoji: '🇹🇷',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-spain',
    name: 'Espagne',
    description: 'Chaînes espagnoles gratuites (RTVE, autonomes, web TV)',
    url: `${IPTV_ORG}/countries/es.m3u`,
    group: 'Régions & langues',
    channels: '≈ 180',
    emoji: '🇪🇸',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-kids',
    name: 'Jeunesse',
    description: 'Chaînes pour enfants légalement accessibles (dessins animés, éducatif)',
    url: `${IPTV_ORG}/categories/kids.m3u`,
    group: 'Divertissement',
    channels: '≈ 430',
    emoji: '🧸',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-movies',
    name: 'Cinéma & séries',
    description: 'Chaînes FAST (financées par la publicité) et web TV de cinéma',
    url: `${IPTV_ORG}/categories/movies.m3u`,
    group: 'Divertissement',
    channels: '≈ 760',
    emoji: '🎬',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-music',
    name: 'Musique',
    description: 'Clips, concerts et radios musicales publiques',
    url: `${IPTV_ORG}/categories/music.m3u`,
    group: 'Divertissement',
    channels: '≈ 780',
    emoji: '🎵',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-documentary',
    name: 'Documentaires',
    description: 'Chaînes documentaires gratuites (nature, science, histoire)',
    url: `${IPTV_ORG}/categories/documentary.m3u`,
    group: 'Divertissement',
    channels: '≈ 250',
    emoji: '🌿',
    kind: 'communauté',
  },
  {
    id: 'free-tv',
    name: 'Free-TV — sélection curatée',
    description: 'Liste maintenue à la main : une seule URL par chaîne, priorité à la qualité HD',
    url: FREE_TV,
    group: 'Divertissement',
    channels: '≈ 1 000',
    emoji: '✅',
    kind: 'communauté',
  },
  {
    id: 'iptv-org-all',
    name: 'Catalogue complet iptv-org',
    description: 'Tout le catalogue (10 000+ chaînes). Volumineux : préférez les sélections ci-dessus',
    url: `${IPTV_ORG}/index.m3u`,
    group: 'Divertissement',
    channels: '≈ 10 000',
    emoji: '🌐',
    kind: 'communauté',
  },
];

/** Groupes dans l'ordre d'affichage. */
export const FREE_SOURCE_GROUPS: FreeSourceGroup[] = ['Actualités', 'Sport', 'Régions & langues', 'Divertissement'];

/** Sources EPG libres proposées pour l'association automatique. */
export interface FreeEpgSource {
  id: string;
  name: string;
  description: string;
  url: string;
  coverage: string;
}

export const FREE_EPG_SOURCES: FreeEpgSource[] = [
  {
    id: 'freeview-uk',
    name: 'Freeview (Royaume-Uni)',
    description: 'Guide XMLTV des chaînes gratuites britanniques, mis à jour quotidiennement',
    url: 'https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml',
    coverage: '≈ 100 chaînes UK',
  },
  {
    id: 'xmltvfr',
    name: 'XML-TV-Fr (France)',
    description: 'Guide francophone ; à auto-héberger ou à récupérer depuis une instance xmltvfr.fr',
    url: 'https://xmltvfr.fr/xmltv.xml',
    coverage: '≈ 200 chaînes FR/BE/CH',
  },
];

/** Filtre le catalogue par groupe (ou renvoie tout si `group` est absent). */
export function sourcesByGroup(group?: FreeSourceGroup): FreeSource[] {
  return group ? FREE_SOURCES.filter((source) => source.group === group) : FREE_SOURCES;
}
